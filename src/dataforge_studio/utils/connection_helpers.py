"""
Connection helpers — shared utilities for database connection parsing.
"""

import logging
from typing import Optional
from urllib.parse import quote, unquote

from ..constants import CONNECTION_TIMEOUT_S

logger = logging.getLogger(__name__)


def quote_credential(value: str) -> str:
    """Percent-encode a username or password for use inside a URL.

    A raw '@' or '/' in a password produces a malformed URL that no parser can
    read back reliably - the host ends up wrong and the connection is attempted
    against a name that does not exist.
    """
    return quote(value or "", safe="")


def split_db_url(url_part: str, default_port: str) -> dict:
    """Split '[user[:password]@]host[:port][/database]' into its parts.

    Single source of truth, because the same hand-rolled parser used to live in
    five places and all five split on the FIRST '@'. A password ending in '@'
    then shifted the host: 'lucie:termine@@192.168.86.30' was read as the host
    '@192.168.86.30', which of course fails to resolve.

    The userinfo ends at the LAST '@' (RFC 3986), and the path only starts after
    it - a password may legitimately contain '/' too. Values are percent-decoded.

    Args:
        url_part: the URL with its scheme already stripped
        default_port: port to assume when the URL carries none
    """
    user = password = ""

    # Split on the LAST '@': everything before it is the userinfo.
    userinfo, separator, remainder = url_part.rpartition("@")
    if not separator:
        remainder = url_part
    elif userinfo:
        if ":" in userinfo:
            user, password = userinfo.split(":", 1)
        else:
            user = userinfo

    # Cut the path only AFTER the credentials
    if "/" in remainder:
        host_port, database = remainder.split("/", 1)
        database = database.split("?")[0]  # drop query params
    else:
        host_port, database = remainder, ""

    if host_port.startswith("["):                    # IPv6 literal
        host, _, rest = host_port.partition("]")
        host = host.lstrip("[")
        port = rest.lstrip(":") or default_port
    elif ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host, port = host_port, default_port

    return {
        "user": unquote(user),
        "password": unquote(password),
        "host": host,
        "port": port or default_port,
        "database": unquote(database),
    }


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

    parts = split_db_url(url_part, default_port="5432")
    if not username:
        username = parts["user"]
    if not password:
        password = parts["password"]
    host, port = parts["host"], parts["port"]
    database = parts["database"] or "postgres"

    return {
        "host": host,
        "port": int(port),
        "user": username or "",
        "password": password or "",
        "database": database,
        "connect_timeout": CONNECTION_TIMEOUT_S,
    }


def parse_mysql_url(conn_str: str, db_id: Optional[str] = None) -> Optional[dict]:
    """
    Parse a 'mysql+pymysql://' URL and return pymysql.connect() kwargs.

    If db_id is provided, credentials are fetched from keyring and take
    priority over those embedded in the URL.

    Returns None if conn_str doesn't start with 'mysql+pymysql://'.
    """
    if not conn_str.startswith("mysql+pymysql://"):
        return None

    from .credential_manager import CredentialManager

    url_part = conn_str.replace("mysql+pymysql://", "")

    username, password = None, None
    if db_id:
        username, password = CredentialManager.get_credentials(db_id)

    parts = split_db_url(url_part, default_port="3306")
    if not username:
        username = parts["user"]
    if not password:
        password = parts["password"]
    host, port = parts["host"], parts["port"]
    database = parts["database"]

    return {
        "host": host,
        "port": int(port),
        "user": username or "",
        "password": password or "",
        "database": database or None,
        "connect_timeout": CONNECTION_TIMEOUT_S,
    }
