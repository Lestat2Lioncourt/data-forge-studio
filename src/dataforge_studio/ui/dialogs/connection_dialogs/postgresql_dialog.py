"""
PostgreSQL Connection Dialog - Simple and Advanced modes
"""

from typing import Optional

from PySide6.QtWidgets import QWidget

from .multimode_connection_dialog import MultiModeConnectionDialog
from ....database.config_db import DatabaseConnection

import logging
logger = logging.getLogger(__name__)


class PostgreSQLConnectionDialog(MultiModeConnectionDialog):
    """
    PostgreSQL connection dialog with Simple and Advanced modes.

    Simple Mode:
    - Host
    - Port (default: 5432)
    - Database (optional)
    - Username/Password

    Advanced Mode:
    - Direct connection string
    - Username/Password separate
    """

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _get_default_port(self) -> str:
        return "5432"

    def _get_connection_prefix(self) -> str:
        return "postgresql://"

    def _get_simple_mode_placeholder(self) -> str:
        return "Leave empty to connect all authorized databases"

    def _get_advanced_mode_placeholder(self) -> str:
        return (
            "Example:\n"
            "postgresql://localhost:5432/mydb\n\n"
            "Or with schema:\n"
            "postgresql://localhost:5432/mydb?options=-c%20search_path=myschema"
        )

    def _get_db_type(self) -> str:
        return "postgresql"

    def _test_connection(self, connection_string: str) -> tuple[bool, str]:
        """Test PostgreSQL connection."""
        try:
            import psycopg2

            # Parse connection string
            if connection_string.startswith("postgresql://"):
                conn_str = connection_string.replace("postgresql://", "")

                # Parse username:password@host:port/database
                if "@" in conn_str:
                    auth_part, server_part = conn_str.split("@", 1)
                    username, password = auth_part.split(":", 1) if ":" in auth_part else (auth_part, "")
                else:
                    username, password = "", ""
                    server_part = conn_str

                # Parse host:port/database
                if "/" in server_part:
                    host_port, database_opts = server_part.split("/", 1)
                    # Remove query params if present
                    database = database_opts.split("?")[0] if "?" in database_opts else database_opts
                else:
                    host_port = server_part
                    database = ""

                host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")

                # Connect
                conn = psycopg2.connect(
                    host=host,
                    port=int(port),
                    user=username,
                    password=password,
                    database=database if database else "postgres",
                    connect_timeout=5
                )

                cursor = conn.cursor()

                # Get PostgreSQL version
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]

                # Get current database
                cursor.execute("SELECT current_database()")
                current_db = cursor.fetchone()[0]

                conn.close()

                return (True, f"PostgreSQL version:\n{version[:100]}...\n\nCurrent database: {current_db}")

            else:
                return (False, "Unsupported connection string format. Use postgresql:// format.")

        except ImportError:
            return (False, "psycopg2 library not installed. Please install it:\npip install psycopg2-binary")
        except Exception as e:
            return (False, str(e))
