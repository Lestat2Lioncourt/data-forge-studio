"""
Execution Mixin - Query execution for QueryTab.
"""
from __future__ import annotations

import logging
import time
import sqlite3
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....utils.sql_splitter import split_sql_statements, SQLStatement
from ....database.sqlserver_connection import connect_sqlserver

if TYPE_CHECKING:
    from ..query_tab import ResultTabState

logger = logging.getLogger(__name__)


class QueryExecutionMixin:
    """Query execution methods for QueryTab."""

    def _get_executable_sql(self) -> str:
        """Return selected text if any, otherwise the full editor content."""
        cursor = self.sql_editor.textCursor()
        selected = cursor.selectedText().strip()
        if selected:
            # QTextEdit uses \u2029 (paragraph separator) instead of \n
            return selected.replace('\u2029', '\n')
        return self.sql_editor.toPlainText().strip()

    def _execute_as_query(self):
        """Execute as independent queries (parallel mode with separate connections).

        Each SELECT statement runs in its own connection, allowing parallel
        background loading. Best for independent queries.
        """
        query = self._get_executable_sql()

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
        query = self._get_executable_sql()

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

                # Process all result sets (a single batch may produce multiple)
                has_more = True
                needs_commit = False
                while has_more:
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
                        if rows_affected >= 0:
                            self._append_message(f"  → {rows_affected} row(s) affected")
                        needs_commit = True

                    # Advance to next result set (if any)
                    try:
                        has_more = cursor.nextset()
                    except Exception:
                        has_more = False

                if needs_commit:
                    self.connection.commit()

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
                    return sqlite3.connect(db_path, check_same_thread=False)
            elif self.db_type == "sqlserver":
                # SQL Server: create new connection (pyodbc or pytds)
                from ....utils.credential_manager import CredentialManager
                conn_str = self.db_connection.connection_string
                if "trusted_connection=yes" not in conn_str.lower():
                    username, password = CredentialManager.get_credentials(self.db_connection.id)
                    if username and password:
                        if "uid=" not in conn_str.lower():
                            if not conn_str.endswith(";"):
                                conn_str += ";"
                            conn_str += f"UID={username};PWD={password};"
                from ....constants import CONNECTION_TIMEOUT_S
                return connect_sqlserver(conn_str, timeout=CONNECTION_TIMEOUT_S)
            elif self.db_type == "postgresql":
                import psycopg2
                from ....utils.connection_helpers import parse_postgresql_url
                pg_kwargs = parse_postgresql_url(self.db_connection.connection_string, self.db_connection.id)
                if pg_kwargs:
                    return psycopg2.connect(**pg_kwargs)
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
