"""
Queries Manager Module - Manage saved queries with TreeView
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from typing import List, Dict, Optional
from ..utils.logger import logger
from ..database.config_db import SavedQuery, config_db
from ..database.connections_config import connections_manager


class QueriesManager(ttk.Frame):
    """Queries Manager GUI - Manage saved queries"""

    def __init__(self, parent):
        super().__init__(parent)
        self._create_widgets()
        self._load_queries()

    def _create_widgets(self):
        """Create main widgets"""
        # Title removed - now using toolbar for navigation

        # Toolbar
        toolbar = ttk.Frame(self, padding="5")
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="Refresh", command=self._load_queries).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Execute Query", command=self._execute_query).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit Query", command=self._edit_query).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete Query", command=self._delete_query).pack(side=tk.LEFT, padx=2)

        # Main container with paned window
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: TreeView (Categories > Queries) - Projects shown as query info
        left_frame = ttk.Frame(main_paned, width=400)
        main_paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Queries Tree", font=("Arial", 10, "bold")).pack(pady=5)

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree_scroll_y = ttk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.queries_tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        self.queries_tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.queries_tree.yview)
        tree_scroll_x.config(command=self.queries_tree.xview)

        self.queries_tree.bind("<<TreeviewSelect>>", self._on_query_select)
        self.queries_tree.bind("<Double-Button-1>", self._on_query_double_click)

        # Right: Query details
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        # Title at top
        ttk.Label(right_frame, text="Query Details", font=("Arial", 11, "bold")).pack(pady=(5, 2), anchor=tk.W, padx=10)

        # Details fields - smaller fonts
        details_frame = ttk.Frame(right_frame, padding="5")
        details_frame.pack(fill=tk.BOTH, expand=True)

        # Projects
        ttk.Label(details_frame, text="Projects:", font=("Arial", 8)).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.project_label = ttk.Label(details_frame, text="", foreground="blue", font=("Arial", 8))
        self.project_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        # Category
        ttk.Label(details_frame, text="Category:", font=("Arial", 8)).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.category_label = ttk.Label(details_frame, text="", foreground="blue", font=("Arial", 8))
        self.category_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)

        # Name
        ttk.Label(details_frame, text="Name:", font=("Arial", 8)).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.name_label = ttk.Label(details_frame, text="", foreground="blue", font=("Arial", 8))
        self.name_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)

        # Database
        ttk.Label(details_frame, text="Database:", font=("Arial", 8)).grid(row=3, column=0, sticky=tk.W, pady=2)
        self.database_label = ttk.Label(details_frame, text="", foreground="green", font=("Arial", 8))
        self.database_label.grid(row=3, column=1, sticky=tk.W, pady=2, padx=5)

        # Description
        ttk.Label(details_frame, text="Description:", font=("Arial", 8)).grid(row=4, column=0, sticky=tk.NW, pady=2)
        self.description_text = scrolledtext.ScrolledText(details_frame, width=50, height=4, wrap=tk.WORD, font=("Arial", 8))
        self.description_text.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=5)
        self.description_text.config(state=tk.DISABLED, bg="#f0f0f0")

        # Query text
        ttk.Label(details_frame, text="Query:", font=("Arial", 8)).grid(row=5, column=0, sticky=tk.NW, pady=2)
        self.query_text = scrolledtext.ScrolledText(details_frame, width=50, height=15, wrap=tk.WORD, font=("Consolas", 9))
        self.query_text.grid(row=5, column=1, sticky=tk.NSEW, pady=2, padx=5)
        self.query_text.config(state=tk.DISABLED, bg="#f0f0f0")

        details_frame.columnconfigure(1, weight=1)
        details_frame.rowconfigure(5, weight=1)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _load_queries(self):
        """Load all saved queries into tree"""
        # Clear tree
        for item in self.queries_tree.get_children():
            self.queries_tree.delete(item)

        # Clear details
        self._clear_details()

        # Get all queries
        all_queries = config_db.get_all_saved_queries()

        if not all_queries:
            self.status_var.set("No saved queries found")
            return

        # Organize by Category > Query
        categories = {}
        for query in all_queries:
            if query.category not in categories:
                categories[query.category] = []
            categories[query.category].append(query)

        # Build tree
        for category_name in sorted(categories.keys()):
            category_node = self.queries_tree.insert(
                "", "end",
                text=f"📂 {category_name}",
                values=("category", category_name),
                open=True
            )

            for query in sorted(categories[category_name], key=lambda q: q.name):
                # Get database name
                db_conn = connections_manager.get_connection(query.target_database_id)
                db_name = db_conn.name if db_conn else "Unknown"

                # Get projects attached to this query
                projects = config_db.get_query_projects(query.id)
                projects_str = ", ".join([p.name for p in projects]) if projects else "No project"

                self.queries_tree.insert(
                    category_node, "end",
                    text=f"🔍 {query.name} [{db_name}] ({projects_str})",
                    values=("query", query.id)
                )

        self.status_var.set(f"Loaded {len(all_queries)} saved queries")
        logger.info(f"Loaded {len(all_queries)} saved queries")

    def _on_query_select(self, event):
        """Handle query selection"""
        selection = self.queries_tree.selection()
        if not selection:
            return

        item_values = self.queries_tree.item(selection[0], "values")
        if not item_values or len(item_values) < 2:
            self._clear_details()
            return

        item_type = item_values[0]

        if item_type == "query":
            query_id = item_values[1]
            self._show_query_details(query_id)
        else:
            self._clear_details()

    def _show_query_details(self, query_id: str):
        """Show details of selected query"""
        # Find query
        all_queries = config_db.get_all_saved_queries()
        query = None
        for q in all_queries:
            if q.id == query_id:
                query = q
                break

        if not query:
            self._clear_details()
            return

        # Get database name
        db_conn = connections_manager.get_connection(query.target_database_id)
        db_name = db_conn.name if db_conn else "Unknown"

        # Get projects attached to this query
        projects = config_db.get_query_projects(query.id)
        projects_str = ", ".join([p.name for p in projects]) if projects else "No project"

        # Update details
        self.project_label.config(text=projects_str)
        self.category_label.config(text=query.category)
        self.name_label.config(text=query.name)
        self.database_label.config(text=db_name)

        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(1.0, query.description if query.description else "No description")
        self.description_text.config(state=tk.DISABLED)

        self.query_text.config(state=tk.NORMAL)
        self.query_text.delete(1.0, tk.END)
        self.query_text.insert(1.0, query.query_text)
        self.query_text.config(state=tk.DISABLED)

    def _clear_details(self):
        """Clear query details"""
        self.project_label.config(text="")
        self.category_label.config(text="")
        self.name_label.config(text="")
        self.database_label.config(text="")

        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete(1.0, tk.END)
        self.description_text.config(state=tk.DISABLED)

        self.query_text.config(state=tk.NORMAL)
        self.query_text.delete(1.0, tk.END)
        self.query_text.config(state=tk.DISABLED)

    def _on_query_double_click(self, event):
        """Handle double-click on query - execute it"""
        self._execute_query()

    def _delete_query(self):
        """Delete selected query"""
        selection = self.queries_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a query to delete.")
            return

        item_values = self.queries_tree.item(selection[0], "values")
        if not item_values or len(item_values) < 2 or item_values[0] != "query":
            messagebox.showwarning("Invalid Selection", "Please select a query (not a category).")
            return

        query_id = item_values[1]

        # Find query
        all_queries = config_db.get_all_saved_queries()
        query = None
        for q in all_queries:
            if q.id == query_id:
                query = q
                break

        if not query:
            messagebox.showerror("Error", "Query not found.")
            return

        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this query?\n\nCategory: {query.category}\nName: {query.name}"
        )

        if result:
            if config_db.delete_saved_query(query_id):
                logger.important(f"Deleted query: {query.category}/{query.name}")
                self._load_queries()
            else:
                messagebox.showerror("Error", "Failed to delete query.")

    def _edit_query(self):
        """Edit selected query - load it in Query Manager for editing"""
        selection = self.queries_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a query to edit.")
            return

        item_values = self.queries_tree.item(selection[0], "values")
        if not item_values or len(item_values) < 2 or item_values[0] != "query":
            messagebox.showwarning("Invalid Selection", "Please select a query (not a category).")
            return

        query_id = item_values[1]

        # Find query
        all_queries = config_db.get_all_saved_queries()
        query = None
        for q in all_queries:
            if q.id == query_id:
                query = q
                break

        if not query:
            messagebox.showerror("Error", "Query not found.")
            return

        # Switch to Query Manager and load the query for editing
        # Access GUI via stored reference: self.master.gui = DataLakeLoaderGUI
        gui = getattr(self.master, 'gui', None)
        if gui and hasattr(gui, '_show_database_frame_with_query'):
            gui._show_database_frame_with_query(query, execute=False)
            logger.info(f"Loaded query for editing: {query.category}/{query.name}")
        else:
            messagebox.showerror("Error", "Could not access Query Manager. Please open it manually from Database menu.")

    def _execute_query(self):
        """Execute selected query - load it in Query Manager and run it"""
        selection = self.queries_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a query to execute.")
            return

        item_values = self.queries_tree.item(selection[0], "values")
        if not item_values or len(item_values) < 2 or item_values[0] != "query":
            messagebox.showwarning("Invalid Selection", "Please select a query (not a category).")
            return

        query_id = item_values[1]

        # Find query
        all_queries = config_db.get_all_saved_queries()
        query = None
        for q in all_queries:
            if q.id == query_id:
                query = q
                break

        if not query:
            messagebox.showerror("Error", "Query not found.")
            return

        # Switch to Query Manager, load the query, and execute it
        # Access GUI via stored reference: self.master.gui = DataLakeLoaderGUI
        gui = getattr(self.master, 'gui', None)
        if gui and hasattr(gui, '_show_database_frame_with_query'):
            gui._show_database_frame_with_query(query, execute=True)
            logger.info(f"Executed query: {query.category}/{query.name}")
        else:
            messagebox.showerror("Error", "Could not access Query Manager. Please open it manually from Database menu.")

    def _load_in_query_manager(self):
        """Load selected query in Query Manager"""
        selection = self.queries_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a query to load.")
            return

        item_values = self.queries_tree.item(selection[0], "values")
        if not item_values or len(item_values) < 2 or item_values[0] != "query":
            messagebox.showwarning("Invalid Selection", "Please select a query (not a category).")
            return

        query_id = item_values[1]

        # Find query
        all_queries = config_db.get_all_saved_queries()
        query = None
        for q in all_queries:
            if q.id == query_id:
                query = q
                break

        if not query:
            messagebox.showerror("Error", "Query not found.")
            return

        # Switch to Query Manager and load the query
        # Access GUI via stored reference: self.master.gui = DataLakeLoaderGUI
        gui = getattr(self.master, 'gui', None)
        if gui and hasattr(gui, '_show_database_frame_with_query'):
            gui._show_database_frame_with_query(query)
            logger.info(f"Loaded query in Query Manager: {query.category}/{query.name}")
        else:
            messagebox.showerror("Error", "Could not access Query Manager. Please open it manually from Database menu.")
