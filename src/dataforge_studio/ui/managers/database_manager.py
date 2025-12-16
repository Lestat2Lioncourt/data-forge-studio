"""
Database Manager - Multi-tab SQL query interface with SSMS-style tree
"""

from typing import Optional, Union, Dict
import pyodbc
import sqlite3
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QTabWidget, QPushButton, QTreeWidget, QTreeWidgetItem,
                               QLabel, QMenu, QApplication, QInputDialog)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon, QAction, QCursor
import uuid

from .query_tab import QueryTab
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.distribution_analysis_dialog import DistributionAnalysisDialog
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, DatabaseConnection
from ...utils.image_loader import get_database_icon, get_icon
from ...utils.credential_manager import CredentialManager
from ...utils.network_utils import check_server_reachable

import logging
logger = logging.getLogger(__name__)


class DatabaseManager(QWidget):
    """
    Multi-tab SQL query manager with SSMS-style database explorer.

    Layout:
    - TOP: Toolbar (New Tab, Refresh, etc.)
    - LEFT: Database tree (connections > databases > tables/views > columns)
    - RIGHT: QTabWidget with multiple QueryTab instances
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.connections: Dict[str, Union[pyodbc.Connection, sqlite3.Connection]] = {}
        self.tab_counter = 1
        self._expand_connected = False

        self._setup_ui()
        self._load_all_connections()

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button("➕ New Query Tab", self._new_query_tab, icon="add.png")
        toolbar_builder.add_button(tr("btn_refresh_schema"), self._refresh_schema, icon="refresh.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("New Connection", self._new_connection)
        toolbar_builder.add_button("Manage Connections", self._manage_connections)

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter (left: tree, right: tabs)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Database explorer tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        tree_label = QLabel("Database Explorer")
        tree_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(tree_label)

        self.schema_tree = QTreeWidget()
        self.schema_tree.setHeaderHidden(True)
        self.schema_tree.setIndentation(20)
        self.schema_tree.setRootIsDecorated(False)  # No branch decoration for root items
        self.schema_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.schema_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.schema_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        left_layout.addWidget(self.schema_tree)

        main_splitter.addWidget(left_widget)

        # Right panel: Query tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)

        # Add welcome tab
        self._create_welcome_tab()

        main_splitter.addWidget(self.tab_widget)

        # Set splitter proportions (left 25%, right 75%)
        main_splitter.setSizes([300, 900])

        layout.addWidget(main_splitter)

    def _create_welcome_tab(self):
        """Create welcome tab"""
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Welcome to Database Manager")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        welcome_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Click '➕ New Query Tab' to start writing SQL queries")
        subtitle.setStyleSheet("font-size: 11pt; color: gray;")
        welcome_layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        info = QLabel("Double-click on tables/views in the explorer to generate SELECT queries")
        info.setStyleSheet("font-size: 10pt; color: gray;")
        welcome_layout.addWidget(info, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tab_widget.addTab(welcome_widget, "Welcome")

    def get_tree_widget(self):
        """Return the tree widget for embedding in ResourcesManager."""
        return self.schema_tree

    def refresh(self):
        """Public refresh method."""
        self._load_all_connections()

    def _load_all_connections(self):
        """Load all database connections into tree (lazy - no actual connection)"""
        self.schema_tree.clear()
        self.connections.clear()

        try:
            config_db = get_config_db()
            db_connections = config_db.get_all_database_connections()

            if not db_connections:
                no_conn_item = QTreeWidgetItem(self.schema_tree)
                no_conn_item.setText(0, "No connections configured")
                no_conn_item.setForeground(0, Qt.GlobalColor.gray)
                return

            for db_conn in db_connections:
                self._add_connection_node(db_conn)

        except Exception as e:
            logger.error(f"Error loading connections: {e}")

    def _add_connection_node(self, db_conn: DatabaseConnection):
        """Add a connection node to tree (lazy - no actual connection yet)"""
        # Create server node with DB type icon
        server_item = QTreeWidgetItem(self.schema_tree)

        # Set icon and text based on database type
        db_icon = get_database_icon(db_conn.db_type, size=16)
        if db_icon:
            server_item.setIcon(0, db_icon)
        server_item.setText(0, f"{db_conn.name} (clic pour connecter)")
        server_item.setForeground(0, Qt.GlobalColor.gray)
        server_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "server",
            "config": db_conn,
            "connected": False
        })

        # Add placeholder child to show expand arrow
        placeholder = QTreeWidgetItem(server_item)
        placeholder.setText(0, "Double-clic pour charger...")
        placeholder.setForeground(0, Qt.GlobalColor.gray)
        placeholder.setData(0, Qt.ItemDataRole.UserRole, {"type": "placeholder"})

        # Connect expand signal only once
        if not self._expand_connected:
            self.schema_tree.itemExpanded.connect(self._on_item_expanded)
            self._expand_connected = True

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion - lazy load schema if needed"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "server":
            return

        # Already connected?
        if data.get("connected"):
            return

        db_conn = data.get("config")
        if not db_conn:
            return

        # Remove placeholder
        while item.childCount() > 0:
            item.removeChild(item.child(0))

        # Actually connect now
        self._connect_and_load_schema(item, db_conn)

    def _get_main_window(self):
        """Find the main window to access status bar"""
        widget = self
        while widget is not None:
            if hasattr(widget, 'status_bar'):
                return widget
            # Check if parent has window attribute (for wrapped windows)
            if hasattr(widget, 'window') and hasattr(widget.window, 'status_bar'):
                return widget.window
            widget = widget.parent()
        return None

    def _set_status_message(self, message: str):
        """Set message in status bar if available"""
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, 'status_bar'):
            main_window.status_bar.set_message(message)

    def _connect_and_load_schema(self, server_item: QTreeWidgetItem, db_conn: DatabaseConnection):
        """Actually connect to database and load schema"""
        try:
            # Show wait cursor and status message
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            self._set_status_message(f"Connexion à {db_conn.name}...")

            # Update visual to show connecting
            server_item.setText(0, f"{db_conn.name} (connexion...)")
            server_item.setForeground(0, Qt.GlobalColor.yellow)
            QApplication.processEvents()

            # First, check if server is reachable (skip for local databases)
            if db_conn.db_type != "sqlite":
                self._set_status_message(f"Vérification de {db_conn.name}...")
                QApplication.processEvents()

                reachable, vpn_message = check_server_reachable(
                    db_conn.connection_string,
                    db_type=db_conn.db_type,
                    timeout=3
                )

                if not reachable:
                    error_item = QTreeWidgetItem(server_item)
                    error_item.setText(0, "Serveur non accessible")
                    error_item.setForeground(0, Qt.GlobalColor.red)
                    # Add VPN hint as child
                    vpn_item = QTreeWidgetItem(error_item)
                    vpn_item.setText(0, "VPN requis ? / VPN required?")
                    vpn_item.setForeground(0, Qt.GlobalColor.yellow)
                    server_item.setText(0, f"{db_conn.name} (non accessible)")
                    server_item.setForeground(0, Qt.GlobalColor.red)
                    server_item.setExpanded(True)
                    self._set_status_message(f"Serveur non accessible - VPN requis ?")
                    return

            if db_conn.db_type == "sqlite":
                # Handle both formats: "sqlite:///path" and "DRIVER={...};Database=path"
                conn_str = db_conn.connection_string
                if conn_str.startswith("sqlite:///"):
                    db_path = conn_str.replace("sqlite:///", "")
                elif "Database=" in conn_str:
                    # Extract path from ODBC-style connection string
                    import re
                    match = re.search(r'Database=([^;]+)', conn_str)
                    db_path = match.group(1) if match else conn_str
                else:
                    db_path = conn_str

                if Path(db_path).exists():
                    connection = sqlite3.connect(db_path)
                    self.connections[db_conn.id] = connection
                    self._load_sqlite_schema(server_item, connection, db_conn)
                    # Mark as connected
                    server_item.setText(0, db_conn.name)
                    server_item.setForeground(0, Qt.GlobalColor.white)
                    data = server_item.data(0, Qt.ItemDataRole.UserRole)
                    data["connected"] = True
                    server_item.setData(0, Qt.ItemDataRole.UserRole, data)
                    self._set_status_message(f"Connecté à {db_conn.name}")
                else:
                    error_item = QTreeWidgetItem(server_item)
                    error_item.setText(0, f"Erreur: Fichier introuvable")
                    error_item.setForeground(0, Qt.GlobalColor.red)
                    server_item.setText(0, f"{db_conn.name} (erreur)")
                    server_item.setForeground(0, Qt.GlobalColor.red)
                    self._set_status_message(f"Erreur: fichier introuvable")

            elif db_conn.db_type == "sqlserver":
                # Build connection string with credentials if needed
                conn_str = db_conn.connection_string

                # Check if NOT using Windows Authentication
                if "trusted_connection=yes" not in conn_str.lower():
                    # Retrieve credentials from secure storage
                    username, password = CredentialManager.get_credentials(db_conn.id)
                    if username and password:
                        # Add credentials to connection string if not already present
                        if "uid=" not in conn_str.lower() and "user id=" not in conn_str.lower():
                            if not conn_str.endswith(";"):
                                conn_str += ";"
                            conn_str += f"UID={username};PWD={password};"
                    else:
                        logger.warning(f"No credentials found for SQL Server connection: {db_conn.name}")

                # Set a timeout for SQL Server connections
                if "timeout" not in conn_str.lower() and "connection timeout" not in conn_str.lower():
                    conn_str += ";Connection Timeout=5"

                connection = pyodbc.connect(conn_str, timeout=5)
                self.connections[db_conn.id] = connection
                self._load_sqlserver_schema(server_item, connection, db_conn)
                # Mark as connected
                server_item.setText(0, db_conn.name)
                server_item.setForeground(0, Qt.GlobalColor.white)
                data = server_item.data(0, Qt.ItemDataRole.UserRole)
                data["connected"] = True
                server_item.setData(0, Qt.ItemDataRole.UserRole, data)
                self._set_status_message(f"Connecté à {db_conn.name}")

            else:
                # Other DB types - show as not supported yet
                error_item = QTreeWidgetItem(server_item)
                error_item.setText(0, f"Type non supporté: {db_conn.db_type}")
                error_item.setForeground(0, Qt.GlobalColor.yellow)
                self._set_status_message(f"Type non supporté: {db_conn.db_type}")

        except Exception as e:
            logger.warning(f"Could not connect to {db_conn.name}: {e}")
            error_item = QTreeWidgetItem(server_item)
            error_item.setText(0, f"Erreur: {str(e)[:50]}")
            error_item.setForeground(0, Qt.GlobalColor.red)
            server_item.setText(0, f"{db_conn.name} (erreur)")
            server_item.setForeground(0, Qt.GlobalColor.red)
            self._set_status_message(f"Erreur de connexion: {str(e)[:40]}")

        finally:
            # Always restore cursor
            QApplication.restoreOverrideCursor()

    def _load_sqlite_schema(self, server_item: QTreeWidgetItem,
                           connection: sqlite3.Connection,
                           db_conn: DatabaseConnection):
        """Load SQLite schema"""
        cursor = connection.cursor()

        # Tables folder
        tables_folder = QTreeWidgetItem(server_item)
        folder_icon = get_icon("RootFolders", size=16)
        if folder_icon:
            tables_folder.setIcon(0, folder_icon)
        tables_folder.setText(0, "Tables")
        tables_folder.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "tables_folder",
            "db_id": db_conn.id
        })

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            table_item = QTreeWidgetItem(tables_folder)
            # Use a simple style icon for tables
            table_icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogListView)
            table_item.setIcon(0, table_icon)
            table_item.setText(0, table_name)
            table_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "table",
                "name": table_name,
                "db_id": db_conn.id,
                "db_name": db_conn.name  # SQLite database name (connection name)
            })

            # Load columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                col_item = QTreeWidgetItem(table_item)
                col_item.setText(0, f"{col_name} ({col_type})")
                col_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "column",
                    "table": table_name,
                    "column": col_name
                })

        # Views folder
        views_folder = QTreeWidgetItem(server_item)
        if folder_icon:
            views_folder.setIcon(0, folder_icon)
        views_folder.setText(0, "Views")
        views_folder.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "views_folder",
            "db_id": db_conn.id
        })

        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()
        for view in views:
            view_item = QTreeWidgetItem(views_folder)
            # Use a different style icon for views
            view_icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView)
            view_item.setIcon(0, view_icon)
            view_item.setText(0, view[0])
            view_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "view",
                "name": view[0],
                "db_id": db_conn.id,
                "db_name": db_conn.name  # SQLite database name (connection name)
            })

    def _load_sqlserver_schema(self, server_item: QTreeWidgetItem,
                               connection: pyodbc.Connection,
                               db_conn: DatabaseConnection):
        """Load SQL Server schema"""
        cursor = connection.cursor()

        # Get databases
        try:
            cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4 ORDER BY name")
            databases = cursor.fetchall()
        except:
            databases = [(connection.getinfo(pyodbc.SQL_DATABASE_NAME),)]

        for db in databases:
            db_name = db[0]
            db_node = QTreeWidgetItem(server_item)
            # Use database icon
            db_icon = get_icon("database.png", size=16)
            if db_icon:
                db_node.setIcon(0, db_icon)
            db_node.setText(0, db_name)
            db_node.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "database",
                "name": db_name,
                "db_id": db_conn.id
            })

            try:
                # Tables folder
                tables_folder = QTreeWidgetItem(db_node)
                folder_icon = get_icon("RootFolders", size=16)
                if folder_icon:
                    tables_folder.setIcon(0, folder_icon)
                tables_folder.setText(0, "Tables")
                tables_folder.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "tables_folder",
                    "db_id": db_conn.id,
                    "db_name": db_name
                })

                # Get tables
                cursor.execute(f"""
                    SELECT s.name as schema_name, t.name as table_name
                    FROM [{db_name}].sys.tables t
                    INNER JOIN [{db_name}].sys.schemas s ON t.schema_id = s.schema_id
                    ORDER BY s.name, t.name
                """)
                tables = cursor.fetchall()

                for schema_name, table_name in tables:
                    full_name = f"{schema_name}.{table_name}"
                    table_item = QTreeWidgetItem(tables_folder)
                    # Use Qt standard icon for tables
                    table_icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogListView)
                    table_item.setIcon(0, table_icon)
                    table_item.setText(0, f"{schema_name}.{table_name}")
                    table_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "table",
                        "name": full_name,
                        "db_id": db_conn.id,
                        "db_name": db_name
                    })

                    # Load columns with sizes
                    cursor.execute(f"""
                        SELECT c.name, ty.name, c.max_length, c.precision, c.scale
                        FROM [{db_name}].sys.columns c
                        INNER JOIN [{db_name}].sys.types ty ON c.user_type_id = ty.user_type_id
                        INNER JOIN [{db_name}].sys.tables t ON c.object_id = t.object_id
                        INNER JOIN [{db_name}].sys.schemas s ON t.schema_id = s.schema_id
                        WHERE t.name = '{table_name}' AND s.name = '{schema_name}'
                        ORDER BY c.column_id
                    """)
                    columns = cursor.fetchall()
                    for col_name, col_type, max_length, precision, scale in columns:
                        type_display = col_type
                        if col_type in ('nvarchar', 'nchar'):
                            if max_length == -1:
                                type_display = f"{col_type}(MAX)"
                            elif max_length > 0:
                                type_display = f"{col_type}({max_length // 2})"
                        elif col_type in ('varchar', 'char', 'binary', 'varbinary'):
                            if max_length == -1:
                                type_display = f"{col_type}(MAX)"
                            elif max_length > 0:
                                type_display = f"{col_type}({max_length})"
                        elif col_type in ('decimal', 'numeric'):
                            type_display = f"{col_type}({precision},{scale})"

                        col_item = QTreeWidgetItem(table_item)
                        col_item.setText(0, f"{col_name} ({type_display})")
                        col_item.setData(0, Qt.ItemDataRole.UserRole, {
                            "type": "column",
                            "table": full_name,
                            "column": col_name
                        })

                # Views folder
                views_folder = QTreeWidgetItem(db_node)
                if folder_icon:
                    views_folder.setIcon(0, folder_icon)
                views_folder.setText(0, "Views")
                views_folder.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "views_folder",
                    "db_id": db_conn.id,
                    "db_name": db_name
                })

                cursor.execute(f"""
                    SELECT s.name, v.name
                    FROM [{db_name}].sys.views v
                    INNER JOIN [{db_name}].sys.schemas s ON v.schema_id = s.schema_id
                    ORDER BY s.name, v.name
                """)
                views = cursor.fetchall()
                for schema_name, view_name in views:
                    view_item = QTreeWidgetItem(views_folder)
                    # Use Qt standard icon for views
                    view_icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView)
                    view_item.setIcon(0, view_icon)
                    view_item.setText(0, f"{schema_name}.{view_name}")
                    view_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "view",
                        "name": f"{schema_name}.{view_name}",
                        "db_id": db_conn.id,
                        "db_name": db_name
                    })

            except Exception as e:
                logger.warning(f"Could not load schema for database {db_name}: {e}")

    def _on_tree_context_menu(self, position: QPoint):
        """Show context menu on tree item right-click"""
        item = self.schema_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        node_type = data.get("type", "")

        menu = QMenu(self.schema_tree)

        # Context menu for server (connection)
        if node_type == "server":
            # Edit connection (full dialog with credentials)
            edit_conn_action = QAction("Edit Connection...", self)
            edit_conn_action.triggered.connect(lambda: self._edit_full_connection(data["config"]))
            menu.addAction(edit_conn_action)

            # Edit name/description only
            edit_action = QAction("Edit Name & Description", self)
            edit_action.triggered.connect(lambda: self._edit_connection(data["config"]))
            menu.addAction(edit_action)

            menu.addSeparator()

            # Add to Workspace submenu (server = all databases)
            db_config = data.get("config")
            if db_config:
                workspace_menu = self._build_workspace_submenu(db_config.id, database_name=None)
                menu.addMenu(workspace_menu)
                menu.addSeparator()

            refresh_action = QAction("Refresh", self)
            refresh_action.triggered.connect(self._refresh_schema)
            menu.addAction(refresh_action)

            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

        # Context menu for individual database (SQL Server)
        elif node_type == "database":
            db_id = data.get("db_id")
            db_name = data.get("name")

            if db_id and db_name:
                # Add to Workspace submenu (specific database)
                workspace_menu = self._build_workspace_submenu(db_id, database_name=db_name)
                menu.addMenu(workspace_menu)

                menu.exec(self.schema_tree.viewport().mapToGlobal(position))

        # Context menu for tables and views
        elif node_type in ["table", "view"]:
            # SELECT TOP 100 action
            select_top_action = QAction("SELECT TOP 100 *", self)
            select_top_action.triggered.connect(lambda: self._generate_select_query(data, limit=100))
            menu.addAction(select_top_action)

            # SELECT * action
            select_all_action = QAction("SELECT *", self)
            select_all_action.triggered.connect(lambda: self._generate_select_query(data, limit=None))
            menu.addAction(select_all_action)

            menu.addSeparator()

            # Distribution Analysis action
            dist_action = QAction("📊 Distribution Analysis", self)
            dist_action.triggered.connect(lambda: self._show_distribution_analysis(data))
            menu.addAction(dist_action)

            # Show menu at cursor position
            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

    def _generate_select_query(self, data: dict, limit: Optional[int] = None):
        """Generate and insert a SELECT query in the current tab"""
        table_name = data["name"]
        db_id = data.get("db_id")
        db_name = data.get("db_name")  # Database name for SQL Server

        # Get or create a query tab
        current_tab = self._get_or_create_query_tab(db_id)

        if current_tab:
            # Generate query based on database type
            db_conn = self._get_connection_by_id(db_id)
            if db_conn:
                if db_conn.db_type == "sqlite":
                    if limit:
                        query = f"SELECT * FROM {table_name} LIMIT {limit}"
                    else:
                        query = f"SELECT * FROM {table_name}"
                elif db_conn.db_type == "sqlserver" and db_name:
                    # SQL Server: use fully qualified name [database].[schema].[table]
                    full_table_name = f"[{db_name}].{table_name}"
                    if limit:
                        query = f"SELECT TOP {limit} * FROM {full_table_name}"
                    else:
                        query = f"SELECT * FROM {full_table_name}"
                else:
                    # Other databases
                    if limit:
                        query = f"SELECT TOP {limit} * FROM {table_name}"
                    else:
                        query = f"SELECT * FROM {table_name}"

                current_tab.set_query_text(query)
                # Execute query automatically
                current_tab._execute_query()

    def _show_distribution_analysis(self, data: dict):
        """Show distribution analysis for a table or view"""
        table_name = data["name"]
        db_id = data.get("db_id")
        db_name = data.get("db_name")  # Database name for SQL Server

        # Get connection
        connection = self.connections.get(db_id)
        db_conn = self._get_connection_by_id(db_id)

        if not connection or not db_conn:
            DialogHelper.error("No database connection available", parent=self)
            return

        try:
            # Execute query to get data (limit to 10000 rows for analysis)
            cursor = connection.cursor()
            if db_conn.db_type == "sqlite":
                query = f"SELECT * FROM {table_name} LIMIT 10000"
            elif db_conn.db_type == "sqlserver" and db_name:
                # SQL Server: use fully qualified name
                full_table_name = f"[{db_name}].{table_name}"
                query = f"SELECT TOP 10000 * FROM {full_table_name}"
            else:
                query = f"SELECT TOP 10000 * FROM {table_name}"

            cursor.execute(query)

            # Get columns
            columns = [column[0] for column in cursor.description]

            # Fetch data
            rows = cursor.fetchall()
            data_list = [[cell for cell in row] for row in rows]

            if not data_list:
                DialogHelper.info("No data available for analysis", parent=self)
                return

            # Show distribution analysis dialog (non-modal to allow multiple windows)
            db_name = data.get("db_name", db_conn.name if db_conn else "Unknown")
            dialog = DistributionAnalysisDialog(data_list, columns, db_name, table_name, parent=self)
            dialog.show()

        except Exception as e:
            logger.error(f"Error analyzing distribution: {e}")
            DialogHelper.error("Distribution analysis failed", parent=self, details=str(e))

    def _on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item"""
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if not data:
            return

        node_type = data.get("type", "")

        if node_type in ["table", "view"]:
            # Generate SELECT TOP 100 query by default on double-click
            self._generate_select_query(data, limit=100)

    def _get_connection_by_id(self, db_id: str) -> Optional[DatabaseConnection]:
        """Get DatabaseConnection config by ID"""
        try:
            config_db = get_config_db()
            return config_db.get_database_connection(db_id)
        except:
            return None

    def _get_or_create_query_tab(self, db_id: str) -> Optional[QueryTab]:
        """Get existing query tab for database or create new one"""
        # Check if there's already a tab for this database
        for i in range(1, self.tab_widget.count()):  # Skip welcome tab
            widget = self.tab_widget.widget(i)
            if isinstance(widget, QueryTab) and widget.db_connection and widget.db_connection.id == db_id:
                self.tab_widget.setCurrentIndex(i)
                return widget

        # Create new tab for this database
        return self._new_query_tab(db_id)

    def _new_query_tab(self, db_id: Optional[str] = None) -> Optional[QueryTab]:
        """Create a new query tab"""
        # Get database connection
        db_conn = None
        connection = None

        if db_id:
            db_conn = self._get_connection_by_id(db_id)
            connection = self.connections.get(db_id)
        else:
            # Use first available connection
            if self.connections:
                first_id = list(self.connections.keys())[0]
                db_conn = self._get_connection_by_id(first_id)
                connection = self.connections.get(first_id)

        if not connection or not db_conn:
            DialogHelper.warning("No database connection available", parent=self)
            return None

        # Create query tab
        tab_name = f"Query {self.tab_counter}"
        self.tab_counter += 1

        query_tab = QueryTab(
            parent=self,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name
        )

        # Add to tab widget
        index = self.tab_widget.addTab(query_tab, tab_name)
        self.tab_widget.setCurrentIndex(index)

        logger.info(f"Created new query tab: {tab_name}")

        return query_tab

    def _close_tab(self, index: int):
        """Close a tab"""
        if index == 0:  # Don't close welcome tab
            return

        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        if widget:
            # Explicitly cleanup before destroying
            if isinstance(widget, QueryTab):
                widget.cleanup()
            widget.deleteLater()

    def _refresh_schema(self):
        """Refresh database schema tree"""
        self._load_all_connections()

    def _new_connection(self):
        """Open new connection dialog"""
        from PySide6.QtWidgets import QInputDialog
        from ..dialogs.connection_dialog_factory import ConnectionDialogFactory

        # Get supported database types with display names
        db_types_with_names = ConnectionDialogFactory.get_supported_types_with_names()

        # Create display list
        display_names = [name for _, name in db_types_with_names]

        db_type_display, ok = QInputDialog.getItem(
            self,
            "New Database Connection",
            "Select database type:",
            display_names,
            0,
            False
        )

        if not ok:
            return

        # Find the corresponding db_type identifier
        db_type = None
        for type_id, display_name in db_types_with_names:
            if display_name == db_type_display:
                db_type = type_id
                break

        if not db_type:
            return

        try:
            # Create dialog using factory
            dialog = ConnectionDialogFactory.create_dialog(db_type, parent=self)

            if dialog.exec():
                # Refresh tree to show new connection
                self._refresh_schema()

        except Exception as e:
            logger.error(f"Error creating connection dialog: {e}")
            DialogHelper.error("Error creating connection dialog", parent=self, details=str(e))

    def _manage_connections(self):
        """Open manage connections dialog"""
        DialogHelper.info("Manage connections feature - to be implemented", parent=self)

    def _edit_connection(self, db_conn: DatabaseConnection):
        """Edit database connection name and description"""
        from ..widgets.edit_dialogs import EditDatabaseConnectionDialog

        dialog = EditDatabaseConnectionDialog(
            parent=self,
            name=db_conn.name,
            description=db_conn.description or ""
        )

        if dialog.exec():
            name, description = dialog.get_values()

            if not name:
                DialogHelper.warning("Name cannot be empty", parent=self)
                return

            try:
                # Update connection
                db_conn.name = name
                db_conn.description = description

                # Save to database
                config_db = get_config_db()
                config_db.save_database_connection(db_conn)

                # Refresh tree
                self._refresh_schema()

                DialogHelper.info("Connection updated successfully", parent=self)

            except Exception as e:
                logger.error(f"Error updating connection: {e}")
                DialogHelper.error("Error updating connection", parent=self, details=str(e))

    def _edit_full_connection(self, db_conn: DatabaseConnection):
        """Edit full database connection including credentials"""
        from ..dialogs.connection_dialog_factory import ConnectionDialogFactory

        try:
            # Create dialog using factory with existing connection
            dialog = ConnectionDialogFactory.create_dialog(
                db_conn.db_type,
                parent=self,
                connection=db_conn
            )

            if dialog.exec():
                # Refresh tree to show updated connection
                self._refresh_schema()

        except Exception as e:
            logger.error(f"Error opening connection dialog: {e}")
            import traceback
            logger.error(traceback.format_exc())
            DialogHelper.error("Error opening connection dialog", parent=self, details=str(e))

    # ==================== Workspace Management ====================

    def _build_workspace_submenu(self, db_id: str, database_name: Optional[str] = None) -> QMenu:
        """
        Build a submenu for adding/removing a database to/from workspaces.

        Args:
            db_id: Database connection (server) ID
            database_name: Specific database name (None = server/all databases, str = specific database)

        Returns:
            QMenu with workspace options
        """
        from ...database.config_db import get_config_db, Workspace

        config_db = get_config_db()
        menu = QMenu(tr("menu_workspaces"), self)

        # Menu label based on what we're adding
        if database_name:
            menu.setTitle(f"{tr('menu_workspaces')} (base: {database_name})")
        else:
            menu.setTitle(f"{tr('menu_workspaces')} (serveur)")

        # Get all workspaces
        workspaces = config_db.get_all_workspaces()

        # Get workspaces this database belongs to
        # For specific database: check with database_name
        # For server: check with empty string (server-level)
        check_name = database_name if database_name else ''
        current_workspaces = config_db.get_database_workspaces(db_id, database_name=check_name)
        current_workspace_ids = {ws.id for ws in current_workspaces}

        # Add workspace options
        for ws in workspaces:
            is_in_workspace = ws.id in current_workspace_ids
            action = QAction(ws.name, self)
            action.setCheckable(True)
            action.setChecked(is_in_workspace)
            # Use default parameter to capture current values
            action.triggered.connect(
                lambda checked, wid=ws.id, did=db_id, dname=database_name, in_ws=is_in_workspace:
                    self._toggle_workspace_database(wid, did, dname, in_ws)
            )
            menu.addAction(action)

        # Separator and New Workspace option
        if workspaces:
            menu.addSeparator()

        new_action = QAction(tr("new_workspace") + "...", self)
        new_action.triggered.connect(
            lambda: self._create_new_workspace_and_add_database(db_id, database_name)
        )
        menu.addAction(new_action)

        return menu

    def _toggle_workspace_database(self, workspace_id: str, db_id: str,
                                    database_name: Optional[str], is_in_workspace: bool):
        """Toggle a database in/out of a workspace"""
        config_db = get_config_db()

        try:
            if is_in_workspace:
                # Remove from workspace
                config_db.remove_database_from_workspace(workspace_id, db_id, database_name)
                action_text = "Removed from"
            else:
                # Add to workspace
                config_db.add_database_to_workspace(workspace_id, db_id, database_name)
                action_text = "Added to"

            db_desc = f"database '{database_name}'" if database_name else "server"
            logger.info(f"{action_text} workspace: {db_desc} (db_id={db_id})")

        except Exception as e:
            logger.error(f"Error toggling workspace: {e}")
            DialogHelper.error("Error updating workspace", parent=self, details=str(e))

    def _create_new_workspace_and_add_database(self, db_id: str, database_name: Optional[str]):
        """Create a new workspace and add the database to it"""
        from ...database.config_db import Workspace

        name, ok = QInputDialog.getText(self, tr("new_workspace"), tr("workspace_name") + ":")
        if ok and name.strip():
            config_db = get_config_db()

            ws = Workspace(
                id=str(uuid.uuid4()),
                name=name.strip(),
                description=""
            )

            if config_db.add_workspace(ws):
                # Add database to the new workspace
                config_db.add_database_to_workspace(ws.id, db_id, database_name)
                db_desc = f"database '{database_name}'" if database_name else "server"
                logger.info(f"Created workspace '{ws.name}' and added {db_desc}")
            else:
                DialogHelper.warning("Failed to create workspace. Name may already exist.", parent=self)

    def cleanup(self):
        """
        Cleanup all resources - stop background loaders in query tabs.
        Called when the application is closing.
        """
        import threading

        # Cleanup all query tabs first (stop background threads)
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, QueryTab):
                try:
                    widget.cleanup()
                except Exception:
                    pass  # Ignore errors during shutdown

        # Close connections in background thread to not block UI
        connections_to_close = list(self.connections.values())
        self.connections.clear()

        def close_connections():
            for conn in connections_to_close:
                try:
                    conn.close()
                except Exception:
                    pass

        if connections_to_close:
            thread = threading.Thread(target=close_connections, daemon=True)
            thread.start()
            # Don't wait - let it run in background
