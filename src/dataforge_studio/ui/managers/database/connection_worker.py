"""
Database Connection Worker - Background thread for database connections.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path

try:
    import pyodbc
except ImportError:
    pyodbc = None
import sqlite3

from PySide6.QtCore import Signal, QThread

from ....database.config_db import DatabaseConnection
from ....database.schema_loaders import SchemaLoaderFactory
from ....utils.credential_manager import CredentialManager
from ....utils.connection_helpers import parse_postgresql_url
from ....utils.network_utils import check_server_reachable
from ....utils.connection_error_handler import format_connection_error, get_server_unreachable_message
from ....constants import CONNECTION_TIMEOUT_S, PING_TIMEOUT_S
from ....database.sqlserver_connection import connect_sqlserver
from ...core.i18n_bridge import tr

logger = logging.getLogger(__name__)


class DatabaseConnectionWorker(QThread):
    """
    Worker thread for database connection operations.

    Runs connection and schema loading in background to avoid UI freezing.
    """

    # Signals
    connection_success = Signal(object, object)  # connection, schema
    connection_error = Signal(str)  # error message
    status_update = Signal(str)  # status message for UI

    def __init__(self, db_conn: DatabaseConnection, parent=None):
        super().__init__(parent)
        self.db_conn = db_conn
        self._cancelled = False

    def run(self):
        """Execute connection in background thread."""
        try:
            # Check server reachability for remote databases
            if self.db_conn.db_type not in ("sqlite", "access"):
                self.status_update.emit(tr("db_checking_connection", name=self.db_conn.name))

                reachable, vpn_message = check_server_reachable(
                    self.db_conn.connection_string,
                    db_type=self.db_conn.db_type,
                    timeout=PING_TIMEOUT_S
                )

                if not reachable:
                    error_msg = get_server_unreachable_message(
                        self.db_conn.name,
                        db_type=self.db_conn.db_type
                    )
                    self.connection_error.emit(error_msg)
                    return

            if self._cancelled:
                return

            self.status_update.emit(tr("db_connecting_to", name=self.db_conn.name))

            # Create connection
            connection = self._create_connection()
            if connection is None:
                return

            if self._cancelled:
                return

            self.status_update.emit(tr("db_loading_schema", name=self.db_conn.name))

            # Load schema
            loader = SchemaLoaderFactory.create(
                self.db_conn.db_type, connection, self.db_conn.id, self.db_conn.name
            )

            if loader:
                schema = loader.load_schema()
                self.connection_success.emit(connection, schema)
            else:
                self.connection_error.emit(tr("db_type_not_supported", db_type=self.db_conn.db_type))

        except Exception as e:
            logger.error(f"Connection error: {e}")
            error_msg = format_connection_error(e, db_type=self.db_conn.db_type)
            self.connection_error.emit(error_msg)

    def _create_connection(self):
        """Create database connection based on type."""
        try:
            if self.db_conn.db_type == "sqlite":
                conn_str = self.db_conn.connection_string
                if conn_str.startswith("sqlite:///"):
                    db_path = conn_str.replace("sqlite:///", "")
                elif "Database=" in conn_str:
                    match = re.search(r'Database=([^;]+)', conn_str)
                    db_path = match.group(1) if match else conn_str
                else:
                    db_path = conn_str

                if not Path(db_path).exists():
                    self.connection_error.emit(tr("db_file_not_found", path=db_path))
                    return None

                return sqlite3.connect(db_path, check_same_thread=False)

            elif self.db_conn.db_type == "sqlserver":
                conn_str = self.db_conn.connection_string

                # Check if NOT using Windows Authentication
                if "trusted_connection=yes" not in conn_str.lower():
                    username, password = CredentialManager.get_credentials(self.db_conn.id)
                    if username and password:
                        if "uid=" not in conn_str.lower() and "user id=" not in conn_str.lower():
                            if not conn_str.endswith(";"):
                                conn_str += ";"
                            conn_str += f"UID={username};PWD={password};"

                return connect_sqlserver(conn_str, timeout=CONNECTION_TIMEOUT_S)

            elif self.db_conn.db_type == "access":
                conn_str = self.db_conn.connection_string

                # Extract file path from connection string
                db_path = None
                if "Dbq=" in conn_str:
                    match = re.search(r'Dbq=([^;]+)', conn_str, re.IGNORECASE)
                    db_path = match.group(1) if match else None

                if not db_path or not Path(db_path).exists():
                    self.connection_error.emit(tr("db_access_file_not_found"))
                    return None

                if pyodbc is None:
                    self.connection_error.emit(tr("db_pyodbc_required"))
                    return None
                return pyodbc.connect(conn_str)

            elif self.db_conn.db_type == "postgresql":
                import psycopg2
                pg_kwargs = parse_postgresql_url(self.db_conn.connection_string, self.db_conn.id)
                if pg_kwargs:
                    return psycopg2.connect(**pg_kwargs)
                else:
                    self.connection_error.emit(tr("db_pg_format_unsupported"))
                    return None

            else:
                self.connection_error.emit(tr("db_type_not_supported", db_type=self.db_conn.db_type))
                return None

        except Exception as e:
            error_msg = format_connection_error(e, db_type=self.db_conn.db_type)
            self.connection_error.emit(error_msg)
            return None

    def cancel(self):
        """Request cancellation."""
        self._cancelled = True
