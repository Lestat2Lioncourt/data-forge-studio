"""
SQLite Connection Dialog
"""

from typing import Optional
import sqlite3

from PySide6.QtWidgets import QWidget

from .file_based_connection_dialog import FileBasedConnectionDialog
from ....database.config_db import DatabaseConnection
from ....utils.connection_error_handler import format_connection_error

import logging
logger = logging.getLogger(__name__)


class SQLiteConnectionDialog(FileBasedConnectionDialog):
    """
    SQLite connection dialog.

    Features:
    - File selector for .db files
    - Create new database option
    - No authentication required
    """

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _get_file_extension(self) -> str:
        """Get SQLite file extension"""
        return ".db"

    def _get_db_type(self) -> str:
        """Get database type identifier"""
        return "sqlite"

    def _create_database_file(self, file_path: str):
        """Create a new SQLite database file"""
        # Create empty SQLite database
        conn = sqlite3.connect(file_path)
        conn.close()

    def _build_file_connection_string(self, file_path: str, password: str = "") -> str:
        """Build SQLite connection string"""
        # SQLite connection string format for SQLAlchemy
        return f"sqlite:///{file_path}"

    def _test_connection(self, connection_string: str) -> tuple[bool, str]:
        """Test SQLite connection"""
        try:
            # Extract file path from connection string
            file_path = connection_string.replace("sqlite:///", "")

            # Try to connect
            from ....constants import CONNECTION_TIMEOUT_S
            conn = sqlite3.connect(file_path, timeout=CONNECTION_TIMEOUT_S)
            cursor = conn.cursor()

            # Get SQLite version
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]

            # Get table count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            conn.close()

            return (True, f"SQLite version: {version}\nTables: {table_count}")

        except sqlite3.Error as e:
            error_msg = format_connection_error(e, db_type="sqlite", include_original=False)
            return (False, error_msg)

    def _extract_file_path(self, connection_string: str) -> str:
        """Extract file path from SQLite connection string"""
        if connection_string.startswith("sqlite:///"):
            return connection_string.replace("sqlite:///", "")
        return ""

    def _get_credentials(self) -> tuple[str, str, bool]:
        """SQLite doesn't use credentials"""
        return ("", "", False)
