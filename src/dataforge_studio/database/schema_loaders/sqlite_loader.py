"""
SQLite Schema Loader - Load schema from SQLite databases
"""

import sqlite3
from typing import List

from .base import SchemaLoader, SchemaNode, SchemaNodeType

import logging
logger = logging.getLogger(__name__)


class SQLiteSchemaLoader(SchemaLoader):
    """Schema loader for SQLite databases."""

    def __init__(self, connection: sqlite3.Connection, db_id: str, db_name: str):
        super().__init__(connection, db_id, db_name)

    def load_schema(self) -> SchemaNode:
        """Load complete SQLite schema."""
        tables = self.load_tables()
        views = self.load_views()

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

        return root

    def load_tables(self) -> List[SchemaNode]:
        """Load all tables with columns."""
        cursor = self.connection.cursor()
        tables = []

        try:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            table_rows = cursor.fetchall()

            for (table_name,) in table_rows:
                columns = self.load_columns(table_name)
                table_node = self._create_table_node(
                    table_name, column_count=len(columns)
                )
                table_node.children = columns
                tables.append(table_node)

        except Exception as e:
            logger.error(f"Error loading SQLite tables: {e}")

        return tables

    def load_views(self) -> List[SchemaNode]:
        """Load all views."""
        cursor = self.connection.cursor()
        views = []

        try:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
            )
            view_rows = cursor.fetchall()

            for (view_name,) in view_rows:
                # Get column count for view
                try:
                    # Escape identifier for PRAGMA (no parameterization possible)
                    safe_name = view_name.replace("]", "]]")
                    cursor.execute(f"PRAGMA table_info([{safe_name}])")
                    columns = cursor.fetchall()
                    column_count = len(columns)
                except Exception:
                    column_count = 0

                view_node = self._create_view_node(view_name, column_count=column_count)
                views.append(view_node)

        except Exception as e:
            logger.error(f"Error loading SQLite views: {e}")

        return views

    def load_columns(self, table_name: str) -> List[SchemaNode]:
        """Load columns for a table."""
        cursor = self.connection.cursor()
        columns = []

        try:
            # Escape identifier for PRAGMA (no parameterization possible)
            safe_name = table_name.replace("]", "]]")
            cursor.execute(f"PRAGMA table_info([{safe_name}])")
            column_rows = cursor.fetchall()

            for col in column_rows:
                col_name = col[1]
                col_type = col[2] or "TEXT"
                column_node = self._create_column_node(col_name, col_type, table_name)
                columns.append(column_node)

        except Exception as e:
            logger.error(f"Error loading columns for {table_name}: {e}")

        return columns
