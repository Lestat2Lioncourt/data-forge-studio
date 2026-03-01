"""
Workspace Mixin - Workspace integration for database connections.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QMenu, QInputDialog
from PySide6.QtGui import QAction

from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....database.config_db import get_config_db, Workspace

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DatabaseWorkspaceMixin:
    """Mixin providing workspace management for database connections."""

    def _build_workspace_submenu(self, db_id: str, database_name: Optional[str] = None) -> QMenu:
        """
        Build a submenu for adding/removing a database to/from workspaces.

        Args:
            db_id: Database connection (server) ID
            database_name: Specific database name (None = server/all databases, str = specific database)

        Returns:
            QMenu with workspace options
        """
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
