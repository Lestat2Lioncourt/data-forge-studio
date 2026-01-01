"""
Base Database Dialect - Abstract base class for database-specific SQL operations

Dialects handle database-specific syntax differences such as:
- Row limiting (LIMIT vs TOP)
- Identifier quoting ([brackets] vs "quotes")
- System catalog queries (sys.* vs information_schema vs PRAGMA)
- Procedure/function syntax (EXEC vs CALL)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Column metadata returned by dialect queries."""
    name: str
    type_name: str
    is_nullable: bool = True
    is_primary_key: bool = False


@dataclass
class ParameterInfo:
    """Procedure/function parameter info."""
    name: str
    type_name: str
    is_output: bool = False


class DatabaseDialect(ABC):
    """
    Abstract base class for database dialects.

    Each dialect knows how to:
    1. Generate SQL syntax specific to its database type
    2. Query system catalogs for metadata
    3. Quote/escape identifiers appropriately

    Usage:
        dialect = DialectFactory.create("postgresql", connection, db_name)
        query = dialect.generate_select_query("users", limit=100)
        columns = dialect.get_table_columns("users", "public")
    """

    def __init__(self, connection: Any, db_name: Optional[str] = None):
        """
        Initialize the dialect.

        Args:
            connection: Database connection object
            db_name: Optional target database name (for multi-db servers like SQL Server)
        """
        self.connection = connection
        self.db_name = db_name

    # ==================== Identifier Quoting ====================

    @property
    @abstractmethod
    def quote_char(self) -> str:
        """Character used to quote identifiers (e.g., '"' or '[')."""
        pass

    @property
    def quote_char_end(self) -> str:
        """Closing quote character (same as quote_char for most databases)."""
        return self.quote_char

    def quote_identifier(self, identifier: str) -> str:
        """Quote a single identifier (table, column, schema name)."""
        return f"{self.quote_char}{identifier}{self.quote_char_end}"

    def quote_full_table_name(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        include_db: bool = False
    ) -> str:
        """
        Quote a full table reference including optional schema/database.

        Args:
            table_name: Table name
            schema_name: Optional schema name
            include_db: Whether to include database name (for SQL Server)

        Returns:
            Fully qualified and quoted table name
        """
        parts = []
        if include_db and self.db_name:
            parts.append(self.quote_identifier(self.db_name))
        if schema_name:
            parts.append(self.quote_identifier(schema_name))
        parts.append(self.quote_identifier(table_name))
        return ".".join(parts)

    # ==================== Default Schema ====================

    @property
    def default_schema(self) -> str:
        """Default schema name for this database type."""
        return ""

    # ==================== SELECT Query Generation ====================

    @abstractmethod
    def generate_select_query(
        self,
        table_name: str,
        schema_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> str:
        """
        Generate a SELECT query.

        Args:
            table_name: Table or view name
            schema_name: Optional schema name
            columns: List of columns to select (None = all)
            limit: Optional row limit

        Returns:
            Complete SELECT statement
        """
        pass

    # ==================== Column Retrieval ====================

    @abstractmethod
    def get_table_columns(
        self,
        table_name: str,
        schema_name: Optional[str] = None
    ) -> List[ColumnInfo]:
        """
        Get column metadata for a table or view.

        Args:
            table_name: Table or view name
            schema_name: Optional schema name

        Returns:
            List of ColumnInfo objects
        """
        pass

    # ==================== View Operations ====================

    def get_view_definition(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the SQL definition of a view.

        Args:
            view_name: View name
            schema_name: Optional schema name

        Returns:
            View SQL definition or None if not found/no permission
        """
        return None

    def get_alter_view_statement(
        self,
        view_name: str,
        schema_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Get an ALTER VIEW or CREATE OR REPLACE VIEW statement for editing.

        Default implementation converts CREATE VIEW to ALTER VIEW.
        Override in subclasses for database-specific behavior.
        """
        definition = self.get_view_definition(view_name, schema_name)
        if definition:
            # Default: replace CREATE VIEW with ALTER VIEW
            return re.sub(
                r'\bCREATE\s+VIEW\b',
                'ALTER VIEW',
                definition,
                count=1,
                flags=re.IGNORECASE
            )
        return None

    # ==================== Routine Operations (Procedures/Functions) ====================

    def get_routine_definition(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> Optional[str]:
        """
        Get the SQL definition of a stored procedure or function.

        Args:
            routine_name: Procedure or function name
            schema_name: Optional schema name
            routine_type: "procedure" or "function"

        Returns:
            Routine SQL definition or None
        """
        return None

    def get_routine_parameters(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> List[ParameterInfo]:
        """
        Get parameters for a stored procedure or function.

        Returns:
            List of ParameterInfo objects
        """
        return []

    def generate_exec_template(
        self,
        routine_name: str,
        schema_name: Optional[str] = None,
        routine_type: str = "procedure"
    ) -> str:
        """
        Generate EXEC/CALL template for a procedure.

        Returns:
            EXEC or CALL statement template with parameter placeholders
        """
        schema = schema_name or self.default_schema
        if schema:
            full_name = f"{schema}.{routine_name}"
        else:
            full_name = routine_name
        return f"-- No template available for {full_name}"

    def generate_select_function_template(
        self,
        func_name: str,
        schema_name: Optional[str] = None,
        func_type: str = ""
    ) -> str:
        """
        Generate SELECT template for a function.

        Args:
            func_name: Function name
            schema_name: Optional schema name
            func_type: Function type (e.g., "TABLE", "SCALAR", "SETOF")

        Returns:
            SELECT statement template
        """
        schema = schema_name or self.default_schema
        if schema:
            full_name = f"{schema}.{func_name}"
        else:
            full_name = func_name
        return f"SELECT {full_name}()"

    # ==================== Capability Checks ====================

    def supports_stored_procedures(self) -> bool:
        """Whether this database supports stored procedures."""
        return False

    def supports_functions(self) -> bool:
        """Whether this database supports user-defined functions."""
        return False

    def supports_views(self) -> bool:
        """Whether this database supports views."""
        return True

    # ==================== Utility Methods ====================

    def _execute_scalar(self, query: str, params: tuple = ()) -> Any:
        """Execute query and return single scalar value."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else None

    def _execute_all(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute query and return all rows."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
