"""
PostgreSQL Schema Loader - Load schema from PostgreSQL databases
"""

from typing import Any, List

from .base import SchemaLoader, SchemaNode, SchemaNodeType

try:
    from psycopg2 import Error as DbError
except ImportError:
    DbError = Exception  # type: ignore[misc,assignment]

import logging
logger = logging.getLogger(__name__)


class PostgreSQLSchemaLoader(SchemaLoader):
    """Schema loader for PostgreSQL databases."""

    # System schemas to exclude
    SYSTEM_SCHEMAS = ('pg_catalog', 'information_schema', 'pg_toast')

    def __init__(self, connection: Any, db_id: str, db_name: str):
        super().__init__(connection, db_id, db_name)

    def load_schema(self) -> SchemaNode:
        """Load complete PostgreSQL schema."""
        tables = self.load_tables()
        views = self.load_views()
        procedures = self.load_procedures()

        # Create root node (the database itself)
        root = SchemaNode(
            node_type=SchemaNodeType.DATABASE,
            name=self.db_name,
            display_name=self.db_name,
            metadata={"db_id": self.db_id}
        )

        # Tables folder
        tables_folder = self._create_folder_node(
            SchemaNodeType.TABLES_FOLDER, "Tables", len(tables)
        )
        tables_folder.children = tables
        root.add_child(tables_folder)

        # Views folder
        views_folder = self._create_folder_node(
            SchemaNodeType.VIEWS_FOLDER, "Views", len(views)
        )
        views_folder.children = views
        root.add_child(views_folder)

        # Functions folder (PostgreSQL uses functions, not stored procedures)
        if procedures:
            functions_folder = self._create_folder_node(
                SchemaNodeType.PROCEDURES_FOLDER, "Functions", len(procedures)
            )
            functions_folder.metadata["is_functions"] = True
            functions_folder.children = procedures
            root.add_child(functions_folder)

        return root

    def load_tables(self) -> List[SchemaNode]:
        """Load all tables with columns (optimized: single query for all columns)."""
        cursor = self.connection.cursor()
        tables = []

        try:
            # Get all user tables with their schemas
            cursor.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type = 'BASE TABLE'
                AND table_schema NOT IN %s
                ORDER BY table_schema, table_name
            """, (self.SYSTEM_SCHEMAS,))
            table_list = cursor.fetchall()

            # Load ALL columns in one query (avoids N+1 problem)
            columns_by_table = self._load_all_columns_bulk(cursor)

            for row in table_list:
                schema_name, table_name = row
                table_key = f"{schema_name}.{table_name}"
                columns = columns_by_table.get(table_key, [])

                table_node = self._create_table_node(
                    table_name, schema_name, column_count=len(columns)
                )
                table_node.children = columns
                tables.append(table_node)

        except DbError as e:
            logger.error(f"Error loading PostgreSQL tables: {e}")

        return tables

    def _load_all_columns_bulk(self, cursor) -> dict:
        """Load all columns for all tables in a single query."""
        columns_by_table = {}

        try:
            cursor.execute("""
                SELECT table_schema, table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema NOT IN %s
                ORDER BY table_schema, table_name, ordinal_position
            """, (self.SYSTEM_SCHEMAS,))

            for row in cursor.fetchall():
                schema_name, table_name, col_name, col_type, nullable = row
                table_key = f"{schema_name}.{table_name}"

                # Format type with nullable indicator
                type_display = col_type.upper()
                if nullable == 'NO':
                    type_display += ' NOT NULL'

                column_node = self._create_column_node(col_name, type_display, table_key)

                if table_key not in columns_by_table:
                    columns_by_table[table_key] = []
                columns_by_table[table_key].append(column_node)

        except DbError as e:
            logger.error(f"Error bulk loading columns: {e}")

        return columns_by_table

    def load_views(self) -> List[SchemaNode]:
        """Load all views."""
        cursor = self.connection.cursor()
        views = []

        try:
            cursor.execute("""
                SELECT table_schema, table_name,
                       (SELECT COUNT(*) FROM information_schema.columns c
                        WHERE c.table_schema = v.table_schema
                        AND c.table_name = v.table_name) as column_count
                FROM information_schema.views v
                WHERE table_schema NOT IN %s
                ORDER BY table_schema, table_name
            """, (self.SYSTEM_SCHEMAS,))

            for row in cursor.fetchall():
                schema_name, view_name, column_count = row
                view_node = self._create_view_node(
                    view_name, schema_name, column_count=column_count or 0
                )
                views.append(view_node)

        except DbError as e:
            logger.error(f"Error loading PostgreSQL views: {e}")

        return views

    def load_procedures(self) -> List[SchemaNode]:
        """Load all user-defined functions."""
        cursor = self.connection.cursor()
        procedures = []

        try:
            # Get user-defined functions (excluding system functions)
            cursor.execute("""
                SELECT n.nspname as schema_name,
                       p.proname as function_name,
                       pg_catalog.pg_get_function_result(p.oid) as return_type,
                       CASE
                           WHEN p.prokind = 'f' THEN 'FUNCTION'
                           WHEN p.prokind = 'p' THEN 'PROCEDURE'
                           WHEN p.prokind = 'a' THEN 'AGGREGATE'
                           WHEN p.prokind = 'w' THEN 'WINDOW'
                           ELSE 'FUNCTION'
                       END as routine_type
                FROM pg_catalog.pg_proc p
                JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname NOT IN %s
                AND p.prokind IN ('f', 'p')
                ORDER BY n.nspname, p.proname
            """, (self.SYSTEM_SCHEMAS,))

            for row in cursor.fetchall():
                schema_name, func_name, return_type, routine_type = row
                full_name = f"{schema_name}.{func_name}"

                proc_node = SchemaNode(
                    node_type=SchemaNodeType.PROCEDURE,
                    name=full_name,
                    display_name=f"{full_name}()",
                    metadata={
                        "db_id": self.db_id,
                        "db_name": self.db_name,
                        "schema": schema_name,
                        "func_name": func_name,
                        "return_type": return_type,
                        "func_type": routine_type,
                        "is_function": True
                    }
                )
                procedures.append(proc_node)

        except DbError as e:
            logger.error(f"Error loading PostgreSQL functions: {e}")

        return procedures

    def load_columns(self, table_name: str, schema_name: str = None) -> List[SchemaNode]:
        """Load columns for a table or view."""
        cursor = self.connection.cursor()
        columns = []

        try:
            if schema_name:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (schema_name, table_name))
            else:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND table_schema NOT IN %s
                    ORDER BY ordinal_position
                """, (table_name, self.SYSTEM_SCHEMAS))

            for row in cursor.fetchall():
                col_name, col_type, nullable, default = row
                # Format type with nullable indicator
                type_display = col_type.upper()
                if nullable == 'NO':
                    type_display += ' NOT NULL'

                full_table = f"{schema_name}.{table_name}" if schema_name else table_name
                column_node = self._create_column_node(col_name, type_display, full_table)
                columns.append(column_node)

        except DbError as e:
            logger.error(f"Error loading columns for {table_name}: {e}")

        return columns

    def get_databases(self) -> List[str]:
        """Get list of databases on the PostgreSQL server."""
        cursor = self.connection.cursor()
        databases = []

        try:
            cursor.execute("""
                SELECT datname FROM pg_database
                WHERE datistemplate = false
                AND datname NOT IN ('postgres')
                ORDER BY datname
            """)
            databases = [row[0] for row in cursor.fetchall()]
        except DbError as e:
            logger.error(f"Error listing databases: {e}")

        return databases
