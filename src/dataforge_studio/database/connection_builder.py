"""
Connection builder — single source of truth for opening a database connection.

Every place that needs a live DBAPI connection (the async connection worker, the
synchronous DatabaseManager helper, and reconnect) goes through build_connection()
so the per-db-type logic lives in exactly one spot. This avoids the class of bug
where a new database type (or a fix) is added to one path but not the others.

build_connection() does NO UI: it raises ConnectionConfigError for configuration
problems (missing file, unsupported format, missing driver) carrying an i18n key,
and lets runtime driver errors (timeout, auth, etc.) propagate to the caller, which
decides how to surface them (signal, dialog, log).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

try:
    import pyodbc
except ImportError:
    pyodbc = None

from .sqlserver_connection import connect_sqlserver
from ..constants import CONNECTION_TIMEOUT_S
from ..utils.credential_manager import CredentialManager
from ..utils.connection_helpers import parse_postgresql_url, parse_mysql_url


class ConnectionConfigError(Exception):
    """A connection could not be built for a configuration reason.

    Carries an i18n ``key`` (+ format ``params``) so the caller can present a
    localized message via ``tr(err.key, **err.params)``.
    """

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params


def _sqlite_path(conn_str: str) -> str:
    """Extract the file path from a SQLite connection string."""
    if conn_str.startswith("sqlite:///"):
        return conn_str[len("sqlite:///"):]
    if "Database=" in conn_str:
        match = re.search(r'Database=([^;]+)', conn_str)
        return match.group(1) if match else conn_str
    return conn_str


def build_connection(db_conn):
    """Open and return a live DBAPI connection for ``db_conn``.

    Raises:
        ConnectionConfigError: configuration problem (file missing, unsupported
            format, missing driver) — non-fatal, carries an i18n key.
        Exception: runtime driver errors (timeout, auth failure, …) propagate.
    """
    db_type = (db_conn.db_type or "").lower()

    if db_type == "sqlite":
        db_path = _sqlite_path(db_conn.connection_string)
        if not Path(db_path).exists():
            raise ConnectionConfigError("db_file_not_found", path=db_path)
        return sqlite3.connect(db_path, check_same_thread=False)

    if db_type == "sqlserver":
        conn_str = db_conn.connection_string
        # Inject stored credentials unless using Windows Authentication
        if "trusted_connection=yes" not in conn_str.lower():
            username, password = CredentialManager.get_credentials(db_conn.id)
            if (username and password
                    and "uid=" not in conn_str.lower()
                    and "user id=" not in conn_str.lower()):
                if not conn_str.endswith(";"):
                    conn_str += ";"
                conn_str += f"UID={username};PWD={password};"
        return connect_sqlserver(conn_str, timeout=CONNECTION_TIMEOUT_S)

    if db_type == "access":
        conn_str = db_conn.connection_string
        db_path = None
        match = re.search(r'Dbq=([^;]+)', conn_str, re.IGNORECASE)
        if match:
            db_path = match.group(1)
        if not db_path or not Path(db_path).exists():
            raise ConnectionConfigError("db_access_file_missing", path=db_path or "?")
        # Inject stored password if present and not already in the string
        _, password = CredentialManager.get_credentials(db_conn.id)
        if password and "Pwd=" not in conn_str:
            if not conn_str.endswith(";"):
                conn_str += ";"
            conn_str += f"Pwd={password};"
        if pyodbc is None:
            raise ConnectionConfigError("db_pyodbc_required")
        return pyodbc.connect(conn_str, timeout=CONNECTION_TIMEOUT_S)

    if db_type in ("postgresql", "postgres"):
        import psycopg2
        pg_kwargs = parse_postgresql_url(db_conn.connection_string, db_conn.id)
        if not pg_kwargs:
            raise ConnectionConfigError("db_pg_format_unsupported")
        return psycopg2.connect(**pg_kwargs)

    if db_type in ("mysql", "mariadb"):
        try:
            import pymysql
        except ImportError:
            raise ConnectionConfigError("dep_pymysql_missing")
        my_kwargs = parse_mysql_url(db_conn.connection_string, db_conn.id)
        if not my_kwargs:
            raise ConnectionConfigError("db_mysql_format_unsupported")
        return pymysql.connect(**my_kwargs)

    raise ConnectionConfigError("db_type_not_supported", db_type=db_conn.db_type)
