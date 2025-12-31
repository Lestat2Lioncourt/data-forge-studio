"""
DataViewerWidget - Viewer for database tables and saved queries.

Structure:
- Top panel with 2 tabs:
  - Query tab: SQL editor/viewer
  - Details tab: metadata (empty for table exploration, filled for saved queries)
- Bottom: Results grid (CustomDataGridView)
"""

from typing import Optional, Any
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QTextEdit, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from .form_builder import FormBuilder
from .custom_datagridview import CustomDataGridView
from .dialog_helper import DialogHelper

from ...core.data_loader import (
    query_to_dataframe,
    DataLoadResult,
    LoadWarningLevel,
    LARGE_DATASET_THRESHOLD
)

logger = logging.getLogger(__name__)


class DataViewerWidget(QWidget):
    """
    Unified viewer for database tables and saved queries.

    For table exploration:
        - Query tab shows: SELECT * FROM table LIMIT 100
        - Details tab is empty/disabled

    For saved queries:
        - Query tab shows the saved SQL
        - Details tab shows: name, description, target database, etc.
    """

    # Signals
    query_executed = Signal(object)  # Emits DataLoadResult

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._current_connection = None
        self._current_query = None  # SavedQuery object if any
        self._current_table = None
        self._is_saved_query = False

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI with tabs and results grid."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Main splitter: top (tabs) / bottom (results)
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: Tab widget with Query and Details tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # Query tab
        query_tab = QWidget()
        query_layout = QVBoxLayout(query_tab)
        query_layout.setContentsMargins(5, 5, 5, 5)

        # SQL editor (read-only by default for viewing)
        self.sql_editor = QTextEdit()
        self.sql_editor.setFont(QFont("Consolas", 10))
        self.sql_editor.setPlaceholderText("SELECT * FROM ...")
        self.sql_editor.setReadOnly(True)
        query_layout.addWidget(self.sql_editor)

        # Execute button bar
        button_bar = QHBoxLayout()
        button_bar.addStretch()

        self.execute_btn = QPushButton("Execute")
        self.execute_btn.clicked.connect(self._on_execute_clicked)
        button_bar.addWidget(self.execute_btn)

        query_layout.addLayout(button_bar)

        self.tab_widget.addTab(query_tab, "Query")

        # Details tab
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.setContentsMargins(5, 5, 5, 5)

        self.details_form_builder = FormBuilder(title="") \
            .add_field("Name:", "name") \
            .add_field("Description:", "description") \
            .add_field("Database:", "database") \
            .add_field("Created:", "created") \
            .add_field("Updated:", "updated")

        details_widget = self.details_form_builder.build()
        details_layout.addWidget(details_widget)
        details_layout.addStretch()

        # Placeholder for when no saved query
        self.no_details_label = QLabel("No saved query - table exploration mode")
        self.no_details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_details_label.setStyleSheet("color: gray; font-style: italic;")
        details_layout.addWidget(self.no_details_label)

        self.tab_widget.addTab(details_tab, "Details")

        self.splitter.addWidget(self.tab_widget)

        # Bottom: Results grid
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 5, 0, 0)

        results_label = QLabel("Results")
        results_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(results_label)

        self.results_grid = CustomDataGridView()
        results_layout.addWidget(self.results_grid)

        # Row count label
        self.row_count_label = QLabel("")
        self.row_count_label.setStyleSheet("color: gray; font-size: 9pt;")
        results_layout.addWidget(self.row_count_label)

        self.splitter.addWidget(results_container)

        # Set splitter proportions (30% tabs, 70% results)
        self.splitter.setSizes([200, 500])

        layout.addWidget(self.splitter)

    def show_table(self, connection: Any, table_name: str, schema: str = None, db_type: str = None):
        """
        Show table exploration mode.

        Args:
            connection: Database connection
            table_name: Table name
            schema: Optional schema name (or db_name for SQL Server)
            db_type: Database type (sqlite, sqlserver, postgresql, etc.)
        """
        self._current_connection = connection
        self._current_table = table_name
        self._current_query = None
        self._is_saved_query = False

        # Build SQL based on database type
        if db_type == "sqlserver" and schema:
            # SQL Server: [database].[schema].[table] format
            full_table = f"[{schema}].{table_name}"
            sql = f"SELECT TOP 100 * FROM {full_table}"
        elif db_type == "sqlserver":
            sql = f"SELECT TOP 100 * FROM {table_name}"
        elif schema:
            full_table = f"{schema}.{table_name}"
            sql = f"SELECT * FROM {full_table} LIMIT 100"
        else:
            sql = f"SELECT * FROM {table_name} LIMIT 100"

        # Update Query tab
        self.sql_editor.setPlainText(sql)
        self.sql_editor.setReadOnly(True)

        # Update Details tab (empty for table exploration)
        self._show_no_details()

        # Execute query
        self._execute_sql(sql, connection)

        # Switch to Query tab
        self.tab_widget.setCurrentIndex(0)

    def show_query(self, query: Any, connection: Any = None):
        """
        Show a saved query with details.

        Args:
            query: SavedQuery object
            connection: Optional database connection
        """
        self._current_query = query
        self._current_connection = connection
        self._current_table = None
        self._is_saved_query = True

        # Update Query tab with saved SQL
        sql = getattr(query, 'sql_content', '') or getattr(query, 'query_text', '') or ''
        self.sql_editor.setPlainText(sql)
        self.sql_editor.setReadOnly(True)

        # Update Details tab
        self._show_query_details(query)

        # If connection provided, execute the query
        if connection and sql:
            self._execute_sql(sql, connection)

        # Switch to Query tab
        self.tab_widget.setCurrentIndex(0)

    def execute_query(self, sql: str, connection: Any, query: Any = None):
        """
        Execute SQL and display results.

        Args:
            sql: SQL query string
            connection: Database connection
            query: Optional SavedQuery for details
        """
        self._current_connection = connection
        self._current_query = query

        # Update Query tab
        self.sql_editor.setPlainText(sql)
        self.sql_editor.setReadOnly(True)

        # Update Details tab
        if query:
            self._is_saved_query = True
            self._show_query_details(query)
        else:
            self._is_saved_query = False
            self._show_no_details()

        # Execute
        self._execute_sql(sql, connection)

    def _show_query_details(self, query: Any):
        """Show saved query details in Details tab."""
        self.no_details_label.hide()

        # Get attributes safely
        name = getattr(query, 'name', '-')
        description = getattr(query, 'description', '-') or '-'

        # Get database name
        database = '-'
        if hasattr(query, 'target_database_id') and query.target_database_id:
            # Try to get database name from connection
            database = query.target_database_id  # Could be resolved to name later

        created = '-'
        if hasattr(query, 'created_at') and query.created_at:
            try:
                from datetime import datetime
                created = datetime.fromisoformat(query.created_at).strftime("%Y-%m-%d %H:%M:%S")
            except:
                created = query.created_at

        updated = '-'
        if hasattr(query, 'updated_at') and query.updated_at:
            try:
                from datetime import datetime
                updated = datetime.fromisoformat(query.updated_at).strftime("%Y-%m-%d %H:%M:%S")
            except:
                updated = query.updated_at

        self.details_form_builder.set_value("name", name)
        self.details_form_builder.set_value("description", description)
        self.details_form_builder.set_value("database", database)
        self.details_form_builder.set_value("created", created)
        self.details_form_builder.set_value("updated", updated)

    def _show_no_details(self):
        """Show placeholder when no saved query (table exploration mode)."""
        self.no_details_label.show()
        self.details_form_builder.clear()

    def _execute_sql(self, sql: str, connection: Any):
        """Execute SQL and populate results grid."""
        if not sql or not connection:
            self.results_grid.clear()
            self.row_count_label.setText("")
            return

        try:
            # Use centralized data loader
            result = query_to_dataframe(
                connection=connection,
                sql=sql,
                on_large_dataset=self._handle_large_dataset_warning
            )

            if not result.success:
                if result.error:
                    DialogHelper.error("Query execution failed", details=str(result.error))
                self.results_grid.clear()
                self.row_count_label.setText("Error")
                return

            # Display results
            df = result.dataframe
            if df is not None and not df.empty:
                self.results_grid.set_dataframe(df)
                self.row_count_label.setText(f"{result.row_count:,} rows, {result.column_count} columns")
                logger.info(f"Query returned {result.row_count} rows")
            else:
                self.results_grid.clear()
                self.row_count_label.setText("No results")

            self.query_executed.emit(result)

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            DialogHelper.error("Query execution failed", details=str(e))
            self.results_grid.clear()
            self.row_count_label.setText("Error")

    def _on_execute_clicked(self):
        """Handle Execute button click."""
        sql = self.sql_editor.toPlainText().strip()
        if sql and self._current_connection:
            self._execute_sql(sql, self._current_connection)
        else:
            DialogHelper.warning("No SQL query or connection available")

    def _handle_large_dataset_warning(self, row_count: int) -> bool:
        """Handle warning for large datasets."""
        from PySide6.QtWidgets import QMessageBox

        row_count_fmt = f"{row_count:,}"
        threshold_fmt = f"{LARGE_DATASET_THRESHOLD:,}"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Large Dataset Warning")
        msg.setText(f"This query returns {row_count_fmt} rows.")
        msg.setInformativeText(
            f"Loading more than {threshold_fmt} rows may:\n"
            f"- Be slow to load\n"
            f"- Consume significant memory\n"
            f"- Slow down the interface\n\n"
            f"Do you want to continue?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        result = msg.exec()
        return result == QMessageBox.StandardButton.Yes

    def clear(self):
        """Clear all content."""
        self._current_connection = None
        self._current_query = None
        self._current_table = None

        self.sql_editor.clear()
        self.results_grid.clear()
        self.row_count_label.setText("")
        self._show_no_details()

    def get_current_sql(self) -> str:
        """Get current SQL from editor."""
        return self.sql_editor.toPlainText()

    def set_sql_editable(self, editable: bool):
        """Set whether SQL can be edited."""
        self.sql_editor.setReadOnly(not editable)
