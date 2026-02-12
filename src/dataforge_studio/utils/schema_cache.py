"""
Schema Cache for SQL Auto-completion
Caches database schema (tables, columns) to avoid repeated queries.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Union, Any
import sqlite3
try:
    import pyodbc
except ImportError:
    pyodbc = None

import logging
logger = logging.getLogger(__name__)


class SchemaCache:
    """
    Cache for database schema metadata.

    Stores tables and columns per connection to enable fast auto-completion.
    """

    def __init__(self):
        # Cache structure: {connection_id: {"tables": [...], "columns": {table: [...]}}}
        self._cache: Dict[int, Dict] = {}

    def _get_connection_id(self, connection) -> int:
        """Get unique identifier for a connection."""
        return id(connection)

    def get_tables(self, connection: Union[sqlite3.Connection, pyodbc.Connection],
                   db_type: str) -> List[str]:
        """
        Get list of tables for a connection.

        Args:
            connection: Database connection
            db_type: "sqlite", "sqlserver", "postgresql", "mysql", "oracle", or other

        Returns:
            List of table names
        """
        conn_id = self._get_connection_id(connection)

        # Check cache
        if conn_id in self._cache and "tables" in self._cache[conn_id]:
            return self._cache[conn_id]["tables"]

        # Load from database
        tables = self._load_tables(connection, db_type)

        # Store in cache
        if conn_id not in self._cache:
            self._cache[conn_id] = {}
        self._cache[conn_id]["tables"] = tables

        return tables

    def get_columns(self, connection: Union[sqlite3.Connection, pyodbc.Connection],
                    db_type: str, table_name: str) -> List[str]:
        """
        Get list of columns for a table.

        Args:
            connection: Database connection
            db_type: "sqlite", "sqlserver", "postgresql", "mysql", "oracle", or other
            table_name: Name of the table

        Returns:
            List of column names
        """
        conn_id = self._get_connection_id(connection)

        # Initialize cache structure
        if conn_id not in self._cache:
            self._cache[conn_id] = {}
        if "columns" not in self._cache[conn_id]:
            self._cache[conn_id]["columns"] = {}

        # Check cache
        if table_name in self._cache[conn_id]["columns"]:
            return self._cache[conn_id]["columns"][table_name]

        # Load from database
        columns = self._load_columns(connection, db_type, table_name)

        # Store in cache
        self._cache[conn_id]["columns"][table_name] = columns

        return columns

    def get_all_columns(self, connection: Union[sqlite3.Connection, pyodbc.Connection],
                        db_type: str) -> List[str]:
        """
        Get all columns from all tables (for SELECT context).

        Returns:
            List of unique column names
        """
        tables = self.get_tables(connection, db_type)
        all_columns = set()

        for table in tables:
            columns = self.get_columns(connection, db_type, table)
            all_columns.update(columns)

        return sorted(list(all_columns))

    def invalidate(self, connection: Optional[Union[sqlite3.Connection, pyodbc.Connection]] = None):
        """
        Invalidate cache for a connection or all connections.

        Args:
            connection: Specific connection to invalidate, or None for all
        """
        if connection is None:
            self._cache.clear()
        else:
            conn_id = self._get_connection_id(connection)
            if conn_id in self._cache:
                del self._cache[conn_id]

    def _load_tables(self, connection, db_type: str) -> List[str]:
        """Load tables from database."""
        try:
            cursor = connection.cursor()

            if db_type == "sqlite":
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = [row[0] for row in cursor.fetchall()]

            elif db_type == "sqlserver":
                cursor.execute("""
                    SELECT s.name + '.' + t.name
                    FROM sys.tables t
                    JOIN sys.schemas s ON t.schema_id = s.schema_id
                    ORDER BY s.name, t.name
                """)
                tables = [row[0] for row in cursor.fetchall()]

            elif db_type == "postgresql":
                cursor.execute("""
                    SELECT table_schema || '.' || table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]

            elif db_type == "mysql":
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]

            elif db_type == "oracle":
                cursor.execute("""
                    SELECT owner || '.' || table_name
                    FROM all_tables
                    WHERE owner NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'DIP')
                    ORDER BY owner, table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]

            else:
                # Fallback: try information_schema (works for many databases)
                try:
                    cursor.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                except Exception:
                    tables = []

            return tables

        except Exception as e:
            logger.error(f"Error loading tables: {e}")
            return []

    def _load_columns(self, connection, db_type: str, table_name: str) -> List[str]:
        """Load columns for a table."""
        try:
            cursor = connection.cursor()

            if db_type == "sqlite":
                # Escape identifier for PRAGMA (no parameterization possible)
                safe_name = table_name.replace("]", "]]")
                cursor.execute(f"PRAGMA table_info([{safe_name}])")
                columns = [row[1] for row in cursor.fetchall()]

            elif db_type == "sqlserver":
                # Handle schema.table format
                if '.' in table_name:
                    schema, table = table_name.split('.', 1)
                    cursor.execute("""
                        SELECT c.name
                        FROM sys.columns c
                        JOIN sys.tables t ON c.object_id = t.object_id
                        JOIN sys.schemas s ON t.schema_id = s.schema_id
                        WHERE s.name = ? AND t.name = ?
                        ORDER BY c.column_id
                    """, (schema, table))
                else:
                    cursor.execute("""
                        SELECT c.name
                        FROM sys.columns c
                        WHERE c.object_id = OBJECT_ID(?)
                        ORDER BY c.column_id
                    """, (table_name,))
                columns = [row[0] for row in cursor.fetchall()]

            elif db_type == "postgresql":
                # Handle schema.table format
                if '.' in table_name:
                    schema, table = table_name.split('.', 1)
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                    """, (schema, table))
                else:
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                columns = [row[0] for row in cursor.fetchall()]

            elif db_type == "mysql":
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE() AND table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = [row[0] for row in cursor.fetchall()]

            elif db_type == "oracle":
                # Handle owner.table format
                if '.' in table_name:
                    owner, table = table_name.split('.', 1)
                    cursor.execute("""
                        SELECT column_name
                        FROM all_tab_columns
                        WHERE owner = :1 AND table_name = :2
                        ORDER BY column_id
                    """, (owner.upper(), table.upper()))
                else:
                    cursor.execute("""
                        SELECT column_name
                        FROM all_tab_columns
                        WHERE table_name = :1
                        ORDER BY column_id
                    """, (table_name.upper(),))
                columns = [row[0] for row in cursor.fetchall()]

            else:
                # Fallback: try information_schema
                try:
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = ?
                        ORDER BY ordinal_position
                    """, (table_name,))
                    columns = [row[0] for row in cursor.fetchall()]
                except Exception:
                    columns = []

            return columns

        except Exception as e:
            logger.error(f"Error loading columns for {table_name}: {e}")
            return []
