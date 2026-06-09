"""
Database Connection Worker - Background thread for database connections.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Signal, QThread

from ....database.config_db import DatabaseConnection
from ....database.schema_loaders import SchemaLoaderFactory
from ....database.connection_builder import build_connection, ConnectionConfigError
from ....utils.network_utils import check_server_reachable
from ....utils.connection_error_handler import format_connection_error, get_server_unreachable_message
from ....constants import PING_TIMEOUT_S
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
        """Create database connection based on type (delegates to build_connection)."""
        try:
            return build_connection(self.db_conn)
        except ConnectionConfigError as e:
            # Configuration problem (missing file, format, driver) — localized
            self.connection_error.emit(tr(e.key, **e.params))
            return None
        except Exception as e:
            # Runtime driver error (timeout, auth, …)
            error_msg = format_connection_error(e, db_type=self.db_conn.db_type)
            self.connection_error.emit(error_msg)
            return None

    def cancel(self):
        """Request cancellation."""
        self._cancelled = True
