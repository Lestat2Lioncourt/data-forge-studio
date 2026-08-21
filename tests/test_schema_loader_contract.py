"""
Tests that every schema loader honours the abstract contract.

Regression cover: `load_columns` had drifted into four different signatures.

    base         load_columns(table_name)
    SQL Server   load_columns(table_name, schema_name=None, database_name=None)
    MySQL        load_columns(table_name, schema_name=None)
    SQLite       load_columns(table_name)

Every existing caller passed `table_name` alone, so nothing broke until the ER
view expansion became the first caller to work polymorphically — it then raised
`TypeError: takes from 2 to 3 positional arguments but 4 were given` on MySQL,
silently degrading to "no columns" on four dialects out of six.

The point of these tests is that a signature can no longer drift for a dialect
nobody has an instance of to try.
"""
import inspect

import pytest

from dataforge_studio.database.schema_loaders.base import SchemaLoader
from dataforge_studio.database.schema_loaders.access_loader import AccessSchemaLoader
from dataforge_studio.database.schema_loaders.mysql_loader import MySQLSchemaLoader
from dataforge_studio.database.schema_loaders.postgresql_loader import PostgreSQLSchemaLoader
from dataforge_studio.database.schema_loaders.sqlite_loader import SQLiteSchemaLoader
from dataforge_studio.database.schema_loaders.sqlserver_loader import SQLServerSchemaLoader

LOADERS = [
    pytest.param(SQLServerSchemaLoader, id="sqlserver"),
    pytest.param(MySQLSchemaLoader, id="mysql"),
    pytest.param(PostgreSQLSchemaLoader, id="postgresql"),
    pytest.param(SQLiteSchemaLoader, id="sqlite"),
    pytest.param(AccessSchemaLoader, id="access"),
]

# Methods a caller may invoke without knowing which engine is behind the loader
POLYMORPHIC_METHODS = ["load_columns", "load_views", "load_tables"]


def parameters(cls, method):
    return inspect.signature(getattr(cls, method)).parameters


@pytest.mark.parametrize("loader_cls", LOADERS)
@pytest.mark.parametrize("method", POLYMORPHIC_METHODS)
def test_signature_accepts_everything_the_base_declares(loader_cls, method):
    """A dialect may accept more, never less, than the abstract contract."""
    base_params = parameters(SchemaLoader, method)
    own_params = parameters(loader_cls, method)

    missing = [name for name in base_params if name not in own_params]
    assert not missing, (
        f"{loader_cls.__name__}.{method}() does not accept {missing}, which "
        f"{SchemaLoader.__name__}.{method}() declares. A caller that does not "
        "know the engine would raise TypeError."
    )


@pytest.mark.parametrize("loader_cls", LOADERS)
def test_load_columns_takes_table_schema_and_database(loader_cls):
    """The three arguments the view expansion passes must be accepted everywhere.

    A dialect that ignores schema or database still has to accept them.
    """
    params = parameters(loader_cls, "load_columns")
    for name in ("table_name", "schema_name", "database_name"):
        assert name in params, f"{loader_cls.__name__}.load_columns() lacks {name}"

    for name in ("schema_name", "database_name"):
        assert params[name].default is None, (
            f"{loader_cls.__name__}.load_columns({name}) must default to None so "
            "engines that ignore it stay callable with the table name alone."
        )


@pytest.mark.parametrize("loader_cls", LOADERS)
def test_extra_arguments_are_optional_everywhere(loader_cls):
    """Calling with the table name alone must remain valid — that is what the
    existing callers do."""
    params = parameters(loader_cls, "load_columns")
    required = [
        name for name, p in params.items()
        if name != "self"
        and p.default is inspect.Parameter.empty
        and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
    ]
    assert required == ["table_name"], (
        f"{loader_cls.__name__}.load_columns() requires {required}; only "
        "table_name may be mandatory."
    )
