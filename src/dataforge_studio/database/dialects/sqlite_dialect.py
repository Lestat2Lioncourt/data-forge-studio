"""
SQLite Dialect - SQLite-specific SQL operations
"""

from typing import List, Optional
from .base import DatabaseDialect, ColumnInfo

import logging
logger = logging.getLogger(__name__)


class SQLiteDialect(DatabaseDialect):
    """Dialect for SQLite databases."""

    @property
    def quote_char(self) -> str:
        return '"'

    @property
    def default_schema(self) -> str:
        return ""  # SQLite doesn't use schemas

    def generate_select_query(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> str:
        """Generate SQLite SELECT query with LIMIT clause."""
        # Build column list
        if columns:
            cols = ", ".join(self.quote_identifier(c) for c in columns)
        else:
            cols = "*"

        # SQLite doesn't use schemas, just quote the table name
        full_table = self.quote_identifier(table_name)

        # Build query
        query = f"SELECT {cols} FROM {full_table}"

        if limit:
            query += f" LIMIT {limit}"

        return query

    def get_table_columns(
        self,
        table_name: str,
        schema_name: Optional[str] = None
    ) -> List[ColumnInfo]:
        """Get columns using PRAGMA table_info."""
        rows = self._execute_all(f"PRAGMA table_info([{table_name}])")

        return [
            ColumnInfo(
                name=row[1],  # name is at index 1
                type_name=row[2].upper() if row[2] else "TEXT",
                is_nullable=(row[3] == 0),  # notnull is at index 3
                is_primary_key=(row[5] == 1)  # pk is at index 5
            )
            for row in rows
        ]

    def get_view_definition(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """Get view definition from sqlite_master."""
        result = self._execute_scalar(
            "SELECT sql FROM sqlite_master WHERE type='view' AND name=?",
            (view_name,)
        )
        return result

    def supports_stored_procedures(self) -> bool:
        return False

    def supports_functions(self) -> bool:
        return False  # SQLite has built-in functions but not user-defined ones
