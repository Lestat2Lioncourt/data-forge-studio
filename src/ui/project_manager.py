"""
Project Manager Module - Manage projects
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from ..database.config_db import Project, config_db
from ..utils.logger import logger


class ProjectDialog(tk.Toplevel):
    """Dialog for creating/editing projects"""

    def __init__(self, parent, project: Optional[Project] = None):
        super().__init__(parent)
        self.project = project
        self.result = None

        self.title("Edit Project" if project else "New Project")
        self.geometry("500x300")
        self.resizable(False, False)

        # Center the dialog
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

        # Load existing data if editing
        if self.project:
            self._load_project_data()

    def _create_widgets(self):
        """Create dialog widgets"""
        # Main frame
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(main_frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        self.desc_text = tk.Text(main_frame, width=40, height=5, wrap=tk.WORD)
        self.desc_text.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Default checkbox
        self.is_default_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            main_frame,
            text="Set as default project",
            variable=self.is_default_var
        ).grid(row=2, column=1, sticky=tk.W, pady=10, padx=(10, 0))

        # Configure grid
        main_frame.columnconfigure(1, weight=1)

        # Button frame
        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Save", command=self._save).pack(side=tk.RIGHT)

    def _load_project_data(self):
        """Load existing project data"""
        self.name_entry.insert(0, self.project.name)
        self.desc_text.insert("1.0", self.project.description or "")
        self.is_default_var.set(self.project.is_default)

    def _save(self):
        """Save project"""
        name = self.name_entry.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()

        if not name:
            messagebox.showerror("Validation Error", "Project name is required")
            return

        # Create or update project
        if self.project:
            # Update existing project
            self.project.name = name
            self.project.description = description
            self.project.is_default = self.is_default_var.get()
            success = config_db.update_project(self.project)
        else:
            # Create new project
            project = Project(
                id="",
                name=name,
                description=description,
                is_default=self.is_default_var.get()
            )
            success = config_db.add_project(project)
            self.project = project

        if success:
            self.result = self.project
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to save project")

    def show(self) -> Optional[Project]:
        """Show dialog and return result"""
        self.wait_window()
        return self.result


class ProjectManager(ttk.Frame):
    """Project Manager Frame"""

    def __init__(self, parent):
        super().__init__(parent, padding="10")
        self._create_widgets()
        self._load_projects()

    def _create_widgets(self):
        """Create manager widgets"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header_frame,
            text="Project Manager",
            font=("Arial", 12, "bold")
        ).pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side=tk.RIGHT)

        ttk.Button(button_frame, text="➕ New", command=self._new_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="✏️ Edit", command=self._edit_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🗑️ Delete", command=self._delete_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="⭐ Set Default", command=self._set_default).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🔄 Refresh", command=self._load_projects).pack(side=tk.LEFT, padx=2)

        # TreeView
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # TreeView
        columns = ("name", "description", "default", "created")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Configure columns
        self.tree.heading("name", text="Name")
        self.tree.heading("description", text="Description")
        self.tree.heading("default", text="Default")
        self.tree.heading("created", text="Created")

        self.tree.column("name", width=150)
        self.tree.column("description", width=300)
        self.tree.column("default", width=80, anchor=tk.CENTER)
        self.tree.column("created", width=150)

        # Double-click to edit
        self.tree.bind("<Double-Button-1>", lambda e: self._edit_project())

        # Status
        self.status_label = ttk.Label(self, text="", foreground="gray")
        self.status_label.pack(fill=tk.X, pady=(5, 0))

    def _load_projects(self):
        """Load projects into tree"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load projects
        projects = config_db.get_all_projects(sort_by_usage=False)

        for project in projects:
            values = (
                project.name,
                project.description or "",
                "✓" if project.is_default else "",
                project.created_at[:10] if project.created_at else ""
            )
            self.tree.insert("", tk.END, values=values, tags=(project.id,))

        self.status_label.config(text=f"Total projects: {len(projects)}")
        logger.info(f"Loaded {len(projects)} projects")

    def _get_selected_project(self) -> Optional[Project]:
        """Get selected project"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a project")
            return None

        project_id = self.tree.item(selection[0], "tags")[0]
        return config_db.get_project(project_id)

    def _new_project(self):
        """Create new project"""
        dialog = ProjectDialog(self.winfo_toplevel())
        result = dialog.show()

        if result:
            self._load_projects()
            logger.important(f"Created project: {result.name}")

    def _edit_project(self):
        """Edit selected project"""
        project = self._get_selected_project()
        if not project:
            return

        dialog = ProjectDialog(self.winfo_toplevel(), project)
        result = dialog.show()

        if result:
            self._load_projects()
            logger.important(f"Updated project: {result.name}")

    def _delete_project(self):
        """Delete selected project"""
        project = self._get_selected_project()
        if not project:
            return

        # Confirm
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Delete project '{project.name}'?\n\nThis will remove all associations (databases, file roots, queries).",
            icon='warning'
        )

        if response:
            success = config_db.delete_project(project.id)
            if success:
                self._load_projects()
                logger.important(f"Deleted project: {project.name}")
            else:
                messagebox.showerror("Error", "Failed to delete project")

    def _set_default(self):
        """Set selected project as default"""
        project = self._get_selected_project()
        if not project:
            return

        success = config_db.set_default_project(project.id)
        if success:
            self._load_projects()
            logger.important(f"Set default project: {project.name}")
        else:
            messagebox.showerror("Error", "Failed to set default project")


def show_project_manager(parent):
    """Show project manager window"""
    window = tk.Toplevel(parent)
    window.title("Project Manager")
    window.geometry("800x500")

    manager = ProjectManager(window)
    manager.pack(fill=tk.BOTH, expand=True)

    # Center the window
    window.transient(parent)
    window.grab_set()
