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
from .content_handlers import FileContentHandler, ImageContentHandler
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db
from ...utils.image_loader import get_icon, get_database_icon, get_database_icon_with_dot, get_auto_color
from ...constants import QUERY_PREVIEW_LIMIT

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
    manager_selected = Signal(str)  # manager_id when switching to a specific manager

    # Signal emitted when user wants to open the Image Library Manager
    open_image_library_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, title=tr("menu_view"))

        self._category_items = {}
        self._workspace_filter: Optional[str] = None  # Workspace filter ID

        # Manager references (set via set_managers)
        self._database_manager = None
        self._rootfolder_manager = None
        self._ftproot_manager = None
        self._queries_manager = None
        self._jobs_manager = None
        self._scripts_manager = None
        self._image_library_manager = None

        # Image navigation
        self._image_nav_list = []
        self._image_nav_index = 0

        # Tree item references (for image navigation sync)
        self._tree_items = {}

        # FTP pending expansion (when connecting)
        self._pending_ftp_expansion = None

        # Initialize tree configuration
        self._init_tree_config()

    # ==================== Workspace Filtering ====================

    def set_workspace_filter(self, workspace_id: Optional[str]):
        """
        Set workspace filter and refresh the view.

        Args:
            workspace_id: Workspace ID to filter by, or None for all items
        """
        self._workspace_filter = workspace_id
        self.refresh()

    def get_workspace_filter(self) -> Optional[str]:
        """Get the current workspace filter ID."""
        return self._workspace_filter

    # ==================== Initialization ====================

    def _init_tree_config(self):
        """Configure tree widget behavior. Called from base class."""
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

    def _get_panel_title(self) -> str:
        """Return title for the left pinnable panel."""
        return tr("panel_resources")

    def _get_panel_icon(self) -> str:
        """Return icon name for the left pinnable panel."""
        return "databases.png"

    def set_managers(self, database_manager=None, rootfolder_manager=None,
                     ftproot_manager=None, queries_manager=None, jobs_manager=None,
                     scripts_manager=None, image_library_manager=None):
        """Set references to managers for delegation and add their content to stack."""
        self._database_manager = database_manager
        self._rootfolder_manager = rootfolder_manager
        self._ftproot_manager = ftproot_manager
        self._queries_manager = queries_manager
        self._jobs_manager = jobs_manager
        self._scripts_manager = scripts_manager
        self._image_library_manager = image_library_manager

        # Connect to FTPRootManager signals for connection state updates
        if self._ftproot_manager:
            self._ftproot_manager.connection_established.connect(self._on_ftp_connection_established)

        # Connect query_saved signal for auto-refresh of queries list
        if self._database_manager:
            self._database_manager.query_saved.connect(self.refresh_queries)

        # Add manager right panels to the stack (composition)
        self._setup_manager_pages()

    def _setup_manager_pages(self):
        """Add manager content widgets to the stacked widget."""
        from ..widgets.editable_tab_widget import EditableTabWidget

        # Page 2: DatabaseManager's right panel - QTabWidget with QueryTabs
        # (Page 0 = generic, Page 1 = query editor - created in _setup_content)
        if self._database_manager:
            db_wrapper = QWidget()
            db_layout = QVBoxLayout(db_wrapper)
            db_layout.setContentsMargins(0, 0, 0, 0)

            # Create our own EditableTabWidget for query tabs
            self.query_tab_widget = EditableTabWidget()
            self.query_tab_widget.setTabsClosable(True)
            self.query_tab_widget.setMovable(True)
            self.query_tab_widget.tabCloseRequested.connect(
                lambda idx: self._database_manager._close_tab(idx, self.query_tab_widget)
            )

            db_layout.addWidget(self.query_tab_widget)

            self.content_stack.addWidget(db_wrapper)
            self._page_indices["database"] = self.content_stack.count() - 1

        # Page 3: RootFolderManager's right panel (file viewer via FileContentHandler)
        if self._rootfolder_manager:
            self._file_handler = FileContentHandler(self, self.details_form_builder)
            self.content_stack.addWidget(self._file_handler.get_widget())
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
            .add_field(tr("field_encoding"), "encoding") \
            .add_field(tr("field_separator"), "separator") \
            .add_field(tr("field_delimiter"), "delimiter")

        details_widget = self.details_form_builder.build()
        self.details_layout.addWidget(details_widget)

        # Content handlers (created after form_builder is ready)
        self._file_handler: Optional[FileContentHandler] = None
        self._image_handler: Optional[ImageContentHandler] = None

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
        generic_label = QLabel(tr("select_item_for_content"))
        generic_label.setStyleSheet("color: gray;")
        generic_layout.addWidget(generic_label)
        self.content_stack.addWidget(generic_widget)

        # Page 1: Query editor + results (for saved queries)
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        query_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar for query execution
        query_toolbar = QHBoxLayout()
        self.query_execute_btn = QPushButton(tr("query_execute_f5"))
        self.query_execute_btn.clicked.connect(self._execute_saved_query)
        query_toolbar.addWidget(self.query_execute_btn)

        self.query_update_btn = QPushButton("💾 " + tr("btn_update_query"))
        self.query_update_btn.clicked.connect(self._update_saved_query)
        self.query_update_btn.setToolTip(tr("tooltip_update_query"))
        query_toolbar.addWidget(self.query_update_btn)

        query_toolbar.addStretch()
        query_layout.addLayout(query_toolbar)

        # Splitter: SQL editor (top) + Results (bottom)
        query_splitter = QSplitter(Qt.Orientation.Vertical)

        # SQL Editor
        self.query_sql_editor = QTextEdit()
        self.query_sql_editor.setPlaceholderText(tr("placeholder_sql_query"))
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

        # Page 2: Image preview (via ImageContentHandler)
        self._image_handler = ImageContentHandler(self, self.details_form_builder)
        self._image_handler.set_tree_items(self._tree_items)
        self._image_handler.images_refreshed.connect(self.refresh_images)
        self.content_stack.addWidget(self._image_handler.get_widget())

        # Pages for managers will be added in set_managers()
        self._page_indices = {"generic": 0, "query": 1, "image": 2}

        # Current query context
        self._current_query_obj = None
        self._current_query_connection = None
        self._current_query_db_conn = None

        # Current image context
        self._current_image_obj = None

    def _load_items(self):
        """Load all resources into tree, filtered by workspace if set."""
        try:
            config_db = get_config_db()
            self._category_items = {}

            # Categories
            categories = [
                ("databases", tr("menu_database")),
                ("rootfolders", tr("category_rootfolders")),
                ("ftproots", "FTP"),
                ("queries", tr("menu_queries")),
                ("images", tr("category_images")),
                ("jobs", tr("menu_jobs")),
                ("scripts", tr("menu_scripts")),
            ]

            for key, label in categories:
                self._add_category(key, label)

            # Databases - with expand capability (workspace filtered)
            if self._workspace_filter:
                databases = config_db.get_workspace_database_connections(self._workspace_filter)
            else:
                databases = config_db.get_all_database_connections()
            for i, db in enumerate(databases):
                item = self.tree_view.add_item(
                    parent=self._category_items["databases"],
                    text=[db.name],
                    data={"type": "database", "id": db.id, "obj": db}
                )
                color = db.color or get_auto_color(i)
                db_icon = get_database_icon_with_dot(db.db_type, color)
                if db_icon:
                    item.setIcon(0, db_icon)
                self._add_dummy_child(item)

            # Rootfolders - with expand capability (workspace filtered)
            if self._workspace_filter:
                rootfolders = config_db.get_workspace_file_roots(self._workspace_filter)
            else:
                rootfolders = config_db.get_all_file_roots()
            for rf in rootfolders:
                item = self.tree_view.add_item(
                    parent=self._category_items["rootfolders"],
                    text=[rf.name or rf.path],
                    data={"type": "rootfolder", "id": rf.id, "obj": rf, "path": rf.path}
                )
                self._set_item_icon(item, "folder")
                self._add_dummy_child(item)

            # FTP Roots - workspace filtered (with expansion support like rootfolders)
            if self._workspace_filter:
                ftp_roots = config_db.get_workspace_ftp_roots(self._workspace_filter)
            else:
                ftp_roots = config_db.get_all_ftp_roots()
            for ftp in ftp_roots:
                display_name = ftp.name or f"{ftp.protocol.upper()}://{ftp.host}"
                # Check if connected via FTPRootManager
                is_connected = self._ftproot_manager and self._ftproot_manager.is_connected(ftp.id)
                status = tr("res_connected") if is_connected else ""
                item = self.tree_view.add_item(
                    parent=self._category_items["ftproots"],
                    text=[f"{display_name}{status}"],
                    data={"type": "ftproot", "id": ftp.id, "obj": ftp, "connected": is_connected}
                )
                # Icon based on connection state
                icon_name = "ftp_connected" if is_connected else "ftp"
                self._set_item_icon(item, icon_name)
                # Add dummy child for expansion (like rootfolders)
                self._add_dummy_child(item)

            # Queries - grouped by category (workspace filtered)
            if self._workspace_filter:
                queries = config_db.get_workspace_queries(self._workspace_filter)
            else:
                queries = config_db.get_all_saved_queries()

            # Group queries by category
            queries_by_category = {}
            for query in queries:
                cat = query.category or tr("category_no_category")
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

            # Images - only logical categories (user-defined)
            # Images without categories are only visible in ImageLibraryManager
            self._image_category_items = {}
            category_names = config_db.get_all_image_category_names()

            # Always add "Open Image Manager" action item first
            open_manager_item = self.tree_view.add_item(
                parent=self._category_items["images"],
                text=["📷 " + tr("btn_open_image_manager")],
                data={"type": "open_image_manager"}
            )

            for category_name in sorted(category_names):
                images_in_cat = config_db.get_images_by_category(category_name)
                if not images_in_cat:
                    continue

                # Create category folder
                cat_item = self.tree_view.add_item(
                    parent=self._category_items["images"],
                    text=[f"{category_name} ({len(images_in_cat)})"],
                    data={"type": "image_category", "name": category_name}
                )
                self._set_item_icon(cat_item, "folder")
                self._image_category_items[category_name] = cat_item

                # Add images under this category
                for image in images_in_cat:
                    # Check if image has tags for indicator
                    tags = config_db.get_image_tags(image.id)
                    indicator = " ⭐" if tags else ""
                    item = self.tree_view.add_item(
                        parent=cat_item,
                        text=[f"{image.name}{indicator}"],
                        data={"type": "image", "id": image.id, "obj": image}
                    )
                    self._set_item_icon(item, "file")
                    # Store for navigation
                    self._tree_items[f"img_{image.id}"] = item

            # Jobs (workspace filtered)
            if self._workspace_filter:
                jobs = config_db.get_workspace_jobs(self._workspace_filter)
            else:
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
            if key == "rootfolders":
                # For rootfolders, count total files in all root folders
                count = self._count_rootfolder_files(item)
            else:
                count = self._count_leaf_items(item)
            text = item.text(0).split(" (")[0]
            item.setText(0, f"{text} ({count})")

    def _count_rootfolder_files(self, category_item: QTreeWidgetItem) -> int:
        """
        Count total files (not folders) in all root folders.

        Scans the filesystem recursively for each rootfolder to count files.

        Args:
            category_item: The Rootfolders category item

        Returns:
            Total count of files across all root folders
        """
        total_files = 0

        for i in range(category_item.childCount()):
            child = category_item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole) or {}

            if data.get("type") == "rootfolder":
                path_str = data.get("path")
                if path_str:
                    root_path = Path(path_str)
                    if root_path.exists() and root_path.is_dir():
                        try:
                            # Count files recursively (not directories)
                            for _ in root_path.rglob("*"):
                                if _.is_file():
                                    total_files += 1
                        except PermissionError:
                            # Skip folders we can't access
                            pass
                        except Exception as e:
                            logger.warning(f"Error counting files in {root_path}: {e}")

        return total_files

    def _count_leaf_items(self, item: QTreeWidgetItem) -> int:
        """
        Recursively count all leaf items (non-folder items) in a subtree.

        For categories like Queries, this counts the total number of saved queries (not categories).
        For Images, this counts the total number of images.
        For Databases/Rootfolders, counts the number of connections/roots (not expanded content).

        Args:
            item: The parent item to count children for

        Returns:
            Total count of leaf items in the subtree
        """
        count = 0
        for i in range(item.childCount()):
            child = item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole) or {}
            item_type = data.get("type", "")

            # Skip dummy items (for lazy loading)
            if item_type == "dummy":
                continue

            # Special items to skip counting
            if item_type in ("open_image_manager",):
                continue

            # Category/folder types that group items - recurse into them
            if item_type in ("query_category", "image_category"):
                count += self._count_leaf_items(child)
            else:
                # All other items are counted as leaf items:
                # database, rootfolder, query, job, script, image, file, table, view, etc.
                count += 1

        return count

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
                cat = query.category or tr("category_no_category")
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
        # Map category keys to actual icon filenames
        icon_map = {
            "ftproots": "ftp",
            "ftp_connected": "ftp_connected",
            "remote_folder": "folder",
        }
        actual_icon = icon_map.get(icon_name, icon_name)
        icon = get_icon(actual_icon)
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

        elif item_type in ("remote_folder", "remote_file"):
            # Show FTP item details
            self._expand_details_panel()
            self._display_remote_item(item_data)
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
            "ftproot": f"FTP ({getattr(obj, 'protocol', 'ftp').upper()})",
            "query": "Query",
            "job": "Job",
            "script": "Script",
        }

        # Special handling for FTP roots
        if item_type == "ftproot":
            host = getattr(obj, "host", "")
            port = getattr(obj, "port", "")
            path = f"{host}:{port}"

        self.details_form_builder.set_value("name", name)
        self.details_form_builder.set_value("resource_type", type_labels.get(item_type, item_type))
        self.details_form_builder.set_value("description", description)
        self.details_form_builder.set_value("path", path)
        self.details_form_builder.set_value("encoding", "-")
        self.details_form_builder.set_value("separator", "-")
        self.details_form_builder.set_value("delimiter", "-")

    def _display_file_item(self, item_data: dict):
        """Display file/folder item details in the details panel."""
        if self._file_handler:
            self._file_handler.update_details_for_item(item_data)

    def _display_remote_item(self, item_data: dict):
        """Display remote FTP file/folder details in the details panel."""
        from ..utils.tree_helpers import format_file_size

        item_type = item_data.get("type", "")
        name = item_data.get("name", "-")
        path = item_data.get("path", "-")

        if item_type == "remote_folder":
            self.details_form_builder.set_value("name", name)
            self.details_form_builder.set_value("resource_type", "Dossier distant (FTP)")
            self.details_form_builder.set_value("description", "")
            self.details_form_builder.set_value("path", path)
            self.details_form_builder.set_value("encoding", "-")
            self.details_form_builder.set_value("separator", "-")
            self.details_form_builder.set_value("delimiter", "-")
        elif item_type == "remote_file":
            size = item_data.get("size", 0)
            size_str = format_file_size(size) if size else "-"
            self.details_form_builder.set_value("name", name)
            self.details_form_builder.set_value("resource_type", tr("res_remote_file_ftp"))
            self.details_form_builder.set_value("description", tr("res_size_label", size=size_str))
            self.details_form_builder.set_value("path", path)
            self.details_form_builder.set_value("encoding", "-")
            self.details_form_builder.set_value("separator", "-")
            self.details_form_builder.set_value("delimiter", "-")

    def _on_tree_double_click(self, item, column):
        """Double-click: expand/collapse items, or open files/queries."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        if item_type in ("category", "database", "server", "rootfolder", "folder",
                         "tables_folder", "views_folder", "table", "view",
                         "query_category", "image_category"):
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

        elif item_type == "image":
            # Load and display image preview
            image_obj = data.get("obj")
            if image_obj:
                self._load_image_preview(image_obj)

        elif item_type == "open_image_manager":
            # Open dedicated Image Library Manager
            self._open_image_library_manager()

        elif item_type == "ftproot":
            # FTP: connect if not connected, expand if connected (same as FTPRootManager)
            if self._ftproot_manager:
                ftp_obj = data.get("obj")
                if data.get("connected"):
                    # Already connected - toggle expand
                    item.setExpanded(not item.isExpanded())
                else:
                    # Not connected - trigger connection via FTPRootManager
                    self._ftproot_manager._connect_ftp_root(ftp_obj)
                    # Store pending expansion for when connection completes
                    self._pending_ftp_expansion = item

        elif item_type == "remote_folder":
            # Toggle expand/collapse for remote folders
            item.setExpanded(not item.isExpanded())

        elif item_type == "remote_file":
            # Preview remote file via FTPRootManager
            if self._ftproot_manager:
                self._ftproot_manager._preview_remote_file(data)

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
                        dummy.setText(0, tr("double_click_to_load"))
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
                elif item_type == "ftproot" and self._ftproot_manager:
                    self._load_ftproot_children(item, data)
                elif item_type == "remote_folder" and self._ftproot_manager:
                    self._load_remote_folder_children(item, data)
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

    # ==================== FTP Loading (delegates to FTPRootManager) ====================

    def _on_ftp_connection_established(self, ftp_root_id: str):
        """Handle FTP connection established - refresh tree and expand pending item."""
        # Refresh tree to show connected state
        self.refresh()

        # If there's a pending expansion, find and expand the item
        if self._pending_ftp_expansion:
            pending_data = self._pending_ftp_expansion.data(0, Qt.ItemDataRole.UserRole)
            if pending_data and pending_data.get("id") == ftp_root_id:
                # Find the new item (tree was refreshed, old item is invalid)
                for i in range(self._category_items["ftproots"].childCount()):
                    child = self._category_items["ftproots"].child(i)
                    child_data = child.data(0, Qt.ItemDataRole.UserRole)
                    if child_data and child_data.get("id") == ftp_root_id:
                        child.setExpanded(True)
                        break
            self._pending_ftp_expansion = None

    def _load_ftproot_children(self, parent_item: QTreeWidgetItem, data: dict):
        """Load FTP root contents - delegate to FTPRootManager."""
        if not self._ftproot_manager:
            return

        ftp_obj = data.get("obj")
        ftp_root_id = data.get("id")

        if not ftp_obj or not ftp_root_id:
            return

        # Check if connected
        if not self._ftproot_manager.is_connected(ftp_root_id):
            # Not connected - need to connect first
            # Re-add dummy child to allow retry
            self._add_dummy_child(parent_item)
            parent_item.setExpanded(False)
            # Trigger connection
            self._ftproot_manager._connect_ftp_root(ftp_obj)
            self._pending_ftp_expansion = parent_item
            return

        # Connected - load initial path using tree_helpers via FTPRootManager
        initial_path = ftp_obj.initial_path or "/"
        success = self._ftproot_manager.load_folder_to_tree(ftp_root_id, initial_path, parent_item)

        if not success:
            # Error loading - show message
            error_item = self.tree_view.add_item(
                parent=parent_item,
                text=[tr("res_load_error")],
                data={"type": "error"}
            )

    def _load_remote_folder_children(self, parent_item: QTreeWidgetItem, data: dict):
        """Load remote folder contents - delegate to FTPRootManager."""
        if not self._ftproot_manager:
            return

        ftp_root_id = data.get("ftproot_id")
        remote_path = data.get("path")

        if not ftp_root_id or not remote_path:
            return

        # Check if still connected
        if not self._ftproot_manager.is_connected(ftp_root_id):
            # Connection lost - show error
            error_item = self.tree_view.add_item(
                parent=parent_item,
                text=[tr("res_connection_lost")],
                data={"type": "error"}
            )
            return

        # Load folder contents using FTPRootManager's public API
        success = self._ftproot_manager.load_folder_to_tree(ftp_root_id, remote_path, parent_item)

        if not success:
            error_item = self.tree_view.add_item(
                parent=parent_item,
                text=[tr("res_load_error")],
                data={"type": "error"}
            )

    def _disconnect_ftp_and_refresh(self, ftp_root_id: str):
        """Disconnect FTP and refresh tree."""
        if self._ftproot_manager:
            self._ftproot_manager._disconnect_ftp_root(ftp_root_id)
            self.refresh()

    def _refresh_remote_folder(self, item: QTreeWidgetItem, data: dict):
        """Refresh a remote FTP folder."""
        # Clear children and re-add dummy
        while item.childCount() > 0:
            item.removeChild(item.child(0))
        self._add_dummy_child(item)

        # Collapse then expand to trigger reload
        item.setExpanded(False)
        item.setExpanded(True)

    def _download_remote_file(self, data: dict):
        """Download a remote FTP file via FTPRootManager."""
        if not self._ftproot_manager:
            return

        ftp_root_id = data.get("ftproot_id")
        if not self._ftproot_manager.is_connected(ftp_root_id):
            DialogHelper.warning(tr("res_ftp_not_connected"), parent=self)
            return

        # Use FTPRootManager's download functionality
        # We need to select the file in FTPRootManager first, then call download
        self._ftproot_manager._download_file_by_data(data)

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
                # For SQL Server sub-databases, "name" contains the database name
                db_name = data.get("name") if item_type == "database" else None
                # New Query Tab option
                new_tab_action = QAction(tr("btn_new_query_tab"), self)
                new_tab_action.triggered.connect(lambda: self._create_empty_query_tab(db_config.id, target_database=db_name))
                menu.addAction(new_tab_action)

                menu.addSeparator()

                refresh_action = QAction(tr("btn_refresh"), self)
                refresh_action.triggered.connect(lambda: self._refresh_database_item(item, db_config))
                menu.addAction(refresh_action)

        elif item_type in ("tables_folder", "views_folder"):
            # Tables/Views folder - expand/collapse
            if item.isExpanded():
                collapse_action = QAction(tr("menu_collapse"), self)
                collapse_action.triggered.connect(lambda: item.setExpanded(False))
                menu.addAction(collapse_action)
            else:
                expand_action = QAction(tr("menu_expand"), self)
                expand_action.triggered.connect(lambda: item.setExpanded(True))
                menu.addAction(expand_action)

        elif item_type in ("table", "view"):
            # Table/View context menu - execute queries in our query tab
            db_id = data.get("db_id")
            db_name = data.get("db_name")

            # New Query Tab option
            if db_id:
                new_tab_action = QAction(tr("btn_new_query_tab"), self)
                new_tab_action.triggered.connect(lambda: self._create_empty_query_tab(db_id, target_database=db_name))
                menu.addAction(new_tab_action)
                menu.addSeparator()

            # SELECT TOP 100 action
            select_top_action = QAction(tr("menu_select_top_100"), self)
            select_top_action.triggered.connect(lambda: self._execute_query_for_table(data, limit=QUERY_PREVIEW_LIMIT))
            menu.addAction(select_top_action)

            # SELECT * action
            select_all_action = QAction(tr("menu_select_all"), self)
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
                edit_action = QAction(tr("menu_edit_name_desc"), self)
                edit_action.triggered.connect(lambda: self._rootfolder_manager._edit_rootfolder(rootfolder_obj))
                menu.addAction(edit_action)

                menu.addSeparator()

                refresh_action = QAction(tr("btn_refresh"), self)
                refresh_action.triggered.connect(self.refresh)
                menu.addAction(refresh_action)

        elif item_type == "ftproot":
            # FTP Root context menu - same options as FTPRootManager
            ftp_obj = data.get("obj")
            is_connected = data.get("connected", False)

            if ftp_obj and self._ftproot_manager:
                if is_connected:
                    # Disconnect option
                    disconnect_action = QAction(tr("res_disconnect"), self)
                    disconnect_action.triggered.connect(
                        lambda: self._disconnect_ftp_and_refresh(ftp_obj.id))
                    menu.addAction(disconnect_action)
                else:
                    # Connect option
                    connect_action = QAction("Connecter", self)
                    connect_action.triggered.connect(
                        lambda: self._ftproot_manager._connect_ftp_root(ftp_obj))
                    menu.addAction(connect_action)

                menu.addSeparator()

                # Open in dedicated manager
                open_action = QAction("Ouvrir dans FTP Manager", self)
                open_action.triggered.connect(lambda: self.open_resource_requested.emit("ftproot", ftp_obj.id))
                menu.addAction(open_action)

                menu.addSeparator()

                refresh_action = QAction(tr("btn_refresh"), self)
                refresh_action.triggered.connect(self.refresh)
                menu.addAction(refresh_action)

        elif item_type == "remote_folder":
            # Remote FTP folder context menu
            ftp_root_id = data.get("ftproot_id")
            if ftp_root_id and self._ftproot_manager:
                refresh_action = QAction("Rafraîchir", self)
                refresh_action.triggered.connect(lambda: self._refresh_remote_folder(item, data))
                menu.addAction(refresh_action)

        elif item_type == "remote_file":
            # Remote FTP file context menu
            ftp_root_id = data.get("ftproot_id")
            if ftp_root_id and self._ftproot_manager:
                # Preview
                preview_action = QAction(tr("res_preview"), self)
                preview_action.triggered.connect(
                    lambda: self._ftproot_manager._preview_remote_file(data))
                menu.addAction(preview_action)

                # Download
                download_action = QAction(tr("res_download"), self)
                download_action.triggered.connect(
                    lambda: self._download_remote_file(data))
                menu.addAction(download_action)

        elif item_type == "folder":
            # Folder context menu
            path = data.get("path")
            if path:
                open_location_action = QAction(tr("menu_open_folder_location"), self)
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
                open_action = QAction(tr("open"), self)
                open_action.triggered.connect(lambda: self._rootfolder_manager._open_file(Path(path)))
                menu.addAction(open_action)

                open_location_action = QAction(tr("menu_open_file_location"), self)
                open_location_action.triggered.connect(lambda: self._rootfolder_manager._open_file_location(Path(path)))
                menu.addAction(open_location_action)

        elif item_type == "category" and data.get("category_key") == "images":
            # Images root category context menu
            open_manager_action = QAction("📷 " + tr("btn_open_image_manager"), self)
            open_manager_action.triggered.connect(self._open_image_library_manager)
            menu.addAction(open_manager_action)

            menu.addSeparator()
            menu.addAction(tr("btn_refresh"), self.refresh_images)

        elif item_type == "image_category":
            # Image category folder context menu (logical category)
            category_name = data.get("name", "")

            open_manager_action = QAction("📷 " + tr("btn_open_image_manager"), self)
            open_manager_action.triggered.connect(self._open_image_library_manager)
            menu.addAction(open_manager_action)

        elif item_type == "image":
            # Image item context menu
            image_obj = data.get("obj")
            if image_obj:
                # Open in explorer
                open_location_action = QAction("📂 Open in Explorer", self)
                open_location_action.triggered.connect(self._open_image_location)
                menu.addAction(open_location_action)

                # Copy to clipboard
                copy_action = QAction("📋 Copy to Clipboard", self)
                copy_action.triggered.connect(self._copy_image_to_clipboard)
                menu.addAction(copy_action)

                menu.addSeparator()

                # Edit
                edit_action = QAction("✏️ Edit", self)
                edit_action.triggered.connect(lambda: self._edit_image(image_obj))
                menu.addAction(edit_action)

                # Delete
                delete_action = QAction("🗑️ Delete", self)
                delete_action.triggered.connect(lambda: self._delete_image(image_obj))
                menu.addAction(delete_action)

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
        from ...utils.os_helpers import open_in_explorer
        open_in_explorer(path)

    # ==================== Query Tab Management ====================

    def _get_or_create_query_tab(self, db_id: str, db_name: str = None):
        """Get existing query tab for database or create new one (delegated to database_manager)."""
        if not self._database_manager:
            return None
        return self._database_manager._get_or_create_query_tab(
            db_id, target_tab_widget=self.query_tab_widget
        )

    def _create_empty_query_tab(self, db_id: str, target_database: str = None):
        """Create a new empty query tab for the given database (delegated to database_manager)."""
        if not self._database_manager:
            return

        # Switch to database page to show the query tabs
        if "database" in self._page_indices:
            self.content_stack.setCurrentIndex(self._page_indices["database"])
            self._collapse_details_panel()

        self._database_manager._new_query_tab(
            db_id=db_id, target_tab_widget=self.query_tab_widget,
            target_database=target_database
        )

    def _execute_query_for_table(self, data: dict, limit: int = 100):
        """Execute a SELECT query for a table/view (delegated to database_manager)."""
        if not self._database_manager:
            return

        # Switch to database page and collapse details panel
        if "database" in self._page_indices:
            self.content_stack.setCurrentIndex(self._page_indices["database"])
            self._collapse_details_panel()

        self._database_manager._generate_select_query(
            data, limit=limit, target_tab_widget=self.query_tab_widget
        )

    # ==================== File Content Loading ====================

    def _load_file_content(self, file_path: Path):
        """Load and display file content in the file viewer (delegated to FileContentHandler)."""
        if not self._file_handler:
            return

        # Switch to rootfolder page in content stack
        if "rootfolder" in self._page_indices:
            self.content_stack.setCurrentIndex(self._page_indices["rootfolder"])

        self._file_handler.load_file(file_path)

    # ==================== Image Preview ====================

    def _load_image_preview(self, image_obj):
        """Load and display an image in the preview panel (delegated to ImageContentHandler)."""
        if not self._image_handler:
            return

        # Switch to image page
        if "image" in self._page_indices:
            self.content_stack.setCurrentIndex(self._page_indices["image"])
            self._expand_details_panel()

        self._image_handler.load_image(image_obj)
        self._image_handler.build_navigation_list(image_obj, self.tree_view)

    def _navigate_image(self, direction: int):
        """Navigate to previous (-1) or next (+1) image (delegated to ImageContentHandler)."""
        if self._image_handler:
            self._image_handler.navigate(direction, self.tree_view)

    def keyPressEvent(self, event):
        """Handle key press events for image navigation."""
        from PySide6.QtCore import Qt as QtCore

        # Check if we're viewing an image via handler
        if self._image_handler and self._image_handler.has_navigation_list():
            if event.key() == QtCore.Key.Key_Left:
                self._navigate_image(-1)
                event.accept()
                return
            elif event.key() == QtCore.Key.Key_Right:
                self._navigate_image(1)
                event.accept()
                return

        # Default handling
        super().keyPressEvent(event)

    def refresh_images(self):
        """Refresh only the Images section of the tree (logical categories only)."""
        if "images" not in self._category_items:
            return

        images_item = self._category_items["images"]

        # Clear existing image children
        while images_item.childCount() > 0:
            images_item.removeChild(images_item.child(0))

        # Reload images - only logical categories (user-defined)
        try:
            config_db = get_config_db()
            category_names = config_db.get_all_image_category_names()

            # Always add "Open Image Manager" action item first
            open_manager_item = self.tree_view.add_item(
                parent=images_item,
                text=["📷 " + tr("btn_open_image_manager")],
                data={"type": "open_image_manager"}
            )

            self._image_category_items = {}
            total_images = 0

            for category_name in sorted(category_names):
                images_in_cat = config_db.get_images_by_category(category_name)
                if not images_in_cat:
                    continue

                cat_item = self.tree_view.add_item(
                    parent=images_item,
                    text=[f"{category_name} ({len(images_in_cat)})"],
                    data={"type": "image_category", "name": category_name}
                )
                self._set_item_icon(cat_item, "folder")
                self._image_category_items[category_name] = cat_item

                for image in images_in_cat:
                    tags = config_db.get_image_tags(image.id)
                    indicator = " ⭐" if tags else ""
                    item = self.tree_view.add_item(
                        parent=cat_item,
                        text=[f"{image.name}{indicator}"],
                        data={"type": "image", "id": image.id, "obj": image}
                    )
                    self._set_item_icon(item, "file")
                    self._tree_items[f"img_{image.id}"] = item
                    total_images += 1

                cat_item.setExpanded(True)

            # Update images category count
            count = images_item.childCount()
            text = images_item.text(0).split(" (")[0]
            images_item.setText(0, f"{text} ({count})")

            images_item.setExpanded(True)

            logger.info(f"Images refreshed: {total_images} images in {len(category_names)} categories")

        except Exception as e:
            logger.error(f"Error refreshing images: {e}")

    def _open_image_library_manager(self):
        """Emit signal to open the Image Library Manager."""
        self.open_image_library_requested.emit()
        logger.info("Requested to open Image Library Manager")

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
            DialogHelper.warning(tr("no_saved_query_loaded"), parent=self)
            return

        # Get new query text
        new_query_text = self.query_sql_editor.toPlainText().strip()
        if not new_query_text:
            DialogHelper.warning(tr("query_text_empty"), parent=self)
            return

        # Confirm update
        query_name = getattr(self._current_query_obj, 'name', 'Query')
        if not DialogHelper.confirm(
            tr("dialog_confirm_update", name=query_name),
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
                    tr("query_updated_success", name=query_name),
                    parent=self
                )
                logger.info(f"Updated saved query: {query_name}")
            else:
                DialogHelper.error(
                    tr("query_update_failed", name=query_name),
                    parent=self
                )

        except Exception as e:
            logger.error(f"Error updating saved query: {e}")
            DialogHelper.error(
                tr("query_error_update", error=str(e)),
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
            self.query_execute_btn.setText("⏳ " + tr("connecting_to", name=db_conn.name))
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
                        tr("failed_to_connect", name=db_conn.name),
                        parent=self
                    )
                    return
            except Exception as e:
                self.query_execute_btn.setText(f"▶ Execute on {db_conn.name} (F5)")
                self.query_execute_btn.setEnabled(True)
                DialogHelper.error(tr("connection_error"), parent=self, details=str(e))
                return

        if not self._current_query_connection:
            DialogHelper.error(tr("no_db_connection_available"), parent=self)
            return

        query_text = self.query_sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_execute"), parent=self)
            return

        # Show loading state
        self.query_execute_btn.setEnabled(False)
        self.query_execute_btn.setText("⏳ " + tr("executing"))
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
                msg.setWindowTitle(tr("connection_error"))
                msg.setText(tr("connection_lost"))
                msg.setInformativeText(tr("would_you_reconnect"))
                reconnect_btn = msg.addButton(tr("btn_reconnect"), QMessageBox.ButtonRole.AcceptRole)
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
                DialogHelper.info(tr("reconnected_success"), parent=self)
            else:
                DialogHelper.error(tr("reconnection_failed"), parent=self)
        except Exception as e:
            DialogHelper.error(tr("connection_error"), parent=self, details=str(e))

    # ==================== Image Management (delegated to ImageContentHandler) ====================

    def _add_new_image(self, default_category: str = ""):
        """Add a new image to the library (delegated to ImageContentHandler)."""
        if self._image_handler:
            self._image_handler.add_image(default_category)

    def _edit_image(self, image_obj):
        """Edit an image's metadata (delegated to ImageContentHandler)."""
        if self._image_handler:
            self._image_handler.edit_image(image_obj)

    def _delete_image(self, image_obj):
        """Delete an image from the library (delegated to ImageContentHandler)."""
        if self._image_handler:
            if self._image_handler.delete_image(image_obj):
                # Switch to generic page if the deleted image was being displayed
                self.content_stack.setCurrentIndex(self._page_indices["generic"])
