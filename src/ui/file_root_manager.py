"""
File Root Manager Module - Manage file root directories
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
from ..database.config_db import FileRoot, config_db
from ..utils.logger import logger
from .custom_datagridview import CustomDataGridView


class FileRootDialog(tk.Toplevel):
    """Dialog for adding/editing file root directories"""

    def __init__(self, parent, file_root: Optional[FileRoot] = None):
        super().__init__(parent)
        self.file_root = file_root
        self.result = None

        # Configure dialog
        self.title("Add File Root" if file_root is None else "Edit File Root")
        self.geometry("500x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._load_data()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Path
        ttk.Label(main_frame, text="Root Path:").grid(row=0, column=0, sticky=tk.W, pady=5)

        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)

        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=40)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(path_frame, text="Browse...", command=self._browse_path).pack(side=tk.LEFT, padx=(5, 0))

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.description_var, width=50).grid(
            row=1, column=1, sticky=tk.EW, pady=5, padx=5
        )

        main_frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Save", command=self._save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side=tk.LEFT, padx=5)

    def _browse_path(self):
        """Browse for directory"""
        current_path = self.path_var.get()
        initial_dir = current_path if current_path and Path(current_path).exists() else Path.home()

        path = filedialog.askdirectory(
            parent=self,
            title="Select Root Directory",
            initialdir=initial_dir
        )

        if path:
            self.path_var.set(path)

    def _load_data(self):
        """Load existing file root data if editing"""
        if self.file_root:
            self.path_var.set(self.file_root.path)
            self.description_var.set(self.file_root.description)

    def _save(self):
        """Save file root"""
        path = self.path_var.get().strip()
        description = self.description_var.get().strip()

        # Validation
        if not path:
            messagebox.showerror("Validation Error", "Please specify a root path.")
            return

        if not description:
            messagebox.showerror("Validation Error", "Please provide a description.")
            return

        # Check if path exists
        if not Path(path).exists():
            response = messagebox.askyesno(
                "Path Does Not Exist",
                f"The path '{path}' does not exist.\n\nDo you want to create it?",
                icon='warning'
            )
            if response:
                try:
                    Path(path).mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to create directory:\n{e}")
                    return
            else:
                return

        # Create or update FileRoot
        if self.file_root:
            # Update existing
            self.file_root.path = path
            self.file_root.description = description
            success = config_db.update_file_root(self.file_root)
            action = "updated"
        else:
            # Create new
            file_root = FileRoot(
                id="",  # Auto-generated
                path=path,
                description=description
            )
            success = config_db.add_file_root(file_root)
            action = "added"
            self.file_root = file_root

        if success:
            self.result = self.file_root
            logger.important(f"File root {action}: {path}")
            self.destroy()
        else:
            messagebox.showerror("Error", f"Failed to {action.rstrip('d')} file root.")

    def _cancel(self):
        """Cancel dialog"""
        self.destroy()


class FileRootManager(ttk.Frame):
    """File Root Manager - Manage file root directories"""

    def __init__(self, parent):
        super().__init__(parent)
        self._create_widgets()
        self._load_file_roots()

    def _create_widgets(self):
        """Create manager widgets"""
        # Header
        header_frame = ttk.Frame(self, padding="10")
        header_frame.pack(fill=tk.X)

        ttk.Label(
            header_frame,
            text="File Root Manager",
            font=("Arial", 14, "bold")
        ).pack(side=tk.LEFT)

        # Toolbar
        toolbar = ttk.Frame(self, padding="5")
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="Add Root", command=self._add_root).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit Root", command=self._edit_root).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete Root", command=self._delete_root).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Refresh", command=self._load_file_roots).pack(side=tk.LEFT, padx=2)

        # Data Grid
        self.data_grid = CustomDataGridView(
            self,
            show_export=True,
            show_copy=True,
            show_raw_toggle=False
        )
        self.data_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bind double-click to edit
        self.data_grid.tree.bind("<Double-Button-1>", lambda e: self._edit_root())

    def _load_file_roots(self):
        """Load file roots from database"""
        # Load from database
        file_roots = config_db.get_all_file_roots()

        # Convert to list of dictionaries
        data = []
        for root in file_roots:
            created_str = root.created_at[:10] if root.created_at else ""
            data.append({
                "Path": root.path,
                "Description": root.description,
                "Created": created_str,
                "_id": root.id  # Store ID for selection
            })

        # Load into grid
        columns = ["Path", "Description", "Created"]
        self.data_grid.load_data(data, columns)

        logger.info(f"Loaded {len(file_roots)} file roots")

    def _add_root(self):
        """Add new file root"""
        dialog = FileRootDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self._load_file_roots()
            messagebox.showinfo("Success", "File root added successfully!")

    def _edit_root(self):
        """Edit selected file root"""
        selection = self.data_grid.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a file root to edit.")
            return

        # Get the row data
        item_values = self.data_grid.tree.item(selection[0], "values")
        if not item_values:
            return

        # Find file root by path (first column)
        root_path = item_values[0]
        file_roots = config_db.get_all_file_roots()
        file_root = None
        for root in file_roots:
            if root.path == root_path:
                file_root = root
                break

        if not file_root:
            return

        dialog = FileRootDialog(self, file_root)
        self.wait_window(dialog)

        if dialog.result:
            self._load_file_roots()
            messagebox.showinfo("Success", "File root updated successfully!")

    def _delete_root(self):
        """Delete selected file root"""
        selection = self.data_grid.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a file root to delete.")
            return

        # Get the row data
        item_values = self.data_grid.tree.item(selection[0], "values")
        if not item_values:
            return

        # Find file root by path (first column)
        root_path = item_values[0]
        file_roots = config_db.get_all_file_roots()
        file_root = None
        for root in file_roots:
            if root.path == root_path:
                file_root = root
                break

        if not file_root:
            return

        # Confirm deletion
        response = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this file root?\n\n{file_root.path}",
            icon='warning'
        )

        if response:
            if config_db.delete_file_root(file_root.id):
                self._load_file_roots()
                logger.important(f"Deleted file root: {file_root.path}")
                messagebox.showinfo("Success", "File root deleted successfully!")
            else:
                messagebox.showerror("Error", "Failed to delete file root.")


def show_file_root_manager(parent):
    """Show file root manager in a new window"""
    window = tk.Toplevel(parent)
    window.title("File Root Manager")
    window.geometry("800x500")

    manager = FileRootManager(window)
    manager.pack(fill=tk.BOTH, expand=True)

    # Center on parent
    window.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - window.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - window.winfo_height()) // 2
    window.geometry(f"+{x}+{y}")

    return window
