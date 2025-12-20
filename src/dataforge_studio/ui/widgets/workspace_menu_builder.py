"""
Workspace Menu Builder - Consolidated workspace submenu creation

Provides a reusable menu builder for adding/removing items to/from workspaces.
Used by all managers that support workspace integration.
"""

from typing import Callable, List, Optional, Set
from PySide6.QtWidgets import QMenu, QWidget, QInputDialog
from PySide6.QtGui import QAction
import uuid

from ..core.i18n_bridge import tr
from ..widgets.dialog_helper import DialogHelper
from ...database.config_db import get_config_db, Workspace


class WorkspaceMenuBuilder:
    """
    Builder for workspace submenus.

    Consolidates the repeated workspace menu pattern across managers:
    - QueriesManager
    - JobsManager
    - DatabaseManager
    - RootFolderManager

    Example usage:
        builder = WorkspaceMenuBuilder(
            parent=self,
            item_id=query_id,
            get_item_workspaces=lambda: config_db.get_query_workspaces(query_id),
            add_to_workspace=lambda ws_id: config_db.add_query_to_workspace(ws_id, query_id),
            remove_from_workspace=lambda ws_id: config_db.remove_query_from_workspace(ws_id, query_id),
        )
        menu = builder.build()
    """

    def __init__(
        self,
        parent: QWidget,
        item_id: str,
        get_item_workspaces: Callable[[], List[Workspace]],
        add_to_workspace: Callable[[str], None],
        remove_from_workspace: Callable[[str], None],
        menu_title: Optional[str] = None,
        use_checkmarks: bool = True,
        icon_name: Optional[str] = "Workspace",
    ):
        """
        Initialize the workspace menu builder.

        Args:
            parent: Parent widget for the menu
            item_id: ID of the item to add/remove from workspaces
            get_item_workspaces: Callback returning list of workspaces containing this item
            add_to_workspace: Callback to add item to a workspace (takes workspace_id)
            remove_from_workspace: Callback to remove item from a workspace (takes workspace_id)
            menu_title: Optional custom menu title (default: "Workspaces")
            use_checkmarks: If True, use checkable actions; if False, use text prefix
            icon_name: Icon name for the menu (default: "Workspace")
        """
        self.parent = parent
        self.item_id = item_id
        self.get_item_workspaces = get_item_workspaces
        self.add_to_workspace = add_to_workspace
        self.remove_from_workspace = remove_from_workspace
        self.menu_title = menu_title or tr("menu_workspaces")
        self.use_checkmarks = use_checkmarks
        self.icon_name = icon_name

        self._config_db = get_config_db()

    def build(self) -> QMenu:
        """
        Build and return the workspace submenu.

        Returns:
            QMenu with workspace options
        """
        menu = QMenu(self.menu_title, self.parent)

        # Set icon if available
        if self.icon_name:
            from ..widgets.toolbar_builder import get_icon
            icon = get_icon(self.icon_name, size=16) or get_icon("folder", size=16)
            if icon:
                menu.setIcon(icon)

        # Get all workspaces
        workspaces = self._config_db.get_all_workspaces()

        # Handle empty workspaces case
        if not workspaces:
            new_action = QAction(tr("new_workspace"), self.parent)
            new_action.triggered.connect(self._create_new_workspace)
            menu.addAction(new_action)
            return menu

        # Get workspaces this item belongs to
        current_workspaces = self.get_item_workspaces()
        current_workspace_ids = {ws.id for ws in current_workspaces}

        # Add workspace options
        for ws in workspaces:
            is_in_workspace = ws.id in current_workspace_ids

            if self.use_checkmarks:
                action = QAction(ws.name, self.parent)
                action.setCheckable(True)
                action.setChecked(is_in_workspace)
            else:
                # Text prefix style (like rootfolder_manager)
                action_text = f"✓ {ws.name}" if is_in_workspace else ws.name
                action = QAction(action_text, self.parent)

            # Connect toggle action
            action.triggered.connect(
                lambda checked, wid=ws.id, in_ws=is_in_workspace:
                    self._toggle_workspace(wid, in_ws)
            )
            menu.addAction(action)

        # Separator and New Workspace option
        menu.addSeparator()

        new_action = QAction(tr("new_workspace") + "...", self.parent)
        new_action.triggered.connect(self._create_new_workspace)
        menu.addAction(new_action)

        return menu

    def _toggle_workspace(self, workspace_id: str, is_in_workspace: bool):
        """Toggle item in/out of a workspace."""
        try:
            if is_in_workspace:
                self.remove_from_workspace(workspace_id)
            else:
                self.add_to_workspace(workspace_id)
        except Exception as e:
            DialogHelper.error("Error updating workspace", parent=self.parent, details=str(e))

    def _create_new_workspace(self):
        """Create a new workspace and add the item to it."""
        name, ok = QInputDialog.getText(
            self.parent,
            tr("new_workspace"),
            tr("workspace_name") + ":" if hasattr(tr, '__call__') else "Workspace name:"
        )

        if ok and name.strip():
            ws = Workspace(
                id=str(uuid.uuid4()),
                name=name.strip(),
                description=""
            )

            if self._config_db.add_workspace(ws):
                self.add_to_workspace(ws.id)
            else:
                DialogHelper.warning(
                    tr("workspace_create_failed") if hasattr(tr, '__call__') else "Failed to create workspace",
                    parent=self.parent
                )


def build_workspace_menu(
    parent: QWidget,
    item_id: str,
    get_item_workspaces: Callable[[], List[Workspace]],
    add_to_workspace: Callable[[str], None],
    remove_from_workspace: Callable[[str], None],
    menu_title: Optional[str] = None,
    use_checkmarks: bool = True,
) -> QMenu:
    """
    Convenience function to build a workspace submenu.

    Args:
        parent: Parent widget for the menu
        item_id: ID of the item
        get_item_workspaces: Callback returning workspaces containing this item
        add_to_workspace: Callback to add item to workspace
        remove_from_workspace: Callback to remove item from workspace
        menu_title: Optional custom menu title
        use_checkmarks: If True, use checkable actions

    Returns:
        QMenu with workspace options
    """
    builder = WorkspaceMenuBuilder(
        parent=parent,
        item_id=item_id,
        get_item_workspaces=get_item_workspaces,
        add_to_workspace=add_to_workspace,
        remove_from_workspace=remove_from_workspace,
        menu_title=menu_title,
        use_checkmarks=use_checkmarks,
    )
    return builder.build()
