"""
Query Tab - Single SQL query editor tab for DatabaseManager
"""

from typing import Optional, Union, Tuple
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QPushButton, QLabel, QSplitter, QComboBox,
                               QTableWidgetItem, QApplication, QDialog)
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QThread, QTimer
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

# DataFrame-Pivot pattern: use shared threshold
from ...core.data_loader import LARGE_DATASET_THRESHOLD

import logging
import time

logger = logging.getLogger(__name__)


class BackgroundRowLoader(QThread):
    """Background thread for loading rows from cursor"""

    # Signals
    batch_loaded = Signal(list)  # Emits batch of rows
    loading_complete = Signal(int)  # Emits total row count
    loading_error = Signal(str)  # Emits error message

    def __init__(self, cursor, batch_size: int = 1000):
        super().__init__()
        self.cursor = cursor
        self.batch_size = batch_size
        self._stop_requested = False

    def run(self):
        """Load rows in background"""
        try:
            while not self._stop_requested:
                rows = self.cursor.fetchmany(self.batch_size)

                if not rows:
                    break

                # Convert to list of lists
                data = [[cell for cell in row] for row in rows]
                self.batch_loaded.emit(data)

                # Small pause to allow UI updates
                self.msleep(10)

            self.loading_complete.emit(0)  # 0 = normal completion

        except Exception as e:
            self.loading_error.emit(str(e))

    def stop(self):
        """Request stop"""
        self._stop_requested = True


