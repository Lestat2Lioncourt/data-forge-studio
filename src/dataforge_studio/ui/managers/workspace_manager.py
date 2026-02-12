"""
Workspace Manager - Managing workspaces and their resources.

Uses ObjectViewerWidget for unified content display (same as RootFolderManager).
"""

from pathlib import Path
from typing import Optional, TYPE_CHECKING, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QLabel, QMenu, QFileDialog, QTabWidget, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.tree_populator import TreePopulator
from ..widgets.object_viewer_widget import ObjectViewerWidget
from ..widgets.pinnable_panel import PinnablePanel
from ..core.i18n_bridge import tr
from ..utils.tree_helpers import (
    populate_tree_with_local_folder,
    populate_tree_with_remote_files,
)
from ...database.config_db import get_config_db, Workspace, Script
from ...database.models.workspace_resource import WorkspaceFileRoot, WorkspaceDatabase
from ...utils.image_loader import get_icon, get_database_icon
from ...utils.workspace_export import (
    export_workspace_to_json, save_export_to_file, get_export_summary,
    load_import_from_file, check_workspace_conflict, import_workspace_from_json,
    ImportConflictMode, get_import_summary
)

import logging
import uuid
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .database_manager import DatabaseManager
    from .rootfolder_manager import RootFolderManager
    from .scripts_manager import ScriptsManager
    from .jobs_manager import JobsManager


