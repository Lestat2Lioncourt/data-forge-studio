"""
Jobs Manager Module - Manage and execute jobs
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Optional
from ..utils.logger import logger
from .base_view_frame import BaseViewFrame
from .custom_treeview_panel import CustomTreeViewPanel
from .custom_log_panel import CustomLogPanel


class JobsManager(BaseViewFrame):
    """Jobs Manager GUI - Manage and execute jobs"""

    def __init__(self, parent):
        # Define toolbar buttons
        toolbar_buttons = [
            ("➕ New Job", self._create_job),
            ("✏️ Edit Job", self._edit_job),
            ("▶️ Run Job", self._run_job),
            ("🗑️ Delete Job", self._delete_job),
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

        self.jobs_tree = None
        self.selected_job_id = None
        self.log_text = None
        self.job_details_frame = None

        # Create content for each panel
        self._create_left_content()
        self._create_top_content()
        self._create_bottom_content()

        # Load jobs
        self._load_jobs()

    def _create_left_content(self):
        """Create jobs list in left panel"""
        # Load projects for filter first
        from ..database.config_db import config_db
        projects = config_db.get_all_projects()
        project_names = ["All Projects"] + [p.name for p in projects]

        # Use CustomTreeViewPanel with filter
        tree_panel = CustomTreeViewPanel(
            self.left_frame,
            title="Jobs",
            show_filter=True,
            filter_label="Project:",
            filter_values=project_names,
            filter_default_index=0,
            on_filter_change=lambda e: self._load_jobs(),
            on_select=self._on_job_select,
            on_double_click=self._on_job_double_click
        )
        tree_panel.pack(fill=tk.BOTH, expand=True)

        # Keep references
        self.jobs_tree = tree_panel.tree
        self.project_filter = tree_panel.filter_combobox

    def _create_top_content(self):
        """Create job details in top panel"""
        # Use helper method for standardized title
        title = self.create_panel_title(self.top_frame, "Job Details")
        title.pack_configure(pady=(5, 2), anchor=tk.W, padx=10)

        # Details frame
        self.job_details_frame = ttk.Frame(self.top_frame, padding="5")
        self.job_details_frame.pack(fill=tk.BOTH, expand=True)

        # Placeholder
        ttk.Label(self.job_details_frame, text="Select a job to view details", foreground="gray").pack(pady=20)

    def _create_bottom_content(self):
        """Create execution log in bottom panel"""
        # Use CustomLogPanel for standardized logging
        self.log_panel = CustomLogPanel(
            self.bottom_frame,
            title="Execution Log",
            initial_message="Ready to execute jobs..."
        )
        self.log_panel.pack(fill=tk.BOTH, expand=True)


    def _load_jobs(self):
        """Load all jobs into tree"""
        from ..database.config_db import config_db

        # Clear tree
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)

        # Get filter
        filter_value = self.project_filter.get()

        if filter_value == "All Projects":
            jobs = config_db.get_all_jobs()
        else:
            # Find project by name
            projects = config_db.get_all_projects()
            project = next((p for p in projects if p.name == filter_value), None)
            if project:
                jobs = config_db.get_project_jobs(project.id)
            else:
                jobs = []

        # Group by project and hierarchy
        for job in jobs:
            if job.parent_job_id is None:  # Root level jobs only
                self._add_job_node("", job)

        logger.info(f"Loaded {len(jobs)} jobs")

    def _add_job_node(self, parent, job):
        """Add job node to tree"""
        from ..database.config_db import config_db

        # Icon based on job type
        icon = "📦" if job.job_type == "workflow" else "⚙️"
        enabled_icon = "✅" if job.enabled else "❌"

        # Get project and script names
        project_name = "No Project"
        if job.project_id:
            project = config_db.get_project(job.project_id)
            project_name = project.name if project else "Unknown"

        script_name = ""
        if job.script_id:
            script = config_db.get_script(job.script_id)
            script_name = script.name if script else "Unknown"

        text = f"{icon} {job.name} {enabled_icon}"
        if script_name:
            text += f" [{script_name}]"
        text += f" ({project_name})"

        node = self.jobs_tree.insert(
            parent, "end",
            text=text,
            values=(job.id, job.name, job.job_type, job.enabled),
            tags=("job",)
        )

        # Add children if workflow
        if job.job_type == "workflow":
            children = config_db.get_job_children(job.id)
            for child in children:
                self._add_job_node(node, child)

    def _on_job_select(self, event):
        """Handle job selection"""
        selection = self.jobs_tree.selection()
        if not selection:
            return

        item_values = self.jobs_tree.item(selection[0], "values")
        if not item_values or len(item_values) < 1:
            self.selected_job_id = None
            return

        # values = (job_id, job_name, job_type, enabled)
        self.selected_job_id = item_values[0]
        logger.info(f"Selected job: {item_values[1]} (id: {self.selected_job_id})")

        self._display_job_details()

    def _display_job_details(self):
        """Display details of selected job"""
        from ..database.config_db import config_db
        import json

        if not self.selected_job_id:
            return

        job = config_db.get_job(self.selected_job_id)
        if not job:
            return

        # Clear details frame
        for widget in self.job_details_frame.winfo_children():
            widget.destroy()

        # Create details
        details_text = scrolledtext.ScrolledText(
            self.job_details_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            height=10
        )
        details_text.pack(fill=tk.BOTH, expand=True)

        # Build details text
        details = f"""Job: {job.name}
