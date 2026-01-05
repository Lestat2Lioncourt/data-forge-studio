"""
MySQL Schema Loader - Load schema from MySQL/MariaDB databases
"""

from typing import Any, List

from .base import SchemaLoader, SchemaNode, SchemaNodeType

import logging
logger = logging.getLogger(__name__)


class MySQLSchemaLoader(SchemaLoader):
    """Schema loader for MySQL/MariaDB databases."""

    # System schemas to exclude
    SYSTEM_SCHEMAS = ('information_schema', 'mysql', 'performance_schema', 'sys')

    def __init__(self, connection: Any, db_id: str, db_name: str):
        super().__init__(connection, db_id, db_name)

    def load_schema(self) -> SchemaNode:
        """Load complete MySQL schema."""
        tables = self.load_tables()
        views = self.load_views()
        procedures = self.load_procedures()
        functions = self.load_functions()

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

        # Procedures folder
        if procedures:
            procedures_folder = self._create_folder_node(
                SchemaNodeType.PROCEDURES_FOLDER, "Procedures", len(procedures)
            )
            procedures_folder.children = procedures
            root.add_child(procedures_folder)

        # Functions folder
        if functions:
            functions_folder = self._create_folder_node(
                SchemaNodeType.PROCEDURES_FOLDER, "Functions", len(functions)
            )
            functions_folder.metadata["is_functions"] = True
            functions_folder.children = functions
            root.add_child(functions_folder)

        return root

    def load_tables(self) -> List[SchemaNode]:
        """Load all tables with columns (optimized: single query for all columns)."""
        cursor = self.connection.cursor()
        tables = []

        try:
            # Get all user tables with their schemas
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                AND TABLE_SCHEMA NOT IN (%s, %s, %s, %s)
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """, self.SYSTEM_SCHEMAS)
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

        except Exception as e:
            logger.error(f"Error loading MySQL tables: {e}")

        return tables

    def _load_all_columns_bulk(self, cursor) -> dict:
        """Load all columns for all tables in a single query."""
        columns_by_table = {}

        try:
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA NOT IN (%s, %s, %s, %s)
                ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
            """, self.SYSTEM_SCHEMAS)

            for row in cursor.fetchall():
                schema_name, table_name, col_name, col_type, nullable = row
                table_key = f"{schema_name}.{table_name}"

                # Format type with nullable indicator
                type_display = col_type.upper() if col_type else "UNKNOWN"
                if nullable == 'NO':
                    type_display += ' NOT NULL'

                column_node = self._create_column_node(col_name, type_display, table_key)

                if table_key not in columns_by_table:
                    columns_by_table[table_key] = []
                columns_by_table[table_key].append(column_node)

        except Exception as e:
            logger.error(f"Error bulk loading columns: {e}")

        return columns_by_table

    def load_views(self) -> List[SchemaNode]:
        """Load all views."""
        cursor = self.connection.cursor()
        views = []

        try:
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME,
                       (SELECT COUNT(*) FROM information_schema.COLUMNS c
                        WHERE c.TABLE_SCHEMA = v.TABLE_SCHEMA
                        AND c.TABLE_NAME = v.TABLE_NAME) as column_count
                FROM information_schema.VIEWS v
                WHERE TABLE_SCHEMA NOT IN (%s, %s, %s, %s)
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """, self.SYSTEM_SCHEMAS)

            for row in cursor.fetchall():
                schema_name, view_name, column_count = row
                view_node = self._create_view_node(
                    view_name, schema_name, column_count=column_count or 0
                )
                views.append(view_node)

        except Exception as e:
            logger.error(f"Error loading MySQL views: {e}")

        return views

    def load_procedures(self) -> List[SchemaNode]:
        """Load all stored procedures."""
        cursor = self.connection.cursor()
        procedures = []

        try:
            cursor.execute("""
                SELECT ROUTINE_SCHEMA, ROUTINE_NAME
                FROM information_schema.ROUTINES
                WHERE ROUTINE_TYPE = 'PROCEDURE'
                AND ROUTINE_SCHEMA NOT IN (%s, %s, %s, %s)
                ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
            """, self.SYSTEM_SCHEMAS)

            for row in cursor.fetchall():
                schema_name, proc_name = row
                full_name = f"{schema_name}.{proc_name}"

                proc_node = SchemaNode(
                    node_type=SchemaNodeType.PROCEDURE,
                    name=full_name,
                    display_name=f"{full_name}()",
                    metadata={
                        "db_id": self.db_id,
                        "db_name": self.db_name,
                        "schema": schema_name,
                        "proc_name": proc_name,
                        "routine_type": "PROCEDURE"
                    }
                )
                procedures.append(proc_node)

        except Exception as e:
            logger.error(f"Error loading MySQL procedures: {e}")

        return procedures

    def load_functions(self) -> List[SchemaNode]:
        """Load all user-defined functions."""
        cursor = self.connection.cursor()
        functions = []

        try:
            cursor.execute("""
                SELECT ROUTINE_SCHEMA, ROUTINE_NAME, DTD_IDENTIFIER
                FROM information_schema.ROUTINES
                WHERE ROUTINE_TYPE = 'FUNCTION'
                AND ROUTINE_SCHEMA NOT IN (%s, %s, %s, %s)
                ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME
            """, self.SYSTEM_SCHEMAS)

            for row in cursor.fetchall():
                schema_name, func_name, return_type = row
                full_name = f"{schema_name}.{func_name}"

                func_node = SchemaNode(
                    node_type=SchemaNodeType.PROCEDURE,
                    name=full_name,
                    display_name=f"{full_name}()",
                    metadata={
                        "db_id": self.db_id,
                        "db_name": self.db_name,
                        "schema": schema_name,
                        "func_name": func_name,
                        "return_type": return_type,
                        "func_type": "FUNCTION",
                        "is_function": True
                    }
                )
                functions.append(func_node)

        except Exception as e:
            logger.error(f"Error loading MySQL functions: {e}")

        return functions

    def load_columns(self, table_name: str, schema_name: str = None) -> List[SchemaNode]:
        """Load columns for a table or view."""
        cursor = self.connection.cursor()
        columns = []

        try:
            if schema_name:
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (schema_name, table_name))
            else:
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_NAME = %s
                    AND TABLE_SCHEMA NOT IN (%s, %s, %s, %s)
                    ORDER BY ORDINAL_POSITION
                """, (table_name,) + self.SYSTEM_SCHEMAS)

            for row in cursor.fetchall():
                col_name, col_type, nullable, default = row
                # Format type with nullable indicator
                type_display = col_type.upper() if col_type else "UNKNOWN"
                if nullable == 'NO':
                    type_display += ' NOT NULL'

                full_table = f"{schema_name}.{table_name}" if schema_name else table_name
                column_node = self._create_column_node(col_name, type_display, full_table)
                columns.append(column_node)

        except Exception as e:
            logger.error(f"Error loading columns for {table_name}: {e}")

        return columns

    def get_databases(self) -> List[str]:
        """Get list of databases on the MySQL server."""
        cursor = self.connection.cursor()
        databases = []

        try:
            cursor.execute("""
                SELECT SCHEMA_NAME
                FROM information_schema.SCHEMATA
                WHERE SCHEMA_NAME NOT IN (%s, %s, %s, %s)
                ORDER BY SCHEMA_NAME
            """, self.SYSTEM_SCHEMAS)
            databases = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing databases: {e}")

        return databases
