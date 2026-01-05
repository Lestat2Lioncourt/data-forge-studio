"""
Database Dialects - Database-specific SQL operations

This module provides a factory pattern for handling database-specific SQL syntax,
similar to the SchemaLoader pattern for schema loading.

Usage:
    from dataforge_studio.database.dialects import DialectFactory

    # Create a dialect for a connection
    dialect = DialectFactory.create("postgresql", connection, db_name)

    # Generate queries
    query = dialect.generate_select_query("users", schema_name="public", limit=100)

    # Get metadata
    columns = dialect.get_table_columns("users", "public")

    # Get view/routine definitions
    view_code = dialect.get_alter_view_statement("my_view", "public")
    proc_code = dialect.get_routine_definition("my_proc", "public")
"""

from .base import DatabaseDialect, ColumnInfo, ParameterInfo
from .factory import DialectFactory

from .sqlite_dialect import SQLiteDialect
from .sqlserver_dialect import SQLServerDialect
from .postgresql_dialect import PostgreSQLDialect
from .access_dialect import AccessDialect
from .mysql_dialect import MySQLDialect

__all__ = [
    # Base classes
    "DatabaseDialect",
    "ColumnInfo",
    "ParameterInfo",

    # Factory
    "DialectFactory",

    # Implementations
    "SQLiteDialect",
    "SQLServerDialect",
    "PostgreSQLDialect",
    "AccessDialect",
    "MySQLDialect",
]
