"""
Database Manager - Multi-tab SQL query interface (Refactored with BaseManagerView)
Provides interface to connect to databases and execute SQL queries
"""

from typing import Optional, Union, Dict, List, Any
import pyodbc
import sqlite3
import re
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QTextEdit, QSplitter, QPushButton, QLabel,
                               QTreeWidget, QTreeWidgetItem, QMenu)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QAction

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.custom_datagridview import CustomDataGridView
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, DatabaseConnection

import logging
logger = logging.getLogger(__name__)


class SQLEditorTab(QWidget):
    """Single SQL editor tab with query execution and results display."""

    def __init__(self, parent: Optional[QWidget] = None, connection_name: str = "",
                 db_conn_id: str = None, db_manager: 'DatabaseManager' = None):
        """
        Initialize SQL editor tab.

        Args:
            parent: Parent widget (optional)
            connection_name: Name of the database connection
            db_conn_id: Database connection ID
            db_manager: Reference to DatabaseManager parent
        """
        super().__init__(parent)
        self.connection_name = connection_name
        self.db_conn_id = db_conn_id
        self.db_manager = db_manager
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = ToolbarBuilder(self) \
            .add_button(tr("execute_query"), self._execute_query, icon="play.png") \
            .add_button(tr("format_sql"), self._format_sql, icon="format.png") \
            .add_button(tr("clear_query"), self._clear, icon="clear.png") \
            .add_separator() \
            .add_button(tr("export_results"), self._export_results, icon="export.png") \
            .build()
        layout.addWidget(toolbar)

        # Splitter (top: SQL editor, bottom: results)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # SQL editor
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText("-- " + tr("enter_sql_query_here"))
        splitter.addWidget(self.sql_editor)

        # Results grid
        self.results_grid = CustomDataGridView(show_toolbar=False)
        splitter.addWidget(self.results_grid)

        splitter.setSizes([300, 400])
        layout.addWidget(splitter)

    def _execute_query(self):
        """Execute SQL query and display results."""
        query_text = self.sql_editor.toPlainText().strip()

        if not query_text:
            DialogHelper.warning(tr("no_query_to_execute"), parent=self)
            return

        if not self.db_conn_id:
            DialogHelper.warning(tr("no_database_selected"), parent=self)
            return

        try:
            # Get connection from database manager
            conn = self.db_manager.get_connection(self.db_conn_id)
            if not conn:
                DialogHelper.error(tr("database_not_connected"), parent=self)
                return

            cursor = conn.cursor()
            cursor.execute(query_text)

            # Check if query returns results
            if cursor.description:
                # SELECT query - fetch results
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                # Display in grid
                self.results_grid.set_columns(columns)
                data = [[str(cell) if cell is not None else "" for cell in row] for row in results]
                self.results_grid.set_data(data)

                DialogHelper.info(tr("query_executed_successfully").format(rows=len(results)), parent=self)
            else:
                # INSERT/UPDATE/DELETE query - commit and show message
                conn.commit()
                DialogHelper.info(tr("query_executed_no_results"), parent=self)
                self.results_grid.clear()

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            DialogHelper.error(tr("query_execution_error"), parent=self, details=str(e))

    def _format_sql(self):
        """Format SQL text."""
        # TODO: Implement SQL formatting
        DialogHelper.info(tr("feature_coming_soon"), parent=self)

    def _clear(self):
        """Clear SQL editor and results."""
        self.sql_editor.clear()
        self.results_grid.clear()

    def _export_results(self):
        """Export results to CSV."""
        if self.results_grid.get_row_count() == 0:
            DialogHelper.warning(tr("no_results_to_export"), parent=self)
            return

        # Export is handled by CustomDataGridView
        self.results_grid._export_csv()

    def get_query_text(self) -> str:
        """Get current query text."""
        return self.sql_editor.toPlainText()

    def set_query_text(self, text: str):
        """Set query text."""
        self.sql_editor.setPlainText(text)


