"""
Resources Manager - Unified view of all application resources
Standard layout: Left TreeView + Right Details Panel
Delegates to managers for loading children and handling actions.

Architecture:
- Left Panel: TreeView with all resources (categories + items)
- Right Panel: QStackedWidget containing manager interfaces (composition)
  - When a database/table/view is selected → show DatabaseManager's interface
  - When a rootfolder/folder/file is selected → show RootFolderManager's interface
  - For other items → show generic details form
"""

from typing import List, Optional, Any
from pathlib import Path
from PySide6.QtWidgets import QWidget, QTreeWidgetItem, QStackedWidget, QVBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt, Signal

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db
from ...utils.image_loader import get_icon

# DataFrame-Pivot pattern: centralized loading functions
from ...core.data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    excel_to_dataframe,
    LoadWarningLevel,
    LARGE_DATASET_THRESHOLD
)
# Using CustomDataGridView.set_dataframe() directly for optimal performance

import logging
logger = logging.getLogger(__name__)


class ResourcesManager(BaseManagerView):
    """
    Unified resource manager - standard layout like all other managers.

    Left Panel: TreeView with categories
        - Databases (expandable via DatabaseManager)
        - Rootfolders (expandable via RootFolderManager)
        - Queries
        - Jobs
        - Scripts

    Right Panel: Details of selected item

    Delegates to managers for:
        - Loading children (expand)
        - Context menus
        - Actions
    """

    # Signal emitted when user wants to open a resource in dedicated view
    open_resource_requested = Signal(str, str)  # (resource_type, resource_id as UUID string)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, title=tr("menu_view"))

        self._category_items = {}

        # Manager references (set via set_managers)
        self._database_manager = None
        self._rootfolder_manager = None
        self._queries_manager = None
        self._jobs_manager = None
        self._scripts_manager = None

        # Enable tree expansion
        self.tree_view.tree.setRootIsDecorated(True)
        self.tree_view.tree.setAnimated(True)
        self.tree_view.tree.setIndentation(20)
        # Disable default double-click expand/collapse (we handle it ourselves)
        self.tree_view.tree.setExpandsOnDoubleClick(False)

        # Connect expand signal for lazy loading
        self.tree_view.tree.itemExpanded.connect(self._on_item_expanded)

        # Enable context menu
        self.tree_view.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.tree.customContextMenuRequested.connect(self._on_context_menu)

        self._setup_toolbar()
        self._setup_details()
        self._setup_content()
        self.refresh()

        # Collapse details panel by default (only useful for files)
        self._collapse_details_panel()

    def set_managers(self, database_manager=None, rootfolder_manager=None,
                     queries_manager=None, jobs_manager=None, scripts_manager=None):
        """Set references to managers for delegation and add their content to stack."""
        self._database_manager = database_manager
        self._rootfolder_manager = rootfolder_manager
        self._queries_manager = queries_manager
        self._jobs_manager = jobs_manager
        self._scripts_manager = scripts_manager

        # Add manager right panels to the stack (composition)
        self._setup_manager_pages()

    def _setup_manager_pages(self):
        """Add manager content widgets to the stacked widget."""
        from PySide6.QtWidgets import QTabWidget

        # Page 2: DatabaseManager's right panel - QTabWidget with QueryTabs
        # (Page 0 = generic, Page 1 = query editor - created in _setup_content)
        if self._database_manager:
            db_wrapper = QWidget()
            db_layout = QVBoxLayout(db_wrapper)
            db_layout.setContentsMargins(0, 0, 0, 0)

            # Create our own QTabWidget for query tabs
            self.query_tab_widget = QTabWidget()
            self.query_tab_widget.setTabsClosable(True)
            self.query_tab_widget.setMovable(True)
            self.query_tab_widget.tabCloseRequested.connect(self._close_query_tab)
            # Double-click on tab to rename
            self.query_tab_widget.tabBarDoubleClicked.connect(self._rename_query_tab)

            # Add welcome tab
            self._create_db_welcome_tab()

            db_layout.addWidget(self.query_tab_widget)

            self.content_stack.addWidget(db_wrapper)
            self._page_indices["database"] = self.content_stack.count() - 1
            self._query_tab_counter = 1

        # Page 3: RootFolderManager's right panel (file viewer)
        if self._rootfolder_manager:
            from PySide6.QtWidgets import QTextEdit
            from ..widgets.custom_datagridview import CustomDataGridView

            # Create file viewer stack (grid for data files, text for others)
            self.file_viewer_stack = QStackedWidget()

            # Grid viewer for CSV, Excel, etc.
            self.file_grid_viewer = CustomDataGridView()
            self.file_viewer_stack.addWidget(self.file_grid_viewer)

            # Text viewer for text files, JSON, etc.
            self.file_text_viewer = QTextEdit()
            self.file_text_viewer.setReadOnly(True)
            self.file_text_viewer.setStyleSheet("""
                QTextEdit {
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 10pt;
                }
            """)
            self.file_viewer_stack.addWidget(self.file_text_viewer)

            # Welcome/placeholder widget
            file_welcome = QWidget()
            file_welcome_layout = QVBoxLayout(file_welcome)
            file_welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            welcome_label = QLabel("Double-cliquez sur un fichier pour afficher son contenu")
            welcome_label.setStyleSheet("color: gray; font-size: 11pt;")
            file_welcome_layout.addWidget(welcome_label)
            self.file_viewer_stack.addWidget(file_welcome)

            # Start with welcome widget
            self.file_viewer_stack.setCurrentIndex(2)

            self.content_stack.addWidget(self.file_viewer_stack)
            self._page_indices["rootfolder"] = self.content_stack.count() - 1

    def _get_tree_columns(self) -> List[str]:
        return [tr("col_name")]

    def _setup_toolbar(self):
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_refresh"), self.refresh, icon="refresh.png")
        self._replace_toolbar(toolbar_builder)

    def _setup_details(self):
        """Setup details panel (top right) with item info."""
        # Details form shows basic info about selected item
        self.details_form_builder = FormBuilder(title=tr("item_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("col_type"), "resource_type") \
            .add_field(tr("col_description"), "description") \
            .add_field(tr("field_path"), "path") \
            .add_field("Encoding", "encoding") \
            .add_field("Separator", "separator") \
            .add_field("Delimiter", "delimiter")

        details_widget = self.details_form_builder.build()
        self.details_layout.addWidget(details_widget)

        # Store detected file properties for display
        self._detected_encoding = None
        self._detected_separator = None
        self._detected_delimiter = None

    def _setup_content(self):
        """Setup content panel (bottom right) with QStackedWidget for manager content."""
        from PySide6.QtWidgets import QTextEdit, QSplitter, QPushButton, QHBoxLayout
        from ..widgets.custom_datagridview import CustomDataGridView

        # Create stacked widget to hold different manager views
        self.content_stack = QStackedWidget()
        self.content_layout.addWidget(self.content_stack)

        # Page 0: Generic placeholder (for categories, jobs, scripts)
        generic_widget = QWidget()
        generic_layout = QVBoxLayout(generic_widget)
        generic_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        generic_label = QLabel("Sélectionnez un élément pour voir son contenu")
        generic_label.setStyleSheet("color: gray;")
        generic_layout.addWidget(generic_label)
        self.content_stack.addWidget(generic_widget)

        # Page 1: Query editor + results (for saved queries)
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        query_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar for query execution
        query_toolbar = QHBoxLayout()
        self.query_execute_btn = QPushButton("▶ Execute (F5)")
        self.query_execute_btn.clicked.connect(self._execute_saved_query)
        query_toolbar.addWidget(self.query_execute_btn)

        self.query_update_btn = QPushButton("💾 Update Query")
        self.query_update_btn.clicked.connect(self._update_saved_query)
        self.query_update_btn.setToolTip("Update the saved query with current SQL text")
        query_toolbar.addWidget(self.query_update_btn)

        query_toolbar.addStretch()
        query_layout.addLayout(query_toolbar)

        # Splitter: SQL editor (top) + Results (bottom)
        query_splitter = QSplitter(Qt.Orientation.Vertical)

        # SQL Editor
        self.query_sql_editor = QTextEdit()
        self.query_sql_editor.setPlaceholderText("-- SQL Query")
        self.query_sql_editor.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10pt;
            }
        """)
        query_splitter.addWidget(self.query_sql_editor)

        # Results grid
        self.query_results_grid = CustomDataGridView(show_toolbar=True)
        query_splitter.addWidget(self.query_results_grid)

        query_splitter.setSizes([200, 400])
        query_layout.addWidget(query_splitter)

        self.content_stack.addWidget(query_widget)

        # Pages for managers will be added in set_managers()
        self._page_indices = {"generic": 0, "query": 1}

        # Current query context
        self._current_query_obj = None
        self._current_query_connection = None
        self._current_query_db_conn = None

    def _load_items(self):
        """Load all resources into tree."""
        try:
            config_db = get_config_db()
            self._category_items = {}

            # Categories
            categories = [
                ("databases", tr("menu_database")),
                ("rootfolders", "Rootfolders"),
                ("queries", tr("menu_queries")),
                ("jobs", tr("menu_jobs")),
                ("scripts", tr("menu_scripts")),
            ]

            for key, label in categories:
                self._add_category(key, label)

            # Databases - with expand capability
            databases = config_db.get_all_database_connections()
            for db in databases:
                item = self.tree_view.add_item(
                    parent=self._category_items["databases"],
                    text=[db.name],
                    data={"type": "database", "id": db.id, "obj": db}
                )
                self._set_item_icon(item, db.db_type)
                self._add_dummy_child(item)

            # Rootfolders - with expand capability
            rootfolders = config_db.get_all_file_roots()
            for rf in rootfolders:
                item = self.tree_view.add_item(
                    parent=self._category_items["rootfolders"],
                    text=[rf.name or rf.path],
                    data={"type": "rootfolder", "id": rf.id, "obj": rf, "path": rf.path}
                )
                self._set_item_icon(item, "folder")
                self._add_dummy_child(item)

            # Queries - grouped by category
            queries = config_db.get_all_saved_queries()

            # Group queries by category
            queries_by_category = {}
            for query in queries:
                cat = query.category or "No category"
                if cat not in queries_by_category:
                    queries_by_category[cat] = []
                queries_by_category[cat].append(query)

            # Create category folders and add queries
            self._query_category_items = {}
            for category_name in sorted(queries_by_category.keys()):
                # Create category folder
                cat_item = self.tree_view.add_item(
                    parent=self._category_items["queries"],
                    text=[f"{category_name} ({len(queries_by_category[category_name])})"],
                    data={"type": "query_category", "name": category_name}
                )
                self._set_item_icon(cat_item, "folder")
                self._query_category_items[category_name] = cat_item

                # Add queries under this category
                for query in queries_by_category[category_name]:
                    item = self.tree_view.add_item(
                        parent=cat_item,
                        text=[query.name],
                        data={"type": "query", "id": query.id, "obj": query}
                    )
                    self._set_item_icon(item, "queries")

            # Jobs
            jobs = config_db.get_all_jobs()
            for job in jobs:
                item = self.tree_view.add_item(
                    parent=self._category_items["jobs"],
                    text=[job.name],
                    data={"type": "job", "id": job.id, "obj": job}
                )
                self._set_item_icon(item, "jobs")

            # Scripts
            scripts = config_db.get_all_scripts()
            for script in scripts:
                item = self.tree_view.add_item(
                    parent=self._category_items["scripts"],
                    text=[script.name],
                    data={"type": "script", "id": script.id, "obj": script}
                )
                self._set_item_icon(item, "scripts")

            # Expand categories
            for cat_item in self._category_items.values():
                cat_item.setExpanded(True)

            self._update_category_counts()

        except Exception as e:
            logger.error(f"Error loading resources: {e}")

    def _add_category(self, key: str, label: str):
        item = self.tree_view.add_item(
            parent=None,
            text=[label],
            data={"type": "category", "category_key": key}
        )
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        self._set_item_icon(item, key)
        self._category_items[key] = item

    def _update_category_counts(self):
        """Update counts for category items (Databases, Rootfolders, etc.)."""
        for key, item in self._category_items.items():
            count = item.childCount()
            text = item.text(0).split(" (")[0]
            item.setText(0, f"{text} ({count})")

    def refresh_queries(self):
        """
        Refresh only the Queries section of the tree.
        Called after saving a query to avoid collapsing other expanded nodes.
        """
        if "queries" not in self._category_items:
            return

        queries_item = self._category_items["queries"]

        # Clear existing query children (categories and queries)
        while queries_item.childCount() > 0:
            queries_item.removeChild(queries_item.child(0))

        # Reload queries grouped by category
        try:
            config_db = get_config_db()
            queries = config_db.get_all_saved_queries()

            # Group queries by category
            queries_by_category = {}
            for query in queries:
                cat = query.category or "No category"
                if cat not in queries_by_category:
                    queries_by_category[cat] = []
                queries_by_category[cat].append(query)

            # Create category folders and add queries
            self._query_category_items = {}
            for category_name in sorted(queries_by_category.keys()):
                # Create category folder
                cat_item = self.tree_view.add_item(
                    parent=queries_item,
                    text=[f"{category_name} ({len(queries_by_category[category_name])})"],
                    data={"type": "query_category", "name": category_name}
                )
                self._set_item_icon(cat_item, "folder")
                self._query_category_items[category_name] = cat_item

                # Add queries under this category
                for query in queries_by_category[category_name]:
                    item = self.tree_view.add_item(
                        parent=cat_item,
                        text=[query.name],
                        data={"type": "query", "id": query.id, "obj": query}
                    )
                    self._set_item_icon(item, "queries")

                # Expand category to show newly added query
                cat_item.setExpanded(True)

            # Update queries category count
            count = queries_item.childCount()
            text = queries_item.text(0).split(" (")[0]
            queries_item.setText(0, f"{text} ({count})")

            # Make sure queries category is expanded
            queries_item.setExpanded(True)

            logger.info(f"Queries refreshed: {len(queries)} queries in {len(queries_by_category)} categories")

        except Exception as e:
            logger.error(f"Error refreshing queries: {e}")

    def _update_item_count(self, item: QTreeWidgetItem):
        """Update count displayed next to an item after its children are loaded."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")
        text_base = item.text(0).split(" (")[0]  # Remove existing count

        if item_type in ("database", "server"):
            # Count tables and views (grandchildren under Tables/Views folders)
            total = 0
            for i in range(item.childCount()):
                child = item.child(i)
                child_data = child.data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data.get("type") in ("tables_folder", "views_folder"):
                    total += child.childCount()
            if total > 0:
                item.setText(0, f"{text_base} ({total})")

        elif item_type in ("rootfolder", "folder"):
            # Count immediate children (files + folders at this level)
            count = item.childCount()
            # Don't count dummy children
            if count == 1:
                first_child = item.child(0)
                child_data = first_child.data(0, Qt.ItemDataRole.UserRole) if first_child else None
                if child_data and child_data.get("type") == "dummy":
                    return
            if count > 0:
                item.setText(0, f"{text_base} ({count})")

        elif item_type == "tables_folder":
            # Count tables
            count = item.childCount()
            if count > 0:
                item.setText(0, f"{text_base} ({count})")

        elif item_type == "views_folder":
            # Count views
            count = item.childCount()
            if count > 0:
                item.setText(0, f"{text_base} ({count})")

    def _set_item_icon(self, item, icon_name: str):
        icon = get_icon(icon_name)
        if icon:
            item.setIcon(0, icon)

    def _add_dummy_child(self, parent_item):
        """Add dummy child to show expand arrow."""
        dummy = QTreeWidgetItem(parent_item)
        dummy.setText(0, "...")
        dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})

    def _collapse_details_panel(self):
        """Collapse details panel via splitter (avoids layout shifts unlike hide/show)."""
        if self.right_splitter:
            # Store current sizes before collapsing
            sizes = self.right_splitter.sizes()
            if sizes[0] > 0:  # Only store if not already collapsed
                self._details_panel_size = sizes[0]
            # Collapse: set details to 0, give all space to content
            self.right_splitter.setSizes([0, sum(sizes)])

    def _expand_details_panel(self):
        """Expand details panel via splitter."""
        if self.right_splitter:
            sizes = self.right_splitter.sizes()
            # Restore previous size or use default
            details_size = getattr(self, '_details_panel_size', 150)
            total = sum(sizes)
            self.right_splitter.setSizes([details_size, total - details_size])

    def _display_item(self, item_data: Any):
        """Display item details in appropriate panel based on type."""
        if not isinstance(item_data, dict):
            return

        item_type = item_data.get("type", "")
        obj = item_data.get("obj")

        # Switch to appropriate page based on item type
        if item_type in ("database", "server", "table", "view", "column", "tables_folder", "views_folder"):
            # Show database panel - collapse details panel (QueryTab is enough)
            if "database" in self._page_indices:
                self.content_stack.setCurrentIndex(self._page_indices["database"])
            self._collapse_details_panel()
            return

        elif item_type in ("rootfolder", "folder", "file"):
            # Show rootfolder panel with details
            if "rootfolder" in self._page_indices:
                self.content_stack.setCurrentIndex(self._page_indices["rootfolder"])
            self._expand_details_panel()
            self._display_file_item(item_data)
            return

        # Default: show generic details with expanded panel
        self._expand_details_panel()
        self.content_stack.setCurrentIndex(self._page_indices["generic"])

        if item_type == "category":
            self.details_form_builder.set_value("name", item_data.get("category_key", "").capitalize())
            self.details_form_builder.set_value("resource_type", "Category")
            self.details_form_builder.set_value("description", "")
            self.details_form_builder.set_value("path", "")
            self.details_form_builder.set_value("encoding", "-")
            self.details_form_builder.set_value("separator", "-")
            self.details_form_builder.set_value("delimiter", "-")
            return

        if not obj:
            return

        name = getattr(obj, "name", "")
        description = getattr(obj, "description", "") or ""
        path = getattr(obj, "path", "") or ""

        type_labels = {
            "database": f"Database ({getattr(obj, 'db_type', '')})",
            "rootfolder": "Rootfolder",
            "query": "Query",
            "job": "Job",
            "script": "Script",
        }

        self.details_form_builder.set_value("name", name)
        self.details_form_builder.set_value("resource_type", type_labels.get(item_type, item_type))
        self.details_form_builder.set_value("description", description)
        self.details_form_builder.set_value("path", path)
        self.details_form_builder.set_value("encoding", "-")
        self.details_form_builder.set_value("separator", "-")
        self.details_form_builder.set_value("delimiter", "-")

    def _display_file_item(self, item_data: dict):
        """Display file/folder item details in the details panel."""
        item_type = item_data.get("type", "")
        path_str = item_data.get("path", "")
        obj = item_data.get("obj")

        if item_type == "rootfolder" and obj:
            # Root folder from database
            name = getattr(obj, "name", "") or Path(path_str).name
            self.details_form_builder.set_value("name", name)
            self.details_form_builder.set_value("resource_type", "Root Folder")
            self.details_form_builder.set_value("description", getattr(obj, "description", "") or "")
            self.details_form_builder.set_value("path", getattr(obj, "path", path_str))
            self.details_form_builder.set_value("encoding", "-")
            self.details_form_builder.set_value("separator", "-")
            self.details_form_builder.set_value("delimiter", "-")

        elif path_str:
            # File or folder from filesystem
            file_path = Path(path_str)
            if file_path.exists():
                try:
                    stat = file_path.stat()

                    # Format size
                    if file_path.is_file():
                        size_bytes = stat.st_size
                        if size_bytes < 1024:
                            size_str = f"{size_bytes} B"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes / 1024:.2f} KB"
                        else:
                            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
                        file_type = file_path.suffix.upper()[1:] if file_path.suffix else "File"
                        # Encoding will be set when file content is loaded
                        encoding_display = "-"
                    else:
                        size_str = "-"
                        file_type = "Folder"
                        encoding_display = "-"

                    # Format modified date
                    from datetime import datetime
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                    self.details_form_builder.set_value("name", file_path.name)
                    self.details_form_builder.set_value("resource_type", f"{file_type} ({size_str})")
                    self.details_form_builder.set_value("description", f"Modified: {modified}")
                    self.details_form_builder.set_value("path", str(file_path))
                    self.details_form_builder.set_value("encoding", encoding_display)
                    self.details_form_builder.set_value("separator", "-")
                    self.details_form_builder.set_value("delimiter", "-")
                except Exception as e:
                    logger.error(f"Error getting file info: {e}")

    def _on_tree_double_click(self, item, column):
        """Double-click: expand/collapse items, or open files/queries."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        if item_type in ("category", "database", "server", "rootfolder", "folder",
                         "tables_folder", "views_folder", "table", "view",
                         "query_category"):
            # Toggle expand for expandable items (including tables to show columns)
            item.setExpanded(not item.isExpanded())

        elif item_type == "file":
            # Load and display file content in our viewer
            path = data.get("path")
            if path:
                self._load_file_content(Path(path))

        elif item_type == "query":
            # Load query into editor and execute (auto-connect if needed)
            query_obj = data.get("obj")
            if query_obj:
                self._load_saved_query(query_obj)
                # Auto-execute after loading (will auto-connect if needed)
                self._execute_saved_query()

        else:
            # For other items (job, script), emit signal to open in dedicated manager
            item_id = data.get("id")
            if item_id:
                self.open_resource_requested.emit(item_type, item_id)

    # ==================== Lazy Loading (delegates to managers) ====================

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle expand - delegate to appropriate manager."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        # Check for dummy child (lazy loading trigger)
        if item.childCount() == 1:
            first_child = item.child(0)
            child_data = first_child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("type") == "dummy":
                item.removeChild(first_child)

                if item_type == "database" and self._database_manager:
                    self._load_database_children(item, data)
                    # Check if connection succeeded
                    item_data = item.data(0, Qt.ItemDataRole.UserRole)
                    if item_data and item_data.get("connected"):
                        # Update count after loading (shows tables+views count)
                        self._update_item_count(item)
                        # Also update Tables and Views folders
                        for i in range(item.childCount()):
                            child = item.child(i)
                            self._update_item_count(child)
                    else:
                        # Connection failed - re-add dummy child to allow retry
                        item.setExpanded(False)
                        dummy = QTreeWidgetItem(item)
                        dummy.setText(0, "Double-clic pour charger...")
                        dummy.setForeground(0, Qt.GlobalColor.gray)
                        dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})
                elif item_type == "rootfolder" and self._rootfolder_manager:
                    self._load_rootfolder_children(item, data)
                    # Update count after loading (shows files+folders count)
                    self._update_item_count(item)
                elif item_type == "folder" and self._rootfolder_manager:
                    self._load_folder_children(item, data)
                    # Update count after loading
                    self._update_item_count(item)
        else:
            # Item already has children - just update count if needed
            if item_type in ("tables_folder", "views_folder"):
                self._update_item_count(item)

    def _load_database_children(self, parent_item: QTreeWidgetItem, data: dict):
        """Load database schema using DatabaseManager's methods."""
        if not self._database_manager:
            return

        db_obj = data.get("obj")
        if not db_obj:
            return

        # Save original data to restore on failure
        original_data = data.copy()

        # Use DatabaseManager's _connect_and_load_schema method
        # First, update the item's data to match what DatabaseManager expects
        parent_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "server",
            "config": db_obj,
            "connected": False
        })

        # Call the connection and schema loading method
        try:
            self._database_manager._connect_and_load_schema(parent_item, db_obj)
            # Check if connection succeeded
            if not self._database_manager.connections.get(db_obj.id):
                # Connection failed - restore original data
                parent_item.setData(0, Qt.ItemDataRole.UserRole, original_data)
        except Exception as e:
            logger.error(f"Error loading database schema: {e}")
            # Restore original data on exception
            parent_item.setData(0, Qt.ItemDataRole.UserRole, original_data)

    def _load_rootfolder_children(self, parent_item: QTreeWidgetItem, data: dict):
        """Delegate rootfolder loading to RootFolderManager."""
        if not self._rootfolder_manager:
            return

        path = data.get("path")
        if path:
            self._load_folder_children(parent_item, {"path": path})

    def _load_folder_children(self, parent_item: QTreeWidgetItem, data: dict):
        """Load folder contents - delegate to RootFolderManager if available."""
        path = Path(data.get("path", ""))
        if not path.exists():
            return

        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

            for entry in entries:
                if entry.is_dir():
                    folder_item = self.tree_view.add_item(
                        parent=parent_item,
                        text=[entry.name],
                        data={"type": "folder", "path": str(entry)}
                    )
                    self._set_item_icon(folder_item, "folder")
                    self._add_dummy_child(folder_item)
                else:
                    file_item = self.tree_view.add_item(
                        parent=parent_item,
                        text=[entry.name],
                        data={"type": "file", "path": str(entry)}
                    )
                    self._set_item_icon(file_item, self._get_file_icon(entry))

        except Exception as e:
            logger.error(f"Error loading folder: {e}")

    def _get_file_icon(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        return {
            ".csv": "CSV", ".xlsx": "Excel", ".xls": "Excel",
            ".json": "json", ".py": "scripts", ".sql": "queries",
        }.get(ext, "file")

    # ==================== Context Menu (delegates to managers) ====================

    def _on_context_menu(self, position):
        """Show context menu based on item type."""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        item = self.tree_view.tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")
        menu = QMenu(self)

        if item_type == "category":
            menu.addAction(tr("btn_refresh"), self.refresh)

        elif item_type in ("database", "server"):
            # Database connection context menu
            db_config = data.get("config") or data.get("obj")
            if db_config and self._database_manager:
                # New Query Tab option
                new_tab_action = QAction("➕ New Query Tab", self)
                new_tab_action.triggered.connect(lambda: self._create_empty_query_tab(db_config.id))
                menu.addAction(new_tab_action)

                menu.addSeparator()

                refresh_action = QAction(tr("btn_refresh"), self)
                refresh_action.triggered.connect(lambda: self._refresh_database_item(item, db_config))
                menu.addAction(refresh_action)

        elif item_type in ("tables_folder", "views_folder"):
            # Tables/Views folder - expand/collapse
            if item.isExpanded():
                collapse_action = QAction("Collapse", self)
                collapse_action.triggered.connect(lambda: item.setExpanded(False))
                menu.addAction(collapse_action)
            else:
                expand_action = QAction("Expand", self)
                expand_action.triggered.connect(lambda: item.setExpanded(True))
                menu.addAction(expand_action)

        elif item_type in ("table", "view"):
            # Table/View context menu - execute queries in our query tab
            db_id = data.get("db_id")

            # New Query Tab option
            if db_id:
                new_tab_action = QAction("➕ New Query Tab", self)
                new_tab_action.triggered.connect(lambda: self._create_empty_query_tab(db_id))
                menu.addAction(new_tab_action)
                menu.addSeparator()

            # SELECT TOP 100 action
            select_top_action = QAction("SELECT TOP 100 *", self)
            select_top_action.triggered.connect(lambda: self._execute_query_for_table(data, limit=100))
            menu.addAction(select_top_action)

            # SELECT * action
            select_all_action = QAction("SELECT *", self)
            select_all_action.triggered.connect(lambda: self._execute_query_for_table(data, limit=None))
            menu.addAction(select_all_action)

            menu.addSeparator()

            # Distribution Analysis action - use DatabaseManager's method (opens in separate window)
            if self._database_manager:
                dist_action = QAction("📊 Distribution Analysis", self)
                dist_action.triggered.connect(lambda: self._database_manager._show_distribution_analysis(data))
                menu.addAction(dist_action)

        elif item_type == "rootfolder":
            # RootFolder context menu
            rootfolder_obj = data.get("obj")
            if rootfolder_obj and self._rootfolder_manager:
                edit_action = QAction("Edit Name & Description", self)
                edit_action.triggered.connect(lambda: self._rootfolder_manager._edit_rootfolder(rootfolder_obj))
                menu.addAction(edit_action)

                menu.addSeparator()

                refresh_action = QAction(tr("btn_refresh"), self)
                refresh_action.triggered.connect(self.refresh)
                menu.addAction(refresh_action)

        elif item_type == "folder":
            # Folder context menu
            path = data.get("path")
            if path:
                open_location_action = QAction("Open Folder Location", self)
                open_location_action.triggered.connect(lambda: self._open_location(Path(path)))
                menu.addAction(open_location_action)

        elif item_type == "column":
            # Column context menu - copy column name
            col_name = data.get("column", item.text(0).split(" (")[0])
            copy_action = QAction(f"Copy '{col_name}'", self)
            copy_action.triggered.connect(lambda: QApplication.clipboard().setText(col_name))
            menu.addAction(copy_action)

        elif item_type == "file":
            # File context menu
            path = data.get("path")
            if path and self._rootfolder_manager:
                open_action = QAction("Open", self)
                open_action.triggered.connect(lambda: self._rootfolder_manager._open_file(Path(path)))
                menu.addAction(open_action)

                open_location_action = QAction("Open File Location", self)
                open_location_action.triggered.connect(lambda: self._rootfolder_manager._open_file_location(Path(path)))
                menu.addAction(open_location_action)

        # Debug: if no actions were added, log the item type
        if not menu.actions():
            logger.warning(f"No context menu for item type: '{item_type}', data: {data}")

        if menu.actions():
            menu.exec(self.tree_view.tree.viewport().mapToGlobal(position))

    def _refresh_database_item(self, item: QTreeWidgetItem, db_config):
        """Refresh a database item by reloading its schema."""
        # Clear existing children
        while item.childCount() > 0:
            item.removeChild(item.child(0))

        # Add dummy child and reload
        self._add_dummy_child(item)
        item.setExpanded(False)
        item.setExpanded(True)  # This triggers _on_item_expanded

    def _open_location(self, path: Path):
        """Open folder location in file explorer."""
        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                subprocess.run(['explorer', str(path)])
            elif platform.system() == "Darwin":
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            logger.error(f"Error opening location: {e}")

    # ==================== Query Tab Management ====================

    def _create_db_welcome_tab(self):
        """Create welcome tab for database panel."""
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Database Explorer")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        welcome_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Double-cliquez sur une table ou vue pour exécuter SELECT TOP 100")
        subtitle.setStyleSheet("font-size: 11pt; color: gray;")
        welcome_layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        info = QLabel("Clic droit pour plus d'options (SELECT *, Distribution Analysis)")
        info.setStyleSheet("font-size: 10pt; color: gray;")
        welcome_layout.addWidget(info, alignment=Qt.AlignmentFlag.AlignCenter)

        self.query_tab_widget.addTab(welcome_widget, "Bienvenue")

    def _close_query_tab(self, index: int):
        """Close a query tab."""
        if index == 0:  # Don't close welcome tab
            return

        widget = self.query_tab_widget.widget(index)
        self.query_tab_widget.removeTab(index)
        if widget:
            # Cleanup QueryTab resources
            if hasattr(widget, 'cleanup'):
                widget.cleanup()
            widget.deleteLater()

    def _rename_query_tab(self, index: int):
        """Rename a query tab via double-click."""
        if index == 0:  # Don't rename welcome tab
            return

        from PySide6.QtWidgets import QInputDialog

        current_name = self.query_tab_widget.tabText(index)
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Tab / Renommer l'onglet",
            "New name / Nouveau nom:",
            text=current_name
        )

        if ok and new_name.strip():
            self.query_tab_widget.setTabText(index, new_name.strip())
            # Also update QueryTab's tab_name attribute
            widget = self.query_tab_widget.widget(index)
            if hasattr(widget, 'tab_name'):
                widget.tab_name = new_name.strip()
            logger.info(f"Renamed tab from '{current_name}' to '{new_name.strip()}'")

    def _get_or_create_query_tab(self, db_id: str, db_name: str = None):
        """Get existing query tab for database or create new one."""
        from .query_tab import QueryTab

        if not self._database_manager:
            return None

        # Get connection from DatabaseManager
        connection = self._database_manager.connections.get(db_id)
        db_conn = self._database_manager._get_connection_by_id(db_id)

        if not connection or not db_conn:
            DialogHelper.warning("Connexion à la base de données non disponible.\n"
                               "Développez d'abord le noeud de la base de données.", parent=self)
            return None

        # Check if there's already a tab for this database
        for i in range(1, self.query_tab_widget.count()):  # Skip welcome tab
            widget = self.query_tab_widget.widget(i)
            if isinstance(widget, QueryTab) and widget.db_connection and widget.db_connection.id == db_id:
                self.query_tab_widget.setCurrentIndex(i)
                return widget

        # Create new tab
        tab_name = f"Query {self._query_tab_counter}"
        self._query_tab_counter += 1

        query_tab = QueryTab(
            parent=self,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name,
            database_manager=self._database_manager
        )

        # Connect query_saved signal to refresh
        query_tab.query_saved.connect(self.refresh_queries)

        # Add to tab widget
        index = self.query_tab_widget.addTab(query_tab, tab_name)
        self.query_tab_widget.setCurrentIndex(index)

        logger.info(f"Created new query tab: {tab_name} for {db_conn.name}")

        return query_tab

    def _create_empty_query_tab(self, db_id: str):
        """Create a new empty query tab for the given database."""
        from .query_tab import QueryTab

        if not self._database_manager:
            return

        # Switch to database page to show the query tabs
        if "database" in self._page_indices:
            self.content_stack.setCurrentIndex(self._page_indices["database"])
            self._collapse_details_panel()  # Details panel not needed for databases

        # Get connection from DatabaseManager (may need to connect first)
        connection = self._database_manager.connections.get(db_id)
        db_conn = self._database_manager._get_connection_by_id(db_id)

        if not db_conn:
            DialogHelper.warning("Database configuration not found.", parent=self)
            return

        # If not connected, try to connect
        if not connection:
            try:
                connection = self._database_manager.reconnect_database(db_id)
                if not connection:
                    DialogHelper.error(
                        f"Failed to connect to {db_conn.name}.\n"
                        f"Échec de la connexion à {db_conn.name}.",
                        parent=self
                    )
                    return
            except Exception as e:
                DialogHelper.error(f"Connection error: {e}", parent=self)
                return

        # Create new tab (always new, don't reuse existing)
        tab_name = f"Query {self._query_tab_counter}"
        self._query_tab_counter += 1

        query_tab = QueryTab(
            parent=self,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name,
            database_manager=self._database_manager
        )

        # Connect query_saved signal to refresh
        query_tab.query_saved.connect(self.refresh_queries)

        # Add to tab widget
        index = self.query_tab_widget.addTab(query_tab, tab_name)
        self.query_tab_widget.setCurrentIndex(index)

        logger.info(f"Created empty query tab: {tab_name} for {db_conn.name}")

    def _execute_query_for_table(self, data: dict, limit: int = 100):
        """Execute a SELECT query for a table/view in our query tab."""
        table_name = data.get("name", "")
        db_id = data.get("db_id")
        db_name = data.get("db_name")

        if not db_id or not table_name:
            return

        # Switch to database page and collapse details panel
        if "database" in self._page_indices:
            self.content_stack.setCurrentIndex(self._page_indices["database"])
            self._collapse_details_panel()

        # Get or create query tab
        query_tab = self._get_or_create_query_tab(db_id, db_name)
        if not query_tab:
            return

        # Generate query based on database type
        db_conn = self._database_manager._get_connection_by_id(db_id)
        if not db_conn:
            return

        if db_conn.db_type == "sqlite":
            if limit:
                query = f"SELECT * FROM {table_name} LIMIT {limit}"
            else:
                query = f"SELECT * FROM {table_name}"
        elif db_conn.db_type == "sqlserver" and db_name:
            # SQL Server: use fully qualified name [database].[schema].[table]
            full_table_name = f"[{db_name}].{table_name}"
            if limit:
                query = f"SELECT TOP {limit} * FROM {full_table_name}"
            else:
                query = f"SELECT * FROM {full_table_name}"
        else:
            # Other databases
            if limit:
                query = f"SELECT TOP {limit} * FROM {table_name}"
            else:
                query = f"SELECT * FROM {table_name}"

        # Set query and execute
        query_tab.set_query_text(query)
        query_tab._execute_query()

    # ==================== File Content Loading ====================

    def _load_file_content(self, file_path: Path):
        """Load and display file content in the file viewer."""
        if not file_path.exists() or not file_path.is_file():
            return

        if not hasattr(self, 'file_viewer_stack'):
            return

        # Switch to rootfolder page in content stack
        if "rootfolder" in self._page_indices:
            self.content_stack.setCurrentIndex(self._page_indices["rootfolder"])

        ext = file_path.suffix.lower()

        try:
            # CSV files
            if ext == ".csv":
                self._load_csv_file(file_path)

            # Excel files
            elif ext in (".xlsx", ".xls"):
                self._load_excel_file(file_path)

            # JSON files
            elif ext == ".json":
                self._load_json_file(file_path)

            # Text files (py, sql, txt, md, etc.)
            elif ext in (".txt", ".py", ".sql", ".md", ".log", ".ini", ".cfg", ".xml", ".html", ".css", ".js"):
                self._load_text_file(file_path)

            else:
                # Unknown type - try as text
                self._load_text_file(file_path)

        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            self.file_text_viewer.setPlainText(f"Erreur lors du chargement: {str(e)}")
            self.file_viewer_stack.setCurrentIndex(1)  # Text viewer

    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding by trying multiple encodings.

        Returns the encoding name that successfully reads the file.
        """
        # Try common encodings in order of likelihood
        encodings_to_try = [
            'utf-8-sig',  # UTF-8 with BOM (common in Windows)
            'utf-8',      # Standard UTF-8
            'cp1252',     # Windows Western European
            'iso-8859-1', # Latin-1
            'cp850',      # DOS Western European
            'utf-16',     # UTF-16 with BOM
        ]

        # Read raw bytes to check for BOM
        with open(file_path, 'rb') as f:
            raw = f.read(4096)

        # Check for BOM markers
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        elif raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            return 'utf-16'

        # Try each encoding
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()  # Try to read entire file
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue

        # Fallback to latin-1 (never fails)
        return 'iso-8859-1'

    def _load_csv_file(self, file_path: Path):
        """Load CSV file into grid viewer using DataFrame-Pivot pattern."""
        # Use centralized data_loader
        result = csv_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                self.file_text_viewer.setPlainText(f"Erreur: {str(result.error)}")
                self.file_viewer_stack.setCurrentIndex(1)
            return

        # Store detected values for display
        self._detected_encoding = result.source_info.get('encoding')
        self._detected_separator = result.source_info.get('separator')
        self._detected_delimiter = '"'  # pandas default

        df = result.dataframe
        if df is not None and not df.empty:
            # Use optimized set_dataframe method
            self.file_grid_viewer.set_dataframe(df)
            self.file_viewer_stack.setCurrentIndex(0)  # Grid viewer

            # Update details with encoding info
            self._update_file_encoding_details(file_path)

            logger.info(f"CSV loaded: {result.row_count} rows, encoding={self._detected_encoding}")
        else:
            self.file_text_viewer.setPlainText("(Fichier CSV vide)")
            self.file_viewer_stack.setCurrentIndex(1)

    def _load_excel_file(self, file_path: Path):
        """Load Excel file into grid viewer using DataFrame-Pivot pattern."""
        # Use centralized data_loader
        result = excel_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                error_msg = str(result.error)
                if "openpyxl" in error_msg.lower() or "xlrd" in error_msg.lower():
                    self.file_text_viewer.setPlainText(
                        "Module openpyxl non installé.\n"
                        "Installez-le avec: pip install openpyxl"
                    )
                else:
                    self.file_text_viewer.setPlainText(f"Erreur: {error_msg}")
                self.file_viewer_stack.setCurrentIndex(1)
            return

        # Store info for display
        self._detected_encoding = "Excel Binary"
        self._detected_separator = None
        self._detected_delimiter = None

        df = result.dataframe
        if df is not None and not df.empty:
            # Use optimized set_dataframe method
            self.file_grid_viewer.set_dataframe(df)
            self.file_viewer_stack.setCurrentIndex(0)

            # Update details
            sheets = result.source_info.get('available_sheets', [])
            logger.info(f"Excel loaded: {result.row_count} rows, sheets={sheets}")
        else:
            self.file_text_viewer.setPlainText("(Fichier Excel vide)")
            self.file_viewer_stack.setCurrentIndex(1)

    def _load_json_file(self, file_path: Path):
        """Load JSON file - try as table first, fallback to formatted text."""
        import json

        # First, try loading as tabular data using DataFrame-Pivot
        result = json_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        # Store encoding info
        self._detected_encoding = result.source_info.get('encoding', 'utf-8')
        self._detected_separator = None
        self._detected_delimiter = None

        # If successfully loaded as table with multiple rows, show in grid
        if result.success and result.dataframe is not None and len(result.dataframe) > 1:
            df = result.dataframe
            self.file_grid_viewer.set_dataframe(df)
            self.file_viewer_stack.setCurrentIndex(0)  # Grid viewer
            self._update_file_encoding_details(file_path)
            logger.info(f"JSON loaded as table: {result.row_count} rows")
            return

        # Fallback: display as formatted JSON text
        encoding = self._detect_encoding(file_path)
        self._detected_encoding = encoding

        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        try:
            data = json.loads(content)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.file_text_viewer.setPlainText(formatted)
        except json.JSONDecodeError:
            self.file_text_viewer.setPlainText(content)

        self.file_viewer_stack.setCurrentIndex(1)  # Text viewer
        self._update_file_encoding_details(file_path)

    def _load_text_file(self, file_path: Path):
        """Load text file into text viewer with proper encoding detection."""
        # Detect encoding
        encoding = self._detect_encoding(file_path)
        self._detected_encoding = encoding
        self._detected_separator = None  # Not applicable for text files
        self._detected_delimiter = None

        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        self.file_text_viewer.setPlainText(content)
        self.file_viewer_stack.setCurrentIndex(1)  # Text viewer
        self._update_file_encoding_details(file_path)

    def _update_file_encoding_details(self, file_path: Path):
        """Update the details panel with file info including encoding, separator, delimiter."""
        try:
            stat = file_path.stat()

            # Format size
            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.2f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

            file_type = file_path.suffix.upper()[1:] if file_path.suffix else "File"

            # Format modified date
            from datetime import datetime
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

            # Update details form
            self.details_form_builder.set_value("name", file_path.name)
            self.details_form_builder.set_value("resource_type", f"{file_type} ({size_str})")
            self.details_form_builder.set_value("description", f"Modified: {modified}")
            self.details_form_builder.set_value("path", str(file_path))

            # Show encoding
            encoding_display = self._detected_encoding.upper() if self._detected_encoding else "-"
            self.details_form_builder.set_value("encoding", encoding_display)

            # Show separator (with friendly names)
            separator_names = {
                ',': 'Comma (,)',
                ';': 'Semicolon (;)',
                '\t': 'Tab (\\t)',
                '|': 'Pipe (|)',
                ' ': 'Space',
            }
            if self._detected_separator:
                sep_display = separator_names.get(self._detected_separator, f"'{self._detected_separator}'")
            else:
                sep_display = "-"
            self.details_form_builder.set_value("separator", sep_display)

            # Show delimiter (quote character)
            delimiter_names = {
                '"': 'Double quote (")',
                "'": "Single quote (')",
            }
            if self._detected_delimiter:
                delim_display = delimiter_names.get(self._detected_delimiter, f"'{self._detected_delimiter}'")
            else:
                delim_display = "-"
            self.details_form_builder.set_value("delimiter", delim_display)

        except Exception as e:
            logger.error(f"Error updating file details: {e}")

    def _handle_large_dataset_warning(self, row_count: int) -> bool:
        """
        Handle warning for large datasets (> 100k rows).

        Args:
            row_count: Number of rows detected

        Returns:
            True to proceed with loading, False to cancel
        """
        from PySide6.QtWidgets import QMessageBox

        # Format numbers with thousands separator
        row_count_fmt = f"{row_count:,}"
        threshold_fmt = f"{LARGE_DATASET_THRESHOLD:,}"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Large Dataset Warning")
        msg.setText(f"This file contains {row_count_fmt} rows.")
        msg.setInformativeText(
            f"Loading more than {threshold_fmt} rows may:\n"
            f"• Be slow to load\n"
            f"• Consume significant memory\n"
            f"• Slow down the interface\n\n"
            f"Do you want to continue?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        result = msg.exec()
        return result == QMessageBox.StandardButton.Yes

    # ==================== Saved Query Execution ====================

    def _load_saved_query(self, query_obj):
        """
        Load a saved query into the query editor panel.

        Args:
            query_obj: SavedQuery object from database
        """
        import pandas as pd

        # Store current query object
        self._current_query_obj = query_obj

        # Switch to query page
        if "query" in self._page_indices:
            self.content_stack.setCurrentIndex(self._page_indices["query"])

        # Load query text into editor
        query_text = getattr(query_obj, 'query_text', '') or ''
        self.query_sql_editor.setPlainText(query_text)

        # Get the target database connection
        target_db_id = getattr(query_obj, 'target_database_id', None)
        logger.info(f"Query target_database_id: {target_db_id}")

        if target_db_id and self._database_manager:
            db_conn = self._database_manager._get_connection_by_id(target_db_id)
            logger.info(f"Found db_conn: {db_conn.name if db_conn else 'None'}")

            if db_conn:
                # Get existing connection (may be None - will auto-connect on execute)
                connection = self._database_manager.connections.get(db_conn.id)

                self._current_query_connection = connection
                self._current_query_db_conn = db_conn

                # Always show simple "Execute" - auto-connect happens transparently
                self.query_execute_btn.setText(f"▶ Execute on {db_conn.name} (F5)")
            else:
                self._current_query_connection = None
                self._current_query_db_conn = None
                self.query_execute_btn.setText(f"▶ Execute (F5) - DB ID not found: {target_db_id[:8]}...")
        else:
            self._current_query_connection = None
            self._current_query_db_conn = None
            if not target_db_id:
                self.query_execute_btn.setText("▶ Execute (F5) - No target DB in query")
            elif not self._database_manager:
                self.query_execute_btn.setText("▶ Execute (F5) - No DB manager")

        # Clear previous results
        self.query_results_grid.set_dataframe(pd.DataFrame())

        # Update details panel
        query_name = getattr(query_obj, 'name', 'Query')
        description = getattr(query_obj, 'description', '') or ''
        created = getattr(query_obj, 'created_at', '') or ''
        modified = getattr(query_obj, 'updated_at', '') or ''

        self.details_form_builder.set_value("name", query_name)
        self.details_form_builder.set_value("resource_type", "Saved Query")
        self.details_form_builder.set_value("description", description)
        self.details_form_builder.set_value("path", f"Created: {created}")
        self.details_form_builder.set_value("encoding", "-")
        self.details_form_builder.set_value("separator", "-")
        self.details_form_builder.set_value("delimiter", "-")

        logger.info(f"Loaded saved query: {query_name}")

    def _update_saved_query(self):
        """Update the current saved query with the text from the editor."""
        if not self._current_query_obj:
            DialogHelper.warning(
                "No saved query loaded.\nAucune requête enregistrée chargée.",
                parent=self
            )
            return

        # Get new query text
        new_query_text = self.query_sql_editor.toPlainText().strip()
        if not new_query_text:
            DialogHelper.warning(
                "Query text is empty.\nLe texte de la requête est vide.",
                parent=self
            )
            return

        # Confirm update
        query_name = getattr(self._current_query_obj, 'name', 'Query')
        if not DialogHelper.confirm(
            f"Update query '{query_name}' with current SQL text?\n"
            f"Mettre à jour la requête '{query_name}' avec le texte SQL actuel ?",
            parent=self
        ):
            return

        try:
            config_db = get_config_db()

            # Update the query object
            self._current_query_obj.query_text = new_query_text

            # Save to database
            if config_db.update_saved_query(self._current_query_obj):
                DialogHelper.info(
                    f"Query '{query_name}' updated successfully.\n"
                    f"Requête '{query_name}' mise à jour avec succès.",
                    parent=self
                )
                logger.info(f"Updated saved query: {query_name}")
            else:
                DialogHelper.error(
                    f"Failed to update query '{query_name}'.\n"
                    f"Échec de la mise à jour de la requête '{query_name}'.",
                    parent=self
                )

        except Exception as e:
            logger.error(f"Error updating saved query: {e}")
            DialogHelper.error(
                f"Error updating query: {e}\nErreur lors de la mise à jour: {e}",
                parent=self
            )

    def _execute_saved_query(self):
        """Execute the saved query in the editor."""
        import pandas as pd

        # Check if we have a database config but no active connection
        if not self._current_query_connection and self._current_query_db_conn and self._database_manager:
            # Try to establish connection first
            db_conn = self._current_query_db_conn
            self.query_execute_btn.setEnabled(False)
            self.query_execute_btn.setText(f"⏳ Connecting to {db_conn.name}...")
            QApplication.processEvents()

            try:
                # Use reconnect_database which handles connection creation
                connection = self._database_manager.reconnect_database(db_conn.id)
                if connection:
                    self._current_query_connection = connection
                    logger.info(f"Auto-connected to database: {db_conn.name}")
                else:
                    self.query_execute_btn.setText(f"▶ Execute on {db_conn.name} (F5)")
                    self.query_execute_btn.setEnabled(True)
                    DialogHelper.error(
                        f"Failed to connect to {db_conn.name}.\n"
                        f"Échec de la connexion à {db_conn.name}.",
                        parent=self
                    )
                    return
            except Exception as e:
                self.query_execute_btn.setText(f"▶ Execute on {db_conn.name} (F5)")
                self.query_execute_btn.setEnabled(True)
                DialogHelper.error(
                    f"Connection error: {e}\nErreur de connexion: {e}",
                    parent=self
                )
                return

        if not self._current_query_connection:
            DialogHelper.error(
                "No database connection available.\n"
                "Aucune connexion à la base de données disponible.",
                parent=self
            )
            return

        query_text = self.query_sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning("No query to execute.\nAucune requête à exécuter.", parent=self)
            return

        # Show loading state
        self.query_execute_btn.setEnabled(False)
        self.query_execute_btn.setText("⏳ Executing...")
        QApplication.processEvents()

        try:
            # Execute query
            cursor = self._current_query_connection.cursor()
            cursor.execute(query_text)

            # Check if this is a SELECT query (has results)
            if cursor.description:
                # Fetch results
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                # Convert to DataFrame
                df = pd.DataFrame.from_records(rows, columns=columns)
                self.query_results_grid.set_dataframe(df)

                logger.info(f"Query returned {len(df)} rows")
            else:
                # Non-SELECT query (INSERT, UPDATE, DELETE, etc.)
                rows_affected = cursor.rowcount
                self._current_query_connection.commit()

                # Show message
                self.query_results_grid.set_dataframe(pd.DataFrame({
                    "Result": [f"{rows_affected} row(s) affected"]
                }))

                logger.info(f"Query executed: {rows_affected} rows affected")

            cursor.close()

        except Exception as e:
            logger.error(f"Query execution error: {e}")

            # Check if connection error
            error_str = str(e).lower()
            connection_indicators = [
                "communication link failure", "tcp provider", "connection failure",
                "network-related", "connection was forcibly closed"
            ]

            if any(ind in error_str for ind in connection_indicators):
                # Connection lost - offer reconnection
                from PySide6.QtWidgets import QMessageBox
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle("Connection Error")
                msg.setText("Database connection lost.\nLa connexion a été perdue.")
                msg.setInformativeText("Would you like to reconnect?\nVoulez-vous vous reconnecter ?")
                reconnect_btn = msg.addButton("Reconnect", QMessageBox.ButtonRole.AcceptRole)
                msg.addButton(QMessageBox.StandardButton.Cancel)
                msg.exec()

                if msg.clickedButton() == reconnect_btn:
                    self._reconnect_saved_query()
            else:
                # Show error in results
                self.query_results_grid.set_dataframe(pd.DataFrame({
                    "Error": [str(e)]
                }))

        finally:
            # Restore button
            db_name = getattr(self._current_query_db_conn, 'name', 'DB') if self._current_query_db_conn else 'DB'
            self.query_execute_btn.setText(f"▶ Execute on {db_name} (F5)")
            self.query_execute_btn.setEnabled(True)

    def _reconnect_saved_query(self):
        """Reconnect to the database for saved query execution."""
        if not self._current_query_db_conn or not self._database_manager:
            return

        try:
            # Reconnect via DatabaseManager
            new_connection = self._database_manager.reconnect_database(self._current_query_db_conn.id)
            if new_connection:
                self._current_query_connection = new_connection
                DialogHelper.info("Reconnected successfully.\nReconnexion réussie.", parent=self)
            else:
                DialogHelper.error("Reconnection failed.\nÉchec de la reconnexion.", parent=self)
        except Exception as e:
            DialogHelper.error(f"Reconnection error: {e}", parent=self)
