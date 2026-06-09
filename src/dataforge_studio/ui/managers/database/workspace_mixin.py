"""
Workspace Mixin - Workspace integration for database connections.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QMenu, QInputDialog, QApplication
from PySide6.QtGui import QAction, QCursor
from PySide6.QtCore import Qt

from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....database.config_db import get_config_db, Workspace
from ....utils.db_capabilities import is_multi_database_server

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

        # Multi-database server (no specific database): offer to link ALL its
        # databases (snapshot, one link per database) instead of a single
        # ambiguous server-level link. Unlinking is then done per database.
        db_conn = self._get_connection_by_id(db_id)
        if not database_name and db_conn and is_multi_database_server(db_conn.db_type):
            for ws in workspaces:
                action = QAction(tr("ws_link_all_databases", workspace=ws.name), self)
                action.triggered.connect(
                    lambda checked, wid=ws.id, did=db_id:
                        self._link_all_databases_to_workspace(wid, did)
                )
                menu.addAction(action)
            if workspaces:
                menu.addSeparator()
            new_action = QAction(tr("new_workspace") + "...", self)
            new_action.triggered.connect(
                lambda: self._create_new_workspace_and_link_all_databases(db_id)
            )
            menu.addAction(new_action)
            return menu

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

    def _enumerate_server_databases(self, db_conn):
        """Connect (if needed) and return the list of database names, or None.

        Requires a live connection — used by the 'link all databases' action.
        """
        connection = self.connections.get(db_conn.id)
        if connection is None:
            # Fast reachability check to avoid a long blocking timeout.
            if hasattr(self, "_is_server_reachable") and not self._is_server_reachable(db_conn):
                return None
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                connection = self._create_connection(db_conn)
            except Exception as e:
                # Timeout, auth failure, driver error… — handled gracefully by
                # the caller (shows ws_link_all_failed), never a crash block.
                logger.warning(f"Could not connect to {db_conn.name}: {e}")
                connection = None
            finally:
                QApplication.restoreOverrideCursor()
        if connection is None:
            return None
        self.connections[db_conn.id] = connection  # cache for reuse
        try:
            from ....database.schema_loaders import SchemaLoaderFactory
            loader = SchemaLoaderFactory.create(
                db_conn.db_type, connection, db_conn.id, db_conn.name
            )
            if loader:
                return loader.get_databases() or []
        except Exception as e:
            logger.error(f"Could not enumerate databases for {db_conn.name}: {e}")
        return None

    def _link_all_databases_to_workspace(self, workspace_id: str, db_id: str):
        """Link every database of a multi-database server to a workspace.

        Snapshot semantics: creates one specific-database link per database
        (skipping those already linked) and removes any server-level ('') link.
        Requires a live connection to enumerate the databases.
        """
        db_conn = self._get_connection_by_id(db_id)
        if not db_conn:
            return

        names = self._enumerate_server_databases(db_conn)
        if not names:
            DialogHelper.warning(tr("ws_link_all_failed"), parent=self)
            return

        config_db = get_config_db()
        if config_db.replace_server_link_with_databases(workspace_id, db_id, names):
            if self._workspace_manager:
                self._workspace_manager.refresh_workspace(workspace_id)
            DialogHelper.info(tr("ws_link_all_done", count=len(names)), parent=self)

    def _create_new_workspace_and_link_all_databases(self, db_id: str):
        """Create a new workspace and link all databases of a server to it."""
        name, ok = QInputDialog.getText(self, tr("new_workspace"), tr("workspace_name") + ":")
        if not (ok and name.strip()):
            return
        config_db = get_config_db()
        ws = Workspace(id=str(uuid.uuid4()), name=name.strip(), description="")
        if config_db.add_workspace(ws):
            self._link_all_databases_to_workspace(ws.id, db_id)
        else:
            DialogHelper.warning("Failed to create workspace. Name may already exist.", parent=self)
