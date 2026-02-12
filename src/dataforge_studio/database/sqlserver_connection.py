"""
SQL Server Connection Helper - pyodbc with pytds fallback.

Provides a unified connect_sqlserver() entry point that uses pyodbc when
available (with an ODBC driver installed), and falls back to pytds (pure-Python
TDS implementation) otherwise.
"""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend detection (cached)
# ---------------------------------------------------------------------------

_backend_cache: Optional[str] = None


def _detect_backend() -> str:
    """Detect best available SQL Server backend. Result is cached."""
    # 1. Try pyodbc + ODBC driver
    try:
        import pyodbc  # noqa: F811

        drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if drivers:
            return "pyodbc"
        logger.info("pyodbc available but no SQL Server ODBC driver found")
    except Exception:
        logger.info("pyodbc not available")

    # 2. Try pytds
    try:
        import pytds  # noqa: F401

        logger.info("Using pytds as SQL Server backend")
        return "pytds"
    except ImportError:
        logger.warning("Neither pyodbc (with driver) nor pytds available for SQL Server")

    return ""


def get_backend() -> str:
    """Return ``"pyodbc"``, ``"pytds"`` or ``""``."""
    global _backend_cache
    if _backend_cache is None:
        _backend_cache = _detect_backend()
    return _backend_cache


# ---------------------------------------------------------------------------
# ODBC connection-string parser
# ---------------------------------------------------------------------------

def parse_odbc_connection_string(conn_str: str) -> Dict[str, str]:
    """
    Parse an ODBC-style connection string into a dict.

    Handles ``Key=Value;`` pairs and ``Driver={...}`` with braces.
    Keys are normalised to lower-case.
    """
    result: Dict[str, str] = {}
    i = 0
    length = len(conn_str)

    while i < length:
        # Skip whitespace / semicolons
        while i < length and conn_str[i] in (" ", "\t", ";", "\r", "\n"):
            i += 1
        if i >= length:
            break

        # Read key
        eq_pos = conn_str.find("=", i)
        if eq_pos == -1:
            break
        key = conn_str[i:eq_pos].strip()
        i = eq_pos + 1

        # Read value
        if i < length and conn_str[i] == "{":
            # Brace-quoted value  Driver={ODBC Driver 17 for SQL Server}
            close = conn_str.find("}", i + 1)
            if close == -1:
                value = conn_str[i + 1:]
                i = length
            else:
                value = conn_str[i + 1:close]
                i = close + 1
        else:
            semi = conn_str.find(";", i)
            if semi == -1:
                value = conn_str[i:]
                i = length
            else:
                value = conn_str[i:semi]
                i = semi + 1

        result[key.lower()] = value.strip()

    return result


# ---------------------------------------------------------------------------
# Placeholder translator  ?  ->  %s  (outside quoted strings)
# ---------------------------------------------------------------------------

def _translate_placeholders(sql: str) -> str:
    """Replace ``?`` with ``%s`` outside of single-quoted strings."""
    out: list[str] = []
    in_quote = False
    i = 0
    length = len(sql)

    while i < length:
        ch = sql[i]
        if ch == "'":
            if in_quote and i + 1 < length and sql[i + 1] == "'":
                # Escaped quote inside string ('')
                out.append("''")
                i += 2
                continue
            in_quote = not in_quote
            out.append(ch)
        elif ch == "?" and not in_quote:
            out.append("%s")
        else:
            out.append(ch)
        i += 1

    return "".join(out)


# ---------------------------------------------------------------------------
# pytds wrappers
# ---------------------------------------------------------------------------

class PytdsCursorWrapper:
    """Wraps a pytds cursor to translate ``?`` placeholders to ``%s``."""

    def __init__(self, real_cursor):
        self._cursor = real_cursor

    # --- delegated properties ---
    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    # --- execute ---
    def execute(self, sql: str, params=None):
        sql = _translate_placeholders(sql)
        if params is not None:
            if isinstance(params, (list, tuple)):
                return self._cursor.execute(sql, params)
            return self._cursor.execute(sql, (params,))
        return self._cursor.execute(sql)

    def executemany(self, sql: str, params_seq):
        sql = _translate_placeholders(sql)
        return self._cursor.executemany(sql, params_seq)

    # --- fetch ---
    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        if size is not None:
            return self._cursor.fetchmany(size)
        return self._cursor.fetchmany()

    # --- misc ---
    def close(self):
        return self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)


class PytdsConnectionWrapper:
    """Wraps a pytds connection to provide a pyodbc-compatible interface."""

    def __init__(self, real_conn):
        self._conn = real_conn

    def cursor(self):
        return PytdsCursorWrapper(self._conn.cursor())

    def close(self):
        return self._conn.close()

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def getinfo(self, info_type):
        """Emulate pyodbc getinfo – only SQL_DATABASE_NAME (16) supported."""
        # pyodbc.SQL_DATABASE_NAME == 16
        if info_type == 16:
            cur = self._conn.cursor()
            cur.execute("SELECT DB_NAME()")
            row = cur.fetchone()
            return row[0] if row else ""
        raise NotImplementedError(f"getinfo({info_type}) not supported via pytds")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def connect_sqlserver(conn_str: str, timeout: int = 5):
    """
    Connect to SQL Server using the best available backend.

    Args:
        conn_str: ODBC-style connection string.
        timeout: Connection timeout in seconds.

    Returns:
        A connection object (pyodbc.Connection or PytdsConnectionWrapper).

    Raises:
        RuntimeError: If no SQL Server backend is available.
        Exception: Any connection error from the underlying driver.
    """
    backend = get_backend()

    if backend == "pyodbc":
        import pyodbc
        return pyodbc.connect(conn_str, timeout=timeout)

    if backend == "pytds":
        return _connect_via_pytds(conn_str, timeout)

    raise RuntimeError(
        "No SQL Server backend available. "
        "Install pyodbc with an ODBC driver, or install python-tds."
    )


def _connect_via_pytds(conn_str: str, timeout: int) -> PytdsConnectionWrapper:
    """Build a pytds connection from an ODBC connection string."""
    import pytds

    params = parse_odbc_connection_string(conn_str)

    # Server & instance
    raw_server = params.get("server", params.get("data source", "localhost"))
    if "\\" in raw_server:
        server, instance = raw_server.split("\\", 1)
    else:
        server = raw_server
        instance = None

    # Port
    port = 1433
    if "," in server:
        # Server=host,port format
        server, port_str = server.rsplit(",", 1)
        try:
            port = int(port_str.strip())
        except ValueError:
            port = 1433

    database = params.get("database", params.get("initial catalog", "master"))

    # Authentication
    uid = params.get("uid", params.get("user id", ""))
    pwd = params.get("pwd", params.get("password", ""))
    trusted = params.get("trusted_connection", "").lower() in ("yes", "true", "sspi")

    connect_kwargs: Dict[str, Any] = {
        "server": server,
        "port": port,
        "database": database,
        "login_timeout": timeout,
    }

    if instance:
        connect_kwargs["instance"] = instance

    if trusted:
        # Windows integrated authentication via SSPI
        try:
            from pytds.login import SspiAuth
            connect_kwargs["auth"] = SspiAuth()
        except ImportError:
            logger.warning("SSPI auth requested but SspiAuth unavailable – trying without auth")
    elif uid:
        connect_kwargs["user"] = uid
        connect_kwargs["password"] = pwd

    conn = pytds.connect(**connect_kwargs)
    return PytdsConnectionWrapper(conn)
