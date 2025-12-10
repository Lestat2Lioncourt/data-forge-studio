"""
RootFolder Manager Module - Manage RootFolders with TreeView
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional
from datetime import datetime
from ..utils.logger import logger
from ..database.config_db import FileRoot, config_db
from .base_view_frame import BaseViewFrame
from .custom_datagridview import CustomDataGridView
from .file_root_manager import show_file_root_manager
from .custom_treeview_panel import CustomTreeViewPanel


class RootFolderManager(BaseViewFrame):
    """RootFolder Manager GUI - Manage RootFolders"""

    def __init__(self, parent):
        # Define toolbar buttons
        toolbar_buttons = [
            ("➕ New RootFolder", self._new_rootfolder),
            ("✏️ Edit RootFolder", self._edit_rootfolder),
            ("🗑️ Delete RootFolder", self._delete_rootfolder),
            ("🔄 Refresh", self._refresh),
        ]

        # Initialize base with standard layout
        super().__init__(
            parent,
            toolbar_buttons=toolbar_buttons,
            show_left_panel=True,
            left_weight=1,
            right_weight=2,
            top_weight=1,
            bottom_weight=1
        )

        self.rootfolders_tree = None
        self.selected_rootfolder = None
        self.files_grid = None

        # Create content for each panel
        self._create_left_content()
        self._create_top_content()
        self._create_bottom_content()

        # Load rootfolders
        self._load_rootfolders()

    def _create_left_content(self):
        """Create TreeView in left panel"""
        # Use CustomTreeViewPanel for standardized tree with expand support
        tree_panel = CustomTreeViewPanel(
            self.left_frame,
            title="RootFolders",
            on_select=self._on_folder_select,
            on_expand=self._on_folder_expand
        )
        tree_panel.pack(fill=tk.BOTH, expand=True)

        # Keep reference to the internal tree
        self.rootfolders_tree = tree_panel.tree

    def _create_top_content(self):
        """Create RootFolder details in top panel"""
        # Use helper method for standardized title
        title = self.create_panel_title(self.top_frame, "RootFolder Details", font_size=11)
        title.pack_configure(pady=(5, 2), anchor=tk.W, padx=10)

        details_frame = ttk.Frame(self.top_frame, padding="5")
        details_frame.pack(fill=tk.BOTH, expand=True)

        # Name
        ttk.Label(details_frame, text="Name:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_label = ttk.Label(details_frame, text="", foreground="blue", font=("Arial", 9))
        self.name_label.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # Path
        ttk.Label(details_frame, text="Path:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.path_label = ttk.Label(details_frame, text="", foreground="green", font=("Arial", 9))
        self.path_label.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        # Description
        ttk.Label(details_frame, text="Description:", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.description_label = ttk.Label(details_frame, text="", font=("Arial", 9))
        self.description_label.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)

        details_frame.columnconfigure(1, weight=1)

    def _create_bottom_content(self):
        """Create files grid in bottom panel"""
        # Use helper method for standardized title
        self.create_panel_title(self.bottom_frame, "Folder Contents")

        # Use CustomDataGridView for files
        self.files_grid = CustomDataGridView(
            self.bottom_frame,
            show_export=True,
            show_copy=True,
            show_refresh=False
        )
        self.files_grid.pack(fill=tk.BOTH, expand=True)

    def _load_rootfolders(self):
        """Load all rootfolders into tree"""
        # Clear tree
        for item in self.rootfolders_tree.get_children():
            self.rootfolders_tree.delete(item)

        # Get all rootfolders
        all_rootfolders = config_db.get_all_file_roots()

        if not all_rootfolders:
            self.rootfolders_tree.insert("", "end", text="No RootFolders configured", values=("info",))
            return

        for rootfolder in all_rootfolders:
            icon = "📁"
            # Use path as display name (extract folder name from path)
            path_obj = Path(rootfolder.path)
            display_name = path_obj.name if path_obj.name else rootfolder.path
            node_id = self.rootfolders_tree.insert(
                "", "end",
                text=f"{icon} {display_name}",
                values=(rootfolder.id, str(path_obj), "rootfolder"),
                tags=("rootfolder",)
            )

            # Add dummy child to make it expandable (lazy loading)
            if path_obj.exists() and path_obj.is_dir():
                if any(item.is_dir() for item in path_obj.iterdir()):
                    self.rootfolders_tree.insert(node_id, "end", text="dummy")

        logger.info(f"Loaded {len(all_rootfolders)} rootfolders")

    def _on_folder_expand(self, event):
        """Handle folder expansion - load subdirectories (lazy loading)"""
        node = self.rootfolders_tree.focus()
        if not node:
            return

        # Check if this node has dummy children
        children = self.rootfolders_tree.get_children(node)
        if len(children) == 1 and self.rootfolders_tree.item(children[0], "text") == "dummy":
            # Remove dummy
            self.rootfolders_tree.delete(children[0])

            # Load actual subdirectories
            node_values = self.rootfolders_tree.item(node, "values")
            if len(node_values) >= 2:
                folder_path = Path(node_values[1])
                self._load_subdirectories(node, folder_path)

    def _load_subdirectories(self, parent_node, parent_path: Path):
        """Load subdirectories of a folder"""
        try:
            if not parent_path.exists() or not parent_path.is_dir():
                return

            # Get all subdirectories
            subdirs = []
            for item in parent_path.iterdir():
                if item.is_dir():
                    subdirs.append(item)

            # Sort by name
            subdirs.sort(key=lambda x: x.name.lower())

            # Add to tree
            for subdir in subdirs:
                child_node = self.rootfolders_tree.insert(
                    parent_node, "end",
                    text=f"📁 {subdir.name}",
                    values=("", str(subdir), "folder"),  # Empty rootfolder_id, path, type
                    tags=("folder",)
                )

                # Add dummy if this folder has subdirectories
                try:
                    if any(subitem.is_dir() for subitem in subdir.iterdir()):
                        self.rootfolders_tree.insert(child_node, "end", text="dummy")
                except Exception:
                    pass  # Permission error or similar

        except Exception as e:
            logger.error(f"Error loading subdirectories of {parent_path}: {e}")

    def _on_folder_select(self, event):
        """Handle folder selection (RootFolder or subfolder)"""
        selection = self.rootfolders_tree.selection()
        if not selection:
            return

        item_values = self.rootfolders_tree.item(selection[0], "values")
        if not item_values or len(item_values) < 1:
            self._clear_details()
            return

        # Check if it's info node
        if item_values[0] == "info":
            self._clear_details()
            return

        # Get the folder path (index 1) and type (index 2 if exists)
        if len(item_values) < 2:
            self._clear_details()
            return

        folder_path_str = item_values[1]
        folder_path = Path(folder_path_str)

        # Get rootfolder_id if it's a rootfolder node
        rootfolder_id = item_values[0] if item_values[0] else None

        # Show folder details and contents
        self._show_folder_details(folder_path, rootfolder_id)

    def _show_folder_details(self, folder_path: Path, rootfolder_id: Optional[str] = None):
        """Show details of selected folder (RootFolder or subfolder)"""
        # If it's a RootFolder, get its info from database
        if rootfolder_id:
            all_rootfolders = config_db.get_all_file_roots()
            rootfolder = None
            for rf in all_rootfolders:
                if rf.id == rootfolder_id:
                    rootfolder = rf
                    break

            if rootfolder:
                self.selected_rootfolder = rootfolder
                display_name = folder_path.name if folder_path.name else rootfolder.path
                self.name_label.config(text=display_name)
                self.path_label.config(text=str(rootfolder.path))
                self.description_label.config(text=rootfolder.description if rootfolder.description else "No description")
            else:
                self.selected_rootfolder = None
                self.name_label.config(text=folder_path.name)
                self.path_label.config(text=str(folder_path))
                self.description_label.config(text="Subfolder")
        else:
            # It's a subfolder, not a RootFolder
            self.selected_rootfolder = None
            self.name_label.config(text=folder_path.name)
            self.path_label.config(text=str(folder_path))
            self.description_label.config(text="Subfolder")

        # Load folder contents
        self._load_folder_contents(folder_path)

    def _load_folder_contents(self, folder_path: Path):
        """Load files in folder into grid"""
        try:
            if not folder_path.exists():
                self.files_grid.clear()
                return

            # Get all files in folder
            files_data = []
            for item in folder_path.iterdir():
                try:
                    name = item.name
                    if item.is_file():
                        size = item.stat().st_size
                        # Format size
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.2f} KB"
                        elif size < 1024 * 1024 * 1024:
                            size_str = f"{size / (1024 * 1024):.2f} MB"
                        else:
                            size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
                    else:
                        size_str = "<DIR>"

                    # Get creation time
                    creation_time = datetime.fromtimestamp(item.stat().st_ctime)
                    date_str = creation_time.strftime("%Y-%m-%d %H:%M:%S")

                    files_data.append([name, size_str, date_str])
                except Exception as e:
                    logger.error(f"Error reading file {item}: {e}")
                    continue

            # Sort by name
            files_data.sort(key=lambda x: x[0])

            # Convert to dict format for CustomDataGridView
            dict_data = []
            for item in files_data:
                dict_data.append({
                    "Name": item[0],
                    "Size": item[1],
                    "Creation Date": item[2]
                })

            # Load data in grid
            columns = ["Name", "Size", "Creation Date"]
            self.files_grid.load_data(dict_data, columns)

            logger.info(f"Loaded {len(files_data)} items from {folder_path}")

        except Exception as e:
            logger.error(f"Error loading folder contents: {e}")
            self.files_grid.clear()

    def _clear_details(self):
        """Clear rootfolder details"""
        self.selected_rootfolder = None
        self.name_label.config(text="")
        self.path_label.config(text="")
        self.description_label.config(text="")
        self.files_grid.clear()

    def _new_rootfolder(self):
        """Create new rootfolder"""
        parent = self.winfo_toplevel()
        show_file_root_manager(parent)
        self._refresh()

    def _edit_rootfolder(self):
        """Edit selected rootfolder"""
        if not self.selected_rootfolder:
            messagebox.showwarning("No Selection", "Please select a RootFolder to edit.")
            return

        parent = self.winfo_toplevel()
        show_file_root_manager(parent)
        self._refresh()

    def _delete_rootfolder(self):
        """Delete selected rootfolder"""
        if not self.selected_rootfolder:
            messagebox.showwarning("No Selection", "Please select a RootFolder to delete.")
            return

        path_obj = Path(self.selected_rootfolder.path)
        display_name = path_obj.name if path_obj.name else self.selected_rootfolder.path

        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this RootFolder?\n\nName: {display_name}\nPath: {self.selected_rootfolder.path}"
        )

        if result:
            if config_db.delete_file_root(self.selected_rootfolder.id):
                logger.important(f"Deleted RootFolder: {display_name}")
                self._refresh()
            else:
                messagebox.showerror("Error", "Failed to delete RootFolder.")

    def _refresh(self):
        """Refresh rootfolders list"""
        self._load_rootfolders()
        self._clear_details()
        logger.info("RootFolders refreshed")
