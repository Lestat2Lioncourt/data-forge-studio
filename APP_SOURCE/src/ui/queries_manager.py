"""
Queries Manager Module - Manage saved queries with TreeView
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from typing import List, Dict, Optional
from ..utils.logger import logger
from ..database.config_db import SavedQuery, config_db
from ..database.connections_config import connections_manager
from .base_view_frame import BaseViewFrame
from .custom_datagridview import CustomDataGridView


class QueriesManager(BaseViewFrame):
    """Queries Manager GUI - Manage saved queries"""

    def __init__(self, parent):
        # Define toolbar buttons
        toolbar_buttons = [
            ("🔄 Refresh", self._load_queries),
            ("▶️ Execute Query", self._execute_query),
            ("✏️ Edit Query", self._edit_query),
            ("🗑️ Delete Query", self._delete_query),
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

        self.queries_tree = None
        self.status_var = None
        self.result_grid = None
        self.result_info_var = None

        # Create content for each panel
        self._create_left_content()
        self._create_top_content()
        self._create_bottom_content()

        # Load queries
        self._load_queries()

    def _create_left_content(self):
        """Create TreeView in left panel"""
        ttk.Label(self.left_frame, text="Queries Tree", font=("Arial", 10, "bold")).pack(pady=5)

        tree_frame = ttk.Frame(self.left_frame)
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

    def _create_top_content(self):
        """Create query details in top panel"""
        # Title at top
        ttk.Label(self.top_frame, text="Query Details", font=("Arial", 11, "bold")).pack(pady=(5, 2), anchor=tk.W, padx=10)

        # Details fields - smaller fonts
        details_frame = ttk.Frame(self.top_frame, padding="5")
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
        self.description_text = scrolledtext.ScrolledText(details_frame, width=50, height=3, wrap=tk.WORD, font=("Arial", 8))
        self.description_text.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=5)
        self.description_text.config(state=tk.DISABLED, bg="#f0f0f0")

        # Query text
        ttk.Label(details_frame, text="Query:", font=("Arial", 8)).grid(row=5, column=0, sticky=tk.NW, pady=2)
        self.query_text = scrolledtext.ScrolledText(details_frame, width=50, height=8, wrap=tk.WORD, font=("Consolas", 9))
        self.query_text.grid(row=5, column=1, sticky=tk.NSEW, pady=2, padx=5)
        self.query_text.config(state=tk.DISABLED, bg="#f0f0f0")

        details_frame.columnconfigure(1, weight=1)
        details_frame.rowconfigure(5, weight=1)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.top_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

    def _create_bottom_content(self):
        """Create results grid in bottom panel"""
        # Result info label
        self.result_info_var = tk.StringVar(value="No query executed yet")
        ttk.Label(
            self.bottom_frame,
            textvariable=self.result_info_var,
            foreground="gray",
            font=("Arial", 9)
        ).pack(pady=5)

        # Use CustomDataGridView for results
        self.result_grid = CustomDataGridView(
            self.bottom_frame,
            show_export=True,
            show_copy=True,
            show_refresh=False
        )
        self.result_grid.pack(fill=tk.BOTH, expand=True)

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

        # Clear results grid
        if self.result_grid:
            self.result_grid.clear()
        if self.result_info_var:
            self.result_info_var.set("No query executed yet")

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

    def _connect_sqlite(self, connection_string: str):
        """Connect to SQLite database"""
        import sqlite3
        from pathlib import Path

        # Parse connection string (format: "Database=path/to/db.sqlite")
        db_path = connection_string.split("=", 1)[1].strip()
        db_file = Path(db_path)

        if not db_file.exists():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")

        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def _execute_query(self):
        """Execute selected query locally and display results"""
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

        # Get database connection
        db_conn = connections_manager.get_connection(query.target_database_id)
        if not db_conn:
            messagebox.showerror("Error", f"Database connection not found: {query.target_database_id}")
            return

        # Create connection
        try:
            if db_conn.db_type == 'sqlite':
                connection = self._connect_sqlite(db_conn.connection_string)
            else:
                import pyodbc
                connection = pyodbc.connect(db_conn.connection_string)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to database:\n{e}")
            logger.error(f"Connection error: {e}")
            return

        # Execute query
        try:
            cursor = connection.cursor()
            cursor.execute(query.query_text)

            if cursor.description:
                # SELECT query - show results
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()

                # Convert rows to list of dictionaries for CustomDataGridView
                data = []
                for row in rows:
                    data.append({col: row[i] for i, col in enumerate(columns)})

                # Load data into grid
                self.result_grid.load_data(data, columns)
                self.result_info_var.set(f"✓ {len(rows)} row(s) returned from {db_conn.name}")
                logger.info(f"Executed saved query '{query.name}': {len(rows)} rows returned")
            else:
                # INSERT/UPDATE/DELETE query
                rows_affected = cursor.rowcount
                self.result_grid.clear()
                self.result_info_var.set(f"✓ Query executed on {db_conn.name}. {rows_affected} row(s) affected")
                logger.important(f"Executed saved query '{query.name}': {rows_affected} rows affected")

            connection.commit()

        except Exception as e:
            self.result_info_var.set(f"✗ Error: {str(e)}")
            messagebox.showerror("Query Error", f"Failed to execute query:\n{e}")
            logger.error(f"Query execution error: {e}")
        finally:
            # Close connection
            if connection:
                connection.close()
