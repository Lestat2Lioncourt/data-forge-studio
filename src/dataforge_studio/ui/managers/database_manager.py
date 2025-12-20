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
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QIcon, QAction, QCursor
import uuid

from .query_tab import QueryTab
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.distribution_analysis_dialog import DistributionAnalysisDialog
from ..widgets.pinnable_panel import PinnablePanel
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, DatabaseConnection
from ...database.schema_loaders import SchemaLoaderFactory, SchemaNode, SchemaNodeType
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

    # Signal emitted when a query is saved in any QueryTab
    query_saved = Signal()

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

        # Left panel: Pinnable panel with database explorer tree
        self.left_panel = PinnablePanel(
            title="Database Explorer",
            icon_name="database.png"
        )
        self.left_panel.set_normal_width(280)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self.schema_tree = QTreeWidget()
        self.schema_tree.setHeaderHidden(True)
        self.schema_tree.setIndentation(20)
        self.schema_tree.setRootIsDecorated(False)  # No branch decoration for root items
        self.schema_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.schema_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.schema_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        tree_layout.addWidget(self.schema_tree)

        self.left_panel.set_content(tree_container)
        main_splitter.addWidget(self.left_panel)

        # Right panel: Query tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.tabBarDoubleClicked.connect(self._rename_query_tab)

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
        server_item.setText(0, db_conn.name)
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

        # Try to connect (placeholder will be removed only on success)
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

            QApplication.processEvents()

            # First, check if server is reachable (skip for local file-based databases)
            if db_conn.db_type not in ("sqlite", "access"):
                self._set_status_message(f"Connexion à la base {db_conn.name}...")
                QApplication.processEvents()

                reachable, vpn_message = check_server_reachable(
                    db_conn.connection_string,
                    db_type=db_conn.db_type,
                    timeout=3
                )

                if not reachable:
                    self._set_status_message(tr("status_ready"))
                    server_item.setExpanded(False)  # Collapse to allow retry
                    DialogHelper.warning(
                        f"Serveur non accessible : {db_conn.name}\n\nVérifiez que le VPN est actif.",
                        parent=self
                    )
                    return

            # Create connection based on database type
            connection = self._create_connection(db_conn)
            if connection is None:
                return

            self.connections[db_conn.id] = connection

            # Remove placeholder on success
            while server_item.childCount() > 0:
                server_item.removeChild(server_item.child(0))

            # Use SchemaLoaderFactory to load schema
            loader = SchemaLoaderFactory.create(
                db_conn.db_type, connection, db_conn.id, db_conn.name
            )
            if loader:
                schema = loader.load_schema()
                self._populate_tree_from_schema(server_item, schema, db_conn)

                # Update server node text for SQL Server (show database count)
                if db_conn.db_type == "sqlserver":
                    server_item.setText(0, schema.display_name)
            else:
                self._set_status_message(f"Type non supporté: {db_conn.db_type}")
                DialogHelper.warning(
                    f"Type de base non supporté : {db_conn.db_type}",
                    parent=self
                )
                return

            # Mark as connected
            data = server_item.data(0, Qt.ItemDataRole.UserRole)
            data["connected"] = True
            server_item.setData(0, Qt.ItemDataRole.UserRole, data)

            # Delay expansion to run after Qt's double-click toggle
            QTimer.singleShot(0, lambda item=server_item: item.setExpanded(True))
            self._set_status_message(f"Connecté à {db_conn.name}")

        except Exception as e:
            logger.warning(f"Could not connect to {db_conn.name}: {e}")
            self._set_status_message(tr("status_ready"))
            server_item.setExpanded(False)  # Collapse to allow retry
            DialogHelper.error(
                f"Erreur de connexion : {db_conn.name}",
                parent=self,
                details=str(e)
            )

        finally:
            # Always restore cursor
            QApplication.restoreOverrideCursor()

    def _create_connection(self, db_conn: DatabaseConnection):
        """
        Create a database connection based on connection type.

        Returns connection object or None if failed.
        """
        import re

        if db_conn.db_type == "sqlite":
            conn_str = db_conn.connection_string
            if conn_str.startswith("sqlite:///"):
                db_path = conn_str.replace("sqlite:///", "")
            elif "Database=" in conn_str:
                match = re.search(r'Database=([^;]+)', conn_str)
                db_path = match.group(1) if match else conn_str
            else:
                db_path = conn_str

            if not Path(db_path).exists():
                self._set_status_message(tr("status_ready"))
                DialogHelper.warning(f"Fichier introuvable : {db_path}", parent=self)
                return None

            return sqlite3.connect(db_path)

        elif db_conn.db_type == "sqlserver":
            conn_str = db_conn.connection_string

            # Check if NOT using Windows Authentication
            if "trusted_connection=yes" not in conn_str.lower():
                username, password = CredentialManager.get_credentials(db_conn.id)
                if username and password:
                    if "uid=" not in conn_str.lower() and "user id=" not in conn_str.lower():
                        if not conn_str.endswith(";"):
                            conn_str += ";"
                        conn_str += f"UID={username};PWD={password};"
                else:
                    logger.warning(f"No credentials found for SQL Server connection: {db_conn.name}")

            # Set a timeout for SQL Server connections
            if "timeout" not in conn_str.lower() and "connection timeout" not in conn_str.lower():
                conn_str += ";Connection Timeout=5"

            return pyodbc.connect(conn_str, timeout=5)

        elif db_conn.db_type == "access":
            conn_str = db_conn.connection_string

            # Extract file path from connection string
            db_path = None
            if "Dbq=" in conn_str:
                match = re.search(r'Dbq=([^;]+)', conn_str, re.IGNORECASE)
                db_path = match.group(1) if match else None

            if not db_path or not Path(db_path).exists():
                self._set_status_message(tr("status_ready"))
                DialogHelper.warning(
                    f"Fichier Access introuvable : {db_path or 'chemin non spécifié'}",
                    parent=self
                )
                return None

            # Add password if stored in credentials
            _, password = CredentialManager.get_credentials(db_conn.id)
            if password and "Pwd=" not in conn_str:
                if not conn_str.endswith(";"):
                    conn_str += ";"
                conn_str += f"Pwd={password};"

            return pyodbc.connect(conn_str, timeout=5)

        else:
            # Unsupported database type
            return None

    def _populate_tree_from_schema(self, parent_item: QTreeWidgetItem,
                                    schema: SchemaNode, db_conn: DatabaseConnection):
        """
        Populate tree widget from SchemaNode structure.

        Converts the abstract SchemaNode tree into QTreeWidgetItem hierarchy,
        setting appropriate icons, text, and metadata for each node.
        """
        folder_icon = get_icon("RootFolders", size=16)
        db_icon = get_icon("database.png", size=16)
        proc_icon = get_icon("scripts.png", size=16)
        func_icon = get_icon("jobs.png", size=16)
        table_icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogListView)
        view_icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView)

        def create_item(node: SchemaNode, parent: QTreeWidgetItem) -> QTreeWidgetItem:
            """Recursively create tree items from schema nodes."""
            item = QTreeWidgetItem(parent)
            item.setText(0, node.display_name)

            # Build metadata from node type and node.metadata
            metadata = dict(node.metadata)  # Copy existing metadata
            metadata["db_id"] = db_conn.id

            # Map SchemaNodeType to tree item type and icon
            if node.node_type == SchemaNodeType.DATABASE:
                if metadata.get("is_server"):
                    metadata["type"] = "server"
                else:
                    metadata["type"] = "database"
                    if db_icon:
                        item.setIcon(0, db_icon)

            elif node.node_type == SchemaNodeType.TABLES_FOLDER:
                metadata["type"] = "tables_folder"
                if folder_icon:
                    item.setIcon(0, folder_icon)

            elif node.node_type == SchemaNodeType.VIEWS_FOLDER:
                metadata["type"] = "views_folder"
                if folder_icon:
                    item.setIcon(0, folder_icon)

            elif node.node_type == SchemaNodeType.PROCEDURES_FOLDER:
                if metadata.get("is_functions"):
                    metadata["type"] = "functions_folder"
                    if func_icon:
                        item.setIcon(0, func_icon)
                    elif folder_icon:
                        item.setIcon(0, folder_icon)
                else:
                    metadata["type"] = "procedures_folder"
                    if proc_icon:
                        item.setIcon(0, proc_icon)
                    elif folder_icon:
                        item.setIcon(0, folder_icon)

            elif node.node_type == SchemaNodeType.TABLE:
                metadata["type"] = "table"
                metadata["name"] = node.name
                # Set db_name from node metadata or fallback to connection name
                if "db_name" not in metadata:
                    metadata["db_name"] = db_conn.name
                item.setIcon(0, table_icon)

            elif node.node_type == SchemaNodeType.VIEW:
                metadata["type"] = "view"
                metadata["name"] = node.name
                if "db_name" not in metadata:
                    metadata["db_name"] = db_conn.name
                item.setIcon(0, view_icon)

            elif node.node_type == SchemaNodeType.COLUMN:
                metadata["type"] = "column"
                metadata["column"] = node.name
                # table should already be in metadata from schema loader

            elif node.node_type == SchemaNodeType.PROCEDURE:
                if metadata.get("is_function"):
                    metadata["type"] = "function"
                    if func_icon:
                        item.setIcon(0, func_icon)
                else:
                    metadata["type"] = "procedure"
                    if proc_icon:
                        item.setIcon(0, proc_icon)

            item.setData(0, Qt.ItemDataRole.UserRole, metadata)

            # Recursively create children
            for child in node.children:
                create_item(child, item)

            return item

        # Create items for all children of the schema root
        for child in schema.children:
            create_item(child, parent_item)

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

            menu.addSeparator()

            # Delete connection
            delete_action = QAction("🗑️ Delete Connection", self)
            delete_action.triggered.connect(lambda: self._delete_connection(data["config"]))
            menu.addAction(delete_action)

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

            # Edit Code for views only
            if node_type == "view":
                edit_code_action = QAction("✏️ Edit Code (ALTER VIEW)", self)
                edit_code_action.triggered.connect(lambda: self._load_view_code(data))
                menu.addAction(edit_code_action)
                menu.addSeparator()

            # Distribution Analysis action
            dist_action = QAction("📊 Distribution Analysis", self)
            dist_action.triggered.connect(lambda: self._show_distribution_analysis(data))
            menu.addAction(dist_action)

            # Show menu at cursor position
            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

        # Context menu for stored procedures
        elif node_type == "procedure":
            # View code
            view_code_action = QAction("📄 View Code", self)
            view_code_action.triggered.connect(lambda: self._load_routine_code(data))
            menu.addAction(view_code_action)

            menu.addSeparator()

            # Generate EXEC template
            exec_action = QAction("⚡ Generate EXEC Template", self)
            exec_action.triggered.connect(lambda: self._generate_exec_template(data))
            menu.addAction(exec_action)

            # Copy name
            copy_name_action = QAction("📋 Copy Name", self)
            copy_name_action.triggered.connect(
                lambda: QApplication.clipboard().setText(f"[{data.get('db_name')}].[{data.get('schema')}].[{data.get('proc_name')}]")
            )
            menu.addAction(copy_name_action)

            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

        # Context menu for functions
        elif node_type == "function":
            # View code
            view_code_action = QAction("📄 View Code", self)
            view_code_action.triggered.connect(lambda: self._load_routine_code(data))
            menu.addAction(view_code_action)

            menu.addSeparator()

            # Generate SELECT template
            select_action = QAction("⚡ Generate SELECT Template", self)
            select_action.triggered.connect(lambda: self._generate_select_function(data))
            menu.addAction(select_action)

            # Copy name
            copy_name_action = QAction("📋 Copy Name", self)
            copy_name_action.triggered.connect(
                lambda: QApplication.clipboard().setText(f"[{data.get('db_name')}].[{data.get('schema')}].[{data.get('func_name')}]")
            )
            menu.addAction(copy_name_action)

            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

    def _generate_select_query(self, data: dict, limit: Optional[int] = None):
        """Generate and execute a SELECT query in a NEW tab named after the table"""
        table_name = data["name"]
        db_id = data.get("db_id")
        db_name = data.get("db_name")  # Database name for SQL Server

        # Get database connection
        db_conn = self._get_connection_by_id(db_id)
        connection = self.connections.get(db_id)

        if not connection or not db_conn:
            DialogHelper.warning("Database not connected. Please expand the database node first.", parent=self)
            return

        # Generate query based on database type
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

        # Always create a NEW tab named after the table (don't reuse existing)
        # Extract simple table name for tab title (remove schema prefix if present)
        simple_name = table_name.split('.')[-1].strip('[]')
        tab_name = simple_name

        query_tab = QueryTab(
            parent=self,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name,
            database_manager=self
        )

        # Connect query_saved signal
        query_tab.query_saved.connect(self.query_saved.emit)

        # Add to tab widget
        index = self.tab_widget.addTab(query_tab, tab_name)
        self.tab_widget.setCurrentIndex(index)

        # Set query and execute
        query_tab.set_query_text(query)
        query_tab._execute_query()

        logger.info(f"Created query tab '{tab_name}' for table {table_name}")

    def _load_view_code(self, data: dict):
        """Load view code into query editor as ALTER VIEW"""
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        view_name = data.get("name")  # schema.viewname

        if not all([db_id, db_name, view_name]):
            return

        # Parse schema and view name
        parts = view_name.split(".")
        if len(parts) == 2:
            schema, name = parts
        else:
            schema = "dbo"
            name = view_name

        # Get connection
        connection = self.connections.get(db_id)
        if not connection:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            cursor = connection.cursor()

            # Get view definition from sys.sql_modules
            cursor.execute(f"""
                SELECT m.definition
                FROM [{db_name}].sys.sql_modules m
                INNER JOIN [{db_name}].sys.views v ON m.object_id = v.object_id
                INNER JOIN [{db_name}].sys.schemas s ON v.schema_id = s.schema_id
                WHERE v.name = ? AND s.name = ?
            """, (name, schema))

            result = cursor.fetchone()

            if result and result[0]:
                code = result[0]

                # Convert CREATE VIEW to ALTER VIEW
                import re
                # Match CREATE VIEW (case insensitive) and replace with ALTER VIEW
                code = re.sub(
                    r'\bCREATE\s+VIEW\b',
                    'ALTER VIEW',
                    code,
                    count=1,
                    flags=re.IGNORECASE
                )

                # Get or create a query tab
                current_tab = self._get_or_create_query_tab(db_id)

                if current_tab:
                    current_tab.set_query_text(code)
                    logger.info(f"Loaded view code: {schema}.{name}")
            else:
                DialogHelper.warning(
                    f"Could not retrieve code for view {schema}.{name}\n"
                    "You may not have permission to view the definition.",
                    parent=self
                )

        except Exception as e:
            logger.error(f"Error loading view code: {e}")
            DialogHelper.error(
                "Error loading view code",
                parent=self,
                details=str(e)
            )

    def _load_routine_code(self, data: dict):
        """Load stored procedure or function code into query editor"""
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        routine_type = data.get("type")  # "procedure" or "function"

        if routine_type == "procedure":
            routine_name = data.get("proc_name")
        else:
            routine_name = data.get("func_name")

        if not all([db_id, db_name, schema, routine_name]):
            return

        # Get connection
        connection = self.connections.get(db_id)
        if not connection:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            cursor = connection.cursor()

            # Get routine definition from sys.sql_modules
            cursor.execute(f"""
                SELECT m.definition
                FROM [{db_name}].sys.sql_modules m
                INNER JOIN [{db_name}].sys.objects o ON m.object_id = o.object_id
                INNER JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
                WHERE o.name = ? AND s.name = ?
            """, (routine_name, schema))

            result = cursor.fetchone()

            if result and result[0]:
                code = result[0]

                # Get or create a query tab
                current_tab = self._get_or_create_query_tab(db_id)

                if current_tab:
                    current_tab.set_query_text(code)
                    logger.info(f"Loaded {routine_type} code: {schema}.{routine_name}")
            else:
                DialogHelper.warning(
                    f"Could not retrieve code for {schema}.{routine_name}\n"
                    "You may not have permission to view the definition.",
                    parent=self
                )

        except Exception as e:
            logger.error(f"Error loading routine code: {e}")
            DialogHelper.error(
                f"Error loading {routine_type} code",
                parent=self,
                details=str(e)
            )

    def _generate_exec_template(self, data: dict):
        """Generate EXEC template for stored procedure"""
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        proc_name = data.get("proc_name")

        if not all([db_id, db_name, schema, proc_name]):
            return

        # Get connection to fetch parameters
        connection = self.connections.get(db_id)
        if not connection:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            cursor = connection.cursor()

            # Get procedure parameters
            cursor.execute(f"""
                SELECT p.name, t.name as type_name, p.max_length, p.is_output
                FROM [{db_name}].sys.parameters p
                INNER JOIN [{db_name}].sys.types t ON p.user_type_id = t.user_type_id
                INNER JOIN [{db_name}].sys.procedures pr ON p.object_id = pr.object_id
                INNER JOIN [{db_name}].sys.schemas s ON pr.schema_id = s.schema_id
                WHERE pr.name = ? AND s.name = ?
                ORDER BY p.parameter_id
            """, (proc_name, schema))

            params = cursor.fetchall()

            # Build EXEC template
            full_name = f"[{db_name}].[{schema}].[{proc_name}]"

            if params:
                param_list = []
                for param_name, type_name, max_length, is_output in params:
                    output_str = " OUTPUT" if is_output else ""
                    param_list.append(f"    {param_name} = NULL{output_str}  -- {type_name}")

                template = f"EXEC {full_name}\n" + ",\n".join(param_list)
            else:
                template = f"EXEC {full_name}"

            # Load into editor
            current_tab = self._get_or_create_query_tab(db_id)
            if current_tab:
                current_tab.set_query_text(template)

        except Exception as e:
            logger.error(f"Error generating EXEC template: {e}")
            # Fallback to simple template
            full_name = f"[{db_name}].[{schema}].[{proc_name}]"
            current_tab = self._get_or_create_query_tab(db_id)
            if current_tab:
                current_tab.set_query_text(f"EXEC {full_name}")

    def _generate_select_function(self, data: dict):
        """Generate SELECT template for function"""
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        func_name = data.get("func_name")
        func_type = data.get("func_type", "")

        if not all([db_id, db_name, schema, func_name]):
            return

        full_name = f"[{db_name}].[{schema}].[{func_name}]"

        # Get connection to fetch parameters
        connection = self.connections.get(db_id)

        template = ""
        if connection:
            try:
                cursor = connection.cursor()

                # Get function parameters
                cursor.execute(f"""
                    SELECT p.name, t.name as type_name
                    FROM [{db_name}].sys.parameters p
                    INNER JOIN [{db_name}].sys.types t ON p.user_type_id = t.user_type_id
                    INNER JOIN [{db_name}].sys.objects o ON p.object_id = o.object_id
                    INNER JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
                    WHERE o.name = ? AND s.name = ? AND p.parameter_id > 0
                    ORDER BY p.parameter_id
                """, (func_name, schema))

                params = cursor.fetchall()

                if params:
                    param_placeholders = ", ".join([f"NULL /* {p[0]}: {p[1]} */" for p in params])
                else:
                    param_placeholders = ""

                # Table-valued function vs scalar function
                if "TABLE" in func_type.upper():
                    template = f"SELECT * FROM {full_name}({param_placeholders})"
                else:
                    template = f"SELECT {full_name}({param_placeholders})"

            except Exception as e:
                logger.warning(f"Could not get function parameters: {e}")

        if not template:
            # Fallback
            if "TABLE" in func_type.upper():
                template = f"SELECT * FROM {full_name}()"
            else:
                template = f"SELECT {full_name}()"

        current_tab = self._get_or_create_query_tab(db_id)
        if current_tab:
            current_tab.set_query_text(template)

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

        if node_type == "server" and not data.get("connected", False):
            # Try to connect (first attempt or retry, same code)
            db_conn = data.get("config")
            if db_conn:
                self._connect_and_load_schema(item, db_conn)

        elif node_type in ["table", "view"]:
            # Generate SELECT TOP 100 query by default on double-click
            self._generate_select_query(data, limit=100)

        elif node_type in ["procedure", "function"]:
            # Load procedure/function code into editor
            self._load_routine_code(data)

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
            tab_name=tab_name,
            database_manager=self
        )

        # Connect query_saved signal to forward to DatabaseManager's signal
        query_tab.query_saved.connect(self.query_saved.emit)

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

    def _rename_query_tab(self, index: int):
        """Rename a query tab via double-click."""
        if index == 0:  # Don't rename welcome tab
            return

        current_name = self.tab_widget.tabText(index)
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Tab / Renommer l'onglet",
            "New name / Nouveau nom:",
            text=current_name
        )

        if ok and new_name.strip():
            self.tab_widget.setTabText(index, new_name.strip())
            # Also update QueryTab's tab_name attribute
            widget = self.tab_widget.widget(index)
            if hasattr(widget, 'tab_name'):
                widget.tab_name = new_name.strip()
            logger.info(f"Renamed tab from '{current_name}' to '{new_name.strip()}'")

    def _refresh_schema(self):
        """Refresh database schema tree"""
        self._load_all_connections()

    def _new_connection(self):
        """Open new connection dialog using ConnectionSelectorDialog"""
        from ..dialogs.connection_dialogs import ConnectionSelectorDialog

        dialog = ConnectionSelectorDialog(parent=self)
        dialog.connection_created.connect(self._refresh_schema)
        dialog.exec()

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

    def _delete_connection(self, db_conn: DatabaseConnection):
        """Delete a database connection after confirmation."""
        config_db = get_config_db()

        # Check if database is used in workspaces
        workspaces = config_db.get_database_workspaces(db_conn.id)

        if workspaces:
            workspace_names = ", ".join(ws.name for ws in workspaces)
            confirm = DialogHelper.confirm(
                f"Delete connection '{db_conn.name}'?\n\n"
                f"⚠️ This connection is used in {len(workspaces)} workspace(s):\n"
                f"{workspace_names}\n\n"
                f"The connection will be removed from these workspaces.\n"
                f"The database itself will not be deleted.",
                parent=self
            )
        else:
            confirm = DialogHelper.confirm(
                f"Delete connection '{db_conn.name}'?\n\n"
                f"This will remove the connection configuration.\n"
                f"The database itself will not be deleted.",
                parent=self
            )

        if not confirm:
            return

        try:
            # Close active connection if any
            if db_conn.id in self.connections:
                try:
                    self.connections[db_conn.id].close()
                except Exception:
                    pass
                del self.connections[db_conn.id]

            # Remove from all workspaces first
            for ws in workspaces:
                config_db.remove_database_from_workspace(ws.id, db_conn.id)

            # Delete credentials from keyring
            CredentialManager.delete_credentials(db_conn.id)

            # Delete from config database
            config_db.delete_database_connection(db_conn.id)

            # Refresh the tree
            self._refresh_schema()

            self._set_status_message(f"Connection '{db_conn.name}' deleted")
            logger.info(f"Deleted connection: {db_conn.name} ({db_conn.id})")

        except Exception as e:
            logger.error(f"Error deleting connection: {e}")
            DialogHelper.error("Error deleting connection", parent=self, details=str(e))

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

    def reconnect_database(self, db_id: str) -> Optional[Union[pyodbc.Connection, sqlite3.Connection]]:
        """
        Reconnect to a database and update all QueryTabs using this connection.

        Args:
            db_id: Database connection ID

        Returns:
            New connection object or None if failed
        """
        # Close existing connection if any
        old_conn = self.connections.pop(db_id, None)
        if old_conn:
            try:
                old_conn.close()
            except Exception:
                pass

        # Get connection config
        db_conn = self._get_connection_by_id(db_id)
        if not db_conn:
            return None

        # Try to reconnect
        try:
            if db_conn.db_type == "sqlite":
                conn_str = db_conn.connection_string
                if conn_str.startswith("sqlite:///"):
                    db_path = conn_str.replace("sqlite:///", "")
                elif "Database=" in conn_str:
                    import re
                    match = re.search(r'Database=([^;]+)', conn_str)
                    db_path = match.group(1) if match else conn_str
                else:
                    db_path = conn_str

                connection = sqlite3.connect(db_path)
                self.connections[db_id] = connection

            elif db_conn.db_type == "sqlserver":
                conn_str = db_conn.connection_string

                if "trusted_connection=yes" not in conn_str.lower():
                    from ...utils.credential_manager import CredentialManager
                    username, password = CredentialManager.get_credentials(db_id)
                    if username and password:
                        if "uid=" not in conn_str.lower() and "user id=" not in conn_str.lower():
                            if not conn_str.endswith(";"):
                                conn_str += ";"
                            conn_str += f"UID={username};PWD={password};"

                if "timeout" not in conn_str.lower() and "connection timeout" not in conn_str.lower():
                    conn_str += ";Connection Timeout=5"

                connection = pyodbc.connect(conn_str, timeout=5)
                self.connections[db_id] = connection
            else:
                return None

            # Update all QueryTabs using this connection
            self._update_query_tabs_connection(db_id, connection)

            logger.info(f"Reconnected to database: {db_conn.name}")
            return connection

        except Exception as e:
            logger.error(f"Failed to reconnect to {db_conn.name}: {e}")
            return None

    def _update_query_tabs_connection(self, db_id: str, new_connection):
        """Update connection reference in all QueryTabs using this db_id"""
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, QueryTab):
                if widget.db_connection and widget.db_connection.id == db_id:
                    widget.connection = new_connection
                    logger.debug(f"Updated connection in tab: {widget.tab_name}")

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
