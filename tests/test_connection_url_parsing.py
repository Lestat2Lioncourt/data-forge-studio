"""
Tests for connection URL splitting.

Regression cover for a bug reported from production: testing a remote MySQL
connection failed with

    (2003, "Can't connect to MySQL server on '@192.168.86.30'
           ([Errno 11003] getaddrinfo failed)")

The password ended with '@'. Five hand-rolled parsers all split on the FIRST
'@', so everything after it became the host - here the literal string
'@192.168.86.30', which of course does not resolve. No packet ever left the
machine, which is why the network trace was a red herring.

Saving and browsing kept working because stored connection strings carry no
credentials at all (they live in the keyring); only the Test button injects
them into the URL.
"""
import pytest

from dataforge_studio.utils.connection_helpers import (
    quote_credential,
    split_db_url,
    parse_mysql_url,
    parse_postgresql_url,
)

HOST = "192.168.86.30"


@pytest.mark.parametrize("password", [
    "simple",
    "termine@",      # the reported case: trailing '@'
    "P@ssw0rd",      # '@' in the middle
    "a/b",           # '/' would look like the start of the database path
    "a@b/c@d",       # several of each
    "@",             # nothing but the separator
])
def test_password_special_characters_do_not_shift_the_host(password):
    url = f"lucie:{password}@{HOST}:3306/cnip3"
    parts = split_db_url(url, default_port="3306")
    assert parts["host"] == HOST
    assert parts["port"] == "3306"
    assert parts["user"] == "lucie"
    assert parts["password"] == password
    assert parts["database"] == "cnip3"


def test_the_exact_url_from_the_bug_report():
    """'@192.168.86.30' as a host was the whole failure."""
    parts = split_db_url(f"lucie:termine@@{HOST}:3306/cnip3", default_port="3306")
    assert parts["host"] == HOST
    assert not parts["host"].startswith("@")


@pytest.mark.parametrize("url, default_port, expected", [
    # No credentials at all - how connections are actually stored
    (f"{HOST}:3306/cnip3", "3306", {"host": HOST, "port": "3306", "user": "",
                                    "password": "", "database": "cnip3"}),
    (f"{HOST}:3306", "3306", {"host": HOST, "port": "3306", "user": "",
                              "password": "", "database": ""}),
    # No port -> the engine default
    (f"bob@{HOST}/base", "5432", {"host": HOST, "port": "5432", "user": "bob",
                                  "password": "", "database": "base"}),
    # Query parameters are dropped from the database name
    (f"{HOST}:5432/base?sslmode=require", "5432", {"host": HOST, "port": "5432",
                                                   "user": "", "password": "",
                                                   "database": "base"}),
    # IPv6 literal
    ("u:p@[2001:db8::1]:3306/base", "3306", {"host": "2001:db8::1", "port": "3306",
                                             "user": "u", "password": "p",
                                             "database": "base"}),
])
def test_url_shapes(url, default_port, expected):
    assert split_db_url(url, default_port) == expected


def test_percent_encoded_credentials_round_trip():
    """What the dialog writes must be what the parser reads back."""
    user, password = "lucie", "termine@/x"
    url = f"{quote_credential(user)}:{quote_credential(password)}@{HOST}:3306/cnip3"
    assert "@" not in url.rpartition("@")[0].replace(quote_credential(password), "")
    parts = split_db_url(url, default_port="3306")
    assert parts["user"] == user
    assert parts["password"] == password
    assert parts["host"] == HOST


def test_mysql_url_helper_uses_the_shared_parser():
    kwargs = parse_mysql_url(f"mysql+pymysql://lucie:termine@@{HOST}:3306/cnip3")
    assert kwargs["host"] == HOST
    assert kwargs["port"] == 3306
    assert kwargs["user"] == "lucie"
    assert kwargs["password"] == "termine@"
    assert kwargs["database"] == "cnip3"


def test_postgresql_url_helper_uses_the_shared_parser():
    kwargs = parse_postgresql_url(f"postgresql://bob:p@ss@{HOST}:5432/base")
    assert kwargs["host"] == HOST
    assert kwargs["port"] == 5432
    assert kwargs["password"] == "p@ss"
    assert kwargs["database"] == "base"


def test_stored_shape_without_credentials_still_parses():
    """Existing saved connections carry no credentials - must be untouched."""
    kwargs = parse_mysql_url(f"mysql+pymysql://{HOST}:3306/cnip3")
    assert kwargs["host"] == HOST
    assert kwargs["user"] == ""
    assert kwargs["database"] == "cnip3"
