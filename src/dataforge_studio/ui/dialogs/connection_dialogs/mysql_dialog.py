"""
MySQL Connection Dialog - Simple and Advanced modes
"""

from typing import Optional

from PySide6.QtWidgets import QWidget

from .multimode_connection_dialog import MultiModeConnectionDialog
from ....database.config_db import DatabaseConnection

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

            # Parse connection string (SQLAlchemy format)
            if connection_string.startswith("mysql+pymysql://"):
                conn_str = connection_string.replace("mysql+pymysql://", "")

                # Parse username:password@host:port/database
                if "@" in conn_str:
                    auth_part, server_part = conn_str.split("@", 1)
                    username, password = auth_part.split(":", 1) if ":" in auth_part else (auth_part, "")
                else:
                    username, password = "", ""
                    server_part = conn_str

                # Parse host:port/database
                if "/" in server_part:
                    host_port, database = server_part.split("/", 1)
                else:
                    host_port = server_part
                    database = ""

                host, port = host_port.split(":") if ":" in host_port else (host_port, "3306")

                # Connect
                conn = pymysql.connect(
                    host=host,
                    port=int(port),
                    user=username,
                    password=password,
                    database=database if database else None,
                    connect_timeout=5
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
            return (False, "PyMySQL library not installed. Please install it:\npip install pymysql")
        except Exception as e:
            return (False, str(e))
