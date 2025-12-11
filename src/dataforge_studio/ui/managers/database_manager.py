"""
Database Manager - Multi-tab SQL query interface
Provides interface to connect to databases and execute SQL queries
"""

from typing import Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QTextEdit, QSplitter, QPushButton, QComboBox, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.custom_datagridview import CustomDataGridView
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr


class SQLEditorTab(QWidget):
    """Single SQL editor tab with query execution and results display."""

    def __init__(self, parent: Optional[QWidget] = None, connection_name: str = ""):
        """
        Initialize SQL editor tab.

        Args:
            parent: Parent widget (optional)
            connection_name: Name of the database connection
        """
        super().__init__(parent)
        self.connection_name = connection_name
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Toolbar
        toolbar = ToolbarBuilder(self) \
            .add_button(tr("btn_execute"), self._execute_query, icon="play.png") \
            .add_button(tr("btn_format"), self._format_sql, icon="format.png") \
            .add_separator() \
            .add_button(tr("btn_clear"), self._clear_editor, icon="clear.png") \
            .add_button(tr("btn_export"), self._export_results, icon="export.png") \
            .build()
        layout.addWidget(toolbar)

        # Main splitter (vertical: top SQL editor, bottom results)
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: SQL editor
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        editor_label = QLabel(tr("sql_editor_label"))
        editor_layout.addWidget(editor_label)

        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText(tr("sql_editor_placeholder"))

        # Set monospace font for SQL
        sql_font = QFont("Consolas", 10)
        sql_font.setStyleHint(QFont.StyleHint.Monospace)
        self.sql_editor.setFont(sql_font)

        # TODO: Apply SQL syntax highlighting when available
        # from ...utils.sql_highlighter import SQLHighlighter
        # self.highlighter = SQLHighlighter(self.sql_editor.document())

        editor_layout.addWidget(self.sql_editor)
        main_splitter.addWidget(editor_container)

        # Bottom: Results grid
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)

        results_label = QLabel(tr("results_label"))
        results_layout.addWidget(results_label)

        self.results_grid = CustomDataGridView(show_toolbar=True)
        results_layout.addWidget(self.results_grid)
        main_splitter.addWidget(results_container)

        # Set proportions (40% editor, 60% results)
        main_splitter.setSizes([400, 600])

        layout.addWidget(main_splitter)

    def _execute_query(self):
        """Execute SQL query and display results."""
        query_text = self.sql_editor.toPlainText().strip()

        if not query_text:
            DialogHelper.warning(
                tr("empty_query_warning"),
                tr("execute_query_title"),
                self
            )
            return

        # TODO: Execute query through database connection
        # For now, show placeholder data
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("execute_query_title"),
            self
        )

        # Placeholder: Show sample results
        self.results_grid.set_columns(["ID", "Name", "Email", "Created"])
        sample_data = [
            ["1", "John Doe", "john@example.com", "2025-01-01"],
            ["2", "Jane Smith", "jane@example.com", "2025-01-02"],
            ["3", "Bob Johnson", "bob@example.com", "2025-01-03"]
        ]
        self.results_grid.set_data(sample_data)

    def _format_sql(self):
        """Format SQL query text."""
        query_text = self.sql_editor.toPlainText().strip()

        if not query_text:
            return

        # TODO: Use sqlparse to format SQL
        # import sqlparse
        # formatted = sqlparse.format(query_text, reindent=True, keyword_case='upper')
        # self.sql_editor.setPlainText(formatted)

        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("format_sql_title"),
            self
        )

    def _clear_editor(self):
        """Clear SQL editor and results."""
        if self.sql_editor.toPlainText().strip():
            if DialogHelper.confirm(
                tr("confirm_clear_editor"),
                tr("clear_editor_title"),
                self
            ):
                self.sql_editor.clear()
                self.results_grid.clear()

    def _export_results(self):
        """Export results to CSV."""
        if self.results_grid.get_row_count() == 0:
            DialogHelper.warning(
                tr("no_results_to_export"),
                tr("export_results_title"),
                self
            )
            return

        # Export is handled by CustomDataGridView's built-in export
        self.results_grid._export_csv()

    def get_query_text(self) -> str:
        """Get current query text."""
        return self.sql_editor.toPlainText()

    def set_query_text(self, text: str):
        """Set query text."""
        self.sql_editor.setPlainText(text)


