"""
Dialect Factory - Create appropriate dialect based on database type
"""

from typing import Any, Optional, Type, Dict
from .base import DatabaseDialect

import logging
logger = logging.getLogger(__name__)


class DialectFactory:
    """
    Factory for creating database dialects.

    Usage:
        dialect = DialectFactory.create("sqlite", connection)
        query = dialect.generate_select_query("users", limit=100)
    """

    # Registry of supported database types
    _dialects: Dict[str, Type[DatabaseDialect]] = {}

    @classmethod
    def create(
        cls,
        db_type: str,
        connection: Any,
        db_name: Optional[str] = None
    ) -> Optional[DatabaseDialect]:
        """
        Create a dialect for the specified database type.

        Args:
            db_type: Database type (sqlite, sqlserver, postgresql, access)
            connection: Database connection object
            db_name: Optional target database name

        Returns:
            DatabaseDialect instance or None if type not supported
        """
        db_type_lower = db_type.lower()

        dialect_class = cls._dialects.get(db_type_lower)
        if dialect_class is None:
            logger.warning(f"No dialect for database type: {db_type}")
            return None

        return dialect_class(connection, db_name)

    @classmethod
    def is_supported(cls, db_type: str) -> bool:
        """Check if a database type is supported."""
        return db_type.lower() in cls._dialects

    @classmethod
    def supported_types(cls) -> list:
        """Get list of supported database types."""
        return list(cls._dialects.keys())

    @classmethod
    def register(cls, db_type: str, dialect_class: Type[DatabaseDialect]):
        """
        Register a new dialect type.

        Args:
            db_type: Database type identifier
            dialect_class: DatabaseDialect subclass
        """
        cls._dialects[db_type.lower()] = dialect_class
        logger.debug(f"Registered dialect for: {db_type}")


def _register_default_dialects():
    """Register built-in dialects. Called on module import."""
    from .sqlite_dialect import SQLiteDialect
    from .sqlserver_dialect import SQLServerDialect
    from .postgresql_dialect import PostgreSQLDialect
    from .access_dialect import AccessDialect
    from .mysql_dialect import MySQLDialect

    DialectFactory.register("sqlite", SQLiteDialect)
    DialectFactory.register("sqlserver", SQLServerDialect)
    DialectFactory.register("postgresql", PostgreSQLDialect)
    DialectFactory.register("postgres", PostgreSQLDialect)  # Alias
    DialectFactory.register("access", AccessDialect)
    DialectFactory.register("mysql", MySQLDialect)
    DialectFactory.register("mariadb", MySQLDialect)  # Alias


# Register on module import
_register_default_dialects()
