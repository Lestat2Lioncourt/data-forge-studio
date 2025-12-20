"""
SQL Server Schema Loader - Load schema from SQL Server databases

Supports loading multiple databases from a server, including:
- Tables with schema prefixes (e.g., dbo.TableName)
- Views
- Stored Procedures
- Functions (Scalar, Table-Valued, etc.)
"""

from typing import List, Any, Tuple

from .base import SchemaLoader, SchemaNode, SchemaNodeType

import logging
logger = logging.getLogger(__name__)


class SQLServerSchemaLoader(SchemaLoader):
    """Schema loader for SQL Server databases."""

    def __init__(self, connection: Any, db_id: str, db_name: str):
        """
        Initialize SQL Server schema loader.

        Args:
            connection: pyodbc Connection object
            db_id: Database connection ID
            db_name: Connection name for display
        """
        super().__init__(connection, db_id, db_name)
        self._cursor = None

    def _get_cursor(self):
        """Get or create cursor."""
        if self._cursor is None:
            self._cursor = self.connection.cursor()
        return self._cursor

    def get_databases(self) -> List[str]:
        """Get list of user databases on the server."""
        cursor = self._get_cursor()
        try:
            cursor.execute(
                "SELECT name FROM sys.databases WHERE database_id > 4 ORDER BY name"
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception:
            # Fallback: get current database name
            import pyodbc
            return [self.connection.getinfo(pyodbc.SQL_DATABASE_NAME)]

    def load_schema(self) -> SchemaNode:
        """
        Load complete SQL Server schema (all databases).

        Returns a root node containing database nodes, each with
        tables, views, procedures, and functions.
        """
        databases = self.get_databases()

        # Root node represents the server/connection
        root = SchemaNode(
            node_type=SchemaNodeType.DATABASE,
            name=self.db_name,
            display_name=f"{self.db_name} ({len(databases)} db)",
            metadata={"db_id": self.db_id, "is_server": True}
        )

        for db_name in databases:
            db_node = self._load_database_schema(db_name)
            root.add_child(db_node)

        return root

    def _load_database_schema(self, database_name: str) -> SchemaNode:
        """Load schema for a specific database."""
        tables = self.load_tables(database_name)
        views = self.load_views(database_name)
        procedures = self.load_procedures(database_name)
        functions = self.load_functions(database_name)

        # Database node - show total object count (tables + views + procedures + functions)
        total = len(tables) + len(views) + len(procedures) + len(functions)
        display = f"{database_name} ({total})"

        db_node = SchemaNode(
            node_type=SchemaNodeType.DATABASE,
            name=database_name,
            display_name=display,
            metadata={"db_id": self.db_id, "db_name": database_name}
        )

        # Tables folder
        tables_folder = self._create_folder_node(
            SchemaNodeType.TABLES_FOLDER, "Tables", len(tables)
        )
        tables_folder.metadata["db_name"] = database_name
        tables_folder.children = tables
        db_node.add_child(tables_folder)

        # Views folder
        views_folder = self._create_folder_node(
            SchemaNodeType.VIEWS_FOLDER, "Views", len(views)
        )
        views_folder.metadata["db_name"] = database_name
        views_folder.children = views
        db_node.add_child(views_folder)

        # Procedures folder
        procs_folder = self._create_folder_node(
            SchemaNodeType.PROCEDURES_FOLDER, "Procedures", len(procedures)
        )
        procs_folder.metadata["db_name"] = database_name
        procs_folder.children = procedures
        db_node.add_child(procs_folder)

        # Functions folder (custom type, reuse PROCEDURES_FOLDER)
        funcs_folder = SchemaNode(
            node_type=SchemaNodeType.PROCEDURES_FOLDER,
            name="Functions",
            display_name=f"Functions ({len(functions)})",
            metadata={"db_id": self.db_id, "db_name": database_name, "is_functions": True}
        )
        funcs_folder.children = functions
        db_node.add_child(funcs_folder)

        return db_node

    def load_tables(self, database_name: str = None) -> List[SchemaNode]:
        """Load all tables with columns from a database."""
        if database_name is None:
            database_name = self.db_name

        cursor = self._get_cursor()
        tables = []

        try:
            cursor.execute(f"""
                SELECT s.name as schema_name, t.name as table_name
                FROM [{database_name}].sys.tables t
                INNER JOIN [{database_name}].sys.schemas s ON t.schema_id = s.schema_id
                ORDER BY s.name, t.name
            """)
            table_rows = cursor.fetchall()

            for schema_name, table_name in table_rows:
                columns = self.load_columns(table_name, schema_name, database_name)
                table_node = self._create_table_node(
                    table_name, schema_name, column_count=len(columns)
                )
                table_node.metadata["db_name"] = database_name
                table_node.children = columns
                tables.append(table_node)

        except Exception as e:
            logger.error(f"Error loading tables from {database_name}: {e}")

        return tables

    def load_views(self, database_name: str = None) -> List[SchemaNode]:
        """Load all views from a database."""
        if database_name is None:
            database_name = self.db_name

        cursor = self._get_cursor()
        views = []

        try:
            cursor.execute(f"""
                SELECT s.name, v.name
                FROM [{database_name}].sys.views v
                INNER JOIN [{database_name}].sys.schemas s ON v.schema_id = s.schema_id
                ORDER BY s.name, v.name
            """)
            view_rows = cursor.fetchall()

            for schema_name, view_name in view_rows:
                # Get column count
                try:
                    cursor.execute(f"""
                        SELECT COUNT(*)
                        FROM [{database_name}].sys.columns c
                        INNER JOIN [{database_name}].sys.views v ON c.object_id = v.object_id
                        INNER JOIN [{database_name}].sys.schemas s ON v.schema_id = s.schema_id
                        WHERE v.name = '{view_name}' AND s.name = '{schema_name}'
                    """)
                    column_count = cursor.fetchone()[0]
                except Exception:
                    column_count = 0

                view_node = self._create_view_node(
                    view_name, schema_name, column_count=column_count
                )
                view_node.metadata["db_name"] = database_name
                views.append(view_node)

        except Exception as e:
            logger.error(f"Error loading views from {database_name}: {e}")

        return views

    def load_procedures(self, database_name: str = None) -> List[SchemaNode]:
        """Load all stored procedures from a database."""
        if database_name is None:
            database_name = self.db_name

        cursor = self._get_cursor()
        procedures = []

        try:
            cursor.execute(f"""
                SELECT s.name as schema_name, p.name as proc_name
                FROM [{database_name}].sys.procedures p
                INNER JOIN [{database_name}].sys.schemas s ON p.schema_id = s.schema_id
                ORDER BY s.name, p.name
            """)
            proc_rows = cursor.fetchall()

            for schema_name, proc_name in proc_rows:
                proc_node = self._create_procedure_node(proc_name, schema_name)
                proc_node.metadata["db_name"] = database_name
                procedures.append(proc_node)

        except Exception as e:
            logger.warning(f"Could not load procedures from {database_name}: {e}")

        return procedures

    def load_functions(self, database_name: str = None) -> List[SchemaNode]:
        """Load all functions from a database."""
        if database_name is None:
            database_name = self.db_name

        cursor = self._get_cursor()
        functions = []

        try:
            cursor.execute(f"""
                SELECT s.name as schema_name, o.name as func_name, o.type_desc
                FROM [{database_name}].sys.objects o
                INNER JOIN [{database_name}].sys.schemas s ON o.schema_id = s.schema_id
                WHERE o.type IN ('FN', 'IF', 'TF', 'AF')
                ORDER BY s.name, o.name
            """)
            func_rows = cursor.fetchall()

            for schema_name, func_name, type_desc in func_rows:
                type_short = type_desc.replace("_", " ").title() if type_desc else ""
                full_name = f"{schema_name}.{func_name}"

                func_node = SchemaNode(
                    node_type=SchemaNodeType.PROCEDURE,  # Reuse procedure type
                    name=full_name,
                    display_name=f"{full_name} ({type_short})",
                    metadata={
                        "db_id": self.db_id,
                        "db_name": database_name,
                        "schema": schema_name,
                        "func_name": func_name,
                        "func_type": type_desc,
                        "is_function": True
                    }
                )
                functions.append(func_node)

        except Exception as e:
            logger.warning(f"Could not load functions from {database_name}: {e}")

        return functions

    def load_columns(self, table_name: str, schema_name: str = None,
                     database_name: str = None) -> List[SchemaNode]:
        """Load columns for a table with SQL Server type formatting."""
        if database_name is None:
            database_name = self.db_name
        if schema_name is None:
            schema_name = "dbo"

        cursor = self._get_cursor()
        columns = []

        try:
            cursor.execute(f"""
                SELECT c.name, ty.name, c.max_length, c.precision, c.scale
                FROM [{database_name}].sys.columns c
                INNER JOIN [{database_name}].sys.types ty ON c.user_type_id = ty.user_type_id
                INNER JOIN [{database_name}].sys.tables t ON c.object_id = t.object_id
                INNER JOIN [{database_name}].sys.schemas s ON t.schema_id = s.schema_id
                WHERE t.name = '{table_name}' AND s.name = '{schema_name}'
                ORDER BY c.column_id
            """)
            column_rows = cursor.fetchall()

            full_table_name = f"{schema_name}.{table_name}"

            for col_name, col_type, max_length, precision, scale in column_rows:
                type_display = self._format_column_type(
                    col_type, max_length, precision, scale
                )
                column_node = self._create_column_node(
                    col_name, type_display, full_table_name
                )
                columns.append(column_node)

        except Exception as e:
            logger.error(f"Error loading columns for {schema_name}.{table_name}: {e}")

        return columns

    def _format_column_type(self, col_type: str, max_length: int,
                            precision: int, scale: int) -> str:
        """Format SQL Server column type with size/precision."""
        if col_type in ('nvarchar', 'nchar'):
            if max_length == -1:
                return f"{col_type}(MAX)"
            elif max_length > 0:
                return f"{col_type}({max_length // 2})"
        elif col_type in ('varchar', 'char', 'binary', 'varbinary'):
            if max_length == -1:
                return f"{col_type}(MAX)"
            elif max_length > 0:
                return f"{col_type}({max_length})"
        elif col_type in ('decimal', 'numeric'):
            return f"{col_type}({precision},{scale})"
        return col_type
