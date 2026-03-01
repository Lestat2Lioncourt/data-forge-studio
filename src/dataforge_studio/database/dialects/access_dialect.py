"""
Access Dialect - Microsoft Access-specific SQL operations
"""

from typing import List, Optional
from .base import DatabaseDialect, ColumnInfo

import logging
logger = logging.getLogger(__name__)


class AccessDialect(DatabaseDialect):
    """Dialect for Microsoft Access databases."""

    @property
    def quote_char(self) -> str:
        return "["

    @property
    def quote_char_end(self) -> str:
        return "]"

    @property
    def default_schema(self) -> str:
        return ""  # Access doesn't use schemas

    def generate_select_query(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> str:
        """Generate Access SELECT query with TOP clause."""
        # Build column list
        if columns:
            cols = ", ".join(self.quote_identifier(c) for c in columns)
        else:
            cols = "*"

        # Access doesn't use schemas
        full_table = self.quote_identifier(table_name)

        # Build query with TOP (Access style, like SQL Server)
        if limit:
            query = f"SELECT TOP {limit} {cols} FROM {full_table}"
        else:
            query = f"SELECT {cols} FROM {full_table}"

        return query

    def get_table_columns(
        self,
        table_name: str,
        schema_name: Optional[str] = None
    ) -> List[ColumnInfo]:
        """Get columns using ODBC cursor.columns()."""
        try:
            cursor = self.connection.cursor()

            # Use ODBC catalog function
            columns_result = cursor.columns(table=table_name)

            columns = []
            for row in columns_result:
                columns.append(ColumnInfo(
                    name=row.column_name,
                    type_name=row.type_name.upper() if row.type_name else "VARCHAR",
                    is_nullable=(row.nullable == 1)
                ))

            return columns

        except Exception as e:
            logger.warning(f"Could not get columns for {table_name}: {e}")
            # Fallback: query the table and get column names from description
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"SELECT TOP 1 * FROM {self.quote_identifier(table_name)}")
                return [
                    ColumnInfo(name=desc[0], type_name="UNKNOWN")
                    for desc in cursor.description
                ]
            except Exception:
                return []

    def get_view_definition(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """Access views (queries) - limited support via MSysQueries."""
        # Access stores queries in MSysQueries but it's often not accessible
        # Return None as we can't reliably get view definitions
        return None

    def supports_stored_procedures(self) -> bool:
        return False

    def supports_functions(self) -> bool:
        return False

    def supports_views(self) -> bool:
        # Access has "queries" which are like views, but limited support
        return True
