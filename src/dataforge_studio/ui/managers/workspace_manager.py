"""
Workspace Manager
Manager for workspaces - creating, editing, deleting and viewing resources.
Follows the same pattern as RootFolderManager.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QLabel, QMenu, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.form_builder import FormBuilder
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Workspace
from ...utils.image_loader import get_icon

import logging
import uuid
logger = logging.getLogger(__name__)


class WorkspaceManager(QWidget):
    """
    Workspace manager - browse and manage workspaces and their resources.

    Layout (same as RootFolderManager):
    - TOP: Toolbar (New, Rename, Delete, Refresh)
    - LEFT: Tree (workspaces > databases/queries/rootfolders)
    - RIGHT: Details of selected item
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.config_db = get_config_db()
        self._loaded = False
        self._current_workspace_id = None
        self._current_item: Optional[Workspace] = None

        self._setup_ui()

    def showEvent(self, event):
        """Override showEvent to lazy-load data on first show"""
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._load_workspaces)

    # ==================== ManagerProtocol Implementation ====================

    def refresh(self) -> None:
        """Refresh the view (reload workspaces from database)."""
        self._refresh()

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        """Set workspace filter.

        Note: WorkspaceManager doesn't filter by workspace (it manages workspaces).
        This method is provided for protocol compliance only.
        """
        pass  # No-op for WorkspaceManager

    def get_workspace_filter(self) -> Optional[str]:
        """Get current workspace filter (always None for WorkspaceManager)."""
        return None

    def get_current_item(self) -> Optional[Workspace]:
        """Get currently selected workspace."""
        return self._current_item

    def clear_selection(self) -> None:
        """Clear current selection."""
        self._current_item = None
        self._current_workspace_id = None
        self.workspace_tree.clearSelection()

    # ==================== UI Setup ====================

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar at TOP
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button("+ New", self._new_workspace, icon="add.png")
        toolbar_builder.add_button("Edit", self._edit_workspace, icon="edit.png")
        toolbar_builder.add_button("Delete", self._delete_workspace, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_refresh"), self._refresh, icon="refresh.png")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter (left: tree, right: details)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Workspace tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        tree_label = QLabel(tr("menu_workspaces"))
        tree_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(tree_label)

        self.workspace_tree = QTreeWidget()
        self.workspace_tree.setHeaderHidden(True)
        self.workspace_tree.setIndentation(20)
        self.workspace_tree.setRootIsDecorated(False)
        self.workspace_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.workspace_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.workspace_tree.itemClicked.connect(self._on_tree_click)
        self.workspace_tree.itemExpanded.connect(self._on_item_expanded)
        left_layout.addWidget(self.workspace_tree)

        main_splitter.addWidget(left_widget)

        # Right panel: Details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Details form
        self.details_form_builder = FormBuilder(title="Details") \
            .add_field("Name:", "name") \
            .add_field("Type:", "type") \
            .add_field("Description:", "description") \
            .add_field("Created:", "created") \
            .add_field("Updated:", "updated")

        details_form_widget = self.details_form_builder.build()
        right_layout.addWidget(details_form_widget, stretch=1)

        # Placeholder for future content (e.g., resource list)
        right_layout.addStretch(4)

        main_splitter.addWidget(right_widget)

        # Set splitter proportions (left 30%, right 70%)
        main_splitter.setSizes([350, 850])

        layout.addWidget(main_splitter)

    def _load_workspaces(self):
        """Load all workspaces into tree"""
        self.workspace_tree.clear()

        workspaces = self.config_db.get_all_workspaces()

        for ws in workspaces:
            self._add_workspace_to_tree(ws)

    def _add_workspace_to_tree(self, workspace: Workspace):
        """Add a workspace and its resources to the tree"""
        # Create workspace item
        ws_item = QTreeWidgetItem(self.workspace_tree)

        # Icon for workspace
        ws_icon = get_icon("workspace.png", size=16)
        if not ws_icon:
            ws_icon = get_icon("folder.png", size=16)
        if ws_icon:
            ws_item.setIcon(0, ws_icon)

        ws_item.setText(0, workspace.name)
        ws_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "workspace",
            "id": workspace.id,
            "workspace_obj": workspace
        })

        # Add dummy child for lazy loading (show expand arrow)
        dummy = QTreeWidgetItem(ws_item)
        dummy.setText(0, "Loading...")
        dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})

    def _load_workspace_resources(self, ws_item: QTreeWidgetItem, workspace_id: str):
        """Load resources for a workspace (called on expand)"""
        # Load databases
        databases = self.config_db.get_workspace_databases(workspace_id)
        for db in databases:
            db_item = QTreeWidgetItem(ws_item)
            db_icon = get_icon(f"{db.db_type.lower()}.png", size=16) or get_icon("database.png", size=16)
            if db_icon:
                db_item.setIcon(0, db_icon)
            db_item.setText(0, db.name)
            db_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "database",
                "id": db.id,
                "resource_obj": db
            })

        # Load queries
        queries = self.config_db.get_workspace_queries(workspace_id)
        for q in queries:
            q_item = QTreeWidgetItem(ws_item)
            q_icon = get_icon("query.png", size=16) or get_icon("sql.png", size=16)
            if q_icon:
                q_item.setIcon(0, q_icon)
            q_item.setText(0, q.name)
            q_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "query",
                "id": q.id,
                "resource_obj": q
            })

        # Load file roots
        file_roots = self.config_db.get_workspace_file_roots(workspace_id)
        for fr in file_roots:
            fr_item = QTreeWidgetItem(ws_item)
            fr_icon = get_icon("RootFolders.png", size=16)
            if fr_icon:
                fr_item.setIcon(0, fr_icon)
            fr_item.setText(0, fr.name or fr.path)
            fr_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "rootfolder",
                "id": fr.id,
                "resource_obj": fr
            })

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion (lazy loading)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        # Check if this workspace has a dummy "Loading..." child
        if item.childCount() == 1:
            first_child = item.child(0)
            child_data = first_child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("type") == "dummy":
                # Remove dummy
                item.removeChild(first_child)

                # Load real resources
                if data["type"] == "workspace":
                    self._load_workspace_resources(item, data["id"])

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        """Handle click on tree item (show details)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data["type"] == "workspace":
            self._show_workspace_details(data["workspace_obj"])
        elif data["type"] == "database":
            self._show_database_details(data["resource_obj"])
        elif data["type"] == "query":
            self._show_query_details(data["resource_obj"])
        elif data["type"] == "rootfolder":
            self._show_rootfolder_details(data["resource_obj"])

    def _show_workspace_details(self, workspace: Workspace):
        """Show workspace details in the details panel"""
        try:
            from datetime import datetime

            created = datetime.fromisoformat(workspace.created_at).strftime("%Y-%m-%d %H:%M:%S") if workspace.created_at else "N/A"
            updated = datetime.fromisoformat(workspace.updated_at).strftime("%Y-%m-%d %H:%M:%S") if workspace.updated_at else "N/A"

            self.details_form_builder.set_value("name", workspace.name)
            self.details_form_builder.set_value("type", "Workspace")
            self.details_form_builder.set_value("description", workspace.description or "")
            self.details_form_builder.set_value("created", created)
            self.details_form_builder.set_value("updated", updated)

            self._current_workspace_id = workspace.id

        except Exception as e:
            logger.error(f"Error showing workspace details: {e}")

    def _show_database_details(self, db):
        """Show database details"""
        self.details_form_builder.set_value("name", db.name)
        self.details_form_builder.set_value("type", f"Database ({db.db_type})")
        self.details_form_builder.set_value("description", db.description or "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_query_details(self, query):
        """Show query details"""
        self.details_form_builder.set_value("name", query.name)
        self.details_form_builder.set_value("type", "Query")
        self.details_form_builder.set_value("description", query.description or "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_rootfolder_details(self, rootfolder):
        """Show rootfolder details"""
        self.details_form_builder.set_value("name", rootfolder.name or rootfolder.path)
        self.details_form_builder.set_value("type", "RootFolder")
        self.details_form_builder.set_value("description", rootfolder.description or "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _on_tree_context_menu(self, position):
        """Show context menu for tree item"""
        item = self.workspace_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if data["type"] == "workspace":
            # Workspace context menu
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self._edit_workspace_item(item, data))
            menu.addAction(edit_action)

            menu.addSeparator()

            delete_action = QAction("Delete Workspace", self)
            delete_action.triggered.connect(lambda: self._delete_workspace_item(data["id"]))
            menu.addAction(delete_action)

        elif data["type"] in ["database", "query", "rootfolder"]:
            # Resource context menu - remove from workspace
            remove_action = QAction("Remove from Workspace", self)
            remove_action.triggered.connect(lambda: self._remove_resource_from_workspace(item, data))
            menu.addAction(remove_action)

        menu.exec(self.workspace_tree.viewport().mapToGlobal(position))

    def _remove_resource_from_workspace(self, item: QTreeWidgetItem, data: dict):
        """Remove a resource from its parent workspace"""
        parent_item = item.parent()
        if not parent_item:
            return

        parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if not parent_data or parent_data["type"] != "workspace":
            return

        workspace_id = parent_data["id"]
        resource_type = data["type"]
        resource_id = data["id"]

        if resource_type == "database":
            self.config_db.remove_database_from_workspace(workspace_id, resource_id)
        elif resource_type == "query":
            self.config_db.remove_query_from_workspace(workspace_id, resource_id)
        elif resource_type == "rootfolder":
            self.config_db.remove_file_root_from_workspace(workspace_id, resource_id)

        # Remove from tree
        parent_item.removeChild(item)

    def _new_workspace(self):
        """Create a new workspace using dialog"""
        from ..widgets.edit_dialogs import EditWorkspaceDialog

        dialog = EditWorkspaceDialog(parent=self, is_new=True)
        if dialog.exec():
            name, description = dialog.get_values()
            if name:
                ws = Workspace(
                    id=str(uuid.uuid4()),
                    name=name,
                    description=description
                )
                if self.config_db.add_workspace(ws):
                    self._add_workspace_to_tree(ws)
                else:
                    DialogHelper.warning("Failed to create workspace. Name may already exist.")
            else:
                DialogHelper.warning("Workspace name cannot be empty.")

    def _edit_workspace(self):
        """Edit the selected workspace"""
        selected_items = self.workspace_tree.selectedItems()
        if not selected_items:
            DialogHelper.warning("Please select a workspace to edit")
            return

        item = selected_items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data["type"] == "workspace":
            self._edit_workspace_item(item, data)
        else:
            DialogHelper.warning("Please select a workspace (not a resource)")

    def _edit_workspace_item(self, item: QTreeWidgetItem, data: dict):
        """Edit a workspace item using dialog"""
        from ..widgets.edit_dialogs import EditWorkspaceDialog

        ws = data["workspace_obj"]

        dialog = EditWorkspaceDialog(
            parent=self,
            name=ws.name,
            description=ws.description or "",
            is_new=False
        )

        if dialog.exec():
            name, description = dialog.get_values()
            if name:
                ws.name = name
                ws.description = description
                if self.config_db.update_workspace(ws):
                    item.setText(0, ws.name)
                    # Update stored data
                    data["workspace_obj"] = ws
                    item.setData(0, Qt.ItemDataRole.UserRole, data)
                    # Update details panel if this workspace is displayed
                    if self._current_workspace_id == ws.id:
                        self._show_workspace_details(ws)
                else:
                    DialogHelper.warning("Failed to update workspace. Name may already exist.")
            else:
                DialogHelper.warning("Workspace name cannot be empty.")

    def _delete_workspace(self):
        """Delete the selected workspace"""
        selected_items = self.workspace_tree.selectedItems()
        if not selected_items:
            DialogHelper.warning("Please select a workspace to delete")
            return

        item = selected_items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data["type"] == "workspace":
            self._delete_workspace_item(data["id"])
        else:
            DialogHelper.warning("Please select a workspace (not a resource)")

    def _delete_workspace_item(self, workspace_id: str):
        """Delete a workspace by ID"""
        if not DialogHelper.confirm(
            "Delete this workspace?\n\n"
            "This will only remove the workspace, not the resources in it."
        ):
            return

        if self.config_db.delete_workspace(workspace_id):
            self._refresh()
        else:
            DialogHelper.warning("Failed to delete workspace")

    def _refresh(self):
        """Refresh the tree"""
        self._load_workspaces()
        self.details_form_builder.clear()
