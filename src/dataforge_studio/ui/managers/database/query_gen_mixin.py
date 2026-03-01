"""
Query Generation Mixin - SQL query generation and execution.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QTabWidget

from ..query_tab import QueryTab
from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....database.dialects import DialectFactory, DatabaseDialect
from ....constants import QUERY_PREVIEW_LIMIT

if TYPE_CHECKING:
    from ....database.config_db import DatabaseConnection

logger = logging.getLogger(__name__)


class DatabaseQueryGenMixin:
    """Mixin providing SQL query generation and execution."""

    def _get_dialect(self, db_id: str, db_name: Optional[str] = None) -> Optional[DatabaseDialect]:
        """
        Get or create a dialect for a database connection.

        Args:
            db_id: Database connection ID
            db_name: Actual database name (important for SQL Server multi-db)

        Returns:
            DatabaseDialect instance or None if connection not available
        """
        db_conn = self._get_connection_by_id(db_id)
        connection = self.connections.get(db_id)

        if not db_conn or not connection:
            return None

        # For SQL Server, db_name must be the actual database name, not the connection name
        actual_db_name = db_name or db_conn.name

        # Check cache - but update db_name if provided (SQL Server may switch databases)
        if db_id in self._dialects:
            dialect = self._dialects[db_id]
            if db_name:
                dialect.db_name = db_name
            return dialect

        dialect = DialectFactory.create(db_conn.db_type, connection, actual_db_name)
        if dialect:
            self._dialects[db_id] = dialect

        return dialect

    def _load_template_into_tab(
        self,
        db_id: str,
        db_name: Optional[str],
        template: str,
        tab_name: str,
        target_tab_widget: Optional[QTabWidget] = None,
        workspace_id: Optional[str] = None
    ):
        """Load a SQL template into a query tab.

        Args:
            db_id: Database connection ID
            db_name: Database name
            template: SQL template to load
            tab_name: Name for the tab
            target_tab_widget: Optional QTabWidget (default: self.tab_widget)
            workspace_id: Optional workspace ID to auto-link saved queries
        """
        connection = self.connections.get(db_id)

        if target_tab_widget:
            # Create new tab in target widget
            db_conn = self._get_connection_by_id(db_id)
            query_tab = QueryTab(
                parent=self,
                connection=connection,
                db_connection=db_conn,
                tab_name=tab_name,
                database_manager=self,
                target_database=db_name,
                workspace_id=workspace_id
            )
            query_tab.query_saved.connect(self.query_saved.emit)
            self._add_query_tab_to_widget(target_tab_widget, query_tab, tab_name, db_conn)
            query_tab.set_query_text(template)
        else:
            # Use existing method for self.tab_widget
            current_tab = self._get_or_create_query_tab(db_id)
            if current_tab:
                current_tab.set_query_text(template)

    def _generate_select_query(self, data: dict, limit: Optional[int] = None, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Generate and execute a SELECT query in a NEW tab named after the table.

        Args:
            data: Dict with table info (name, db_id, db_name)
            limit: Optional row limit
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
        """
        table_name = data["name"]
        db_id = data.get("db_id")
        db_name = data.get("db_name")  # Database name for SQL Server

        # Get database connection
        db_conn = self._get_connection_by_id(db_id)
        connection = self.connections.get(db_id)

        # Auto-reconnect if no active connection
        if not connection and db_conn:
            connection = self.reconnect_database(db_id)

        if not connection or not db_conn:
            DialogHelper.warning("Database not connected. Please expand the database node first.", parent=self)
            return

        # Generate query with proper identifier quoting
        # For SQL Server, db_name is the actual database catalog (e.g. "MyDB")
        # For PostgreSQL/SQLite, table_name already contains "schema.table" — no extra prefix
        from ....constants import build_preview_sql
        schema_prefix = db_name if db_conn.db_type in ("sqlserver", "access") else None
        query = build_preview_sql(table_name, db_conn.db_type, schema=schema_prefix, limit=limit)

        # Always create a NEW tab named after the table (don't reuse existing)
        # Extract simple table name for tab title (remove schema prefix if present)
        simple_name = table_name.split('.')[-1].strip('[]')
        tab_name = simple_name

        query_tab = QueryTab(
            parent=self,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name,
            database_manager=self,
            target_database=db_name,
            workspace_id=workspace_id
        )

        # Connect query_saved signal
        query_tab.query_saved.connect(self.query_saved.emit)

        # Add to target tab widget (or self.tab_widget if not specified)
        tab_widget = target_tab_widget if target_tab_widget else self.tab_widget
        self._add_query_tab_to_widget(tab_widget, query_tab, tab_name, db_conn)

        # Set query and execute
        query_tab.set_query_text(query)
        query_tab._execute_as_query()

        logger.info(f"Created query tab '{tab_name}' for table {table_name}")

    def _generate_select_columns_query(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Generate a formatted SELECT query with all column names in a new tab.

        Args:
            data: Dict with table info (name, db_id, db_name)
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
        """
        table_name = data["name"]
        db_id = data.get("db_id")
        db_name = data.get("db_name")

        db_conn = self._get_connection_by_id(db_id)
        connection = self.connections.get(db_id)

        if not connection or not db_conn:
            DialogHelper.warning("Database not connected. Please expand the database node first.", parent=self)
            return

        try:
            # Get columns based on database type
            if db_conn.db_type == "sqlite":
                cursor = connection.cursor()
                cursor.execute(f"PRAGMA table_info([{table_name}])")
                columns = [row[1] for row in cursor.fetchall()]
                full_table_name = f"[{table_name}]"
            elif db_conn.db_type == "sqlserver" and db_name:
                # Parse schema.table format
                parts = table_name.split(".")
                if len(parts) == 2:
                    schema, tbl_name = parts
                else:
                    schema, tbl_name = "dbo", table_name

                cursor = connection.cursor()
                safe_db = db_name.replace("]", "]]")
                cursor.execute(f"""
                    SELECT c.name
                    FROM [{safe_db}].sys.columns c
                    INNER JOIN [{safe_db}].sys.tables t ON c.object_id = t.object_id
                    INNER JOIN [{safe_db}].sys.schemas s ON t.schema_id = s.schema_id
                    WHERE t.name = ? AND s.name = ?
                    ORDER BY c.column_id
                """, (tbl_name, schema))
                columns = [row[0] for row in cursor.fetchall()]

                # If no columns found, try as a view
                if not columns:
                    cursor.execute(f"""
                        SELECT c.name
                        FROM [{safe_db}].sys.columns c
                        INNER JOIN [{safe_db}].sys.views v ON c.object_id = v.object_id
                        INNER JOIN [{safe_db}].sys.schemas s ON v.schema_id = s.schema_id
                        WHERE v.name = ? AND s.name = ?
                        ORDER BY c.column_id
                    """, (tbl_name, schema))
                    columns = [row[0] for row in cursor.fetchall()]

                full_table_name = f"[{db_name}].[{schema}].[{tbl_name}]"
            elif db_conn.db_type == "postgresql":
                # PostgreSQL: use information_schema
                parts = table_name.split(".")
                if len(parts) == 2:
                    schema, tbl_name = parts
                else:
                    schema, tbl_name = "public", table_name

                cursor = connection.cursor()
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema, tbl_name))
                columns = [row[0] for row in cursor.fetchall()]
                full_table_name = f'"{schema}"."{tbl_name}"'
            else:
                # Fallback: get columns from a sample query
                cursor = connection.cursor()
                cursor.execute(f"SELECT TOP 1 * FROM [{table_name}]")
                columns = [desc[0] for desc in cursor.description]
                full_table_name = f"[{table_name}]"

            if not columns:
                DialogHelper.warning("No columns found for this table.", parent=self)
                return

            # Format the query
            query = self._format_select_columns_query(columns, full_table_name)

            # Create a new query tab
            simple_name = table_name.split('.')[-1].strip('[]')
            tab_name = f"{simple_name} (columns)"

            query_tab = QueryTab(
                parent=self,
                connection=connection,
                db_connection=db_conn,
                tab_name=tab_name,
                database_manager=self,
                target_database=db_name,
                workspace_id=workspace_id
            )

            query_tab.query_saved.connect(self.query_saved.emit)

            # Add to target tab widget (or self.tab_widget if not specified)
            tab_widget = target_tab_widget if target_tab_widget else self.tab_widget
            self._add_query_tab_to_widget(tab_widget, query_tab, tab_name, db_conn)

            # Set query but don't execute (user may want to modify it first)
            query_tab.set_query_text(query)

            logger.info(f"Created SELECT COLUMNS query for {table_name}")

        except Exception as e:
            logger.error(f"Error generating SELECT COLUMNS query: {e}")
            DialogHelper.error(f"Error generating query: {e}", parent=self)

    def _format_select_columns_query(self, columns: list, table_name: str) -> str:
        """
        Format a SELECT query with columns in sophisticated/ultimate style.

        Style:
        SELECT
              [Column1]
            , [Column2]
            ...
        FROM [Table]
        WHERE 1 = 1
            -- AND [Column1] = ''
        ORDER BY
              [Column1] ASC
        ;
        """
        lines = ["SELECT"]

        # Format columns with leading comma style
        for i, col in enumerate(columns):
            if i == 0:
                lines.append(f"      [{col}]")
            else:
                lines.append(f"    , [{col}]")

        lines.append(f"FROM {table_name}")
        lines.append("WHERE 1 = 1")

        # Add commented WHERE conditions for first 5 columns
        for col in columns[:5]:
            lines.append(f"    -- AND [{col}] = ''")

        if len(columns) > 5:
            lines.append(f"    -- ... ({len(columns) - 5} more columns)")

        lines.append("ORDER BY")
        lines.append(f"      [{columns[0]}] ASC")

        if len(columns) > 1:
            lines.append(f"    --, [{columns[1]}] DESC")

        lines.append(";")

        return "\n".join(lines)

    def _load_view_code(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Load view code into query editor as ALTER VIEW.

        Args:
            data: Dict with view info (name, db_id, db_name)
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
        """
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        view_name = data.get("name")  # schema.viewname

        if not all([db_id, db_name, view_name]):
            return

        # Get dialect for database-specific operations
        dialect = self._get_dialect(db_id, db_name)
        if not dialect:
            DialogHelper.warning("Database not connected", parent=self)
            return

        # Parse schema and view name
        parts = view_name.split(".")
        if len(parts) == 2:
            schema, name = parts
        else:
            schema = dialect.default_schema or "dbo"
            name = view_name

        try:
            # Use dialect to get view definition
            code = dialect.get_alter_view_statement(name, schema)

            if code:
                connection = self.connections.get(db_id)

                # Determine target tab widget
                tab_widget = target_tab_widget if target_tab_widget else self.tab_widget

                # Get or create a query tab
                if target_tab_widget:
                    # Create new tab in target widget
                    db_conn = self._get_connection_by_id(db_id)
                    tab_name = f"{name} (view)"
                    query_tab = QueryTab(
                        parent=self,
                        connection=connection,
                        db_connection=db_conn,
                        tab_name=tab_name,
                        database_manager=self,
                        target_database=db_name,
                        workspace_id=workspace_id
                    )
                    query_tab.query_saved.connect(self.query_saved.emit)
                    self._add_query_tab_to_widget(tab_widget, query_tab, tab_name, db_conn)
                    query_tab.set_query_text(code)
                    logger.info(f"Loaded view code: {schema}.{name}")
                else:
                    # Use existing method for self.tab_widget
                    current_tab = self._get_or_create_query_tab(db_id)
                    if current_tab:
                        current_tab.set_query_text(code)
                        logger.info(f"Loaded view code: {schema}.{name}")
            else:
                DialogHelper.warning(
                    f"Could not retrieve code for view {schema}.{name}\n"
                    "You may not have permission to view the definition.",
                    parent=self
                )

        except Exception as e:
            logger.error(f"Error loading view code: {e}")
            DialogHelper.error(
                "Error loading view code",
                parent=self,
                details=str(e)
            )

    def _load_routine_code(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Load stored procedure or function code into query editor.

        Args:
            data: Dict with routine info
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
        """
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        routine_type = data.get("type")  # "procedure" or "function"

        if routine_type == "procedure":
            routine_name = data.get("proc_name")
        else:
            routine_name = data.get("func_name")

        if not all([db_id, schema, routine_name]):
            return

        # Get dialect for database-specific operations
        dialect = self._get_dialect(db_id, db_name)
        if not dialect:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            # Use dialect to get routine definition
            code = dialect.get_routine_definition(routine_name, schema, routine_type)

            if code:
                connection = self.connections.get(db_id)

                if target_tab_widget:
                    # Create new tab in target widget
                    db_conn = self._get_connection_by_id(db_id)
                    tab_name = f"{routine_name} ({routine_type})"
                    query_tab = QueryTab(
                        parent=self,
                        connection=connection,
                        db_connection=db_conn,
                        tab_name=tab_name,
                        database_manager=self,
                        target_database=db_name,
                        workspace_id=workspace_id
                    )
                    query_tab.query_saved.connect(self.query_saved.emit)
                    self._add_query_tab_to_widget(target_tab_widget, query_tab, tab_name, db_conn)
                    query_tab.set_query_text(code)
                    logger.info(f"Loaded {routine_type} code: {schema}.{routine_name}")
                else:
                    # Use existing method for self.tab_widget
                    current_tab = self._get_or_create_query_tab(db_id)
                    if current_tab:
                        current_tab.set_query_text(code)
                        logger.info(f"Loaded {routine_type} code: {schema}.{routine_name}")
            else:
                DialogHelper.warning(
                    f"Could not retrieve code for {schema}.{routine_name}\n"
                    "You may not have permission to view the definition.",
                    parent=self
                )

        except Exception as e:
            logger.error(f"Error loading routine code: {e}")
            DialogHelper.error(
                f"Error loading {routine_type} code",
                parent=self,
                details=str(e)
            )

    def _generate_exec_template(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Generate EXEC/CALL template for stored procedure.

        Args:
            data: Dict with procedure info
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
            workspace_id: Optional workspace ID to auto-link saved queries
        """
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        proc_name = data.get("proc_name")

        if not all([db_id, schema, proc_name]):
            return

        # Get dialect for database-specific operations
        dialect = self._get_dialect(db_id, db_name)
        if not dialect:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            # Use dialect to generate template
            template = dialect.generate_exec_template(proc_name, schema, "procedure")

            # Load into editor
            self._load_template_into_tab(db_id, db_name, template, f"{proc_name} (exec)", target_tab_widget, workspace_id=workspace_id)

        except Exception as e:
            logger.error(f"Error generating EXEC template: {e}")
            # Fallback to simple template
            template = dialect.generate_exec_template(proc_name, schema, "procedure")
            self._load_template_into_tab(db_id, db_name, template, f"{proc_name} (exec)", target_tab_widget, workspace_id=workspace_id)

    def _generate_select_function(self, data: dict, target_tab_widget: Optional[QTabWidget] = None, workspace_id: Optional[str] = None):
        """Generate SELECT template for function.

        Args:
            data: Dict with function info
            target_tab_widget: Optional QTabWidget to add the QueryTab to (default: self.tab_widget)
            workspace_id: Optional workspace ID to auto-link saved queries
        """
        db_id = data.get("db_id")
        db_name = data.get("db_name")
        schema = data.get("schema")
        func_name = data.get("func_name")
        func_type = data.get("func_type", "")

        if not all([db_id, schema, func_name]):
            return

        # Get dialect for database-specific operations
        dialect = self._get_dialect(db_id, db_name)
        if not dialect:
            DialogHelper.warning("Database not connected", parent=self)
            return

        try:
            # Use dialect to generate template
            template = dialect.generate_select_function_template(func_name, schema, func_type)
            self._load_template_into_tab(db_id, db_name, template, f"{func_name} (select)", target_tab_widget, workspace_id=workspace_id)

        except Exception as e:
            logger.warning(f"Could not generate function template: {e}")
            # Fallback
            template = dialect.generate_select_function_template(func_name, schema, func_type)
            self._load_template_into_tab(db_id, db_name, template, f"{func_name} (select)", target_tab_widget, workspace_id=workspace_id)

    def execute_saved_query(self, saved_query, target_tab_widget=None, workspace_id=None):
        """
        Execute a saved query in a new QueryTab.

        Args:
            saved_query: SavedQuery object to execute
            target_tab_widget: Optional QTabWidget to add the tab to (default: self.tab_widget)
            workspace_id: Optional workspace ID for auto-linking new queries
        """
        db_id = saved_query.target_database_id
        if not db_id:
            DialogHelper.warning(
                "No target database specified for this query.",
                parent=self
            )
            return

        # Get connection info
        connection = self.connections.get(db_id)
        db_conn = self._get_connection_by_id(db_id)

        if not db_conn:
            DialogHelper.warning(
                "Target database connection not found.",
                parent=self
            )
            return

        if not connection:
            # Try to reconnect
            try:
                connection = self.reconnect_database(db_id)
                if not connection:
                    DialogHelper.error(
                        f"Failed to connect to {db_conn.name}.",
                        parent=self
                    )
                    return
            except Exception as e:
                DialogHelper.error(f"Connection error: {e}", parent=self)
                return

        # Get target database name
        target_db = getattr(saved_query, 'target_database_name', None) or None
        tab_name = saved_query.name

        query_tab = QueryTab(
            parent=self,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name,
            database_manager=self,
            target_database=target_db,
            workspace_id=workspace_id,
            saved_query=saved_query
        )

        # Connect query_saved signal
        query_tab.query_saved.connect(self.query_saved.emit)

        # Add to target tab widget (or self.tab_widget if not specified)
        tab_widget = target_tab_widget if target_tab_widget else self.tab_widget
        self._add_query_tab_to_widget(tab_widget, query_tab, tab_name, db_conn)

        # Set query text and execute
        query_tab.set_query_text(saved_query.query_text or "")
        try:
            query_tab._execute_as_query()
        except Exception as e:
            logger.error(f"Error executing saved query '{saved_query.name}': {e}")
            DialogHelper.error(f"Error executing query: {e}", parent=self)

        logger.info(f"Executed saved query: {saved_query.name}")
