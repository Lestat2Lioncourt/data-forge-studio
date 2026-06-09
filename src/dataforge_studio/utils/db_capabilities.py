"""
Database capabilities — small helpers describing what a connection type supports.

Kept as a single source of truth so the Resources context menu and the Workspace
tree agree on whether a connection exposes several databases (server) or a single
one (file-based / per-database connection).
"""

# Connection types where a single connection can reach several databases.
# PostgreSQL connects to ONE database per connection, so it is treated as
# single-database here (no server-level grouping in the tree).
MULTI_DATABASE_TYPES = {"sqlserver", "mysql", "mariadb"}


def is_multi_database_server(db_type: str) -> bool:
    """Return True if a connection of this type exposes multiple databases.

    Multi-database servers (SQL Server, MySQL/MariaDB) are grouped under a server
    node in the workspace tree, with one child per linked database. Single-database
    connections (SQLite, Access, PostgreSQL) are shown as a single node.
    """
    return (db_type or "").lower() in MULTI_DATABASE_TYPES
