"""
GUI Module - Tkinter graphical interface for DataForge Studio
Single window with interchangeable frames
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import pyodbc

# Import from core modules
from ..core.file_dispatcher import FileDispatcher
from ..core.data_loader import DataLoader

# Import from utils
from ..utils.config import Config
from ..utils.logger import logger, LogLevel
from ..utils.update_checker import get_update_checker

# Import from database
from ..database.config_db import DatabaseConnection
from ..database.connections_config import connections_manager, ConnectionsManager

# Import from ui
from .database_manager import DatabaseManager
from .connection_dialog import ConnectionDialog
from .queries_manager import QueriesManager
from .help_viewer import show_help
from .data_explorer import DataExplorer
from .file_root_manager import show_file_root_manager
from .preferences_dialog import PreferencesDialog

# Import config managers
from ..config.theme_manager import get_theme_manager
from ..config.user_preferences import get_preferences
from ..config.i18n import get_i18n
from ..constants import APP_NAME, APP_VERSION, APP_TITLE, APP_DESCRIPTION


class DataLakeFrame(ttk.Frame):
    """Data Lake operations frame"""

    def __init__(self, parent, gui_parent):
        super().__init__(parent)
        self.gui_parent = gui_parent
        self._create_widgets()

    def _create_widgets(self):
        """Create widgets for data lake operations"""
        title_frame = ttk.Frame(self, padding="10")
        title_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            title_frame,
            text="Data Lake Operations",
            font=("Arial", 16, "bold")
        )
        title_label.pack()

        info_frame = ttk.LabelFrame(self, text="Configuration", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(info_frame, text=f"Root Folder: {Config.DATA_ROOT_FOLDER}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Database: {Config.DB_NAME} on {Config.DB_HOST}").pack(anchor=tk.W)

        # Log area
        self._create_log_area()

    def _create_log_area(self):
        """Create log area with filters"""
        log_frame = ttk.LabelFrame(self, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        filter_frame = ttk.Frame(log_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(
            filter_frame,
            text="Error",
            variable=self.gui_parent.log_filters[LogLevel.ERROR]
        ).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(
            filter_frame,
            text="Warning",
            variable=self.gui_parent.log_filters[LogLevel.WARNING]
        ).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(
            filter_frame,
            text="Important",
            variable=self.gui_parent.log_filters[LogLevel.IMPORTANT]
        ).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(
            filter_frame,
            text="Information",
            variable=self.gui_parent.log_filters[LogLevel.INFO]
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            filter_frame,
            text="Clear Log",
            command=self.gui_parent._clear_log
        ).pack(side=tk.RIGHT, padx=5)

        self.gui_parent.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=80,
            height=15,
            state=tk.DISABLED
        )
        self.gui_parent.log_text.pack(fill=tk.BOTH, expand=True)

        self.gui_parent.log_text.tag_config("ERROR", foreground="red")
        self.gui_parent.log_text.tag_config("WARNING", foreground="orange")
        self.gui_parent.log_text.tag_config("IMPORTANT", foreground="blue")
        self.gui_parent.log_text.tag_config("INFO", foreground="black")

    def dispatch_files_threaded(self):
        """Run dispatch files in separate thread"""
        thread = threading.Thread(target=self.dispatch_files)
        thread.daemon = True
        thread.start()

    def dispatch_files(self):
        """Execute file dispatch process"""
        self.gui_parent._update_menu_state(False)
        logger.info("=" * 60)
        logger.info("Starting File Dispatch Process")
        logger.info("=" * 60)
        logger.info(f"Root folder: {Config.DATA_ROOT_FOLDER}")

        try:
            dispatcher = FileDispatcher()
            stats = dispatcher.dispatch_files()

            logger.info("")
            logger.info("=" * 60)
            logger.important("File Dispatch Completed")
            logger.info("=" * 60)
            logger.important(f"Files dispatched: {stats['dispatched']}")
            logger.warning(f"Invalid files: {stats['invalid']}")
            if stats['errors'] > 0:
                logger.error(f"Errors: {stats['errors']}")
            logger.info("=" * 60)

            messagebox.showinfo("Success", "File dispatch completed successfully!")

        except Exception as e:
            logger.error(f"Error during file dispatch: {e}")
            messagebox.showerror("Error", f"Error during file dispatch:\n{e}")

        finally:
            self.gui_parent._update_menu_state(True)

    def load_files_threaded(self):
        """Run load files in separate thread"""
        thread = threading.Thread(target=self.load_files)
        thread.daemon = True
        thread.start()

    def load_files(self):
        """Execute data load process"""
        self.gui_parent._update_menu_state(False)
        logger.info("=" * 60)
        logger.info("Starting Data Load Process")
        logger.info("=" * 60)
        logger.info(f"Root folder: {Config.DATA_ROOT_FOLDER}")
        logger.info(f"Database: {Config.DB_NAME} on {Config.DB_HOST}")

        try:
            loader = DataLoader()
            stats = loader.load_all_files()

            logger.info("")
            logger.info("=" * 60)
            logger.important("Data Load Completed")
            logger.info("=" * 60)
            logger.important(f"Files processed: {stats['files_processed']}")
            logger.important(f"Files imported: {stats['files_imported']}")
            if stats['files_failed'] > 0:
                logger.error(f"Files failed: {stats['files_failed']}")
            logger.important(f"Tables created: {stats['tables_created']}")
            logger.important(f"Tables updated: {stats['tables_updated']}")
            logger.info("=" * 60)

            messagebox.showinfo("Success", "Data load completed successfully!")

        except Exception as e:
            logger.error(f"Error during data load: {e}")
            messagebox.showerror("Error", f"Error during data load:\n{e}")

        finally:
            self.gui_parent._update_menu_state(True)


class DataLakeLoaderGUI:
    """Main GUI with interchangeable frames"""

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1200x800")

        # Initialize configuration managers
        self.theme_manager = get_theme_manager()
        self.preferences = get_preferences()
        self.i18n = get_i18n()

        # Load saved preferences
        saved_theme = self.preferences.get_theme()
        saved_language = self.preferences.get_language()

        # Normalize theme name: convert display name to theme ID if needed
        available_themes = self.theme_manager.get_available_themes()
        if saved_theme not in available_themes:
            # Try to find by display name
            for theme_id, display_name in available_themes.items():
                if display_name == saved_theme:
                    saved_theme = theme_id
                    self.preferences.set_theme(theme_id)  # Update to use correct ID
                    break

        # If still not found, use default
        if saved_theme not in available_themes:
            saved_theme = 'classic_light'
            self.preferences.set_theme(saved_theme)

        # Apply saved preferences
        self.theme_manager.set_theme(saved_theme)
        self.i18n.set_language(saved_language)

        # Register as observers for live updates
        self.theme_manager.register_observer(self._apply_theme)
        self.i18n.register_observer(self._apply_language)

        self.log_filters = {
            LogLevel.ERROR: tk.BooleanVar(value=True),
            LogLevel.WARNING: tk.BooleanVar(value=True),
            LogLevel.IMPORTANT: tk.BooleanVar(value=True),
            LogLevel.INFO: tk.BooleanVar(value=True)
        }

        self.current_frame = None
        self.log_text = None
        self.toolbar_buttons = {}  # Store toolbar button references
        self.update_on_quit = False  # Flag for automatic update on quit

        self._create_menubar()
        self._create_toolbar()
        self._create_status_bar()
        self._create_main_container()

        logger.set_gui_callback(self._log_from_logger)

        # Apply initial theme
        self._apply_theme()

        # Show Data Explorer by default
        self._show_data_explorer()

        # Check for updates (with 24h cooldown)
        self._check_for_updates_startup()

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_menubar(self):
        """Create menu bar"""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # ==================== DATA MENU ====================
        self.data_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Data", menu=self.data_menu)
        self.data_menu.add_command(label="📁 Manage Projects...", command=self._manage_projects)
        self.data_menu.add_command(label="💾 Manage Root Folders...", command=self._manage_root_folders)

        # ==================== SCRIPTS MENU ====================
        self.scripts_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Scripts", menu=self.scripts_menu)
        self.scripts_menu.add_command(label="📥 Dispatch Files", command=self._dispatch_files_from_menu)
        self.scripts_menu.add_command(label="📤 Load to Database", command=self._load_files_from_menu)

        # ==================== DATABASES MENU ====================
        self.databases_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Databases", menu=self.databases_menu)
        self.databases_menu.add_command(label="➕ New Connection...", command=self._new_database_connection)
        self.databases_menu.add_command(label="⚙️ Manage Connections...", command=self._manage_connections)

        # ==================== JOBS MENU ====================
        self.jobs_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Jobs", menu=self.jobs_menu)
        self.jobs_menu.add_command(label="📋 Job Manager (Coming Soon)", state='disabled')
        self.jobs_menu.add_separator()
        self.jobs_menu.add_command(label="⚙️ Configure Jobs...", state='disabled')

        # ==================== SETTINGS MENU ====================
        settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="⚙️ Preferences...", command=self._show_preferences)

        # ==================== HELP MENU ====================
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📚 Documentation", command=self._show_documentation)
        help_menu.add_separator()
        help_menu.add_command(label="🔄 Check for Updates...", command=self._check_for_updates_manual)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_separator()
        help_menu.add_command(label="Exit", command=self.root.quit)

    def _create_toolbar(self):
        """Create toolbar with view selection buttons"""
        self.toolbar_frame = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        self.toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)

        # Define toolbar buttons
        buttons_config = [
            ("data_explorer", "📂 Projets", self._show_data_explorer),
            ("data_lake", "📊 Data Lake", self._show_datalake_frame),
            ("databases", "🗄️ Databases", self._show_database_frame),
            ("queries", "📋 Queries", self._show_queries_frame),
        ]

        for btn_id, label, command in buttons_config:
            btn = tk.Button(
                self.toolbar_frame,
                text=label,
                command=command,
                relief=tk.FLAT,
                padx=15,
                pady=8,
                font=("Segoe UI", 10),
                bg="#f0f0f0",
                activebackground="#0078d4",
                activeforeground="white",
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.toolbar_buttons[btn_id] = btn

    def _update_toolbar_state(self, active_button_id):
        """Update toolbar buttons visual state using current theme"""
        theme = self.theme_manager.get_current_theme()

        for btn_id, btn in self.toolbar_buttons.items():
            if btn_id == active_button_id:
                # Active state - use theme's active button colors
                btn.config(
                    relief=tk.SUNKEN,
                    bg=theme.get('button_active_bg'),
                    fg=theme.get('button_active_fg'),
                    font=("Segoe UI", 10, "bold")
                )
            else:
                # Inactive state - use theme's normal button colors
                btn.config(
                    relief=tk.FLAT,
                    bg=theme.get('button_bg'),
                    fg=theme.get('button_fg'),
                    font=("Segoe UI", 10)
                )

    def _create_main_container(self):
        """Create main container for interchangeable frames"""
        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Store reference to GUI for child frames to access
        self.container.gui = self

    def _create_status_bar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root, padding="5")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame, text=self.i18n.t('status_version_up_to_date'), relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)

        # Store update info for click handler
        self.update_info = None

    def _switch_frame(self, frame_class, *args, **kwargs):
        """Switch to a different frame"""
        if self.current_frame is not None:
            self.current_frame.destroy()

        # Reset log_text when switching frames
        self.log_text = None

        self.current_frame = frame_class(self.container, *args, **kwargs)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def _show_datalake_frame(self):
        """Show Data Lake operations frame"""
        self._switch_frame(DataLakeFrame, self)
        self._update_toolbar_state("data_lake")
        # self.status_label.config(text="Data Lake Operations")
        logger.info("Switched to Data Lake view")

    def _dispatch_files_from_menu(self):
        """Dispatch files from menu"""
        if isinstance(self.current_frame, DataLakeFrame):
            self.current_frame.dispatch_files_threaded()
        else:
            messagebox.showwarning("Wrong View", "Please switch to Data Lake view first.")

    def _load_files_from_menu(self):
        """Load files from menu"""
        if isinstance(self.current_frame, DataLakeFrame):
            self.current_frame.load_files_threaded()
        else:
            messagebox.showwarning("Wrong View", "Please switch to Data Lake view first.")

    def _show_database_frame(self):
        """Show Database Manager frame"""
        from ..database.connections_config import connections_manager

        # Check if coming from DataExplorer with a selected database
        selected_db_id = None
        if isinstance(self.current_frame, DataExplorer):
            selected_db_id = self.current_frame.get_selected_database_id()
            if selected_db_id:
                logger.info(f"Detected selected database ID from DataExplorer: {selected_db_id}")

        self._switch_frame(DatabaseManager)
        self._update_toolbar_state("databases")
        logger.info("Switched to Database Manager view")

        # If a database was selected in DataExplorer, create a new query tab for it
        if selected_db_id and isinstance(self.current_frame, DatabaseManager):
            db_conn = connections_manager.get_connection(selected_db_id)
            if db_conn:
                logger.info(f"Found database connection: {db_conn.name}")
                # Check if connection is loaded in DatabaseManager
                if db_conn.id in self.current_frame.connections:
                    logger.info(f"Database connection found in DatabaseManager.connections")
                    # Set temporary selected database and create new query tab
                    self.current_frame._temp_selected_db = db_conn
                    self.current_frame._new_query_tab()
                    logger.info(f"Auto-created query tab for database: {db_conn.name}")
                else:
                    logger.warning(f"Database {db_conn.name} (ID: {db_conn.id}) not found in DatabaseManager.connections")
                    logger.warning(f"Available connections: {list(self.current_frame.connections.keys())}")
            else:
                logger.error(f"Database connection not found for ID: {selected_db_id}")

    def _show_queries_frame(self):
        """Show Queries Manager frame"""
        self._switch_frame(QueriesManager)
        self._update_toolbar_state("queries")
        # self.status_label.config(text="Saved Queries Manager")
        logger.info("Switched to Queries Manager view")

    def _show_data_explorer(self):
        """Show Data Explorer frame"""
        self._switch_frame(DataExplorer, self)
        self._update_toolbar_state("data_explorer")
        # self.status_label.config(text="Data Explorer")
        logger.info("Switched to Data Explorer view")

    def _manage_root_folders(self):
        """Open Root Folders management window"""
        show_file_root_manager(self.root)
        logger.info("Opened Root Folders Manager")

    def _manage_projects(self):
        """Open Projects management window"""
        from .project_manager import show_project_manager
        show_project_manager(self.root)
        logger.info("Opened Projects Manager")

    def _show_database_frame_with_query(self, query, execute=False):
        """Show Database Manager frame and load a specific query

        Args:
            query: SavedQuery object to load
            execute: If True, automatically execute the query after loading
        """
        self._switch_frame(DatabaseManager)
        self._update_toolbar_state("databases")
        # self.status_label.config(text="Database Query Manager")

        action = "executing" if execute else "loading"
        logger.info(f"Switched to Database Manager view - {action} query")

        # Load the query in the DatabaseManager
        if isinstance(self.current_frame, DatabaseManager):
            # Get database connection
            db_conn = connections_manager.get_connection(query.target_database_id)
            if not db_conn:
                messagebox.showerror("Error", "Database connection not found for this query.")
                return

            if db_conn.id not in self.current_frame.connections:
                messagebox.showerror("Connection Error", f"Not connected to {db_conn.name}")
                return

            # Create new tab with the query
            self.current_frame._temp_selected_db = db_conn
            self.current_frame._new_query_tab()

            if self.current_frame.query_tabs:
                current_tab = self.current_frame.query_tabs[-1]

                # Store reference to the query being edited
                current_tab.edited_query = query

                # Load query text
                current_tab.query_text.delete(1.0, tk.END)
                current_tab.query_text.insert(1.0, query.query_text)

                # Rename tab
                if query.category and query.category != "No category":
                    current_tab.tab_name = f"{query.category}/{query.name}"
                else:
                    current_tab.tab_name = query.name
                for i in range(current_tab.parent_notebook.index("end")):
                    if current_tab.parent_notebook.nametowidget(current_tab.parent_notebook.tabs()[i]) == current_tab.frame:
                        current_tab.parent_notebook.tab(i, text=current_tab.tab_name)
                        break

                logger.info(f"Loaded query in Query Manager: {current_tab.tab_name}")

                # Execute query if requested
                if execute:
                    # Schedule execution after UI updates
                    current_tab.frame.after(100, current_tab._execute_query)
                    logger.info(f"Executing query: {current_tab.tab_name}")

    def _execute_table_query_from_explorer(self, db_id: str, query_text: str):
        """Execute a table query from Data Explorer

        Args:
            db_id: Database connection ID
            query_text: SQL query to execute
        """
        # Switch to Database Manager
        self._switch_frame(DatabaseManager)
        self._update_toolbar_state("databases")
        logger.info("Switched to Database Manager view - executing table query")

        # Execute the query in DatabaseManager
        if isinstance(self.current_frame, DatabaseManager):
            # Get database connection
            db_conn = connections_manager.get_connection(db_id)
            if not db_conn:
                messagebox.showerror("Error", "Database connection not found.")
                return

            if db_conn.id not in self.current_frame.connections:
                messagebox.showerror("Connection Error", f"Not connected to {db_conn.name}")
                return

            # Create new tab with the query
            self.current_frame._temp_selected_db = db_conn
            self.current_frame._new_query_tab()

            if self.current_frame.query_tabs:
                current_tab = self.current_frame.query_tabs[-1]

                # Load query text
                current_tab.query_text.delete(1.0, tk.END)
                current_tab.query_text.insert(1.0, query_text)

                # Execute query after UI updates
                current_tab.frame.after(100, current_tab._execute_query)
                logger.info(f"Executing table query: {query_text[:50]}...")

    def _log(self, message: str, tag: str = None):
        """Add message to log"""
        if self.log_text is None:
            return

        self.log_text.configure(state=tk.NORMAL)
        if tag:
            self.log_text.insert(tk.END, message + "\n", tag)
        else:
            self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _log_from_logger(self, level: LogLevel, timestamp: str, message: str):
        """Callback method for logger integration"""
        if not self.log_filters[level].get():
            return

        formatted_message = f"[{timestamp}] [{level.value:10}] {message}"
        self.root.after(0, self._log, formatted_message, level.value)

    def _clear_log(self):
        """Clear log content"""
        if self.log_text is None:
            return

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _update_menu_state(self, enabled: bool):
        """Enable or disable menu items during processing"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.scripts_menu.entryconfig("📥 Dispatch Files", state=state)
        self.scripts_menu.entryconfig("📤 Load to Database", state=state)

    def _new_database_connection(self):
        """Show dialog for new database connection"""
        dialog = ConnectionDialog(self.root)
        result = dialog.show()

        if result:
            # Refresh database manager if it's the current frame
            if isinstance(self.current_frame, DatabaseManager):
                self.current_frame._load_all_connections()

            logger.important(f"Created new connection: {result.name}")

    def _manage_connections(self):
        """Show connections management dialog"""
        manage_window = tk.Toplevel(self.root)
        manage_window.title("Manage Database Connections")
        manage_window.geometry("900x500")
        manage_window.transient(self.root)

        # Title
        ttk.Label(
            manage_window,
            text="Database Connections",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        # Treeview for connections
        tree_frame = ttk.Frame(manage_window, padding="10")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Type", "Name", "Description")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        tree.heading("Type", text="Type")
        tree.heading("Name", text="Name")
        tree.heading("Description", text="Description")

        tree.column("Type", width=150)
        tree.column("Name", width=250)
        tree.column("Description", width=400)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.config(yscrollcommand=scrollbar.set)

        def refresh_list():
            """Refresh connections list"""
            tree.delete(*tree.get_children())
            for conn in connections_manager.get_all_connections():
                icon = ConnectionsManager.get_db_type_icon(conn.db_type)
                tree.insert("", tk.END, values=(icon, conn.name, conn.description), tags=(conn.id,))

        refresh_list()

        # Buttons
        button_frame = ttk.Frame(manage_window)
        button_frame.pack(pady=10)

        def add_connection():
            dialog = ConnectionDialog(manage_window)
            result = dialog.show()
            if result:
                refresh_list()
                # Refresh database manager if it's the current frame
                if isinstance(self.current_frame, DatabaseManager):
                    self.current_frame._load_all_connections()

        def edit_connection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a connection to edit")
                return

            conn_id = tree.item(selection[0])['tags'][0]
            conn = connections_manager.get_connection(conn_id)

            if conn:
                dialog = ConnectionDialog(manage_window, conn)
                result = dialog.show()
                if result:
                    refresh_list()
                    # Refresh database manager if it's the current frame
                    if isinstance(self.current_frame, DatabaseManager):
                        self.current_frame._load_all_connections()

        def delete_connection():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a connection to delete")
                return

            conn_id = tree.item(selection[0])['tags'][0]
            conn = connections_manager.get_connection(conn_id)

            if conn:
                if messagebox.askyesno("Confirm Delete", f"Delete connection '{conn.name}'?"):
                    connections_manager.delete_connection(conn_id)
                    refresh_list()
                    # Refresh database manager if it's the current frame
                    if isinstance(self.current_frame, DatabaseManager):
                        self.current_frame._load_all_connections()
                    logger.info(f"Deleted connection: {conn.name}")

        ttk.Button(button_frame, text="Add", command=add_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit", command=edit_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete", command=delete_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=manage_window.destroy).pack(side=tk.LEFT, padx=5)

    def _show_documentation(self):
        """Show documentation viewer"""
        show_help(self.root)

    def _show_preferences(self):
        """Show preferences dialog"""
        PreferencesDialog(self.root)

    def _apply_theme(self):
        """Apply current theme to GUI elements"""
        theme = self.theme_manager.get_current_theme()

        # ===== Apply to root window =====
        try:
            self.root.configure(bg=theme.get('bg'))
        except Exception as e:
            pass  # Silently fail if theme application fails

        # ===== Customize Windows title bar (Windows 11/10) =====
        try:
            import platform
            if platform.system() == 'Windows':
                try:
                    import ctypes
                    # Get the window handle
                    hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())

                    # Convert hex color to BGR integer
                    def hex_to_bgr(hex_color):
                        hex_color = hex_color.lstrip('#')
                        r = int(hex_color[0:2], 16)
                        g = int(hex_color[2:4], 16)
                        b = int(hex_color[4:6], 16)
                        return b | (g << 8) | (r << 16)

                    # Windows 11 dark mode support
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    DWMWA_CAPTION_COLOR = 35
                    DWMWA_TEXT_COLOR = 36

                    # Detect if theme is dark
                    is_dark = theme.get('bg').lower() in ['#2b2b2b', '#1e1e1e', '#000000'] or \
                              int(theme.get('bg').lstrip('#'), 16) < 0x808080

                    # Enable dark mode
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd,
                        DWMWA_USE_IMMERSIVE_DARK_MODE,
                        ctypes.byref(ctypes.c_int(1 if is_dark else 0)),
                        ctypes.sizeof(ctypes.c_int)
                    )

                    # Set title bar background color
                    title_bg = hex_to_bgr(theme.get('header_bg'))
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd,
                        DWMWA_CAPTION_COLOR,
                        ctypes.byref(ctypes.c_int(title_bg)),
                        ctypes.sizeof(ctypes.c_int)
                    )

                    # Set title bar text color
                    title_fg = hex_to_bgr(theme.get('header_fg'))
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd,
                        DWMWA_TEXT_COLOR,
                        ctypes.byref(ctypes.c_int(title_fg)),
                        ctypes.sizeof(ctypes.c_int)
                    )

                    pass  # Title bar customized successfully
                except Exception as e:
                    pass  # Title bar customization failed
        except Exception as e:
            pass  # Platform-specific customization not available

        # ===== Apply to toolbar frame =====
        try:
            # Configure ttk styles for toolbar
            style = ttk.Style()
            style.configure('Toolbar.TFrame', background=theme.get('toolbar_bg'))
            self.toolbar_frame.configure(style='Toolbar.TFrame')
        except Exception as e:
            pass  # Silently fail

        # ===== Apply to toolbar buttons =====
        for btn_id, btn in self.toolbar_buttons.items():
            try:
                btn.config(
                    bg=theme.get('button_bg'),
                    fg=theme.get('button_fg'),
                    activebackground=theme.get('button_active_bg'),
                    activeforeground=theme.get('button_active_fg')
                )
            except Exception as e:
                pass  # Silently fail

        # ===== Apply to main container =====
        try:
            style = ttk.Style()
            style.configure('TFrame', background=theme.get('frame_bg'))
            if hasattr(self, 'container'):
                self.container.configure(style='TFrame')
        except Exception as e:
            pass  # Silently fail

        # ===== Apply to menubar (limited support in tkinter) =====
        try:
            self.menubar.configure(
                bg=theme.get('header_bg'),
                fg=theme.get('header_fg'),
                activebackground=theme.get('select_bg'),
                activeforeground=theme.get('select_fg')
            )
        except Exception as e:
            pass  # Silently fail

        # ===== Apply to all menus =====
        for menu_attr in ['data_menu', 'scripts_menu', 'databases_menu', 'jobs_menu']:
            try:
                if hasattr(self, menu_attr):
                    menu = getattr(self, menu_attr)
                    menu.configure(
                        bg=theme.get('bg'),
                        fg=theme.get('fg'),
                        activebackground=theme.get('select_bg'),
                        activeforeground=theme.get('select_fg')
                    )
            except Exception as e:
                pass  # Silently fail

        # ===== Apply global ttk styles =====
        try:
            style = ttk.Style()

            # Choose ttk theme based on background brightness
            bg_brightness = int(theme.get('bg').lstrip('#'), 16)
            if bg_brightness < 0x808080:
                # Dark theme - use 'alt' or 'clam'
                try:
                    style.theme_use('clam')
                except:
                    style.theme_use('default')
            else:
                # Light theme
                try:
                    style.theme_use('clam')
                except:
                    style.theme_use('default')

            # Frame styles
            style.configure('TFrame', background=theme.get('frame_bg'))
            style.configure('Panel.TFrame', background=theme.get('panel_bg'))
            style.configure('Sidebar.TFrame', background=theme.get('sidebar_bg'))
            style.configure('Content.TFrame', background=theme.get('content_frame_bg'))

            # Label styles
            style.configure('TLabel', background=theme.get('bg'), foreground=theme.get('fg'))
            style.configure('Header.TLabel', background=theme.get('header_bg'), foreground=theme.get('header_fg'))

            # Button styles with proper state mapping
            style.configure('TButton',
                background=theme.get('button_bg'),
                foreground=theme.get('button_fg'),
                bordercolor=theme.get('button_bg'),
                lightcolor=theme.get('button_bg'),
                darkcolor=theme.get('button_bg'))
            style.map('TButton',
                background=[
                    ('active', theme.get('button_active_bg')),
                    ('pressed', theme.get('button_active_bg')),
                    ('disabled', theme.get('disabled_bg'))
                ],
                foreground=[
                    ('active', theme.get('button_active_fg')),
                    ('pressed', theme.get('button_active_fg')),
                    ('disabled', theme.get('disabled_fg'))
                ])

            # Entry styles
            style.configure('TEntry',
                fieldbackground=theme.get('input_bg'),
                foreground=theme.get('input_fg'),
                bordercolor=theme.get('input_border'),
                lightcolor=theme.get('input_border'),
                darkcolor=theme.get('input_border'))
            style.map('TEntry',
                fieldbackground=[
                    ('readonly', theme.get('disabled_bg')),
                    ('disabled', theme.get('disabled_bg'))
                ],
                foreground=[
                    ('disabled', theme.get('disabled_fg'))
                ])

            # Combobox styles
            style.configure('TCombobox',
                fieldbackground=theme.get('input_bg'),
                background=theme.get('button_bg'),
                foreground=theme.get('input_fg'),
                bordercolor=theme.get('input_border'),
                arrowcolor=theme.get('fg'))
            style.map('TCombobox',
                fieldbackground=[
                    ('readonly', theme.get('input_bg')),
                    ('disabled', theme.get('disabled_bg'))
                ],
                selectbackground=[('readonly', theme.get('select_bg'))],
                selectforeground=[('readonly', theme.get('select_fg'))],
                foreground=[('disabled', theme.get('disabled_fg'))])

            # Notebook (tabs) styles
            style.configure('TNotebook',
                background=theme.get('bg'),
                bordercolor=theme.get('input_border'))
            style.configure('TNotebook.Tab',
                background=theme.get('button_bg'),
                foreground=theme.get('fg'),
                bordercolor=theme.get('input_border'))
            style.map('TNotebook.Tab',
                background=[
                    ('selected', theme.get('select_bg')),
                    ('active', theme.get('hover_bg'))
                ],
                foreground=[
                    ('selected', theme.get('select_fg')),
                    ('active', theme.get('hover_fg'))
                ])

            # Scrollbar styles
            style.configure('TScrollbar',
                background=theme.get('scrollbar_bg'),
                troughcolor=theme.get('scrollbar_bg'),
                bordercolor=theme.get('scrollbar_bg'),
                arrowcolor=theme.get('fg'))
            style.map('TScrollbar',
                background=[('active', theme.get('scrollbar_fg'))])

            # PanedWindow styles (resize bars)
            style.configure('TPanedwindow',
                background=theme.get('paned_sash_bg'))

            # Checkbutton and Radiobutton styles
            style.configure('TCheckbutton',
                background=theme.get('bg'),
                foreground=theme.get('fg'))
            style.configure('TRadiobutton',
                background=theme.get('bg'),
                foreground=theme.get('fg'))

        except Exception as e:
            pass  # Silently fail

        # ===== Notify current frame to update theme =====
        if self.current_frame and hasattr(self.current_frame, 'apply_theme'):
            try:
                self.current_frame.apply_theme()
            except Exception as e:
                logger.error(f"Error applying theme to current frame: {e}")

        logger.info(f"Theme applied: {self.theme_manager.get_current_theme_name()}")

    def _apply_language(self):
        """Apply current language to GUI elements"""
        # Update toolbar button labels
        if hasattr(self, 'toolbar_buttons'):
            for btn_id, btn in self.toolbar_buttons.items():
                try:
                    if btn_id == 'data_explorer':
                        btn.config(text=f"📂 {self.i18n.t('btn_data_explorer')}")
                    elif btn_id == 'databases':
                        btn.config(text=f"🗄️ {self.i18n.t('btn_databases')}")
                except Exception as e:
                    logger.error(f"Error updating toolbar button {btn_id}: {e}")

        # Update status bar (only if not showing update notification and no update scheduled)
        if hasattr(self, 'status_label') and self.update_info is None and not self.update_on_quit:
            try:
                self.status_label.config(
                    text=self.i18n.t('status_version_up_to_date'),
                    font=("TkDefaultFont", 9, "normal")
                )
            except Exception as e:
                logger.error(f"Error updating status bar: {e}")

        # Notify current frame to update language if supported
        if self.current_frame and hasattr(self.current_frame, 'apply_language'):
            try:
                self.current_frame.apply_language()
            except Exception as e:
                logger.error(f"Error applying language to frame: {e}")

        logger.info(f"Language applied: {self.i18n.get_current_language()}")

    def _show_about(self):
        """Show about dialog"""
        about_text = f"""{APP_NAME}

Version: {APP_VERSION}

{APP_DESCRIPTION}

Features:
- Multi-database support (SQL Server, SQLite, PostgreSQL)
- Advanced SQL formatter with 4 styles
- Database query manager (SSMS-like interface)
- Project and query organization
- Theme customization
- Internationalization support

© 2024-2025"""
        messagebox.showinfo("About", about_text)

    def _check_for_updates_startup(self):
        """Check for updates at startup (with cooldown)"""
        update_checker = get_update_checker()

        # Check if we should check (respects 24h cooldown)
        if not update_checker.should_check():
            return

        # Check for updates in background thread
        threading.Thread(target=self._check_updates_thread, daemon=True).start()

    def _check_for_updates_manual(self):
        """Manual update check from menu (ignores cooldown)"""
        # Check for updates in background thread
        threading.Thread(target=self._check_updates_thread, args=(True,), daemon=True).start()

    def _check_updates_thread(self, is_manual=False):
        """Background thread to check for updates"""
        update_checker = get_update_checker()

        try:
            update_info = update_checker.check_for_update()

            if update_info:
                version, url, notes = update_info
                # Schedule UI update in main thread
                self.root.after(0, lambda: self._show_update_notification(version, url, notes))
            elif is_manual:
                # Manual check with no update found
                self.root.after(0, lambda: messagebox.showinfo(
                    "No Updates",
                    f"You are using the latest version ({APP_VERSION})"
                ))
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            if is_manual:
                self.root.after(0, lambda: messagebox.showerror(
                    "Update Check Failed",
                    f"Could not check for updates:\n{str(e)}"
                ))

    def _show_update_notification(self, version, url, notes):
        """Show update notification in status bar"""
        # Store update info
        self.update_info = (version, url, notes)

        # Update status bar with dark green bold text
        update_text = f"⚠️  Version {version} available (click for details)"
        self.status_label.config(
            text=update_text,
            foreground="#006400",  # Dark green
            font=("TkDefaultFont", 9, "bold"),
            cursor="hand2"
        )

        # Make label clickable
        self.status_label.bind("<Button-1>", lambda e: self._show_update_details())

        logger.info(f"Update notification displayed: v{version}")

    def _show_update_details(self):
        """Show update details dialog"""
        if not self.update_info:
            return

        version, url, notes = self.update_info

        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Update Available - v{version}")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()

        # Main frame
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text=f"🎉 New Version Available!",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Version info
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=10)

        ttk.Label(info_frame, text="Current Version:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Label(info_frame, text=APP_VERSION).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(info_frame, text="Latest Version:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Label(info_frame, text=version, foreground="green").grid(row=1, column=1, sticky=tk.W, padx=5)

        # Release notes
        notes_frame = ttk.LabelFrame(main_frame, text="What's New", padding="10")
        notes_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        notes_text = scrolledtext.ScrolledText(notes_frame, wrap=tk.WORD, height=10)
        notes_text.pack(fill=tk.BOTH, expand=True)
        notes_text.insert(1.0, notes if notes else "No release notes available.")
        notes_text.config(state=tk.DISABLED)

        # Instructions
        instructions_frame = ttk.LabelFrame(main_frame, text="How to Update", padding="10")
        instructions_frame.pack(fill=tk.X, pady=10)

        instructions = """To update DataForge Studio:

🚀 Quick Update (Recommended):
1. Close this application
2. Open a terminal in the project directory
3. Run: uv run run.py --update
4. Restart DataForge Studio

📝 Manual Update:
1. Close this application
2. Open a terminal in the project directory
3. Run: git pull
4. Run: uv sync
5. Restart DataForge Studio"""

        instructions_label = ttk.Label(instructions_frame, text=instructions, justify=tk.LEFT)
        instructions_label.pack()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        def open_github():
            import webbrowser
            webbrowser.open(url)

        def update_on_quit():
            self.update_on_quit = True
            # Reset status bar with update pending message
            self.status_label.config(
                text=f"⏳ {self.i18n.t('status_update_on_quit')}",
                foreground="#006400",
                font=("TkDefaultFont", 9, "bold"),
                cursor=""
            )
            self.status_label.unbind("<Button-1>")
            dialog.destroy()
            logger.info("Update scheduled for application quit")

        def remind_later():
            update_checker = get_update_checker()
            update_checker.dismiss_update()
            # Reset status bar
            self.status_label.config(text=self.i18n.t('status_version_up_to_date'), foreground="black", font=("TkDefaultFont", 9, "normal"), cursor="")
            self.status_label.unbind("<Button-1>")
            self.update_info = None
            dialog.destroy()
            logger.info("Update reminder dismissed for 24 hours")

        ttk.Button(button_frame, text="🌐 View on GitHub", command=open_github).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🚀 Update on Quit", command=update_on_quit).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="⏰ Remind Tomorrow", command=remind_later).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _on_closing(self):
        """Handle window close event"""
        if self.update_on_quit:
            logger.info("Launching update process before quit...")

            # Launch update script in a new terminal window
            import subprocess
            import sys
            import os

            try:
                # Get the project directory
                project_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

                # Platform-specific terminal launch
                if sys.platform == 'win32':
                    # Windows: Open new CMD window with update command
                    cmd = f'cd /d "{project_dir}" && uv run run.py --update && pause'
                    subprocess.Popen(f'start cmd /k {cmd}', shell=True)
                else:
                    # Unix-like: Try to open a new terminal
                    subprocess.Popen(['x-terminal-emulator', '-e', f'cd "{project_dir}" && uv run run.py --update'])

                logger.info("Update process launched successfully")
            except Exception as e:
                logger.error(f"Failed to launch update process: {e}")
                messagebox.showerror(
                    "Update Error",
                    f"Could not launch update process:\n{str(e)}\n\nPlease run manually:\nuv run run.py --update"
                )

        # Close the application
        self.root.quit()


def main():
    """Main entry point for GUI"""
    root = tk.Tk()
    app = DataLakeLoaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
