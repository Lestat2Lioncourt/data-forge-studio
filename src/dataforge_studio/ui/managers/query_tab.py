"""
Query Tab - Single SQL query editor tab for DatabaseManager

Supports multiple SQL statements with results in separate tabs (SSMS-style).

Implementation split into mixins in query/ subpackage:
- QueryCompletionMixin: SQL auto-completion
- QueryResultTabsMixin: Result tab management
- QueryDataLoadingMixin: Background data loading
- QueryConnectionMixin: Connection management
- QueryExecutionMixin: Query execution
- QueryToolbarMixin: Toolbar actions, formatting, save
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union, List, Any
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QPushButton, QLabel, QSplitter, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
try:
    import pyodbc
except ImportError:
    pyodbc = None
import sqlite3

from ..widgets.custom_datagridview import CustomDataGridView
from ..core.i18n_bridge import tr
from ...database.config_db import DatabaseConnection
from ...utils.sql_highlighter import SQLHighlighter
from ...utils.schema_cache import SchemaCache
from ...config.user_preferences import UserPreferences
from .query_loader import BackgroundRowLoader
from .query import (
    QueryCompletionMixin,
    QueryResultTabsMixin,
    QueryDataLoadingMixin,
    QueryConnectionMixin,
    QueryExecutionMixin,
    QueryToolbarMixin,
)

import logging

logger = logging.getLogger(__name__)


@dataclass
class ResultTabState:
    """State for a single results tab in multi-statement execution."""
    grid: CustomDataGridView
    statement_index: int = 0
    cursor: Optional[Any] = None
    background_loader: Optional[BackgroundRowLoader] = None
    total_rows_fetched: int = 0
    total_rows_expected: Optional[int] = None
    has_more_rows: bool = False
    is_loading: bool = False
    columns: List[str] = field(default_factory=list)


class QueryTab(
    QueryCompletionMixin,
    QueryResultTabsMixin,
    QueryDataLoadingMixin,
    QueryConnectionMixin,
    QueryExecutionMixin,
    QueryToolbarMixin,
    QWidget,
):
    """Single SQL query editor tab"""

    # Signal emitted when tab requests to be closed
    close_requested = Signal()
    # Signal emitted when a query is saved to saved queries
    query_saved = Signal()

    def cleanup(self):
        """Stop background tasks and cleanup resources"""
        try:
            # Stop all result tab loaders
            result_tabs = getattr(self, '_result_tabs', [])
            for tab_state in result_tabs:
                loader = tab_state.background_loader
                if loader is not None:
                    try:
                        loader.batch_loaded.disconnect()
                        loader.loading_complete.disconnect()
                        loader.loading_error.disconnect()
                    except (RuntimeError, TypeError):
                        pass
                    if loader.isRunning():
                        loader.stop()
                        if not loader.wait(20):
                            loader.terminate()

            # Also handle legacy single loader if exists
            loader = getattr(self, '_background_loader', None)
            if loader is not None:
                try:
                    loader.batch_loaded.disconnect()
                    loader.loading_complete.disconnect()
                    loader.loading_error.disconnect()
                except (RuntimeError, TypeError):
                    pass
                if loader.isRunning():
                    loader.stop()
                    if not loader.wait(20):
                        loader.terminate()
                self._background_loader = None
        except (RuntimeError, AttributeError):
            # Object may be partially destroyed during shutdown
            pass

    def closeEvent(self, event):
        """Handle close event"""
        self.cleanup()
        super().closeEvent(event)

    def __init__(self, parent: Optional[QWidget] = None,
                 connection: Union[pyodbc.Connection, sqlite3.Connection] = None,
                 db_connection: DatabaseConnection = None,
                 tab_name: str = "Query",
                 database_manager=None,
                 target_database: str = None,
                 workspace_id: str = None,
                 saved_query=None):
        """
        Initialize query tab.

        Args:
            parent: Parent widget
            connection: Database connection
            db_connection: Database connection config
            tab_name: Name of the tab
            database_manager: Reference to parent DatabaseManager for reconnection
            target_database: Target database name for SQL Server (to select in combo)
            workspace_id: Optional workspace ID to auto-link saved queries
            saved_query: Optional SavedQuery object (for update-on-save instead of create)
        """
        super().__init__(parent)

        self.connection = connection
        self.db_connection = db_connection
        self.tab_name = tab_name
        self._database_manager = database_manager
        self._target_database = target_database  # Database to select initially
        self._workspace_id = workspace_id  # Auto-link queries to this workspace
        self._saved_query = saved_query  # If set, save will UPDATE instead of INSERT
        self.is_sqlite = isinstance(connection, sqlite3.Connection)
        # Use db_type from connection config, fallback to detection
        if db_connection and hasattr(db_connection, 'db_type'):
            self.db_type = db_connection.db_type
        else:
            self.db_type = "sqlite" if self.is_sqlite else "sqlserver"

        # Query state
        self.original_query = ""
        self.active_sorts = []
        self.current_columns = []
        self.current_database = None  # Current database context

        # Batch loading settings
        self.batch_size = 1000  # Rows per batch
        self.total_rows_fetched = 0
        self.total_rows_expected = None  # Total rows if known (from COUNT)
        self.has_more_rows = False
        self._cursor = None  # Keep cursor for loading more
        self._background_loader = None  # Background loading thread
        self._is_loading = False  # Loading state
        self._loading_start_time = None  # Track loading duration

        # Auto-completion
        self.schema_cache = SchemaCache()
        self._completer_prefix = ""  # Text being completed

        self._setup_ui()
        self._setup_completer()
        self._load_connections()
        self._load_databases()

        # Auto-refresh connection list when connections change
        if self._database_manager and hasattr(self._database_manager, 'connections_changed'):
            self._database_manager.connections_changed.connect(self._load_connections)

    def _setup_ui(self):
        """Setup UI components"""
        from PySide6.QtWidgets import QGroupBox

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Top toolbar - with GroupBox containers
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # === Connection GroupBox ===
        conn_group = QGroupBox("Connection")
        conn_layout = QHBoxLayout(conn_group)
        conn_layout.setContentsMargins(5, 2, 5, 5)

        self.conn_combo = QComboBox()
        self.conn_combo.setMinimumWidth(150)
        self.conn_combo.setToolTip("Select database connection")
        self.conn_combo.currentIndexChanged.connect(self._on_connection_changed)
        conn_layout.addWidget(self.conn_combo)

        toolbar.addWidget(conn_group)

        # === Database GroupBox ===
        db_group = QGroupBox(tr("field_database").rstrip(" :"))
        db_layout = QHBoxLayout(db_group)
        db_layout.setContentsMargins(5, 2, 5, 5)

        self.db_combo = QComboBox()
        self.db_combo.setMinimumWidth(150)
        self.db_combo.setToolTip(tr("query_tooltip_select_db"))
        self.db_combo.currentTextChanged.connect(self._on_database_changed)
        db_layout.addWidget(self.db_combo)

        toolbar.addWidget(db_group)

        # === Execute GroupBox ===
        exec_group = QGroupBox(tr("query_toolbar_execute"))
        exec_layout = QHBoxLayout(exec_group)
        exec_layout.setContentsMargins(5, 2, 5, 5)
        exec_layout.setSpacing(4)

        self.execute_combo = QComboBox()
        self.execute_combo.addItem(tr("query_execute_auto"), "auto")
        self.execute_combo.addItem(tr("query_execute_query"), "query")
        self.execute_combo.addItem(tr("query_execute_script"), "script")
        self.execute_combo.setToolTip(tr("query_execute_auto_tooltip"))
        self.execute_combo.setMinimumWidth(100)
        self.execute_combo.currentIndexChanged.connect(self._on_execute_mode_changed)
        exec_layout.addWidget(self.execute_combo)

        self.run_btn = QPushButton(tr("query_btn_run"))
        self.run_btn.setToolTip(tr("query_execute_query_tooltip"))
        self.run_btn.clicked.connect(self._run_execute)
        self.run_btn.setShortcut("F5")
        self.run_btn.setFixedSize(40, 28)
        self.run_btn.setStyleSheet("font-weight: bold; font-size: 16px;")
        exec_layout.addWidget(self.run_btn)

        toolbar.addWidget(exec_group)

        # === Format GroupBox ===
        format_group = QGroupBox(tr("query_toolbar_format"))
        format_layout = QHBoxLayout(format_group)
        format_layout.setContentsMargins(5, 2, 5, 5)
        format_layout.setSpacing(4)

        self.format_combo = QComboBox()
        self.format_combo.addItem(tr("query_format_compact"), "compact")
        self.format_combo.addItem(tr("query_format_expanded"), "expanded")
        self.format_combo.addItem(tr("query_format_comma_first"), "comma_first")
        self.format_combo.addItem(tr("query_format_ultimate"), "ultimate")
        self.format_combo.setMinimumWidth(100)
        # Load saved format preference
        prefs = UserPreferences.instance()
        saved_format = prefs.get("sql_format_style", "expanded")
        for i in range(self.format_combo.count()):
            if self.format_combo.itemData(i) == saved_format:
                self.format_combo.setCurrentIndex(i)
                break
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_combo)

        self.format_btn = QPushButton()
        self.format_btn.setToolTip(tr("format_sql"))
        self.format_btn.clicked.connect(self._run_format)
        self.format_btn.setFixedSize(40, 28)
        # Load themed Format icon
        format_icon_path = self._get_themed_icon("Format.png")
        if format_icon_path:
            self.format_btn.setIcon(QIcon(str(format_icon_path)))
        else:
            self.format_btn.setText(tr("query_btn_format"))
        format_layout.addWidget(self.format_btn)

        toolbar.addWidget(format_group)

        # === Export button (standalone, opens dialog with language choice) ===
        self.export_btn = QPushButton()
        self.export_btn.setToolTip(tr("query_toolbar_export"))
        self.export_btn.clicked.connect(self._run_export)
        self.export_btn.setFixedHeight(40)
        # Use {/} text symbol for code export
        self.export_btn.setText("{ / }")
        self.export_btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 0 8px;")
        toolbar.addWidget(self.export_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        toolbar.addStretch()

        # === Save button (standalone) ===
        self.save_query_btn = QPushButton("\U0001f4be")
        self.save_query_btn.setToolTip(tr("query_save_to_queries"))
        self.save_query_btn.clicked.connect(self._save_query)
        self.save_query_btn.setFixedWidth(40)
        self.save_query_btn.setFixedHeight(40)
        toolbar.addWidget(self.save_query_btn)

        layout.addLayout(toolbar)

        # Splitter for SQL editor (top) and results (bottom)
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # SQL Editor
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText("-- " + tr("enter_sql_query_here"))
        self.sql_editor.setFont(QFont("Consolas", 10))
        # Colors are managed by the theme system and SQLHighlighter

        # Apply SQL syntax highlighting
        self.sql_highlighter = SQLHighlighter(self.sql_editor.document())

        self.splitter.addWidget(self.sql_editor)

        # Results panel
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # Result info bar with label and control buttons
        result_bar = QHBoxLayout()

        self.result_info_label = QLabel(tr("query_no_executed"))
        self.result_info_label.setStyleSheet("color: gray;")
        result_bar.addWidget(self.result_info_label)

        result_bar.addStretch()

        # Stop loading button (visible during background loading)
        self.stop_loading_btn = QPushButton(tr("query_stop"))
        self.stop_loading_btn.clicked.connect(self._stop_all_background_loading)
        self.stop_loading_btn.setVisible(False)
        result_bar.addWidget(self.stop_loading_btn)

        # Load more button (visible when background loading is stopped/paused)
        self.load_more_btn = QPushButton(tr("query_load_more"))
        self.load_more_btn.clicked.connect(self._load_more_rows)
        self.load_more_btn.setVisible(False)
        result_bar.addWidget(self.load_more_btn)

        results_layout.addLayout(result_bar)

        # EditableTabWidget for multiple result sets (SSMS-style)
        from ..widgets.editable_tab_widget import EditableTabWidget
        self.results_tab_widget = EditableTabWidget()
        self.results_tab_widget.setTabsClosable(False)
        self.results_tab_widget.setDocumentMode(True)
        self.results_tab_widget.set_protected_suffix_tabs(1)  # Messages tab
        results_layout.addWidget(self.results_tab_widget)

        # Messages tab (always present, last tab)
        self._messages_text = QTextEdit()
        self._messages_text.setReadOnly(True)
        self._messages_text.setFont(QFont("Consolas", 9))
        self.results_tab_widget.addTab(self._messages_text, tr("query_messages_tab"))

        # Track result tab states
        self._result_tabs: List[ResultTabState] = []

        # Legacy compatibility: results_grid points to first result tab's grid (or None)
        self.results_grid = None

        self.splitter.addWidget(results_widget)

        # Set splitter proportions (default values)
        self.splitter.setSizes([300, 400])

        # Restore saved splitter sizes from preferences
        self._restore_splitter_sizes()

        # Save splitter sizes when changed
        self.splitter.splitterMoved.connect(self._save_splitter_sizes)

        layout.addWidget(self.splitter)

    def _restore_splitter_sizes(self):
        """Restore splitter sizes from user preferences."""
        try:
            prefs = UserPreferences.instance()
            saved_sizes = prefs.get("query_tab_splitter_sizes")
            if saved_sizes:
                # Parse "300,400" format
                sizes = [int(s) for s in saved_sizes.split(",")]
                if len(sizes) == 2 and all(s > 0 for s in sizes):
                    self.splitter.setSizes(sizes)
        except Exception as e:
            pass  # Silently ignore - use defaults

    def _save_splitter_sizes(self):
        """Save splitter sizes to user preferences."""
        try:
            sizes = self.splitter.sizes()
            if sizes and len(sizes) == 2:
                prefs = UserPreferences.instance()
                prefs.set("query_tab_splitter_sizes", f"{sizes[0]},{sizes[1]}")
        except Exception:
            pass  # Silently ignore

    @staticmethod
    def _get_themed_icon(icon_name: str):
        """Get themed icon path using the theme bridge system."""
        try:
            from ..core.theme_bridge import ThemeBridge
            from ..core.theme_image_generator import get_themed_icon_path
            bridge = ThemeBridge.get_instance()
            colors = bridge.get_theme_colors(bridge.current_theme)
            icon_color = colors.get('icon_color', colors.get('text_primary', '#e0e0e0'))
            is_dark = colors.get('is_dark', True)
            return get_themed_icon_path(icon_name, is_dark, icon_color)
        except Exception:
            return None