class DatabaseManager(BaseManagerView):
    """Multi-tab database query manager with schema tree (using BaseManagerView)."""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize database manager.

        Args:
            parent: Parent widget (optional)
        """
        self._tab_counter = 0
        self.connections: Dict[str, Union[pyodbc.Connection, sqlite3.Connection]] = {}
        self.schema_tree = None  # Will be populated in _setup_details

        super().__init__(parent, title="Database Manager", enable_details_panel=True)

        self._setup_toolbar()
        self._setup_details()
        self._setup_content()
        self.refresh()

    def _get_tree_columns(self) -> List[str]:
        """Return column names for database connections tree."""
        return [tr("database_name"), tr("database_type")]

    def _setup_toolbar(self):
        """Setup toolbar with database-specific buttons."""
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_new_tab"), self._new_tab, icon="add.png")
        toolbar_builder.add_button(tr("btn_refresh_schema"), self._refresh_schema, icon="refresh.png")

        # Replace default toolbar
        old_toolbar = self.toolbar
        self.toolbar = toolbar_builder.build()
        self.layout().replaceWidget(old_toolbar, self.toolbar)
        old_toolbar.setParent(None)

    def _setup_details(self):
        """Setup details panel with database schema tree."""
        # Schema tree label
        schema_label = QLabel(tr("schema_explorer_label"))
        schema_font = QFont()
        schema_font.setBold(True)
        schema_label.setFont(schema_font)
        self.details_layout.addWidget(schema_label)

        # Schema tree widget
        self.schema_tree = QTreeWidget()
        self.schema_tree.setHeaderHidden(True)
        self.schema_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.schema_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.schema_tree.itemDoubleClicked.connect(self._on_schema_tree_double_click)
        self.details_layout.addWidget(self.schema_tree)

    def _setup_content(self):
        """Setup content panel with query tabs."""
        # Tab widget for multiple SQL queries
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.setMovable(True)
        self.content_layout.addWidget(self.tabs)

        # Create initial welcome tab
        self._create_welcome_tab()

    def _create_welcome_tab(self):
        """Create welcome tab."""
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)

        welcome_label = QLabel(tr("welcome_database_manager"))
        welcome_font = QFont()
        welcome_font.setPointSize(16)
        welcome_font.setBold(True)
        welcome_label.setFont(welcome_font)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(welcome_label)

        info_label = QLabel(tr("click_new_tab_to_start"))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(info_label)

        welcome_layout.addStretch()

        self.tabs.addTab(welcome_widget, tr("welcome_tab"))

    def _load_items(self):
        """Load database connections into left tree view."""
        try:
            config_db = get_config_db()
            connections = config_db.get_all_database_connections()

            for conn_config in connections:
                # Add connection to tree
                self.tree_view.add_item(
                    parent=None,
                    text=[conn_config.name, conn_config.db_type.upper()],
                    data=conn_config
                )

                # Try to connect
                try:
                    if conn_config.db_type == "sqlite":
                        # SQLite connection
                        db_path = conn_config.connection_string.replace("sqlite:///", "")
                        if Path(db_path).exists():
                            connection = sqlite3.connect(db_path)
                            self.connections[conn_config.id] = connection
                    elif conn_config.db_type == "sqlserver":
                        # SQL Server connection
                        connection = pyodbc.connect(conn_config.connection_string)
                        self.connections[conn_config.id] = connection
                except Exception as e:
                    logger.warning(f"Could not connect to {conn_config.name}: {e}")

        except Exception as e:
            logger.error(f"Error loading database connections: {e}")
            DialogHelper.error(tr("error_loading_connections"), parent=self, details=str(e))

    def _display_item(self, item_data: Any):
        """
        Display selected database connection schema.

        Args:
            item_data: DatabaseConnection object
        """
        if not isinstance(item_data, DatabaseConnection):
            return

        # Load schema for this connection
        self._load_schema_for_connection(item_data)

    def _load_schema_for_connection(self, conn_config: DatabaseConnection):
        """Load and display database schema in schema tree."""
        self.schema_tree.clear()

        if conn_config.id not in self.connections:
            # Not connected
            no_conn_item = QTreeWidgetItem(self.schema_tree, [tr("database_not_connected")])
            return

        try:
            conn = self.connections[conn_config.id]
            cursor = conn.cursor()

            # Create root item for this database
            db_item = QTreeWidgetItem(self.schema_tree, [conn_config.name])
            db_item.setExpanded(True)

            if conn_config.db_type == "sqlite":
                # SQLite: Get tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = cursor.fetchall()

                tables_item = QTreeWidgetItem(db_item, ["Tables"])
                for table in tables:
                    table_name = table[0]
                    table_item = QTreeWidgetItem(tables_item, [table_name])
                    table_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "table",
                        "name": table_name,
                        "db_id": conn_config.id
                    })

                tables_item.setExpanded(True)

            elif conn_config.db_type == "sqlserver":
                # SQL Server: Get tables from sys.tables
                cursor.execute("""
                    SELECT s.name as schema_name, t.name as table_name
                    FROM sys.tables t
                    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
                    ORDER BY s.name, t.name
                """)
                tables = cursor.fetchall()

                # Group by schema
                schemas = {}
                for schema_name, table_name in tables:
                    if schema_name not in schemas:
                        schemas[schema_name] = []
                    schemas[schema_name].append(table_name)

                # Add schema nodes
                for schema_name, table_list in schemas.items():
                    schema_item = QTreeWidgetItem(db_item, [f"Schema: {schema_name}"])

                    for table_name in table_list:
                        full_name = f"{schema_name}.{table_name}"
                        table_item = QTreeWidgetItem(schema_item, [table_name])
                        table_item.setData(0, Qt.ItemDataRole.UserRole, {
                            "type": "table",
                            "name": full_name,
                            "db_id": conn_config.id
                        })

                    schema_item.setExpanded(True)

                db_item.setExpanded(True)

        except Exception as e:
            logger.error(f"Error loading schema for {conn_config.name}: {e}")
            error_item = QTreeWidgetItem(self.schema_tree, [f"Error: {str(e)}"])

    def _refresh_schema(self):
        """Refresh schema tree for currently selected database."""
        if self._current_item:
            self._display_item(self._current_item)
        else:
            DialogHelper.info(tr("select_database_first"), parent=self)

    def _on_tree_context_menu(self, position):
        """Handle context menu on schema tree."""
        item = self.schema_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "table":
            return

        menu = QMenu(self)

        select_100 = menu.addAction(tr("select_top_100"))
        select_1000 = menu.addAction(tr("select_top_1000"))
        select_10000 = menu.addAction(tr("select_top_10000"))
        menu.addSeparator()
        select_all = menu.addAction(tr("select_all"))

        action = menu.exec(self.schema_tree.mapToGlobal(position))

        if action:
            table_name = data["name"]
            db_id = data["db_id"]

            if action == select_100:
                query = f"SELECT TOP 100 * FROM {table_name}"
            elif action == select_1000:
                query = f"SELECT TOP 1000 * FROM {table_name}"
            elif action == select_10000:
                query = f"SELECT TOP 10000 * FROM {table_name}"
            elif action == select_all:
                query = f"SELECT * FROM {table_name}"
            else:
                return

            # Create new tab with query
            self._new_tab(db_id, query)

    def _on_schema_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on schema tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "table":
            table_name = data["name"]
            db_id = data["db_id"]
            query = f"SELECT TOP 100 * FROM {table_name}"
            self._new_tab(db_id, query)

    def _new_tab(self, db_conn_id: str = None, initial_query: str = ""):
        """
        Create new SQL editor tab.

        Args:
            db_conn_id: Database connection ID (optional)
            initial_query: Initial query text (optional)
        """
        # Remove welcome tab if it exists
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == tr("welcome_tab"):
                self.tabs.removeTab(i)
                break

        # Determine connection name
        if db_conn_id and db_conn_id in self.connections:
            # Find connection config
            config_db = get_config_db()
            connections = config_db.get_all_database_connections()
            conn_config = next((c for c in connections if c.id == db_conn_id), None)
            connection_name = conn_config.name if conn_config else tr("new_query")
        else:
            db_conn_id = self._current_item.id if self._current_item else None
            connection_name = self._current_item.name if self._current_item else tr("new_query")

        # Create new tab
        self._tab_counter += 1
        tab = SQLEditorTab(
            connection_name=connection_name,
            db_conn_id=db_conn_id,
            db_manager=self
        )

        if initial_query:
            tab.set_query_text(initial_query)

        tab_title = f"{connection_name} #{self._tab_counter}"
        self.tabs.addTab(tab, tab_title)
        self.tabs.setCurrentWidget(tab)

    def _close_tab(self, index: int):
        """Close a tab."""
        self.tabs.removeTab(index)

        # If no tabs left, show welcome tab
        if self.tabs.count() == 0:
            self._create_welcome_tab()

    def get_connection(self, db_conn_id: str) -> Optional[Union[pyodbc.Connection, sqlite3.Connection]]:
        """
        Get database connection by ID.

        Args:
            db_conn_id: Database connection ID

        Returns:
            Connection object or None
        """
        return self.connections.get(db_conn_id)
