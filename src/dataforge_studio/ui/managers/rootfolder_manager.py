"""
RootFolder Manager - File browser and viewer for configured root folders

Uses ObjectViewerWidget for unified file display.
"""

from typing import Optional
from pathlib import Path
import logging
import sqlite3
import uuid

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QMenu, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.pinnable_panel import PinnablePanel
from ..widgets.object_viewer_widget import ObjectViewerWidget
from ..core.i18n_bridge import tr
from ..utils.tree_helpers import (
    get_file_icon,
    count_files_recursive,
    populate_tree_with_local_folder,
    add_dummy_child,
)
from ...database.config_db import get_config_db, FileRoot
from ...utils.image_loader import get_icon

logger = logging.getLogger(__name__)


class RootFolderManager(QWidget):
    """
    Root folder browser and file viewer.

    Layout:
    - TOP: Toolbar (Add RootFolder, Remove RootFolder, Refresh)
    - LEFT: File tree (root folders > folders > files)
    - RIGHT: ObjectViewerWidget (unified file display)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.config_db = get_config_db()
        self._loaded = False
        self._workspace_filter: Optional[str] = None
        self._current_item: Optional[FileRoot] = None

        self._setup_ui()

    def showEvent(self, event):
        """Override showEvent to lazy-load data on first show"""
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._load_root_folders)

    # ==================== ManagerProtocol Implementation ====================

    def refresh(self) -> None:
        """Refresh the view (reload root folders from database)."""
        self._load_root_folders()

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        """Set workspace filter and refresh the view."""
        self._workspace_filter = workspace_id
        if self._loaded:
            self.refresh()

    def get_workspace_filter(self) -> Optional[str]:
        """Get current workspace filter."""
        return self._workspace_filter

    def get_current_item(self) -> Optional[FileRoot]:
        """Get currently selected root folder."""
        return self._current_item

    def clear_selection(self) -> None:
        """Clear current selection."""
        self._current_item = None
        self.file_tree.clearSelection()

    # ==================== UI Setup ====================

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button("Add RootFolder", self._add_rootfolder, icon="add.png")
        toolbar_builder.add_button("Remove RootFolder", self._remove_rootfolder, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_refresh"), self._refresh, icon="refresh.png")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter (left: tree, right: object viewer)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.setChildrenCollapsible(False)

        # Left panel: Pinnable panel with file explorer tree
        self.left_panel = PinnablePanel(
            title="RootFolders",
            icon_name="RootFolders.png"
        )
        self.left_panel.set_normal_width(280)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setIndentation(20)
        self.file_tree.setRootIsDecorated(False)
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.file_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.file_tree.itemClicked.connect(self._on_tree_click)
        self.file_tree.itemExpanded.connect(self._on_item_expanded)
        tree_layout.addWidget(self.file_tree)

        self.left_panel.set_content(tree_container)
        self.main_splitter.addWidget(self.left_panel)

        # Right panel: ObjectViewerWidget (unified display)
        self.object_viewer = ObjectViewerWidget()
        self.main_splitter.addWidget(self.object_viewer)

        # Set splitter proportions (left 30%, right 70%)
        self.main_splitter.setSizes([350, 850])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.main_splitter)

    # ==================== Tree Loading ====================

    def _load_root_folders(self):
        """Load all root folders into tree"""
        self.file_tree.clear()

        if self._workspace_filter:
            root_folders = self.config_db.get_workspace_file_roots(self._workspace_filter)
        else:
            root_folders = self.config_db.get_all_file_roots()

        for root_folder in root_folders:
            self._add_rootfolder_to_tree(root_folder)

    def _add_rootfolder_to_tree(self, root_folder: FileRoot):
        """Add a root folder and its contents to the tree"""
        root_path = Path(root_folder.path)

        if not root_path.exists():
            logger.warning(f"RootFolder path does not exist: {root_path}")
            return

        root_item = QTreeWidgetItem(self.file_tree)

        root_icon = get_icon("RootFolders.png", size=16)
        if root_icon:
            root_item.setIcon(0, root_icon)

        file_count = count_files_recursive(root_path)
        display_name = root_folder.name or root_path.name
        root_item.setText(0, f"{display_name} ({file_count})")
        root_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "rootfolder",
            "rootfolder_obj": root_folder,
            "id": root_folder.id,
            "path": str(root_path),
            "name": root_folder.name or root_path.name
        })

        # Use tree_helpers for folder population
        populate_tree_with_local_folder(root_item, root_path, recursive=False)

    # Note: Folder loading is now handled by tree_helpers.populate_tree_with_local_folder

    # ==================== Tree Event Handlers ====================

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion (lazy loading)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if item.childCount() == 1:
            first_child = item.child(0)
            child_data = first_child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("type") == "dummy":
                item.removeChild(first_child)

                if data["type"] in ["folder", "rootfolder"]:
                    folder_path = Path(data["path"])
                    # Use tree_helpers for folder population
                    populate_tree_with_local_folder(item, folder_path, recursive=False)

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        """Handle single click on tree item (show details)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data["type"] == "rootfolder":
            self._show_rootfolder_details(data["rootfolder_obj"])
        elif data["type"] == "folder":
            self._show_folder_details(data)
        elif data["type"] == "file":
            # Use public API method
            self.show_file(Path(data["path"]))

    def _on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item (open file)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data["type"] == "file":
            # Use public API method
            self.show_file(Path(data["path"]))

    def _show_rootfolder_details(self, rootfolder: FileRoot):
        """Show root folder details in the viewer"""
        try:
            from datetime import datetime
            modified = "-"
            if rootfolder.updated_at:
                try:
                    modified = datetime.fromisoformat(rootfolder.updated_at).strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    modified = rootfolder.updated_at

            self.object_viewer.show_folder(
                name=rootfolder.name or Path(rootfolder.path).name,
                path=rootfolder.path,
                modified=modified
            )
            self._current_item = rootfolder

        except Exception as e:
            logger.error(f"Error showing root folder details: {e}")

    def _show_folder_details(self, data: dict):
        """Show folder details in the viewer"""
        self.object_viewer.show_folder(
            name=data.get("name", "-"),
            path=data.get("path", "-"),
            modified="-"
        )

    # ==================== Public API (for WorkspaceManager) ====================

    def show_file(self, file_path: Path, target_viewer=None):
        """
        Display a file in the viewer.

        Args:
            file_path: Path to the file
            target_viewer: Optional ObjectViewerWidget (default: self.object_viewer)
        """
        viewer = target_viewer if target_viewer else self.object_viewer
        viewer.show_file(file_path)

    def show_folder(self, name: str, path: str, modified: str = "-", target_viewer=None):
        """
        Display folder details in the viewer.

        Args:
            name: Folder name
            path: Folder path
            modified: Last modified date
            target_viewer: Optional ObjectViewerWidget (default: self.object_viewer)
        """
        viewer = target_viewer if target_viewer else self.object_viewer
        viewer.show_folder(name, path, modified)

    def open_file_location(self, file_path: Path):
        """Open file location in system file explorer."""
        self._open_file_location(file_path)

    def get_file_context_actions(self, data: dict, parent, target_viewer=None):
        """
        Get context menu actions for a file.

        Args:
            data: File data dict with 'path' key
            parent: Parent widget for actions
            target_viewer: Optional ObjectViewerWidget for "Open" action

        Returns:
            List of QAction objects
        """
        actions = []
        file_path = Path(data.get("path", ""))

        # Open action
        open_action = QAction("Open", parent)
        open_action.triggered.connect(
            lambda: self.show_file(file_path, target_viewer)
        )
        actions.append(open_action)

        # Open File Location action
        open_location_action = QAction("Open File Location", parent)
        open_location_action.triggered.connect(
            lambda: self.open_file_location(file_path)
        )
        actions.append(open_location_action)

        return actions

    # ==================== Context Menu ====================

    def _on_tree_context_menu(self, position):
        """Show context menu for tree item"""
        item = self.file_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if data["type"] == "rootfolder":
            edit_action = QAction("Edit Name & Description", self)
            edit_action.triggered.connect(lambda: self._edit_rootfolder(data["rootfolder_obj"]))
            menu.addAction(edit_action)

            menu.addSeparator()

            workspace_menu = self._build_workspace_submenu(data["id"], None)
            menu.addMenu(workspace_menu)

            menu.addSeparator()

            remove_action = QAction("Remove RootFolder", self)
            remove_action.triggered.connect(lambda: self._remove_rootfolder_by_id(data["id"]))
            menu.addAction(remove_action)

            refresh_action = QAction("Refresh", self)
            refresh_action.triggered.connect(self._refresh)
            menu.addAction(refresh_action)

        elif data["type"] == "folder":
            rootfolder_id, subfolder_path = self._get_rootfolder_info(item)
            if rootfolder_id:
                workspace_menu = self._build_workspace_submenu(rootfolder_id, subfolder_path)
                menu.addMenu(workspace_menu)

        elif data["type"] == "file":
            # Use public API methods
            for action in self.get_file_context_actions(data, self):
                menu.addAction(action)

        menu.exec(self.file_tree.viewport().mapToGlobal(position))

    def _open_file_location(self, file_path: Path):
        """Open file location in file explorer"""
        from ...utils.os_helpers import reveal_in_explorer
        reveal_in_explorer(file_path)

    # ==================== RootFolder CRUD ====================

    def _add_rootfolder(self):
        """Add a new root folder"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Root Folder",
            str(Path.home())
        )

        if not folder_path:
            return

        try:
            root_folder = FileRoot(
                id=str(uuid.uuid4()),
                path=folder_path,
                description=""
            )

            self.config_db._save_file_root(root_folder)
            self._refresh()
            DialogHelper.info(f"RootFolder added: {folder_path}")

        except sqlite3.Error as e:
            logger.error(f"Error adding RootFolder: {e}")
            DialogHelper.error("Error adding RootFolder", details=str(e))

    def _edit_rootfolder(self, rootfolder: FileRoot):
        """Edit root folder name and description"""
        from ..widgets.edit_dialogs import EditRootFolderDialog

        dialog = EditRootFolderDialog(
            parent=self,
            name=rootfolder.name or Path(rootfolder.path).name,
            description=rootfolder.description or "",
            path=rootfolder.path
        )

        if dialog.exec():
            name, description, path = dialog.get_values()

            if not name:
                DialogHelper.warning("Name cannot be empty")
                return

            try:
                rootfolder.name = name
                rootfolder.description = description
                self.config_db._save_file_root(rootfolder)
                self._refresh()
                DialogHelper.info("RootFolder updated successfully")

            except sqlite3.Error as e:
                logger.error(f"Error updating RootFolder: {e}")
                DialogHelper.error("Error updating RootFolder", details=str(e))

    def _remove_rootfolder(self):
        """Remove selected root folder"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            DialogHelper.warning("Please select a RootFolder to remove")
            return

        item = selected_items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data["type"] == "rootfolder":
            self._remove_rootfolder_by_id(data["id"])
        else:
            DialogHelper.warning("Please select a RootFolder (not a file or subfolder)")

    def _remove_rootfolder_by_id(self, root_id: str):
        """Remove root folder by ID"""
        if not DialogHelper.confirm("Remove this RootFolder?\n\n(The folder itself will not be deleted)"):
            return

        try:
            self.config_db._delete_file_root(root_id)
            self._refresh()
            DialogHelper.info("RootFolder removed")

        except sqlite3.Error as e:
            logger.error(f"Error removing RootFolder: {e}")
            DialogHelper.error("Error removing RootFolder", details=str(e))

    def get_tree_widget(self):
        """Return the tree widget for embedding in ResourcesManager."""
        return self.file_tree

    def _refresh(self):
        """Refresh the tree"""
        self._load_root_folders()
        self.object_viewer.clear()

    # ==================== Workspace Management ====================

    def _get_rootfolder_info(self, item: QTreeWidgetItem) -> tuple:
        """Get rootfolder ID and subfolder path for a tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or "path" not in data:
            return None, None

        folder_path = Path(data["path"])

        current = item.parent()
        while current:
            parent_data = current.data(0, Qt.ItemDataRole.UserRole)
            if parent_data and parent_data.get("type") == "rootfolder":
                rootfolder_id = parent_data["id"]
                rootfolder_obj = parent_data.get("rootfolder_obj")
                if rootfolder_obj:
                    rootfolder_path = Path(rootfolder_obj.path)
                    try:
                        subfolder_path = str(folder_path.relative_to(rootfolder_path))
                        return rootfolder_id, subfolder_path
                    except ValueError:
                        return rootfolder_id, str(folder_path)
                return rootfolder_id, None
            current = current.parent()

        return None, None

    def _build_workspace_submenu(self, rootfolder_id: str, subfolder_path: Optional[str]) -> QMenu:
        """Build a submenu for adding/removing a file root to/from workspaces."""
        from ...database.config_db import Workspace

        menu = QMenu(tr("menu_workspaces"), self)

        workspaces = self.config_db.get_all_workspaces()
        current_workspaces = self.config_db.get_file_root_workspaces(rootfolder_id, subfolder_path)
        current_workspace_ids = {ws.id for ws in current_workspaces}

        for ws in workspaces:
            is_in_workspace = ws.id in current_workspace_ids
            action_text = f"* {ws.name}" if is_in_workspace else ws.name

            action = QAction(action_text, self)
            action.triggered.connect(
                lambda checked, wid=ws.id, rid=rootfolder_id, sp=subfolder_path, in_ws=is_in_workspace:
                    self._toggle_workspace(wid, rid, sp, in_ws)
            )
            menu.addAction(action)

        if workspaces:
            menu.addSeparator()

        new_action = QAction("+ " + tr("menu_workspaces_manage").replace("...", ""), self)
        new_action.triggered.connect(
            lambda: self._create_new_workspace_and_add(rootfolder_id, subfolder_path)
        )
        menu.addAction(new_action)

        return menu

    def _toggle_workspace(self, workspace_id: str, rootfolder_id: str, subfolder_path: Optional[str], is_in_workspace: bool):
        """Toggle a file root in/out of a workspace"""
        try:
            if is_in_workspace:
                self.config_db.remove_file_root_from_workspace(workspace_id, rootfolder_id)
            else:
                self.config_db.add_file_root_to_workspace(workspace_id, rootfolder_id, subfolder_path)

            logger.info(f"{'Removed from' if is_in_workspace else 'Added to'} workspace: rootfolder {rootfolder_id}")

        except Exception as e:
            logger.error(f"Error toggling workspace: {e}")
            DialogHelper.error("Error updating workspace", details=str(e))

    def _create_new_workspace_and_add(self, rootfolder_id: str, subfolder_path: Optional[str]):
        """Create a new workspace and add the file root to it"""
        from ...database.config_db import Workspace

        name, ok = QInputDialog.getText(self, "New Workspace", "Workspace name:")
        if ok and name.strip():
            ws = Workspace(
                id=str(uuid.uuid4()),
                name=name.strip(),
                description=""
            )

            if self.config_db.add_workspace(ws):
                self._toggle_workspace(ws.id, rootfolder_id, subfolder_path, False)
                logger.info(f"Created workspace '{ws.name}' and added rootfolder")
            else:
                DialogHelper.warning("Failed to create workspace. Name may already exist.")
