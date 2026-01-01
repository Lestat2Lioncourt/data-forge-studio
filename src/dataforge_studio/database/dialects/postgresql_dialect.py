"""
PostgreSQL Dialect - PostgreSQL-specific SQL operations
"""

from typing import List, Optional
from .base import DatabaseDialect, ColumnInfo, ParameterInfo

import logging
logger = logging.getLogger(__name__)


class PostgreSQLDialect(DatabaseDialect):
    """Dialect for PostgreSQL databases."""

    # System schemas to exclude
    SYSTEM_SCHEMAS = ('pg_catalog', 'information_schema', 'pg_toast')

    @property
    def quote_char(self) -> str:
        return '"'

    @property
    def default_schema(self) -> str:
        return "public"

    def generate_select_query(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> str:
        """Generate PostgreSQL SELECT query with LIMIT clause."""
        # Build column list
        if columns:
            cols = ", ".join(self.quote_identifier(c) for c in columns)
        else:
            cols = "*"

        # Build table reference
        full_table = self.quote_full_table_name(
            table_name,
            schema_name or self.default_schema
        )

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
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, table_name))

        return [
            ColumnInfo(
                name=row[0],
                type_name=row[1].upper(),
                is_nullable=(row[2] == 'YES')
            )
            for row in rows
        ]

    def get_view_definition(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """Get view definition using pg_get_viewdef."""
        schema = schema_name or self.default_schema

        result = self._execute_scalar("""
            SELECT pg_get_viewdef(c.oid, true)
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = %s AND n.nspname = %s AND c.relkind = 'v'
        """, (view_name, schema))

        return result

    def get_alter_view_statement(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """PostgreSQL uses CREATE OR REPLACE VIEW."""
        schema = schema_name or self.default_schema
        definition = self.get_view_definition(view_name, schema)

        if definition:
            full_name = f"{schema}.{view_name}"
            return f"CREATE OR REPLACE VIEW {full_name} AS\n{definition}"
        return None

    def get_routine_definition(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> Optional[str]:
        """Get function/procedure definition using pg_get_functiondef."""
        schema = schema_name or self.default_schema

        result = self._execute_scalar("""
            SELECT pg_get_functiondef(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE p.proname = %s AND n.nspname = %s
        """, (routine_name, schema))

        return result

    def get_routine_parameters(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> List[ParameterInfo]:
        """Get function arguments using pg_get_function_arguments."""
        schema = schema_name or self.default_schema

        args_str = self._execute_scalar("""
            SELECT pg_get_function_arguments(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE p.proname = %s AND n.nspname = %s
        """, (routine_name, schema))

        if not args_str:
            return []

        # Parse "arg1 type1, arg2 type2, ..."
        params = []
        for arg in args_str.split(','):
            arg = arg.strip()
            if arg:
                parts = arg.split()
                if len(parts) >= 2:
                    name = parts[0]
                    type_name = ' '.join(parts[1:])
                    params.append(ParameterInfo(name=name, type_name=type_name))
                elif len(parts) == 1:
                    # Unnamed parameter, just type
                    params.append(ParameterInfo(name=f"$", type_name=parts[0]))

        return params

    def generate_exec_template(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> str:
        """Generate CALL template for PostgreSQL."""
        schema = schema_name or self.default_schema
        full_name = f"{schema}.{routine_name}"

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
        """Generate SELECT template for PostgreSQL function."""
        schema = schema_name or self.default_schema
        full_name = f"{schema}.{func_name}"

        params = self.get_routine_parameters(func_name, schema, "function")

        if params:
            placeholders = ", ".join(
                f"NULL /* {p.name}: {p.type_name} */" for p in params
            )
        else:
            placeholders = ""

        # Set-returning vs scalar
        if "SETOF" in func_type.upper() or "TABLE" in func_type.upper():
            return f"SELECT * FROM {full_name}({placeholders})"

        return f"SELECT {full_name}({placeholders})"

    def supports_stored_procedures(self) -> bool:
        """PostgreSQL supports procedures (since v11)."""
        return True

    def supports_functions(self) -> bool:
        return True
