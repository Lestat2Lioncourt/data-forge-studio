"""
Context Menu Mixin - Tree context menus and double-click handling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction

from ...widgets.dialog_helper import DialogHelper
from ...widgets.distribution_analysis_dialog import DistributionAnalysisDialog
from ...core.i18n_bridge import tr
from ....constants import QUERY_PREVIEW_LIMIT, ANALYSIS_ROW_LIMIT

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTreeWidgetItem

logger = logging.getLogger(__name__)


class DatabaseContextMenuMixin:
    """Mixin providing context menu and double-click handling for the schema tree."""

    def _on_tree_context_menu(self, position: QPoint):
        """Show context menu on tree item right-click"""
        item = self.schema_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        node_type = data.get("type", "")

        menu = QMenu(self.schema_tree)

        # Context menu for server (connection)
        if node_type == "server":
            # New Query tab
            db_config = data.get("config")
            if db_config:
                new_query_action = QAction("New Query", self)
                new_query_action.triggered.connect(lambda checked, did=db_config.id: self._new_query_tab(did))
                menu.addAction(new_query_action)
                menu.addSeparator()

            # Edit connection (full dialog with credentials)
            edit_conn_action = QAction("Edit Connection...", self)
            edit_conn_action.triggered.connect(lambda: self._edit_full_connection(data["config"]))
            menu.addAction(edit_conn_action)

            # Edit name/description only
            edit_action = QAction("Edit Name & Description", self)
            edit_action.triggered.connect(lambda: self._edit_connection(data["config"]))
            menu.addAction(edit_action)

            # Change color
            color_action = QAction(tr("conn_change_color"), self)
            color_action.triggered.connect(lambda: self._change_connection_color(data["config"]))
            menu.addAction(color_action)

            menu.addSeparator()

            # Add to Workspace submenu (server = all databases)
            if db_config:
                workspace_menu = self._build_workspace_submenu(db_config.id, database_name=None)
                menu.addMenu(workspace_menu)

            menu.addSeparator()

            refresh_action = QAction("Refresh", self)
            refresh_action.triggered.connect(self._refresh_schema)
            menu.addAction(refresh_action)

            menu.addSeparator()

            # Delete connection
            delete_action = QAction("\U0001f5d1\ufe0f Delete Connection", self)
            delete_action.triggered.connect(lambda: self._delete_connection(data["config"]))
            menu.addAction(delete_action)

            menu.addSeparator()

            # Export connection
            export_action = QAction("\U0001f4e4 Export Connection...", self)
            export_action.triggered.connect(lambda: self._export_connection(data["config"]))
            menu.addAction(export_action)

            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

        # Context menu for individual database (SQL Server)
        elif node_type == "database":
            db_id = data.get("db_id")
            db_name = data.get("name")

            if db_id and db_name:
                # New Query tab
                new_query_action = QAction("New Query", self)
                new_query_action.triggered.connect(lambda checked, did=db_id: self._new_query_tab(did))
                menu.addAction(new_query_action)

                menu.addSeparator()

                # Add to Workspace submenu (specific database)
                workspace_menu = self._build_workspace_submenu(db_id, database_name=db_name)
                menu.addMenu(workspace_menu)

                menu.exec(self.schema_tree.viewport().mapToGlobal(position))

        # Context menu for tables and views
        elif node_type in ["table", "view"]:
            # SELECT * action
            select_all_action = QAction("SELECT *", self)
            select_all_action.triggered.connect(lambda: self._generate_select_query(data, limit=None))
            menu.addAction(select_all_action)

            # SELECT TOP 100 action
            select_top_action = QAction("SELECT TOP 100 *", self)
            select_top_action.triggered.connect(lambda: self._generate_select_query(data, limit=QUERY_PREVIEW_LIMIT))
            menu.addAction(select_top_action)

            # SELECT COLUMNS action
            select_cols_action = QAction("SELECT COLUMNS...", self)
            select_cols_action.triggered.connect(lambda checked, d=data: self._generate_select_columns_query(d))
            menu.addAction(select_cols_action)

            menu.addSeparator()

            # Edit Code for views only
            if node_type == "view":
                edit_code_action = QAction("\u270f\ufe0f Edit Code (ALTER VIEW)", self)
                edit_code_action.triggered.connect(lambda: self._load_view_code(data))
                menu.addAction(edit_code_action)
                menu.addSeparator()

            # Distribution Analysis action
            dist_action = QAction("\U0001f4ca Distribution Analysis", self)
            dist_action.triggered.connect(lambda: self._show_distribution_analysis(data))
            menu.addAction(dist_action)

            # Show menu at cursor position
            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

        # Context menu for stored procedures
        elif node_type == "procedure":
            # View code
            view_code_action = QAction("\U0001f4c4 View Code", self)
            view_code_action.triggered.connect(lambda: self._load_routine_code(data))
            menu.addAction(view_code_action)

            menu.addSeparator()

            # Generate EXEC template
            exec_action = QAction("\u26a1 Generate EXEC Template", self)
            exec_action.triggered.connect(lambda: self._generate_exec_template(data))
            menu.addAction(exec_action)

            # Copy name
            copy_name_action = QAction("\U0001f4cb Copy Name", self)
            copy_name_action.triggered.connect(
                lambda: QApplication.clipboard().setText(f"[{data.get('db_name')}].[{data.get('schema')}].[{data.get('proc_name')}]")
            )
            menu.addAction(copy_name_action)

            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

        # Context menu for functions
        elif node_type == "function":
            # View code
            view_code_action = QAction("\U0001f4c4 View Code", self)
            view_code_action.triggered.connect(lambda: self._load_routine_code(data))
            menu.addAction(view_code_action)

            menu.addSeparator()

            # Generate SELECT template
            select_action = QAction("\u26a1 Generate SELECT Template", self)
            select_action.triggered.connect(lambda: self._generate_select_function(data))
            menu.addAction(select_action)

            # Copy name
            copy_name_action = QAction("\U0001f4cb Copy Name", self)
            copy_name_action.triggered.connect(
                lambda: QApplication.clipboard().setText(f"[{data.get('db_name')}].[{data.get('schema')}].[{data.get('func_name')}]")
            )
            menu.addAction(copy_name_action)

            menu.exec(self.schema_tree.viewport().mapToGlobal(position))

    def _show_distribution_analysis(self, data: dict):
        """Show distribution analysis for a table or view"""
        table_name = data["name"]
        db_id = data.get("db_id")
        db_name = data.get("db_name")  # Database name for SQL Server

        # Get connection
        connection = self.connections.get(db_id)
        db_conn = self._get_connection_by_id(db_id)

        if not connection or not db_conn:
            DialogHelper.error(tr("db_no_connection_available"), parent=self)
            return

        try:
            # Execute query to get data (limit rows for analysis)
            cursor = connection.cursor()
            from ....constants import build_preview_sql
            schema_prefix = db_name if db_conn.db_type in ("sqlserver", "access") else None
            query = build_preview_sql(table_name, db_conn.db_type, schema=schema_prefix, limit=ANALYSIS_ROW_LIMIT)

            cursor.execute(query)

            # Get columns
            columns = [column[0] for column in cursor.description]

            # Fetch data
            rows = cursor.fetchall()
            data_list = [[cell for cell in row] for row in rows]

            if not data_list:
                DialogHelper.info(tr("db_no_data_for_analysis"), parent=self)
                return

            # Show distribution analysis dialog (non-modal to allow multiple windows)
            db_name = data.get("db_name", db_conn.name if db_conn else "Unknown")
            dialog = DistributionAnalysisDialog(data_list, columns, db_name, table_name, parent=self)
            dialog.show()

        except Exception as e:
            logger.error(f"Error analyzing distribution: {e}")
            DialogHelper.error(tr("db_analysis_failed"), parent=self, details=str(e))

    def _on_tree_double_click(self, item, column: int):
        """Handle double-click on tree item"""
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if not data:
            return

        node_type = data.get("type", "")

        if node_type == "server" and not data.get("connected", False):
            # Try to connect (first attempt or retry, same code)
            db_conn = data.get("config")
            if db_conn:
                self._connect_and_load_schema(item, db_conn)

        elif node_type in ["table", "view"]:
            # Generate SELECT TOP 100 query by default on double-click
            self._generate_select_query(data, limit=QUERY_PREVIEW_LIMIT)

        elif node_type in ["procedure", "function"]:
            # Load procedure/function code into editor
            self._load_routine_code(data)
