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
from PySide6.QtWidgets import QWidget, QTreeWidgetItem, QStackedWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db
from ...utils.image_loader import get_icon

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
    open_resource_requested = Signal(str, int)  # (resource_type, resource_id)

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

        # Page 1: DatabaseManager's right panel - QTabWidget with QueryTabs
        if self._database_manager:
            db_wrapper = QWidget()
            db_layout = QVBoxLayout(db_wrapper)
            db_layout.setContentsMargins(0, 0, 0, 0)

            # Create our own QTabWidget for query tabs
            self.query_tab_widget = QTabWidget()
            self.query_tab_widget.setTabsClosable(True)
            self.query_tab_widget.setMovable(True)
            self.query_tab_widget.tabCloseRequested.connect(self._close_query_tab)

            # Add welcome tab
            self._create_db_welcome_tab()

            db_layout.addWidget(self.query_tab_widget)

            self.content_stack.addWidget(db_wrapper)
            self._page_indices["database"] = self.content_stack.count() - 1
            self._query_tab_counter = 1

        # Page 2: RootFolderManager's right panel (file viewer)
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
            .add_field(tr("field_path"), "path")

        details_widget = self.details_form_builder.build()
        self.details_layout.addWidget(details_widget)

    def _setup_content(self):
        """Setup content panel (bottom right) with QStackedWidget for manager content."""
        # Create stacked widget to hold different manager views
        self.content_stack = QStackedWidget()
        self.content_layout.addWidget(self.content_stack)

        # Page 0: Generic placeholder (for categories, queries, jobs, scripts)
        generic_widget = QWidget()
        generic_layout = QVBoxLayout(generic_widget)
        generic_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        generic_label = QLabel("Sélectionnez un élément pour voir son contenu")
        generic_label.setStyleSheet("color: gray;")
        generic_layout.addWidget(generic_label)
        self.content_stack.addWidget(generic_widget)

        # Pages for managers will be added in set_managers()
        self._page_indices = {"generic": 0}

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

            # Queries
            queries = config_db.get_all_saved_queries()
            for query in queries:
                item = self.tree_view.add_item(
                    parent=self._category_items["queries"],
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
        for key, item in self._category_items.items():
            count = item.childCount()
            text = item.text(0).split(" (")[0]
            item.setText(0, f"{text} ({count})")

    def _set_item_icon(self, item, icon_name: str):
        icon = get_icon(icon_name)
        if icon:
            item.setIcon(0, icon)

    def _add_dummy_child(self, parent_item):
        """Add dummy child to show expand arrow."""
        dummy = QTreeWidgetItem(parent_item)
        dummy.setText(0, "...")
        dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})

    def _display_item(self, item_data: Any):
        """Display item details in appropriate panel based on type."""
        if not isinstance(item_data, dict):
            return

        item_type = item_data.get("type", "")
        obj = item_data.get("obj")

        # Switch to appropriate page based on item type
        if item_type in ("database", "server", "table", "view", "column", "tables_folder", "views_folder"):
            # Show database panel - hide details panel (QueryTab is enough)
            if "database" in self._page_indices:
                self.content_stack.setCurrentIndex(self._page_indices["database"])
            self.details_panel.hide()
            return

        elif item_type in ("rootfolder", "folder", "file"):
            # Show rootfolder panel with details
            if "rootfolder" in self._page_indices:
                self.content_stack.setCurrentIndex(self._page_indices["rootfolder"])
            self.details_panel.show()
            self._display_file_item(item_data)
            return

        # Default: show generic details
        self.details_panel.show()
        self.content_stack.setCurrentIndex(self._page_indices["generic"])

        if item_type == "category":
            self.details_form_builder.set_value("name", item_data.get("category_key", "").capitalize())
            self.details_form_builder.set_value("resource_type", "Category")
            self.details_form_builder.set_value("description", "")
            self.details_form_builder.set_value("path", "")
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
                    else:
                        size_str = "-"
                        file_type = "Folder"

                    # Format modified date
                    from datetime import datetime
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                    self.details_form_builder.set_value("name", file_path.name)
                    self.details_form_builder.set_value("resource_type", f"{file_type} ({size_str})")
                    self.details_form_builder.set_value("description", f"Modified: {modified}")
                    self.details_form_builder.set_value("path", str(file_path))
                except Exception as e:
                    logger.error(f"Error getting file info: {e}")

    def _on_tree_double_click(self, item, column):
        """Double-click: expand, execute query, or open file."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        if item_type in ("category", "database", "server", "rootfolder", "folder", "tables_folder", "views_folder"):
            # Toggle expand for expandable items
            item.setExpanded(not item.isExpanded())

        elif item_type in ("table", "view"):
            # Generate and execute SELECT TOP 100 query in our query tab
            self._execute_query_for_table(data, limit=100)

        elif item_type == "file":
            # Load and display file content in our viewer
            path = data.get("path")
            if path:
                self._load_file_content(Path(path))

        else:
            # For other items (query, job, script), emit signal to open in dedicated manager
            item_id = data.get("id")
            if item_id:
                self.open_resource_requested.emit(item_type, item_id)

    # ==================== Lazy Loading (delegates to managers) ====================

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle expand - delegate to appropriate manager."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        # Check for dummy child
        if item.childCount() == 1:
            first_child = item.child(0)
            child_data = first_child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("type") == "dummy":
                item.removeChild(first_child)

                item_type = data.get("type", "")
                if item_type == "database" and self._database_manager:
                    self._load_database_children(item, data)
                elif item_type == "rootfolder" and self._rootfolder_manager:
                    self._load_rootfolder_children(item, data)
                elif item_type == "folder" and self._rootfolder_manager:
                    self._load_folder_children(item, data)

    def _load_database_children(self, parent_item: QTreeWidgetItem, data: dict):
        """Load database schema using DatabaseManager's methods."""
        if not self._database_manager:
            return

        db_obj = data.get("obj")
        if not db_obj:
            return

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
        except Exception as e:
            logger.error(f"Error loading database schema: {e}")
            error_item = QTreeWidgetItem(parent_item)
            error_item.setText(0, f"Erreur: {str(e)[:50]}")
            error_item.setForeground(0, Qt.GlobalColor.red)

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
            tab_name=tab_name
        )

        # Add to tab widget
        index = self.query_tab_widget.addTab(query_tab, tab_name)
        self.query_tab_widget.setCurrentIndex(index)

        logger.info(f"Created new query tab: {tab_name} for {db_conn.name}")

        return query_tab

    def _execute_query_for_table(self, data: dict, limit: int = 100):
        """Execute a SELECT query for a table/view in our query tab."""
        table_name = data.get("name", "")
        db_id = data.get("db_id")
        db_name = data.get("db_name")

        if not db_id or not table_name:
            return

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

    def _load_csv_file(self, file_path: Path):
        """Load CSV file into grid viewer."""
        import csv

        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # Try to detect delimiter
            sample = f.read(4096)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample)
                reader = csv.reader(f, dialect)
            except csv.Error:
                reader = csv.reader(f)

            rows = list(reader)

        if rows:
            headers = rows[0]
            data = rows[1:]

            self.file_grid_viewer.set_columns(headers)
            self.file_grid_viewer.set_data(data)
            self.file_viewer_stack.setCurrentIndex(0)  # Grid viewer
        else:
            self.file_text_viewer.setPlainText("(Fichier CSV vide)")
            self.file_viewer_stack.setCurrentIndex(1)

    def _load_excel_file(self, file_path: Path):
        """Load Excel file into grid viewer."""
        try:
            import openpyxl
        except ImportError:
            self.file_text_viewer.setPlainText("Module openpyxl non installé.\nInstallez-le avec: pip install openpyxl")
            self.file_viewer_stack.setCurrentIndex(1)
            return

        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet = wb.active

        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append([str(cell) if cell is not None else "" for cell in row])

        wb.close()

        if rows:
            headers = rows[0]
            data = rows[1:]

            self.file_grid_viewer.set_columns(headers)
            self.file_grid_viewer.set_data(data)
            self.file_viewer_stack.setCurrentIndex(0)
        else:
            self.file_text_viewer.setPlainText("(Fichier Excel vide)")
            self.file_viewer_stack.setCurrentIndex(1)

    def _load_json_file(self, file_path: Path):
        """Load JSON file into text viewer with formatting."""
        import json

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            data = json.loads(content)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.file_text_viewer.setPlainText(formatted)
        except json.JSONDecodeError:
            self.file_text_viewer.setPlainText(content)

        self.file_viewer_stack.setCurrentIndex(1)  # Text viewer

    def _load_text_file(self, file_path: Path):
        """Load text file into text viewer."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()

        self.file_text_viewer.setPlainText(content)
        self.file_viewer_stack.setCurrentIndex(1)  # Text viewer
