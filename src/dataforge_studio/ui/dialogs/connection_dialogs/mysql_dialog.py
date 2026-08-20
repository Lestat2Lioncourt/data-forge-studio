"""
MySQL Connection Dialog - Simple and Advanced modes
"""

from typing import Optional

from PySide6.QtWidgets import QWidget

from .multimode_connection_dialog import MultiModeConnectionDialog
from ....database.config_db import DatabaseConnection
from ....constants import CONNECTION_TIMEOUT_S

import logging
logger = logging.getLogger(__name__)


class MySQLConnectionDialog(MultiModeConnectionDialog):
    """
    MySQL connection dialog with Simple and Advanced modes.

    Simple Mode:
    - Host
    - Port (default: 3306)
    - Database (optional)
    - Username/Password

    Advanced Mode:
    - Direct connection string
    - Username/Password separate
    """

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _get_default_port(self) -> str:
        return "3306"

    def _get_connection_prefix(self) -> str:
        return "mysql+pymysql://"

    def _get_simple_mode_placeholder(self) -> str:
        return "Leave empty to connect all authorized databases"

    def _get_advanced_mode_placeholder(self) -> str:
        return (
            "Example:\n"
            "mysql+pymysql://localhost:3306/mydb\n\n"
            "Or ODBC:\n"
            "Driver={MySQL ODBC 8.0 Driver};Server=localhost;Port=3306;Database=mydb;"
        )

    def _get_db_type(self) -> str:
        return "mysql"

    def _test_connection(self, connection_string: str) -> tuple[bool, str]:
        """Test MySQL connection."""
        try:
            import pymysql

            # Parse connection string (SQLAlchemy format) with the shared parser:
            # splitting on the first '@' here used to shift the host whenever a
            # password contained one.
            if connection_string.startswith("mysql+pymysql://"):
                from ....utils.connection_helpers import split_db_url

                parts = split_db_url(
                    connection_string.replace("mysql+pymysql://", ""),
                    default_port="3306",
                )

                # Connect
                conn = pymysql.connect(
                    host=parts["host"],
                    port=int(parts["port"]),
                    user=parts["user"],
                    password=parts["password"],
                    database=parts["database"] or None,
                    connect_timeout=CONNECTION_TIMEOUT_S
                )

                cursor = conn.cursor()

                # Get MySQL version
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]

                # Get current database
                cursor.execute("SELECT DATABASE()")
                current_db = cursor.fetchone()[0] or "(none)"

                conn.close()

                return (True, f"MySQL version: {version}\nCurrent database: {current_db}")

            else:
                return (False, "Unsupported connection string format. Use mysql+pymysql:// format.")

        except ImportError:
            from ....config.i18n import t
            return (False, t("dep_pymysql_missing"))
        except Exception as e:
            return (False, str(e))
