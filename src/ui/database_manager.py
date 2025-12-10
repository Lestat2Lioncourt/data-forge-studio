"""
Database Manager Module - Multi-tab query manager for multiple databases
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import pyodbc
import sqlite3
import re
import threading
from typing import List, Dict, Optional, Union
from pathlib import Path
from ..utils.logger import logger
from ..database.config_db import DatabaseConnection, SavedQuery, config_db
from ..database.connections_config import connections_manager, ConnectionsManager
from ..utils.sql_highlighter import SQLHighlighter, format_sql, SQL_FORMAT_STYLES
from ..config.user_preferences import get_preferences
from .connection_dialog import ConnectionDialog
from .custom_datagridview import CustomDataGridView


class QueryTab:
    """Single query tab"""

    def __init__(self, parent_notebook, tab_name: str, connection: Union[pyodbc.Connection, sqlite3.Connection], db_connection: DatabaseConnection):
        self.parent_notebook = parent_notebook
        self.tab_name = tab_name
        self.connection = connection
        self.db_connection = db_connection
        self.is_sqlite = isinstance(connection, sqlite3.Connection)

        # Sorting state
        self.original_query = ""  # Query as typed by user (without modifications)
        self.active_sorts = []    # List of (column_name, direction) tuples - e.g. [('Nom', 'DESC'), ('Ville', 'ASC')]
        self.current_columns = []  # Column names from last query result

        # Editing state - track if editing an existing saved query
        self.edited_query = None  # SavedQuery object if editing existing query

        # Create tab frame
        self.frame = ttk.Frame(parent_notebook)
        parent_notebook.add(self.frame, text=tab_name)

        self._create_widgets()

    def _create_widgets(self):
        """Create query and result widgets"""
        # Query area
        query_frame = ttk.LabelFrame(self.frame, text="Query", padding="5")
        query_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Toolbar for query
        toolbar = ttk.Frame(query_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="▶ Execute (F5)", command=self._execute_query).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💾 Save Query", command=self._save_query).pack(side=tk.LEFT, padx=2)

        # Format SQL with style selector
        format_frame = ttk.Frame(toolbar)
        format_frame.pack(side=tk.LEFT, padx=2)

        ttk.Label(format_frame, text="Style:").pack(side=tk.LEFT, padx=(0, 2))

        # Create list of display names for combobox
        self.format_style_keys = list(SQL_FORMAT_STYLES.keys())
        style_names = [SQL_FORMAT_STYLES[key]['name'] for key in self.format_style_keys]

        # Load saved format style preference
        prefs = get_preferences()
        saved_style_key = prefs.get_query_format_style()

        # Find corresponding display name
        default_style_name = style_names[0]  # Fallback
        if saved_style_key in SQL_FORMAT_STYLES:
            default_style_name = SQL_FORMAT_STYLES[saved_style_key]['name']

        self.format_style_var = tk.StringVar(value=default_style_name)
        self.style_combo = ttk.Combobox(
            format_frame,
            textvariable=self.format_style_var,
            values=style_names,
            state='readonly',
            width=20
        )
        self.style_combo.pack(side=tk.LEFT, padx=2)

        ttk.Button(format_frame, text="🎨 Format", command=self._format_sql).pack(side=tk.LEFT, padx=2)

        ttk.Button(toolbar, text="🗑 Clear", command=self._clear_query).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏️ Rename Tab", command=self._rename_tab).pack(side=tk.LEFT, padx=2)

        self.query_text = scrolledtext.ScrolledText(
            query_frame,
            wrap=tk.WORD,
            height=10,
            font=("Consolas", 10)
        )
        self.query_text.pack(fill=tk.BOTH, expand=True)
        self.query_text.bind("<F5>", lambda e: self._execute_query())

        # Initialize SQL syntax highlighter
        self.highlighter = SQLHighlighter(self.query_text)
        self.highlight_timer = None

        # Bind text modification for syntax highlighting (with debouncing)
        self.query_text.bind("<KeyRelease>", self._on_text_modified)

        # Bind paste events to trigger highlighting
        self.query_text.bind("<<Paste>>", self._on_text_modified)
        self.query_text.bind("<Control-v>", self._on_text_modified)
        self.query_text.bind("<Control-V>", self._on_text_modified)
        self.query_text.bind("<Shift-Insert>", self._on_text_modified)

        # Results area
        result_frame = ttk.LabelFrame(self.frame, text="Results", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Result info
        self.result_info_var = tk.StringVar(value="No query executed")
        ttk.Label(result_frame, textvariable=self.result_info_var, foreground="gray").pack(pady=2)

        # Use CustomDataGridView for results
        self.result_grid = CustomDataGridView(
            result_frame,
            show_export=True,
            show_copy=True,
            show_raw_toggle=False
        )
        self.result_grid.pack(fill=tk.BOTH, expand=True)

    def _execute_query(self):
        """Execute the query"""
        query = self.query_text.get(1.0, tk.END).strip()
        if not query:
            messagebox.showwarning("No Query", "Please enter a SQL query.")
            return

        # Save original query and parse ORDER BY
        self.original_query = query
        self.active_sorts = self._parse_order_by(query)

        try:
            cursor = self.connection.cursor()
            cursor.execute(query)

            if cursor.description:
                # SELECT query - show results
                columns = [column[0] for column in cursor.description]
                self.current_columns = columns

                rows = cursor.fetchall()

                # Convert rows to list of dictionaries for CustomDataGridView
                data = []
                for row in rows:
                    data.append({col: row[i] for i, col in enumerate(columns)})

                # Load data into CustomDataGridView
                self.result_grid.load_data(data, columns)

                self.result_info_var.set(f"✓ {len(rows)} row(s) returned")
                logger.info(f"Query executed on {self.db_connection.name}: {len(rows)} rows returned")
            else:
                # INSERT/UPDATE/DELETE query
                rows_affected = cursor.rowcount
                self.result_grid.clear()
                self.result_info_var.set(f"✓ Query executed. {rows_affected} row(s) affected")
                logger.important(f"Query executed on {self.db_connection.name}: {rows_affected} rows affected")

            self.connection.commit()

        except Exception as e:
            self.result_info_var.set(f"✗ Error: {str(e)}")
            messagebox.showerror("Query Error", f"Failed to execute query:\n{e}")
            logger.error(f"Query execution failed on {self.db_connection.name}: {e}")

    def _parse_order_by(self, sql: str) -> list:
        """
        Parse ORDER BY clause from SQL query

        Returns: List of (column_name, direction) tuples
        Example: [('Nom', 'DESC'), ('Ville', 'ASC')]
        """
        import re

        # Find ORDER BY clause (case insensitive)
        order_by_match = re.search(r'\bORDER\s+BY\s+(.+?)(?:\s+LIMIT|\s+OFFSET|\s*$)', sql, re.IGNORECASE | re.DOTALL)

        if not order_by_match:
            return []

        order_clause = order_by_match.group(1).strip()

        # Split by comma (but be careful with functions)
        sorts = []
        parts = re.split(r',\s*', order_clause)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for DESC or ASC
            if re.search(r'\bDESC\b', part, re.IGNORECASE):
                direction = 'DESC'
                column = re.sub(r'\s+DESC\b', '', part, flags=re.IGNORECASE).strip()
            elif re.search(r'\bASC\b', part, re.IGNORECASE):
                direction = 'ASC'
                column = re.sub(r'\s+ASC\b', '', part, flags=re.IGNORECASE).strip()
            else:
                # Default is ASC if not specified
                direction = 'ASC'
                column = part.strip()

            sorts.append((column, direction))

        return sorts

    def _remove_order_by(self, sql: str) -> str:
        """Remove ORDER BY clause from SQL query"""
        import re

        # Remove ORDER BY and everything after it (including LIMIT, OFFSET, etc.)
        # But keep LIMIT/OFFSET if they exist
        result = re.sub(r'\bORDER\s+BY\s+.+?(?=\s+LIMIT|\s+OFFSET|\s*$)', '', sql, flags=re.IGNORECASE | re.DOTALL)

        return result.strip()

    def _build_order_by_clause(self) -> str:
        """Build ORDER BY clause from active_sorts"""
        if not self.active_sorts:
            return ""

        parts = [f"{col} {direction}" for col, direction in self.active_sorts]
        return f"ORDER BY {', '.join(parts)}"

    def _get_query_with_sort(self) -> str:
        """Get the original query with current sort applied"""
        # Start with original query
        base_query = self._remove_order_by(self.original_query)

        # Add current sort
        order_clause = self._build_order_by_clause()

        if order_clause:
            return f"{base_query}\n{order_clause}"
        else:
            return base_query

    def _clear_query(self):
        """Clear query text"""
        self.query_text.delete(1.0, tk.END)

    def _format_sql(self):
        """Format SQL query for readability"""
        sql_text = self.query_text.get(1.0, tk.END).strip()
        if not sql_text:
            return

        try:
            # Get selected style display name
            style_name = self.format_style_var.get()

            # Map display name back to style key
            style_key = 'expanded'  # default
            for key, info in SQL_FORMAT_STYLES.items():
                if info['name'] == style_name:
                    style_key = key
                    break

            # Format SQL with selected style
            formatted = format_sql(sql_text, style=style_key, keyword_case='upper')

            # Replace text
            self.query_text.delete(1.0, tk.END)
            self.query_text.insert(1.0, formatted)

            # Apply syntax highlighting
            self.highlighter.highlight(formatted)

            # Save the selected style as preference
            prefs = get_preferences()
            prefs.set_query_format_style(style_key)

            logger.info(f"SQL formatted with style: {style_key}")
        except Exception as e:
            messagebox.showerror("Format Error", f"Failed to format SQL:\n{e}")
            logger.error(f"SQL formatting failed: {e}")

    def _on_text_modified(self, event=None):
        """Handle text modification for syntax highlighting with debouncing"""
        # Cancel previous timer
        if self.highlight_timer:
            self.highlight_timer.cancel()

        # Schedule highlighting after 500ms of inactivity
        self.highlight_timer = threading.Timer(0.5, self._apply_highlighting)
        self.highlight_timer.start()

    def _apply_highlighting(self):
        """Apply syntax highlighting to current text"""
        try:
            self.highlighter.highlight()
        except Exception:
            # Silently fail - don't interrupt user
            pass

    def _rename_tab(self):
        """Rename this tab"""
        new_name = simpledialog.askstring("Rename Tab", "Enter new tab name:", initialvalue=self.tab_name)
        if new_name and new_name.strip():
            self.tab_name = new_name.strip()
            # Find tab index and update
            for i in range(self.parent_notebook.index("end")):
                if self.parent_notebook.nametowidget(self.parent_notebook.tabs()[i]) == self.frame:
                    self.parent_notebook.tab(i, text=self.tab_name)
                    break

    def _save_query(self):
        """Save current query to database"""
        # Always use textarea content - this is what the user sees and wants to save
        query_to_save = self.query_text.get(1.0, tk.END).strip()

        if not query_to_save:
            messagebox.showwarning("No Query", "Please enter a SQL query to save.")
            return

        # Determine if editing existing query
        is_editing = self.edited_query is not None

        # Create dialog for query details
        dialog = tk.Toplevel(self.frame)
        dialog.title("Update Query" if is_editing else "Save Query")
        dialog.geometry("500x450")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        # Main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Name
        ttk.Label(main_frame, text="Query Name:*", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar(value=self.edited_query.name if is_editing else "")
        name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)

        # Category (optional)
        ttk.Label(main_frame, text="Category:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        default_category = self.edited_query.category if is_editing else "No category"
        category_var = tk.StringVar(value=default_category)
        category_entry = ttk.Entry(main_frame, textvariable=category_var, width=40)
        category_entry.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=5)

        # Description
        ttk.Label(main_frame, text="Description:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.NW, pady=5)
        description_text = scrolledtext.ScrolledText(main_frame, width=40, height=5, wrap=tk.WORD)
        description_text.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=5)
        if is_editing and self.edited_query.description:
            description_text.insert(1.0, self.edited_query.description)

        # Query preview (read-only) - show query with current sort
        ttk.Label(main_frame, text="Query:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.NW, pady=5)
        query_preview = scrolledtext.ScrolledText(main_frame, width=40, height=8, wrap=tk.WORD)
        query_preview.insert(1.0, query_to_save)
        query_preview.config(state=tk.DISABLED, bg="#f0f0f0")
        query_preview.grid(row=3, column=1, sticky=tk.EW, pady=5, padx=5)

        main_frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)

        result = [None]

        def on_save():
            name = name_var.get().strip()
            category = category_var.get().strip()
            description = description_text.get(1.0, tk.END).strip()

            if not name:
                messagebox.showwarning("Missing Information", "Please enter a Query Name.")
                return

            # Use default category if empty
            if not category:
                category = "No category"

            if is_editing:
                # Update existing query
                self.edited_query.name = name
                self.edited_query.category = category
                self.edited_query.description = description
                self.edited_query.query_text = query_to_save

                if config_db.update_saved_query(self.edited_query):
                    logger.important(f"Updated query: {category}/{name}")
                    result[0] = self.edited_query

                    # Update textarea with query including current sort
                    self.query_text.delete(1.0, tk.END)
                    self.query_text.insert(1.0, query_to_save)

                    # Update original_query to match
                    self.original_query = query_to_save

                    # Clear active sorts since we're saving the query as-is
                    self.active_sorts = []

                    # Update tab name
                    if category and category != "No category":
                        self.tab_name = f"{category}/{name}"
                    else:
                        self.tab_name = name
                    for i in range(self.parent_notebook.index("end")):
                        if self.parent_notebook.nametowidget(self.parent_notebook.tabs()[i]) == self.frame:
                            self.parent_notebook.tab(i, text=self.tab_name)
                            break

                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to update query.")
            else:
                # Create new saved query
                saved_query = SavedQuery(
                    id="",  # Will be auto-generated
                    name=name,
                    target_database_id=self.db_connection.id,
                    query_text=query_to_save,
                    category=category,
                    description=description
                )

                # Save to database
                if config_db.add_saved_query(saved_query):
                    logger.important(f"Saved query: {category}/{name}")
                    result[0] = saved_query

                    # Update textarea with query including current sort
                    self.query_text.delete(1.0, tk.END)
                    self.query_text.insert(1.0, query_to_save)

                    # Update original_query to match
                    self.original_query = query_to_save

                    # Clear active sorts since we're saving the query as-is
                    self.active_sorts = []

                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save query.")

        def on_save_as_new():
            """Save as a new query (only available when editing)"""
            name = name_var.get().strip()
            category = category_var.get().strip()
            description = description_text.get(1.0, tk.END).strip()

            if not name:
                messagebox.showwarning("Missing Information", "Please enter a Query Name.")
                return

            # Use default category if empty
            if not category:
                category = "No category"

            # Create new saved query
            saved_query = SavedQuery(
                id="",  # Will be auto-generated
                name=name,
                target_database_id=self.db_connection.id,
                query_text=query_to_save,
                category=category,
                description=description
            )

            # Save to database
            if config_db.add_saved_query(saved_query):
                logger.important(f"Saved new query: {category}/{name}")
                result[0] = saved_query

                # Clear edited_query reference so this tab is now working with the new query
                self.edited_query = saved_query

                # Update textarea with query including current sort
                self.query_text.delete(1.0, tk.END)
                self.query_text.insert(1.0, query_to_save)

                # Update original_query to match
                self.original_query = query_to_save

                # Clear active sorts since we're saving the query as-is
                self.active_sorts = []

                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to save new query.")

        def on_cancel():
            dialog.destroy()

        save_button_text = "💾 Update" if is_editing else "💾 Save"
        ttk.Button(button_frame, text=save_button_text, command=on_save).pack(side=tk.LEFT, padx=5)

        # Add "Save As New" button only when editing
        if is_editing:
            ttk.Button(button_frame, text="📋 Save As New", command=on_save_as_new).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

        # Focus on name entry
        name_entry.focus()

        dialog.wait_window()


class DatabaseManager(ttk.Frame):
    """Database Manager GUI - Multi-tab, multi-database interface"""

    def __init__(self, parent):
        super().__init__(parent)
        self.connections = {}  # {db_connection.id: pyodbc.Connection}
        self.query_tabs = []
        self.tab_counter = 1

        self._create_widgets()
        self._load_all_connections()

    def _create_widgets(self):
        """Create main widgets"""
        # Title removed - now using toolbar for navigation

        # Toolbar
        toolbar = ttk.Frame(self, padding="5")
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="➕ New Query Tab", command=self._new_query_tab).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📂 Load Saved Query", command=self._load_saved_query).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔌 New Connection", command=self._new_connection).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⚙️ Manage Connections", command=self._manage_connections).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 Refresh Schema", command=self._refresh_current_schema).pack(side=tk.LEFT, padx=2)

        # Main container with paned window
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Database explorer (all connections)
        left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Database Explorer", font=("Arial", 10, "bold")).pack(pady=5)

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.schema_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set)
        self.schema_tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.schema_tree.yview)

        self.schema_tree.bind("<Double-Button-1>", self._on_tree_double_click)
        self.schema_tree.bind("<Button-3>", self._on_tree_right_click)  # Right-click menu

        # Right: Notebook for query tabs
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Bind right-click on tabs to show context menu
        self.notebook.bind("<Button-3>", self._on_tab_right_click)

        # Welcome tab
        self._create_welcome_tab()

    def _create_welcome_tab(self):
        """Create welcome tab"""
        welcome_frame = ttk.Frame(self.notebook)
        self.notebook.add(welcome_frame, text="Welcome")

        ttk.Label(
            welcome_frame,
            text="Welcome to Database Query Manager",
            font=("Arial", 16, "bold")
        ).pack(pady=50)

        ttk.Label(
            welcome_frame,
            text="Click '➕ New Query Tab' to start writing queries",
            font=("Arial", 11)
        ).pack(pady=10)

        ttk.Label(
            welcome_frame,
            text="All configured database connections are shown in the explorer on the left",
            font=("Arial", 11)
        ).pack(pady=10)

    def _load_all_connections(self):
        """Load and connect to all configured databases"""
        self.schema_tree.delete(*self.schema_tree.get_children())

        all_connections = connections_manager.get_all_connections()

        if not all_connections:
            no_conn_node = self.schema_tree.insert("", "end", text="No connections configured", values=("info",))
            return

        for db_conn in all_connections:
            try:
                # Connect to database - use sqlite3 for SQLite, pyodbc for others
                if db_conn.db_type == 'sqlite':
                    conn = self._connect_sqlite(db_conn.connection_string)
                else:
                    conn = pyodbc.connect(db_conn.connection_string)

                self.connections[db_conn.id] = conn

                # Add to tree
                icon = ConnectionsManager.get_db_type_icon(db_conn.db_type)
                db_node = self.schema_tree.insert(
                    "", "end",
                    text=f"{icon} {db_conn.name}",
                    values=(db_conn.id, "database"),
                    open=False
                )

                # Load schema for this connection
                self._load_database_schema(conn, db_node, db_conn)

                logger.info(f"Connected to database: {db_conn.name}")

            except Exception as e:
                icon = ConnectionsManager.get_db_type_icon(db_conn.db_type)
                error_node = self.schema_tree.insert(
                    "", "end",
                    text=f"{icon} {db_conn.name} (Connection Failed)",
                    values=(db_conn.id, "error")
                )
                logger.error(f"Failed to connect to {db_conn.name}: {e}")

    def _connect_sqlite(self, connection_string: str) -> sqlite3.Connection:
        """Extract database path from SQLite connection string and connect"""
        # Extract path from ODBC-style connection string: DRIVER={...};Database=path
        match = re.search(r'Database=([^;]+)', connection_string, re.IGNORECASE)
        if match:
            db_path = match.group(1).strip()
        else:
            # If not ODBC format, assume it's a direct path
            db_path = connection_string

        # Convert to Path and connect
        db_file = Path(db_path)
        if not db_file.exists():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")

        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_database_schema(self, conn: Union[pyodbc.Connection, sqlite3.Connection], parent_node, db_conn: DatabaseConnection):
        """Load schema for a specific database"""
        try:
            cursor = conn.cursor()
            is_sqlite = isinstance(conn, sqlite3.Connection)

            # Tables
            tables_node = self.schema_tree.insert(parent_node, "end", text="Tables", values=(db_conn.id, "folder"))
            self._load_tables(cursor, tables_node, db_conn, is_sqlite)

            # Views
            views_node = self.schema_tree.insert(parent_node, "end", text="Views", values=(db_conn.id, "folder"))
            self._load_views(cursor, views_node, db_conn, is_sqlite)

        except Exception as e:
            logger.error(f"Failed to load schema for {db_conn.name}: {e}")

    def _load_tables(self, cursor: Union[pyodbc.Cursor, sqlite3.Cursor], parent_node, db_conn: DatabaseConnection, is_sqlite: bool = False):
        """Load tables into tree view"""
        if is_sqlite:
            query = """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """
        else:
            query = """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """
        try:
            cursor.execute(query)
            for row in cursor.fetchall():
                table_name = row[0]
                table_node = self.schema_tree.insert(
                    parent_node, "end",
                    text=table_name,
                    values=(db_conn.id, "table", table_name)
                )
                self._load_columns(cursor, table_node, table_name, db_conn, is_sqlite)
        except Exception as e:
            logger.error(f"Failed to load tables: {e}")

    def _load_views(self, cursor: Union[pyodbc.Cursor, sqlite3.Cursor], parent_node, db_conn: DatabaseConnection, is_sqlite: bool = False):
        """Load views into tree view"""
        if is_sqlite:
            query = """
                SELECT name FROM sqlite_master
                WHERE type='view'
                ORDER BY name
            """
        else:
            query = """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'VIEW'
                ORDER BY TABLE_NAME
            """
        try:
            cursor.execute(query)
            for row in cursor.fetchall():
                view_name = row[0]
                view_node = self.schema_tree.insert(
                    parent_node, "end",
                    text=view_name,
                    values=(db_conn.id, "view", view_name)
                )
                self._load_columns(cursor, view_node, view_name, db_conn, is_sqlite)
        except Exception as e:
            logger.error(f"Failed to load views: {e}")

    def _load_columns(self, cursor: Union[pyodbc.Cursor, sqlite3.Cursor], parent_node, table_name: str, db_conn: DatabaseConnection, is_sqlite: bool = False):
        """Load columns for a table/view"""
        try:
            if is_sqlite:
                # SQLite uses PRAGMA table_info
                cursor.execute(f"PRAGMA table_info([{table_name}])")
                for row in cursor.fetchall():
                    # row: (cid, name, type, notnull, dflt_value, pk)
                    col_name = row[1]
                    data_type = row[2] if row[2] else "TEXT"
                    notnull = row[3]

                    type_str = data_type.upper()
                    null_str = " NOT NULL" if notnull else " NULL"
                    column_text = f"{col_name} ({type_str}{null_str})"

                    self.schema_tree.insert(
                        parent_node, "end",
                        text=column_text,
                        values=(db_conn.id, "column")
                    )
            else:
                # Standard INFORMATION_SCHEMA for other databases
                query = """
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = ?
                    ORDER BY ORDINAL_POSITION
                """
                cursor.execute(query, table_name)
                for row in cursor.fetchall():
                    col_name = row[0]
                    data_type = row[1]
                    max_length = row[2]
                    nullable = row[3]

                    type_str = data_type.upper()
                    if max_length and max_length > 0:
                        type_str += f"({max_length})"

                    null_str = " NULL" if nullable == "YES" else " NOT NULL"
                    column_text = f"{col_name} ({type_str}{null_str})"

                    self.schema_tree.insert(
                        parent_node, "end",
                        text=column_text,
                        values=(db_conn.id, "column")
                    )
        except Exception as e:
            logger.error(f"Failed to load columns: {e}")

    def _on_tree_double_click(self, event):
        """Handle double-click on tree item"""
        item = self.schema_tree.selection()
        if not item:
            return

        item_values = self.schema_tree.item(item[0], "values")
        if not item_values or len(item_values) < 2:
            return

        db_conn_id = item_values[0]
        item_type = item_values[1]

        if item_type in ["table", "view"] and len(item_values) >= 3:
            table_name = item_values[2]

            # Find active tab or create new one
            if not self.query_tabs or self.notebook.index("end") == 1:  # Only welcome tab
                self._new_query_tab()

            # Get current tab
            current_tab = self.query_tabs[-1] if self.query_tabs else None
            if current_tab:
                # Generate query based on database type
                if current_tab.is_sqlite:
                    query = f"SELECT * FROM [{table_name}] LIMIT 100"
                else:
                    query = f"SELECT TOP 100 * FROM [{table_name}]"
                current_tab.query_text.delete(1.0, tk.END)
                current_tab.query_text.insert(1.0, query)

    def _on_tree_right_click(self, event):
        """Handle right-click on tree item - show context menu"""
        # Select the item under cursor
        item = self.schema_tree.identify_row(event.y)
        if not item:
            return

        self.schema_tree.selection_set(item)

        # Get item info
        item_values = self.schema_tree.item(item, "values")
        if not item_values or len(item_values) < 2:
            return

        db_conn_id = item_values[0]
        item_type = item_values[1]

        # Show different menus based on item type
        if item_type == "database":
            # Database node - show database menu
            self._show_database_context_menu(event, db_conn_id)
            return
        elif item_type in ["table", "view"] and len(item_values) >= 3:
            # Table/View node - show table menu
            self._show_table_context_menu(event, db_conn_id, item_type, item_values[2])
            return

    def _show_database_context_menu(self, event, db_conn_id: str):
        """Show context menu for database node"""
        db_conn = connections_manager.get_connection(db_conn_id)
        if not db_conn:
            return

        # Create context menu
        context_menu = tk.Menu(self, tearoff=0)

        context_menu.add_command(
            label="Edit Connection",
            command=lambda: self._edit_database_connection(db_conn_id)
        )
        context_menu.add_command(
            label="Test Connection",
            command=lambda: self._test_database_connection(db_conn_id)
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="Refresh Schema",
            command=lambda: self._refresh_database_schema(db_conn_id)
        )

        # Show menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _show_table_context_menu(self, event, db_conn_id: str, item_type: str, table_name: str):
        """Show context menu for table/view node"""
        # Get database connection to check if it's SQLite
        db_conn = connections_manager.get_connection(db_conn_id)
        if not db_conn:
            return

        is_sqlite = db_conn.db_type == 'sqlite'

        # Create context menu
        context_menu = tk.Menu(self, tearoff=0)

        # Add menu options with different row limits
        context_menu.add_command(
            label="SELECT Top 100 rows",
            command=lambda: self._execute_select_query(db_conn_id, table_name, 100, is_sqlite)
        )
        context_menu.add_command(
            label="SELECT Top 1000 rows",
            command=lambda: self._execute_select_query(db_conn_id, table_name, 1000, is_sqlite)
        )
        context_menu.add_command(
            label="SELECT Top 10000 rows",
            command=lambda: self._execute_select_query(db_conn_id, table_name, 10000, is_sqlite)
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="SELECT ALL rows (no limit)",
            command=lambda: self._execute_select_query(db_conn_id, table_name, None, is_sqlite)
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="COUNT(*) rows",
            command=lambda: self._execute_count_query(db_conn_id, table_name)
        )

        # Show menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _execute_select_query(self, db_conn_id: str, table_name: str, limit: Optional[int], is_sqlite: bool):
        """Execute a SELECT query with specified limit"""
        # Get or create a query tab for this database
        db_conn = connections_manager.get_connection(db_conn_id)
        if not db_conn:
            return

        # Check if we have an active tab for this database, otherwise create one
        current_tab = None
        if self.query_tabs and self.notebook.select():
            # Check if current tab is for same database
            try:
                current_idx = self.notebook.index(self.notebook.select())
                # Check if it's not the welcome tab (index 0) and is a valid query tab
                if current_idx > 0 and current_idx <= len(self.query_tabs):
                    tab = self.query_tabs[current_idx - 1]
                    if tab.db_connection.id == db_conn_id:
                        current_tab = tab
            except:
                pass

        # If no suitable tab found, create new one
        if not current_tab:
            # Temporarily store the db_conn_id for _new_query_tab
            self._temp_selected_db = db_conn
            self._new_query_tab()
            if self.query_tabs:
                current_tab = self.query_tabs[-1]

        if not current_tab:
            return

        # Generate query based on database type and limit
        if limit is None:
            # No limit
            query = f"SELECT * FROM [{table_name}]"
        elif is_sqlite:
            query = f"SELECT * FROM [{table_name}] LIMIT {limit}"
        else:
            query = f"SELECT TOP {limit} * FROM [{table_name}]"

        # Insert query and execute
        current_tab.query_text.delete(1.0, tk.END)
        current_tab.query_text.insert(1.0, query)
        current_tab._execute_query()

        logger.info(f"Executed SELECT on {table_name} with limit={limit}")

    def _execute_count_query(self, db_conn_id: str, table_name: str):
        """Execute a COUNT(*) query"""
        db_conn = connections_manager.get_connection(db_conn_id)
        if not db_conn:
            return

        # Check if we have an active tab for this database
        current_tab = None
        if self.query_tabs and self.notebook.select():
            try:
                current_idx = self.notebook.index(self.notebook.select())
                if current_idx > 0 and current_idx <= len(self.query_tabs):
                    tab = self.query_tabs[current_idx - 1]
                    if tab.db_connection.id == db_conn_id:
                        current_tab = tab
            except:
                pass

        if not current_tab:
            self._temp_selected_db = db_conn
            self._new_query_tab()
            if self.query_tabs:
                current_tab = self.query_tabs[-1]

        if not current_tab:
            return

        # Generate COUNT query
        query = f"SELECT COUNT(*) as row_count FROM [{table_name}]"

        # Insert query and execute
        current_tab.query_text.delete(1.0, tk.END)
        current_tab.query_text.insert(1.0, query)
        current_tab._execute_query()

        logger.info(f"Executed COUNT on {table_name}")

    def _new_query_tab(self):
        """Create new query tab"""
        # Check if there's a pre-selected database (from context menu)
        if hasattr(self, '_temp_selected_db') and self._temp_selected_db:
            db_conn = self._temp_selected_db
            logger.info(f"Using pre-selected database: {db_conn.name}")
            self._temp_selected_db = None  # Clear temporary selection
        else:
            logger.info("No pre-selected database, showing selection dialog")
            # Show database selection dialog
            db_conn = self._select_database()
            if not db_conn:
                return

        if db_conn.id not in self.connections:
            messagebox.showerror("Connection Error", f"Not connected to {db_conn.name}")
            return

        tab_name = f"Query {self.tab_counter}"
        self.tab_counter += 1

        query_tab = QueryTab(
            self.notebook,
            tab_name,
            self.connections[db_conn.id],
            db_conn
        )
        self.query_tabs.append(query_tab)

        # Select the new tab
        self.notebook.select(self.notebook.index("end") - 1)

        logger.info(f"Created new query tab for {db_conn.name}")

    def _select_database(self) -> Optional[DatabaseConnection]:
        """Show dialog to select database for query tab"""
        all_connections = connections_manager.get_all_connections()

        if not all_connections:
            messagebox.showwarning("No Connections", "No database connections configured.\n\nPlease add a connection first.")
            return None

        if len(all_connections) == 1:
            return all_connections[0]

        # Create selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Select Database")
        dialog.geometry("500x400")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="Select Database Connection:", font=("Arial", 11, "bold")).pack(pady=10)

        # Listbox with connections
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        for conn in all_connections:
            icon = ConnectionsManager.get_db_type_icon(conn.db_type)
            listbox.insert(tk.END, f"{icon} {conn.name} - {conn.description}")

        listbox.select_set(0)

        selected_conn = [None]

        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_conn[0] = all_connections[selection[0]]
                dialog.destroy()

        def on_cancel():
            dialog.destroy()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Select", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

        listbox.bind("<Double-Button-1>", lambda e: on_select())

        dialog.wait_window()
        return selected_conn[0]

    def _close_current_tab(self):
        """Close the currently selected tab"""
        current_tab_index = self.notebook.index(self.notebook.select())

        # Don't close welcome tab
        if current_tab_index == 0 and self.notebook.tab(0, "text") == "Welcome":
            messagebox.showinfo("Info", "Cannot close the welcome tab")
            return

        # Find and remove the query tab
        tab_widget = self.notebook.nametowidget(self.notebook.select())
        for i, qt in enumerate(self.query_tabs):
            if qt.frame == tab_widget:
                self.query_tabs.pop(i)
                break

        self.notebook.forget(current_tab_index)
        logger.info("Closed query tab")

    def _on_tab_right_click(self, event):
        """Handle right-click on notebook tab"""
        # Identify which tab was clicked
        try:
            clicked_tab = self.notebook.tk.call(self.notebook._w, "identify", "tab", event.x, event.y)
        except:
            return  # Click was not on a tab

        if clicked_tab == '':
            return  # Click was not on a tab

        # Get tab index
        tab_index = int(clicked_tab)

        # Don't show menu for welcome tab
        if tab_index == 0 and self.notebook.tab(0, "text") == "Welcome":
            return

        # Show context menu
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(
            label="❌ Close Tab",
            command=lambda: self._close_tab_by_index(tab_index)
        )

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _close_tab_by_index(self, tab_index: int):
        """Close a tab by its index"""
        # Don't close welcome tab
        if tab_index == 0 and self.notebook.tab(0, "text") == "Welcome":
            return

        # Find and remove the query tab
        tab_widget = self.notebook.nametowidget(self.notebook.tabs()[tab_index])
        for i, qt in enumerate(self.query_tabs):
            if qt.frame == tab_widget:
                self.query_tabs.pop(i)
                break

        self.notebook.forget(tab_index)
        logger.info("Closed query tab")

    def _refresh_current_schema(self):
        """Refresh schema tree"""
        self._load_all_connections()
        logger.info("Schema refreshed")

    def _load_saved_query(self):
        """Load a saved query from database"""
        # Get all saved queries
        all_queries = config_db.get_all_saved_queries()

        if not all_queries:
            messagebox.showinfo("No Saved Queries", "No saved queries found in the database.")
            return

        # Create selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Load Saved Query")
        dialog.geometry("700x500")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="Select a Saved Query:", font=("Arial", 11, "bold")).pack(pady=10)

        # Create treeview with columns
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        columns = ("Name", "Category", "Database", "Projects", "Description")
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, minwidth=50)

        tree.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)

        # Populate tree
        query_map = {}
        rows_data = []
        for query in all_queries:
            # Get database name
            db_conn = connections_manager.get_connection(query.target_database_id)
            db_name = db_conn.name if db_conn else "Unknown"

            # Get projects attached to this query
            projects = config_db.get_query_projects(query.id)
            projects_str = ", ".join([p.name for p in projects]) if projects else "No project"

            row_values = (
                query.name,
                query.category,
                db_name,
                projects_str,
                query.description
            )
            item_id = tree.insert("", "end", values=row_values)
            query_map[item_id] = query
            rows_data.append(row_values)

        # Auto-size columns based on content
        self._autosize_treeview_columns(tree, columns, rows_data)

        selected_query = [None]

        def on_select():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a query to load.")
                return

            selected_query[0] = query_map[selection[0]]
            dialog.destroy()

        def on_double_click(event):
            on_select()

        def on_cancel():
            dialog.destroy()

        tree.bind("<Double-Button-1>", on_double_click)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Load Query", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

        dialog.wait_window()

        if selected_query[0]:
            # Load the query
            query = selected_query[0]

            # Get database connection
            db_conn = connections_manager.get_connection(query.target_database_id)
            if not db_conn:
                messagebox.showerror("Error", f"Database connection not found for this query.")
                return

            if db_conn.id not in self.connections:
                messagebox.showerror("Connection Error", f"Not connected to {db_conn.name}")
                return

            # Create or reuse query tab
            current_tab = None
            if self.query_tabs and self.notebook.select():
                try:
                    current_idx = self.notebook.index(self.notebook.select())
                    if current_idx > 0 and current_idx <= len(self.query_tabs):
                        tab = self.query_tabs[current_idx - 1]
                        if tab.db_connection.id == db_conn.id:
                            current_tab = tab
                except:
                    pass

            if not current_tab:
                # Create new tab for this database
                self._temp_selected_db = db_conn
                self._new_query_tab()
                if self.query_tabs:
                    current_tab = self.query_tabs[-1]

            if current_tab:
                # Load query text
                current_tab.query_text.delete(1.0, tk.END)
                current_tab.query_text.insert(1.0, query.query_text)

                # Rename tab to query name
                current_tab.tab_name = f"{query.category}/{query.name}"
                for i in range(current_tab.parent_notebook.index("end")):
                    if current_tab.parent_notebook.nametowidget(current_tab.parent_notebook.tabs()[i]) == current_tab.frame:
                        current_tab.parent_notebook.tab(i, text=current_tab.tab_name)
                        break

                logger.info(f"Loaded saved query: {query.category}/{query.name}")
                messagebox.showinfo("Success", f"Query '{query.name}' loaded successfully!")

    def _edit_database_connection(self, db_conn_id: str):
        """Edit a database connection"""
        db_conn = connections_manager.get_connection(db_conn_id)
        if not db_conn:
            messagebox.showerror("Error", "Database connection not found.")
            return

        # Show edit dialog
        dialog = ConnectionDialog(self, connection=db_conn)
        if dialog.result:
            # Refresh connections
            self._load_all_connections()
            logger.info(f"Edited database connection: {db_conn.name}")

    def _test_database_connection(self, db_conn_id: str):
        """Test a database connection"""
        db_conn = connections_manager.get_connection(db_conn_id)
        if not db_conn:
            messagebox.showerror("Error", "Database connection not found.")
            return

        try:
            if db_conn.db_type == 'sqlite':
                test_conn = self._connect_sqlite(db_conn.connection_string)
            else:
                test_conn = pyodbc.connect(db_conn.connection_string, timeout=5)

            test_conn.close()
            messagebox.showinfo("Success", f"Connection to '{db_conn.name}' successful!")
            logger.info(f"Test connection successful: {db_conn.name}")
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Failed to connect to '{db_conn.name}':\n\n{str(e)}")
            logger.error(f"Test connection failed for {db_conn.name}: {e}")

    def _refresh_database_schema(self, db_conn_id: str):
        """Refresh schema for a specific database"""
        db_conn = connections_manager.get_connection(db_conn_id)
        if not db_conn:
            return

        # Find the database node in the tree
        for item in self.schema_tree.get_children():
            item_values = self.schema_tree.item(item, "values")
            if item_values and len(item_values) >= 2 and item_values[0] == db_conn_id:
                # Delete children (Tables, Views folders)
                for child in self.schema_tree.get_children(item):
                    self.schema_tree.delete(child)

                # Reload schema
                if db_conn_id in self.connections:
                    self._load_database_schema(self.connections[db_conn_id], item, db_conn)
                    logger.info(f"Refreshed schema for: {db_conn.name}")
                break

    def _new_connection(self):
        """Open new connection dialog"""
        parent = self.winfo_toplevel()

        dialog = ConnectionDialog(parent)
        result = dialog.show()

        if result:
            # Refresh connections list
            self._load_all_connections()
            logger.important(f"Created new connection: {result.name}")

    def _manage_connections(self):
        """Open connections management window"""
        # Find the main GUI window
        parent = self.winfo_toplevel()

        # Call the manage connections method if it exists
        for widget in parent.winfo_children():
            if hasattr(widget, 'master') and hasattr(widget.master, '_manage_connections'):
                widget.master._manage_connections()
                # Refresh after closing
                self.after(500, self._load_all_connections)
                return

        messagebox.showinfo("Info", "Please use Database → Manage Connections from the main menu")

    def apply_theme(self):
        """Apply current theme to DatabaseManager and all query tabs"""
        try:
            # Apply theme to schema tree if it exists
            if hasattr(self, 'schema_tree'):
                # Note: schema_tree is a ttk.Treeview, not CustomTreeView
                # Theme will be applied via ttk.Style in child components
                pass

            # Apply theme to all query tabs
            for tab_id, tab_data in self.query_tabs.items():
                if 'grid' in tab_data and hasattr(tab_data['grid'], 'apply_theme'):
                    tab_data['grid'].apply_theme()

        except Exception as e:
            from ..utils.logger import logger
            logger.debug(f"Failed to apply theme to DatabaseManager: {e}")
