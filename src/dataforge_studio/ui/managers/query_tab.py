"""
Query Tab - Single SQL query editor tab for DatabaseManager

Supports multiple SQL statements with results in separate tabs (SSMS-style).
"""

from dataclasses import dataclass, field
from typing import Optional, Union, Tuple, List, Any
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QPushButton, QLabel, QSplitter, QComboBox,
                               QTableWidgetItem, QApplication, QDialog,
                               QTabWidget)
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QTimer
from PySide6.QtGui import QFont, QKeyEvent
import pyodbc
import sqlite3
import re

from ..widgets.custom_datagridview import CustomDataGridView
from ..widgets.sql_completer import SQLCompleterPopup
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from ...database.config_db import DatabaseConnection
from ...utils.sql_highlighter import SQLHighlighter
from ...utils.schema_cache import SchemaCache
from ...utils.sql_formatter import format_sql
from ...utils.sql_splitter import split_sql_statements, SQLStatement
from .query_loader import BackgroundRowLoader

# DataFrame-Pivot pattern: use shared threshold
from ...core.data_loader import LARGE_DATASET_THRESHOLD

import logging
import time

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


class QueryTab(QWidget):
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
                 target_database: str = None):
        """
        Initialize query tab.

        Args:
            parent: Parent widget
            connection: Database connection
            db_connection: Database connection config
            tab_name: Name of the tab
            database_manager: Reference to parent DatabaseManager for reconnection
            target_database: Target database name for SQL Server (to select in combo)
        """
        super().__init__(parent)

        self.connection = connection
        self.db_connection = db_connection
        self.tab_name = tab_name
        self._database_manager = database_manager
        self._target_database = target_database  # Database to select initially
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
        self._load_databases()

    def _setup_ui(self):
        """Setup UI components"""
        from PySide6.QtWidgets import QGroupBox

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Top toolbar - with GroupBox containers
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

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
        self.execute_combo.addItem(tr("query_execute_query"), "query")
        self.execute_combo.addItem(tr("query_execute_script"), "script")
        self.execute_combo.setToolTip(tr("query_execute_query_tooltip"))
        self.execute_combo.setMinimumWidth(100)
        self.execute_combo.currentIndexChanged.connect(self._on_execute_mode_changed)
        exec_layout.addWidget(self.execute_combo)

        self.run_btn = QPushButton(tr("query_btn_run"))
        self.run_btn.setToolTip(tr("query_execute_query_tooltip"))
        self.run_btn.clicked.connect(self._run_execute)
        self.run_btn.setShortcut("F5")
        self.run_btn.setFixedWidth(35)
        self.run_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
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
        format_layout.addWidget(self.format_combo)

        self.format_btn = QPushButton(tr("query_btn_format"))
        self.format_btn.setToolTip(tr("format_sql"))
        self.format_btn.clicked.connect(self._run_format)
        self.format_btn.setFixedWidth(35)
        format_layout.addWidget(self.format_btn)

        toolbar.addWidget(format_group)

        # === Export GroupBox ===
        export_group = QGroupBox(tr("query_toolbar_export"))
        export_layout = QHBoxLayout(export_group)
        export_layout.setContentsMargins(5, 2, 5, 5)
        export_layout.setSpacing(4)

        self.export_combo = QComboBox()
        self.export_combo.addItem("Python", "python")
        self.export_combo.addItem("T-SQL", "tsql")
        self.export_combo.addItem("VB", "vb")
        self.export_combo.addItem("C#", "csharp")
        self.export_combo.setMinimumWidth(80)
        export_layout.addWidget(self.export_combo)

        self.export_btn = QPushButton(tr("query_btn_export"))
        self.export_btn.setToolTip(tr("query_toolbar_export"))
        self.export_btn.clicked.connect(self._run_export)
        self.export_btn.setFixedWidth(35)
        export_layout.addWidget(self.export_btn)

        toolbar.addWidget(export_group)

        toolbar.addStretch()

        # === Save button (standalone) ===
        self.save_query_btn = QPushButton("💾")
        self.save_query_btn.setToolTip(tr("query_save_to_queries"))
        self.save_query_btn.clicked.connect(self._save_query)
        self.save_query_btn.setFixedWidth(40)
        self.save_query_btn.setFixedHeight(40)
        toolbar.addWidget(self.save_query_btn)

        layout.addLayout(toolbar)

        # Splitter for SQL editor (top) and results (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # SQL Editor
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText("-- " + tr("enter_sql_query_here"))
        self.sql_editor.setFont(QFont("Consolas", 10))
        # Colors are managed by the theme system and SQLHighlighter

        # Apply SQL syntax highlighting
        self.sql_highlighter = SQLHighlighter(self.sql_editor.document())

        splitter.addWidget(self.sql_editor)

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

        # QTabWidget for multiple result sets (SSMS-style)
        self.results_tab_widget = QTabWidget()
        self.results_tab_widget.setTabsClosable(False)
        self.results_tab_widget.setDocumentMode(True)
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

        splitter.addWidget(results_widget)

        # Set splitter proportions
        splitter.setSizes([300, 400])

        layout.addWidget(splitter)

    def _execute_as_query(self):
        """Execute as independent queries (parallel mode with separate connections).

        Each SELECT statement runs in its own connection, allowing parallel
        background loading. Best for independent queries.
        """
        query = self.sql_editor.toPlainText().strip()

        if not query:
            DialogHelper.warning(tr("no_query_to_execute"), parent=self)
            return

        if not self.connection:
            DialogHelper.error(tr("query_no_connection"), parent=self)
            return

        # Clear previous results
        self._clear_result_tabs()

        # Save original query
        self.original_query = query
        self._loading_start_time = time.time()
        self.load_more_btn.setVisible(False)
        self.stop_loading_btn.setVisible(False)

        # Split into statements
        statements = split_sql_statements(query, self.db_type)

        if not statements:
            DialogHelper.warning(tr("no_query_to_execute"), parent=self)
            return

        # Show initial status
        stmt_count = len(statements)
        self.result_info_label.setText(tr("query_executing_statements", count=stmt_count))
        self.result_info_label.setStyleSheet("color: orange;")
        QApplication.processEvents()

        # Execute each statement with its own connection for SELECT queries
        select_count = 0
        error_occurred = False

        for i, stmt in enumerate(statements):
            if error_occurred:
                break

            try:
                self._append_message(f"-- [Query] Executing statement {i+1}/{stmt_count}...")
                QApplication.processEvents()

                if stmt.is_select:
                    # SELECT: Create a new connection for parallel loading
                    select_count += 1
                    tab_name = self._generate_result_tab_name(stmt.text, select_count)
                    tab_state = self._create_result_tab(i, tab_name)

                    # Create a separate connection for this query
                    new_conn = self._create_parallel_connection()
                    if new_conn:
                        cursor = new_conn.cursor()
                        cursor.execute(stmt.text)
                        tab_state.cursor = cursor
                        # Store connection reference for cleanup
                        tab_state.grid.setProperty("_parallel_connection", new_conn)
                        self._execute_select_statement(tab_state, cursor, stmt, is_multi_statement=False)
                    else:
                        # Fallback to main connection (synchronous)
                        cursor = self.connection.cursor()
                        cursor.execute(stmt.text)
                        self._execute_select_statement(tab_state, cursor, stmt, is_multi_statement=True)

                    if select_count == 1:
                        self.results_tab_widget.setCurrentIndex(0)
                        self.results_grid = tab_state.grid
                else:
                    # Non-SELECT: use main connection
                    cursor = self.connection.cursor()
                    cursor.execute(stmt.text)
                    rows_affected = cursor.rowcount
                    self.connection.commit()
                    self._append_message(f"  → {rows_affected} row(s) affected")

            except Exception as e:
                error_occurred = True
                self._append_message(f"Error in statement {i+1}: {str(e)}", is_error=True)
                logger.error(f"Query execution error: {e}")
                messages_tab_index = self.results_tab_widget.count() - 1
                self.results_tab_widget.setCurrentIndex(messages_tab_index)
                if self._is_connection_error(e):
                    self._handle_connection_error(e)

        # Final status
        self._finalize_execution(stmt_count, select_count, error_occurred)

    def _execute_as_script(self):
        """Execute as a script (sequential mode on same connection).

        All statements run sequentially on the same connection, preserving
        session state (temp tables, variables, transactions). Best for scripts.
        """
        query = self.sql_editor.toPlainText().strip()

        if not query:
            DialogHelper.warning(tr("no_query_to_execute"), parent=self)
            return

        if not self.connection:
            DialogHelper.error(tr("query_no_connection"), parent=self)
            return

        # Clear previous results
        self._clear_result_tabs()

        # Save original query
        self.original_query = query
        self._loading_start_time = time.time()
        self.load_more_btn.setVisible(False)
        self.stop_loading_btn.setVisible(False)

        # Split into statements
        statements = split_sql_statements(query, self.db_type)

        if not statements:
            DialogHelper.warning(tr("no_query_to_execute"), parent=self)
            return

        # Show initial status
        stmt_count = len(statements)
        self.result_info_label.setText(tr("query_executing_statements", count=stmt_count))
        self.result_info_label.setStyleSheet("color: orange;")
        QApplication.processEvents()

        # Execute each statement sequentially on same connection
        select_count = 0
        error_occurred = False

        for i, stmt in enumerate(statements):
            if error_occurred:
                break

            try:
                self._append_message(f"-- [Script] Executing statement {i+1}/{stmt_count}...")
                QApplication.processEvents()

                cursor = self.connection.cursor()
                cursor.execute(stmt.text)

                if cursor.description:
                    # SELECT query - create result tab
                    select_count += 1
                    tab_name = self._generate_result_tab_name(stmt.text, select_count)
                    tab_state = self._create_result_tab(i, tab_name)

                    # Always use synchronous loading in script mode
                    self._execute_select_statement(tab_state, cursor, stmt, is_multi_statement=True)

                    if select_count == 1:
                        self.results_tab_widget.setCurrentIndex(0)
                        self.results_grid = tab_state.grid
                else:
                    # Non-SELECT statement
                    rows_affected = cursor.rowcount
                    self.connection.commit()
                    self._append_message(f"  → {rows_affected} row(s) affected")

            except Exception as e:
                error_occurred = True
                self._append_message(f"Error in statement {i+1} (line {stmt.line_start}): {str(e)}", is_error=True)
                logger.error(f"Script execution error: {e}")
                messages_tab_index = self.results_tab_widget.count() - 1
                self.results_tab_widget.setCurrentIndex(messages_tab_index)
                if self._is_connection_error(e):
                    self._handle_connection_error(e)

        # Final status
        self._finalize_execution(stmt_count, select_count, error_occurred)

    def _create_parallel_connection(self):
        """Create a new connection for parallel query execution."""
        try:
            if self.db_type == "sqlite":
                # SQLite: create new connection to same database
                conn_str = self.db_connection.connection_string
                if conn_str.startswith("sqlite:///"):
                    db_path = conn_str[10:]
                    return sqlite3.connect(db_path)
            elif self.db_type == "sqlserver":
                # SQL Server: create new pyodbc connection
                from ...utils.credential_manager import CredentialManager
                conn_str = self.db_connection.connection_string
                if "trusted_connection=yes" not in conn_str.lower():
                    username, password = CredentialManager.get_credentials(self.db_connection.id)
                    if username and password:
                        if "uid=" not in conn_str.lower():
                            if not conn_str.endswith(";"):
                                conn_str += ";"
                            conn_str += f"UID={username};PWD={password};"
                return pyodbc.connect(conn_str, timeout=5)
            # Add other database types as needed
        except Exception as e:
            logger.warning(f"Could not create parallel connection: {e}")
        return None

    def _finalize_execution(self, stmt_count: int, select_count: int, error_occurred: bool):
        """Finalize execution and update status."""
        duration = self._get_duration_str()
        if error_occurred:
            self.result_info_label.setText(f"✗ Error after {duration}")
            self.result_info_label.setStyleSheet("color: red;")
        else:
            self.result_info_label.setText(
                tr("query_completed_summary",
                   statements=stmt_count,
                   results=select_count,
                   duration=duration)
            )
            self.result_info_label.setStyleSheet("color: green;")
            self._append_message(f"\n-- Completed: {stmt_count} statement(s), {select_count} result set(s) in {duration}")

        self._update_loading_buttons()

    def _execute_select_statement(self, tab_state: ResultTabState, cursor, stmt: SQLStatement,
                                     is_multi_statement: bool = False):
        """Execute a SELECT statement and load results into its tab.

        Args:
            tab_state: The result tab state
            cursor: Database cursor with results
            stmt: The SQL statement
            is_multi_statement: If True, fetch all rows synchronously (no background loading)
                               to avoid "connection busy" errors with SQL Server
        """
        columns = [column[0] for column in cursor.description]
        tab_state.columns = columns

        # Setup grid
        tab_state.grid.set_columns(columns)
        db_name = self.current_database or (self.db_connection.name if self.db_connection else None)
        tab_state.grid.set_context(db_name=db_name, table_name=f"Query {tab_state.statement_index + 1}")

        if is_multi_statement:
            # Multi-statement mode: fetch ALL rows synchronously to free the connection
            # This is required because SQL Server doesn't support multiple active result sets
            # by default (MARS disabled)
            self._append_message(f"  → Loading results...")
            QApplication.processEvents()

            all_rows = cursor.fetchall()
            tab_state.total_rows_fetched = len(all_rows)

            # Convert to list of lists
            data = [[cell for cell in row] for row in all_rows]
            self._load_data_to_grid(tab_state.grid, data)

            self._append_message(f"  → {tab_state.total_rows_fetched:,} row(s) returned")
        else:
            # Single statement mode: use batch loading for better UX with large datasets
            rows = cursor.fetchmany(self.batch_size)
            tab_state.total_rows_fetched = len(rows)

            # Load first batch
            data = [[cell for cell in row] for row in rows]
            self._load_data_to_grid(tab_state.grid, data)

            # Check for more rows
            if len(rows) == self.batch_size:
                tab_state.cursor = cursor
                tab_state.has_more_rows = True
                self._start_background_loading_for_tab(tab_state)
                self._append_message(f"  → Loading results (first {tab_state.total_rows_fetched} rows)...")
            else:
                self._append_message(f"  → {tab_state.total_rows_fetched} row(s) returned")

    # =========================================================================
    # Result Tab Management
    # =========================================================================

    def _clear_result_tabs(self):
        """Clear all result tabs except Messages."""
        # Stop any running loaders
        for tab_state in self._result_tabs:
            if tab_state.background_loader and tab_state.background_loader.isRunning():
                tab_state.background_loader.stop()
                tab_state.background_loader.wait(100)

        # Remove all tabs except Messages (last tab)
        while self.results_tab_widget.count() > 1:
            widget = self.results_tab_widget.widget(0)
            self.results_tab_widget.removeTab(0)
            widget.deleteLater()

        self._result_tabs.clear()
        self._messages_text.clear()
        self.results_grid = None

    def _create_result_tab(self, statement_index: int, tab_name: str = None) -> ResultTabState:
        """Create a new results tab with its own grid."""
        if tab_name is None:
            tab_name = tr("query_results_tab", index=len(self._result_tabs) + 1)

        grid = CustomDataGridView(show_toolbar=True)

        tab_state = ResultTabState(
            grid=grid,
            statement_index=statement_index
        )

        # Insert before Messages tab (which is always last)
        insert_index = self.results_tab_widget.count() - 1
        self.results_tab_widget.insertTab(insert_index, grid, tab_name)

        self._result_tabs.append(tab_state)
        return tab_state

    def _append_message(self, message: str, is_error: bool = False):
        """Append a message to the Messages tab."""
        if is_error:
            self._messages_text.append(f'<span style="color: #e74c3c;">{message}</span>')
        else:
            self._messages_text.append(message)

    def _generate_result_tab_name(self, sql_text: str, index: int) -> str:
        """Generate a name for a result tab."""
        return f"Query({index})"

    def _load_data_to_grid(self, grid: CustomDataGridView, data: list):
        """Load data into a specific grid with optimizations."""
        table = grid.table
        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)
        try:
            grid.set_data(data)
        finally:
            table.setUpdatesEnabled(True)

    # =========================================================================
    # Per-Tab Background Loading
    # =========================================================================

    def _start_background_loading_for_tab(self, tab_state: ResultTabState):
        """Start background loading for a specific results tab."""
        tab_state.is_loading = True

        # Create loader for this tab
        loader = BackgroundRowLoader(tab_state.cursor, self.batch_size)
        tab_state.background_loader = loader

        # Connect signals with tab_state context using closures
        loader.batch_loaded.connect(
            lambda data, ts=tab_state: self._on_tab_batch_loaded(ts, data)
        )
        loader.loading_complete.connect(
            lambda status, ts=tab_state: self._on_tab_loading_complete(ts)
        )
        loader.loading_error.connect(
            lambda error, ts=tab_state: self._on_tab_loading_error(ts, error)
        )

        loader.start()
        self._update_loading_buttons()

    def _on_tab_batch_loaded(self, tab_state: ResultTabState, data: list):
        """Handle batch loaded for a specific tab."""
        if not data:
            return

        tab_state.total_rows_fetched += len(data)

        # Append to grid
        table = tab_state.grid.table
        table.setUpdatesEnabled(False)
        try:
            current_row = table.rowCount()
            table.setRowCount(current_row + len(data))

            for row_idx, row_data in enumerate(data):
                for col_idx, cell in enumerate(row_data):
                    item = QTableWidgetItem(str(cell) if cell is not None else "")
                    table.setItem(current_row + row_idx, col_idx, item)

            tab_state.grid.data.extend(data)
        finally:
            table.setUpdatesEnabled(True)

        self._update_overall_status()

    def _on_tab_loading_complete(self, tab_state: ResultTabState):
        """Handle loading complete for a specific tab."""
        tab_state.is_loading = False
        tab_state.has_more_rows = False
        tab_state.background_loader = None

        self._append_message(
            f"  → Statement {tab_state.statement_index + 1}: {tab_state.total_rows_fetched:,} row(s) loaded"
        )

        self._update_overall_status()
        self._update_loading_buttons()

    def _on_tab_loading_error(self, tab_state: ResultTabState, error_msg: str):
        """Handle loading error for a specific tab."""
        tab_state.is_loading = False
        tab_state.background_loader = None

        self._append_message(
            f"Error loading results for statement {tab_state.statement_index + 1}: {error_msg}",
            is_error=True
        )

        self._update_overall_status()
        self._update_loading_buttons()

    def _stop_all_background_loading(self):
        """Stop all background loading across all tabs."""
        for tab_state in self._result_tabs:
            if tab_state.background_loader and tab_state.background_loader.isRunning():
                tab_state.background_loader.stop()
                tab_state.background_loader.wait(500)
                tab_state.is_loading = False

        # Also stop legacy loader if exists
        if self._background_loader and self._background_loader.isRunning():
            self._background_loader.stop()
            self._background_loader.wait(500)

        self._update_loading_buttons()

        duration = self._get_duration_str()
        total_rows = sum(ts.total_rows_fetched for ts in self._result_tabs)
        self.result_info_label.setText(f"⏸ {total_rows:,} row(s) loaded in {duration} - Stopped")
        self.result_info_label.setStyleSheet("color: orange;")

    def _update_loading_buttons(self):
        """Update visibility of loading control buttons."""
        loading_count = sum(1 for ts in self._result_tabs if ts.is_loading)
        self.stop_loading_btn.setVisible(loading_count > 0)
        # Load more button not used in multi-tab mode for now
        self.load_more_btn.setVisible(False)

    def _update_overall_status(self):
        """Update the overall status label based on all tabs."""
        loading_count = sum(1 for ts in self._result_tabs if ts.is_loading)

        if loading_count > 0:
            total_rows = sum(ts.total_rows_fetched for ts in self._result_tabs)
            duration = self._get_duration_str()
            self.result_info_label.setText(
                f"⏳ Loading... {total_rows:,} row(s) in {duration} ({loading_count} result set(s) in progress)"
            )
            self.result_info_label.setStyleSheet("color: #3498db;")
        else:
            duration = self._get_duration_str()
            total_rows = sum(ts.total_rows_fetched for ts in self._result_tabs)
            stmt_count = len(self._result_tabs)
            self.result_info_label.setText(
                tr("query_completed_summary",
                   statements=stmt_count,
                   results=stmt_count,
                   duration=duration) + f" ({total_rows:,} rows)"
            )
            self.result_info_label.setStyleSheet("color: green;")

    def _get_query_row_count(self, query: str) -> Optional[int]:
        """
        Try to get the total row count for a SELECT query.
        Returns None if count cannot be determined.
        """
        # Clean query - remove trailing semicolons and whitespace
        clean_query = query.strip().rstrip(';').strip()
        query_upper = clean_query.upper()

        # Only try for SELECT queries
        if not query_upper.startswith("SELECT"):
            logger.debug("Count skipped: not a SELECT query")
            return None

        # Skip if query has TOP/LIMIT (count would be misleading)
        if "TOP " in query_upper or " LIMIT " in query_upper:
            logger.debug("Count skipped: query has TOP/LIMIT")
            return None

        # Skip if query has ORDER BY (SQL Server requires TOP with ORDER BY in subquery)
        # We'll remove ORDER BY for the count query
        if " ORDER BY " in query_upper:
            # Find ORDER BY position and remove it for count
            order_pos = query_upper.rfind(" ORDER BY ")
            clean_query = clean_query[:order_pos].strip()
            logger.debug("Removed ORDER BY clause for count query")

        try:
            # Wrap query in COUNT subquery
            count_query = f"SELECT COUNT(*) FROM ({clean_query}) AS count_subquery"
            logger.info(f"Counting rows with: {count_query[:150]}...")

            cursor = self.connection.cursor()
            cursor.execute(count_query)
            result = cursor.fetchone()
            cursor.close()

            if result:
                count = result[0]
                logger.info(f"Query row count: {count:,}")
                return count

        except Exception as e:
            # Count failed - not critical, we'll load without known total
            logger.warning(f"Could not get row count: {e}")

        return None

    def _handle_large_dataset_warning(self, row_count: int) -> bool:
        """
        Handle warning for large query results (> 100k rows).

        Args:
            row_count: Number of rows detected

        Returns:
            True to proceed with loading, False to cancel
        """
        from PySide6.QtWidgets import QMessageBox

        # Format numbers with thousands separator
        row_count_fmt = f"{row_count:,}"
        threshold_fmt = f"{LARGE_DATASET_THRESHOLD:,}"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Large Query Result Warning")
        msg.setText(f"This query will return {row_count_fmt} rows.")
        msg.setInformativeText(
            f"Loading more than {threshold_fmt} rows may:\n"
            f"• Be slow to load\n"
            f"• Consume significant memory\n"
            f"• Slow down the interface\n\n"
            f"Consider adding TOP/LIMIT to your query.\n\n"
            f"Do you want to continue?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        result = msg.exec()
        return result == QMessageBox.StandardButton.Yes

    def _start_background_loading(self, cursor):
        """Start background thread to load remaining rows"""
        self._is_loading = True
        self.stop_loading_btn.setVisible(True)
        self.load_more_btn.setVisible(False)

        # Update status
        self._update_loading_status()

        # Create and start background loader
        self._background_loader = BackgroundRowLoader(cursor, self.batch_size)
        self._background_loader.batch_loaded.connect(self._on_batch_loaded)
        self._background_loader.loading_complete.connect(self._on_loading_complete)
        self._background_loader.loading_error.connect(self._on_loading_error)
        self._background_loader.start()

    def _on_batch_loaded(self, data: list):
        """Handle batch of rows loaded from background thread"""
        if not data:
            return

        self.total_rows_fetched += len(data)
        self._append_data_optimized(data)
        self._update_loading_status()

    def _on_loading_complete(self, status: int):
        """Handle background loading completed"""
        self._is_loading = False
        self.has_more_rows = False
        self.stop_loading_btn.setVisible(False)
        self.load_more_btn.setVisible(False)

        duration = self._get_duration_str()

        if self.total_rows_expected:
            self.result_info_label.setText(
                f"✓ {self.total_rows_fetched:,}/{self.total_rows_expected:,} row(s) (100%) in {duration}"
            )
        else:
            self.result_info_label.setText(
                f"✓ {self.total_rows_fetched:,} row(s) loaded in {duration}"
            )
        self.result_info_label.setStyleSheet("color: green;")

        logger.info(f"Background loading complete: {self.total_rows_fetched} total rows in {duration}")

        # Cleanup
        self._background_loader = None

    def _on_loading_error(self, error_msg: str):
        """Handle background loading error"""
        self._is_loading = False
        self.stop_loading_btn.setVisible(False)
        self.load_more_btn.setVisible(self.has_more_rows)

        duration = self._get_duration_str()
        self.result_info_label.setText(
            f"⚠ {self.total_rows_fetched} row(s) loaded in {duration} - Error: {error_msg}"
        )
        self.result_info_label.setStyleSheet("color: orange;")

        logger.error(f"Background loading error: {error_msg}")

    def _stop_background_loading(self):
        """Stop background loading"""
        if self._background_loader and self._background_loader.isRunning():
            self._background_loader.stop()
            self._background_loader.wait(1000)  # Wait up to 1 second
            self._background_loader = None

        self._is_loading = False
        self.stop_loading_btn.setVisible(False)

        if self.has_more_rows:
            self.load_more_btn.setVisible(True)
            duration = self._get_duration_str()
            self.result_info_label.setText(
                f"⏸ {self.total_rows_fetched} row(s) loaded in {duration} - Stopped"
            )
            self.result_info_label.setStyleSheet("color: orange;")

    def _update_loading_status(self):
        """Update the loading status label with progress and duration"""
        duration = self._get_duration_str()

        if self.total_rows_expected:
            # Show progress with known total
            percent = (self.total_rows_fetched / self.total_rows_expected) * 100
            self.result_info_label.setText(
                f"⏳ {self.total_rows_fetched:,}/{self.total_rows_expected:,} row(s) "
                f"({percent:.0f}%) in {duration}"
            )
        else:
            # Show progress without known total
            self.result_info_label.setText(
                f"⏳ {self.total_rows_fetched:,} row(s) loaded in {duration}..."
            )

        self.result_info_label.setStyleSheet("color: #3498db;")  # Blue for loading

    def _get_duration_str(self) -> str:
        """Get formatted duration string"""
        if not self._loading_start_time:
            return "0.0s"

        elapsed = time.time() - self._loading_start_time

        if elapsed < 60:
            return f"{elapsed:.1f}s"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = elapsed % 60
            return f"{minutes}m {seconds:.0f}s"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}h {minutes}m"

    def _load_data_optimized(self, data: list):
        """Load data into grid with optimizations for large datasets"""
        table = self.results_grid.table

        # Disable updates during loading for better performance
        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)

        try:
            self.results_grid.set_data(data)
        finally:
            # Re-enable updates
            table.setUpdatesEnabled(True)

    def _load_more_rows(self):
        """Load more rows from the cursor"""
        if not self._cursor or not self.has_more_rows:
            return

        try:
            self.result_info_label.setText(tr("query_loading_more"))
            self.result_info_label.setStyleSheet("color: orange;")
            QApplication.processEvents()

            # Fetch next batch
            rows = self._cursor.fetchmany(self.batch_size)

            if not rows:
                self.has_more_rows = False
                self.load_more_btn.setVisible(False)
                self.result_info_label.setText(
                    f"✓ {self.total_rows_fetched} row(s) - All rows loaded"
                )
                self.result_info_label.setStyleSheet("color: green;")
                return

            self.total_rows_fetched += len(rows)

            # Check if there are more rows
            if len(rows) < self.batch_size:
                self.has_more_rows = False
                self.load_more_btn.setVisible(False)

            # Convert and append to grid
            data = [[cell for cell in row] for row in rows]
            self._append_data_optimized(data)

            # Update status
            if self.has_more_rows:
                self.result_info_label.setText(
                    f"✓ {self.total_rows_fetched} row(s) loaded (more available)"
                )
            else:
                self.result_info_label.setText(
                    f"✓ {self.total_rows_fetched} row(s) - All rows loaded"
                )
            self.result_info_label.setStyleSheet("color: green;")

            logger.info(f"Loaded {len(rows)} more rows, total: {self.total_rows_fetched}")

        except Exception as e:
            self.result_info_label.setText(f"✗ Error loading more rows: {str(e)}")
            self.result_info_label.setStyleSheet("color: red;")
            self.load_more_btn.setVisible(False)
            logger.error(f"Error loading more rows: {e}")

    def _append_data_optimized(self, data: list):
        """Append data to existing grid with optimizations"""
        table = self.results_grid.table

        # Disable updates during loading
        table.setUpdatesEnabled(False)

        try:
            current_row_count = table.rowCount()
            table.setRowCount(current_row_count + len(data))

            for row_idx, row_data in enumerate(data):
                actual_row = current_row_count + row_idx
                for col_idx, cell_value in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_value) if cell_value is not None else "")
                    table.setItem(actual_row, col_idx, item)

            # Also update the stored data in results_grid
            self.results_grid.data.extend(data)

        finally:
            table.setUpdatesEnabled(True)

    def _clear_query(self):
        """Clear the SQL editor"""
        self.sql_editor.clear()

    def _load_databases(self):
        """Load available databases into the dropdown"""
        self.db_combo.blockSignals(True)
        self.db_combo.clear()

        if not self.connection:
            self.db_combo.addItem("(No connection)")
            self.db_combo.blockSignals(False)
            return

        try:
            if self.db_type == "sqlite":
                # SQLite has only one database
                db_name = self.db_connection.name if self.db_connection else "SQLite"
                self.db_combo.addItem(db_name)
                self.current_database = db_name

            elif self.db_type == "sqlserver":
                cursor = self.connection.cursor()

                # Get all databases (user databases, not system)
                cursor.execute("""
                    SELECT name FROM sys.databases
                    WHERE database_id > 4
                    ORDER BY name
                """)
                databases = [row[0] for row in cursor.fetchall()]

                # Add databases to combo
                for db in databases:
                    self.db_combo.addItem(db)

                # Determine which database to select:
                # 1. Use target_database if specified (from right-click on table)
                # 2. Otherwise use current database from connection
                target_db = self._target_database
                if not target_db:
                    cursor.execute("SELECT DB_NAME()")
                    target_db = cursor.fetchone()[0]

                # Select target database and switch context
                if target_db in databases:
                    self.db_combo.setCurrentText(target_db)
                    self.current_database = target_db
                    # Switch database context
                    try:
                        cursor.execute(f"USE [{target_db}]")
                    except Exception as e:
                        logger.warning(f"Could not switch to database {target_db}: {e}")

            else:
                # Other database types - just show connection name
                db_name = self.db_connection.name if self.db_connection else "Database"
                self.db_combo.addItem(db_name)
                self.current_database = db_name

        except Exception as e:
            logger.error(f"Error loading databases: {e}")
            self.db_combo.addItem("(Error loading)")

        self.db_combo.blockSignals(False)

    def _on_database_changed(self, db_name: str):
        """Handle database selection change"""
        if not db_name or db_name.startswith("("):
            return

        if not self.connection or self.db_type != "sqlserver":
            return

        try:
            # Change database context using USE statement
            cursor = self.connection.cursor()
            cursor.execute(f"USE [{db_name}]")
            self.current_database = db_name

            # Clear schema cache for new database
            self.schema_cache.invalidate()

            logger.info(f"Database context changed to: {db_name}")

        except Exception as e:
            logger.error(f"Error changing database: {e}")
            DialogHelper.error(f"Cannot switch to database '{db_name}'", parent=self, details=str(e))
            # Revert to previous selection
            if self.current_database:
                self.db_combo.blockSignals(True)
                self.db_combo.setCurrentText(self.current_database)
                self.db_combo.blockSignals(False)

    # =========================================================================
    # Toolbar action handlers
    # =========================================================================

    def _on_execute_mode_changed(self, index: int):
        """Update tooltip when execute mode changes."""
        mode = self.execute_combo.currentData()
        if mode == "query":
            self.run_btn.setToolTip(tr("query_execute_query_tooltip"))
            self.run_btn.setShortcut("F5")
        else:
            self.run_btn.setToolTip(tr("query_execute_script_tooltip"))
            self.run_btn.setShortcut("F6")

    def _run_execute(self):
        """Execute query based on selected mode."""
        mode = self.execute_combo.currentData()
        if mode == "script":
            self._execute_as_script()
        else:
            self._execute_as_query()

    def _run_format(self):
        """Format SQL based on selected style."""
        style = self.format_combo.currentData()
        self._format_sql(style)

    def _run_export(self):
        """Export SQL based on selected format."""
        from .script_format_dialog import ScriptFormatDialog

        query_text = self.sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_format"), parent=self)
            return

        export_format = self.export_combo.currentData()
        dialog = ScriptFormatDialog(
            parent=self,
            query_text=query_text,
            format_type=export_format
        )
        dialog.exec()

    def _format_sql(self, style: str):
        """
        Format SQL query with specified style.

        Args:
            style: Format style ("compact", "expanded", "comma_first", "ultimate")
        """
        query_text = self.sql_editor.toPlainText().strip()

        if not query_text:
            return

        try:
            formatted = format_sql(query_text, style)
            self.sql_editor.setPlainText(formatted)

        except Exception as e:
            logger.error(f"SQL formatting error: {e}")
            DialogHelper.error("Formatting failed", parent=self, details=str(e))

    def _format_for_python(self):
        """
        Format the SQL query as a Python variable assignment.
        Shows result in a dialog with copy option.
        """
        from .script_format_dialog import ScriptFormatDialog

        query_text = self.sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_format"), parent=self)
            return

        # Show format dialog
        dialog = ScriptFormatDialog(
            parent=self,
            query_text=query_text,
            format_type="python"
        )
        dialog.exec()

    def _format_for_tsql(self):
        """
        Format the SQL query as a T-SQL variable assignment.
        Shows result in a dialog with copy option.
        """
        from .script_format_dialog import ScriptFormatDialog

        query_text = self.sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_format"), parent=self)
            return

        # Show format dialog
        dialog = ScriptFormatDialog(
            parent=self,
            query_text=query_text,
            format_type="tsql"
        )
        dialog.exec()

    def set_query_text(self, query: str):
        """Set the SQL query text"""
        self.sql_editor.setPlainText(query)

    def get_query_text(self) -> str:
        """Get the SQL query text"""
        return self.sql_editor.toPlainText()

    # =========================================================================
    # Auto-completion methods
    # =========================================================================

    def _setup_completer(self):
        """Setup SQL auto-completer."""
        self.completer = SQLCompleterPopup(self.sql_editor)
        self.completer.completion_selected.connect(self._insert_completion)

        # Install event filter to intercept key events
        self.sql_editor.installEventFilter(self)

        # Override focusOutEvent to hide completer when editor loses focus
        self.sql_editor.focusOutEvent = self._editor_focus_out

    def _editor_focus_out(self, event):
        """Handle editor losing focus - hide completer."""
        # Hide completer when editor loses focus
        if self.completer.isVisible():
            self.completer.cancel()
        # Call original focusOutEvent
        QTextEdit.focusOutEvent(self.sql_editor, event)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events for the SQL editor to handle auto-completion."""
        if obj != self.sql_editor:
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            return self._handle_key_press(key_event)

        return super().eventFilter(obj, event)

    def _handle_key_press(self, event: QKeyEvent) -> bool:
        """
        Handle key press for auto-completion.

        Returns:
            True if event was consumed, False to pass to editor
        """
        key = event.key()
        modifiers = event.modifiers()

        # Ctrl+Space: Manual trigger
        if key == Qt.Key.Key_Space and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._trigger_completion(force=True)
            return True

        # If completer is visible, handle navigation
        if self.completer.isVisible():
            if key == Qt.Key.Key_Escape:
                self.completer.cancel()
                return True

            if key == Qt.Key.Key_Up:
                self.completer.navigate_up()
                return True

            if key == Qt.Key.Key_Down:
                self.completer.navigate_down()
                return True

            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                if self.completer.accept_completion():
                    return True

            # For normal characters or backspace, let editor handle it
            # then update the filter dynamically
            if event.text() or key == Qt.Key.Key_Backspace:
                QTimer.singleShot(0, self._update_completer_filter)
                return False  # Let editor process the key

            # Space or other non-word characters close the completer
            if key == Qt.Key.Key_Space:
                self.completer.cancel()
                return False

        # Let the editor handle the key first
        # We'll check for triggers after text changes
        # Schedule trigger check after key is processed
        QTimer.singleShot(0, self._check_auto_trigger)

        return False

    def _update_completer_filter(self):
        """Update the completer filter based on current prefix."""
        if not self.completer.isVisible():
            return

        context, prefix, table_name = self._get_context()

        # If we've typed something that breaks the context, close completer
        if context is None:
            self.completer.cancel()
            return

        # Update the filter with new prefix
        self._completer_prefix = prefix
        self.completer.update_filter(prefix)

    def _check_auto_trigger(self):
        """Check if we should auto-trigger completion after typing."""
        if not self.connection:
            return

        context, prefix, table_name = self._get_context()

        # Auto-trigger rules:
        # - "table_column" (after table.): always trigger (user explicitly wants columns)
        # - "table" (after FROM/JOIN): trigger with 1+ char prefix (helps find tables)
        # - "column" (after SELECT/WHERE): only trigger with 2+ char prefix
        #   (avoids loading all columns which can be slow and annoying)

        if context == "table_column":
            # After "table." - always show columns for that table
            self._trigger_completion(context=context, prefix=prefix, table_name=table_name)

        elif context == "table" and len(prefix) >= 1:
            # After FROM/JOIN with at least 1 char - show matching tables
            self._trigger_completion(context=context, prefix=prefix, table_name=table_name)

        elif context == "column" and len(prefix) >= 2:
            # After SELECT/WHERE with at least 2 chars - show matching columns
            self._trigger_completion(context=context, prefix=prefix, table_name=table_name)

        elif self.completer.isVisible():
            # Update filter if completer is already visible
            if prefix:
                self.completer.update_filter(prefix)
            else:
                self.completer.cancel()

    def _trigger_completion(self, force: bool = False, context: str = None,
                            prefix: str = "", table_name: str = None):
        """
        Trigger the auto-completion popup.

        Args:
            force: If True, show all suggestions (Ctrl+Space)
            context: Detected context ("table", "column", "table_column")
            prefix: Current word prefix for filtering
            table_name: Table name for column completion
        """
        if not self.connection:
            return

        # Get context if not provided
        if context is None:
            context, prefix, table_name = self._get_context()

        suggestions = []

        try:
            if force:
                # Show everything
                tables = self.schema_cache.get_tables(self.connection, self.db_type)
                columns = self.schema_cache.get_all_columns(self.connection, self.db_type)
                suggestions = sorted(set(tables + columns))

            elif context == "table":
                # After FROM/JOIN - show tables
                suggestions = self.schema_cache.get_tables(self.connection, self.db_type)

            elif context == "column":
                # After SELECT/WHERE - show all columns
                suggestions = self.schema_cache.get_all_columns(self.connection, self.db_type)

            elif context == "table_column" and table_name:
                # After table. - show columns for that table
                suggestions = self.schema_cache.get_columns(
                    self.connection, self.db_type, table_name
                )

        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return

        if suggestions:
            self._completer_prefix = prefix
            cursor_rect = self.sql_editor.cursorRect()
            self.completer.show_completions(suggestions, prefix, cursor_rect)

    def _get_context(self) -> Tuple[Optional[str], str, Optional[str]]:
        """
        Analyze text before cursor to determine completion context.

        Returns:
            Tuple of (context_type, prefix, table_name)
            context_type: "table", "column", "table_column", or None
            prefix: Current word being typed
            table_name: For table_column context, the table name
        """
        cursor = self.sql_editor.textCursor()
        text = self.sql_editor.toPlainText()
        pos = cursor.position()

        # Get text before cursor (last 200 chars should be enough)
        text_before = text[max(0, pos - 200):pos]

        # Pattern: table.prefix - columns for specific table
        match = re.search(r'(\w+)\.(\w*)$', text_before)
        if match:
            table_name = match.group(1)
            prefix = match.group(2)
            return ("table_column", prefix, table_name)

        # Pattern: FROM/JOIN table_prefix - tables
        match = re.search(r'(?:FROM|JOIN)\s+(\w*)$', text_before, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            return ("table", prefix, None)

        # Pattern: SELECT columns - all columns
        match = re.search(r'SELECT\s+(?:.*,\s*)?(\w*)$', text_before, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            return ("column", prefix, None)

        # Pattern: WHERE/AND/OR column - all columns
        match = re.search(r'(?:WHERE|AND|OR)\s+(\w*)$', text_before, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            return ("column", prefix, None)

        return (None, "", None)

    def _insert_completion(self, text: str):
        """
        Insert the selected completion into the editor.

        Args:
            text: The completion text to insert
        """
        cursor = self.sql_editor.textCursor()

        # Remove the prefix we're replacing
        if self._completer_prefix:
            for _ in range(len(self._completer_prefix)):
                cursor.deletePreviousChar()

        # Insert the completion
        cursor.insertText(text)
        self.sql_editor.setTextCursor(cursor)

    # =========================================================================
    # Connection error handling
    # =========================================================================

    def _is_connection_error(self, error: Exception) -> bool:
        """
        Check if an exception is a connection-related error.

        Args:
            error: The exception to check

        Returns:
            True if this is a connection error (VPN dropped, server unreachable, etc.)
        """
        error_str = str(error).lower()

        # Common connection error indicators
        connection_indicators = [
            "communication link failure",
            "tcp provider",
            "connection failure",
            "network-related",
            "connection was forcibly closed",
            "connection timed out",
            "server has gone away",
            "lost connection",
            "unable to connect",
            "connection refused",
            "no connection",
            "08001",  # SQL Server connection error
            "08s01",  # Communication link failure
            "hyt00",  # Timeout expired
            "hyt01",  # Connection timeout
        ]

        return any(indicator in error_str for indicator in connection_indicators)

    def _handle_connection_error(self, error: Exception):
        """
        Handle a connection error by offering reconnection option.

        Args:
            error: The connection error
        """
        from PySide6.QtWidgets import QMessageBox

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(tr("connection_error"))
        msg.setText(tr("connection_lost"))
        msg.setInformativeText(
            tr("reconnecting_vpn_hint") + "\n\n" + tr("would_you_reconnect")
        )
        msg.setDetailedText(str(error))

        # Add custom buttons
        reconnect_btn = msg.addButton(tr("btn_reconnect"), QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)

        msg.exec()

        if msg.clickedButton() == reconnect_btn:
            self._attempt_reconnection()

    def _attempt_reconnection(self):
        """Attempt to reconnect to the database and re-execute the query."""
        if not self.db_connection:
            DialogHelper.error(tr("no_db_config"), parent=self)
            return

        # Find the DatabaseManager parent
        database_manager = self._find_database_manager()
        if not database_manager:
            DialogHelper.error(tr("cannot_find_db_manager"), parent=self)
            return

        # Show reconnecting status
        self.result_info_label.setText(tr("reconnecting"))
        self.result_info_label.setStyleSheet("color: orange;")
        QApplication.processEvents()

        try:
            # Attempt reconnection via DatabaseManager
            new_connection = database_manager.reconnect_database(self.db_connection.id)

            if new_connection:
                # Update our connection reference
                self.connection = new_connection

                self.result_info_label.setText(tr("reconnected"))
                self.result_info_label.setStyleSheet("color: green;")

                # Reload databases dropdown
                self._load_databases()

                # Ask if user wants to re-execute the query
                from PySide6.QtWidgets import QMessageBox
                result = QMessageBox.question(
                    self,
                    tr("reexecute_query_title"),
                    tr("reexecute_query_question"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if result == QMessageBox.StandardButton.Yes:
                    self._execute_as_query()
            else:
                self.result_info_label.setText(tr("reconnect_failed"))
                self.result_info_label.setStyleSheet("color: red;")
                DialogHelper.error(
                    tr("reconnect_failed") + "\n\n" + tr("check_vpn_connection"),
                    parent=self
                )

        except Exception as e:
            self.result_info_label.setText(tr("reconnection_error"))
            self.result_info_label.setStyleSheet("color: red;")
            DialogHelper.error(tr("reconnect_failed"), parent=self, details=str(e))
            logger.error(f"Reconnection error: {e}")

    def _find_database_manager(self):
        """Find the parent DatabaseManager widget."""
        # Use stored reference if available
        if self._database_manager is not None:
            return self._database_manager

        # Fallback: traverse parent hierarchy
        widget = self.parent()
        while widget is not None:
            if widget.__class__.__name__ == "DatabaseManager":
                return widget
            widget = widget.parent()
        return None

    # =========================================================================
    # Save Query
    # =========================================================================

    def _save_query(self):
        """Save the current query to saved queries collection."""
        from ..widgets.save_query_dialog import SaveQueryDialog
        from ...database.config_db import get_config_db, SavedQuery

        # Get query text
        query_text = self.sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_save"), parent=self)
            return

        # Get database info
        database_name = ""
        database_id = ""

        if self.db_connection:
            database_name = self.db_connection.name
            database_id = self.db_connection.id
            logger.info(f"db_connection found: name={database_name}, id={database_id}")
        else:
            logger.warning("No db_connection available in QueryTab")

        # Show save dialog
        dialog = SaveQueryDialog(
            parent=self,
            query_text=query_text,
            database_name=database_name,
            database_id=database_id
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get data and save
            data = dialog.get_query_data()

            logger.info(f"Saving query with target_database_id: {data['target_database_id']}")

            try:
                config_db = get_config_db()

                # Create SavedQuery object
                saved_query = SavedQuery(
                    id="",  # Will be generated
                    name=data["name"],
                    target_database_id=data["target_database_id"],
                    query_text=data["query_text"],
                    category=data["category"],
                    description=data["description"]
                )

                logger.info(f"SavedQuery created with id: {saved_query.id}")

                # Save to database
                result = config_db.add_saved_query(saved_query)
                logger.info(f"add_saved_query result: {result}")

                if result:
                    DialogHelper.info(
                        tr("query_saved_success", name=data['name']),
                        parent=self
                    )
                    logger.info(f"Saved query: {data['name']} to category: {data['category']}")
                    # Emit signal to trigger refresh
                    self.query_saved.emit()
                else:
                    DialogHelper.error(
                        tr("query_save_db_constraint"),
                        parent=self,
                        details=f"Database ID: {data['target_database_id']}"
                    )

            except Exception as e:
                logger.error(f"Error saving query: {e}")
                DialogHelper.error(
                    tr("query_save_failed"),
                    parent=self,
                    details=str(e)
                )
