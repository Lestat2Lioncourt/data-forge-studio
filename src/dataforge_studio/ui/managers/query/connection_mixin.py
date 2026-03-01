"""
Connection Mixin - Connection management for QueryTab.
"""
from __future__ import annotations

import logging
import sqlite3

from PySide6.QtWidgets import QApplication

from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr

logger = logging.getLogger(__name__)


class QueryConnectionMixin:
    """Connection management methods for QueryTab."""

    def _load_connections(self):
        """Load available connections into the connection dropdown.

        Shows all configured connections (not just active ones).
        If workspace_id is set, only shows connections linked to that workspace.
        Inactive connections are shown with a dimmed prefix so the user can connect on demand.
        """
        self.conn_combo.blockSignals(True)
        self.conn_combo.clear()

        if not self._database_manager:
            self.conn_combo.addItem("(No manager)", None)
            self.conn_combo.blockSignals(False)
            return

        from ....database.config_db import get_config_db
        config_db = get_config_db()

        # Get connections scoped to workspace or all
        if self._workspace_id:
            all_db_conns = config_db.get_workspace_databases(self._workspace_id)
        else:
            all_db_conns = config_db.get_all_database_connections()

        active_ids = set(self._database_manager.connections.keys())

        for db_conn in all_db_conns:
            is_active = db_conn.id in active_ids
            label = db_conn.name if is_active else f"○ {db_conn.name}"
            self.conn_combo.addItem(label, db_conn.id)

        # Select current connection
        if self.db_connection:
            for i in range(self.conn_combo.count()):
                if self.conn_combo.itemData(i) == self.db_connection.id:
                    self.conn_combo.setCurrentIndex(i)
                    break

        self.conn_combo.blockSignals(False)

    def _on_connection_changed(self, index: int):
        """Handle connection selector change."""
        if index < 0:
            return

        db_id = self.conn_combo.itemData(index)
        if not db_id or not self._database_manager:
            return

        # Same connection? Skip
        if self.db_connection and self.db_connection.id == db_id:
            return

        new_db_conn = self._database_manager._get_connection_by_id(db_id)
        if not new_db_conn:
            return

        # Get active connection, or auto-connect if inactive
        new_conn = self._database_manager.connections.get(db_id)
        if not new_conn:
            try:
                self._append_message(f"-- Connecting to {new_db_conn.name}...")
                QApplication.processEvents()
                new_conn = self._database_manager._create_connection(new_db_conn)
                if new_conn:
                    self._database_manager.connections[db_id] = new_conn
                    self._database_manager.connections_changed.emit()
                    self._append_message(f"-- Connected to {new_db_conn.name}")
                else:
                    self._append_message(f"-- Failed to connect to {new_db_conn.name}", is_error=True)
                    # Revert selection
                    if self.db_connection:
                        self.conn_combo.blockSignals(True)
                        for i in range(self.conn_combo.count()):
                            if self.conn_combo.itemData(i) == self.db_connection.id:
                                self.conn_combo.setCurrentIndex(i)
                                break
                        self.conn_combo.blockSignals(False)
                    return
            except Exception as e:
                self._append_message(f"-- Connection error: {e}", is_error=True)
                logger.error(f"Auto-connect failed for {new_db_conn.name}: {e}")
                return

        # Switch connection
        self.connection = new_conn
        self.db_connection = new_db_conn
        self.is_sqlite = isinstance(new_conn, sqlite3.Connection)
        self.db_type = new_db_conn.db_type if hasattr(new_db_conn, 'db_type') else ("sqlite" if self.is_sqlite else "sqlserver")
        self._target_database = None

        # Clear schema cache and reload databases
        self.schema_cache.invalidate()
        self._load_databases()

        logger.info(f"QueryTab switched to connection: {new_db_conn.name}")

    def _load_databases(self):
        """Load available databases into the dropdown"""
        self.db_combo.blockSignals(True)
        self.db_combo.clear()

        if not self.connection:
            self.db_combo.addItem("(No connection)")
            self.db_combo.blockSignals(False)
            return

        try:
            if self.db_type == "sqlite":
                # SQLite has only one database
                db_name = self.db_connection.name if self.db_connection else "SQLite"
                self.db_combo.addItem(db_name)
                self.current_database = db_name

            elif self.db_type == "sqlserver":
                cursor = self.connection.cursor()

                # Get all databases (user databases, not system)
                cursor.execute("""
                    SELECT name FROM sys.databases
                    WHERE database_id > 4
                    ORDER BY name
                """)
                databases = [row[0] for row in cursor.fetchall()]

                # Add databases to combo
                for db in databases:
                    self.db_combo.addItem(db)

                # Determine which database to select:
                # 1. Use target_database if specified (from right-click on table)
                # 2. Otherwise use current database from connection
                target_db = self._target_database
                if not target_db:
                    cursor.execute("SELECT DB_NAME()")
                    target_db = cursor.fetchone()[0]

                # Select target database and switch context
                if target_db in databases:
                    self.db_combo.setCurrentText(target_db)
                    self.current_database = target_db
                    # Switch database context
                    try:
                        safe_target = target_db.replace("]", "]]")
                        cursor.execute(f"USE [{safe_target}]")
                    except Exception as e:
                        logger.warning(f"Could not switch to database {target_db}: {e}")

            elif self.db_type == "postgresql":
                # PostgreSQL: show current database (can't switch without reconnecting)
                cursor = self.connection.cursor()
                cursor.execute("SELECT current_database()")
                current_db = cursor.fetchone()[0]
                self.db_combo.addItem(current_db)
                self.current_database = current_db

            else:
                # Other database types - just show connection name
                db_name = self.db_connection.name if self.db_connection else "Database"
                self.db_combo.addItem(db_name)
                self.current_database = db_name

        except Exception as e:
            logger.error(f"Error loading databases: {e}")
            self.db_combo.addItem("(Error loading)")

        self.db_combo.blockSignals(False)

    def _on_database_changed(self, db_name: str):
        """Handle database selection change"""
        if not db_name or db_name.startswith("("):
            return

        if not self.connection or self.db_type != "sqlserver":
            return

        try:
            # Change database context using USE statement
            cursor = self.connection.cursor()
            safe_db = db_name.replace("]", "]]")
            cursor.execute(f"USE [{safe_db}]")
            self.current_database = db_name

            # Clear schema cache for new database
            self.schema_cache.invalidate()

            logger.info(f"Database context changed to: {db_name}")

        except Exception as e:
            logger.error(f"Error changing database: {e}")
            DialogHelper.error(f"Cannot switch to database '{db_name}'", parent=self, details=str(e))
            # Revert to previous selection
            if self.current_database:
                self.db_combo.blockSignals(True)
                self.db_combo.setCurrentText(self.current_database)
                self.db_combo.blockSignals(False)

    # =========================================================================
    # Connection error handling
    # =========================================================================

    def _is_connection_error(self, error: Exception) -> bool:
        """
        Check if an exception is a connection-related error.

        Args:
            error: The exception to check

        Returns:
            True if this is a connection error (VPN dropped, server unreachable, etc.)
        """
        error_str = str(error).lower()

        # Common connection error indicators
        connection_indicators = [
            "communication link failure",
            "tcp provider",
            "connection failure",
            "network-related",
            "connection was forcibly closed",
            "connection timed out",
            "server has gone away",
            "lost connection",
            "unable to connect",
            "connection refused",
            "no connection",
            "08001",  # SQL Server connection error
            "08s01",  # Communication link failure
            "hyt00",  # Timeout expired
            "hyt01",  # Connection timeout
        ]

        return any(indicator in error_str for indicator in connection_indicators)

    def _handle_connection_error(self, error: Exception):
        """
        Handle a connection error by offering reconnection option.

        Args:
            error: The connection error
        """
        from PySide6.QtWidgets import QMessageBox

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(tr("connection_error"))
        msg.setText(tr("connection_lost"))
        msg.setInformativeText(
            tr("reconnecting_vpn_hint") + "\n\n" + tr("would_you_reconnect")
        )
        msg.setDetailedText(str(error))

        # Add custom buttons
        reconnect_btn = msg.addButton(tr("btn_reconnect"), QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)

        msg.exec()

        if msg.clickedButton() == reconnect_btn:
            self._attempt_reconnection()

    def _attempt_reconnection(self):
        """Attempt to reconnect to the database and re-execute the query."""
        if not self.db_connection:
            DialogHelper.error(tr("no_db_config"), parent=self)
            return

        # Find the DatabaseManager parent
        database_manager = self._find_database_manager()
        if not database_manager:
            DialogHelper.error(tr("cannot_find_db_manager"), parent=self)
            return

        # Show reconnecting status
        self.result_info_label.setText(tr("reconnecting"))
        self.result_info_label.setStyleSheet("color: orange;")
        QApplication.processEvents()

        try:
            # Attempt reconnection via DatabaseManager
            new_connection = database_manager.reconnect_database(self.db_connection.id)

            if new_connection:
                # Update our connection reference
                self.connection = new_connection

                self.result_info_label.setText(tr("reconnected"))
                self.result_info_label.setStyleSheet("color: green;")

                # Reload databases dropdown
                self._load_databases()

                # Ask if user wants to re-execute the query
                from PySide6.QtWidgets import QMessageBox
                result = QMessageBox.question(
                    self,
                    tr("reexecute_query_title"),
                    tr("reexecute_query_question"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if result == QMessageBox.StandardButton.Yes:
                    self._execute_as_query()
            else:
                self.result_info_label.setText(tr("reconnect_failed"))
                self.result_info_label.setStyleSheet("color: red;")
                DialogHelper.error(
                    tr("reconnect_failed") + "\n\n" + tr("check_vpn_connection"),
                    parent=self
                )

        except Exception as e:
            self.result_info_label.setText(tr("reconnection_error"))
            self.result_info_label.setStyleSheet("color: red;")
            DialogHelper.error(tr("reconnect_failed"), parent=self, details=str(e))
            logger.error(f"Reconnection error: {e}")

    def _find_database_manager(self):
        """Find the parent DatabaseManager widget."""
        # Use stored reference if available
        if self._database_manager is not None:
            return self._database_manager

        # Fallback: traverse parent hierarchy
        widget = self.parent()
        while widget is not None:
            if widget.__class__.__name__ == "DatabaseManager":
                return widget
            widget = widget.parent()
        return None
