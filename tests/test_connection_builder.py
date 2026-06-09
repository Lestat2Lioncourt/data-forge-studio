"""
Unit tests for the centralized connection builder.

Covers the configuration-error paths (no real server needed): these are the
cases that used to be duplicated across the worker / mixin / reconnect and could
silently diverge.
"""
import pytest

from dataforge_studio.database.connection_builder import (
    build_connection, ConnectionConfigError,
)
from dataforge_studio.database.models import DatabaseConnection


def _conn(db_type, connection_string=""):
    return DatabaseConnection(
        id="t", name="T", db_type=db_type,
        connection_string=connection_string, description=""
    )


class TestConnectionBuilder:
    def test_unsupported_type(self):
        with pytest.raises(ConnectionConfigError) as ei:
            build_connection(_conn("oracle"))
        assert ei.value.key == "db_type_not_supported"
        assert ei.value.params.get("db_type") == "oracle"

    def test_sqlite_missing_file(self):
        with pytest.raises(ConnectionConfigError) as ei:
            build_connection(_conn("sqlite", "sqlite:///Z:/nope/missing.db"))
        assert ei.value.key == "db_file_not_found"

    def test_access_missing_file(self):
        with pytest.raises(ConnectionConfigError) as ei:
            build_connection(_conn("access", "Driver={x};Dbq=Z:/nope/missing.accdb;"))
        assert ei.value.key == "db_access_file_missing"

    def test_mysql_bad_format(self):
        with pytest.raises(ConnectionConfigError) as ei:
            build_connection(_conn("mysql", "not-a-mysql-url"))
        assert ei.value.key == "db_mysql_format_unsupported"

    def test_mariadb_alias_bad_format(self):
        # 'mariadb' must be handled like 'mysql'
        with pytest.raises(ConnectionConfigError) as ei:
            build_connection(_conn("mariadb", "not-a-mysql-url"))
        assert ei.value.key == "db_mysql_format_unsupported"

    def test_postgres_bad_format(self):
        with pytest.raises(ConnectionConfigError) as ei:
            build_connection(_conn("postgresql", "not-a-pg-url"))
        assert ei.value.key == "db_pg_format_unsupported"

    def test_postgres_alias_bad_format(self):
        # 'postgres' alias must be handled like 'postgresql'
        with pytest.raises(ConnectionConfigError) as ei:
            build_connection(_conn("postgres", "not-a-pg-url"))
        assert ei.value.key == "db_pg_format_unsupported"
