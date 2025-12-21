"""
Workspace Manager
Manager for workspaces - creating, editing, deleting and viewing resources.
Follows the same pattern as RootFolderManager.

Resources are displayed with their full subtrees:
- RootFolders: show subfolder attached, then folder/file tree
- Databases: show specific database attached, then tables/views
- Queries: grouped by category
"""

from pathlib import Path
from typing import Optional, TYPE_CHECKING
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QLabel, QMenu, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.form_builder import FormBuilder
from ..widgets.tree_populator import TreePopulator
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Workspace
from ...database.models.workspace_resource import WorkspaceFileRoot, WorkspaceDatabase
from ...utils.image_loader import get_icon

import logging
import uuid
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .database_manager import DatabaseManager
    from .rootfolder_manager import RootFolderManager


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

        # Manager references for delegating subtree loading
        self._database_manager: Optional["DatabaseManager"] = None
        self._rootfolder_manager: Optional["RootFolderManager"] = None

        self._setup_ui()

    def set_managers(
        self,
        database_manager: Optional["DatabaseManager"] = None,
        rootfolder_manager: Optional["RootFolderManager"] = None
    ):
        """
        Set references to managers for delegation of subtree loading.

        Args:
            database_manager: DatabaseManager instance for loading database schemas
            rootfolder_manager: RootFolderManager instance (currently unused, for future)
        """
        self._database_manager = database_manager
        self._rootfolder_manager = rootfolder_manager

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
        """
        Load resources for a workspace (called on expand).

        Uses *_with_context methods to get subfolder_path and database_name.
        Adds dummy children for lazy loading of subtrees.
        Groups queries by category.
        """
        # Load databases with context (specific database_name if attached)
        ws_databases = self.config_db.get_workspace_databases_with_context(workspace_id)
        for ws_db in ws_databases:
            db = ws_db.connection
            db_item = QTreeWidgetItem(ws_item)
            db_icon = get_icon(f"{db.db_type.lower()}.png", size=16) or get_icon("database.png", size=16)
            if db_icon:
                db_item.setIcon(0, db_icon)
            # Display specific database name or server name
            db_item.setText(0, ws_db.display_name)
            db_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "database",
                "id": db.id,
                "database_name": ws_db.database_name,
                "resource_obj": db,
                "ws_database": ws_db
            })
            # Add dummy child for lazy loading of schema
            TreePopulator.add_dummy_child(db_item)

        # Load queries grouped by category
        queries = self.config_db.get_workspace_queries(workspace_id)
        if queries:
            self._add_queries_grouped_by_category(ws_item, queries)

        # Load file roots with context (subfolder_path if attached)
        ws_file_roots = self.config_db.get_workspace_file_roots_with_context(workspace_id)
        for ws_fr in ws_file_roots:
            fr = ws_fr.file_root
            fr_item = QTreeWidgetItem(ws_item)
            fr_icon = get_icon("folder.png", size=16)
            if fr_icon:
                fr_item.setIcon(0, fr_icon)
            # Display subfolder name or root name
            fr_item.setText(0, ws_fr.display_name)
            fr_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "rootfolder",
                "id": fr.id,
                "subfolder_path": ws_fr.subfolder_path,
                "full_path": ws_fr.full_path,
                "resource_obj": fr,
                "ws_file_root": ws_fr
            })
            # Add dummy child for lazy loading of folder contents
            TreePopulator.add_dummy_child(fr_item)

    def _add_queries_grouped_by_category(self, parent_item: QTreeWidgetItem, queries: list):
        """Add queries to tree grouped by category."""
        # Group queries by category
        categories = {}
        for q in queries:
            cat = q.category or "No category"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(q)

        # Create category nodes
        for cat_name in sorted(categories.keys()):
            cat_queries = categories[cat_name]

            # If only one category, add queries directly (no category node)
            if len(categories) == 1:
                for q in cat_queries:
                    self._add_query_item(parent_item, q)
            else:
                # Create category node
                cat_item = QTreeWidgetItem(parent_item)
                cat_icon = get_icon("folder.png", size=16)
                if cat_icon:
                    cat_item.setIcon(0, cat_icon)
                cat_item.setText(0, f"{cat_name} ({len(cat_queries)})")
                cat_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "query_category",
                    "name": cat_name
                })

                # Add queries under category
                for q in cat_queries:
                    self._add_query_item(cat_item, q)

    def _add_query_item(self, parent_item: QTreeWidgetItem, query) -> QTreeWidgetItem:
        """Add a single query item to the tree."""
        q_item = QTreeWidgetItem(parent_item)
        q_icon = get_icon("query.png", size=16) or get_icon("sql.png", size=16)
        if q_icon:
            q_item.setIcon(0, q_icon)
        q_item.setText(0, query.name)
        q_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "query",
            "id": query.id,
            "resource_obj": query
        })
        return q_item

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion (lazy loading)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        # Check if item has a dummy child (needs lazy loading)
        if TreePopulator.has_dummy_child(item):
            TreePopulator.remove_dummy_child(item)

            if item_type == "workspace":
                self._load_workspace_resources(item, data["id"])

            elif item_type == "database":
                self._load_database_subtree(item, data)

            elif item_type == "rootfolder":
                self._load_folder_subtree(item, data)

            elif item_type == "folder":
                # Subfolder expansion - use path from data
                self._load_subfolder_contents(item, data)

    def _load_database_subtree(self, parent_item: QTreeWidgetItem, data: dict):
        """Load database schema subtree using DatabaseManager."""
        if not self._database_manager:
            logger.warning("No database_manager set - cannot load database schema")
            return

        db_config = data.get("resource_obj")
        database_name = data.get("database_name", "")

        if not db_config:
            return

        # Use TreePopulator to delegate to DatabaseManager
        success = TreePopulator.load_database_subtree(
            parent_item,
            db_config,
            self._database_manager,
            database_name=database_name
        )

        if not success:
            # Re-add dummy child to allow retry
            TreePopulator.add_dummy_child(parent_item, tr("double_click_to_load") if hasattr(tr, '__call__') else "Double-click to load")
            parent_item.setExpanded(False)

    def _load_folder_subtree(self, parent_item: QTreeWidgetItem, data: dict):
        """Load folder contents subtree (for rootfolder items)."""
        full_path = data.get("full_path")
        if not full_path:
            return

        folder_path = Path(full_path)
        if not folder_path.exists():
            logger.warning(f"Folder does not exist: {folder_path}")
            return

        # Use TreePopulator to load folder contents
        TreePopulator.load_folder_subtree(
            parent_item,
            folder_path,
            add_item_callback=self._add_tree_item
        )

    def _load_subfolder_contents(self, parent_item: QTreeWidgetItem, data: dict):
        """Load subfolder contents (for folder items within rootfolder)."""
        folder_path = data.get("path")
        if not folder_path:
            return

        folder_path = Path(folder_path)
        if not folder_path.exists():
            logger.warning(f"Folder does not exist: {folder_path}")
            return

        # Use TreePopulator to load folder contents
        TreePopulator.load_folder_subtree(
            parent_item,
            folder_path,
            add_item_callback=self._add_tree_item
        )

    def _add_tree_item(self, parent: QTreeWidgetItem, text: list, data: dict) -> QTreeWidgetItem:
        """Callback for TreePopulator to add items to tree."""
        item = QTreeWidgetItem(parent)
        item.setText(0, text[0])
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        return item

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        """Handle click on tree item (show details)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        if item_type == "workspace":
            self._show_workspace_details(data["workspace_obj"])
        elif item_type == "database":
            self._show_database_details(data)
        elif item_type == "query":
            self._show_query_details(data["resource_obj"])
        elif item_type == "query_category":
            self._show_category_details(data)
        elif item_type == "rootfolder":
            self._show_rootfolder_details(data)
        elif item_type == "folder":
            self._show_folder_details(data)
        elif item_type == "file":
            self._show_file_details(data)

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

    def _show_database_details(self, data: dict):
        """Show database details"""
        db = data.get("resource_obj")
        database_name = data.get("database_name", "")

        if database_name:
            # Specific database
            self.details_form_builder.set_value("name", database_name)
            self.details_form_builder.set_value("type", f"Database on {db.name}")
        else:
            # Server
            self.details_form_builder.set_value("name", db.name)
            self.details_form_builder.set_value("type", f"Server ({db.db_type})")

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

    def _show_rootfolder_details(self, data: dict):
        """Show rootfolder details"""
        rootfolder = data.get("resource_obj")
        subfolder_path = data.get("subfolder_path", "")
        full_path = data.get("full_path", "")

        if subfolder_path:
            # Subfolder attached
            self.details_form_builder.set_value("name", Path(subfolder_path).name)
            self.details_form_builder.set_value("type", "Subfolder")
        else:
            # Root folder
            self.details_form_builder.set_value("name", rootfolder.name or rootfolder.path)
            self.details_form_builder.set_value("type", "RootFolder")

        self.details_form_builder.set_value("description", full_path or rootfolder.path)
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_folder_details(self, data: dict):
        """Show folder details"""
        folder_path = data.get("path", "")
        self.details_form_builder.set_value("name", Path(folder_path).name if folder_path else "")
        self.details_form_builder.set_value("type", "Folder")
        self.details_form_builder.set_value("description", folder_path)
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_file_details(self, data: dict):
        """Show file details"""
        file_path = data.get("path", "")
        path_obj = Path(file_path) if file_path else None

        self.details_form_builder.set_value("name", path_obj.name if path_obj else "")
        self.details_form_builder.set_value("type", f"File ({path_obj.suffix})" if path_obj else "File")
        self.details_form_builder.set_value("description", file_path)
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_category_details(self, data: dict):
        """Show query category details"""
        cat_name = data.get("name", "")
        self.details_form_builder.set_value("name", cat_name)
        self.details_form_builder.set_value("type", "Query Category")
        self.details_form_builder.set_value("description", "")
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
