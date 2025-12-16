"""
Database Manager - Multi-tab SQL query interface (Refactored with BaseManagerView)
Provides interface to connect to databases and execute SQL queries
"""

from typing import Optional, Union, Dict, List, Any
import pyodbc
import sqlite3
import sqlparse
import re
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.custom_datagridview import CustomDataGridView
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, DatabaseConnection

import logging
logger = logging.getLogger(__name__)


class DatabaseManager(BaseManagerView):
    """
    SSMS-style database query manager.

    Layout:
    - LEFT PANEL: Hierarchical tree (Server > Database > Tables/Views > Columns)
    - RIGHT TOP PANEL: SQL query editor
    - RIGHT BOTTOM PANEL: Query results grid
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize database manager.

        Args:
            parent: Parent widget (optional)
        """
        self.connections: Dict[str, Union[pyodbc.Connection, sqlite3.Connection]] = {}
        self.current_db_id = None  # Track current database connection

        # SSMS style: left tree, right top = SQL editor, right bottom = results
        super().__init__(parent, title="Database Manager", enable_details_panel=True)

        self._setup_toolbar()
        self._setup_details()  # SQL editor
        self._setup_content()  # Results grid
        self.refresh()

    def _get_tree_columns(self) -> List[str]:
        """Return single column for SSMS-style hierarchical tree."""
        return ["Objects"]  # Single column for server/database/table/column hierarchy

    def _setup_toolbar(self):
        """Setup toolbar with database-specific buttons."""
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_refresh_schema"), self._refresh_schema, icon="refresh.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("execute_query"), self._execute_query, icon="play.png")
        toolbar_builder.add_button(tr("clear_query"), self._clear_query, icon="clear.png")

        # Replace default toolbar
        old_toolbar = self.toolbar
        self.toolbar = toolbar_builder.build()
        self.layout().replaceWidget(old_toolbar, self.toolbar)
        old_toolbar.setParent(None)

    def _setup_details(self):
        """Setup details panel with SQL editor (RIGHT TOP)."""
        # Format buttons toolbar
        from PySide6.QtWidgets import QHBoxLayout
        format_toolbar = QHBoxLayout()

        compact_btn = QPushButton("Compact")
        compact_btn.clicked.connect(lambda: self._format_sql("compact"))
        compact_btn.setToolTip("Compact style - Multiple columns on same line")
        format_toolbar.addWidget(compact_btn)

        expanded_btn = QPushButton("Expanded")
        expanded_btn.clicked.connect(lambda: self._format_sql("expanded"))
        expanded_btn.setToolTip("Expanded style - One column per line")
        format_toolbar.addWidget(expanded_btn)

        comma_first_btn = QPushButton("Comma First")
        comma_first_btn.clicked.connect(lambda: self._format_sql("comma_first"))
        comma_first_btn.setToolTip("Comma First style - Commas at beginning of line")
        format_toolbar.addWidget(comma_first_btn)

        sophisticated_btn = QPushButton("Sophisticated")
        sophisticated_btn.clicked.connect(lambda: self._format_sql("sophisticated"))
        sophisticated_btn.setToolTip("Sophisticated style - Advanced alignment")
        format_toolbar.addWidget(sophisticated_btn)

        format_toolbar.addStretch()
        self.details_layout.addLayout(format_toolbar)

        # SQL editor
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText("-- " + tr("enter_sql_query_here"))
        self.sql_editor.setFont(QFont("Consolas", 10))

        # Apply SQL syntax highlighting
        from ...utils.sql_highlighter import SQLHighlighter
        self.sql_highlighter = SQLHighlighter(self.sql_editor.document())

        self.details_layout.addWidget(self.sql_editor)

    def _setup_content(self):
        """Setup content panel with results grid (RIGHT BOTTOM)."""
        # Results grid
        self.results_grid = CustomDataGridView(show_toolbar=True)
        self.content_layout.addWidget(self.results_grid)

    def _load_items(self):
        """Load database servers with full hierarchy (SSMS-style)."""
        try:
            config_db = get_config_db()
            connections = config_db.get_all_database_connections()

            for conn_config in connections:
                # Create server node with DB type icon
                server_item = self.tree_view.add_item(
                    parent=None,
                    text=[f"{conn_config.name} ({conn_config.db_type.upper()})"],
                    data={"type": "server", "config": conn_config}
                )

                # Try to connect and load schema hierarchy
                try:
                    if conn_config.db_type == "sqlite":
                        db_path = conn_config.connection_string.replace("sqlite:///", "")
                        if Path(db_path).exists():
                            connection = sqlite3.connect(db_path)
                            self.connections[conn_config.id] = connection
                            self._load_sqlite_schema(server_item, connection, conn_config)
                    elif conn_config.db_type == "sqlserver":
                        connection = pyodbc.connect(conn_config.connection_string)
                        self.connections[conn_config.id] = connection
                        self._load_sqlserver_schema(server_item, connection, conn_config)
                except Exception as e:
                    logger.warning(f"Could not connect to {conn_config.name}: {e}")
                    error_item = self.tree_view.add_item(
                        parent=server_item,
                        text=[f"Error: {str(e)}"],
                        data={"type": "error"}
                    )

        except Exception as e:
            logger.error(f"Error loading database connections: {e}")
            DialogHelper.error(tr("error_loading_connections"), parent=self, details=str(e))

    def _load_sqlite_schema(self, server_item, connection, conn_config):
        """Load SQLite schema hierarchy under server node."""
        cursor = connection.cursor()

        # Tables node
        tables_node = self.tree_view.add_item(
            parent=server_item,
            text=["Tables"],
            data={"type": "tables_folder", "db_id": conn_config.id}
        )

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            table_item = self.tree_view.add_item(
                parent=tables_node,
                text=[table_name],
                data={"type": "table", "name": table_name, "db_id": conn_config.id}
            )

            # Load columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                self.tree_view.add_item(
                    parent=table_item,
                    text=[f"{col_name} ({col_type})"],
                    data={"type": "column", "table": table_name, "column": col_name, "col_type": col_type}
                )

        # Views node
        views_node = self.tree_view.add_item(
            parent=server_item,
            text=["Views"],
            data={"type": "views_folder", "db_id": conn_config.id}
        )

        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()
        for view in views:
            self.tree_view.add_item(
                parent=views_node,
                text=[view[0]],
                data={"type": "view", "name": view[0], "db_id": conn_config.id}
            )

    def _load_sqlserver_schema(self, server_item, connection, conn_config):
        """Load SQL Server schema hierarchy under server node."""
        cursor = connection.cursor()

        # Get databases
        try:
            cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4 ORDER BY name")
            databases = cursor.fetchall()
        except:
            # If can't query sys.databases, use current database
            databases = [(connection.getinfo(pyodbc.SQL_DATABASE_NAME),)]

        for db in databases:
            db_name = db[0]
            db_node = self.tree_view.add_item(
                parent=server_item,
                text=[db_name],
                data={"type": "database", "name": db_name, "db_id": conn_config.id}
            )

            try:
                # Tables node
                tables_node = self.tree_view.add_item(
                    parent=db_node,
                    text=["Tables"],
                    data={"type": "tables_folder", "db_id": conn_config.id, "db_name": db_name}
                )

                # Get tables
                cursor.execute(f"""
                    SELECT s.name as schema_name, t.name as table_name
                    FROM [{db_name}].sys.tables t
                    INNER JOIN [{db_name}].sys.schemas s ON t.schema_id = s.schema_id
                    ORDER BY s.name, t.name
                """)
                tables = cursor.fetchall()

                for schema_name, table_name in tables:
                    full_name = f"{schema_name}.{table_name}"
                    table_item = self.tree_view.add_item(
                        parent=tables_node,
                        text=[f"{schema_name}.{table_name}"],
                        data={"type": "table", "name": full_name, "db_id": conn_config.id, "db_name": db_name}
                    )

                    # Load columns with size information
                    cursor.execute(f"""
                        SELECT c.name, ty.name, c.max_length, c.precision, c.scale
                        FROM [{db_name}].sys.columns c
                        INNER JOIN [{db_name}].sys.types ty ON c.user_type_id = ty.user_type_id
                        INNER JOIN [{db_name}].sys.tables t ON c.object_id = t.object_id
                        INNER JOIN [{db_name}].sys.schemas s ON t.schema_id = s.schema_id
                        WHERE t.name = '{table_name}' AND s.name = '{schema_name}'
                        ORDER BY c.column_id
                    """)
                    columns = cursor.fetchall()
                    for col_name, col_type, max_length, precision, scale in columns:
                        # Format type with size
                        type_display = col_type
                        if col_type in ('nvarchar', 'nchar'):
                            if max_length == -1:
                                type_display = f"{col_type}(MAX)"
                            elif max_length > 0:
                                type_display = f"{col_type}({max_length // 2})"  # nvarchar uses 2 bytes per char
                        elif col_type in ('varchar', 'char', 'binary', 'varbinary'):
                            if max_length == -1:
                                type_display = f"{col_type}(MAX)"
                            elif max_length > 0:
                                type_display = f"{col_type}({max_length})"
                        elif col_type in ('decimal', 'numeric'):
                            type_display = f"{col_type}({precision},{scale})"

                        self.tree_view.add_item(
                            parent=table_item,
                            text=[f"{col_name} ({type_display})"],
                            data={"type": "column", "table": full_name, "column": col_name, "col_type": type_display}
                        )

                # Views node
                views_node = self.tree_view.add_item(
                    parent=db_node,
                    text=["Views"],
                    data={"type": "views_folder", "db_id": conn_config.id, "db_name": db_name}
                )

                cursor.execute(f"""
                    SELECT s.name, v.name
                    FROM [{db_name}].sys.views v
                    INNER JOIN [{db_name}].sys.schemas s ON v.schema_id = s.schema_id
                    ORDER BY s.name, v.name
                """)
                views = cursor.fetchall()
                for schema_name, view_name in views:
                    self.tree_view.add_item(
                        parent=views_node,
                        text=[f"{schema_name}.{view_name}"],
                        data={"type": "view", "name": f"{schema_name}.{view_name}", "db_id": conn_config.id, "db_name": db_name}
                    )

            except Exception as e:
                logger.warning(f"Could not load schema for database {db_name}: {e}")

    def _display_item(self, item_data: Any):
        """
        Handle tree item selection.
        For tables/views, nothing happens on single click (only on double-click).

        Args:
            item_data: Node data (dict with "type" key)
        """
        # Nothing to display in detail - all info is in the tree
        pass

    def _on_tree_double_click(self, item, column: int):
        """
        Handle double-click on tree items.
        For tables/views, insert SELECT query into SQL editor.

        Args:
            item: QTreeWidgetItem
            column: Column index
        """
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if not data:
            return

        node_type = data.get("type", "")

        if node_type == "table":
            # Generate SELECT query for table
            table_name = data["name"]
            self.current_db_id = data.get("db_id")
            query = f"SELECT TOP 100 * FROM {table_name}"
            self.sql_editor.setPlainText(query)

        elif node_type == "view":
            # Generate SELECT query for view
            view_name = data["name"]
            self.current_db_id = data.get("db_id")
            query = f"SELECT TOP 100 * FROM {view_name}"
            self.sql_editor.setPlainText(query)

        elif node_type == "server":
            # Set current database connection
            conn_config = data.get("config")
            if conn_config:
                self.current_db_id = conn_config.id

    def _execute_query(self):
        """Execute SQL query from editor and display results in grid."""
        query_text = self.sql_editor.toPlainText().strip()

        if not query_text:
            DialogHelper.warning(tr("no_query_to_execute"), parent=self)
            return

        if not self.current_db_id:
            DialogHelper.warning(tr("no_database_selected"), parent=self)
            return

        if self.current_db_id not in self.connections:
            DialogHelper.error(tr("database_not_connected"), parent=self)
            return

        try:
            conn = self.connections[self.current_db_id]
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

    def _clear_query(self):
        """Clear SQL editor and results grid."""
        self.sql_editor.clear()
        self.results_grid.clear()

    def _refresh_schema(self):
        """Refresh entire schema tree."""
        self.refresh()

    def _format_sql(self, style: str):
        """
        Format SQL query in editor with specified style.

        Args:
            style: Formatting style ("compact", "expanded", "comma_first", "sophisticated")
        """
        query_text = self.sql_editor.toPlainText().strip()

        if not query_text:
            DialogHelper.warning(tr("no_query_to_format"), parent=self)
            return

        try:
            if style == "compact":
                # Compact: multiple columns on same line (more compact)
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=2,
                    indent_tabs=False,
                    use_space_around_operators=True,
                    wrap_after=120,  # Longer lines allowed
                    comma_first=False
                )

            elif style == "expanded":
                # Expanded: one column per line (maximum readability)
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=4,
                    indent_tabs=False,
                    use_space_around_operators=True,
                    comma_first=False
                )
                # Post-process to force one column per line in SELECT
                formatted = self._force_one_column_per_line(formatted)

            elif style == "comma_first":
                # Comma First: commas at beginning of line
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=4,
                    indent_tabs=False,
                    use_space_around_operators=True,
                    comma_first=True
                )

            elif style == "sophisticated":
                # Sophisticated: advanced alignment
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=4,
                    indent_tabs=False,
                    use_space_around_operators=True
                )
                # Apply sophisticated formatting (aligned columns, operators, etc.)
                formatted = self._apply_sophisticated_formatting(formatted)

            else:
                # Default to expanded
                formatted = sqlparse.format(
                    query_text,
                    reindent=True,
                    keyword_case='upper',
                    indent_width=4,
                    indent_tabs=False,
                    use_space_around_operators=True
                )

            # Update editor with formatted SQL
            self.sql_editor.setPlainText(formatted)

        except Exception as e:
            logger.error(f"SQL formatting error: {e}")
            DialogHelper.error(tr("sql_format_error"), parent=self, details=str(e))

    def _force_one_column_per_line(self, sql_text: str) -> str:
        """Force SELECT columns to be on separate lines."""
        lines = sql_text.split('\n')
        result = []

        in_select = False
        for line in lines:
            stripped = line.strip().upper()

            # Detect start of SELECT
            if stripped.startswith('SELECT'):
                in_select = True
                # Split columns if they're on the same line as SELECT
                if ',' in line:
                    parts = line.split(',')
                    result.append(parts[0])  # SELECT with first column
                    for part in parts[1:]:
                        # Maintain indentation
                        indent = '    '  # 4 spaces
                        result.append(f"{indent}, {part.strip()}")
                else:
                    result.append(line)

            # Detect end of SELECT clause
            elif in_select and (stripped.startswith('FROM') or stripped.startswith('WHERE') or
                               stripped.startswith('ORDER BY') or stripped.startswith('GROUP BY')):
                in_select = False
                result.append(line)

            # Inside SELECT: split comma-separated columns
            elif in_select and ',' in line:
                parts = line.split(',')
                for i, part in enumerate(parts):
                    if i == 0:
                        result.append(part.rstrip())
                    else:
                        # Get indentation from original line
                        indent = len(line) - len(line.lstrip())
                        result.append(f"{' ' * indent}, {part.strip()}")

            else:
                result.append(line)

        return '\n'.join(result)

    def _apply_sophisticated_formatting(self, sql_text: str) -> str:
        """Apply sophisticated formatting with aligned columns and operators."""
        lines = sql_text.split('\n')
        result = []

        # Parse SELECT columns to align AS clauses
        in_select = False
        select_lines = []

        for line in lines:
            stripped = line.strip().upper()

            if stripped.startswith('SELECT'):
                in_select = True
                select_lines = [line]
            elif in_select and (stripped.startswith('FROM') or stripped.startswith('WHERE') or
                               stripped.startswith('ORDER BY') or stripped.startswith('GROUP BY') or
                               stripped.startswith('HAVING') or stripped.startswith('LIMIT')):
                # End of SELECT, apply alignment
                aligned = self._align_select_columns(select_lines)
                result.extend(aligned)
                in_select = False
                select_lines = []
                result.append(line)
            elif in_select:
                select_lines.append(line)
            else:
                result.append(line)

        # Handle case where SELECT goes to end of query
        if select_lines:
            aligned = self._align_select_columns(select_lines)
            result.extend(aligned)

        return '\n'.join(result)

    def _align_select_columns(self, lines: List[str]) -> List[str]:
        """Align AS clauses in SELECT columns."""
        if not lines:
            return lines

        # Find all AS positions
        as_positions = []
        for line in lines:
            upper_line = line.upper()
            as_pos = upper_line.find(' AS ')
            if as_pos != -1:
                as_positions.append(as_pos)

        if not as_positions:
            return lines

        # Calculate target AS position (max position)
        target_as_pos = max(as_positions)

        # Align lines
        result = []
        for line in lines:
            upper_line = line.upper()
            as_pos = upper_line.find(' AS ')

            if as_pos != -1:
                # Split at AS
                before_as = line[:as_pos]
                after_as = line[as_pos + 4:]  # +4 to skip ' AS '

                # Calculate padding
                padding = target_as_pos - as_pos
                result.append(f"{before_as}{' ' * padding} AS {after_as}")
            else:
                result.append(line)

        return result

    def get_connection(self, db_conn_id: str) -> Optional[Union[pyodbc.Connection, sqlite3.Connection]]:
        """
        Get database connection by ID.

        Args:
            db_conn_id: Database connection ID

        Returns:
            Connection object or None
        """
        return self.connections.get(db_conn_id)
