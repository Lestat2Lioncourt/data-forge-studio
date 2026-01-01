"""
SQL Server Dialect - SQL Server-specific SQL operations
"""

from typing import List, Optional
from .base import DatabaseDialect, ColumnInfo, ParameterInfo

import logging
logger = logging.getLogger(__name__)


class SQLServerDialect(DatabaseDialect):
    """Dialect for SQL Server databases."""

    @property
    def quote_char(self) -> str:
        return "["

    @property
    def quote_char_end(self) -> str:
        return "]"

    @property
    def default_schema(self) -> str:
        return "dbo"

    def generate_select_query(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> str:
        """Generate SQL Server SELECT query with TOP clause."""
        # Build column list
        if columns:
            cols = ", ".join(self.quote_identifier(c) for c in columns)
        else:
            cols = "*"

        # Build table reference with optional database and schema
        full_table = self.quote_full_table_name(
            table_name,
            schema_name or self.default_schema,
            include_db=True
        )

        # Build query with TOP (SQL Server style)
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
        """Get columns using sys.columns."""
        schema = schema_name or self.default_schema

        # Try tables first
        rows = self._execute_all(f"""
            SELECT c.name, t.name as type_name, c.is_nullable
            FROM [{self.db_name}].sys.columns c
            INNER JOIN [{self.db_name}].sys.tables tbl ON c.object_id = tbl.object_id
            INNER JOIN [{self.db_name}].sys.schemas s ON tbl.schema_id = s.schema_id
            INNER JOIN [{self.db_name}].sys.types t ON c.user_type_id = t.user_type_id
            WHERE tbl.name = ? AND s.name = ?
            ORDER BY c.column_id
        """, (table_name, schema))

        # If no columns found, try views
        if not rows:
            rows = self._execute_all(f"""
                SELECT c.name, t.name as type_name, c.is_nullable
                FROM [{self.db_name}].sys.columns c
                INNER JOIN [{self.db_name}].sys.views v ON c.object_id = v.object_id
                INNER JOIN [{self.db_name}].sys.schemas s ON v.schema_id = s.schema_id
                INNER JOIN [{self.db_name}].sys.types t ON c.user_type_id = t.user_type_id
                WHERE v.name = ? AND s.name = ?
                ORDER BY c.column_id
            """, (table_name, schema))

        return [
            ColumnInfo(
                name=row[0],
                type_name=row[1].upper(),
                is_nullable=bool(row[2])
            )
            for row in rows
        ]

    def get_view_definition(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """Get view definition from sys.sql_modules."""
        schema = schema_name or self.default_schema

        result = self._execute_scalar(f"""
            SELECT m.definition
            FROM [{self.db_name}].sys.sql_modules m
            INNER JOIN [{self.db_name}].sys.views v ON m.object_id = v.object_id
            INNER JOIN [{self.db_name}].sys.schemas s ON v.schema_id = s.schema_id
            WHERE v.name = ? AND s.name = ?
        """, (view_name, schema))

        return result

    def get_routine_definition(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> Optional[str]:
        """Get procedure/function definition from sys.sql_modules."""
        schema = schema_name or self.default_schema

        result = self._execute_scalar(f"""
            SELECT m.definition
            FROM [{self.db_name}].sys.sql_modules m
            INNER JOIN [{self.db_name}].sys.objects o ON m.object_id = o.object_id
            INNER JOIN [{self.db_name}].sys.schemas s ON o.schema_id = s.schema_id
            WHERE o.name = ? AND s.name = ?
        """, (routine_name, schema))

        return result

    def get_routine_parameters(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> List[ParameterInfo]:
        """Get procedure/function parameters from sys.parameters."""
        schema = schema_name or self.default_schema

        if routine_type == "procedure":
            rows = self._execute_all(f"""
                SELECT p.name, t.name as type_name, p.is_output
                FROM [{self.db_name}].sys.parameters p
                INNER JOIN [{self.db_name}].sys.types t ON p.user_type_id = t.user_type_id
                INNER JOIN [{self.db_name}].sys.procedures pr ON p.object_id = pr.object_id
                INNER JOIN [{self.db_name}].sys.schemas s ON pr.schema_id = s.schema_id
                WHERE pr.name = ? AND s.name = ?
                ORDER BY p.parameter_id
            """, (routine_name, schema))
        else:
            rows = self._execute_all(f"""
                SELECT p.name, t.name as type_name, p.is_output
                FROM [{self.db_name}].sys.parameters p
                INNER JOIN [{self.db_name}].sys.types t ON p.user_type_id = t.user_type_id
                INNER JOIN [{self.db_name}].sys.objects o ON p.object_id = o.object_id
                INNER JOIN [{self.db_name}].sys.schemas s ON o.schema_id = s.schema_id
                WHERE o.name = ? AND s.name = ? AND p.parameter_id > 0
                ORDER BY p.parameter_id
            """, (routine_name, schema))

        return [
            ParameterInfo(
                name=row[0],
                type_name=row[1],
                is_output=bool(row[2])
            )
            for row in rows
        ]

    def generate_exec_template(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> str:
        """Generate EXEC template for SQL Server."""
        schema = schema_name or self.default_schema
        full_name = f"[{self.db_name}].[{schema}].[{routine_name}]"

        params = self.get_routine_parameters(routine_name, schema, routine_type)

        if params:
            param_list = []
            for p in params:
                output_str = " OUTPUT" if p.is_output else ""
                param_list.append(f"    {p.name} = NULL{output_str}  -- {p.type_name}")
            return f"EXEC {full_name}\n" + ",\n".join(param_list)

        return f"EXEC {full_name}"

    def generate_select_function_template(
        self,
        func_name: str,
        schema_name: Optional[str] = None,
        func_type: str = ""
    ) -> str:
        """Generate SELECT template for SQL Server function."""
        schema = schema_name or self.default_schema
        full_name = f"[{self.db_name}].[{schema}].[{func_name}]"

        params = self.get_routine_parameters(func_name, schema, "function")

        if params:
            param_placeholders = ", ".join(
                f"NULL /* {p.name}: {p.type_name} */" for p in params
            )
        else:
            param_placeholders = ""

        # Table-valued function vs scalar function
        if "TABLE" in func_type.upper():
            return f"SELECT * FROM {full_name}({param_placeholders})"

        return f"SELECT {full_name}({param_placeholders})"

    def supports_stored_procedures(self) -> bool:
        return True

    def supports_functions(self) -> bool:
        return True
