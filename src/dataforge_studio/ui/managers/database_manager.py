"""
Database Manager - Multi-tab SQL query interface with SSMS-style tree
"""

from __future__ import annotations
from typing import Optional, Union, Dict, Any, TYPE_CHECKING
try:
    import pyodbc
except ImportError:
    pyodbc = None
import sqlite3

if TYPE_CHECKING:
    from .workspace_manager import WorkspaceManager
import re
import threading
import traceback
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QTabWidget, QPushButton, QTreeWidget, QTreeWidgetItem,
                               QLabel, QMenu, QApplication, QInputDialog, QFileDialog)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QThread
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
from ...database.dialects import DialectFactory, DatabaseDialect
from ...utils.image_loader import get_database_icon, get_icon
from ...utils.credential_manager import CredentialManager
from ...utils.network_utils import check_server_reachable
from ...config.user_preferences import UserPreferences
from ...utils.workspace_export import (
    export_connections_to_json, save_export_to_file, get_export_summary,
    load_import_from_file, import_connections_from_json
)
from ...utils.connection_error_handler import format_connection_error, get_server_unreachable_message
from ...database.sqlserver_connection import connect_sqlserver

import logging
logger = logging.getLogger(__name__)


class DatabaseConnectionWorker(QThread):
    """
    Worker thread for database connection operations.

    Runs connection and schema loading in background to avoid UI freezing.
    """

    # Signals
    connection_success = Signal(object, object)  # connection, schema
    connection_error = Signal(str)  # error message
    status_update = Signal(str)  # status message for UI

    def __init__(self, db_conn: DatabaseConnection, parent=None):
        super().__init__(parent)
        self.db_conn = db_conn
        self._cancelled = False

    def run(self):
        """Execute connection in background thread."""
        try:
            # Check server reachability for remote databases
            if self.db_conn.db_type not in ("sqlite", "access"):
                self.status_update.emit(f"Vérification de {self.db_conn.name}...")

                reachable, vpn_message = check_server_reachable(
                    self.db_conn.connection_string,
                    db_type=self.db_conn.db_type,
                    timeout=3
                )

                if not reachable:
                    error_msg = get_server_unreachable_message(
                        self.db_conn.name,
                        db_type=self.db_conn.db_type
                    )
                    self.connection_error.emit(error_msg)
                    return

            if self._cancelled:
                return

            self.status_update.emit(f"Connexion à {self.db_conn.name}...")

            # Create connection
            connection = self._create_connection()
            if connection is None:
                return

            if self._cancelled:
                return

            self.status_update.emit(f"Chargement du schéma {self.db_conn.name}...")

            # Load schema
            loader = SchemaLoaderFactory.create(
                self.db_conn.db_type, connection, self.db_conn.id, self.db_conn.name
            )

            if loader:
                schema = loader.load_schema()
                self.connection_success.emit(connection, schema)
            else:
                self.connection_error.emit(f"Type de base non supporté : {self.db_conn.db_type}")

        except Exception as e:
            logger.error(f"Connection error: {e}")
            error_msg = format_connection_error(e, db_type=self.db_conn.db_type)
            self.connection_error.emit(error_msg)

    def _create_connection(self):
        """Create database connection based on type."""
        try:
            if self.db_conn.db_type == "sqlite":
                conn_str = self.db_conn.connection_string
                if conn_str.startswith("sqlite:///"):
                    db_path = conn_str.replace("sqlite:///", "")
                elif "Database=" in conn_str:
                    match = re.search(r'Database=([^;]+)', conn_str)
                    db_path = match.group(1) if match else conn_str
                else:
                    db_path = conn_str

                if not Path(db_path).exists():
                    self.connection_error.emit(f"Fichier introuvable : {db_path}")
                    return None

                return sqlite3.connect(db_path, check_same_thread=False)

            elif self.db_conn.db_type == "sqlserver":
                conn_str = self.db_conn.connection_string

                # Check if NOT using Windows Authentication
                if "trusted_connection=yes" not in conn_str.lower():
                    username, password = CredentialManager.get_credentials(self.db_conn.id)
                    if username and password:
                        if "uid=" not in conn_str.lower() and "user id=" not in conn_str.lower():
                            if not conn_str.endswith(";"):
                                conn_str += ";"
                            conn_str += f"UID={username};PWD={password};"

                return connect_sqlserver(conn_str, timeout=5)

            elif self.db_conn.db_type == "access":
                conn_str = self.db_conn.connection_string

                # Extract file path from connection string
                db_path = None
                if "Dbq=" in conn_str:
                    match = re.search(r'Dbq=([^;]+)', conn_str, re.IGNORECASE)
                    db_path = match.group(1) if match else None

                if not db_path or not Path(db_path).exists():
                    self.connection_error.emit(f"Fichier Access introuvable")
                    return None

                if pyodbc is None:
                    self.connection_error.emit("pyodbc requis pour les bases Access")
                    return None
                return pyodbc.connect(conn_str)

            elif self.db_conn.db_type == "postgresql":
                import psycopg2
                conn_str = self.db_conn.connection_string

                # Parse postgresql:// URL format
                if conn_str.startswith("postgresql://"):
                    url_part = conn_str.replace("postgresql://", "")

                    # Get credentials from keyring if available
                    username, password = CredentialManager.get_credentials(self.db_conn.id)

                    # Parse URL: [user:pass@]host[:port][/database]
                    if "@" in url_part:
                        auth_part, server_part = url_part.split("@", 1)
                        if not username:
                            username = auth_part.split(":")[0] if ":" in auth_part else auth_part
                        if not password and ":" in auth_part:
                            password = auth_part.split(":", 1)[1]
                    else:
                        server_part = url_part

                    # Parse host:port/database
                    if "/" in server_part:
                        host_port, database = server_part.split("/", 1)
                        database = database.split("?")[0]  # Remove query params
                    else:
                        host_port = server_part
                        database = "postgres"

                    host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")

                    return psycopg2.connect(
                        host=host,
                        port=int(port),
                        user=username or "",
                        password=password or "",
                        database=database,
                        connect_timeout=5
                    )
                else:
                    self.connection_error.emit("Format de connexion PostgreSQL non supporté. Utilisez postgresql://")
                    return None

            else:
                self.connection_error.emit(f"Type non supporté: {self.db_conn.db_type}")
                return None

        except Exception as e:
            error_msg = format_connection_error(e, db_type=self.db_conn.db_type)
            self.connection_error.emit(error_msg)
            return None

    def cancel(self):
        """Request cancellation."""
        self._cancelled = True


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
        self._dialects: Dict[str, DatabaseDialect] = {}  # Database-specific SQL dialects
        self.tab_counter = 1
        self._expand_connected = False
        self._workspace_filter: Optional[str] = None
        self._current_item = None
        self._pending_workers: Dict[str, DatabaseConnectionWorker] = {}  # Track active connection workers
        self._workspace_manager: Optional["WorkspaceManager"] = None

        self._setup_ui()
        self._load_all_connections()

    def set_workspace_manager(self, workspace_manager: "WorkspaceManager"):
        """Set reference to WorkspaceManager for auto-refresh on workspace changes."""
        self._workspace_manager = workspace_manager

    def _get_dialect(self, db_id: str, db_name: Optional[str] = None) -> Optional[DatabaseDialect]:
        """
        Get or create a dialect for a database connection.

        Args:
            db_id: Database connection ID
            db_name: Actual database name (important for SQL Server multi-db)

        Returns:
            DatabaseDialect instance or None if connection not available
        """
        db_conn = self._get_connection_by_id(db_id)
        connection = self.connections.get(db_id)

        if not db_conn or not connection:
            return None

        # For SQL Server, db_name must be the actual database name, not the connection name
        actual_db_name = db_name or db_conn.name

        # Check cache - but update db_name if provided (SQL Server may switch databases)
        if db_id in self._dialects:
            dialect = self._dialects[db_id]
            if db_name:
                dialect.db_name = db_name
            return dialect

        dialect = DialectFactory.create(db_conn.db_type, connection, actual_db_name)
        if dialect:
            self._dialects[db_id] = dialect

        return dialect

    def _load_template_into_tab(
        self,
        db_id: str,
        db_name: Optional[str],
        template: str,
        tab_name: str,
        target_tab_widget: Optional[QTabWidget] = None,
        workspace_id: Optional[str] = None
    ):
        """Load a SQL template into a query tab.

        Args:
            db_id: Database connection ID
            db_name: Database name
            template: SQL template to load
            tab_name: Name for the tab
            target_tab_widget: Optional QTabWidget (default: self.tab_widget)
            workspace_id: Optional workspace ID to auto-link saved queries
        """
        connection = self.connections.get(db_id)

        if target_tab_widget:
            # Create new tab in target widget
            db_conn = self._get_connection_by_id(db_id)
            query_tab = QueryTab(
                parent=self,
                connection=connection,
                db_connection=db_conn,
                tab_name=tab_name,
                database_manager=self,
                target_database=db_name,
                workspace_id=workspace_id
            )
            query_tab.query_saved.connect(self.query_saved.emit)
            index = target_tab_widget.addTab(query_tab, tab_name)
            target_tab_widget.setCurrentIndex(index)
            query_tab.set_query_text(template)
        else:
            # Use existing method for self.tab_widget
            current_tab = self._get_or_create_query_tab(db_id)
            if current_tab:
                current_tab.set_query_text(template)

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_new_tab"), self._new_query_tab, icon="add.png")
        toolbar_builder.add_button(tr("btn_refresh_schema"), self._refresh_schema, icon="refresh.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("menu_new_connection"), self._new_connection)
        toolbar_builder.add_button(tr("db_connections"), self._manage_connections)
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Import", self._import_connections, icon="import.png")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter (left: tree, right: tabs)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(6)  # Larger handle for easier grabbing
        self.main_splitter.setChildrenCollapsible(False)  # Prevent collapsing children

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
        self.main_splitter.addWidget(self.left_panel)

        # Right panel: Query tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.tabBarDoubleClicked.connect(self._rename_query_tab)
        # Set minimum width to prevent it from pushing left panel
        self.tab_widget.setMinimumWidth(200)

        # Add welcome tab
        self._create_welcome_tab()

        self.main_splitter.addWidget(self.tab_widget)

        # Set splitter proportions (left 25%, right 75%) - default values
        self.main_splitter.setSizes([300, 900])

        # Restore saved splitter sizes from preferences
        self._restore_splitter_sizes()

        # Save splitter sizes when changed
        self.main_splitter.splitterMoved.connect(self._save_splitter_sizes)

        # Allow both panels to be resized freely
        self.main_splitter.setStretchFactor(0, 0)  # Left panel: don't auto-stretch
        self.main_splitter.setStretchFactor(1, 1)  # Right panel: takes remaining space

        layout.addWidget(self.main_splitter)

    def _create_welcome_tab(self):
        """Create welcome tab"""
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(tr("db_welcome_title"))
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        welcome_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(tr("db_welcome_subtitle"))
        subtitle.setStyleSheet("font-size: 11pt; color: gray;")
        welcome_layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        info = QLabel(tr("db_welcome_info"))
        info.setStyleSheet("font-size: 10pt; color: gray;")
        welcome_layout.addWidget(info, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tab_widget.addTab(welcome_widget, tr("welcome_tab"))

    def _restore_splitter_sizes(self):
        """Restore splitter sizes from user preferences."""
        try:
            prefs = UserPreferences.instance()
            saved_sizes = prefs.get("db_manager_splitter_sizes")
            if saved_sizes:
                # Parse "300,900" format
                sizes = [int(s) for s in saved_sizes.split(",")]
                if len(sizes) == 2 and all(s > 0 for s in sizes):
                    self.main_splitter.setSizes(sizes)
        except Exception as e:
            logger.debug(f"Could not restore splitter sizes: {e}")

    def _save_splitter_sizes(self):
        """Save splitter sizes to user preferences."""
        try:
            sizes = self.main_splitter.sizes()
            if sizes and len(sizes) == 2:
                prefs = UserPreferences.instance()
                prefs.set("db_manager_splitter_sizes", f"{sizes[0]},{sizes[1]}")
        except Exception as e:
            logger.debug(f"Could not save splitter sizes: {e}")

    def refresh(self):
        """Public refresh method."""
        self._load_all_connections()

    # ==================== ManagerProtocol Implementation ====================

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        """Set workspace filter and refresh the view."""
        self._workspace_filter = workspace_id
        self.refresh()

    def get_workspace_filter(self) -> Optional[str]:
        """Get current workspace filter."""
        return self._workspace_filter

    def get_current_item(self) -> Optional[DatabaseConnection]:
        """Get currently selected database connection."""
        return self._current_item

    def clear_selection(self) -> None:
        """Clear current selection."""
        self._current_item = None
        self.schema_tree.clearSelection()

    # ==================== Data Loading ====================

    def _load_all_connections(self):
        """Load all database connections into tree (lazy - no actual connection)"""
        self.schema_tree.clear()
        self.connections.clear()

        try:
            config_db = get_config_db()

            # Apply workspace filter if set
            if self._workspace_filter:
                db_connections = config_db.get_workspace_databases(self._workspace_filter)
            else:
                db_connections = config_db.get_all_database_connections()

            if not db_connections:
                no_conn_item = QTreeWidgetItem(self.schema_tree)
                no_conn_item.setText(0, tr("no_connections_configured"))
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
        """Start background connection to database and load schema."""
        # Check if already connecting
        if db_conn.id in self._pending_workers:
            return

        # Update tree item to show loading state
        while server_item.childCount() > 0:
            server_item.removeChild(server_item.child(0))

        loading_item = QTreeWidgetItem(server_item)
        loading_item.setText(0, "⏳ Connexion en cours...")
        loading_item.setForeground(0, Qt.GlobalColor.gray)
        loading_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "loading"})

        self._set_status_message(f"Connexion à {db_conn.name}...")

        # Create and start worker
        worker = DatabaseConnectionWorker(db_conn, self)

        # Connect signals with lambdas that capture the context
        worker.connection_success.connect(
            lambda conn, schema, item=server_item, dbc=db_conn:
                self._on_connection_success(item, dbc, conn, schema)
        )
        worker.connection_error.connect(
            lambda error, item=server_item, dbc=db_conn:
                self._on_connection_error(item, dbc, error)
        )
        worker.status_update.connect(self._set_status_message)

        # Track worker
        self._pending_workers[db_conn.id] = worker

        # Start connection in background
        worker.start()

    def connect_database_silent(self, db_conn: DatabaseConnection) -> bool:
        """
        Connect to database silently (for auto-connect on startup).
        Returns True if connection was started, False if failed.
        No interactive dialogs - only uses saved credentials.
        Errors are logged but not shown as popups.
        """
        # Find the server item in tree
        server_item = None
        for i in range(self.schema_tree.topLevelItemCount()):
            item = self.schema_tree.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("config") and data["config"].id == db_conn.id:
                server_item = item
                break

        if not server_item:
            logger.warning(f"No tree item found for database {db_conn.name}")
            return False

        # Check if already connected
        data = server_item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("connected"):
            logger.info(f"Database {db_conn.name} already connected")
            return True

        # Check if already connecting
        if db_conn.id in self._pending_workers:
            return True

        # Update tree item to show loading state
        while server_item.childCount() > 0:
            server_item.removeChild(server_item.child(0))

        loading_item = QTreeWidgetItem(server_item)
        loading_item.setText(0, "⏳ Auto-connexion...")
        loading_item.setForeground(0, Qt.GlobalColor.gray)
        loading_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "loading"})

        # Create and start worker
        worker = DatabaseConnectionWorker(db_conn, self)

        # Connect signals with silent handlers
        worker.connection_success.connect(
            lambda conn, schema, item=server_item, dbc=db_conn:
                self._on_connection_success_silent(item, dbc, conn, schema)
        )
        worker.connection_error.connect(
            lambda error, item=server_item, dbc=db_conn:
                self._on_connection_error_silent(item, dbc, error)
        )
        worker.status_update.connect(lambda msg: logger.debug(f"DB auto-connect: {msg}"))

        # Track worker
        self._pending_workers[db_conn.id] = worker

        # Start connection in background
        worker.start()
        return True

    def _on_connection_success_silent(self, server_item: QTreeWidgetItem, db_conn: DatabaseConnection,
                                       connection, schema):
        """Handle successful connection silently (no popup)."""
        # Remove from pending
        self._pending_workers.pop(db_conn.id, None)

        # Store connection
        self.connections[db_conn.id] = connection

        # Remove loading placeholder
        while server_item.childCount() > 0:
            server_item.removeChild(server_item.child(0))

        # Populate tree with schema
        self._populate_tree_from_schema(server_item, schema, db_conn)

        # Update server node text for SQL Server (show database count)
        if db_conn.db_type == "sqlserver":
            server_item.setText(0, schema.display_name)

        # Mark as connected
        data = server_item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            data["connected"] = True
            server_item.setData(0, Qt.ItemDataRole.UserRole, data)

        # Expand the node
        QTimer.singleShot(0, lambda item=server_item: item.setExpanded(True))

        # Log only, no popup
        logger.info(f"Database auto-connected: {db_conn.name}")
        self._set_status_message(f"✓ DB: {db_conn.name}")

    def _on_connection_error_silent(self, server_item: QTreeWidgetItem, db_conn: DatabaseConnection,
                                     error_message: str):
        """Handle connection error silently (log only, no popup)."""
        # Remove from pending
        self._pending_workers.pop(db_conn.id, None)

        # Update tree item to show error
        while server_item.childCount() > 0:
            server_item.removeChild(server_item.child(0))

        # Add placeholder back for retry
        placeholder = QTreeWidgetItem(server_item)
        placeholder.setText(0, tr("double_click_to_load"))
        placeholder.setForeground(0, Qt.GlobalColor.gray)

        server_item.setExpanded(False)  # Collapse to allow retry

        # Log only, no popup
        logger.warning(f"Database auto-connect failed for {db_conn.name}: {error_message}")

    def _on_connection_success(self, server_item: QTreeWidgetItem, db_conn: DatabaseConnection,
                                connection, schema):
        """Handle successful connection from worker thread."""
        # Remove from pending
        self._pending_workers.pop(db_conn.id, None)

        # Store connection
        self.connections[db_conn.id] = connection

        # Remove loading placeholder
        while server_item.childCount() > 0:
            server_item.removeChild(server_item.child(0))

        # Populate tree with schema
        self._populate_tree_from_schema(server_item, schema, db_conn)

        # Update server node text for SQL Server (show database count)
        if db_conn.db_type == "sqlserver":
            server_item.setText(0, schema.display_name)

        # Mark as connected
        data = server_item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            data["connected"] = True
            server_item.setData(0, Qt.ItemDataRole.UserRole, data)

        # Expand the node
        QTimer.singleShot(0, lambda item=server_item: item.setExpanded(True))
        self._set_status_message(f"Connecté à {db_conn.name}")

    def _on_connection_error(self, server_item: QTreeWidgetItem, db_conn: DatabaseConnection,
                              error_message: str):
        """Handle connection error from worker thread."""
        # Remove from pending
        self._pending_workers.pop(db_conn.id, None)

        # Update tree item to show error
        while server_item.childCount() > 0:
            server_item.removeChild(server_item.child(0))

        # Add placeholder back for retry
        placeholder = QTreeWidgetItem(server_item)
        placeholder.setText(0, tr("double_click_to_load"))
        placeholder.setForeground(0, Qt.GlobalColor.gray)

        server_item.setExpanded(False)  # Collapse to allow retry

        self._set_status_message(tr("status_ready"))

        # Show error dialog
        DialogHelper.error(
            f"Erreur de connexion : {db_conn.name}",
            parent=self,
            details=error_message
        )

    def _create_connection(self, db_conn: DatabaseConnection):
        """
        Create a database connection based on connection type.

        Returns connection object or None if failed.
        """
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

            return sqlite3.connect(db_path, check_same_thread=False)

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

            return connect_sqlserver(conn_str, timeout=5)

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

            if pyodbc is None:
                DialogHelper.warning("pyodbc requis pour les bases Access", parent=self)
                return None
            return pyodbc.connect(conn_str, timeout=5)

        elif db_conn.db_type == "postgresql":
            import psycopg2
            conn_str = db_conn.connection_string

            # Parse postgresql:// URL format
            if conn_str.startswith("postgresql://"):
                url_part = conn_str.replace("postgresql://", "")

                # Get credentials from keyring if available
                username, password = CredentialManager.get_credentials(db_conn.id)

                # Parse URL: [user:pass@]host[:port][/database]
                if "@" in url_part:
                    auth_part, server_part = url_part.split("@", 1)
                    if not username:
                        username = auth_part.split(":")[0] if ":" in auth_part else auth_part
                    if not password and ":" in auth_part:
                        password = auth_part.split(":", 1)[1]
                else:
                    server_part = url_part

                # Parse host:port/database
                if "/" in server_part:
                    host_port, database = server_part.split("/", 1)
                    database = database.split("?")[0]  # Remove query params
                else:
                    host_port = server_part
                    database = "postgres"

                host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")

                return psycopg2.connect(
                    host=host,
                    port=int(port),
                    user=username or "",
                    password=password or "",
                    database=database,
                    connect_timeout=5
                )
            else:
                self._set_status_message(tr("status_ready"))
                DialogHelper.warning("Format de connexion PostgreSQL non supporté. Utilisez postgresql://", parent=self)
                return None

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
        tables_folder_icon = get_icon("tables.png", size=16) or folder_icon
        table_icon = get_icon("table.png", size=16) or self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogListView)
        view_icon = get_icon("view.png", size=16) or self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView)

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
                    metadata["name"] = node.name  # Database name for workspace menu
                    if db_icon:
                        item.setIcon(0, db_icon)

            elif node.node_type == SchemaNodeType.TABLES_FOLDER:
                metadata["type"] = "tables_folder"
                if tables_folder_icon:
                    item.setIcon(0, tables_folder_icon)

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

    def load_specific_database_schema(
        self,
        parent_item: QTreeWidgetItem,
        db_conn: DatabaseConnection,
        database_name: str
    ) -> bool:
        """
        Load schema for a specific database (not the whole server).

        Used by WorkspaceManager when a specific database is attached to a workspace.
        Shows loading indicator for consistent UX with DatabaseManager.

        Args:
            parent_item: Tree item to populate with database schema
            db_conn: Database connection config
            database_name: Name of the specific database to load

        Returns:
            True if successfully loaded, False otherwise
        """
        # Show loading indicator (same as _connect_and_load_schema)
        while parent_item.childCount() > 0:
            parent_item.removeChild(parent_item.child(0))

        loading_item = QTreeWidgetItem(parent_item)
        loading_item.setText(0, "⏳ Connexion en cours...")
        loading_item.setForeground(0, Qt.GlobalColor.gray)
        loading_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "loading"})

        # Expand parent and get the tree widget to force repaint
        parent_item.setExpanded(True)
        tree = parent_item.treeWidget()
        if tree:
            tree.repaint()

        # Force multiple UI updates to ensure loading indicator is visible
        QApplication.processEvents()
        QApplication.processEvents()

        try:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

            # Get or create connection
            connection = self.connections.get(db_conn.id)
            if not connection:
                connection = self._create_connection(db_conn)
                if connection is None:
                    # Remove loading indicator on failure
                    while parent_item.childCount() > 0:
                        parent_item.removeChild(parent_item.child(0))
                    return False
                self.connections[db_conn.id] = connection

            # Use the schema loader to load just the specific database
            loader = SchemaLoaderFactory.create(
                db_conn.db_type, connection, db_conn.id, db_conn.name
            )

            if not loader:
                logger.warning(f"No loader for db_type: {db_conn.db_type}")
                # Remove loading indicator on failure
                while parent_item.childCount() > 0:
                    parent_item.removeChild(parent_item.child(0))
                return False

            # Remove loading indicator before populating
            while parent_item.childCount() > 0:
                parent_item.removeChild(parent_item.child(0))

            # For SQL Server, use _load_database_schema for a specific database
            if hasattr(loader, '_load_database_schema'):
                db_schema = loader._load_database_schema(database_name)
                # Populate with just this database's contents (Tables, Views, etc.)
                self._populate_tree_from_schema(parent_item, db_schema, db_conn)
                return True
            else:
                # For other DB types, load full schema
                schema = loader.load_schema()
                self._populate_tree_from_schema(parent_item, schema, db_conn)
                return True

        except Exception as e:
            logger.error(f"Error loading specific database schema: {e}")
            # Remove loading indicator on failure
            while parent_item.childCount() > 0:
                parent_item.removeChild(parent_item.child(0))
            return False

        finally:
            QApplication.restoreOverrideCursor()

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

            menu.addSeparator()

            # Export connection
            export_action = QAction("📤 Export Connection...", self)
            export_action.triggered.connect(lambda: self._export_connection(data["config"]))
            menu.addAction(export_action)

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
            # SELECT * action
            select_all_action = QAction("SELECT *", self)
            select_all_action.triggered.connect(lambda: self._generate_select_query(data, limit=None))
            menu.addAction(select_all_action)

            # SELECT TOP 100 action
            select_top_action = QAction("SELECT TOP 100 *", self)
            select_top_action.triggered.connect(lambda: self._generate_select_query(data, limit=100))
            menu.addAction(select_top_action)

            # SELECT COLUMNS action
            select_cols_action = QAction("SELECT COLUMNS...", self)
            select_cols_action.triggered.connect(lambda checked, d=data: self._generate_select_columns_query(d))
            menu.addAction(select_cols_action)

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

    def _generate_select_query(self, data: dict, limit: Optional[int] = None, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Generate and execute a SELECT query in a NEW tab named after the table.

        Args:
            data: Dict with table info (name, db_id, db_name)
            limit: Optional row limit
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
        """
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
        elif db_conn.db_type == "postgresql":
            # PostgreSQL: use schema.table format with quotes
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
            # Other databases (Access, etc.)
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
            database_manager=self,
            target_database=db_name,
            workspace_id=workspace_id
        )

        # Connect query_saved signal
        query_tab.query_saved.connect(self.query_saved.emit)

        # Add to target tab widget (or self.tab_widget if not specified)
        tab_widget = target_tab_widget if target_tab_widget else self.tab_widget
        index = tab_widget.addTab(query_tab, tab_name)
        tab_widget.setCurrentIndex(index)

        # Set query and execute
        query_tab.set_query_text(query)
        query_tab._execute_as_query()

        logger.info(f"Created query tab '{tab_name}' for table {table_name}")

    def _generate_select_columns_query(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Generate a formatted SELECT query with all column names in a new tab.

        Args:
            data: Dict with table info (name, db_id, db_name)
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
        """
        table_name = data["name"]
        db_id = data.get("db_id")
        db_name = data.get("db_name")

        db_conn = self._get_connection_by_id(db_id)
        connection = self.connections.get(db_id)

        if not connection or not db_conn:
            DialogHelper.warning("Database not connected. Please expand the database node first.", parent=self)
            return

        try:
            # Get columns based on database type
            if db_conn.db_type == "sqlite":
                cursor = connection.cursor()
                cursor.execute(f"PRAGMA table_info([{table_name}])")
                columns = [row[1] for row in cursor.fetchall()]
                full_table_name = f"[{table_name}]"
            elif db_conn.db_type == "sqlserver" and db_name:
                # Parse schema.table format
                parts = table_name.split(".")
                if len(parts) == 2:
                    schema, tbl_name = parts
                else:
                    schema, tbl_name = "dbo", table_name

                cursor = connection.cursor()
                cursor.execute(f"""
                    SELECT c.name
                    FROM [{db_name}].sys.columns c
                    INNER JOIN [{db_name}].sys.tables t ON c.object_id = t.object_id
                    INNER JOIN [{db_name}].sys.schemas s ON t.schema_id = s.schema_id
                    WHERE t.name = '{tbl_name}' AND s.name = '{schema}'
                    ORDER BY c.column_id
                """)
                columns = [row[0] for row in cursor.fetchall()]

                # If no columns found, try as a view
                if not columns:
                    cursor.execute(f"""
                        SELECT c.name
                        FROM [{db_name}].sys.columns c
                        INNER JOIN [{db_name}].sys.views v ON c.object_id = v.object_id
                        INNER JOIN [{db_name}].sys.schemas s ON v.schema_id = s.schema_id
                        WHERE v.name = '{tbl_name}' AND s.name = '{schema}'
                        ORDER BY c.column_id
                    """)
                    columns = [row[0] for row in cursor.fetchall()]

                full_table_name = f"[{db_name}].[{schema}].[{tbl_name}]"
            elif db_conn.db_type == "postgresql":
                # PostgreSQL: use information_schema
                parts = table_name.split(".")
                if len(parts) == 2:
                    schema, tbl_name = parts
                else:
                    schema, tbl_name = "public", table_name

                cursor = connection.cursor()
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema, tbl_name))
                columns = [row[0] for row in cursor.fetchall()]
                full_table_name = f'"{schema}"."{tbl_name}"'
            else:
                # Fallback: get columns from a sample query
                cursor = connection.cursor()
                cursor.execute(f"SELECT TOP 1 * FROM [{table_name}]")
                columns = [desc[0] for desc in cursor.description]
                full_table_name = f"[{table_name}]"

            if not columns:
                DialogHelper.warning("No columns found for this table.", parent=self)
                return

            # Format the query
            query = self._format_select_columns_query(columns, full_table_name)

            # Create a new query tab
            simple_name = table_name.split('.')[-1].strip('[]')
            tab_name = f"{simple_name} (columns)"

            query_tab = QueryTab(
                parent=self,
                connection=connection,
                db_connection=db_conn,
                tab_name=tab_name,
                database_manager=self,
                target_database=db_name,
                workspace_id=workspace_id
            )

            query_tab.query_saved.connect(self.query_saved.emit)

            # Add to target tab widget (or self.tab_widget if not specified)
            tab_widget = target_tab_widget if target_tab_widget else self.tab_widget
            index = tab_widget.addTab(query_tab, tab_name)
            tab_widget.setCurrentIndex(index)

            # Set query but don't execute (user may want to modify it first)
            query_tab.set_query_text(query)

            logger.info(f"Created SELECT COLUMNS query for {table_name}")

        except Exception as e:
            logger.error(f"Error generating SELECT COLUMNS query: {e}")
            DialogHelper.error(f"Error generating query: {e}", parent=self)

    def _format_select_columns_query(self, columns: list, table_name: str) -> str:
        """
        Format a SELECT query with columns in sophisticated/ultimate style.

        Style:
        SELECT
              [Column1]
            , [Column2]
            ...
        FROM [Table]
        WHERE 1 = 1
            -- AND [Column1] = ''
        ORDER BY
              [Column1] ASC
        ;
        """
        lines = ["SELECT"]

        # Format columns with leading comma style
        for i, col in enumerate(columns):
            if i == 0:
                lines.append(f"      [{col}]")
            else:
                lines.append(f"    , [{col}]")

        lines.append(f"FROM {table_name}")
        lines.append("WHERE 1 = 1")

        # Add commented WHERE conditions for first 5 columns
        for col in columns[:5]:
            lines.append(f"    -- AND [{col}] = ''")

        if len(columns) > 5:
            lines.append(f"    -- ... ({len(columns) - 5} more columns)")

        lines.append("ORDER BY")
        lines.append(f"      [{columns[0]}] ASC")

        if len(columns) > 1:
            lines.append(f"    --, [{columns[1]}] DESC")

        lines.append(";")

        return "\n".join(lines)

    def _load_view_code(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Load view code into query editor as ALTER VIEW.

        Args:
            data: Dict with view info (name, db_id, db_name)
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
        """
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        view_name = data.get("name")  # schema.viewname

        if not all([db_id, db_name, view_name]):
            return

        # Get dialect for database-specific operations
        dialect = self._get_dialect(db_id, db_name)
        if not dialect:
            DialogHelper.warning("Database not connected", parent=self)
            return

        # Parse schema and view name
        parts = view_name.split(".")
        if len(parts) == 2:
            schema, name = parts
        else:
            schema = dialect.default_schema or "dbo"
            name = view_name

        try:
            # Use dialect to get view definition
            code = dialect.get_alter_view_statement(name, schema)

            if code:
                connection = self.connections.get(db_id)

                # Determine target tab widget
                tab_widget = target_tab_widget if target_tab_widget else self.tab_widget

                # Get or create a query tab
                if target_tab_widget:
                    # Create new tab in target widget
                    db_conn = self._get_connection_by_id(db_id)
                    tab_name = f"{name} (view)"
                    query_tab = QueryTab(
                        parent=self,
                        connection=connection,
                        db_connection=db_conn,
                        tab_name=tab_name,
                        database_manager=self,
                        target_database=db_name,
                        workspace_id=workspace_id
                    )
                    query_tab.query_saved.connect(self.query_saved.emit)
                    index = tab_widget.addTab(query_tab, tab_name)
                    tab_widget.setCurrentIndex(index)
                    query_tab.set_query_text(code)
                    logger.info(f"Loaded view code: {schema}.{name}")
                else:
                    # Use existing method for self.tab_widget
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

    def _load_routine_code(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Load stored procedure or function code into query editor.

        Args:
            data: Dict with routine info
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
        """
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        routine_type = data.get("type")  # "procedure" or "function"

        if routine_type == "procedure":
            routine_name = data.get("proc_name")
        else:
            routine_name = data.get("func_name")

        if not all([db_id, schema, routine_name]):
            return

        # Get dialect for database-specific operations
        dialect = self._get_dialect(db_id, db_name)
        if not dialect:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            # Use dialect to get routine definition
            code = dialect.get_routine_definition(routine_name, schema, routine_type)

            if code:
                connection = self.connections.get(db_id)

                if target_tab_widget:
                    # Create new tab in target widget
                    db_conn = self._get_connection_by_id(db_id)
                    tab_name = f"{routine_name} ({routine_type})"
                    query_tab = QueryTab(
                        parent=self,
                        connection=connection,
                        db_connection=db_conn,
                        tab_name=tab_name,
                        database_manager=self,
                        target_database=db_name,
                        workspace_id=workspace_id
                    )
                    query_tab.query_saved.connect(self.query_saved.emit)
                    index = target_tab_widget.addTab(query_tab, tab_name)
                    target_tab_widget.setCurrentIndex(index)
                    query_tab.set_query_text(code)
                    logger.info(f"Loaded {routine_type} code: {schema}.{routine_name}")
                else:
                    # Use existing method for self.tab_widget
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

    def _generate_exec_template(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Generate EXEC/CALL template for stored procedure.

        Args:
            data: Dict with procedure info
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
            workspace_id: Optional workspace ID to auto-link saved queries
        """
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        proc_name = data.get("proc_name")

        if not all([db_id, schema, proc_name]):
            return

        # Get dialect for database-specific operations
        dialect = self._get_dialect(db_id, db_name)
        if not dialect:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            # Use dialect to generate template
            template = dialect.generate_exec_template(proc_name, schema, "procedure")

            # Load into editor
            self._load_template_into_tab(db_id, db_name, template, f"{proc_name} (exec)", target_tab_widget, workspace_id=workspace_id)

        except Exception as e:
            logger.error(f"Error generating EXEC template: {e}")
            # Fallback to simple template
            template = dialect.generate_exec_template(proc_name, schema, "procedure")
            self._load_template_into_tab(db_id, db_name, template, f"{proc_name} (exec)", target_tab_widget, workspace_id=workspace_id)

    def _generate_select_function(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Generate SELECT template for function.

        Args:
            data: Dict with function info
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
            workspace_id: Optional workspace ID to auto-link saved queries
        """
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        func_name = data.get("func_name")
        func_type = data.get("func_type", "")

        if not all([db_id, schema, func_name]):
            return

        # Get dialect for database-specific operations
        dialect = self._get_dialect(db_id, db_name)
        if not dialect:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            # Use dialect to generate template
            template = dialect.generate_select_function_template(func_name, schema, func_type)
            self._load_template_into_tab(db_id, db_name, template, f"{func_name} (select)", target_tab_widget, workspace_id=workspace_id)

        except Exception as e:
            logger.warning(f"Could not generate function template: {e}")
            # Fallback
            template = dialect.generate_select_function_template(func_name, schema, func_type)
            self._load_template_into_tab(db_id, db_name, template, f"{func_name} (select)", target_tab_widget, workspace_id=workspace_id)

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
            elif db_conn.db_type == "postgresql":
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
        except (OSError, ValueError) as e:
            logger.debug(f"Could not get connection {db_id}: {e}")
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

            # Clean up dialect
            if db_conn.id in self._dialects:
                del self._dialects[db_conn.id]

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

            # Refresh workspace if manager is set
            if self._workspace_manager:
                self._workspace_manager.refresh_workspace(workspace_id)

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

                # Refresh workspace if manager is set
                if self._workspace_manager:
                    self._workspace_manager.refresh_workspace(ws.id)
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
                    match = re.search(r'Database=([^;]+)', conn_str)
                    db_path = match.group(1) if match else conn_str
                else:
                    db_path = conn_str

                connection = sqlite3.connect(db_path, check_same_thread=False)
                self.connections[db_id] = connection

            elif db_conn.db_type == "sqlserver":
                conn_str = db_conn.connection_string

                if "trusted_connection=yes" not in conn_str.lower():
                    username, password = CredentialManager.get_credentials(db_id)
                    if username and password:
                        if "uid=" not in conn_str.lower() and "user id=" not in conn_str.lower():
                            if not conn_str.endswith(";"):
                                conn_str += ";"
                            conn_str += f"UID={username};PWD={password};"

                connection = connect_sqlserver(conn_str, timeout=5)
                self.connections[db_id] = connection

            elif db_conn.db_type in ("postgresql", "postgres"):
                import psycopg2
                conn_str = db_conn.connection_string

                if conn_str.startswith("postgresql://"):
                    url_part = conn_str.replace("postgresql://", "")

                    username, password = CredentialManager.get_credentials(db_id)

                    if "@" in url_part:
                        auth_part, server_part = url_part.split("@", 1)
                        if not username:
                            username = auth_part.split(":")[0] if ":" in auth_part else auth_part
                        if not password and ":" in auth_part:
                            password = auth_part.split(":", 1)[1]
                    else:
                        server_part = url_part

                    if "/" in server_part:
                        host_port, database = server_part.split("/", 1)
                        database = database.split("?")[0]
                    else:
                        host_port = server_part
                        database = "postgres"

                    host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")

                    connection = psycopg2.connect(
                        host=host,
                        port=int(port),
                        user=username or "",
                        password=password or "",
                        database=database,
                        connect_timeout=5
                    )
                    self.connections[db_id] = connection
                else:
                    return None

            else:
                return None

            # Update all QueryTabs using this connection
            self._update_query_tabs_connection(db_id, connection)

            logger.info(f"Reconnected to database: {db_conn.name}")
            return connection

        except Exception as e:
            logger.error(f"Failed to reconnect to {db_conn.name}: {e}")
            return None

    def execute_saved_query(self, saved_query, target_tab_widget=None, workspace_id=None):
        """
        Execute a saved query in a new QueryTab.

        Args:
            saved_query: SavedQuery object to execute
            target_tab_widget: Optional QTabWidget to add the tab to (default: self.tab_widget)
            workspace_id: Optional workspace ID for auto-linking new queries
        """
        db_id = saved_query.target_database_id
        if not db_id:
            DialogHelper.warning(
                "No target database specified for this query.",
                parent=self
            )
            return

        # Get connection info
        connection = self.connections.get(db_id)
        db_conn = self._get_connection_by_id(db_id)

        if not db_conn:
            DialogHelper.warning(
                "Target database connection not found.",
                parent=self
            )
            return

        if not connection:
            # Try to reconnect
            try:
                connection = self.reconnect_database(db_id)
                if not connection:
                    DialogHelper.error(
                        f"Failed to connect to {db_conn.name}.",
                        parent=self
                    )
                    return
            except Exception as e:
                DialogHelper.error(f"Connection error: {e}", parent=self)
                return

        # Get target database name
        target_db = getattr(saved_query, 'target_database_name', None) or None
        tab_name = saved_query.name

        query_tab = QueryTab(
            parent=self,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name,
            database_manager=self,
            target_database=target_db,
            workspace_id=workspace_id,
            saved_query=saved_query
        )

        # Connect query_saved signal
        query_tab.query_saved.connect(self.query_saved.emit)

        # Add to target tab widget (or self.tab_widget if not specified)
        tab_widget = target_tab_widget if target_tab_widget else self.tab_widget
        index = tab_widget.addTab(query_tab, tab_name)
        tab_widget.setCurrentIndex(index)

        # Set query text and execute
        query_tab.set_query_text(saved_query.query_text or "")
        try:
            query_tab._execute_as_query()
        except Exception as e:
            logger.error(f"Error executing saved query '{saved_query.name}': {e}")
            DialogHelper.error(f"Error executing query: {e}", parent=self)

        logger.info(f"Executed saved query: {saved_query.name}")

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
        # Cancel all pending connection workers first
        for worker_id, worker in list(self._pending_workers.items()):
            try:
                worker.cancel()
                # Disconnect signals to prevent callbacks after cleanup
                worker.connection_success.disconnect()
                worker.connection_error.disconnect()
                worker.status_update.disconnect()
                worker.quit()
                worker.wait(1000)  # Wait max 1 second
            except Exception:
                pass  # Ignore errors during shutdown
        self._pending_workers.clear()

        # Cleanup all query tabs (stop background threads)
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

    def _export_connection(self, db_conn: DatabaseConnection):
        """Export a single connection to JSON file."""
        try:
            # Ask user for file location
            default_filename = f"{db_conn.name.replace(' ', '_')}_connection.json"
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Export Connection",
                default_filename,
                "JSON Files (*.json);;All Files (*)"
            )

            if not filepath:
                return  # User cancelled

            # Export connection
            export_data = export_connections_to_json(
                connection_ids=[db_conn.id],
                include_credentials=False  # Security: don't export passwords
            )

            # Save to file
            save_export_to_file(export_data, filepath)

            # Show success message
            summary = get_export_summary(export_data)
            DialogHelper.info(
                f"Export successful!\n\n{summary}\n\nFile: {filepath}",
                parent=self
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            DialogHelper.error(f"Export failed: {str(e)}", parent=self)

    def _export_all_connections(self):
        """Export all connections to JSON file."""
        try:
            # Ask user for file location
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Export All Connections",
                "connections_export.json",
                "JSON Files (*.json);;All Files (*)"
            )

            if not filepath:
                return  # User cancelled

            # Export all connections
            export_data = export_connections_to_json(
                connection_ids=None,  # All connections
                include_credentials=False  # Security: don't export passwords
            )

            # Save to file
            save_export_to_file(export_data, filepath)

            # Show success message
            summary = get_export_summary(export_data)
            DialogHelper.info(
                f"Export successful!\n\n{summary}\n\nFile: {filepath}",
                parent=self
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            DialogHelper.error(f"Export failed: {str(e)}", parent=self)

    def _import_connections(self):
        """Import connections from JSON file."""
        try:
            # Ask user for file location
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Import Connections",
                "",
                "JSON Files (*.json);;All Files (*)"
            )

            if not filepath:
                return  # User cancelled

            # Load import data
            import_data = load_import_from_file(filepath)

            # Check export type - must be connections or workspace (we extract connections)
            export_type = import_data.get("export_type", "")
            if export_type not in ["connections", "workspace"]:
                DialogHelper.error(
                    f"Format de fichier non supporté: {export_type}",
                    parent=self
                )
                return

            # Import connections
            results = import_connections_from_json(import_data)

            # Refresh schema tree to show new connections
            self._refresh_schema()

            # Show results
            created = results.get("created", [])
            existing = results.get("existing", [])
            errors = results.get("errors", [])

            summary_lines = ["Import terminé!"]
            if created:
                summary_lines.append(f"\nConnexions créées ({len(created)}):")
                for name in created[:5]:
                    summary_lines.append(f"  - {name}")
                if len(created) > 5:
                    summary_lines.append(f"  ... et {len(created) - 5} autres")

            if existing:
                summary_lines.append(f"\nConnexions existantes ({len(existing)}):")
                for name in existing[:5]:
                    summary_lines.append(f"  - {name}")
                if len(existing) > 5:
                    summary_lines.append(f"  ... et {len(existing) - 5} autres")

            if errors:
                summary_lines.append(f"\nErreurs ({len(errors)}):")
                for err in errors[:3]:
                    summary_lines.append(f"  - {err}")
                if len(errors) > 3:
                    summary_lines.append(f"  ... et {len(errors) - 3} autres")

            DialogHelper.info("\n".join(summary_lines), parent=self)

        except ValueError as e:
            DialogHelper.error(f"Erreur de format: {str(e)}", parent=self)
        except Exception as e:
            logger.error(f"Import failed: {e}")
            DialogHelper.error(f"Import échoué: {str(e)}", parent=self)
