"""
Scripts Manager Module - Manage and execute scripts
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Optional
from ..utils.logger import logger
from .base_view_frame import BaseViewFrame
from .custom_treeview_panel import CustomTreeViewPanel
from .custom_log_panel import CustomLogPanel


class ScriptsManager(BaseViewFrame):
    """Scripts Manager GUI - Manage and execute scripts"""

    def __init__(self, parent):
        # Define toolbar buttons
        toolbar_buttons = [
            ("▶️ Run Script", self._run_script),
            ("✏️ Edit Script", self._edit_script),
            ("🗑️ Clear Log", self._clear_log),
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
            bottom_weight=2
        )

        self.scripts_tree = None
        self.selected_script = None
        self.selected_script_id = None
        self.log_text = None
        self.jobs_list = None

        # Create content for each panel
        self._create_left_content()
        self._create_top_content()
        self._create_bottom_content()

        # Load scripts
        self._load_scripts()

    def _create_left_content(self):
        """Create scripts list in left panel"""
        # Use CustomTreeViewPanel for standardized tree with events
        tree_panel = CustomTreeViewPanel(
            self.left_frame,
            title="Available Scripts",
            on_select=self._on_script_select,
            on_double_click=self._on_script_double_click,
            on_right_click=self._on_script_right_click
        )
        tree_panel.pack(fill=tk.BOTH, expand=True)

        # Keep reference to the internal tree
        self.scripts_tree = tree_panel.tree

    def _create_top_content(self):
        """Create jobs list in top panel"""
        # Use helper method for standardized title
        title = self.create_panel_title(self.top_frame, "Jobs Using This Script")
        title.pack_configure(pady=(5, 2), anchor=tk.W, padx=10)

        # Jobs listbox
        jobs_frame = ttk.Frame(self.top_frame, padding="5")
        jobs_frame.pack(fill=tk.BOTH, expand=True)

        jobs_scroll = ttk.Scrollbar(jobs_frame)
        jobs_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.jobs_list = tk.Listbox(
            jobs_frame,
            yscrollcommand=jobs_scroll.set,
            font=("Arial", 9),
            bg="#f0f0f0"
        )
        self.jobs_list.pack(fill=tk.BOTH, expand=True)
        jobs_scroll.config(command=self.jobs_list.yview)

        # Placeholder message
        self.jobs_list.insert(tk.END, "No jobs configured yet")
        self.jobs_list.config(state=tk.DISABLED)

    def _create_bottom_content(self):
        """Create execution log in bottom panel"""
        # Use CustomLogPanel for standardized logging
        self.log_panel = CustomLogPanel(
            self.bottom_frame,
            title="Execution Log",
            initial_message="Ready to execute scripts..."
        )
        self.log_panel.pack(fill=tk.BOTH, expand=True)

    def _load_scripts(self):
        """Load all available scripts into tree"""
        from ..database.config_db import config_db

        # Clear tree
        for item in self.scripts_tree.get_children():
            self.scripts_tree.delete(item)

        # Load scripts from database
        scripts = config_db.get_all_scripts()

        for script in scripts:
            icon = "📜"
            self.scripts_tree.insert(
                "", "end",
                text=f"{icon} {script.name}",
                values=(script.id, script.name, script.description, script.script_type),
                tags=("script",)
            )

        logger.info(f"Loaded {len(scripts)} scripts")

    def _on_script_select(self, event):
        """Handle script selection"""
        selection = self.scripts_tree.selection()
        if not selection:
            return

        item_values = self.scripts_tree.item(selection[0], "values")
        if not item_values or len(item_values) < 2:
            self.selected_script = None
            self.selected_script_id = None
            return

        # values = (script_id, script_name, description, script_type)
        script_id = item_values[0]
        script_name = item_values[1]
        self.selected_script = script_name
        self.selected_script_id = script_id
        logger.info(f"Selected script: {script_name} (id: {script_id})")

    def _on_script_double_click(self, event):
        """Handle double-click on script - run it"""
        self._run_script()

    def _run_script(self):
        """Run selected script"""
        if not self.selected_script:
            messagebox.showwarning("No Selection", "Please select a script to run.")
            return

        # Show parameters dialog
        params = self._show_parameters_dialog()
        if params is None:  # User cancelled
            return

        self.log_panel.log_message(f"\n{'='*60}")
        self.log_panel.log_message(f"Running script: {self.selected_script}")
        self.log_panel.log_message(f"{'='*60}\n")

        try:
            if self.selected_script == "Dispatch Files":
                self._run_dispatch_files(params)
            elif self.selected_script == "Load to Database":
                self._run_load_to_database(params)
            else:
                self.log_panel.log_message(f"ERROR: Unknown script '{self.selected_script}'", "error")

        except Exception as e:
            self.log_panel.log_message(f"ERROR: {str(e)}", "error")
            logger.error(f"Error running script {self.selected_script}: {e}")

    def _show_parameters_dialog(self):
        """Show parameters configuration dialog based on selected script"""
        from ..database.config_db import config_db
        from ..database.connections_config import connections_manager

        dialog = tk.Toplevel(self)
        dialog.title(f"Configure {self.selected_script}")
        dialog.geometry("500x300")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        result = {}

        # Title
        ttk.Label(
            dialog,
            text=f"Configure parameters for: {self.selected_script}",
            font=("Arial", 11, "bold")
        ).pack(pady=10, padx=10)

        # Parameters frame
        params_frame = ttk.Frame(dialog, padding="10")
        params_frame.pack(fill=tk.BOTH, expand=True)

        if self.selected_script == "Dispatch Files":
            # RootFolder selection
            ttk.Label(params_frame, text="Select RootFolder:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)

            rootfolders = config_db.get_all_file_roots()
            if not rootfolders:
                messagebox.showerror("Error", "No RootFolders configured. Please add a RootFolder first.")
                dialog.destroy()
                return None

            rootfolder_var = tk.StringVar()
            rootfolder_combo = ttk.Combobox(
                params_frame,
                textvariable=rootfolder_var,
                state='readonly',
                width=50
            )
            rootfolder_combo['values'] = [f"{rf.path} - {rf.description}" for rf in rootfolders]
            rootfolder_combo.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
            if rootfolders:
                rootfolder_combo.current(0)

            result['rootfolder_combo'] = rootfolder_combo
            result['rootfolders'] = rootfolders

        elif self.selected_script == "Load to Database":
            # RootFolder selection
            ttk.Label(params_frame, text="Select RootFolder:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)

            rootfolders = config_db.get_all_file_roots()
            if not rootfolders:
                messagebox.showerror("Error", "No RootFolders configured. Please add a RootFolder first.")
                dialog.destroy()
                return None

            rootfolder_var = tk.StringVar()
            rootfolder_combo = ttk.Combobox(
                params_frame,
                textvariable=rootfolder_var,
                state='readonly',
                width=50
            )
            rootfolder_combo['values'] = [f"{rf.path} - {rf.description}" for rf in rootfolders]
            rootfolder_combo.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
            if rootfolders:
                rootfolder_combo.current(0)

            # Database selection
            ttk.Label(params_frame, text="Select Database:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)

            databases = connections_manager.get_all_connections()
            if not databases:
                messagebox.showerror("Error", "No database connections configured. Please add a database first.")
                dialog.destroy()
                return None

            database_var = tk.StringVar()
            database_combo = ttk.Combobox(
                params_frame,
                textvariable=database_var,
                state='readonly',
                width=50
            )
            database_combo['values'] = [f"{db.name} ({db.db_type})" for db in databases]
            database_combo.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=5)
            if databases:
                database_combo.current(0)

            result['rootfolder_combo'] = rootfolder_combo
            result['rootfolders'] = rootfolders
            result['database_combo'] = database_combo
            result['databases'] = databases

        params_frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        def on_ok():
            # Capture selected indices BEFORE destroying dialog
            if 'rootfolder_combo' in result:
                result['rootfolder_idx'] = result['rootfolder_combo'].current()
            if 'database_combo' in result:
                result['database_idx'] = result['database_combo'].current()

            # Remove widget references (they'll be destroyed)
            result.pop('rootfolder_combo', None)
            result.pop('database_combo', None)

            dialog.result = result
            dialog.destroy()

        def on_cancel():
            dialog.result = None
            dialog.destroy()

        ttk.Button(button_frame, text="OK", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)

        # Wait for dialog
        dialog.wait_window()

        return getattr(dialog, 'result', None)

    def _run_dispatch_files(self, params):
        """Run Dispatch Files script"""
        from pathlib import Path
        from ..scripts.file_dispatcher import FileDispatcher

        self.log_panel.log_message("Dispatch Files script started...")

        # Get selected rootfolder
        rootfolder_idx = params['rootfolder_idx']
        rootfolder = params['rootfolders'][rootfolder_idx]

        self.log_panel.log_message(f"RootFolder: {rootfolder.path}")
        self.log_panel.log_message(f"Description: {rootfolder.description}")

        root_path = Path(rootfolder.path)
        if not root_path.exists():
            self.log_panel.log_message(f"ERROR: RootFolder does not exist: {root_path}", "error")
            return

        # Run dispatcher
        dispatcher = FileDispatcher(root_folder=root_path)
        self.log_panel.log_message("Dispatching files...")

        stats = dispatcher.dispatch_files()

        self.log_panel.log_message(f"\nResults:", "success")
        self.log_panel.log_message(f"  Files dispatched: {stats['dispatched']}", "success")
        self.log_panel.log_message(f"  Invalid files: {stats['invalid']}", "warning" if stats['invalid'] > 0 else "info")
        self.log_panel.log_message(f"  Errors: {stats['errors']}", "error" if stats['errors'] > 0 else "info")
        self.log_panel.log_message("\nScript completed.", "success")

    def _run_load_to_database(self, params):
        """Run Load to Database script"""
        from pathlib import Path
        from ..scripts.data_loader import DataLoader
        from ..database.connections_config import connections_manager

        self.log_panel.log_message("Load to Database script started...")

        # Get selected rootfolder
        rootfolder_idx = params['rootfolder_idx']
        rootfolder = params['rootfolders'][rootfolder_idx]

        # Get selected database
        database_idx = params['database_idx']
        database = params['databases'][database_idx]

        self.log_panel.log_message(f"RootFolder: {rootfolder.path}")
        self.log_panel.log_message(f"Database: {database.name} ({database.db_type})")

        root_path = Path(rootfolder.path)
        if not root_path.exists():
            self.log_panel.log_message(f"ERROR: RootFolder does not exist: {root_path}", "error")
            return

        # Get connection string from database object
        connection_string = database.connection_string
        if not connection_string:
            self.log_panel.log_message(f"ERROR: No connection string for database {database.name}", "error")
            return

        # Run loader
        loader = DataLoader(connection_string=connection_string)
        self.log_panel.log_message("Loading files into database...")

        stats = loader.load_all_files(root_folder=root_path)

        self.log_panel.log_message(f"\nResults:", "success")
        self.log_panel.log_message(f"  Files processed: {stats['files_processed']}", "info")
        self.log_panel.log_message(f"  Files imported: {stats['files_imported']}", "success")
        self.log_panel.log_message(f"  Files failed: {stats['files_failed']}", "error" if stats['files_failed'] > 0 else "info")
        self.log_panel.log_message(f"  Tables created: {stats['tables_created']}", "success")
        self.log_panel.log_message(f"  Tables updated: {stats['tables_updated']}", "success")
        self.log_panel.log_message("\nScript completed.", "success")

    def _clear_log(self):
        """Clear execution log"""
        self.log_panel.clear()
        self.log_panel.log_message("Log cleared. Ready to execute scripts...")
        logger.info("Script execution log cleared")

    def _refresh(self):
        """Refresh scripts list"""
        self._load_scripts()
        self.selected_script = None
        self.selected_script_id = None
        logger.info("Scripts list refreshed")

    def _on_script_right_click(self, event):
        """Handle right-click on script"""
        # Select item under cursor
        item = self.scripts_tree.identify_row(event.y)
        if item:
            self.scripts_tree.selection_set(item)
            self._on_script_select(None)  # Update selected_script_id

            # Create popup menu
            popup_menu = tk.Menu(self, tearoff=0)
            popup_menu.add_command(label="✏️ Edit Configuration", command=self._edit_script)
            popup_menu.add_command(label="▶️ Run Script", command=self._run_script)
            popup_menu.add_separator()
            popup_menu.add_command(label="📝 Edit Code (VS Code)", command=self._edit_script_code)

            # Show popup menu
            popup_menu.tk_popup(event.x_root, event.y_root)

    def _edit_script_code(self):
        """Open script code in VS Code with project workspace"""
        import subprocess
        from pathlib import Path
        from ..database.config_db import config_db

        if not self.selected_script_id:
            messagebox.showwarning("No Selection", "Please select a script to edit.")
            return

        # Get script from database
        script = config_db.get_script(self.selected_script_id)
        if not script:
            return

        # Map script_type to Python file
        script_files = {
            "dispatch_files": "src/scripts/file_dispatcher.py",
            "load_to_database": "src/scripts/data_loader.py",
        }

        script_file = script_files.get(script.script_type)
        if not script_file:
            messagebox.showerror("Error", f"Script file not found for type: {script.script_type}")
            return

        # Get full path
        project_root = Path(__file__).parent.parent.parent
        full_path = project_root / script_file

        if not full_path.exists():
            messagebox.showerror("Error", f"Script file does not exist:\n{full_path}")
            return

        # Find the data-forge-studio root folder by walking up from the file
        def find_project_root(file_path: Path) -> Path:
            """Find the data-forge-studio project root by walking up the directory tree"""
            current = file_path.parent if file_path.is_file() else file_path

            while current != current.parent:  # Stop at filesystem root
                if current.name.startswith("data-forge-studio"):
                    return current
                current = current.parent

            # If not found, return the file's direct parent
            return file_path.parent if file_path.is_file() else file_path

        workspace_folder = find_project_root(full_path)

        # Try to open with VS Code
        try:
            # Open the workspace folder with the file already opened
            # Use shell=True on Windows to find 'code' command in PATH
            cmd = f'code --new-window "{workspace_folder}" "{full_path}"'
            subprocess.Popen(cmd, shell=True)
            logger.info(f"Opened VS Code workspace: {workspace_folder}, file: {full_path}")
        except Exception as e:
            # VS Code not found or failed, open folder with default file explorer
            logger.warning(f"VS Code failed: {e}")
            try:
                import os
                # Open the workspace FOLDER, not the file
                os.startfile(str(workspace_folder))
                logger.info(f"Opened folder with default file explorer: {workspace_folder}")

                # Show info popup with file location
                messagebox.showinfo(
                    "Explorateur ouvert",
                    f"Le fichier se trouve dans :\n\n{full_path}"
                )
            except Exception as e2:
                messagebox.showerror("Error", f"Could not open folder:\n{str(e2)}\n\nPath: {workspace_folder}")
                logger.error(f"Error opening folder: {e2}")

    def _edit_script(self):
        """Edit selected script configuration"""
        import json
        from ..database.config_db import config_db

        if not self.selected_script_id:
            messagebox.showwarning("No Selection", "Please select a script to edit.")
            return

        # Get script from database
        script = config_db.get_script(self.selected_script_id)
        if not script:
            messagebox.showerror("Error", f"Script not found: {self.selected_script_id}")
            return

        # Parse parameters schema
        try:
            params_schema = json.loads(script.parameters_schema) if script.parameters_schema else {}
        except json.JSONDecodeError:
            params_schema = {}

        # Create edit dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Script Configuration: {script.name}")
        dialog.geometry("750x550")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Title at top
        ttk.Label(
            dialog,
            text=f"Edit Script Configuration",
            font=("Arial", 12, "bold")
        ).pack(side=tk.TOP, pady=10, padx=10)

        # Buttons at bottom - create BEFORE notebook to reserve space
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 10), padx=10)

        # Notebook for tabs - will expand to fill available space
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # Tab 1: General info
        general_frame = ttk.Frame(notebook, padding="10")
        notebook.add(general_frame, text="General")

        # Name field
        ttk.Label(general_frame, text="Name:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar(value=script.name)
        name_entry = ttk.Entry(general_frame, textvariable=name_var, width=50)
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)

        # Description field
        ttk.Label(general_frame, text="Description:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky=tk.NW, pady=5)
        desc_text = scrolledtext.ScrolledText(general_frame, width=50, height=8, wrap=tk.WORD, font=("Arial", 9))
        desc_text.grid(row=1, column=1, sticky=tk.NSEW, pady=5, padx=5)
        desc_text.insert("1.0", script.description or "")

        # Script type (read-only)
        ttk.Label(general_frame, text="Type:", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(general_frame, text=script.script_type, foreground="gray").grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)

        general_frame.columnconfigure(1, weight=1)
        general_frame.rowconfigure(1, weight=1)

        # Tab 2: Parameters
        params_frame = ttk.Frame(notebook, padding="10")
        notebook.add(params_frame, text="Parameters")

        ttk.Label(params_frame, text="Parameters Schema (JSON format):", font=("Arial", 9, "bold")).pack(pady=5, anchor=tk.W)

        params_text = scrolledtext.ScrolledText(params_frame, width=70, height=15, wrap=tk.WORD, font=("Consolas", 9))
        params_text.pack(fill=tk.BOTH, expand=True, pady=5)
        params_text.insert("1.0", json.dumps(params_schema, indent=2))

        # Help text
        help_text = """Format exemple:
{
  "root_folder": {
    "type": "file_root",
    "required": true,
    "description": "RootFolder containing files"
  },
  "database": {
    "type": "database",
    "required": true,
    "description": "Target database"
  }
}

