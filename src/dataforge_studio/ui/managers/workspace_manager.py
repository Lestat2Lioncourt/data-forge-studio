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
from PySide6.QtGui import QAction, QFont

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.form_builder import FormBuilder
from ..widgets.tree_populator import TreePopulator
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Workspace, Script
from ...database.models.workspace_resource import WorkspaceFileRoot, WorkspaceDatabase
from ...utils.image_loader import get_icon, get_database_icon

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
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(6)  # Larger handle for easier grabbing
        self.main_splitter.setChildrenCollapsible(False)  # Prevent collapsing children

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
        self.workspace_tree.setExpandsOnDoubleClick(False)  # We handle double-click ourselves
        self.workspace_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.workspace_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.workspace_tree.itemClicked.connect(self._on_tree_click)
        self.workspace_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.workspace_tree.itemExpanded.connect(self._on_item_expanded)
        left_layout.addWidget(self.workspace_tree)

        self.main_splitter.addWidget(left_widget)

        # Right panel: Details + Content viewer
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Details form (compact)
        self.details_form_builder = FormBuilder(title="Details") \
            .add_field("Name:", "name") \
            .add_field("Type:", "type") \
            .add_field("Description:", "description") \
            .add_field("Created:", "created") \
            .add_field("Updated:", "updated")

        details_form_widget = self.details_form_builder.build()
        right_layout.addWidget(details_form_widget, stretch=0)

        # Content viewer header
        from PySide6.QtWidgets import QStackedWidget, QTextEdit
        content_header = QHBoxLayout()
        self.content_label = QLabel("Content")
        self.content_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        content_header.addWidget(self.content_label)
        content_header.addStretch()
        right_layout.addLayout(content_header)

        # Stacked widget for different content types
        self.content_stack = QStackedWidget()

        # Page 0: Welcome/placeholder
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.addStretch()
        welcome_label = QLabel(tr("workspace_select_item") if hasattr(tr, '__call__') else "Select an item to view its content")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("color: gray; font-style: italic;")
        welcome_layout.addWidget(welcome_label)
        welcome_layout.addStretch()
        self.content_stack.addWidget(welcome_widget)

        # Page 1: Data grid (for CSV, Excel, JSON table, query results)
        from ..widgets.custom_datagridview import CustomDataGridView
        self.content_grid = CustomDataGridView()
        self.content_stack.addWidget(self.content_grid)

        # Page 2: Text viewer (for text files, logs, raw JSON)
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setFont(QFont("Consolas", 10))
        self.content_stack.addWidget(self.content_text)

        right_layout.addWidget(self.content_stack, stretch=4)

        self.main_splitter.addWidget(right_widget)

        # Set splitter proportions (left 30%, right 70%)
        self.main_splitter.setSizes([350, 850])

        # Allow both panels to be resized freely
        self.main_splitter.setStretchFactor(0, 0)  # Left panel: don't auto-stretch
        self.main_splitter.setStretchFactor(1, 1)  # Right panel: takes remaining space

        layout.addWidget(self.main_splitter)

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
            db_icon = get_database_icon(db.db_type, size=16)
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

        # Load scripts grouped by type
        scripts = self.config_db.get_workspace_scripts(workspace_id)
        if scripts:
            self._add_scripts_grouped_by_type(ws_item, scripts)

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

    def _add_scripts_grouped_by_type(self, parent_item: QTreeWidgetItem, scripts: list):
        """Add scripts to tree grouped by script_type."""
        # Group scripts by type
        types = {}
        for s in scripts:
            script_type = s.script_type or "other"
            if script_type not in types:
                types[script_type] = []
            types[script_type].append(s)

        # Create type nodes
        for type_name in sorted(types.keys()):
            type_scripts = types[type_name]

            # If only one type, add scripts directly (no type node)
            if len(types) == 1:
                for s in type_scripts:
                    self._add_script_item(parent_item, s)
            else:
                # Create type node
                type_item = QTreeWidgetItem(parent_item)
                type_icon = get_icon("folder.png", size=16)
                if type_icon:
                    type_item.setIcon(0, type_icon)
                type_item.setText(0, f"{type_name} ({len(type_scripts)})")
                type_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "script_type",
                    "name": type_name
                })

                # Add scripts under type
                for s in type_scripts:
                    self._add_script_item(type_item, s)

    def _add_script_item(self, parent_item: QTreeWidgetItem, script: Script) -> QTreeWidgetItem:
        """Add a single script item to the tree."""
        s_item = QTreeWidgetItem(parent_item)
        s_icon = get_icon("scripts.png", size=16) or get_icon("python.png", size=16)
        if s_icon:
            s_item.setIcon(0, s_icon)
        s_item.setText(0, script.name)
        s_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "script",
            "id": script.id,
            "resource_obj": script
        })
        return s_item

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
        elif item_type == "script":
            self._show_script_details(data["resource_obj"])
        elif item_type == "script_type":
            self._show_script_type_details(data)
        elif item_type == "rootfolder":
            self._show_rootfolder_details(data)
        elif item_type == "folder":
            self._show_folder_details(data)
        elif item_type == "file":
            self._show_file_details(data)
        # Database schema items (loaded from DatabaseManager)
        elif item_type == "table":
            self._show_table_details(data)
        elif item_type == "view":
            self._show_view_details(data)
        elif item_type == "procedure":
            self._show_procedure_details(data)
        elif item_type == "function":
            self._show_function_details(data)
        elif item_type == "column":
            self._show_column_details(data)
        elif item_type in ("tables_folder", "views_folder", "procedures_folder", "functions_folder"):
            self._show_schema_folder_details(data, item_type)

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

    def _show_script_details(self, script: Script):
        """Show script details"""
        self.details_form_builder.set_value("name", script.name)
        self.details_form_builder.set_value("type", f"Script ({script.script_type})")
        self.details_form_builder.set_value("description", script.description or "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_script_type_details(self, data: dict):
        """Show script type folder details"""
        type_name = data.get("name", "")
        self.details_form_builder.set_value("name", type_name)
        self.details_form_builder.set_value("type", "Script Type")
        self.details_form_builder.set_value("description", "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_table_details(self, data: dict):
        """Show table details"""
        table_name = data.get("name", "")
        db_name = data.get("db_name", "")
        self.details_form_builder.set_value("name", table_name)
        self.details_form_builder.set_value("type", "Table")
        self.details_form_builder.set_value("description", f"Database: {db_name}" if db_name else "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_view_details(self, data: dict):
        """Show view details"""
        view_name = data.get("name", "")
        db_name = data.get("db_name", "")
        self.details_form_builder.set_value("name", view_name)
        self.details_form_builder.set_value("type", "View")
        self.details_form_builder.set_value("description", f"Database: {db_name}" if db_name else "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_procedure_details(self, data: dict):
        """Show stored procedure details"""
        proc_name = data.get("proc_name", data.get("name", ""))
        schema = data.get("schema", "")
        db_name = data.get("db_name", "")
        full_name = f"{schema}.{proc_name}" if schema else proc_name
        self.details_form_builder.set_value("name", full_name)
        self.details_form_builder.set_value("type", "Stored Procedure")
        self.details_form_builder.set_value("description", f"Database: {db_name}" if db_name else "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_function_details(self, data: dict):
        """Show function details"""
        func_name = data.get("func_name", data.get("name", ""))
        schema = data.get("schema", "")
        db_name = data.get("db_name", "")
        func_type = data.get("func_type", "")
        full_name = f"{schema}.{func_name}" if schema else func_name
        self.details_form_builder.set_value("name", full_name)
        self.details_form_builder.set_value("type", f"Function ({func_type})" if func_type else "Function")
        self.details_form_builder.set_value("description", f"Database: {db_name}" if db_name else "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_column_details(self, data: dict):
        """Show column details"""
        col_name = data.get("name", "")
        col_type = data.get("column_type", "")
        table_name = data.get("table_name", "")
        self.details_form_builder.set_value("name", col_name)
        self.details_form_builder.set_value("type", f"Column ({col_type})" if col_type else "Column")
        self.details_form_builder.set_value("description", f"Table: {table_name}" if table_name else "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _show_schema_folder_details(self, data: dict, folder_type: str):
        """Show schema folder details (Tables, Views, Procedures, Functions)"""
        db_name = data.get("db_name", "")
        type_map = {
            "tables_folder": "Tables Folder",
            "views_folder": "Views Folder",
            "procedures_folder": "Procedures Folder",
            "functions_folder": "Functions Folder"
        }
        self.details_form_builder.set_value("name", type_map.get(folder_type, folder_type))
        self.details_form_builder.set_value("type", "Schema Folder")
        self.details_form_builder.set_value("description", f"Database: {db_name}" if db_name else "")
        self.details_form_builder.set_value("created", "")
        self.details_form_builder.set_value("updated", "")

    def _on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item - display content in viewer"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        # Database items - execute query and show results
        if item_type in ["table", "view"]:
            self._execute_select_query(data, limit=100)

        elif item_type in ["procedure", "function"]:
            self._show_routine_code(data)

        # File items - display content
        elif item_type == "file":
            file_path = data.get("path")
            if file_path:
                self._display_file_content(Path(file_path))

        # Expandable items - toggle expansion
        elif item_type in ["workspace", "database", "rootfolder", "folder",
                           "tables_folder", "views_folder", "procedures_folder", "functions_folder"]:
            item.setExpanded(not item.isExpanded())

    def _on_tree_context_menu(self, position):
        """Show context menu for tree item"""
        item = self.workspace_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")
        menu = QMenu(self)

        if item_type == "workspace":
            # Workspace context menu
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self._edit_workspace_item(item, data))
            menu.addAction(edit_action)

            menu.addSeparator()

            delete_action = QAction("Delete Workspace", self)
            delete_action.triggered.connect(lambda: self._delete_workspace_item(data["id"]))
            menu.addAction(delete_action)

        elif item_type in ["database", "query", "rootfolder", "script"]:
            # Resource context menu - remove from workspace
            remove_action = QAction("Remove from Workspace", self)
            remove_action.triggered.connect(lambda: self._remove_resource_from_workspace(item, data))
            menu.addAction(remove_action)

        # Database schema items - execute in workspace
        elif item_type in ["table", "view"]:
            # SELECT * action
            select_all_action = QAction("SELECT *", self)
            select_all_action.triggered.connect(
                lambda checked, d=data: self._execute_select_query(d, limit=None)
            )
            menu.addAction(select_all_action)

            # SELECT TOP 100 action
            select_top_action = QAction("SELECT TOP 100 *", self)
            select_top_action.triggered.connect(
                lambda checked, d=data: self._execute_select_query(d, limit=100)
            )
            menu.addAction(select_top_action)

            # SELECT COLUMNS action (formatted with column names)
            select_cols_action = QAction("SELECT COLUMNS...", self)
            select_cols_action.triggered.connect(
                lambda checked, d=data: self._generate_select_columns_query(d)
            )
            menu.addAction(select_cols_action)

            menu.addSeparator()

            # View Code for views only
            if item_type == "view":
                view_code_action = QAction("📄 View Code", self)
                view_code_action.triggered.connect(
                    lambda checked, d=data: self._show_routine_code(d)
                )
                menu.addAction(view_code_action)
                menu.addSeparator()

            # Distribution Analysis action (dialog)
            if self._database_manager:
                dist_action = QAction("📊 Distribution Analysis", self)
                dist_action.triggered.connect(
                    lambda checked, d=data: self._database_manager._show_distribution_analysis(d)
                )
                menu.addAction(dist_action)

        elif item_type in ["procedure", "function"]:
            # View code
            view_code_action = QAction("📄 View Code", self)
            view_code_action.triggered.connect(
                lambda checked, d=data: self._show_routine_code(d)
            )
            menu.addAction(view_code_action)

        # File items - display in workspace
        elif item_type == "file":
            file_path = data.get("path")
            if file_path:
                # Open file action (display in viewer)
                open_action = QAction(tr("menu_open_file"), self)
                open_action.triggered.connect(
                    lambda checked, p=file_path: self._display_file_content(Path(p))
                )
                menu.addAction(open_action)

                # Open file location (opens explorer)
                if self._rootfolder_manager:
                    open_location_action = QAction(tr("menu_open_file_location"), self)
                    open_location_action.triggered.connect(
                        lambda checked, p=file_path: self._rootfolder_manager._open_file_location(Path(p))
                    )
                    menu.addAction(open_location_action)

        # Folder items
        elif item_type == "folder":
            folder_path = data.get("path")
            if folder_path and self._rootfolder_manager:
                # Open folder location (opens explorer)
                open_location_action = QAction(tr("menu_open_file_location"), self)
                open_location_action.triggered.connect(
                    lambda checked, p=folder_path: self._rootfolder_manager._open_file_location(Path(p))
                )
                menu.addAction(open_location_action)

        # Only show menu if it has actions
        if menu.actions():
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
        elif resource_type == "script":
            self.config_db.remove_script_from_workspace(workspace_id, resource_id)

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
        self.content_stack.setCurrentIndex(0)  # Show welcome

    # ==================== Content Display ====================

    def _display_file_content(self, file_path: Path):
        """Display file content in the content viewer."""
        if not file_path.exists():
            DialogHelper.warning(f"File not found: {file_path}")
            return

        self.content_label.setText(f"Content: {file_path.name}")

        ext = file_path.suffix.lower()

        try:
            # CSV files
            if ext == ".csv":
                self._display_csv_file(file_path)

            # Excel files
            elif ext in [".xlsx", ".xls"]:
                self._display_excel_file(file_path)

            # JSON files
            elif ext == ".json":
                self._display_json_file(file_path)

            # Text files
            else:
                self._display_text_file(file_path)

        except Exception as e:
            logger.error(f"Error displaying file {file_path}: {e}")
            self.content_text.setPlainText(f"Error loading file:\n{e}")
            self.content_stack.setCurrentIndex(2)

    def _display_csv_file(self, file_path: Path):
        """Display CSV file in grid."""
        import csv

        # Detect encoding
        encoding = self._detect_encoding(file_path)

        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            # Try to detect delimiter
            sample = f.read(4096)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ','

            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)

        if rows:
            headers = rows[0]
            data = rows[1:]
            self.content_grid.set_columns(headers)
            self.content_grid.set_data(data)
            self.content_stack.setCurrentIndex(1)
        else:
            self.content_text.setPlainText("(Empty file)")
            self.content_stack.setCurrentIndex(2)

    def _display_excel_file(self, file_path: Path):
        """Display Excel file in grid."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb.active

            rows = list(ws.iter_rows(values_only=True))
            wb.close()

            if rows:
                headers = [str(h) if h else f"Col{i}" for i, h in enumerate(rows[0])]
                data = [[str(cell) if cell is not None else "" for cell in row] for row in rows[1:]]
                self.content_grid.set_columns(headers)
                self.content_grid.set_data(data)
                self.content_stack.setCurrentIndex(1)
            else:
                self.content_text.setPlainText("(Empty file)")
                self.content_stack.setCurrentIndex(2)

        except ImportError:
            self.content_text.setPlainText("openpyxl not installed - cannot read Excel files")
            self.content_stack.setCurrentIndex(2)

    def _display_json_file(self, file_path: Path):
        """Display JSON file - as table if array of objects, else as text."""
        import json

        encoding = self._detect_encoding(file_path)

        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()

        try:
            data = json.loads(content)

            # If array of objects, display as table
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                headers = list(data[0].keys())
                rows = [[str(item.get(h, "")) for h in headers] for item in data]
                self.content_grid.set_columns(headers)
                self.content_grid.set_data(rows)
                self.content_stack.setCurrentIndex(1)
            # If dict with string keys and dict values (row-keyed), display as table
            elif isinstance(data, dict) and len(data) > 0:
                first_val = next(iter(data.values()))
                if isinstance(first_val, dict):
                    headers = ["_key"] + list(first_val.keys())
                    rows = [[k] + [str(v.get(h, "")) for h in headers[1:]] for k, v in data.items()]
                    self.content_grid.set_columns(headers)
                    self.content_grid.set_data(rows)
                    self.content_stack.setCurrentIndex(1)
                else:
                    # Regular JSON - show as formatted text
                    self.content_text.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
                    self.content_stack.setCurrentIndex(2)
            else:
                # Not tabular - show as formatted text
                self.content_text.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
                self.content_stack.setCurrentIndex(2)

        except json.JSONDecodeError as e:
            self.content_text.setPlainText(f"Invalid JSON:\n{e}\n\n{content[:1000]}")
            self.content_stack.setCurrentIndex(2)

    def _display_text_file(self, file_path: Path):
        """Display text file."""
        encoding = self._detect_encoding(file_path)

        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read(500000)  # Limit to 500KB
                if len(content) == 500000:
                    content += "\n\n... (truncated)"
        except Exception as e:
            content = f"Error reading file: {e}"

        self.content_text.setPlainText(content)
        self.content_stack.setCurrentIndex(2)

    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding."""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw = f.read(10000)
            result = chardet.detect(raw)
            return result.get('encoding', 'utf-8') or 'utf-8'
        except ImportError:
            return 'utf-8'

    def _execute_select_query(self, data: dict, limit: Optional[int] = None):
        """Execute SELECT query and display results in grid."""
        if not self._database_manager:
            DialogHelper.warning("Database manager not available")
            return

        db_id = data.get("db_id")
        db_name = data.get("db_name")
        table_name = data.get("name")

        if not db_id or not table_name:
            return

        # Get connection
        connection = self._database_manager.connections.get(db_id)
        if not connection:
            DialogHelper.warning("Not connected to database. Please expand the database first.")
            return

        # Build query
        db_conn = self._database_manager._get_connection_by_id(db_id)
        if not db_conn:
            return

        try:
            if db_conn.db_type == "sqlite":
                if limit:
                    query = f"SELECT * FROM [{table_name}] LIMIT {limit}"
                else:
                    query = f"SELECT * FROM [{table_name}]"
            elif db_conn.db_type == "sqlserver" and db_name:
                full_table_name = f"[{db_name}].{table_name}"
                if limit:
                    query = f"SELECT TOP {limit} * FROM {full_table_name}"
                else:
                    query = f"SELECT * FROM {full_table_name}"
            else:
                if limit:
                    query = f"SELECT TOP {limit} * FROM [{table_name}]"
                else:
                    query = f"SELECT * FROM [{table_name}]"

            self.content_label.setText(f"Query: {table_name}")

            # Execute query
            cursor = connection.cursor()
            cursor.execute(query)

            # Get column names
            columns = [desc[0] for desc in cursor.description]

            # Fetch all rows
            rows = cursor.fetchall()
            data_list = [[str(cell) if cell is not None else "" for cell in row] for row in rows]

            # Display in grid
            self.content_grid.set_columns(columns)
            self.content_grid.set_data(data_list)
            self.content_stack.setCurrentIndex(1)

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            self.content_text.setPlainText(f"Error executing query:\n{e}")
            self.content_stack.setCurrentIndex(2)

    def _show_routine_code(self, data: dict):
        """Show stored procedure or function code."""
        if not self._database_manager:
            DialogHelper.warning("Database manager not available")
            return

        db_id = data.get("db_id")
        db_name = data.get("db_name")

        connection = self._database_manager.connections.get(db_id)
        if not connection:
            DialogHelper.warning("Not connected to database. Please expand the database first.")
            return

        item_type = data.get("type", "")
        name = data.get("name", "")

        try:
            if item_type == "view":
                # Get view code
                schema_view = name.split(".")
                if len(schema_view) == 2:
                    schema, view_name = schema_view
                else:
                    schema, view_name = "dbo", name

                query = f"""
                    SELECT m.definition
                    FROM [{db_name}].sys.sql_modules m
                    INNER JOIN [{db_name}].sys.views v ON m.object_id = v.object_id
                    INNER JOIN [{db_name}].sys.schemas s ON v.schema_id = s.schema_id
                    WHERE v.name = '{view_name}' AND s.name = '{schema}'
                """
            elif item_type == "procedure":
                schema = data.get("schema", "dbo")
                proc_name = data.get("proc_name", name)

                query = f"""
                    SELECT m.definition
                    FROM [{db_name}].sys.sql_modules m
                    INNER JOIN [{db_name}].sys.objects o ON m.object_id = o.object_id
                    INNER JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
                    WHERE o.name = '{proc_name}' AND s.name = '{schema}'
                """
            elif item_type == "function":
                schema = data.get("schema", "dbo")
                func_name = data.get("func_name", name)

                query = f"""
                    SELECT m.definition
                    FROM [{db_name}].sys.sql_modules m
                    INNER JOIN [{db_name}].sys.objects o ON m.object_id = o.object_id
                    INNER JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
                    WHERE o.name = '{func_name}' AND s.name = '{schema}'
                """
            else:
                self.content_text.setPlainText("Unknown routine type")
                self.content_stack.setCurrentIndex(2)
                return

            self.content_label.setText(f"Code: {name}")

            cursor = connection.cursor()
            cursor.execute(query)
            row = cursor.fetchone()

            if row and row[0]:
                self.content_text.setPlainText(row[0])
            else:
                self.content_text.setPlainText("-- Code not available")

            self.content_stack.setCurrentIndex(2)

        except Exception as e:
            logger.error(f"Error loading routine code: {e}")
            self.content_text.setPlainText(f"Error loading code:\n{e}")
            self.content_stack.setCurrentIndex(2)

    def _generate_select_columns_query(self, data: dict):
        """Generate a formatted SELECT query with all column names."""
        if not self._database_manager:
            DialogHelper.warning("Database manager not available")
            return

        db_id = data.get("db_id")
        db_name = data.get("db_name")
        table_name = data.get("name")

        if not db_id or not table_name:
            return

        connection = self._database_manager.connections.get(db_id)
        if not connection:
            DialogHelper.warning("Not connected to database. Please expand the database first.")
            return

        db_conn = self._database_manager._get_connection_by_id(db_id)
        if not db_conn:
            return

        try:
            # Get columns based on database type
            if db_conn.db_type == "sqlite":
                cursor = connection.cursor()
                cursor.execute(f"PRAGMA table_info([{table_name}])")
                columns = [row[1] for row in cursor.fetchall()]
                full_table_name = f"[{table_name}]"
            elif db_conn.db_type == "sqlserver" and db_name:
                # Parse schema.table format
                parts = table_name.split(".")
                if len(parts) == 2:
                    schema, tbl_name = parts
                else:
                    schema, tbl_name = "dbo", table_name

                cursor = connection.cursor()
                cursor.execute(f"""
                    SELECT c.name
                    FROM [{db_name}].sys.columns c
                    INNER JOIN [{db_name}].sys.tables t ON c.object_id = t.object_id
                    INNER JOIN [{db_name}].sys.schemas s ON t.schema_id = s.schema_id
                    WHERE t.name = '{tbl_name}' AND s.name = '{schema}'
                    ORDER BY c.column_id
                """)
                columns = [row[0] for row in cursor.fetchall()]

                # If no columns found, try as a view
                if not columns:
                    cursor.execute(f"""
                        SELECT c.name
                        FROM [{db_name}].sys.columns c
                        INNER JOIN [{db_name}].sys.views v ON c.object_id = v.object_id
                        INNER JOIN [{db_name}].sys.schemas s ON v.schema_id = s.schema_id
                        WHERE v.name = '{tbl_name}' AND s.name = '{schema}'
                        ORDER BY c.column_id
                    """)
                    columns = [row[0] for row in cursor.fetchall()]

                full_table_name = f"[{db_name}].[{schema}].[{tbl_name}]"
            else:
                # Fallback
                cursor = connection.cursor()
                cursor.execute(f"SELECT TOP 1 * FROM [{table_name}]")
                columns = [desc[0] for desc in cursor.description]
                full_table_name = f"[{table_name}]"

            if not columns:
                self.content_text.setPlainText("-- No columns found")
                self.content_stack.setCurrentIndex(2)
                return

            # Format the query in "sophisticated/ultimate" style
            query = self._format_select_query(columns, full_table_name)

            self.content_label.setText(f"Query: {table_name}")
            self.content_text.setPlainText(query)
            self.content_stack.setCurrentIndex(2)

        except Exception as e:
            logger.error(f"Error generating SELECT COLUMNS query: {e}")
            self.content_text.setPlainText(f"Error generating query:\n{e}")
            self.content_stack.setCurrentIndex(2)

    def _format_select_query(self, columns: list, table_name: str) -> str:
        """
        Format a SELECT query with columns in sophisticated/ultimate style.

        Style:
        SELECT
              [Column1]
            , [Column2]
            , [Column3]
            ...
        FROM [Table]
        WHERE 1 = 1
            -- AND [Column1] = ''
            -- AND [Column2] = ''
        ORDER BY
              [Column1] ASC
            --, [Column2] DESC
        ;
        """
        lines = ["SELECT"]

        # Format columns with leading comma style
        for i, col in enumerate(columns):
            if i == 0:
                lines.append(f"      [{col}]")
            else:
                lines.append(f"    , [{col}]")

        lines.append(f"FROM {table_name}")
        lines.append("WHERE 1 = 1")

        # Add commented WHERE conditions for each column
        for col in columns[:5]:  # Limit to first 5 columns for brevity
            lines.append(f"    -- AND [{col}] = ''")

        if len(columns) > 5:
            lines.append(f"    -- ... ({len(columns) - 5} more columns)")

        lines.append("ORDER BY")
        lines.append(f"      [{columns[0]}] ASC")

        if len(columns) > 1:
            lines.append(f"    --, [{columns[1]}] DESC")

        lines.append(";")

        return "\n".join(lines)
