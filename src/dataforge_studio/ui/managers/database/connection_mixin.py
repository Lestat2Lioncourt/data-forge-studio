"""
Connection Mixin - Connection lifecycle management for DatabaseManager.
"""

from __future__ import annotations

import re
import logging
import threading
from typing import Optional, Union, TYPE_CHECKING
from pathlib import Path

try:
    import pyodbc
except ImportError:
    pyodbc = None
import sqlite3

from PySide6.QtWidgets import QTreeWidgetItem, QApplication
from PySide6.QtCore import Qt, QTimer

from .connection_worker import DatabaseConnectionWorker
from ..query_tab import QueryTab
from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....database.config_db import get_config_db, DatabaseConnection
from ....database.schema_loaders import SchemaLoaderFactory
from ....utils.image_loader import get_database_icon_with_dot, get_auto_color
from ....utils.credential_manager import CredentialManager
from ....utils.connection_helpers import parse_postgresql_url
from ....utils.connection_error_handler import format_connection_error
from ....constants import CONNECTION_TIMEOUT_S
from ....database.sqlserver_connection import connect_sqlserver

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DatabaseConnectionMixin:
    """Mixin providing connection lifecycle management."""

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

            for i, db_conn in enumerate(db_connections):
                self._add_connection_node(db_conn, index=i)

        except sqlite3.Error as e:
            logger.error(f"Error loading connections: {e}")

    def _ensure_connection_color(self, db_conn: DatabaseConnection, index: int = 0):
        """Auto-assign a color to the connection if it doesn't have one, and persist it."""
        if not db_conn.color:
            db_conn.color = get_auto_color(index)
            try:
                config_db = get_config_db()
                config_db.save_database_connection(db_conn)
            except sqlite3.Error as e:
                logger.warning(f"Could not persist auto-color for {db_conn.name}: {e}")

    def _add_connection_node(self, db_conn: DatabaseConnection, index: int = 0):
        """Add a connection node to tree (lazy - no actual connection yet)"""
        # Ensure connection has a color
        self._ensure_connection_color(db_conn, index)

        # Create server node with DB type icon + color dot
        server_item = QTreeWidgetItem(self.schema_tree)

        # Set icon with color dot based on database type
        db_icon = get_database_icon_with_dot(db_conn.db_type, db_conn.color)
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
        placeholder.setText(0, tr("db_double_click_to_load"))
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
        loading_item.setText(0, tr("db_connecting_in_progress"))
        loading_item.setForeground(0, Qt.GlobalColor.gray)
        loading_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "loading"})

        self._set_status_message(tr("db_connecting_to", name=db_conn.name))

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
        loading_item.setText(0, "\u23f3 Auto-connexion...")
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
        self.connections_changed.emit()

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
        self._set_status_message(f"\u2713 DB: {db_conn.name}")

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
        self.connections_changed.emit()

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
        self._set_status_message(tr("db_connected_to", name=db_conn.name))

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
            tr("db_connection_error", name=db_conn.name),
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
                DialogHelper.warning(tr("db_file_not_found", path=db_path), parent=self)
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

            return connect_sqlserver(conn_str, timeout=CONNECTION_TIMEOUT_S)

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
                    tr("db_access_file_missing", path=db_path or "?"),
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
                DialogHelper.warning(tr("db_pyodbc_required"), parent=self)
                return None
            return pyodbc.connect(conn_str, timeout=CONNECTION_TIMEOUT_S)

        elif db_conn.db_type == "postgresql":
            import psycopg2
            pg_kwargs = parse_postgresql_url(db_conn.connection_string, db_conn.id)
            if pg_kwargs:
                return psycopg2.connect(**pg_kwargs)
            else:
                self._set_status_message(tr("status_ready"))
                DialogHelper.warning(tr("db_pg_format_unsupported"), parent=self)
                return None

        else:
            # Unsupported database type
            return None

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

                connection = connect_sqlserver(conn_str, timeout=CONNECTION_TIMEOUT_S)
                self.connections[db_id] = connection

            elif db_conn.db_type in ("postgresql", "postgres"):
                import psycopg2
                pg_kwargs = parse_postgresql_url(db_conn.connection_string, db_id)
                if pg_kwargs:
                    connection = psycopg2.connect(**pg_kwargs)
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
