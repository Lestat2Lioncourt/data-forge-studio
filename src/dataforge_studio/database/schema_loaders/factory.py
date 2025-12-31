"""
Schema Loader Factory - Create appropriate schema loader based on database type
"""

from typing import Any, Optional

from .base import SchemaLoader
from .sqlite_loader import SQLiteSchemaLoader
from .sqlserver_loader import SQLServerSchemaLoader
from .access_loader import AccessSchemaLoader
from .postgresql_loader import PostgreSQLSchemaLoader

import logging
logger = logging.getLogger(__name__)


class SchemaLoaderFactory:
    """
    Factory for creating database schema loaders.

    Usage:
        loader = SchemaLoaderFactory.create("sqlite", connection, db_id, db_name)
        schema = loader.load_schema()
    """

    # Registry of supported database types
    _loaders = {
        "sqlite": SQLiteSchemaLoader,
        "sqlserver": SQLServerSchemaLoader,
        "access": AccessSchemaLoader,
        "postgresql": PostgreSQLSchemaLoader,
        "postgres": PostgreSQLSchemaLoader,  # Alias
    }

    @classmethod
    def create(cls, db_type: str, connection: Any,
               db_id: str, db_name: str) -> Optional[SchemaLoader]:
        """
        Create a schema loader for the specified database type.

        Args:
            db_type: Database type (sqlite, sqlserver, access, mysql, etc.)
            connection: Database connection object
            db_id: Database connection ID
            db_name: Database name for display

        Returns:
            SchemaLoader instance or None if type not supported
        """
        db_type_lower = db_type.lower()

        loader_class = cls._loaders.get(db_type_lower)
        if loader_class is None:
            logger.warning(f"No schema loader for database type: {db_type}")
            return None

        return loader_class(connection, db_id, db_name)

    @classmethod
    def is_supported(cls, db_type: str) -> bool:
        """Check if a database type is supported."""
        return db_type.lower() in cls._loaders

    @classmethod
    def supported_types(cls) -> list:
        """Get list of supported database types."""
        return list(cls._loaders.keys())

    @classmethod
    def register(cls, db_type: str, loader_class: type):
        """
        Register a new schema loader type.

        Args:
            db_type: Database type identifier
            loader_class: SchemaLoader subclass
        """
        cls._loaders[db_type.lower()] = loader_class
        logger.info(f"Registered schema loader for: {db_type}")
