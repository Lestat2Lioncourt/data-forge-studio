"""
Connection Dialog Factory - Creates appropriate connection dialog based on database type
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from .connection_dialogs.sqlserver_dialog import SQLServerConnectionDialog
from .connection_dialogs.mysql_dialog import MySQLConnectionDialog
from .connection_dialogs.postgresql_dialog import PostgreSQLConnectionDialog
from .connection_dialogs.mongodb_dialog import MongoDBConnectionDialog
from .connection_dialogs.oracle_dialog import OracleConnectionDialog
from .connection_dialogs.sqlite_dialog import SQLiteConnectionDialog
from .connection_dialogs.access_dialog import AccessConnectionDialog

from ...database.config_db import DatabaseConnection


class ConnectionDialogFactory:
    """
    Factory for creating database connection dialogs.

    Supports:
    - SQL Server
    - MySQL
    - PostgreSQL
    - MongoDB
    - Oracle
    - SQLite
    - Microsoft Access
    """

    # Mapping of database type to dialog class
    DIALOG_MAP = {
        "sqlserver": SQLServerConnectionDialog,
        "mysql": MySQLConnectionDialog,
        "postgresql": PostgreSQLConnectionDialog,
        "postgres": PostgreSQLConnectionDialog,  # Alias
        "mongodb": MongoDBConnectionDialog,
        "mongo": MongoDBConnectionDialog,  # Alias
        "oracle": OracleConnectionDialog,
        "sqlite": SQLiteConnectionDialog,
        "access": AccessConnectionDialog,
    }

    # Display names for each database type
    DISPLAY_NAMES = {
        "sqlserver": "SQL Server",
        "mysql": "MySQL",
        "postgresql": "PostgreSQL",
        "mongodb": "MongoDB",
        "oracle": "Oracle",
        "sqlite": "SQLite",
        "access": "Microsoft Access",
    }

    @staticmethod
    def create_dialog(db_type: str, parent: Optional[QWidget] = None,
                     connection: Optional[DatabaseConnection] = None):
        """
        Create appropriate connection dialog for the given database type.

        Args:
            db_type: Database type identifier (e.g., "sqlserver", "mysql")
            parent: Parent widget
            connection: Existing connection to edit (None for new connection)

        Returns:
            Connection dialog instance

        Raises:
            ValueError: If database type is not supported
        """
        db_type_lower = db_type.lower()

        if db_type_lower not in ConnectionDialogFactory.DIALOG_MAP:
            raise ValueError(
                f"Unsupported database type: {db_type}\n\n"
                f"Supported types: {', '.join(ConnectionDialogFactory.DIALOG_MAP.keys())}"
            )

        dialog_class = ConnectionDialogFactory.DIALOG_MAP[db_type_lower]
        return dialog_class(parent=parent, connection=connection)

    @staticmethod
    def get_supported_types() -> list[str]:
        """
        Get list of supported database types.

        Returns:
            List of supported database type identifiers
        """
        # Return unique types (exclude aliases)
        return ["sqlserver", "mysql", "postgresql", "mongodb", "oracle", "sqlite", "access"]

    @staticmethod
    def get_display_name(db_type: str) -> str:
        """
        Get display name for a database type.

        Args:
            db_type: Database type identifier

        Returns:
            Display name
        """
        return ConnectionDialogFactory.DISPLAY_NAMES.get(db_type.lower(), db_type.upper())

    @staticmethod
    def get_supported_types_with_names() -> list[tuple[str, str]]:
        """
        Get list of supported database types with display names.

        Returns:
            List of tuples (db_type, display_name)
        """
        types = ConnectionDialogFactory.get_supported_types()
        return [(db_type, ConnectionDialogFactory.get_display_name(db_type)) for db_type in types]