Types supportés: file_root, database, string, number, boolean"""

        ttk.Label(params_frame, text=help_text, font=("Arial", 8), foreground="gray", justify=tk.LEFT).pack(pady=5, anchor=tk.W)

        # Define save and cancel functions
        def on_save():
            new_name = name_var.get().strip()
            new_description = desc_text.get("1.0", tk.END).strip()
            new_params_json = params_text.get("1.0", tk.END).strip()

            if not new_name:
                messagebox.showerror("Error", "Script name cannot be empty.")
                return

            # Validate and normalize parameters JSON
            try:
                if new_params_json:
                    params_obj = json.loads(new_params_json)
                    if not isinstance(params_obj, dict):
                        messagebox.showerror("Error", "Parameters schema must be a JSON object.")
                        return
                    # Re-serialize to ensure proper formatting
                    new_params_json = json.dumps(params_obj)
                else:
                    # Empty is valid - save as empty JSON object
                    new_params_json = json.dumps({})
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON in parameters schema:\n{str(e)}")
                return

            # Update script
            script.name = new_name
            script.description = new_description
            script.parameters_schema = new_params_json

            if config_db.update_script(script):
                dialog.destroy()
                self._refresh()
            else:
                messagebox.showerror("Error", "Failed to update script.")

        def on_cancel():
            dialog.destroy()

        # Center the buttons
        buttons_inner = ttk.Frame(button_frame)
        buttons_inner.pack()

        ttk.Button(buttons_inner, text="Save", command=on_save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_inner, text="Cancel", command=on_cancel, width=15).pack(side=tk.LEFT, padx=5)

        # Wait for dialog
        dialog.wait_window()