Type: {job.job_type}
Enabled: {'Yes' if job.enabled else 'No'}
Description: {job.description or 'N/A'}

"""

        if job.script_id:
            script = config_db.get_script(job.script_id)
            details += f"Script: {script.name if script else 'Unknown'}\n\n"

        if job.parameters:
            try:
                params = json.loads(job.parameters)
                details += "Parameters:\n"
                details += json.dumps(params, indent=2)
            except:
                details += f"Parameters: {job.parameters}"
        else:
            details += "Parameters: None"

        details_text.insert("1.0", details)
        details_text.config(state=tk.DISABLED)

    def _on_job_double_click(self, event):
        """Handle double-click on job - edit it"""
        self._edit_job()

    def _create_job(self):
        """Create a new job"""
        self._show_job_dialog()

    def _edit_job(self):
        """Edit selected job"""
        if not self.selected_job_id:
            messagebox.showwarning("No Selection", "Please select a job to edit.")
            return

        self._show_job_dialog(job_id=self.selected_job_id)

    def _sort_jobs_by_dependency(self, jobs):
        """
        Sort jobs by their dependency order using topological sort.
        Jobs with previous_job_id must run after their dependencies.

        Args:
            jobs: List of Job objects to sort

        Returns:
            List of Job objects in execution order

        Raises:
            ValueError: If circular dependency detected
        """
        # Build dependency graph
        job_map = {job.id: job for job in jobs}
        result = []
        visited = set()
        visiting = set()  # For cycle detection

        def visit(job_id):
            """DFS visit for topological sort"""
            if job_id in visited:
                return
            if job_id in visiting:
                # Circular dependency detected
                raise ValueError(f"Circular dependency detected involving job ID: {job_id[:8]}...")

            visiting.add(job_id)

            job = job_map.get(job_id)
            if job:
                # Visit dependency first (if it exists and is in our job list)
                if job.previous_job_id and job.previous_job_id in job_map:
                    visit(job.previous_job_id)

                visiting.remove(job_id)
                visited.add(job_id)
                result.append(job)

        # Visit all jobs
        for job in jobs:
            if job.id not in visited:
                visit(job.id)

        return result

    def _run_job(self):
        """Run selected job"""
        from ..database.config_db import config_db
        import json

        if not self.selected_job_id:
            messagebox.showwarning("No Selection", "Please select a job to run.")
            return

        job = config_db.get_job(self.selected_job_id)
        if not job:
            messagebox.showerror("Error", "Job not found.")
            return

        if not job.enabled:
            result = messagebox.askyesno(
                "Job Disabled",
                f"Job '{job.name}' is currently disabled. Do you want to run it anyway?"
            )
            if not result:
                return

        # Handle workflow jobs
        if job.job_type == "workflow":
            self.log_panel.log_message(f"\n{'='*60}")
            self.log_panel.log_message(f"Running workflow: {job.name}")
            self.log_panel.log_message(f"{'='*60}\n")

            # Get child jobs
            children = config_db.get_job_children(job.id)
            enabled_children = [c for c in children if c.enabled]

            if not enabled_children:
                self.log_panel.log_message("WARNING: No enabled jobs in workflow.", "warning")
                return

            # Sort jobs by dependency order (respecting previous_job_id)
            try:
                sorted_children = self._sort_jobs_by_dependency(enabled_children)
            except ValueError as e:
                self.log_panel.log_message(f"ERROR: {str(e)}", "error")
                return

            self.log_panel.log_message(f"Workflow has {len(sorted_children)} enabled job(s):")
            self.log_panel.log_message(f"Execution order (respecting dependencies):")
            for idx, child in enumerate(sorted_children, 1):
                dep_info = ""
                if child.previous_job_id:
                    prev_job = next((j for j in enabled_children if j.id == child.previous_job_id), None)
                    if prev_job:
                        dep_info = f" (after {prev_job.name})"
                self.log_panel.log_message(f"  {idx}. {child.name}{dep_info}")

            self.log_panel.log_message("")

            # Run each child job in dependency order
            for child in sorted_children:
                self.log_panel.log_message(f"\n--- Running child job: {child.name} ---", "info")
                self._execute_script_job(child)

            self.log_panel.log_message(f"\n{'='*60}")
            self.log_panel.log_message(f"Workflow '{job.name}' completed.", "success")
            self.log_panel.log_message(f"{'='*60}\n")

        # Handle script jobs
        elif job.job_type == "script":
            self.log_panel.log_message(f"\n{'='*60}")
            self.log_panel.log_message(f"Running job: {job.name}")
            self.log_panel.log_message(f"{'='*60}\n")

            self._execute_script_job(job)

            self.log_panel.log_message(f"\n{'='*60}")
            self.log_panel.log_message(f"Job '{job.name}' completed.", "success")
            self.log_panel.log_message(f"{'='*60}\n")

        # Update last run timestamp
        config_db.update_job_last_run(job.id)

    def _execute_script_job(self, job):
        """
        Execute a script job

        Args:
            job: Job object (must be script type)
        """
        from ..database.config_db import config_db
        import json

        if job.job_type != "script":
            self.log_panel.log_message(f"ERROR: Job '{job.name}' is not a script job.", "error")
            return

        if not job.script_id:
            self.log_panel.log_message(f"ERROR: Job '{job.name}' has no script assigned.", "error")
            return

        # Get script
        script = config_db.get_script(job.script_id)
        if not script:
            self.log_panel.log_message(f"ERROR: Script not found for job '{job.name}'.", "error")
            return

        self.log_panel.log_message(f"Script: {script.name}")
        self.log_panel.log_message(f"Type: {script.script_type}")

        # Parse parameters
        try:
            params = json.loads(job.parameters) if job.parameters else {}
            self.log_panel.log_message(f"Parameters: {json.dumps(params, indent=2)}")
        except json.JSONDecodeError as e:
            self.log_panel.log_message(f"ERROR: Invalid parameters JSON: {str(e)}", "error")
            return

        # Execute based on script type
        try:
            if script.script_type == "dispatch_files":
                self._run_dispatch_files_job(params)
            elif script.script_type == "load_to_database":
                self._run_load_to_database_job(params)
            elif script.script_type == "custom":
                self.log_panel.log_message(f"ERROR: Custom script execution not yet implemented.", "error")
            else:
                self.log_panel.log_message(f"ERROR: Unknown script type '{script.script_type}'.", "error")

        except Exception as e:
            self.log_panel.log_message(f"ERROR: {str(e)}", "error")
            logger.error(f"Error executing job {job.name}: {e}")

    def _run_dispatch_files_job(self, params):
        """Run Dispatch Files script with job parameters"""
        from pathlib import Path
        from ..scripts.file_dispatcher import FileDispatcher
        from ..database.config_db import config_db

        self.log_panel.log_message("Dispatch Files script started...")

        # Get rootfolder by ID
        rootfolder_id = params.get('rootfolder_id')
        if not rootfolder_id:
            self.log_panel.log_message("ERROR: rootfolder_id not found in parameters.", "error")
            return

        rootfolder = config_db.get_file_root(rootfolder_id)
        if not rootfolder:
            self.log_panel.log_message(f"ERROR: RootFolder not found: {rootfolder_id}", "error")
            return

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

    def _run_load_to_database_job(self, params):
        """Run Load to Database script with job parameters"""
        from pathlib import Path
        from ..scripts.data_loader import DataLoader
        from ..database.connections_config import connections_manager
        from ..database.config_db import config_db

        self.log_panel.log_message("Load to Database script started...")

        # Get rootfolder by ID
        rootfolder_id = params.get('rootfolder_id')
        if not rootfolder_id:
            self.log_panel.log_message("ERROR: rootfolder_id not found in parameters.", "error")
            return

        rootfolder = config_db.get_file_root(rootfolder_id)
        if not rootfolder:
            self.log_panel.log_message(f"ERROR: RootFolder not found: {rootfolder_id}", "error")
            return

        # Get database connection by ID
        database_id = params.get('database_id')
        if not database_id:
            self.log_panel.log_message("ERROR: database_id not found in parameters.", "error")
            return

        db_conn = config_db.get_database_connection(database_id)
        if not db_conn:
            self.log_panel.log_message(f"ERROR: Database connection not found: {database_id}", "error")
            return

        self.log_panel.log_message(f"RootFolder: {rootfolder.path}")
        self.log_panel.log_message(f"Database: {db_conn.name}")

        root_path = Path(rootfolder.path)
        if not root_path.exists():
            self.log_panel.log_message(f"ERROR: RootFolder does not exist: {root_path}", "error")
            return

        # Get connection string
        conn_string = connections_manager.get_connection_string(db_conn.id)
        if not conn_string:
            self.log_panel.log_message(f"ERROR: Connection string not found for database '{db_conn.name}'", "error")
            return

        # Run loader
        loader = DataLoader(
            root_folder=root_path,
            connection_string=conn_string,
            db_type=db_conn.db_type
        )
        self.log_panel.log_message("Loading files to database...")

        stats = loader.load_all_files()

        self.log_panel.log_message(f"\nResults:", "success")
        self.log_panel.log_message(f"  Files processed: {stats['processed']}", "success")
        self.log_panel.log_message(f"  Rows loaded: {stats['rows_loaded']}", "success")
        self.log_panel.log_message(f"  Errors: {stats['errors']}", "error" if stats['errors'] > 0 else "info")
        self.log_panel.log_message("\nScript completed.", "success")

    def _delete_job(self):
        """Delete selected job"""
        from ..database.config_db import config_db

        if not self.selected_job_id:
            messagebox.showwarning("No Selection", "Please select a job to delete.")
            return

        job = config_db.get_job(self.selected_job_id)
        if not job:
            return

        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete job '{job.name}'?\n\nThis action cannot be undone."
        )

        if result:
            if config_db.delete_job(self.selected_job_id):
                messagebox.showinfo("Success", f"Job '{job.name}' deleted successfully.")
                self.selected_job_id = None
                self._refresh()
            else:
                messagebox.showerror("Error", "Failed to delete job.")

    def _clear_log(self):
        """Clear execution log"""
        self.log_panel.clear()
        self.log_panel.log_message("Log cleared. Ready to execute jobs...")
        logger.info("Job execution log cleared")

    def _refresh(self):
        """Refresh jobs list"""
        self._load_jobs()
        self.selected_job_id = None
        logger.info("Jobs list refreshed")

    def _show_job_dialog(self, job_id: str = None):
        """
        Show job create/edit dialog

        Args:
            job_id: If provided, edit existing job. If None, create new job.
        """
        from ..database.config_db import config_db, Job
        import json

        is_edit = job_id is not None
        job = config_db.get_job(job_id) if is_edit else None

        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"{'Edit' if is_edit else 'Create'} Job")
        dialog.geometry("800x600")
        dialog.transient(self)
        dialog.grab_set()

        # Title
        ttk.Label(
            dialog,
            text=f"{'Edit' if is_edit else 'Create'} Job",
            font=("Arial", 12, "bold")
        ).pack(side=tk.TOP, pady=10, padx=10)

        # Button frame at bottom - create BEFORE notebook
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 10), padx=10)

        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

        # Main content in notebook
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # === General Tab ===
        general_tab = ttk.Frame(notebook, padding="10")
        notebook.add(general_tab, text="General")

        # Project selection (optional)
        row = 0
        ttk.Label(general_tab, text="Project (Optional):").grid(row=row, column=0, sticky=tk.W, pady=5)
        project_var = tk.StringVar()
        project_combo = ttk.Combobox(general_tab, textvariable=project_var, state='readonly', width=40)
        project_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))

        # Load projects with "No Project" option
        projects = config_db.get_all_projects()
        project_names = ["(No Project)"] + [p.name for p in projects]
        project_combo['values'] = project_names
        if is_edit and job:
            if job.project_id:
                project = config_db.get_project(job.project_id)
                if project:
                    project_combo.set(project.name)
                else:
                    project_combo.set("(No Project)")
            else:
                project_combo.set("(No Project)")
        else:
            project_combo.set("(No Project)")

        # Job name
        row += 1
        ttk.Label(general_tab, text="Job Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar(value=job.name if is_edit and job else "")
        name_entry = ttk.Entry(general_tab, textvariable=name_var, width=42)
        name_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))

        # Job type
        row += 1
        ttk.Label(general_tab, text="Job Type:").grid(row=row, column=0, sticky=tk.W, pady=5)
        job_type_var = tk.StringVar(value=job.job_type if is_edit and job else "script")
        job_type_frame = ttk.Frame(general_tab)
        job_type_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(5, 0))

        ttk.Radiobutton(job_type_frame, text="Script Job", variable=job_type_var, value="script").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(job_type_frame, text="Workflow", variable=job_type_var, value="workflow").pack(side=tk.LEFT)

        # Script selection (only for script jobs)
        row += 1
        script_label = ttk.Label(general_tab, text="Script:")
        script_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        script_var = tk.StringVar()
        script_combo = ttk.Combobox(general_tab, textvariable=script_var, state='readonly', width=40)
        script_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))

        # Load scripts
        scripts = config_db.get_all_scripts()
        script_names = [s.name for s in scripts]
        script_combo['values'] = script_names
        if is_edit and job and job.script_id:
            script = config_db.get_script(job.script_id)
            if script:
                script_combo.set(script.name)
        elif scripts:
            script_combo.current(0)

        # Description
        row += 1
        ttk.Label(general_tab, text="Description:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=5)
        desc_text = scrolledtext.ScrolledText(general_tab, wrap=tk.WORD, height=6, width=40)
        desc_text.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        if is_edit and job:
            desc_text.insert("1.0", job.description or "")

        # Previous Job (Dependency) - Optional
        row += 1
        ttk.Label(general_tab, text="Previous Job (Optional):").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(general_tab, text="Job must complete before this one can run", font=("Arial", 7), foreground="gray").grid(row=row, column=1, sticky=tk.W, pady=(0, 2), padx=(5, 0))
        row += 1
        previous_job_var = tk.StringVar()
        previous_job_combo = ttk.Combobox(general_tab, textvariable=previous_job_var, state='readonly', width=40)
        previous_job_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))

        # Load all jobs for selection (we'll filter sibling jobs later if needed)
        all_jobs = config_db.get_all_jobs()
        job_names = ["(No Dependency)"] + [f"{j.name} ({j.id[:8]})" for j in all_jobs if not is_edit or j.id != (job.id if job else "")]
        previous_job_combo['values'] = job_names
        if is_edit and job and job.previous_job_id:
            prev_job = config_db.get_job(job.previous_job_id)
            if prev_job:
                previous_job_combo.set(f"{prev_job.name} ({prev_job.id[:8]})")
            else:
                previous_job_combo.set("(No Dependency)")
        else:
            previous_job_combo.set("(No Dependency)")

        # Enabled
        row += 1
        enabled_var = tk.BooleanVar(value=job.enabled if is_edit and job else True)
        ttk.Checkbutton(general_tab, text="Enabled", variable=enabled_var).grid(row=row, column=1, sticky=tk.W, pady=5, padx=(5, 0))

        general_tab.columnconfigure(1, weight=1)

        # === Parameters Tab ===
        params_tab = ttk.Frame(notebook, padding="10")
        notebook.add(params_tab, text="Parameters")

        ttk.Label(params_tab, text="Job Parameters (JSON):", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))

        params_text = scrolledtext.ScrolledText(params_tab, wrap=tk.WORD, font=("Consolas", 9), height=20)
        params_text.pack(fill=tk.BOTH, expand=True)

        # Load existing parameters if editing
        if is_edit and job and job.parameters:
            try:
                params_obj = json.loads(job.parameters)
                params_text.insert("1.0", json.dumps(params_obj, indent=2))
            except:
                params_text.insert("1.0", job.parameters)
        else:
            params_text.insert("1.0", "{}")

        # Info label
        info_label = ttk.Label(params_tab, text="", foreground="gray", font=("Arial", 8))
        info_label.pack(anchor=tk.W, pady=(5, 0))

        # Function to update script info and parameter hint
        def on_script_or_type_change(*args):
            job_type = job_type_var.get()

            # Show/hide script selection based on job type
            if job_type == "workflow":
                script_label.grid_remove()
                script_combo.grid_remove()
                info_label.config(text="Workflow jobs contain other jobs and don't have parameters.")
                params_text.config(state=tk.DISABLED)
            else:
                script_label.grid()
                script_combo.grid()
                params_text.config(state=tk.NORMAL)

                # Update info based on selected script
                script_name = script_var.get()
                if script_name:
                    script = next((s for s in scripts if s.name == script_name), None)
                    if script and script.parameters_schema:
                        try:
                            schema = json.loads(script.parameters_schema)
                            if schema:
                                info_label.config(text=f"Required parameters: {', '.join(schema.keys())}")
                            else:
                                info_label.config(text="This script has no required parameters.")
                        except:
                            info_label.config(text="")
                    else:
                        info_label.config(text="This script has no required parameters.")
                else:
                    info_label.config(text="")

        # Bind change events
        job_type_var.trace_add("write", on_script_or_type_change)
        script_var.trace_add("write", on_script_or_type_change)

        # Initial update
        on_script_or_type_change()

        # Save button (defined after all widgets)
        def on_save():
            new_name = name_var.get().strip()
            new_project_name = project_var.get()
            new_job_type = job_type_var.get()
            new_script_name = script_var.get()
            new_description = desc_text.get("1.0", tk.END).strip()
            new_enabled = enabled_var.get()
            new_params_json = params_text.get("1.0", tk.END).strip()
            new_previous_job_selection = previous_job_var.get()

            # Validation
            if not new_name:
                messagebox.showerror("Error", "Job name is required.")
                return

            # Get project ID (optional - can be None)
            project_id = None
            if new_project_name and new_project_name != "(No Project)":
                project = next((p for p in projects if p.name == new_project_name), None)
                if not project:
                    messagebox.showerror("Error", "Selected project not found.")
                    return
                project_id = project.id

            # Get previous job ID (optional - can be None)
            previous_job_id = None
            if new_previous_job_selection and new_previous_job_selection != "(No Dependency)":
                # Extract ID from selection like "Job Name (12345678)"
                import re
                match = re.search(r'\(([a-f0-9]{8})\)$', new_previous_job_selection)
                if match:
                    prev_job_short_id = match.group(1)
                    # Find the full job ID that starts with this short ID
                    prev_job = next((j for j in all_jobs if j.id.startswith(prev_job_short_id)), None)
                    if prev_job:
                        previous_job_id = prev_job.id

            # Get script ID if script job
            script_id = None
            if new_job_type == "script":
                if not new_script_name:
                    messagebox.showerror("Error", "Script is required for script jobs.")
                    return

                script = next((s for s in scripts if s.name == new_script_name), None)
                if not script:
                    messagebox.showerror("Error", "Selected script not found.")
                    return
                script_id = script.id

                # Validate parameters JSON
                try:
                    if new_params_json:
                        params_obj = json.loads(new_params_json)
                        if not isinstance(params_obj, dict):
                            messagebox.showerror("Error", "Parameters must be a JSON object.")
                            return
                        new_params_json = json.dumps(params_obj)
                    else:
                        new_params_json = json.dumps({})
                except json.JSONDecodeError as e:
                    messagebox.showerror("Error", f"Invalid JSON in parameters:\n{str(e)}")
                    return
            else:
                # Workflow jobs don't have parameters
                new_params_json = None

            # Create or update job
            if is_edit:
                job.name = new_name
                job.description = new_description
                job.job_type = new_job_type
                job.script_id = script_id
                job.project_id = project_id
                job.previous_job_id = previous_job_id
                job.parameters = new_params_json
                job.enabled = new_enabled

                if config_db.update_job(job):
                    dialog.destroy()
                    self._refresh()
                else:
                    messagebox.showerror("Error", "Failed to update job.")
            else:
                from datetime import datetime
                new_job = Job(
                    id="",  # Will be generated by __post_init__
                    name=new_name,
                    description=new_description,
                    job_type=new_job_type,
                    script_id=script_id,
                    project_id=project_id,
                    parent_job_id=None,
                    previous_job_id=previous_job_id,
                    parameters=new_params_json,
                    enabled=new_enabled,
                    created_at=None,
                    updated_at=None,
                    last_run_at=None
                )

                if config_db.add_job(new_job):
                    dialog.destroy()
                    self._refresh()
                else:
                    messagebox.showerror("Error", "Failed to create job.")

        ttk.Button(button_frame, text="Save", command=on_save, style='Accent.TButton').pack(side=tk.RIGHT, padx=5)
