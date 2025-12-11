"""
Connection Dialog - Add/Edit database connections
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyodbc
from ..database.config_db import DatabaseConnection
from ..database.connections_config import ConnectionsManager, connections_manager
from ..utils.logger import logger


class ConnectionDialog:
    """Dialog for adding/editing database connections"""

    def __init__(self, parent, connection: DatabaseConnection = None):
        self.parent = parent
        self.connection = connection
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Database Connection" if connection is None else f"Edit Connection: {connection.name}")
        self.dialog.geometry("700x550")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()

        if connection:
            self._load_connection_data()

    def _create_widgets(self):
        """Create dialog widgets"""
        # Title
        title = "New Database Connection" if self.connection is None else "Edit Database Connection"
        ttk.Label(
            self.dialog,
            text=title,
            font=("Arial", 12, "bold")
        ).pack(pady=10)

        # Main form
        form_frame = ttk.Frame(self.dialog, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Name
        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(form_frame, width=50)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)

        # Database Type
        ttk.Label(form_frame, text="Database Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.db_type_var = tk.StringVar(value="sqlserver")
        db_type_frame = ttk.Frame(form_frame)
        db_type_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        db_types = [
            ("SQL Server", "sqlserver"),
            ("MySQL", "mysql"),
            ("PostgreSQL", "postgresql"),
            ("Oracle", "oracle"),
            ("SQLite", "sqlite"),
            ("Other", "other")
        ]

        for i, (label, value) in enumerate(db_types):
            ttk.Radiobutton(
                db_type_frame,
                text=label,
                variable=self.db_type_var,
                value=value
            ).pack(side=tk.LEFT, padx=5)

        # Description
        ttk.Label(form_frame, text="Description:").grid(row=2, column=0, sticky=tk.NW, pady=5)
        self.desc_entry = ttk.Entry(form_frame, width=50)
        self.desc_entry.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=5)

        # Connection String
        ttk.Label(form_frame, text="Connection String:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.conn_text = scrolledtext.ScrolledText(form_frame, wrap=tk.WORD, height=8, width=50)
        self.conn_text.grid(row=3, column=1, sticky=tk.EW, pady=5, padx=5)

        form_frame.columnconfigure(1, weight=1)

        # Examples
        examples_frame = ttk.LabelFrame(self.dialog, text="Connection String Examples", padding="5")
        examples_frame.pack(fill=tk.X, padx=10, pady=5)

        examples_text = scrolledtext.ScrolledText(examples_frame, wrap=tk.WORD, height=6, width=80)
        examples_text.pack(fill=tk.BOTH, expand=True)

        examples = """SQL Server:
DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=MyDB;UID=user;PWD=password
DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=MyDB;Trusted_Connection=yes

MySQL:
DRIVER={MySQL ODBC 8.0 Driver};SERVER=localhost;DATABASE=mydb;USER=root;PASSWORD=password

PostgreSQL:
DRIVER={PostgreSQL Unicode};SERVER=localhost;PORT=5432;DATABASE=mydb;UID=postgres;PWD=password"""

        examples_text.insert(1.0, examples)
        examples_text.config(state=tk.DISABLED)

        # Status label
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(self.dialog, textvariable=self.status_var, foreground="blue")
        self.status_label.pack(pady=5)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", command=self._save_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _load_connection_data(self):
        """Load existing connection data into form"""
        self.name_entry.insert(0, self.connection.name)
        self.db_type_var.set(self.connection.db_type)
        self.desc_entry.insert(0, self.connection.description)
        self.conn_text.insert(1.0, self.connection.connection_string)

    def _test_connection(self):
        """Test the connection"""
        conn_str = self.conn_text.get(1.0, tk.END).strip()
        if not conn_str:
            self.status_var.set("Please enter a connection string")
            self.status_label.config(foreground="red")
            return

        try:
            # Try to connect based on database type
            test_conn = pyodbc.connect(conn_str)
            test_conn.close()
            self.status_var.set("✓ Connection successful!")
            self.status_label.config(foreground="green")
            logger.info(f"Database connection test successful for '{self.name_entry.get()}'")
        except Exception as e:
            error_msg = str(e)[:100]
            self.status_var.set(f"✗ Connection failed: {error_msg}")
            self.status_label.config(foreground="red")
            logger.error(f"Database connection test failed: {e}")

    def _save_connection(self):
        """Save the connection"""
        name = self.name_entry.get().strip()
        db_type = self.db_type_var.get()
        description = self.desc_entry.get().strip()
        conn_str = self.conn_text.get(1.0, tk.END).strip()

        if not name:
            messagebox.showwarning("Missing Information", "Please enter a connection name")
            return

        if not conn_str:
            messagebox.showwarning("Missing Information", "Please enter a connection string")
            return

        # Test connection first
        try:
            test_conn = pyodbc.connect(conn_str)
            test_conn.close()
        except Exception as e:
            result = messagebox.askyesno(
                "Connection Failed",
                f"Connection test failed:\n{e}\n\nDo you want to save anyway?"
            )
            if not result:
                return

        # Create or update connection
        if self.connection is None:
            # New connection
            new_conn = DatabaseConnection(
                id="",  # Will be auto-generated by __post_init__
                name=name,
                db_type=db_type,
                description=description,
                connection_string=conn_str
            )
            connections_manager.add_connection(new_conn)
            logger.important(f"Created new database connection: {name}")
            self.result = new_conn
        else:
            # Update existing connection
            updated_conn = DatabaseConnection(
                id=self.connection.id,  # Keep existing ID
                name=name,
                db_type=db_type,
                description=description,
                connection_string=conn_str
            )
            connections_manager.update_connection(self.connection.id, updated_conn)
            logger.important(f"Updated database connection: {name}")
            self.result = updated_conn

        self.dialog.destroy()

    def show(self) -> DatabaseConnection:
        """Show dialog and return result"""
        self.dialog.wait_window()
        return self.result
