"""
Access Schema Loader - Load schema from Microsoft Access databases
"""

from typing import List, Any

from .base import SchemaLoader, SchemaNode, SchemaNodeType

import logging
logger = logging.getLogger(__name__)


class AccessSchemaLoader(SchemaLoader):
    """Schema loader for Microsoft Access databases (.mdb, .accdb)."""

    def __init__(self, connection: Any, db_id: str, db_name: str):
        """
        Initialize Access schema loader.

        Args:
            connection: pyodbc Connection object
            db_id: Database connection ID
            db_name: Database name for display
        """
        super().__init__(connection, db_id, db_name)

    def load_schema(self) -> SchemaNode:
        """Load complete Access schema."""
        tables = self.load_tables()
        views = self.load_views()  # Access queries

        # Create root node
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

        # Queries folder (Access calls them queries, not views)
        queries_folder = self._create_folder_node(
            SchemaNodeType.VIEWS_FOLDER, "Queries", len(views)
        )
        queries_folder.children = views
        root.add_child(queries_folder)

        return root

    def load_tables(self) -> List[SchemaNode]:
        """Load all tables with columns."""
        cursor = self.connection.cursor()
        tables = []

        try:
            # Use ODBC catalog function to get tables
            table_names = []
            for row in cursor.tables(tableType='TABLE'):
                table_name = row.table_name
                # Skip Access system tables
                if not table_name.startswith('MSys'):
                    table_names.append(table_name)

            for table_name in sorted(table_names):
                columns = self.load_columns(table_name)
                table_node = self._create_table_node(
                    table_name, column_count=len(columns)
                )
                table_node.children = columns
                tables.append(table_node)

        except Exception as e:
            logger.error(f"Error loading Access tables: {e}")

        return tables

    def load_views(self) -> List[SchemaNode]:
        """Load all Access queries (views)."""
        cursor = self.connection.cursor()
        views = []

        try:
            # Use ODBC catalog function to get views/queries
            view_names = []
            for row in cursor.tables(tableType='VIEW'):
                view_name = row.table_name
                if not view_name.startswith('MSys'):
                    view_names.append(view_name)

            for view_name in sorted(view_names):
                view_node = self._create_view_node(view_name)
                views.append(view_node)

        except Exception as e:
            logger.error(f"Error loading Access queries: {e}")

        return views

    def load_columns(self, table_name: str) -> List[SchemaNode]:
        """Load columns for a table using ODBC catalog."""
        cursor = self.connection.cursor()
        columns = []

        try:
            for col_row in cursor.columns(table=table_name):
                col_name = col_row.column_name
                col_type = col_row.type_name
                col_size = col_row.column_size

                # Format type with size for string types
                if col_size and col_type.upper() in (
                    'VARCHAR', 'CHAR', 'TEXT', 'NVARCHAR', 'NCHAR', 'MEMO'
                ):
                    type_display = f"{col_type}({col_size})"
                else:
                    type_display = col_type

                column_node = self._create_column_node(col_name, type_display, table_name)
                columns.append(column_node)

        except Exception as e:
            logger.error(f"Error loading columns for {table_name}: {e}")

        return columns