class WorkspaceManager(QWidget):
    """
    Workspace manager - browse and manage workspaces and their resources.

    Layout:
    - TOP: Toolbar (New, Rename, Delete, Refresh)
    - LEFT: Tree (workspaces > databases/queries/rootfolders)
    - RIGHT: ObjectViewerWidget (unified content display)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.config_db = get_config_db()
        self._loaded = False
        self._current_workspace_id = None
        self._current_item: Optional[Workspace] = None

        self._database_manager: Optional["DatabaseManager"] = None
        self._rootfolder_manager: Optional["RootFolderManager"] = None
        self._ftproot_manager: Optional["FTPRootManager"] = None
        self._scripts_manager: Optional["ScriptsManager"] = None
        self._jobs_manager: Optional["JobsManager"] = None

        # Pending FTP loads: {ftp_root_id: (parent_item, remote_path)}
        self._pending_ftp_loads_map: dict = {}

        # Filter state
        self._filter_pending_pattern: Optional[str] = None  # Pattern waiting for FTP loads
        self._filter_debounce_timer: Optional["QTimer"] = None  # Debounce timer for filter input

        self._setup_ui()

    def set_managers(
        self,
        database_manager: Optional["DatabaseManager"] = None,
        rootfolder_manager: Optional["RootFolderManager"] = None,
        ftproot_manager: Optional["FTPRootManager"] = None,
        scripts_manager: Optional["ScriptsManager"] = None,
        jobs_manager: Optional["JobsManager"] = None
    ):
        """Set references to managers for delegation."""
        self._database_manager = database_manager
        self._rootfolder_manager = rootfolder_manager
        self._ftproot_manager = ftproot_manager
        self._scripts_manager = scripts_manager
        self._jobs_manager = jobs_manager

        # Connect to FTPRootManager's connection signals
        if self._ftproot_manager:
            self._ftproot_manager.connection_established.connect(
                self._on_ftp_connection_established
            )
            self._ftproot_manager.connection_failed.connect(
                self._on_ftp_connection_failed
            )

        # Refresh workspace tree when a query is saved (auto-linked)
        if self._database_manager:
            self._database_manager.query_saved.connect(self._on_query_saved_from_workspace)

    def showEvent(self, event):
        """Lazy-load data on first show."""
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._load_workspaces)

    # ==================== ManagerProtocol Implementation ====================

    def refresh(self) -> None:
        self._refresh()

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        pass  # WorkspaceManager doesn't filter by workspace

    def get_workspace_filter(self) -> Optional[str]:
        return None

    def get_current_item(self) -> Optional[Workspace]:
        return self._current_item

    def clear_selection(self) -> None:
        self._current_item = None
        self._current_workspace_id = None
        self.workspace_tree.clearSelection()

    # ==================== UI Setup ====================

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button("+ New", self._new_workspace, icon="add.png")
        toolbar_builder.add_button("Edit", self._edit_workspace, icon="edit.png")
        toolbar_builder.add_button("Delete", self._delete_workspace, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Import", self._import_workspace, icon="import.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_refresh"), self._refresh, icon="refresh.png")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.setChildrenCollapsible(False)

        # Left panel: Pinnable panel with workspace tree
        self.left_panel = PinnablePanel(
            title=tr("menu_workspaces"),
            icon_name="workspace.png"
        )
        self.left_panel.set_normal_width(350)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(4)

        # Filter input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filtre: *valeur* ou valeur")
        self.filter_input.setClearButtonEnabled(True)
        self.filter_input.textChanged.connect(self._on_filter_changed)
        tree_layout.addWidget(self.filter_input)

        self.workspace_tree = QTreeWidget()
        self.workspace_tree.setHeaderHidden(True)
        self.workspace_tree.setIndentation(20)
        self.workspace_tree.setRootIsDecorated(False)
        self.workspace_tree.setExpandsOnDoubleClick(False)
        self.workspace_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.workspace_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.workspace_tree.itemClicked.connect(self._on_tree_click)
        self.workspace_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.workspace_tree.itemExpanded.connect(self._on_item_expanded)
        tree_layout.addWidget(self.workspace_tree)

        self.left_panel.set_content(tree_container)
        self.main_splitter.addWidget(self.left_panel)

        # Right panel: Tab widget for queries (like DatabaseManager)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.setMinimumWidth(200)

        # Add welcome/preview tab with ObjectViewerWidget
        self.object_viewer = ObjectViewerWidget()
        self.tab_widget.addTab(self.object_viewer, "Preview")

        self.main_splitter.addWidget(self.tab_widget)

        # Set splitter proportions
        self.main_splitter.setSizes([350, 850])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.main_splitter)

    def _close_tab(self, index: int):
        """Close a tab (but not the Preview tab)."""
        if index == 0:  # Don't close Preview tab
            return

        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        if widget:
            if hasattr(widget, 'cleanup'):
                widget.cleanup()
            widget.deleteLater()

    # ==================== Tree Filtering ====================

    def _on_filter_changed(self, text: str):
        """Handle filter input change with debounce."""
        from PySide6.QtCore import QTimer

        # Cancel any pending debounce timer
        if self._filter_debounce_timer:
            self._filter_debounce_timer.stop()
            self._filter_debounce_timer.deleteLater()
            self._filter_debounce_timer = None

        pattern = text.strip()

        # If empty, immediately clear filter (no debounce needed)
        if not pattern:
            self._filter_pending_pattern = None
            self._pending_ftp_loads_map.clear()
            self._set_all_items_visible(self.workspace_tree.invisibleRootItem())
            self._collapse_all(self.workspace_tree.invisibleRootItem())
            self._show_status_message("")
            return

        # Show typing indicator
        self._show_status_message("⌨ Saisie en cours...", timeout=0)

        # Debounce: wait 400ms after last keystroke before filtering
        self._filter_debounce_timer = QTimer()
        self._filter_debounce_timer.setSingleShot(True)
        self._filter_debounce_timer.timeout.connect(lambda: self._execute_filter(pattern))
        self._filter_debounce_timer.start(400)

    def _execute_filter(self, text: str):
        """Execute the actual filter after debounce delay."""
        import fnmatch

        self._filter_debounce_timer = None
        pattern = text.lower()

        # Add wildcards if not present
        if "*" not in pattern and "?" not in pattern:
            pattern = f"*{pattern}*"

        # Store pattern for async FTP loading
        self._filter_pending_pattern = pattern
        self._pending_ftp_loads_map.clear()

        # Check if we need to load lazy items
        has_lazy = self._has_lazy_items(self.workspace_tree.invisibleRootItem())
        if has_lazy:
            self._show_status_message("⏳ Chargement du workspace en cours...", timeout=0)

        # First, expand all items with dummy children to load content
        self._expand_all_lazy_items(self.workspace_tree.invisibleRootItem())

        # Small delay to let expansion handlers complete, then filter
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._apply_filter(pattern))

    def _expand_all_lazy_items(self, parent: QTreeWidgetItem):
        """Expand all items that have dummy children (trigger lazy loading)."""
        for i in range(parent.childCount()):
            child = parent.child(i)
            # Check if has dummy child
            if TreePopulator.has_dummy_child(child):
                child.setExpanded(True)  # Triggers _on_item_expanded
            # Recurse into children
            self._expand_all_lazy_items(child)

    def _apply_filter(self, pattern: str):
        """Apply filter pattern to tree after content is loaded."""
        # Check if pattern changed while loading
        if self._filter_pending_pattern != pattern:
            return  # Pattern changed, abort this filter

        # Expand any remaining lazy items (from newly loaded content)
        has_lazy = self._has_lazy_items(self.workspace_tree.invisibleRootItem())
        if has_lazy:
            self._expand_all_lazy_items(self.workspace_tree.invisibleRootItem())
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._apply_filter(pattern))
            return

        # Check for pending FTP loads
        if self._pending_ftp_loads_map:
            self._show_status_message(
                f"⏳ Connexion FTP en cours ({len(self._pending_ftp_loads_map)} restante(s))...",
                timeout=0
            )
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, lambda: self._apply_filter(pattern))
            return

        # All content loaded, apply filter
        self._filter_tree_recursive(self.workspace_tree.invisibleRootItem(), pattern)

        # Clear filter state and show result
        self._filter_pending_pattern = None
        match_count = self._count_visible_items(self.workspace_tree.invisibleRootItem())
        self._show_status_message(f"✓ Filtre appliqué: {match_count} élément(s) trouvé(s)")

    def _has_lazy_items(self, parent: QTreeWidgetItem) -> bool:
        """Check if any items still have dummy children."""
        for i in range(parent.childCount()):
            child = parent.child(i)
            if TreePopulator.has_dummy_child(child):
                return True
            if self._has_lazy_items(child):
                return True
        return False

    def _filter_tree_recursive(self, parent: QTreeWidgetItem, pattern: str) -> bool:
        """
        Recursively filter tree items.
        Returns True if this item or any descendant matches.
        """
        import fnmatch

        any_child_visible = False

        for i in range(parent.childCount()):
            child = parent.child(i)
            item_text = child.text(0).lower()

            # Skip dummy items
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "dummy":
                child.setHidden(True)
                continue

            # Check if this item matches
            item_matches = fnmatch.fnmatch(item_text, pattern)

            # Recursively check children
            child_matches = self._filter_tree_recursive(child, pattern)

            # Item is visible if it matches OR any child matches
            is_visible = item_matches or child_matches
            child.setHidden(not is_visible)

            # Expand items with matching children (to show the matches)
            if child_matches:
                child.setExpanded(True)

            if is_visible:
                any_child_visible = True

        return any_child_visible

    def _set_all_items_visible(self, parent: QTreeWidgetItem):
        """Make all items visible (clear filter)."""
        for i in range(parent.childCount()):
            child = parent.child(i)
            # Hide dummy items, show everything else
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "dummy":
                continue
            child.setHidden(False)
            self._set_all_items_visible(child)

    def _collapse_all(self, parent: QTreeWidgetItem):
        """Collapse all items."""
        for i in range(parent.childCount()):
            child = parent.child(i)
            child.setExpanded(False)
            self._collapse_all(child)

    def _count_visible_items(self, parent: QTreeWidgetItem) -> int:
        """Count visible (non-hidden) leaf items."""
        count = 0
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.isHidden():
                continue
            # Skip dummy items
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "dummy":
                continue
            # Count leaf items (no visible children) or recurse
            child_count = self._count_visible_items(child)
            if child_count == 0:
                count += 1  # Leaf item
            else:
                count += child_count
        return count

    def _show_status_message(self, message: str, timeout: int = 5000):
        """Show message in the main window status bar."""
        try:
            from PySide6.QtWidgets import QApplication
            main_window = QApplication.activeWindow()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(message, timeout)
        except Exception:
            pass

    # ==================== Tree Loading ====================

    def _load_workspaces(self):
        """Load all workspaces into tree."""
        self.workspace_tree.clear()
        workspaces = self.config_db.get_all_workspaces()
        for ws in workspaces:
            self._add_workspace_to_tree(ws)

        # Auto-select and expand if only one workspace
        if self.workspace_tree.topLevelItemCount() == 1:
            ws_item = self.workspace_tree.topLevelItem(0)
            self.workspace_tree.setCurrentItem(ws_item)
            self._auto_expand_workspace(ws_item)

    def _auto_expand_workspace(self, ws_item: QTreeWidgetItem):
        """Expand workspace with categories visible, collapse all others."""
        # Collapse all other workspaces and their descendants
        for i in range(self.workspace_tree.topLevelItemCount()):
            top_item = self.workspace_tree.topLevelItem(i)
            if top_item != ws_item:
                self._collapse_all(top_item)
                top_item.setExpanded(False)

        # Expand the selected workspace (triggers lazy loading via _on_item_expanded)
        ws_item.setExpanded(True)

        # Expand each category node (but not deeper)
        for i in range(ws_item.childCount()):
            child = ws_item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "resource_category":
                child.setExpanded(True)

    def _add_workspace_to_tree(self, workspace: Workspace):
        """Add a workspace to the tree."""
        ws_item = QTreeWidgetItem(self.workspace_tree)
        ws_icon = get_icon("workspace.png", size=16) or get_icon("folder.png", size=16)
        if ws_icon:
            ws_item.setIcon(0, ws_icon)

        # Show auto_connect indicator (handle missing attribute for old data)
        display_name = workspace.name
        auto_connect = getattr(workspace, 'auto_connect', False)
        if auto_connect:
            display_name = f"⚡ {workspace.name}"

        ws_item.setText(0, display_name)
        ws_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "workspace",
            "id": workspace.id,
            "workspace_obj": workspace
        })

        if auto_connect:
            ws_item.setToolTip(0, "Connexion automatique au démarrage")

        TreePopulator.add_dummy_child(ws_item)

    def _load_workspace_resources(self, ws_item: QTreeWidgetItem, workspace_id: str):
        """Load resources for a workspace, grouped by category."""
        # Databases
        ws_databases = self.config_db.get_workspace_databases_with_context(workspace_id)
        if ws_databases:
            db_cat = self._create_category_item(ws_item, "Databases", "database.png", len(ws_databases))
            for ws_db in ws_databases:
                db = ws_db.connection
                db_item = QTreeWidgetItem(db_cat)
                db_icon = get_database_icon(db.db_type, size=16)
                if db_icon:
                    db_item.setIcon(0, db_icon)
                db_item.setText(0, ws_db.display_name)
                db_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "database",
                    "id": db.id,
                    "database_name": ws_db.database_name,
                    "resource_obj": db,
                    "ws_database": ws_db
                })
                TreePopulator.add_dummy_child(db_item)

        # Queries
        queries = self.config_db.get_workspace_queries(workspace_id)
        if queries:
            q_cat = self._create_category_item(ws_item, "Queries", "query.png", len(queries))
            self._add_queries_grouped_by_category(q_cat, queries)

        # Scripts
        scripts = self.config_db.get_workspace_scripts(workspace_id)
        if scripts:
            s_cat = self._create_category_item(ws_item, "Scripts", "script.png", len(scripts))
            self._add_scripts_grouped_by_type(s_cat, scripts)

        # Jobs
        jobs = self.config_db.get_workspace_jobs(workspace_id)
        if jobs:
            j_cat = self._create_category_item(ws_item, "Jobs", "jobs.png", len(jobs))
            self._add_jobs_grouped_by_type(j_cat, jobs)

        # RootFolders
        ws_file_roots = self.config_db.get_workspace_file_roots_with_context(workspace_id)
        if ws_file_roots:
            rf_cat = self._create_category_item(ws_item, "RootFolders", "RootFolders.png", len(ws_file_roots))
            for ws_fr in ws_file_roots:
                fr = ws_fr.file_root
                fr_item = QTreeWidgetItem(rf_cat)
                fr_icon = get_icon("RootFolders.png", size=16)
                if fr_icon:
                    fr_item.setIcon(0, fr_icon)
                fr_item.setText(0, ws_fr.display_name)

                full_path = Path(fr.path)
                if ws_fr.subfolder_path:
                    full_path = full_path / ws_fr.subfolder_path

                fr_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "rootfolder",
                    "id": fr.id,
                    "subfolder_path": ws_fr.subfolder_path,
                    "full_path": str(full_path),
                    "resource_obj": fr,
                    "ws_file_root": ws_fr
                })
                TreePopulator.add_dummy_child(fr_item)

        # FTP Roots (with dummy child for expansion/navigation)
        ws_ftp_roots = self.config_db.get_workspace_ftp_roots_with_context(workspace_id)
        if ws_ftp_roots:
            ftp_cat = self._create_category_item(ws_item, "FTP", "ftp.png", len(ws_ftp_roots))
            for ws_ftp in ws_ftp_roots:
                ftp = ws_ftp.ftp_root
                ftp_item = QTreeWidgetItem(ftp_cat)
                ftp_icon = get_icon("ftp.png", size=16) or get_icon("database.png", size=16)
                if ftp_icon:
                    ftp_item.setIcon(0, ftp_icon)
                ftp_item.setText(0, ws_ftp.display_name)
                ftp_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "ftproot",
                    "id": ftp.id,
                    "subfolder_path": ws_ftp.subfolder_path,
                    "full_remote_path": ws_ftp.full_remote_path,
                    "resource_obj": ftp,
                    "ws_ftp_root": ws_ftp
                })
                TreePopulator.add_dummy_child(ftp_item)

    def _create_category_item(self, parent: QTreeWidgetItem, name: str, icon_name: str, count: int) -> QTreeWidgetItem:
        """Create a category grouping item under a workspace."""
        cat_item = QTreeWidgetItem(parent)
        icon = get_icon(icon_name, size=16)
        if icon:
            cat_item.setIcon(0, icon)
        cat_item.setText(0, f"{name} ({count})")
        cat_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "resource_category",
            "name": name
        })
        return cat_item

    def _add_queries_grouped_by_category(self, parent: QTreeWidgetItem, queries: list):
        """Add queries grouped by category."""
        categories = {}
        for q in queries:
            cat = q.category or "Uncategorized"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(q)

        for cat_name, cat_queries in sorted(categories.items()):
            cat_item = QTreeWidgetItem(parent)
            cat_icon = get_icon("folder.png", size=16)
            if cat_icon:
                cat_item.setIcon(0, cat_icon)
            cat_item.setText(0, f"{cat_name} ({len(cat_queries)})")
            cat_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "query_category",
                "name": cat_name
            })

            for query in cat_queries:
                q_item = QTreeWidgetItem(cat_item)
                q_icon = get_icon("query.png", size=16)
                if q_icon:
                    q_item.setIcon(0, q_icon)
                q_item.setText(0, query.name)
                q_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "query",
                    "id": query.id,
                    "resource_obj": query
                })

    def _add_scripts_grouped_by_type(self, parent: QTreeWidgetItem, scripts: list):
        """Add scripts grouped by type."""
        types = {}
        for s in scripts:
            stype = s.script_type or "Other"
            if stype not in types:
                types[stype] = []
            types[stype].append(s)

        for type_name, type_scripts in sorted(types.items()):
            type_item = QTreeWidgetItem(parent)
            type_icon = get_icon("folder.png", size=16)
            if type_icon:
                type_item.setIcon(0, type_icon)
            type_item.setText(0, f"{type_name} ({len(type_scripts)})")
            type_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "script_type",
                "name": type_name
            })

            for script in type_scripts:
                s_item = QTreeWidgetItem(type_item)
                s_icon = get_icon("script.png", size=16)
                if s_icon:
                    s_item.setIcon(0, s_icon)
                s_item.setText(0, script.name)
                s_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "script",
                    "id": script.id,
                    "resource_obj": script
                })

    def _add_jobs_grouped_by_type(self, parent: QTreeWidgetItem, jobs: list):
        """Add jobs grouped by type."""
        types = {}
        for j in jobs:
            jtype = j.job_type or "script"
            if jtype not in types:
                types[jtype] = []
            types[jtype].append(j)

        for type_name, type_jobs in sorted(types.items()):
            type_item = QTreeWidgetItem(parent)
            type_icon = get_icon("folder.png", size=16)
            if type_icon:
                type_item.setIcon(0, type_icon)
            type_item.setText(0, f"Jobs: {type_name} ({len(type_jobs)})")
            type_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "job_type",
                "name": type_name
            })

            for job in type_jobs:
                j_item = QTreeWidgetItem(type_item)
                j_icon = get_icon("jobs.png", size=16)
                if j_icon:
                    j_item.setIcon(0, j_icon)
                # Include status indicator
                status_icon = "✓" if job.enabled else "✗"
                j_item.setText(0, f"{status_icon} {job.name}")
                j_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "job",
                    "id": job.id,
                    "resource_obj": job
                })

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion (lazy loading)."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if not TreePopulator.has_dummy_child(item):
            return

        TreePopulator.remove_dummy_child(item)
        item_type = data.get("type", "")

        if item_type == "workspace":
            self._load_workspace_resources(item, data["id"])
        elif item_type == "database":
            self._load_database_schema(item, data)
        elif item_type == "rootfolder":
            self._load_rootfolder_contents(item, data)
        elif item_type == "ftproot":
            self._load_ftproot_contents(item, data)
        elif item_type == "remote_folder":
            self._load_remote_folder_contents(item, data)
        elif item_type == "folder":
            # Load folder contents with file counts (same as RootFolderManager)
            folder_path = data.get("path")
            if folder_path:
                self._load_folder_contents(item, Path(folder_path), recursive=False)
        elif item_type in ["tables_folder", "views_folder", "procedures_folder", "functions_folder"]:
            pass  # Database schema folders - already loaded

    def _load_database_schema(self, db_item: QTreeWidgetItem, data: dict):
        """
        Load database schema by delegating to DatabaseManager.

        This ensures consistent behavior (loading indicator, connection handling)
        between DatabaseManager and WorkspaceManager.
        """
        if not self._database_manager:
            logger.warning("WorkspaceManager: No database_manager available")
            return

        db_conn = data.get("resource_obj")
        database_name = data.get("database_name")

        if not db_conn:
            logger.warning(f"WorkspaceManager: No resource_obj in data")
            return

        # Delegate entirely to DatabaseManager for consistent behavior
        success = self._database_manager.load_specific_database_schema(
            parent_item=db_item,
            db_conn=db_conn,
            database_name=database_name or db_conn.name
        )

        if not success:
            DialogHelper.warning(f"Could not load schema for: {db_conn.name}")

    def _load_folder_contents(self, parent_item: QTreeWidgetItem, folder_path: Path, recursive: bool = False):
        """Load folder contents using tree_helpers (no plugin dependency)."""
        # Use tree_helpers directly - no dependency on RootFolderManager
        populate_tree_with_local_folder(parent_item, folder_path, recursive=recursive)

    def _load_rootfolder_contents(self, parent_item: QTreeWidgetItem, data: dict):
        """Load rootfolder contents."""
        full_path = data.get("full_path")
        if not full_path:
            return

        folder_path = Path(full_path)
        if not folder_path.exists():
            return

        self._load_folder_contents(parent_item, folder_path, recursive=False)

    def _load_ftproot_contents(self, parent_item: QTreeWidgetItem, data: dict):
        """
        Load FTP root contents by delegating to FTPRootManager.

        Connects if needed, then loads remote folder contents.
        """
        if not self._ftproot_manager:
            logger.warning("WorkspaceManager: No ftproot_manager available")
            return

        ftp_root = data.get("resource_obj")
        if not ftp_root:
            return

        ftp_root_id = ftp_root.id
        remote_path = data.get("full_remote_path", ftp_root.initial_path)

        # Check if already connected
        if ftp_root_id not in self._ftproot_manager._connections:
            # Need to connect first - delegate to FTPRootManager
            self._ftproot_manager._connect_ftp_root(ftp_root)
            # Connection is async, contents will load when connected
            # Store pending load info for this FTP root
            self._pending_ftp_loads_map[ftp_root_id] = (parent_item, remote_path)
            return

        # Already connected - load contents
        self._load_ftp_folder_from_manager(parent_item, ftp_root_id, remote_path)

    def _load_remote_folder_contents(self, parent_item: QTreeWidgetItem, data: dict):
        """Load remote FTP folder contents."""
        if not self._ftproot_manager:
            return

        ftp_root_id = data.get("ftproot_id")
        remote_path = data.get("path")

        if ftp_root_id and remote_path:
            self._load_ftp_folder_from_manager(parent_item, ftp_root_id, remote_path)

    def _load_ftp_folder_from_manager(self, parent_item: QTreeWidgetItem, ftp_root_id: str, remote_path: str):
        """Load FTP folder contents by delegating to FTPRootManager."""
        if not self._ftproot_manager:
            logger.warning("WorkspaceManager: No ftproot_manager available")
            return

        # Delegate to FTPRootManager's public API
        success = self._ftproot_manager.load_folder_to_tree(ftp_root_id, remote_path, parent_item)

        if not success:
            DialogHelper.warning("Erreur de chargement FTP. Verifiez la connexion.", parent=self)

    def _on_ftp_connection_established(self, ftp_root_id: str):
        """Handle FTP connection established - process pending load if any."""
        # Check if we have a pending load for this FTP root
        if ftp_root_id not in self._pending_ftp_loads_map:
            return

        # Get and remove pending load info
        parent_item, remote_path = self._pending_ftp_loads_map.pop(ftp_root_id)

        # Load the FTP folder contents
        self._load_ftp_folder_from_manager(parent_item, ftp_root_id, remote_path)

    def _on_ftp_connection_failed(self, ftp_root_id: str):
        """Handle FTP connection failure - remove from pending list."""
        if ftp_root_id in self._pending_ftp_loads_map:
            self._pending_ftp_loads_map.pop(ftp_root_id)

    def _on_query_saved_from_workspace(self):
        """Refresh current workspace when a query is saved (auto-linked)."""
        if self._current_workspace_id:
            self.refresh_workspace(self._current_workspace_id, select_and_expand=False)

    def _add_tree_item(self, parent: QTreeWidgetItem, text: list, data: dict) -> QTreeWidgetItem:
        """Callback for TreePopulator."""
        item = QTreeWidgetItem(parent)
        item.setText(0, text[0])
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        return item

    # ==================== Tree Event Handlers ====================

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        """Handle click - show details."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        if item_type == "workspace":
            ws = data["workspace_obj"]
            self._current_workspace_id = ws.id
            self._current_item = ws
            self.object_viewer.show_details(
                name=ws.name,
                obj_type="Workspace",
                description=ws.description or "",
                created=ws.created_at or "",
                updated=ws.updated_at or ""
            )
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab
            self._auto_expand_workspace(item)

        elif item_type == "database":
            db = data.get("resource_obj")
            db_name = data.get("database_name", "")
            if db_name:
                self.object_viewer.show_details(db_name, f"Database on {db.name}", db.description or "")
            else:
                self.object_viewer.show_details(db.name, f"Server ({db.db_type})", db.description or "")
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type == "query":
            query = data["resource_obj"]
            self.object_viewer.show_details(query.name, "Query", query.description or "")
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type == "script":
            script = data["resource_obj"]
            if self._scripts_manager:
                self._scripts_manager.show_script(script, target_viewer=self.object_viewer)
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type == "job":
            job = data["resource_obj"]
            if self._jobs_manager:
                self._jobs_manager.show_job(job, target_viewer=self.object_viewer)
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type == "rootfolder":
            fr = data.get("resource_obj")
            full_path = data.get("full_path", "")
            subfolder = data.get("subfolder_path", "")
            if subfolder:
                self.object_viewer.show_details(Path(subfolder).name, "Subfolder", full_path)
            else:
                self.object_viewer.show_details(fr.name or fr.path, "RootFolder", fr.path)
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type == "ftproot":
            ftp = data.get("resource_obj")
            subfolder = data.get("subfolder_path", "")
            remote_path = data.get("full_remote_path", "")
            protocol = ftp.protocol.upper() if ftp else "FTP"
            if subfolder:
                self.object_viewer.show_details(Path(subfolder).name, f"{protocol} Subfolder", remote_path)
            else:
                display_name = ftp.name or f"{ftp.host}:{ftp.port}" if ftp else "FTP"
                self.object_viewer.show_details(display_name, f"{protocol} Connection", f"{ftp.host}:{ftp.port}" if ftp else "")
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type == "folder":
            path = data.get("path", "")
            if self._rootfolder_manager:
                self._rootfolder_manager.show_folder(
                    Path(path).name, path, target_viewer=self.object_viewer
                )
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type == "file":
            file_path = data.get("path")
            if file_path and self._rootfolder_manager:
                self._rootfolder_manager.show_file(Path(file_path), target_viewer=self.object_viewer)
                self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type in ["table", "view"]:
            name = data.get("name", "")
            db_name = data.get("db_name", "")
            self.object_viewer.show_details(name, item_type.title(), f"Database: {db_name}" if db_name else "")
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

        elif item_type in ["resource_category", "query_category", "script_type", "job_type", "tables_folder", "views_folder"]:
            name = data.get("name", item_type)
            self.object_viewer.show_details(name, item_type.replace("_", " ").title(), "")
            self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab

    def _on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click - display content or expand."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        if item_type in ["table", "view"]:
            # Use DatabaseManager method with QueryTab in WorkspaceManager's tab_widget
            if self._database_manager:
                self._database_manager._generate_select_query(
                    data, limit=100, target_tab_widget=self.tab_widget,
                    workspace_id=self._current_workspace_id
                )
        elif item_type == "query":
            # Execute saved query in workspace tab
            query_obj = data.get("resource_obj")
            if query_obj and self._database_manager:
                self._database_manager.execute_saved_query(
                    query_obj, target_tab_widget=self.tab_widget,
                    workspace_id=self._current_workspace_id
                )
        elif item_type == "file":
            file_path = data.get("path")
            if file_path and self._rootfolder_manager:
                self._rootfolder_manager.show_file(Path(file_path), target_viewer=self.object_viewer)
                self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab
        elif item_type == "remote_file":
            # Preview remote FTP file
            if self._ftproot_manager:
                self._ftproot_manager._preview_remote_file(data, target_viewer=self.object_viewer)
                self.tab_widget.setCurrentIndex(0)  # Switch to Preview tab
        elif item_type in ["workspace", "database", "rootfolder", "ftproot", "remote_folder",
                           "folder", "tables_folder", "views_folder", "query_category", "script_type",
                           "resource_category"]:
            item.setExpanded(not item.isExpanded())

    # ==================== Context Menu ====================

    def _on_tree_context_menu(self, position):
        """Show context menu."""
        item = self.workspace_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")
        menu = QMenu(self)

        if item_type == "workspace":
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self._edit_workspace_item(item, data))
            menu.addAction(edit_action)

            menu.addSeparator()

            delete_action = QAction("Delete Workspace", self)
            delete_action.triggered.connect(lambda: self._delete_workspace_item(data["id"]))
            menu.addAction(delete_action)

            menu.addSeparator()

            export_action = QAction("Export Workspace...", self)
            export_action.triggered.connect(lambda: self._export_workspace(data["id"], data.get("workspace_obj").name))
            menu.addAction(export_action)

        elif item_type == "script":
            # Use ScriptsManager's context actions
            if self._scripts_manager:
                script = data.get("resource_obj")
                if script:
                    script_actions = self._scripts_manager.get_script_context_actions(
                        script, self, target_viewer=self.object_viewer
                    )
                    for action in script_actions:
                        menu.addAction(action)
                    menu.addSeparator()

            remove_action = QAction("Remove from Workspace", self)
            remove_action.triggered.connect(lambda: self._remove_resource_from_workspace(item, data))
            menu.addAction(remove_action)

        elif item_type == "job":
            # Use JobsManager's context actions
            if self._jobs_manager:
                job = data.get("resource_obj")
                if job:
                    job_actions = self._jobs_manager.get_job_context_actions(
                        job, self, target_viewer=self.object_viewer
                    )
                    for action in job_actions:
                        menu.addAction(action)
                    menu.addSeparator()

            remove_action = QAction("Remove from Workspace", self)
            remove_action.triggered.connect(lambda: self._remove_resource_from_workspace(item, data))
            menu.addAction(remove_action)

        elif item_type == "query":
            # Execute query action
            if self._database_manager:
                query_obj = data.get("resource_obj")
                if query_obj:
                    exec_action = QAction("Execute / Exécuter", self)
                    ws_id = self._current_workspace_id
                    exec_action.triggered.connect(
                        lambda checked, q=query_obj, w=ws_id: self._database_manager.execute_saved_query(
                            q, target_tab_widget=self.tab_widget, workspace_id=w
                        )
                    )
                    menu.addAction(exec_action)
                    menu.addSeparator()

            remove_action = QAction("Remove from Workspace", self)
            remove_action.triggered.connect(lambda: self._remove_resource_from_workspace(item, data))
            menu.addAction(remove_action)

        elif item_type in ["database", "rootfolder"]:
            remove_action = QAction("Remove from Workspace", self)
            remove_action.triggered.connect(lambda: self._remove_resource_from_workspace(item, data))
            menu.addAction(remove_action)

        elif item_type in ["table", "view"]:
            # Use DatabaseManager methods with WorkspaceManager's tab_widget
            if self._database_manager:
                ws_id = self._current_workspace_id

                # SELECT * action
                select_all_action = QAction("SELECT *", self)
                select_all_action.triggered.connect(
                    lambda checked, d=data, w=ws_id: self._database_manager._generate_select_query(
                        d, limit=None, target_tab_widget=self.tab_widget, workspace_id=w
                    )
                )
                menu.addAction(select_all_action)

                # SELECT TOP 100 action
                select_top_action = QAction("SELECT TOP 100 *", self)
                select_top_action.triggered.connect(
                    lambda checked, d=data, w=ws_id: self._database_manager._generate_select_query(
                        d, limit=100, target_tab_widget=self.tab_widget, workspace_id=w
                    )
                )
                menu.addAction(select_top_action)

                # SELECT COLUMNS action
                select_cols_action = QAction("SELECT COLUMNS...", self)
                select_cols_action.triggered.connect(
                    lambda checked, d=data, w=ws_id: self._database_manager._generate_select_columns_query(
                        d, target_tab_widget=self.tab_widget, workspace_id=w
                    )
                )
                menu.addAction(select_cols_action)

                menu.addSeparator()

                # Edit Code for views only
                if item_type == "view":
                    edit_code_action = QAction("Edit Code (ALTER VIEW)", self)
                    edit_code_action.triggered.connect(
                        lambda checked, d=data, w=ws_id: self._database_manager._load_view_code(
                            d, target_tab_widget=self.tab_widget, workspace_id=w
                        )
                    )
                    menu.addAction(edit_code_action)
                    menu.addSeparator()

                # Distribution Analysis (opens dialog, works from anywhere)
                dist_action = QAction("Distribution Analysis", self)
                dist_action.triggered.connect(
                    lambda checked, d=data: self._database_manager._show_distribution_analysis(d)
                )
                menu.addAction(dist_action)

        elif item_type == "procedure":
            # Stored procedure context menu - delegate to DatabaseManager
            if self._database_manager:
                ws_id = self._current_workspace_id

                view_code_action = QAction("View Code", self)
                view_code_action.triggered.connect(
                    lambda checked, d=data, w=ws_id: self._database_manager._load_routine_code(
                        d, target_tab_widget=self.tab_widget, workspace_id=w
                    )
                )
                menu.addAction(view_code_action)

                exec_action = QAction("Generate EXEC Template", self)
                exec_action.triggered.connect(
                    lambda checked, d=data, w=ws_id: self._database_manager._generate_exec_template(
                        d, target_tab_widget=self.tab_widget, workspace_id=w
                    )
                )
                menu.addAction(exec_action)

        elif item_type == "function":
            # Function context menu - delegate to DatabaseManager
            if self._database_manager:
                ws_id = self._current_workspace_id

                view_code_action = QAction("View Code", self)
                view_code_action.triggered.connect(
                    lambda checked, d=data, w=ws_id: self._database_manager._load_routine_code(
                        d, target_tab_widget=self.tab_widget, workspace_id=w
                    )
                )
                menu.addAction(view_code_action)

                select_action = QAction("Generate SELECT", self)
                select_action.triggered.connect(
                    lambda checked, d=data, w=ws_id: self._database_manager._generate_select_function(
                        d, target_tab_widget=self.tab_widget, workspace_id=w
                    )
                )
                menu.addAction(select_action)

        elif item_type == "file":
            # Use RootFolderManager's context actions
            if self._rootfolder_manager:
                file_actions = self._rootfolder_manager.get_file_context_actions(
                    data, self, target_viewer=self.object_viewer
                )
                for action in file_actions:
                    menu.addAction(action)

        if menu.actions():
            menu.exec(self.workspace_tree.viewport().mapToGlobal(position))

    def _remove_resource_from_workspace(self, item: QTreeWidgetItem, data: dict):
        """Remove resource from workspace."""
        # Traverse up to find the workspace ancestor (through category levels)
        workspace_id = None
        ancestor = item.parent()
        while ancestor:
            ancestor_data = ancestor.data(0, Qt.ItemDataRole.UserRole)
            if ancestor_data and ancestor_data.get("type") == "workspace":
                workspace_id = ancestor_data.get("id")
                break
            ancestor = ancestor.parent()

        if not workspace_id:
            return
        item_type = data.get("type")
        resource_id = data.get("id")

        if not workspace_id or not resource_id:
            return

        if not DialogHelper.confirm(f"Remove this {item_type} from the workspace?"):
            return

        try:
            if item_type == "database":
                self.config_db.remove_database_from_workspace(workspace_id, resource_id)
            elif item_type == "query":
                self.config_db.remove_query_from_workspace(workspace_id, resource_id)
            elif item_type == "rootfolder":
                self.config_db.remove_file_root_from_workspace(workspace_id, resource_id)
            elif item_type == "ftproot":
                self.config_db.remove_ftp_root_from_workspace(workspace_id, resource_id)
            elif item_type == "script":
                self.config_db.remove_script_from_workspace(workspace_id, resource_id)
            elif item_type == "job":
                self.config_db.remove_job_from_workspace(workspace_id, resource_id)

            direct_parent = item.parent()
            if direct_parent:
                direct_parent.removeChild(item)
                # Remove empty category node
                cat_data = direct_parent.data(0, Qt.ItemDataRole.UserRole)
                if cat_data and cat_data.get("type") == "resource_category" and direct_parent.childCount() == 0:
                    grandparent = direct_parent.parent()
                    if grandparent:
                        grandparent.removeChild(direct_parent)
            logger.info(f"Removed {item_type} {resource_id} from workspace {workspace_id}")

        except Exception as e:
            logger.error(f"Error removing resource: {e}")
            DialogHelper.error("Error removing resource", details=str(e))

    # ==================== Workspace CRUD ====================

    def _new_workspace(self):
        """Create a new workspace."""
        from ..widgets.edit_dialogs import EditWorkspaceDialog

        from PySide6.QtWidgets import QDialog
        dialog = EditWorkspaceDialog(parent=self, is_new=True)
        if dialog.exec() == QDialog.Accepted:
            name, description, auto_connect = dialog.get_values()
            if name:
                ws = Workspace(
                    id=str(uuid.uuid4()),
                    name=name,
                    description=description,
                    auto_connect=auto_connect
                )
                if self.config_db.add_workspace(ws):
                    # If auto_connect enabled, disable on other workspaces
                    if auto_connect:
                        self.config_db.set_workspace_auto_connect(ws.id, True)
                    self._refresh()
                    DialogHelper.info(f"Workspace '{name}' créé")
                else:
                    DialogHelper.warning("Échec de création. Le nom existe peut-être déjà.")

    def _edit_workspace(self):
        """Edit selected workspace."""
        selected = self.workspace_tree.selectedItems()
        if not selected:
            DialogHelper.warning("Please select a workspace")
            return

        data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "workspace":
            self._edit_workspace_item(selected[0], data)

    def _edit_workspace_item(self, item: QTreeWidgetItem, data: dict):
        """Edit workspace dialog."""
        from ..widgets.edit_dialogs import EditWorkspaceDialog

        ws = data.get("workspace_obj")
        if not ws:
            return

        dialog = EditWorkspaceDialog(
            parent=self,
            name=ws.name,
            description=ws.description or "",
            auto_connect=getattr(ws, 'auto_connect', False),
            is_new=False
        )

        from PySide6.QtWidgets import QDialog
        if dialog.exec() == QDialog.Accepted:
            name, description, auto_connect = dialog.get_values()
            if name:
                ws.name = name
                ws.description = description
                ws.auto_connect = auto_connect

                if self.config_db.update_workspace(ws):
                    # If auto_connect changed, update accordingly
                    if auto_connect:
                        self.config_db.set_workspace_auto_connect(ws.id, True)
                    self._refresh()
                    DialogHelper.info("Workspace mis à jour")
                else:
                    DialogHelper.warning("Échec de mise à jour")

    def _delete_workspace(self):
        """Delete selected workspace."""
        selected = self.workspace_tree.selectedItems()
        if not selected:
            DialogHelper.warning("Please select a workspace")
            return

        data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "workspace":
            self._delete_workspace_item(data["id"])

    def _delete_workspace_item(self, workspace_id: str):
        """Delete workspace by ID."""
        if not DialogHelper.confirm("Delete this workspace?\n\n(Resources will not be deleted)"):
            return

        try:
            self.config_db.delete_workspace(workspace_id)
            self._refresh()
            DialogHelper.info("Workspace deleted")
        except Exception as e:
            logger.error(f"Error deleting workspace: {e}")
            DialogHelper.error("Error deleting workspace", details=str(e))

    def _refresh(self):
        """Refresh the tree."""
        self._load_workspaces()
        self.object_viewer.clear()

    def _find_workspace_item(self, workspace_id: str) -> Optional[QTreeWidgetItem]:
        """Find a workspace item in the tree by ID."""
        for i in range(self.workspace_tree.topLevelItemCount()):
            item = self.workspace_tree.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "workspace" and data.get("id") == workspace_id:
                return item
        return None

    def refresh_workspace(self, workspace_id: str, select_and_expand: bool = True):
        """
        Refresh a specific workspace in the tree.

        Called when a resource is added/removed from a workspace via the menu builder.

        Args:
            workspace_id: ID of the workspace to refresh
            select_and_expand: If True, select and expand the workspace after refresh
        """
        ws_item = self._find_workspace_item(workspace_id)
        if not ws_item:
            # Workspace not found - might be new, do full refresh
            self._load_workspaces()
            ws_item = self._find_workspace_item(workspace_id)

        if ws_item:
            # Collapse, clear children, and reload
            ws_item.setExpanded(False)
            # Remove all children using Qt's takeChildren()
            ws_item.takeChildren()
            TreePopulator.add_dummy_child(ws_item)

            if select_and_expand:
                # Select and expand the workspace
                self.workspace_tree.setCurrentItem(ws_item)
                ws_item.setExpanded(True)  # This triggers _on_item_expanded

    # ==================== Import/Export ====================

    def _export_workspace(self, workspace_id: str, workspace_name: str):
        """Export workspace to JSON file."""
        try:
            default_filename = f"{workspace_name.replace(' ', '_')}_export.json"
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Export Workspace", default_filename,
                "JSON Files (*.json);;All Files (*)"
            )
            if not filepath:
                return

            export_data = export_workspace_to_json(
                workspace_id,
                include_credentials=False,
                include_databases=True,
                include_rootfolders=True,
                include_queries=True,
                include_scripts=True,
                include_jobs=True
            )
            save_export_to_file(export_data, filepath)

            summary = get_export_summary(export_data)
            DialogHelper.info(f"Export successful!\n\n{summary}\n\nFile: {filepath}")

        except Exception as e:
            logger.error(f"Export failed: {e}")
            DialogHelper.error(f"Export failed: {str(e)}")

    def _import_workspace(self):
        """Import workspace from JSON file."""
        try:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Import Workspace", "",
                "JSON Files (*.json);;All Files (*)"
            )
            if not filepath:
                return

            import_data = load_import_from_file(filepath)

            export_type = import_data.get("export_type", "")
            if export_type not in ["workspace", "connections"]:
                DialogHelper.error(f"Unsupported export type: {export_type}")
                return

            ws_name = import_data.get("workspace", {}).get("name", "Imported Workspace")
            conflict = check_workspace_conflict(ws_name)

            mode = ImportConflictMode.CREATE_NEW
            if conflict:
                from PySide6.QtWidgets import QMessageBox
                result = QMessageBox.question(
                    self, "Workspace Exists",
                    f"Workspace '{ws_name}' already exists.\n\nCreate new or merge?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                if result == QMessageBox.StandardButton.Cancel:
                    return
                elif result == QMessageBox.StandardButton.No:
                    mode = ImportConflictMode.MERGE

            result = import_workspace_from_json(import_data, mode)
            summary = get_import_summary(result)
            DialogHelper.info(f"Import successful!\n\n{summary}")
            self._refresh()

        except Exception as e:
            logger.error(f"Import failed: {e}")
            DialogHelper.error(f"Import failed: {str(e)}")