class QueryTab(QWidget):
    """Single SQL query editor tab"""

    # Signal emitted when tab requests to be closed
    close_requested = Signal()
    # Signal emitted when a query is saved to saved queries
    query_saved = Signal()

    def cleanup(self):
        """Stop background tasks and cleanup resources"""
        try:
            # Stop background loader if running
            loader = getattr(self, '_background_loader', None)
            if loader is not None:
                # Disconnect signals first to prevent callbacks during shutdown
                try:
                    loader.batch_loaded.disconnect()
                    loader.loading_complete.disconnect()
                    loader.loading_error.disconnect()
                except (RuntimeError, TypeError):
                    pass  # Signals may not be connected

                if loader.isRunning():
                    loader.stop()
                    # Quick wait, then force terminate - don't block shutdown
                    if not loader.wait(20):  # Wait max 20ms
                        loader.terminate()  # Force terminate immediately
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
                 database_manager=None):
        """
        Initialize query tab.

        Args:
            parent: Parent widget
            connection: Database connection
            db_connection: Database connection config
            tab_name: Name of the tab
            database_manager: Reference to parent DatabaseManager for reconnection
        """
        super().__init__(parent)

        self.connection = connection
        self.db_connection = db_connection
        self.tab_name = tab_name
        self._database_manager = database_manager
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Top toolbar with Execute button on left, format buttons on right
        toolbar = QHBoxLayout()

        # Left side: Database selector (like SSMS)
        db_label = QLabel("Database:")
        toolbar.addWidget(db_label)

        self.db_combo = QComboBox()
        self.db_combo.setMinimumWidth(150)
        self.db_combo.setToolTip("Select database context for queries")
        self.db_combo.currentTextChanged.connect(self._on_database_changed)
        toolbar.addWidget(self.db_combo)

        toolbar.addSpacing(20)

        # Execute button
        self.execute_btn = QPushButton("▶ Execute (F5)")
        self.execute_btn.clicked.connect(self._execute_query)
        self.execute_btn.setShortcut("F5")
        self.execute_btn.setToolTip("Execute the SQL query (F5)")
        toolbar.addWidget(self.execute_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_query)
        toolbar.addWidget(self.clear_btn)

        self.save_query_btn = QPushButton("💾 Save to Queries")
        self.save_query_btn.clicked.connect(self._save_query)
        self.save_query_btn.setToolTip("Save to Saved Queries / Enregistrer dans les requêtes sauvegardées")
        toolbar.addWidget(self.save_query_btn)

        toolbar.addStretch()

        # Right side: Format style buttons
        format_label = QLabel("Format:")
        toolbar.addWidget(format_label)

        self.compact_btn = QPushButton("Compact")
        self.compact_btn.clicked.connect(lambda: self._format_sql("compact"))
        self.compact_btn.setToolTip("Compact style - Multiple columns on same line")
        toolbar.addWidget(self.compact_btn)

        self.expanded_btn = QPushButton("Expanded")
        self.expanded_btn.clicked.connect(lambda: self._format_sql("expanded"))
        self.expanded_btn.setToolTip("Expanded style - One column per line")
        toolbar.addWidget(self.expanded_btn)

        self.comma_first_btn = QPushButton("Comma First")
        self.comma_first_btn.clicked.connect(lambda: self._format_sql("comma_first"))
        self.comma_first_btn.setToolTip("Comma First style - Commas at beginning")
        toolbar.addWidget(self.comma_first_btn)

        self.ultimate_btn = QPushButton("Ultimate")
        self.ultimate_btn.clicked.connect(lambda: self._format_sql("ultimate"))
        self.ultimate_btn.setToolTip("Ultimate style - Advanced alignment")
        toolbar.addWidget(self.ultimate_btn)

        layout.addLayout(toolbar)

        # Splitter for SQL editor (top) and results (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # SQL Editor - black text for identifiers (table names, etc.)
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText("-- " + tr("enter_sql_query_here"))
        self.sql_editor.setFont(QFont("Consolas", 10))
        # Force black text for non-highlighted words (table names, identifiers)
        self.sql_editor.setStyleSheet("QTextEdit { color: #000000; }")

        # Apply SQL syntax highlighting
        self.sql_highlighter = SQLHighlighter(self.sql_editor.document())

        splitter.addWidget(self.sql_editor)

        # Results panel
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # Result info bar with label and control buttons
        result_bar = QHBoxLayout()

        self.result_info_label = QLabel("No query executed")
        self.result_info_label.setStyleSheet("color: gray;")
        result_bar.addWidget(self.result_info_label)

        result_bar.addStretch()

        # Stop loading button (visible during background loading)
        self.stop_loading_btn = QPushButton("⏹ Stop")
        self.stop_loading_btn.clicked.connect(self._stop_background_loading)
        self.stop_loading_btn.setVisible(False)
        self.stop_loading_btn.setToolTip("Stop loading remaining rows")
        result_bar.addWidget(self.stop_loading_btn)

        # Load more button (visible when background loading is stopped/paused)
        self.load_more_btn = QPushButton("Load 1000 more rows...")
        self.load_more_btn.clicked.connect(self._load_more_rows)
        self.load_more_btn.setVisible(False)
        result_bar.addWidget(self.load_more_btn)

        results_layout.addLayout(result_bar)

        # Results grid
        self.results_grid = CustomDataGridView(show_toolbar=True)
        results_layout.addWidget(self.results_grid)

        splitter.addWidget(results_widget)

        # Set splitter proportions
        splitter.setSizes([300, 400])

        layout.addWidget(splitter)

    def _execute_query(self):
        """Execute the SQL query with hybrid loading (immediate + background)"""
        query = self.sql_editor.toPlainText().strip()

        if not query:
            DialogHelper.warning(tr("no_query_to_execute"), parent=self)
            return

        if not self.connection:
            DialogHelper.error("No database connection", parent=self)
            return

        # Stop any existing background loading
        self._stop_background_loading()

        # Save original query
        self.original_query = query

        # Reset batch loading state
        self.total_rows_fetched = 0
        self.total_rows_expected = None
        self.has_more_rows = False
        self._cursor = None
        self._is_loading = False
        self._loading_start_time = time.time()
        self.load_more_btn.setVisible(False)
        self.stop_loading_btn.setVisible(False)

        try:
            # Show loading state
            self.result_info_label.setText("⏳ Counting rows...")
            self.result_info_label.setStyleSheet("color: orange;")
            QApplication.processEvents()

            # Try to get total row count first (for SELECT queries)
            self.total_rows_expected = self._get_query_row_count(query)

            # Check for large dataset and warn user
            if self.total_rows_expected and self.total_rows_expected > LARGE_DATASET_THRESHOLD:
                if not self._handle_large_dataset_warning(self.total_rows_expected):
                    self.result_info_label.setText("Query cancelled by user")
                    self.result_info_label.setStyleSheet("color: gray;")
                    return

            # Show executing state
            self.result_info_label.setText("⏳ Executing query...")
            QApplication.processEvents()

            cursor = self.connection.cursor()
            cursor.execute(query)

            if cursor.description:
                # SELECT query - hybrid loading
                columns = [column[0] for column in cursor.description]
                self.current_columns = columns

                # Fetch first batch synchronously for immediate display
                rows = cursor.fetchmany(self.batch_size)
                self.total_rows_fetched = len(rows)

                # Convert to list of lists for CustomDataGridView
                data = [[cell for cell in row] for row in rows]

                # Load first batch into grid
                self.results_grid.set_columns(columns)
                # Set context for distribution analysis
                db_name = self.current_database or (self.db_connection.name if self.db_connection else None)
                self.results_grid.set_context(db_name=db_name, table_name="Query")
                self._load_data_optimized(data)

                # Check if there are more rows
                if len(rows) == self.batch_size:
                    # Start background loading for remaining rows
                    self._cursor = cursor
                    self.has_more_rows = True
                    self._start_background_loading(cursor)
                else:
                    # All data loaded
                    self.has_more_rows = False
                    duration = self._get_duration_str()
                    if self.total_rows_expected:
                        self.result_info_label.setText(
                            f"✓ {self.total_rows_fetched:,}/{self.total_rows_expected:,} row(s) (100%) in {duration}"
                        )
                    else:
                        self.result_info_label.setText(
                            f"✓ {self.total_rows_fetched:,} row(s) returned in {duration}"
                        )
                    self.result_info_label.setStyleSheet("color: green;")

                logger.info(f"Query executed: {self.total_rows_fetched} rows loaded initially")

            else:
                # INSERT/UPDATE/DELETE query
                rows_affected = cursor.rowcount
                self.connection.commit()

                self.results_grid.clear()
                self.result_info_label.setText(f"✓ Query executed. {rows_affected} row(s) affected")
                self.result_info_label.setStyleSheet("color: green;")
                logger.info(f"Query executed: {rows_affected} rows affected")

        except Exception as e:
            self.result_info_label.setText(f"✗ Error: {str(e)}")
            self.result_info_label.setStyleSheet("color: red;")
            self.load_more_btn.setVisible(False)
            self.stop_loading_btn.setVisible(False)

            # Check if this is a connection error (VPN dropped, server unreachable)
            if self._is_connection_error(e):
                self._handle_connection_error(e)
            else:
                DialogHelper.error("Query execution failed", parent=self, details=str(e))
            logger.error(f"Query execution error: {e}")

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
            self.result_info_label.setText("⏳ Loading more rows...")
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

                # Get current database
                cursor.execute("SELECT DB_NAME()")
                current_db = cursor.fetchone()[0]

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

                # Select current database
                if current_db in databases:
                    self.db_combo.setCurrentText(current_db)
                    self.current_database = current_db

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
            self.schema_cache.clear()

            logger.info(f"Database context changed to: {db_name}")

        except Exception as e:
            logger.error(f"Error changing database: {e}")
            DialogHelper.error(f"Cannot switch to database '{db_name}'", parent=self, details=str(e))
            # Revert to previous selection
            if self.current_database:
                self.db_combo.blockSignals(True)
                self.db_combo.setCurrentText(self.current_database)
                self.db_combo.blockSignals(False)

    def _format_sql(self, style: str):
        """
        Format SQL query with specified style.

        Args:
            style: Format style ("compact", "expanded", "comma_first", "ultimate")
        """
        import sqlparse

        query_text = self.sql_editor.toPlainText().strip()

        if not query_text:
            return

        try:
            if style == "compact":
                # Compact: multiple columns on same line
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=2,
                    use_space_around_operators=True,
                    wrap_after=120
                )

            elif style == "expanded":
                # Expanded: one column per line
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=4,
                    use_space_around_operators=True
                )
                formatted = self._force_one_column_per_line(formatted)

            elif style == "comma_first":
                # Comma first
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=4,
                    use_space_around_operators=True,
                    comma_first=True
                )

            elif style == "ultimate":
                # Ultimate: sophisticated alignment (keywords, AS, aliases, operators)
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=4,
                    use_space_around_operators=True
                )
                # Apply sophisticated alignment
                formatted = self._apply_sophisticated_formatting(formatted)

            else:
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=4
                )

            self.sql_editor.setPlainText(formatted)

        except Exception as e:
            logger.error(f"SQL formatting error: {e}")
            DialogHelper.error("Formatting failed", parent=self, details=str(e))

    def _force_one_column_per_line(self, sql_text: str) -> str:
        """Force SELECT columns to be on separate lines"""
        lines = sql_text.split('\n')
        result = []
        in_select = False

        for line in lines:
            stripped = line.strip().upper()

            if stripped.startswith('SELECT'):
                in_select = True
                if ',' in line:
                    parts = line.split(',')
                    result.append(parts[0])
                    for part in parts[1:]:
                        result.append(f"    , {part.strip()}")
                else:
                    result.append(line)

            elif in_select and (stripped.startswith('FROM') or stripped.startswith('WHERE') or
                               stripped.startswith('ORDER BY') or stripped.startswith('GROUP BY')):
                in_select = False
                result.append(line)

            elif in_select and ',' in line:
                parts = line.split(',')
                for i, part in enumerate(parts):
                    if i == 0:
                        result.append(part.rstrip())
                    else:
                        indent = len(line) - len(line.lstrip())
                        result.append(f"{' ' * indent}, {part.strip()}")
            else:
                result.append(line)

        return '\n'.join(result)

    def _apply_sophisticated_formatting(self, sql_text: str) -> str:
        """
        Apply sophisticated formatting with full alignment:
        - Keywords aligned (SELECT, FROM, WHERE, JOIN, etc.)
        - AS keywords aligned in SELECT
        - Table aliases aligned in FROM/JOIN
        - Operators (=) aligned in ON and WHERE conditions
        - ASC/DESC aligned in ORDER BY
        """
        lines = sql_text.split('\n')

        # Main keywords that should be aligned
        main_keywords = [
            'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY',
            'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN',
            'UNION', 'UNION ALL', 'LIMIT', 'OFFSET'
        ]
        max_keyword_len = max(len(kw) for kw in main_keywords)

        # Parse SQL into sections
        sections = self._parse_sql_sections(lines, main_keywords)

        # Calculate max lengths for alignment
        select_sections = [s for s in sections if s['type'] == 'SELECT']
        from_join_sections = [s for s in sections if s['type'] in
                             ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN')]

        # Max field length for SELECT AS alignment
        max_field_len = 0
        for section in select_sections:
            for col_info in section.get('parsed_columns', []):
                max_field_len = max(max_field_len, len(col_info['field']))

        # Max table name length for alias alignment
        max_table_len = 0
        for section in from_join_sections:
            if section.get('table_name'):
                max_table_len = max(max_table_len, len(section['table_name']))

        # Format each section
        result = []
        for section in sections:
            if section['type'] == 'SELECT':
                self._format_select_section(result, section, max_keyword_len, max_field_len)
            elif section['type'] in ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN'):
                self._format_from_join_section(result, section, max_keyword_len, max_table_len)
            elif section['type'] in ('GROUP BY', 'ORDER BY'):
                self._format_group_order_section(result, section, max_keyword_len)
            elif section['type'] == 'WHERE':
                self._format_where_section(result, section, max_keyword_len)
            else:
                self._format_simple_section(result, section, max_keyword_len)

        return '\n'.join(result)

    def _parse_sql_sections(self, lines: list, main_keywords: list) -> list:
        """Parse SQL lines into sections with pre-parsing."""
        sections = []
        current_section = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if line starts with a main keyword
            keyword_found = None
            for keyword in sorted(main_keywords, key=len, reverse=True):
                if stripped.upper().startswith(keyword + ' ') or stripped.upper() == keyword:
                    keyword_found = keyword
                    break

            if keyword_found:
                if current_section:
                    sections.append(current_section)

                rest = stripped[len(keyword_found):].strip()
                current_section = {
                    'type': keyword_found,
                    'keyword': keyword_found,
                    'content': [rest] if rest else []
                }
            elif current_section:
                current_section['content'].append(stripped)

        if current_section:
            sections.append(current_section)

        # Pre-parse sections
        for section in sections:
            if section['type'] == 'SELECT':
                self._preparse_select_section(section)
            elif section['type'] in ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN'):
                self._preparse_from_join_section(section)

        return sections

    def _preparse_select_section(self, section: dict):
        """Pre-parse SELECT section to extract columns and AS aliases."""
        all_content = ' '.join(section['content'])
        columns = [c.strip() for c in all_content.split(',') if c.strip()]

        parsed_columns = []
        for col in columns:
            as_match = re.search(r'\s+AS\s+', col, re.IGNORECASE)
            if as_match:
                field = col[:as_match.start()].strip()
                alias = col[as_match.end():].strip()
                parsed_columns.append({'field': field, 'alias': alias, 'has_as': True})
            else:
                parsed_columns.append({'field': col, 'alias': None, 'has_as': False})

        section['parsed_columns'] = parsed_columns

    def _preparse_from_join_section(self, section: dict):
        """Pre-parse FROM/JOIN section to extract table, alias, and ON conditions."""
        all_content = ' '.join(section['content'])

        # Parse ON condition
        on_match = re.search(r'\s+ON\s+', all_content, re.IGNORECASE)
        if on_match:
            table_part = all_content[:on_match.start()].strip()
            on_part = all_content[on_match.end():].strip()
        else:
            table_part = all_content
            on_part = None

        # Split table and alias
        table_parts = table_part.split()
        if len(table_parts) >= 2:
            table_name = table_parts[0]
            table_alias = ' '.join(table_parts[1:])
        elif len(table_parts) == 1:
            table_name = table_parts[0]
            table_alias = None
        else:
            table_name = table_part
            table_alias = None

        section['table_name'] = table_name
        section['table_alias'] = table_alias
        section['on_condition'] = on_part

        # Parse ON conditions (split by AND)
        if on_part:
            and_conditions = re.split(r'\s+AND\s+', on_part, flags=re.IGNORECASE)
            parsed_conditions = []
            max_left_len = 0

            for cond in and_conditions:
                cond = cond.strip()
                op_match = re.search(r'\s*(>=|<=|!=|<>|=|<|>|IN|NOT IN|LIKE|NOT LIKE|IS NOT|IS)\s+',
                                    cond, re.IGNORECASE)
                if op_match:
                    left = cond[:op_match.start()].strip()
                    operator = op_match.group(1).strip().upper()
                    right = cond[op_match.end():].strip()
                    parsed_conditions.append({
                        'left': left, 'operator': operator, 'right': right, 'has_operator': True
                    })
                    max_left_len = max(max_left_len, len(left))
                else:
                    parsed_conditions.append({'full': cond, 'has_operator': False})

            section['parsed_on_conditions'] = parsed_conditions
            section['max_on_left_len'] = max_left_len
        else:
            section['parsed_on_conditions'] = []
            section['max_on_left_len'] = 0

    def _format_select_section(self, result: list, section: dict, max_keyword_len: int, max_field_len: int):
        """Format SELECT section with aligned AS keywords."""
        column_indent = ' ' * (max_keyword_len - 1)

        for i, col_info in enumerate(section.get('parsed_columns', [])):
            if i == 0:
                if col_info['has_as']:
                    field_padded = col_info['field'].ljust(max_field_len)
                    result.append(f"SELECT     {field_padded} AS {col_info['alias']}")
                else:
                    result.append(f"SELECT     {col_info['field']}")
            else:
                if col_info['has_as']:
                    field_padded = col_info['field'].ljust(max_field_len)
                    result.append(f"{column_indent}, {field_padded} AS {col_info['alias']}")
                else:
                    result.append(f"{column_indent}, {col_info['field']}")

    def _format_from_join_section(self, result: list, section: dict, max_keyword_len: int, max_table_len: int):
        """Format FROM/JOIN section with aligned aliases and ON conditions."""
        keyword = section['keyword']
        table_name = section.get('table_name', '')
        table_alias = section.get('table_alias', '')
        parsed_conditions = section.get('parsed_on_conditions', [])
        max_left_len = section.get('max_on_left_len', 0)

        # Build base line
        if table_alias:
            table_padded = table_name.ljust(max_table_len)
            line = f"{keyword.ljust(max_keyword_len)} {table_padded} {table_alias}"
            on_start_pos = max_keyword_len + 1 + max_table_len + 1 + len(table_alias) + 1
        else:
            line = f"{keyword.ljust(max_keyword_len)} {table_name}"
            on_start_pos = max_keyword_len + 1 + len(table_name) + 1

        # Add ON conditions
        if parsed_conditions:
            equals_position = max_left_len + 1

            first_cond = parsed_conditions[0]
            if first_cond.get('has_operator'):
                left = first_cond['left']
                operator = first_cond['operator']
                padding = self._calc_operator_padding(left, operator, equals_position)
                line += f" ON  {left}{' ' * padding}{operator} {first_cond['right']}"
            else:
                line += f" ON  {first_cond['full']}"
            result.append(line)

            # Additional AND conditions
            if len(parsed_conditions) > 1:
                and_indent = ' ' * on_start_pos
                for cond_info in parsed_conditions[1:]:
                    if cond_info.get('has_operator'):
                        left = cond_info['left']
                        operator = cond_info['operator']
                        padding = self._calc_operator_padding(left, operator, equals_position)
                        result.append(f"{and_indent}AND {left}{' ' * padding}{operator} {cond_info['right']}")
                    else:
                        result.append(f"{and_indent}AND {cond_info['full']}")
        else:
            result.append(line)

    def _format_group_order_section(self, result: list, section: dict, max_keyword_len: int):
        """Format GROUP BY / ORDER BY with aligned ASC/DESC."""
        all_content = ' '.join(section['content'])
        columns = [c.strip() for c in all_content.split(',') if c.strip()]

        if not columns:
            return

        column_indent = ' ' * (max_keyword_len - 1)
        keyword = section['keyword']

        if keyword == 'ORDER BY':
            # Parse and align ASC/DESC
            parsed_columns = []
            max_col_len = 0

            for col in columns:
                dir_match = re.search(r'\s+(ASC|DESC)\s*$', col, re.IGNORECASE)
                if dir_match:
                    col_name = col[:dir_match.start()].strip()
                    direction = dir_match.group(1).upper()
                    parsed_columns.append({'col': col_name, 'direction': direction})
                    max_col_len = max(max_col_len, len(col_name))
                else:
                    parsed_columns.append({'col': col, 'direction': None})
                    max_col_len = max(max_col_len, len(col))

            for i, col_info in enumerate(parsed_columns):
                if i == 0:
                    if col_info['direction']:
                        col_padded = col_info['col'].ljust(max_col_len)
                        result.append(f"{keyword.ljust(max_keyword_len)} {col_padded} {col_info['direction']}")
                    else:
                        result.append(f"{keyword.ljust(max_keyword_len)} {col_info['col']}")
                else:
                    if col_info['direction']:
                        col_padded = col_info['col'].ljust(max_col_len)
                        result.append(f"{column_indent}, {col_padded} {col_info['direction']}")
                    else:
                        result.append(f"{column_indent}, {col_info['col']}")
        else:
            # GROUP BY - no direction
            for i, col in enumerate(columns):
                if i == 0:
                    result.append(f"{keyword.ljust(max_keyword_len)} {col}")
                else:
                    result.append(f"{column_indent}, {col}")

    def _format_where_section(self, result: list, section: dict, max_keyword_len: int):
        """Format WHERE section with aligned operators."""
        content = ' '.join(section['content'])
        and_conditions = re.split(r'\s+AND\s+', content, flags=re.IGNORECASE)

        if len(and_conditions) == 1:
            result.append(f"{section['keyword'].ljust(max_keyword_len)} {content}")
        else:
            parsed_conditions = []
            max_left_len = 0

            for cond in and_conditions:
                cond = cond.strip()
                op_match = re.search(r'\s*(>=|<=|!=|<>|=|<|>|IN|NOT IN|LIKE|NOT LIKE|IS NOT|IS)\s+',
                                    cond, re.IGNORECASE)
                if op_match:
                    left = cond[:op_match.start()].strip()
                    operator = op_match.group(1).strip().upper()
                    right = cond[op_match.end():].strip()
                    parsed_conditions.append({
                        'left': left, 'operator': operator, 'right': right, 'has_operator': True
                    })
                    max_left_len = max(max_left_len, len(left))
                else:
                    parsed_conditions.append({'full': cond, 'has_operator': False})

            equals_position = max_left_len + 1

            first_cond = parsed_conditions[0]
            if first_cond.get('has_operator'):
                left = first_cond['left']
                operator = first_cond['operator']
                padding = self._calc_operator_padding(left, operator, equals_position)
                result.append(f"WHERE      {left}{' ' * padding}{operator} {first_cond['right']}")
            else:
                result.append(f"WHERE      {first_cond['full']}")

            for cond_info in parsed_conditions[1:]:
                if cond_info.get('has_operator'):
                    left = cond_info['left']
                    operator = cond_info['operator']
                    padding = self._calc_operator_padding(left, operator, equals_position)
                    result.append(f"AND        {left}{' ' * padding}{operator} {cond_info['right']}")
                else:
                    result.append(f"AND        {cond_info['full']}")

    def _format_simple_section(self, result: list, section: dict, max_keyword_len: int):
        """Format simple sections (HAVING, LIMIT, etc.)."""
        content = ' '.join(section['content'])
        if content:
            result.append(f"{section['keyword'].ljust(max_keyword_len)} {content}")
        else:
            result.append(section['keyword'].ljust(max_keyword_len))

    def _calc_operator_padding(self, left_field: str, operator: str, equals_position: int) -> int:
        """Calculate padding to align operators (= signs)."""
        if operator == '=':
            padding = equals_position - len(left_field)
        elif '=' in operator and len(operator) >= 2 and operator[1] == '=':
            padding = equals_position - len(left_field) - 1
        else:
            padding = equals_position - len(left_field)
        return max(1, padding)

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
        msg.setWindowTitle("Connection Error / Erreur de connexion")
        msg.setText("Database connection lost.\nLa connexion à la base de données a été perdue.")
        msg.setInformativeText(
            "This may happen if your VPN connection was interrupted.\n"
            "Cela peut arriver si votre connexion VPN a été interrompue.\n\n"
            "Would you like to reconnect?\n"
            "Voulez-vous vous reconnecter ?"
        )
        msg.setDetailedText(str(error))

        # Add custom buttons
        reconnect_btn = msg.addButton("Reconnect / Reconnecter", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)

        msg.exec()

        if msg.clickedButton() == reconnect_btn:
            self._attempt_reconnection()

    def _attempt_reconnection(self):
        """Attempt to reconnect to the database and re-execute the query."""
        if not self.db_connection:
            DialogHelper.error("No database connection configured", parent=self)
            return

        # Find the DatabaseManager parent
        database_manager = self._find_database_manager()
        if not database_manager:
            DialogHelper.error("Cannot find DatabaseManager for reconnection", parent=self)
            return

        # Show reconnecting status
        self.result_info_label.setText("⏳ Reconnecting / Reconnexion en cours...")
        self.result_info_label.setStyleSheet("color: orange;")
        QApplication.processEvents()

        try:
            # Attempt reconnection via DatabaseManager
            new_connection = database_manager.reconnect_database(self.db_connection.id)

            if new_connection:
                # Update our connection reference
                self.connection = new_connection

                self.result_info_label.setText("✓ Reconnected successfully / Reconnexion réussie")
                self.result_info_label.setStyleSheet("color: green;")

                # Reload databases dropdown
                self._load_databases()

                # Ask if user wants to re-execute the query
                from PySide6.QtWidgets import QMessageBox
                result = QMessageBox.question(
                    self,
                    "Re-execute Query / Réexécuter la requête",
                    "Connection restored. Re-execute the last query?\n"
                    "Connexion rétablie. Réexécuter la dernière requête ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if result == QMessageBox.StandardButton.Yes:
                    self._execute_query()
            else:
                self.result_info_label.setText("✗ Reconnection failed / Échec de la reconnexion")
                self.result_info_label.setStyleSheet("color: red;")
                DialogHelper.error(
                    "Failed to reconnect to database.\n"
                    "Échec de la reconnexion à la base de données.\n\n"
                    "Please check your VPN connection.\n"
                    "Veuillez vérifier votre connexion VPN.",
                    parent=self
                )

        except Exception as e:
            self.result_info_label.setText("✗ Reconnection error")
            self.result_info_label.setStyleSheet("color: red;")
            DialogHelper.error("Reconnection failed", parent=self, details=str(e))
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
            DialogHelper.warning(
                "No query to save.\nAucune requête à enregistrer.",
                parent=self
            )
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
                        f"Query '{data['name']}' saved successfully.\n"
                        f"Requête '{data['name']}' enregistrée avec succès.",
                        parent=self
                    )
                    logger.info(f"Saved query: {data['name']} to category: {data['category']}")
                    # Emit signal to trigger refresh
                    self.query_saved.emit()
                else:
                    DialogHelper.error(
                        f"Failed to save query (database constraint).\n"
                        f"Échec de l'enregistrement (contrainte de base de données).\n\n"
                        f"Database ID: {data['target_database_id']}",
                        parent=self
                    )

            except Exception as e:
                logger.error(f"Error saving query: {e}")
                DialogHelper.error(
                    f"Failed to save query: {e}\n"
                    f"Échec de l'enregistrement: {e}",
                    parent=self
                )
