"""
CRUD Mixin - Create, Read, Update, Delete operations for database connections.
"""

from __future__ import annotations

import logging
import sqlite3
import traceback
from typing import TYPE_CHECKING

from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....database.config_db import get_config_db
from ....utils.credential_manager import CredentialManager

if TYPE_CHECKING:
    from ....database.config_db import DatabaseConnection

logger = logging.getLogger(__name__)


class DatabaseCrudMixin:
    """Mixin providing CRUD operations for database connections."""

    def _refresh_schema(self):
        """Refresh database schema tree"""
        self._load_all_connections()

    def _new_connection(self):
        """Open new connection dialog using ConnectionSelectorDialog"""
        from ...dialogs.connection_dialogs import ConnectionSelectorDialog

        dialog = ConnectionSelectorDialog(parent=self)
        dialog.connection_created.connect(self._refresh_schema)
        dialog.exec()

    def _edit_connection(self, db_conn: DatabaseConnection):
        """Edit database connection name, description and color"""
        from ...widgets.edit_dialogs import EditDatabaseConnectionDialog

        dialog = EditDatabaseConnectionDialog(
            parent=self,
            name=db_conn.name,
            description=db_conn.description or "",
            color=db_conn.color
        )

        if dialog.exec():
            name, description, color = dialog.get_values()

            if not name:
                DialogHelper.warning("Name cannot be empty", parent=self)
                return

            try:
                # Update connection
                db_conn.name = name
                db_conn.description = description
                db_conn.color = color

                # Save to database
                config_db = get_config_db()
                config_db.save_database_connection(db_conn)

                # Refresh tree and tab icons
                self._refresh_schema()
                self._update_tab_icons_for_connection(db_conn.id, color)

                DialogHelper.info("Connection updated successfully", parent=self)

            except Exception as e:
                logger.error(f"Error updating connection: {e}")
                DialogHelper.error("Error updating connection", parent=self, details=str(e))

    def _change_connection_color(self, db_conn: DatabaseConnection):
        """Change connection color via color picker dialog"""
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor

        initial = QColor(db_conn.color) if db_conn.color else QColor("#3498db")
        color = QColorDialog.getColor(initial, self, tr("conn_color_picker_title"))

        if color.isValid():
            hex_color = color.name()
            db_conn.color = hex_color

            try:
                config_db = get_config_db()
                config_db.save_database_connection(db_conn)

                # Refresh tree and tab icons
                self._refresh_schema()
                self._update_tab_icons_for_connection(db_conn.id, hex_color)

            except Exception as e:
                logger.error(f"Error updating connection color: {e}")
                DialogHelper.error("Error updating color", parent=self, details=str(e))

    def _edit_full_connection(self, db_conn: DatabaseConnection):
        """Edit full database connection including credentials"""
        from ...dialogs.connection_dialog_factory import ConnectionDialogFactory

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

        except sqlite3.Error as e:
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
                self.connections_changed.emit()

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

        except sqlite3.Error as e:
            logger.error(f"Error deleting connection: {e}")
            DialogHelper.error("Error deleting connection", parent=self, details=str(e))