class DatabaseManager(QWidget):
    """Multi-tab database query manager."""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize database manager.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self._tab_counter = 0
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Top toolbar with connection selector
        top_toolbar_layout = QHBoxLayout()

        # Connection selector
        connection_label = QLabel(tr("connection_label"))
        top_toolbar_layout.addWidget(connection_label)

        self.connection_combo = QComboBox()
        self.connection_combo.setMinimumWidth(200)
        self._load_connections()
        top_toolbar_layout.addWidget(self.connection_combo)

        # Connect button
        connect_btn = QPushButton(tr("btn_connect"))
        connect_btn.clicked.connect(self._connect_to_database)
        top_toolbar_layout.addWidget(connect_btn)

        # New tab button
        new_tab_btn = QPushButton(tr("btn_new_tab"))
        new_tab_btn.clicked.connect(self._new_tab)
        top_toolbar_layout.addWidget(new_tab_btn)

        top_toolbar_layout.addStretch()

        layout.addLayout(top_toolbar_layout)

        # Tab widget for multiple SQL editors
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.setMovable(True)
        layout.addWidget(self.tabs)

        # Create initial tab
        self._new_tab()

    def _load_connections(self):
        """Load available database connections."""
        # TODO: Load from config database
        # For now, add placeholder connections
        self.connection_combo.addItem(tr("no_connection"), None)
        self.connection_combo.addItem("Database 1 (SQL Server)", "db1")
        self.connection_combo.addItem("Database 2 (PostgreSQL)", "db2")
        self.connection_combo.addItem("Database 3 (SQLite)", "db3")

        # Real implementation:
        # try:
        #     from ...database.config_db import get_config_db
        #     config_db = get_config_db()
        #     connections = config_db.get_all_connections()
        #
        #     for conn in connections:
        #         self.connection_combo.addItem(
        #             f"{conn.name} ({conn.db_type})",
        #             conn.id
        #         )
        # except Exception as e:
        #     DialogHelper.error(
        #         tr("error_loading_connections"),
        #         tr("error_title"),
        #         self,
        #         details=str(e)
        #     )

    def _new_tab(self, connection_name: str = ""):
        """
        Create new SQL editor tab.

        Args:
            connection_name: Name of the database connection (optional)
        """
        self._tab_counter += 1

        if not connection_name:
            connection_name = self.connection_combo.currentText()
            if connection_name == tr("no_connection"):
                connection_name = f"{tr('new_query')} {self._tab_counter}"

        tab = SQLEditorTab(connection_name=connection_name)
        tab_index = self.tabs.addTab(tab, connection_name)
        self.tabs.setCurrentIndex(tab_index)

    def _close_tab(self, index: int):
        """
        Close a tab.

        Args:
            index: Tab index to close
        """
        # Check if tab has unsaved content
        tab = self.tabs.widget(index)
        if isinstance(tab, SQLEditorTab):
            query_text = tab.get_query_text().strip()
            if query_text:
                if not DialogHelper.confirm(
                    tr("confirm_close_tab"),
                    tr("close_tab_title"),
                    self
                ):
                    return

        self.tabs.removeTab(index)

        # Ensure at least one tab remains
        if self.tabs.count() == 0:
            self._new_tab()

    def _connect_to_database(self):
        """Connect to selected database."""
        connection_data = self.connection_combo.currentData()
        connection_name = self.connection_combo.currentText()

        if connection_data is None:
            DialogHelper.warning(
                tr("select_connection_first"),
                tr("connect_title"),
                self
            )
            return

        # TODO: Establish database connection
        DialogHelper.info(
            tr("connection_success").format(name=connection_name),
            tr("connect_title"),
            self
        )

        # Real implementation:
        # try:
        #     from ...database.connections import establish_connection
        #     connection = establish_connection(connection_data)
        #
        #     # Store connection for use in queries
        #     self._current_connection = connection
        #
        #     DialogHelper.info(
        #         tr("connection_success").format(name=connection_name),
        #         tr("connect_title"),
        #         self
        #     )
        # except Exception as e:
        #     DialogHelper.error(
        #         tr("connection_failed"),
        #         tr("connect_title"),
        #         self,
        #         details=str(e)
        #     )

    def get_current_tab(self) -> Optional[SQLEditorTab]:
        """Get currently active SQL editor tab."""
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, SQLEditorTab):
            return current_widget
        return None
