"""
Connection helpers — shared utilities for database connection parsing.
"""

import logging
from typing import Optional

from ..constants import CONNECTION_TIMEOUT_S

logger = logging.getLogger(__name__)


def parse_postgresql_url(conn_str: str, db_id: Optional[str] = None) -> Optional[dict]:
    """
    Parse a postgresql:// URL and return psycopg2.connect() kwargs.

    If db_id is provided, credentials are fetched from keyring and take
    priority over those embedded in the URL.

    Returns None if conn_str doesn't start with 'postgresql://'.
    """
    if not conn_str.startswith("postgresql://"):
        return None

    from .credential_manager import CredentialManager

    url_part = conn_str.replace("postgresql://", "")

    username, password = None, None
    if db_id:
        username, password = CredentialManager.get_credentials(db_id)

    # Parse URL: [user:pass@]host[:port][/database]
    if "@" in url_part:
        auth_part, server_part = url_part.split("@", 1)
        if not username:
            username = auth_part.split(":")[0] if ":" in auth_part else auth_part
        if not password and ":" in auth_part:
            password = auth_part.split(":", 1)[1]
    else:
        server_part = url_part

    # Parse host:port/database
    if "/" in server_part:
        host_port, database = server_part.split("/", 1)
        database = database.split("?")[0]  # Remove query params
    else:
        host_port = server_part
        database = "postgres"

    host, port = host_port.split(":") if ":" in host_port else (host_port, "5432")

    return {
        "host": host,
        "port": int(port),
        "user": username or "",
        "password": password or "",
        "database": database,
        "connect_timeout": CONNECTION_TIMEOUT_S,
    }
