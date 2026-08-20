"""
Tests for connection-string host/port extraction.

Regression cover for two production defects:
- the reachability probe swept every known database port (1433, 3306, 445, ...)
  because the port was never extracted, so a MySQL test knocked on the SQL
  Server port first;
- a password containing '@' or '/' shifted the parsed host, making the probe
  target a nonexistent name and report the server as unreachable while the
  connection itself worked.
"""
import pytest

from dataforge_studio.utils.network_utils import (
    DEFAULT_PORTS,
    extract_host_from_connection_string,
    extract_host_port_from_connection_string,
)


HOST = "dbsrv.corp.local"


@pytest.mark.parametrize("connection_string, db_type, expected_host, expected_port", [
    # MySQL / MariaDB
    (f"mysql+pymysql://alice:secret@{HOST}:3306/ventes", "mysql", HOST, 3306),
    (f"mysql+pymysql://alice:secret@{HOST}/ventes", "mysql", HOST, 3306),
    (f"mysql+pymysql://{HOST}:3306/ventes", "mysql", HOST, 3306),
    (f"mysql+pymysql://alice:s@{HOST}:33060/ventes", "mysql", HOST, 33060),
    (f"mysql+pymysql://alice:secret@{HOST}/ventes", "mariadb", HOST, 3306),
    # PostgreSQL
    (f"postgresql://bob:pwd@{HOST}:5432/base", "postgresql", HOST, 5432),
    # SQL Server, ODBC style
    (f"DRIVER={{ODBC Driver 17}};SERVER={HOST};DATABASE=x;", "sqlserver", HOST, 1433),
    (f"DRIVER={{x}};SERVER={HOST},14330;DATABASE=y;", "sqlserver", HOST, 14330),
    ("DRIVER={x};SERVER=SQLSRV\\PROD;DATABASE=y;", "sqlserver", "SQLSRV", 1433),
    # key=value style with an explicit port
    (f"host={HOST};port=5433;dbname=base", "postgresql", HOST, 5433),
    # IPv6 literal
    (f"mysql+pymysql://u:p@[2001:db8::1]:3306/base", "mysql", "2001:db8::1", 3306),
    # No host at all
    ("sqlite:///C:/data/base.db", "sqlite", None, None),
    ("", "mysql", None, None),
])
def test_extract_host_and_port(connection_string, db_type, expected_host, expected_port):
    host, port = extract_host_port_from_connection_string(connection_string, db_type)
    assert host == expected_host
    assert port == expected_port


@pytest.mark.parametrize("password", [
    "P@ssw0rd",      # '@' would end the userinfo too early
    "a/b",           # '/' would be taken for the start of the database path
    "a/b@c",         # both
    "p@ss/w@rd",     # several of each
])
def test_special_characters_in_password_do_not_shift_the_host(password):
    """The host is what follows the LAST '@', and the path starts after it."""
    conn = f"mysql+pymysql://alice:{password}@{HOST}:3306/ventes"
    host, port = extract_host_port_from_connection_string(conn, "mysql")
    assert host == HOST
    assert port == 3306


def test_port_falls_back_to_the_db_type_default_not_to_a_sweep():
    """Without an explicit port, the default must match the engine — never 1433
    for MySQL, which is what made the probe hit the SQL Server port."""
    host, port = extract_host_port_from_connection_string(
        f"mysql+pymysql://alice:secret@{HOST}/ventes", "mysql")
    assert port == DEFAULT_PORTS["mysql"] == 3306
    assert port != DEFAULT_PORTS["sqlserver"]


def test_legacy_host_only_helper_still_works():
    """The single-value helper is kept for existing callers."""
    assert extract_host_from_connection_string(
        f"mysql+pymysql://alice:P@ssw0rd@{HOST}:3306/ventes", "mysql") == HOST
