"""
Data Explorer Module - Navigate and view files in RootFolders organized by Projects
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import csv
import json
import pandas as pd
import sqlite3
import pyodbc
import re
from ..database.config_db import FileRoot, DatabaseConnection, Project, config_db
from ..database.connections_config import connections_manager
from ..utils.logger import logger
from ..utils.icon_loader import icon_loader
from .custom_treeview import CustomTreeView
from .custom_datagridview import CustomDataGridView
from .base_view_frame import BaseViewFrame


class DataExplorer(BaseViewFrame):
    """Data Explorer - Navigate RootFolders and view files"""

    def __init__(self, parent, gui_parent=None):
        # Define toolbar buttons
        toolbar_buttons = [
            ("🔄 Refresh", self._refresh),
            ("➕ New Project", self._create_new_project),
        ]

        # Initialize base with standard layout
        super().__init__(
            parent,
            toolbar_buttons=toolbar_buttons,
            show_left_panel=True,
            left_weight=1,
            right_weight=2,
            top_weight=0,
            bottom_weight=1
        )

        self.gui_parent = gui_parent
        # Preload icons
        icon_loader.preload_all()
        # Store database connections for auto-connect
        self.db_connections = {}
        # Track selected item and database
        self._selected_item = None
        self._selected_db_id = None

        # Log filter variables (must be initialized before _create_widgets)
        self._log_content = ""  # Store full log content
        self.log_filter_info = tk.BooleanVar(value=True)
        self.log_filter_warning = tk.BooleanVar(value=True)
        self.log_filter_important = tk.BooleanVar(value=True)
        self.log_filter_error = tk.BooleanVar(value=True)

        self._create_widgets()
        self._load_projects()

    def get_selected_database_id(self):
        """
        Get the database ID of the currently selected item in the tree

        Returns:
            str: Database ID if a database/table is selected, None otherwise
        """
        return self._selected_db_id if hasattr(self, '_selected_db_id') else None

    def _create_widgets(self):
        """Create explorer widgets"""
        # BaseViewFrame already created main_paned, left_frame, right_paned with top_frame and bottom_frame

        # Create CustomTreeView in left panel (without toolbar - now at top level)
        self.custom_tree = CustomTreeView(self.left_frame)
        self.custom_tree.pack(fill=tk.BOTH, expand=True)

        # Set event callbacks
        self.custom_tree.set_on_double_click(self._on_tree_double_click)
        self.custom_tree.set_on_select(self._on_tree_select)
        self.custom_tree.set_on_expand(self._on_tree_expand)
        self.custom_tree.set_on_right_click(self._show_context_menu)

        # Keep reference to the internal tree for compatibility
        self.file_tree = self.custom_tree.tree

        # ===== TOP PANEL: Column Statistics =====
        # Use self.top_frame from BaseViewFrame
        self.middle_frame = self.top_frame  # Alias for compatibility

        ttk.Label(self.middle_frame, text="Column Statistics", font=("Arial", 10, "bold")).pack(pady=5)

        # Statistics grid (CustomDataGridView without toolbar)
        self.stats_grid = CustomDataGridView(
            self.middle_frame,
            show_export=False,
            show_copy=False,
            show_raw_toggle=False
        )
        self.stats_grid.pack(fill=tk.BOTH, expand=True)

        # ===== BOTTOM PANEL: File viewer =====
        # Use self.bottom_frame from BaseViewFrame
        self.right_frame = self.bottom_frame  # Alias for compatibility

        # File info
        self.info_frame = ttk.Frame(self.right_frame, padding="5")
        self.info_frame.pack(fill=tk.X)

        self.file_info_label = ttk.Label(self.info_frame, text="No file selected", font=("Arial", 9))
        self.file_info_label.pack(anchor=tk.W)

        # Current path label (moved from toolbar to right panel)
        self.path_label = ttk.Label(self.info_frame, text="", foreground="blue", font=("Arial", 8))
        self.path_label.pack(anchor=tk.W, pady=(2, 0))

        # File content viewer frame
        self.viewer_frame = ttk.LabelFrame(self.right_frame, text="File Content", padding="5")
        self.viewer_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ===== RAW TEXT VIEWER (for text files) =====
        self.raw_viewer_container = ttk.Frame(self.viewer_frame)

        # Viewer toolbar (for raw text mode)
        viewer_toolbar = ttk.Frame(self.raw_viewer_container)
        viewer_toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(viewer_toolbar, text="Encoding:").pack(side=tk.LEFT, padx=(0, 5))

        self.encoding_var = tk.StringVar(value="utf-8")
        encoding_combo = ttk.Combobox(
            viewer_toolbar,
            textvariable=self.encoding_var,
            values=["utf-8", "latin-1", "cp1252", "iso-8859-1"],
            state='readonly',
            width=15
        )
        encoding_combo.pack(side=tk.LEFT, padx=2)
        encoding_combo.bind("<<ComboboxSelected>>", lambda e: self._reload_file())

        ttk.Button(viewer_toolbar, text="Reload", command=self._reload_file).pack(side=tk.LEFT, padx=5)

        # Toggle button for CSV files (shown only for CSV)
        self.toggle_table_btn = ttk.Button(viewer_toolbar, text="📊 Table View", command=self._toggle_csv_view, width=12)
        # Hidden by default, shown only for CSV files

        # Log filters frame (shown only for .log files)
        self.log_filters_frame = ttk.Frame(viewer_toolbar)
        ttk.Label(self.log_filters_frame, text="  |  Show:").pack(side=tk.LEFT, padx=(10, 5))

        ttk.Checkbutton(
            self.log_filters_frame,
            text="ERROR",
            variable=self.log_filter_error,
            command=self._apply_log_filter
        ).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(
            self.log_filters_frame,
            text="WARNING",
            variable=self.log_filter_warning,
            command=self._apply_log_filter
        ).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(
            self.log_filters_frame,
            text="IMPORTANT",
            variable=self.log_filter_important,
            command=self._apply_log_filter
        ).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(
            self.log_filters_frame,
            text="INFO",
            variable=self.log_filter_info,
            command=self._apply_log_filter
        ).pack(side=tk.LEFT, padx=2)
        # Hidden by default, shown only for .log files

        # Scrollable text widget with horizontal and vertical scrollbars
        text_container = ttk.Frame(self.raw_viewer_container)
        text_container.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(text_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Text widget
        self.content_text = tk.Text(
            text_container,
            wrap=tk.NONE,
            font=("Consolas", 9),
            width=80,
            height=25,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure scrollbars
        v_scrollbar.config(command=self.content_text.yview)
        h_scrollbar.config(command=self.content_text.xview)

        # ===== DATA GRID VIEWER (for tabular data) =====
        # CustomDataGridView without raw/table toggle (we use external button)
        self.data_grid = CustomDataGridView(
            self.viewer_frame,
            show_export=True,
            show_copy=True,
            show_raw_toggle=False,  # Toggle is in raw viewer toolbar
            on_raw_toggle=None
        )

        # Use default fullscreen implementation (data-only view without buttons)

        # Start with raw viewer visible
        self.raw_viewer_container.pack(fill=tk.BOTH, expand=True)
        # Data grid hidden by default
        # self.data_grid.pack(fill=tk.BOTH, expand=True)

        # Storage
        self._current_path = None
        self._current_root = None
        self._csv_view_mode = "raw"  # "raw" or "table"
        self._path_items = {}  # Map tree items to Path objects
        self._db_items = {}  # Map tree items to DatabaseConnection objects
        self._item_types = {}  # Map tree items to their type (project, section, folder, db, etc.)

    def _load_projects(self):
        """Load projects with their root folders and databases"""
        # Clear tree
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        self._path_items = {}
        self._db_items = {}
        self._item_types = {}

        # Load projects sorted by last usage (most recent first)
        projects_to_display = config_db.get_all_projects(sort_by_usage=True)

        # Add individual projects FIRST
        for idx, project in enumerate(projects_to_display):
            # First project (most recently used) is the active project
            is_active = (idx == 0 and project.last_used_at is not None)
            icon = "⭐" if is_active else "📁"
            text = f"{icon} {project.name}"

            project_node = self.file_tree.insert(
                "",
                "end",
                text=text,
                tags=("project",),
                open=is_active  # Open active project by default
            )
            self._item_types[project_node] = ("project", project.id)

            # Add sections for this project
            self._add_project_resources(project_node, project.id)

            # Add thin separator after each project
            separator = self.file_tree.insert("", "end", text="─" * 50, tags=("separator",))
            self._item_types[separator] = "separator"

        # Create "All Resources" node at the END
        all_projects_node = self.file_tree.insert(
            "",
            "end",
            text="📁 Toutes les ressources",
            tags=("project", "all"),
            open=False
        )
        self._item_types[all_projects_node] = "all_projects"
        self._add_all_resources(all_projects_node)

        # Configure tags with theme colors
        self._apply_tree_tags()

        # Bind expand event
        self.file_tree.bind("<<TreeviewOpen>>", self._on_tree_expand)

        # Bind right-click for context menu
        self.file_tree.bind("<Button-3>", self._show_context_menu)

        logger.info(f"Loaded {len(projects_to_display)} projects")

    def _add_all_resources(self, parent_node):
        """Add all RootFolders, Databases and Saved Queries under 'All Resources'"""
        # Load section icons
        rootfolders_icon = icon_loader.load_rootfolders_section_icon()
        databases_icon = icon_loader.load_databases_section_icon()

        # Add RootFolders section with icon
        folders_section = self.file_tree.insert(
            parent_node,
            "end",
            text="RootFolders",
            image=rootfolders_icon if rootfolders_icon else "",
            tags=("section",)
        )
        self._item_types[folders_section] = "folders_section"

        # Add all root folders
        root_folders = config_db.get_all_file_roots()
        for root_folder in root_folders:
            self._add_root_folder_node(folders_section, root_folder)

        # Add Databases section with icon
        db_section = self.file_tree.insert(
            parent_node,
            "end",
            text="Databases",
            image=databases_icon if databases_icon else "",
            tags=("section",)
        )
        self._item_types[db_section] = "databases_section"

        # Add all databases
        databases = config_db.get_all_database_connections()
        for db in databases:
            self._add_database_node(db_section, db)

        # Add Saved Queries section
        queries_section = self.file_tree.insert(
            parent_node,
            "end",
            text="📋 Saved Queries",
            tags=("section",)
        )
        self._item_types[queries_section] = "queries_section"

        # Add all saved queries organized by category
        all_queries = config_db.get_all_saved_queries()
        # Group by category
        categories = {}
        for query in all_queries:
            if query.category not in categories:
                categories[query.category] = []
            categories[query.category].append(query)

        # Add categories and queries
        for category_name in sorted(categories.keys()):
            category_node = self.file_tree.insert(
                queries_section,
                "end",
                text=f"📂 {category_name}",
                tags=("category",)
            )
            self._item_types[category_node] = ("query_category", category_name)

            for query in sorted(categories[category_name], key=lambda q: q.name):
                # Get database name
                db_conn = connections_manager.get_connection(query.target_database_id)
                db_name = db_conn.name if db_conn else "Unknown"

                query_item = self.file_tree.insert(
                    category_node,
                    "end",
                    text=f"🔍 {query.name} [{db_name}]",
                    tags=("query",)
                )
                self._item_types[query_item] = ("saved_query", query.id, None)

    def _add_project_resources(self, parent_node, project_id):
        """Add RootFolders, Databases and Saved Queries directly under project (no sections)"""
        # Add project's root folders directly (with subfolder paths)
        root_folders_with_paths = config_db.get_project_file_roots_with_paths(project_id)
        for root_folder, subfolder_path in root_folders_with_paths:
            self._add_root_folder_node(parent_node, root_folder, project_id, subfolder_path)

        # Add project's databases directly
        databases = config_db.get_project_databases(project_id)
        for db in databases:
            self._add_database_node(parent_node, db, project_id)

        # Add project's saved queries under a "Queries" section
        queries = config_db.get_project_saved_queries(project_id)
        if queries:
            # Create "Queries" section
            queries_section = self.file_tree.insert(
                parent_node,
                "end",
                text="📋 Queries",
                tags=("section",)
            )
            self._item_types[queries_section] = ("queries_section", project_id)

            # Group by category
            categories = {}
            for query in queries:
                if query.category not in categories:
                    categories[query.category] = []
                categories[query.category].append(query)

            # Add categories under Queries section
            for category_name in sorted(categories.keys()):
                category_node = self.file_tree.insert(
                    queries_section,
                    "end",
                    text=f"📂 {category_name}",
                    tags=("category",)
                )
                self._item_types[category_node] = ("query_category", category_name, project_id)

                for query in sorted(categories[category_name], key=lambda q: q.name):
                    # Get database name
                    db_conn = connections_manager.get_connection(query.target_database_id)
                    db_name = db_conn.name if db_conn else "Unknown"

                    query_item = self.file_tree.insert(
                        category_node,
                        "end",
                        text=f"🔍 {query.name} [{db_name}]",
                        tags=("query",)
                    )
                    self._item_types[query_item] = ("saved_query", query.id, project_id)

    def _add_root_folder_node(self, parent_node, root_folder: FileRoot, project_id=None, subfolder_path: str = None):
        """
        Add a root folder node

        Args:
            parent_node: Parent tree node
            root_folder: FileRoot object (application RootFolder)
            project_id: Optional project ID if this is attached to a project
            subfolder_path: Optional relative path to a subfolder within the RootFolder
        """
        root_path = Path(root_folder.path)

        # If subfolder_path is provided, use that as the actual path
        if subfolder_path:
            actual_path = root_path / subfolder_path
        else:
            actual_path = root_path

        if not actual_path.exists():
            item = self.file_tree.insert(
                parent_node,
                "end",
                text=f"{actual_path} [NOT FOUND]",
                tags=("error",)
            )
            self._item_types[item] = "error"
            return

        # Load folder icon
        folder_icon = icon_loader.load_folder_icon()

        # Count files recursively in this folder
        file_count = self._count_files_recursive(actual_path)

        # Add folder with icon and file count
        if subfolder_path:
            # Show subfolder name with parent info
            text = f"{actual_path.name} ({file_count}) [subfolder of {root_path.name}]"
        else:
            # Show root folder name
            text = f"{root_path.name} ({file_count})"
            if root_folder.description:
                text += f" - {root_folder.description}"

        item = self.file_tree.insert(
            parent_node,
            "end",
            text=text,
            image=folder_icon if folder_icon else "",
            tags=("root",)
        )
        self._path_items[item] = actual_path
        self._item_types[item] = ("root_folder", root_folder.id, project_id, subfolder_path)

        # Add dummy child to make it expandable
        self.file_tree.insert(item, "end", text="Loading...")

    def _add_database_node(self, parent_node, database: DatabaseConnection, project_id=None):
        """Add a database node"""
        # Load database-specific icon
        db_icon = icon_loader.load_database_icon(database.db_type)

        # Format text
        text = f"{database.name} ({database.db_type})"

        item = self.file_tree.insert(
            parent_node,
            "end",
            text=text,
            image=db_icon if db_icon else "",
            tags=("database",)
        )
        self._db_items[item] = database
        self._item_types[item] = ("database", database.id, project_id)

        # Add dummy child to make database expandable
        self.file_tree.insert(item, "end", text="dummy")

    def _on_tree_expand(self, event):
        """Handle tree expand event"""
        item = self.file_tree.focus()
        if not item:
            return

        # Check if it's a database node
        database = self._db_items.get(item)
        if database:
            self._load_database_tables(item, database)
            return

        # Get path (for folder nodes)
        path = self._path_items.get(item)
        if not path or not path.is_dir():
            return

        # Remove dummy child
        children = self.file_tree.get_children(item)
        for child in children:
            if self.file_tree.item(child, "text") in ["Loading...", "dummy"]:
                self.file_tree.delete(child)

        # Load directory contents
        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

            for item_path in items:
                if item_path.name.startswith('.'):
                    continue  # Skip hidden files

                if item_path.is_dir():
                    # Count files recursively in this folder
                    file_count = self._count_files_recursive(item_path)

                    # Add folder with file count
                    child_item = self.file_tree.insert(
                        item,
                        "end",
                        text=f"📁 {item_path.name} ({file_count})",
                        tags=("folder",)
                    )
                    self._path_items[child_item] = item_path

                    # Add dummy child if folder has contents
                    try:
                        if any(item_path.iterdir()):
                            self.file_tree.insert(child_item, "end", text="Loading...")
                    except PermissionError:
                        pass

                else:
                    # Add file
                    size = item_path.stat().st_size
                    size_str = self._format_size(size)
                    child_item = self.file_tree.insert(
                        item,
                        "end",
                        text=f"📄 {item_path.name} ({size_str})",
                        tags=("file",)
                    )
                    self._path_items[child_item] = item_path

        except PermissionError:
            self.file_tree.insert(item, "end", text="[Permission Denied]", tags=("error",))
        except Exception as e:
            logger.error(f"Error loading directory {path}: {e}")
            self.file_tree.insert(item, "end", text=f"[Error: {e}]", tags=("error",))

    def _load_database_tables(self, item, database: DatabaseConnection):
        """Load tables for a database node"""
        # Remove dummy child
        children = self.file_tree.get_children(item)
        for child in children:
            if self.file_tree.item(child, "text") == "dummy":
                self.file_tree.delete(child)

        # Auto-connect if not already connected
        if database.id not in self.db_connections:
            try:
                if database.db_type.lower() == 'sqlite':
                    # Extract SQLite path from connection string
                    match = re.search(r'Database=([^;]+)', database.connection_string, re.IGNORECASE)
                    if match:
                        db_path = match.group(1).strip()
                    else:
                        # Fallback: assume the whole connection string is the path
                        db_path = database.connection_string.strip()

                    conn = sqlite3.connect(db_path)
                else:
                    # Use pyodbc for other database types
                    conn = pyodbc.connect(database.connection_string)

                self.db_connections[database.id] = conn
                logger.info(f"Auto-connected to database: {database.name}")
            except Exception as e:
                logger.error(f"Failed to auto-connect to {database.name}: {e}")
                self.file_tree.insert(item, "end", text=f"[Connection failed: {str(e)}]", tags=("error",))
                return

        # Now load tables using self.db_connections
        try:
            conn = self.db_connections[database.id]
            cursor = conn.cursor()

            # Get tables based on database type
            if database.db_type.lower() in ['postgresql', 'postgres']:
                cursor.execute("""
                    SELECT tablename FROM pg_catalog.pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY tablename
                """)
            elif database.db_type.lower() == 'mysql':
                cursor.execute("SHOW TABLES")
            elif database.db_type.lower() in ['sqlserver', 'mssql', 'sql server']:
                cursor.execute("SELECT name FROM sys.tables ORDER BY name")
            elif database.db_type.lower() == 'sqlite':
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            else:
                # Generic fallback
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog') ORDER BY table_name")

            tables = cursor.fetchall()

            if not tables:
                self.file_tree.insert(item, "end", text="[No tables found]", tags=("info",))
            else:
                for table in tables:
                    table_name = table[0]
                    table_item = self.file_tree.insert(
                        item,
                        "end",
                        text=f"📋 {table_name}",
                        tags=("table",)
                    )
                    # Store table info for context menu
                    self._item_types[table_item] = ("table", database.id, table_name)

        except Exception as e:
            logger.error(f"Error loading tables for {database.name}: {e}")
            self.file_tree.insert(item, "end", text=f"[Error: {str(e)}]", tags=("error",))

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _count_files_recursive(self, folder_path: Path) -> int:
        """
        Count all files in a folder and its subdirectories recursively

        Args:
            folder_path: Path to the folder

        Returns:
            Total number of files (not including directories)
        """
        file_count = 0
        try:
            for item in folder_path.iterdir():
                if item.name.startswith('.'):
                    continue  # Skip hidden files

                if item.is_dir():
                    # Recursively count files in subdirectory
                    file_count += self._count_files_recursive(item)
                else:
                    # It's a file, count it
                    file_count += 1
        except PermissionError:
            # Can't access this folder, skip it
            pass
        except Exception as e:
            # Log error but continue
            logger.debug(f"Error counting files in {folder_path}: {e}")

        return file_count

    def _on_tree_double_click(self, event):
        """Handle double-click on tree item"""
        item = self.file_tree.focus()
        if not item:
            return

        path = self._path_items.get(item)
        if not path:
            return

        if path.is_file():
            self._view_file(path)

    def _on_tree_select(self, event):
        """Handle tree selection"""
        item = self.file_tree.focus()
        if not item:
            return

        # Store currently selected item and its database ID
        self._selected_item = item

        # Check if this item is a database or table node
        item_type_info = self._item_types.get(item)
        if item_type_info and len(item_type_info) >= 2:
            # item_type_info format: ("database", db_id, project_id) or ("table", db_id, table_name)
            # Database ID is always at index 1
            self._selected_db_id = item_type_info[1]
        else:
            self._selected_db_id = None

        path = self._path_items.get(item)
        if not path:
            return

        self._current_path = path

        # Update path label
        self.path_label.config(text=str(path))

        # Update file info
        if path.is_file():
            stat = path.stat()
            size_str = self._format_size(stat.st_size)
            self.file_info_label.config(
                text=f"File: {path.name} | Size: {size_str} | Type: {path.suffix}"
            )
        else:
            try:
                count = len(list(path.iterdir()))
                self.file_info_label.config(
                    text=f"Folder: {path.name} | Items: {count}"
                )
            except:
                self.file_info_label.config(text=f"Folder: {path.name}")

    def _view_file(self, file_path: Path):
        """View file contents"""
        self.content_text.delete(1.0, tk.END)

        try:
            # Check file size
            size = file_path.stat().st_size
            if size > 5 * 1024 * 1024:  # 5 MB
                response = messagebox.askyesno(
                    "Large File",
                    f"File is {self._format_size(size)}. This may take a while.\n\nContinue?",
                    icon='warning'
                )
                if not response:
                    return

            # Detect file type and display
            suffix = file_path.suffix.lower()

            # Show/hide toggle button based on file type
            if suffix in ['.csv', '.tsv']:
                self.toggle_table_btn.pack(side=tk.LEFT, padx=5)
            else:
                self.toggle_table_btn.pack_forget()
                self._csv_view_mode = "raw"

            # Show/hide log filters based on file type
            if suffix == '.log':
                self.log_filters_frame.pack(side=tk.LEFT, padx=5)
            else:
                self.log_filters_frame.pack_forget()
                self._log_content = ""  # Clear log content

            if suffix in ['.txt', '.log', '.md', '.py', '.js', '.java', '.cpp', '.h', '.sql']:
                # Text file
                self._view_text_file(file_path)

            elif suffix in ['.csv', '.tsv']:
                # CSV file
                self._view_csv_file(file_path)

            elif suffix == '.json':
                # JSON file
                self._view_json_file(file_path)

            else:
                # Binary or unknown file
                self.content_text.insert(1.0, f"[Binary file: {file_path.name}]\n\n")
                self.content_text.insert(tk.END, "Cannot display binary file content.\n")
                self.content_text.insert(tk.END, f"File size: {self._format_size(size)}\n")
                self.content_text.insert(tk.END, f"File type: {suffix}")

            logger.info(f"Viewing file: {file_path}")

        except Exception as e:
            logger.error(f"Error viewing file {file_path}: {e}")
            messagebox.showerror("Error", f"Error viewing file:\n{e}")

    def _view_text_file(self, file_path: Path):
        """View text file"""
        encoding = self.encoding_var.get()
        is_log_file = file_path.suffix.lower() == '.log'

        # Try multiple encodings if the selected one fails
        encodings_to_try = [encoding]
        if encoding == 'utf-8':
            encodings_to_try.extend(['latin-1', 'cp1252', 'iso-8859-1'])

        last_error = None
        for enc in encodings_to_try:
            try:
                content = file_path.read_text(encoding=enc)

                # Store full content for log files (for filtering)
                if is_log_file:
                    self._log_content = content

                # Limit display to first 10,000 lines
                lines = content.splitlines()
                if len(lines) > 10000:
                    self.content_text.insert(1.0, f"[Showing first 10,000 of {len(lines)} lines]\n\n")
                    content = "\n".join(lines[:10000])

                # Success! Update encoding if we used a fallback
                if enc != encoding:
                    self.content_text.insert(1.0, f"[Auto-detected encoding: {enc}]\n\n")
                    self.encoding_var.set(enc)
                    logger.info(f"Auto-detected encoding {enc} for {file_path}")

                # Apply log filter if it's a log file
                if is_log_file:
                    self._apply_log_filter()
                else:
                    self.content_text.insert(tk.END, content)

                return  # Success - exit function

            except UnicodeDecodeError as e:
                last_error = e
                continue  # Try next encoding

        # If we get here, all encodings failed
        if last_error:
            self.content_text.insert(1.0, f"[ENCODING ERROR]\n\n")
            self.content_text.insert(tk.END, f"Cannot decode file with any common encoding.\n\n")
            self.content_text.insert(tk.END, f"Tried: {', '.join(encodings_to_try)}\n\n")
            self.content_text.insert(tk.END, f"Last error: {last_error}\n\n")
            self.content_text.insert(tk.END, "Try selecting a different encoding from the dropdown above and click 'Reload'.")
            logger.error(f"Failed to decode text file {file_path} with any encoding: {encodings_to_try}")

    def _view_csv_file(self, file_path: Path):
        """View CSV file in raw or table format based on mode"""
        if self._csv_view_mode == "table":
            self._view_csv_table(file_path)
        else:
            self._view_csv_raw(file_path)

    def _view_csv_raw(self, file_path: Path):
        """View CSV file in raw text format"""
        encoding = self.encoding_var.get()

        # Try multiple encodings if the selected one fails
        encodings_to_try = [encoding]
        if encoding == 'utf-8':
            encodings_to_try.extend(['latin-1', 'cp1252', 'iso-8859-1'])

        last_error = None
        for enc in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=enc, newline='') as f:
                    # Detect delimiter
                    sample = f.read(1024)
                    f.seek(0)
                    sniffer = csv.Sniffer()
                    try:
                        delimiter = sniffer.sniff(sample).delimiter
                    except:
                        delimiter = ','

                    reader = csv.reader(f, delimiter=delimiter)

                    # Read and display
                    lines = []
                    for i, row in enumerate(reader):
                        if i > 1000:  # Limit to 1000 rows
                            lines.append(f"\n[Showing first 1000 rows only]")
                            break
                        lines.append(delimiter.join(row))

                    # Success! Update encoding if we used a fallback
                    if enc != encoding:
                        self.content_text.insert(1.0, f"[Auto-detected encoding: {enc}]\n\n")
                        self.encoding_var.set(enc)
                        logger.info(f"Auto-detected encoding {enc} for {file_path}")

                    self.content_text.insert(tk.END, "\n".join(lines))
                    return  # Success - exit function

            except UnicodeDecodeError as e:
                last_error = e
                continue  # Try next encoding

            except Exception as e:
                self.content_text.insert(1.0, f"Error reading CSV: {e}")
                return

        # If we get here, all encodings failed
        if last_error:
            self.content_text.insert(1.0, f"[ENCODING ERROR]\n\n")
            self.content_text.insert(tk.END, f"Cannot decode CSV file with any common encoding.\n\n")
            self.content_text.insert(tk.END, f"Tried: {', '.join(encodings_to_try)}\n\n")
            self.content_text.insert(tk.END, f"Last error: {last_error}\n\n")
            self.content_text.insert(tk.END, "Try selecting a different encoding from the dropdown above and click 'Reload'.")
            logger.error(f"Failed to decode CSV {file_path} with any encoding: {encodings_to_try}")

    def _view_csv_table(self, file_path: Path):
        """View CSV file in formatted table layout using CustomDataGridView"""
        encoding = self.encoding_var.get()

        # Try multiple encodings if the selected one fails
        encodings_to_try = [encoding]
        if encoding == 'utf-8':
            encodings_to_try.extend(['latin-1', 'cp1252', 'iso-8859-1'])

        last_error = None
        for enc in encodings_to_try:
            try:
                # Detect delimiter
                with open(file_path, 'r', encoding=enc) as f:
                    sample = f.read(1024)
                    sniffer = csv.Sniffer()
                    try:
                        delimiter = sniffer.sniff(sample).delimiter
                    except:
                        delimiter = ','

                # Read CSV with pandas
                df = pd.read_csv(file_path, encoding=enc, delimiter=delimiter)

                # Success! Update encoding if we used a fallback
                if enc != encoding:
                    self.encoding_var.set(enc)
                    logger.info(f"Auto-detected encoding {enc} for {file_path}")

                # Load data into CustomDataGridView
                self.data_grid.load_from_dataframe(df)

                # Calculate and display column statistics in the middle panel
                stats_data = CustomDataGridView.calculate_column_statistics(
                    self.data_grid.data,
                    self.data_grid.columns
                )
                self.stats_grid.load_data(stats_data, columns=['Column', 'Total', 'Non-Null', 'Empty', 'Distinct'])

                logger.info(f"Loaded CSV into data grid: {len(df)} rows × {len(df.columns)} columns")
                return  # Success - exit function

            except UnicodeDecodeError as e:
                last_error = e
                continue  # Try next encoding

            except Exception as e:
                logger.error(f"Error reading CSV table {file_path}: {e}")
                messagebox.showerror("Error", f"Failed to load CSV: {e}")
                return

        # If we get here, all encodings failed
        if last_error:
            error_msg = f"Cannot decode CSV file with any common encoding.\nTried: {', '.join(encodings_to_try)}"
            logger.error(f"Failed to decode CSV {file_path} with any encoding: {encodings_to_try}")
            messagebox.showerror("Encoding Error", error_msg)

    def _toggle_csv_view(self):
        """Toggle between raw and table view for CSV files"""
        if not self._current_path or self._current_path.suffix.lower() not in ['.csv', '.tsv']:
            return

        # Toggle mode
        if self._csv_view_mode == "raw":
            self._csv_view_mode = "table"
            logger.info("Switched to CSV table view")
            # Update button text
            self.toggle_table_btn.config(text="📄 Raw View")
            # Hide raw viewer, show data grid
            self.raw_viewer_container.pack_forget()
            self.data_grid.pack(fill=tk.BOTH, expand=True)
            # Load CSV data into grid
            self._view_csv_table(self._current_path)
        else:
            self._csv_view_mode = "raw"
            logger.info("Switched to CSV raw view")
            # Update button text
            self.toggle_table_btn.config(text="📊 Table View")
            # Hide data grid, show raw viewer
            self.data_grid.pack_forget()
            self.raw_viewer_container.pack(fill=tk.BOTH, expand=True)
            # Clear statistics
            self.stats_grid.clear()
            # Reload file in raw mode
            self.content_text.delete(1.0, tk.END)
            self._view_csv_raw(self._current_path)


    def _view_json_file(self, file_path: Path):
        """View JSON file with formatting"""
        encoding = self.encoding_var.get()

        # Try multiple encodings if the selected one fails
        encodings_to_try = [encoding]
        if encoding == 'utf-8':
            encodings_to_try.extend(['latin-1', 'cp1252', 'iso-8859-1'])

        last_error = None
        for enc in encodings_to_try:
            try:
                content = file_path.read_text(encoding=enc)
                data = json.loads(content)

                # Pretty print
                formatted = json.dumps(data, indent=2, ensure_ascii=False)

                # Success! Update encoding if we used a fallback
                if enc != encoding:
                    self.content_text.insert(1.0, f"[Auto-detected encoding: {enc}]\n\n")
                    self.encoding_var.set(enc)
                    logger.info(f"Auto-detected encoding {enc} for {file_path}")

                self.content_text.insert(tk.END, formatted)
                return  # Success - exit function

            except UnicodeDecodeError as e:
                last_error = e
                continue  # Try next encoding

            except json.JSONDecodeError as e:
                # JSON decode error - display the content as-is
                self.content_text.insert(1.0, f"[Invalid JSON]\n\n{content}")
                return

        # If we get here, all encodings failed
        if last_error:
            self.content_text.insert(1.0, f"[ENCODING ERROR]\n\n")
            self.content_text.insert(tk.END, f"Cannot decode JSON file with any common encoding.\n\n")
            self.content_text.insert(tk.END, f"Tried: {', '.join(encodings_to_try)}\n\n")
            self.content_text.insert(tk.END, f"Last error: {last_error}\n\n")
            self.content_text.insert(tk.END, "Try selecting a different encoding from the dropdown above and click 'Reload'.")
            logger.error(f"Failed to decode JSON {file_path} with any encoding: {encodings_to_try}")

    def _reload_file(self):
        """Reload current file with new encoding"""
        if self._current_path and self._current_path.is_file():
            self._view_file(self._current_path)

    def _show_context_menu(self, event):
        """Show context menu on right-click"""
        # Select item under cursor
        item = self.file_tree.identify_row(event.y)

        # If clicking in empty space, show "Create Project" menu
        if not item:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(
                label="➕ Créer un nouveau projet",
                command=self._create_new_project
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return

        self.file_tree.selection_set(item)

        # Get item type
        item_type = self._item_types.get(item)

        # Create context menu
        menu = tk.Menu(self, tearoff=0)

        # Check if it's a regular folder (in _path_items but not in _item_types)
        if item_type is None:
            # Get the path for this item
            path = self._path_items.get(item)
            if path and path.is_dir():
                # Sub-folder context menu
                menu.add_command(
                    label="Rattacher à un projet...",
                    command=lambda: self._create_rootfolder_and_attach(path)
                )
                menu.add_command(
                    label="Créer un nouveau projet",
                    command=lambda: self._create_project_and_attach_folder(path)
                )

        # Options based on item type
        elif isinstance(item_type, tuple) and item_type[0] == "root_folder":
            # Root folder context menu
            # Extract components (may have 3 or 4 elements depending on if subfolder_path is present)
            folder_id = item_type[1]
            project_id = item_type[2] if len(item_type) > 2 else None
            subfolder_path = item_type[3] if len(item_type) > 3 else None

            if project_id:
                # In a specific project - allow removal
                menu.add_command(
                    label="Retirer du projet",
                    command=lambda: self._remove_folder_from_project(folder_id, project_id, subfolder_path)
                )
                menu.add_separator()

            # Allow adding to another project
            menu.add_command(
                label="Rattacher à un projet...",
                command=lambda: self._attach_folder_to_project(folder_id)
            )
            menu.add_command(
                label="Créer un nouveau projet",
                command=lambda: self._create_project_with_folder(folder_id)
            )

        elif isinstance(item_type, tuple) and item_type[0] == "database":
            # Database context menu
            _, db_id, project_id = item_type
            if project_id:
                # In a specific project - allow removal
                menu.add_command(
                    label="Retirer du projet",
                    command=lambda: self._remove_database_from_project(db_id, project_id)
                )
                menu.add_separator()

            # Allow adding to another project
            menu.add_command(
                label="Rattacher à un projet...",
                command=lambda: self._attach_database_to_project(db_id)
            )
            menu.add_command(
                label="Créer un nouveau projet",
                command=lambda: self._create_project_with_database(db_id)
            )

        elif isinstance(item_type, tuple) and item_type[0] == "table":
            # Table context menu - Query options
            _, db_id, table_name = item_type

            # Get database connection to check if it's SQLite
            database = None
            for db_item, db_conn in self._db_items.items():
                if db_conn.id == db_id:
                    database = db_conn
                    break

            if database:
                is_sqlite = database.db_type.lower() == 'sqlite'

                menu.add_command(
                    label="SELECT TOP 10",
                    command=lambda: self._execute_table_query(db_id, table_name, 10, is_sqlite)
                )
                menu.add_command(
                    label="SELECT TOP 100",
                    command=lambda: self._execute_table_query(db_id, table_name, 100, is_sqlite)
                )
                menu.add_command(
                    label="SELECT TOP 1000",
                    command=lambda: self._execute_table_query(db_id, table_name, 1000, is_sqlite)
                )
                menu.add_separator()
                menu.add_command(
                    label="SELECT * (no limit)",
                    command=lambda: self._execute_table_query(db_id, table_name, None, is_sqlite)
                )
                menu.add_separator()
                menu.add_command(
                    label="COUNT(*) rows",
                    command=lambda: self._execute_count_query(db_id, table_name)
                )

        elif isinstance(item_type, tuple) and item_type[0] == "saved_query":
            # Saved Query context menu
            _, query_id, project_id = item_type
            if project_id:
                # In a specific project - allow removal
                menu.add_command(
                    label="Retirer du projet",
                    command=lambda: self._remove_query_from_project(query_id, project_id)
                )
                menu.add_separator()

            # Allow adding to project
            menu.add_command(
                label="Rattacher à un projet...",
                command=lambda: self._attach_query_to_project(query_id)
            )
            menu.add_separator()
            menu.add_command(
                label="✏️ Éditer la requête",
                command=lambda: self._edit_saved_query(query_id)
            )
            menu.add_command(
                label="▶️ Exécuter la requête",
                command=lambda: self._execute_saved_query(query_id)
            )

        elif isinstance(item_type, tuple) and item_type[0] == "project":
            # Project context menu
            _, project_id = item_type
            menu.add_command(
                label="⭐ Définir comme projet actif",
                command=lambda: self._set_active_project(project_id)
            )
            menu.add_separator()
            menu.add_command(
                label="🗑️ Supprimer projet",
                command=lambda: self._delete_project(project_id)
            )

        # Show menu if it has items
        if menu.index("end") is not None:
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def _attach_folder_to_project(self, folder_id):
        """Attach a folder to a project"""
        # Show project selection dialog
        projects = config_db.get_all_projects(sort_by_usage=False)
        if not projects:
            messagebox.showinfo("No Projects", "No projects available. Create a project first.")
            return

        # Create simple selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Select Project")
        dialog.geometry("400x300")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="Select a project:", padding="10").pack()

        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for project in projects:
            listbox.insert(tk.END, project.name)

        def on_select():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a project")
                return

            project = projects[selection[0]]
            success = config_db.add_project_file_root(project.id, folder_id)
            if success:
                self._refresh()
                logger.important(f"Attached folder to project: {project.name}")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to attach folder to project")

        ttk.Button(dialog, text="Attach", command=on_select).pack(pady=5)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack()

    def _attach_database_to_project(self, db_id):
        """Attach a database to a project"""
        # Similar to _attach_folder_to_project
        projects = config_db.get_all_projects(sort_by_usage=False)
        if not projects:
            messagebox.showinfo("No Projects", "No projects available. Create a project first.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Select Project")
        dialog.geometry("400x300")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="Select a project:", padding="10").pack()

        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for project in projects:
            listbox.insert(tk.END, project.name)

        def on_select():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a project")
                return

            project = projects[selection[0]]
            success = config_db.add_project_database(project.id, db_id)
            if success:
                self._refresh()
                logger.important(f"Attached database to project: {project.name}")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to attach database to project")

        ttk.Button(dialog, text="Attach", command=on_select).pack(pady=5)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack()

    def _create_project_with_folder(self, folder_id):
        """Create a new project and attach folder"""
        from .project_manager import ProjectDialog
        dialog = ProjectDialog(self.winfo_toplevel())
        result = dialog.show()

        if result:
            # Attach folder to new project
            success = config_db.add_project_file_root(result.id, folder_id)
            if success:
                self._refresh()
                logger.important(f"Created project '{result.name}' with folder")
            else:
                messagebox.showerror("Error", "Failed to attach folder to new project")

    def _create_project_with_database(self, db_id):
        """Create a new project and attach database"""
        from .project_manager import ProjectDialog
        dialog = ProjectDialog(self.winfo_toplevel())
        result = dialog.show()

        if result:
            # Attach database to new project
            success = config_db.add_project_database(result.id, db_id)
            if success:
                self._refresh()
                logger.important(f"Created project '{result.name}' with database")
            else:
                messagebox.showerror("Error", "Failed to attach database to new project")

    def _remove_folder_from_project(self, folder_id, project_id, subfolder_path=None):
        """Remove a folder from a project"""
        response = messagebox.askyesno(
            "Confirm",
            "Remove this folder from the project?",
            icon='question'
        )
        if response:
            success = config_db.remove_project_file_root(project_id, folder_id, subfolder_path)
            if success:
                self._refresh()
                logger.important("Removed folder from project")
            else:
                messagebox.showerror("Error", "Failed to remove folder from project")

    def _remove_database_from_project(self, db_id, project_id):
        """Remove a database from a project"""
        response = messagebox.askyesno(
            "Confirm",
            "Remove this database from the project?",
            icon='question'
        )
        if response:
            success = config_db.remove_project_database(project_id, db_id)
            if success:
                self._refresh()
                logger.important("Removed database from project")
            else:
                messagebox.showerror("Error", "Failed to remove database from project")

    def _set_active_project(self, project_id):
        """Set a project as the active project (most recently used)"""
        success = config_db.update_project_last_used(project_id)
        if success:
            self._refresh()
            project = config_db.get_project(project_id)
            logger.important(f"Projet actif : {project.name if project else project_id}")
        else:
            messagebox.showerror("Error", "Failed to set active project")

    def _execute_table_query(self, db_id: str, table_name: str, limit: Optional[int], is_sqlite: bool):
        """Execute a SELECT query on a table with optional limit and display results in DataExplorer"""
        import sqlite3
        import pyodbc
        import re
        from ..database.connections_config import connections_manager

        # Get database connection config
        db_conn = connections_manager.get_connection(db_id)
        if not db_conn:
            messagebox.showerror("Error", "Database connection not found.")
            return

        # Generate query based on database type and limit
        if limit is None:
            query = f"SELECT * FROM [{table_name}]"
        elif is_sqlite:
            query = f"SELECT * FROM [{table_name}] LIMIT {limit}"
        else:
            query = f"SELECT TOP {limit} * FROM [{table_name}]"

        conn = None
        try:
            # Create connection
            if db_conn.db_type == 'sqlite':
                # Extract path from connection string
                match = re.search(r'Database=([^;]+)', db_conn.connection_string, re.IGNORECASE)
                db_path = match.group(1).strip() if match else db_conn.connection_string
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
            else:
                conn = pyodbc.connect(db_conn.connection_string)

            # Execute query
            cursor = conn.cursor()
            cursor.execute(query)

            if cursor.description:
                # Get columns
                columns = [column[0] for column in cursor.description]

                # Fetch rows
                rows = cursor.fetchall()

                # Convert to list of dicts for CustomDataGridView
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col_name in enumerate(columns):
                        row_dict[col_name] = row[i] if i < len(row) else None
                    data.append(row_dict)

                # Display data in the data grid
                self.data_grid.pack_forget()
                self.raw_viewer_container.pack_forget()
                self.data_grid.pack(fill=tk.BOTH, expand=True)
                self.data_grid.load_data(data, columns)

                # Calculate and display statistics
                stats_data = CustomDataGridView.calculate_column_statistics(data, columns)
                self.stats_grid.load_data(stats_data, columns=['Column', 'Total', 'Non-Null', 'Empty', 'Distinct'])

                # Update file info label
                self.file_info_label.config(text=f"Query Results: {table_name}")
                self.path_label.config(text=f"Database: {db_conn.name} | {len(data)} rows × {len(columns)} columns")

                logger.info(f"Executed SELECT on {table_name} with limit={limit}: {len(data)} rows")
            else:
                messagebox.showinfo("Query Executed", "Query executed successfully with no results.")

            conn.commit()

        except Exception as e:
            logger.error(f"Error executing table query: {e}")
            messagebox.showerror("Error", f"Failed to execute query:\n{str(e)}")

        finally:
            if conn:
                conn.close()

    def _execute_count_query(self, db_id: str, table_name: str):
        """Execute a COUNT(*) query on a table and display results in DataExplorer"""
        import sqlite3
        import pyodbc
        import re
        from ..database.connections_config import connections_manager

        # Get database connection config
        db_conn = connections_manager.get_connection(db_id)
        if not db_conn:
            messagebox.showerror("Error", "Database connection not found.")
            return

        query = f"SELECT COUNT(*) AS row_count FROM [{table_name}]"

        conn = None
        try:
            # Create connection
            if db_conn.db_type == 'sqlite':
                # Extract path from connection string
                match = re.search(r'Database=([^;]+)', db_conn.connection_string, re.IGNORECASE)
                db_path = match.group(1).strip() if match else db_conn.connection_string
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
            else:
                conn = pyodbc.connect(db_conn.connection_string)

            # Execute query
            cursor = conn.cursor()
            cursor.execute(query)

            if cursor.description:
                # Get columns
                columns = [column[0] for column in cursor.description]

                # Fetch rows
                rows = cursor.fetchall()

                # Convert to list of dicts for CustomDataGridView
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col_name in enumerate(columns):
                        row_dict[col_name] = row[i] if i < len(row) else None
                    data.append(row_dict)

                # Display data in the data grid
                self.data_grid.pack_forget()
                self.raw_viewer_container.pack_forget()
                self.data_grid.pack(fill=tk.BOTH, expand=True)
                self.data_grid.load_data(data, columns)

                # Calculate and display statistics
                stats_data = CustomDataGridView.calculate_column_statistics(data, columns)
                self.stats_grid.load_data(stats_data, columns=['Column', 'Total', 'Non-Null', 'Empty', 'Distinct'])

                # Update file info label
                row_count = data[0].get('row_count', 0) if data else 0
                self.file_info_label.config(text=f"Row Count: {table_name}")
                self.path_label.config(text=f"Database: {db_conn.name} | Total rows: {row_count}")

                logger.info(f"Executed COUNT(*) on {table_name}: {row_count} rows")
            else:
                messagebox.showinfo("Query Executed", "Query executed successfully with no results.")

            conn.commit()

        except Exception as e:
            logger.error(f"Error executing count query: {e}")
            messagebox.showerror("Error", f"Failed to execute query:\n{str(e)}")

        finally:
            if conn:
                conn.close()

    def _find_parent_file_root(self, folder_path: Path):
        """
        Find the parent FileRoot that contains the given folder path

        Returns:
            Tuple of (FileRoot, relative_path) where relative_path is None if folder_path
            is the root itself, or the relative path from the root to the folder
        """
        from ..database.config_db import FileRoot

        # Get all application RootFolders
        all_roots = config_db.get_all_file_roots()

        # Check if the folder is exactly a RootFolder
        for root in all_roots:
            root_path = Path(root.path)
            if folder_path == root_path:
                return (root, None)

        # Check if the folder is a subfolder of a RootFolder
        for root in all_roots:
            root_path = Path(root.path)
            try:
                # Check if folder_path is relative to root_path
                rel_path = folder_path.relative_to(root_path)
                return (root, str(rel_path))
            except ValueError:
                # Not a child of this root
                continue

        # Not found in any RootFolder
        return (None, None)

    def _create_project_and_attach_folder(self, folder_path: Path):
        """Create a new project and attach a folder (can be RootFolder or subfolder)"""
        from .project_manager import ProjectDialog

        # Find parent FileRoot for this folder
        parent_root, subfolder_rel_path = self._find_parent_file_root(folder_path)

        if parent_root is None:
            messagebox.showerror(
                "Error",
                f"Le dossier sélectionné n'est pas dans un RootFolder de l'application.\n\n"
                f"Chemin: {folder_path}\n\n"
                f"Veuillez d'abord créer un RootFolder qui contient ce dossier."
            )
            return

        # Open project dialog to create new project
        dialog = ProjectDialog(self.winfo_toplevel())
        result = dialog.show()

        if result:
            # Attach folder to new project
            success = config_db.add_project_file_root(result.id, parent_root.id, subfolder_rel_path)
            if success:
                self._refresh()
                display_path = str(folder_path) if subfolder_rel_path else parent_root.path
                logger.important(f"Created project '{result.name}' with folder '{display_path}'")
                messagebox.showinfo("Success", f"Projet '{result.name}' créé avec le dossier")
            else:
                messagebox.showerror("Error", "Failed to attach folder to new project")

    def _create_rootfolder_from_path(self, folder_path: Path):
        """Create a new RootFolder from a subfolder path"""
        from ..database.config_db import FileRoot
        from tkinter import simpledialog

        # Ask for description
        description = simpledialog.askstring(
            "New RootFolder",
            f"Description for RootFolder:\n{folder_path}",
            initialvalue=folder_path.name
        )

        if description is None:  # User cancelled
            return

        # Create FileRoot
        file_root = FileRoot(
            id="",  # Will be auto-generated
            path=str(folder_path),
            description=description
        )

        # Add to database
        success = config_db.add_file_root(file_root)
        if success:
            self._refresh()
            messagebox.showinfo("Success", f"RootFolder créé : {file_root.description}")
            logger.important(f"Created RootFolder: {file_root.path}")
        else:
            messagebox.showerror("Error", "Failed to create RootFolder")

    def _create_rootfolder_and_attach(self, folder_path: Path):
        """Attach a folder (RootFolder or subfolder) to an existing project"""
        # Get all projects
        projects = config_db.get_all_projects(sort_by_usage=False)
        if not projects:
            messagebox.showinfo("No Projects", "No projects available. Create a project first.")
            return

        # Find parent FileRoot for this folder
        parent_root, subfolder_rel_path = self._find_parent_file_root(folder_path)

        if parent_root is None:
            messagebox.showerror(
                "Error",
                f"Le dossier sélectionné n'est pas dans un RootFolder de l'application.\n\n"
                f"Chemin: {folder_path}\n\n"
                f"Veuillez d'abord créer un RootFolder qui contient ce dossier."
            )
            return

        # Show project selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Select Project")
        dialog.geometry("400x300")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="Select a project to attach the folder:", padding="10").pack()

        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for project in projects:
            listbox.insert(tk.END, project.name)

        def on_select():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a project")
                return

            project = projects[selection[0]]
            success = config_db.add_project_file_root(project.id, parent_root.id, subfolder_rel_path)
            if success:
                self._refresh()
                display_path = str(folder_path) if subfolder_rel_path else parent_root.path
                logger.important(f"Attached folder '{display_path}' to project: {project.name}")
                dialog.destroy()
                messagebox.showinfo("Success", f"Dossier rattaché au projet '{project.name}'")
            else:
                messagebox.showerror("Error", "Failed to attach folder to project")

        ttk.Button(dialog, text="Attach", command=on_select).pack(pady=5)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack()

    def _save_tree_state(self):
        """Save which tree nodes are currently open"""
        open_items = set()

        def collect_open_items(item):
            # Check if item is open
            if self.file_tree.item(item, "open"):
                # Save the item type/ID so we can find it again after refresh
                if item in self._item_types:
                    item_type = self._item_types[item]
                    open_items.add(item_type)

            # Recurse to children
            for child in self.file_tree.get_children(item):
                collect_open_items(child)

        # Collect from all root items
        for item in self.file_tree.get_children():
            collect_open_items(item)

        return open_items

    def _restore_tree_state(self, open_items):
        """Restore tree nodes that should be open"""
        if not open_items:
            return

        def restore_items(item):
            # Check if this item should be open
            if item in self._item_types:
                item_type = self._item_types[item]
                if item_type in open_items:
                    self.file_tree.item(item, open=True)

            # Recurse to children
            for child in self.file_tree.get_children(item):
                restore_items(child)

        # Restore from all root items
        for item in self.file_tree.get_children():
            restore_items(item)

    def _refresh(self):
        """Refresh file tree while preserving expansion state"""
        # Save which nodes are currently open
        open_items = self._save_tree_state()

        # Reload the tree
        self._load_projects()

        # Restore open state
        self._restore_tree_state(open_items)

        logger.info("File tree refreshed")

    def _go_up(self):
        """Go up one level"""
        if not self._current_path:
            messagebox.showinfo("Info", "No folder selected")
            return

        parent = self._current_path.parent
        if parent and parent != self._current_path:
            # Find parent in tree and select it
            for item, path in self._path_items.items():
                if path == parent:
                    self.file_tree.selection_set(item)
                    self.file_tree.focus(item)
                    self.file_tree.see(item)
                    break

    def _go_to_root(self):
        """Go to root folder"""
        self._current_path = None
        self._current_root = None
        self.path_label.config(text="")
        self.file_info_label.config(text="No file selected")
        self.content_text.delete(1.0, tk.END)

    def _apply_log_filter(self):
        """Apply log level filter to displayed log content"""
        if not self._log_content:
            return

        # Clear current display
        self.content_text.delete(1.0, tk.END)

        # Get filter settings
        show_error = self.log_filter_error.get()
        show_warning = self.log_filter_warning.get()
        show_important = self.log_filter_important.get()
        show_info = self.log_filter_info.get()

        # Split content into lines
        lines = self._log_content.splitlines()

        # Limit to first 10,000 lines if needed
        if len(lines) > 10000:
            self.content_text.insert(1.0, f"[Showing first 10,000 of {len(lines)} lines with filters applied]\n\n")
            lines = lines[:10000]

        # Filter and display lines
        filtered_lines = []
        for line in lines:
            # Check if line contains log level keywords
            line_upper = line.upper()

            # Detect log level in line
            is_error = '[ERROR' in line_upper or 'ERROR]' in line_upper
            is_warning = '[WARNING' in line_upper or 'WARNING]' in line_upper
            is_important = '[IMPORTANT' in line_upper or 'IMPORTANT]' in line_upper
            is_info = '[INFO' in line_upper or 'INFO]' in line_upper

            # Include line if its level is enabled (or if no level detected and INFO is enabled)
            should_include = False
            if is_error and show_error:
                should_include = True
            elif is_warning and show_warning:
                should_include = True
            elif is_important and show_important:
                should_include = True
            elif is_info and show_info:
                should_include = True
            elif not (is_error or is_warning or is_important or is_info):
                # No log level detected - include if INFO is enabled (default behavior)
                should_include = show_info

            if should_include:
                filtered_lines.append(line)

        # Display filtered content
        filtered_content = "\n".join(filtered_lines)
        self.content_text.insert(tk.END, filtered_content)

        # Show filter summary
        total_lines = len(lines)
        shown_lines = len(filtered_lines)
        if shown_lines < total_lines:
            self.content_text.insert(1.0, f"[Filtered: Showing {shown_lines} of {total_lines} lines]\n\n")

        logger.info(f"Log filter applied: showing {shown_lines} of {total_lines} lines")

    def _create_new_project(self):
        """Create a new project"""
        from .project_manager import ProjectDialog
        dialog = ProjectDialog(self.winfo_toplevel())
        result = dialog.show()

        if result:
            self._refresh()
            logger.important(f"Created new project: {result.name}")
            messagebox.showinfo("Success", f"Projet '{result.name}' créé avec succès")

    def _delete_project(self, project_id):
        """Delete a project"""
        # Get project details for confirmation
        project = config_db.get_project(project_id)
        if not project:
            messagebox.showerror("Error", "Project not found")
            return

        # Confirm deletion
        response = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this project?\n\n"
            f"Project: {project.name}\n\n"
            f"Note: This will only delete the project, not the associated folders or databases.",
            icon='warning'
        )

        if response:
            success = config_db.delete_project(project_id)
            if success:
                self._refresh()
                logger.important(f"Deleted project: {project.name}")
                messagebox.showinfo("Success", f"Project '{project.name}' deleted successfully")
            else:
                messagebox.showerror("Error", "Failed to delete project")

    def _attach_query_to_project(self, query_id):
        """Attach a saved query to a project"""
        # Show project selection dialog
        projects = config_db.get_all_projects(sort_by_usage=False)
        if not projects:
            messagebox.showinfo("No Projects", "No projects available. Create a project first.")
            return

        # Create simple selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Select Project")
        dialog.geometry("400x300")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="Select a project:", padding="10").pack()

        listbox = tk.Listbox(dialog)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for project in projects:
            listbox.insert(tk.END, project.name)

        def on_select():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a project")
                return

            project = projects[selection[0]]
            success = config_db.add_project_query(project.id, query_id)
            if success:
                self._refresh()
                logger.important(f"Attached query to project: {project.name}")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to attach query to project")

        ttk.Button(dialog, text="Attach", command=on_select).pack(pady=5)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack()

    def _remove_query_from_project(self, query_id, project_id):
        """Remove a query from a project"""
        response = messagebox.askyesno(
            "Confirm",
            "Remove this query from the project?",
            icon='question'
        )
        if response:
            success = config_db.remove_project_query(project_id, query_id)
            if success:
                self._refresh()
                logger.important("Removed query from project")
            else:
                messagebox.showerror("Error", "Failed to remove query from project")

    def _edit_saved_query(self, query_id):
        """Open a saved query in Database Manager for editing"""
        # Get the query
        all_queries = config_db.get_all_saved_queries()
        query = None
        for q in all_queries:
            if q.id == query_id:
                query = q
                break

        if not query:
            messagebox.showerror("Error", "Query not found")
            return

        # Switch to Database Manager and load the query for editing
        if self.gui_parent and hasattr(self.gui_parent, '_show_database_frame_with_query'):
            self.gui_parent._show_database_frame_with_query(query, execute=False)
            logger.info(f"Opened query for editing: {query.name}")
        else:
            messagebox.showerror("Error", "Could not access Database Manager. Please open it manually from Databases menu.")

    def _execute_saved_query(self, query_id):
        """Execute a saved query and display results in DataExplorer"""
        import sqlite3
        import pyodbc
        from ..database.connections_config import connections_manager

        # Get the query
        all_queries = config_db.get_all_saved_queries()
        query = None
        for q in all_queries:
            if q.id == query_id:
                query = q
                break

        if not query:
            messagebox.showerror("Error", "Query not found")
            return

        # Get database connection config
        db_conn = connections_manager.get_connection(query.target_database_id)
        if not db_conn:
            messagebox.showerror("Error", "Database connection not found.")
            return

        # Execute query
        conn = None
        try:
            # Connect to database
            if db_conn.db_type.lower() == 'sqlite':
                # Extract path from connection string
                import re
                match = re.search(r'Database=([^;]+)', db_conn.connection_string, re.IGNORECASE)
                db_path = match.group(1).strip() if match else db_conn.connection_string
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
            else:
                conn = pyodbc.connect(db_conn.connection_string)
                cursor = conn.cursor()

            # Execute the saved query
            cursor.execute(query.query_text)

            if cursor.description:
                # Get columns
                columns = [column[0] for column in cursor.description]

                # Fetch rows
                rows = cursor.fetchall()

                # Convert to list of dicts for CustomDataGridView
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col_name in enumerate(columns):
                        row_dict[col_name] = row[i] if i < len(row) else None
                    data.append(row_dict)

                # Display data in the data grid
                self.data_grid.pack_forget()
                self.raw_viewer_container.pack_forget()
                self.data_grid.pack(fill=tk.BOTH, expand=True)
                self.data_grid.load_data(data, columns)

                # Calculate and display statistics
                stats_data = CustomDataGridView.calculate_column_statistics(data, columns)
                self.stats_grid.load_data(stats_data, columns=['Column', 'Total', 'Non-Null', 'Empty', 'Distinct'])

                # Update file info label
                self.file_info_label.config(text=f"Query Results: {query.name}")
                self.path_label.config(text=f"Database: {db_conn.name} | Category: {query.category} | {len(data)} rows × {len(columns)} columns")

                logger.info(f"Executed saved query '{query.name}': {len(data)} rows returned")
            else:
                # No results to display
                logger.info(f"Executed saved query '{query.name}': No rows returned or no result set")

        except Exception as e:
            logger.error(f"Error executing saved query '{query.name}': {e}")
            messagebox.showerror("Query Error", f"Error executing query:\n{str(e)}")

        finally:
            if conn:
                conn.close()

    def _apply_tree_tags(self):
        """Apply theme colors to tree tags"""
        from ..config.theme_manager import get_theme_manager
        theme = get_theme_manager().get_current_theme()

        # Configure tags with theme colors
        self.file_tree.tag_configure(
            "project",
            foreground=theme.get('tag_project_fg', 'white'),
            background=theme.get('tag_project_bg', '#1E90FF'),
            font=("Arial", 9, "bold")
        )
        self.file_tree.tag_configure(
            "separator",
            foreground=theme.get('tag_separator_fg', 'lightgray'),
            font=("Arial", 6)
        )
        self.file_tree.tag_configure(
            "section",
            foreground=theme.get('tag_section_fg', 'darkblue')
        )
        self.file_tree.tag_configure(
            "root",
            foreground=theme.get('tag_root_fg', 'darkgreen')
        )
        self.file_tree.tag_configure(
            "folder",
            foreground=theme.get('tag_folder_fg', 'darkgreen')
        )
        self.file_tree.tag_configure(
            "file",
            foreground=theme.get('tag_file_fg', 'black')
        )
        self.file_tree.tag_configure(
            "database",
            foreground=theme.get('tag_database_fg', 'purple')
        )
        self.file_tree.tag_configure(
            "category",
            foreground=theme.get('tag_category_fg', 'darkorange')
        )
        self.file_tree.tag_configure(
            "query",
            foreground=theme.get('tag_query_fg', 'darkblue')
        )
        self.file_tree.tag_configure(
            "error",
            foreground=theme.get('tag_error_fg', 'red')
        )
        self.file_tree.tag_configure(
            "info",
            foreground=theme.get('tag_info_fg', 'gray')
        )

    def apply_theme(self):
        """Apply current theme to all child components"""
        try:
            # Apply theme to tree tags
            self._apply_tree_tags()

            # Apply theme to file tree
            if hasattr(self, 'file_tree') and hasattr(self.file_tree, 'apply_theme'):
                self.file_tree.apply_theme()

            # Apply theme to data grid
            if hasattr(self, 'data_grid') and hasattr(self.data_grid, 'apply_theme'):
                self.data_grid.apply_theme()

            # Apply theme to stats grid
            if hasattr(self, 'stats_grid') and hasattr(self.stats_grid, 'apply_theme'):
                self.stats_grid.apply_theme()

        except Exception as e:
            logger.debug(f"Failed to apply theme to DataExplorer: {e}")
