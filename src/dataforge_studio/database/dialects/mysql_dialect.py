"""
MySQL Dialect - MySQL-specific SQL operations
"""

from typing import List, Optional
from .base import DatabaseDialect, ColumnInfo, ParameterInfo

import logging
logger = logging.getLogger(__name__)


class MySQLDialect(DatabaseDialect):
    """Dialect for MySQL/MariaDB databases."""

    # System schemas to exclude
    SYSTEM_SCHEMAS = ('information_schema', 'mysql', 'performance_schema', 'sys')

    @property
    def quote_char(self) -> str:
        """MySQL uses backticks for identifier quoting."""
        return '`'

    @property
    def default_schema(self) -> str:
        """MySQL uses database name as schema."""
        return self.db_name or ""

    def generate_select_query(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> str:
        """Generate MySQL SELECT query with LIMIT clause."""
        # Build column list
        if columns:
            cols = ", ".join(self.quote_identifier(c) for c in columns)
        else:
            cols = "*"

        # Build table reference
        schema = schema_name or self.default_schema
        if schema:
            full_table = self.quote_full_table_name(table_name, schema)
        else:
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
        """Get columns using information_schema."""
        schema = schema_name or self.default_schema

        rows = self._execute_all("""
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, (schema, table_name))

        return [
            ColumnInfo(
                name=row[0],
                type_name=row[1].upper() if row[1] else "UNKNOWN",
                is_nullable=(row[2] == 'YES')
            )
            for row in rows
        ]

    def get_view_definition(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """Get view definition from information_schema."""
        schema = schema_name or self.default_schema

        result = self._execute_scalar("""
            SELECT VIEW_DEFINITION
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """, (schema, view_name))

        return result

    def get_alter_view_statement(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """MySQL uses CREATE OR REPLACE VIEW."""
        schema = schema_name or self.default_schema
        definition = self.get_view_definition(view_name, schema)

        if definition:
            full_name = f"`{schema}`.`{view_name}`"
            return f"CREATE OR REPLACE VIEW {full_name} AS\n{definition}"
        return None

    def get_routine_definition(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> Optional[str]:
        """Get stored procedure/function definition from information_schema."""
        schema = schema_name or self.default_schema
        r_type = routine_type.upper()

        result = self._execute_scalar("""
            SELECT ROUTINE_DEFINITION
            FROM information_schema.ROUTINES
            WHERE ROUTINE_SCHEMA = %s AND ROUTINE_NAME = %s AND ROUTINE_TYPE = %s
        """, (schema, routine_name, r_type))

        return result

    def get_routine_parameters(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> List[ParameterInfo]:
        """Get routine parameters from information_schema."""
        schema = schema_name or self.default_schema

        rows = self._execute_all("""
            SELECT PARAMETER_NAME, DATA_TYPE, PARAMETER_MODE
            FROM information_schema.PARAMETERS
            WHERE SPECIFIC_SCHEMA = %s AND SPECIFIC_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, (schema, routine_name))

        params = []
        for row in rows:
            name = row[0] or f"param_{len(params) + 1}"
            type_name = row[1] or "UNKNOWN"
            mode = row[2] or "IN"
            params.append(ParameterInfo(
                name=name,
                type_name=type_name,
                mode=mode
            ))

        return params

    def generate_exec_template(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> str:
        """Generate CALL template for MySQL stored procedure."""
        schema = schema_name or self.default_schema

        if schema:
            full_name = f"`{schema}`.`{routine_name}`"
        else:
            full_name = f"`{routine_name}`"

        params = self.get_routine_parameters(routine_name, schema, routine_type)

        if params:
            placeholders = ", ".join(
                f"NULL /* {p.name}: {p.type_name} */" for p in params
            )
            return f"CALL {full_name}({placeholders});"

        return f"CALL {full_name}();"

    def generate_select_function_template(
        self,
        func_name: str,
        schema_name: Optional[str] = None,
        func_type: str = ""
    ) -> str:
        """Generate SELECT template for MySQL function."""
        schema = schema_name or self.default_schema

        if schema:
            full_name = f"`{schema}`.`{func_name}`"
        else:
            full_name = f"`{func_name}`"

        params = self.get_routine_parameters(func_name, schema, "function")

        if params:
            placeholders = ", ".join(
                f"NULL /* {p.name}: {p.type_name} */" for p in params
            )
        else:
            placeholders = ""

        return f"SELECT {full_name}({placeholders})"

    def supports_stored_procedures(self) -> bool:
        """MySQL supports stored procedures."""
        return True

    def supports_functions(self) -> bool:
        """MySQL supports functions."""
        return True
