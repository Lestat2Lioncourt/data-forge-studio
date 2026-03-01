"""
Centralized constants for DataForge Studio.

Eliminates magic numbers scattered across the codebase.
Import from here instead of hardcoding values.
"""

# ===========================================================================
# Timeouts (seconds)
# ===========================================================================
CONNECTION_TIMEOUT_S = 5        # Standard DB connection test timeout
PING_TIMEOUT_S = 3              # Quick alive-check (pre-connect)
POOL_WAIT_TIMEOUT_S = 30        # Waiting for a connection from pool
FTP_TEST_TIMEOUT_S = 15         # FTP connection test

# ===========================================================================
# Query / Data limits
# ===========================================================================
QUERY_PREVIEW_LIMIT = 100       # "SELECT TOP 100 *" default
QUERY_BATCH_SIZE = 1000         # Rows per batch for background loading
ANALYSIS_ROW_LIMIT = 10_000     # Max rows for distribution analysis

# ===========================================================================
# Numeric formatting
# ===========================================================================
SCI_NOTATION_UPPER = 10_000     # abs(value) >= this → scientific notation
SCI_NOTATION_LOWER = 0.01       # abs(value) < this → scientific notation

# ===========================================================================
# Connection pool
# ===========================================================================
POOL_MAX_CONNECTIONS = 5

# ===========================================================================
# UI Timer delays (milliseconds)
# ===========================================================================
DEFERRED_LOAD_DELAY_MS = 100    # Lazy-load after widget shown
FILTER_DEBOUNCE_MS = 400        # Wait before applying filter
AUTO_CONNECT_DELAY_MS = 500     # Startup auto-connect delay
WORKER_STOP_TIMEOUT_MS = 1000   # Max wait for worker thread shutdown
STATUS_FEEDBACK_SHORT_MS = 1500
STATUS_FEEDBACK_MS = 2000
STATUS_FEEDBACK_LONG_MS = 3000

# ===========================================================================
# UI sizes (pixels)
# ===========================================================================
TREE_ICON_SIZE = 16
SIDEBAR_ICON_SIZE = 24
TOOLBAR_HEIGHT = 40
PANEL_HEADER_HEIGHT = 28
PANEL_DEFAULT_WIDTH = 280
MAX_COLUMN_WIDTH = 300
DIALOG_MIN_WIDTH = 600
DIALOG_MIN_HEIGHT = 500

# ===========================================================================
# SQL identifier quoting
# ===========================================================================

# Quote characters per database type: (open, close)
_QUOTE_CHARS = {
    "sqlserver": ("[", "]"),
    "access":    ("[", "]"),
    "mysql":     ("`", "`"),
    "postgresql": ('"', '"'),
    "sqlite":    ('"', '"'),
}


def quote_identifier(name: str, db_type: str = "sqlite") -> str:
    """
    Quote a SQL identifier (table name, column, schema).

    Args:
        name: Raw identifier name
        db_type: Database type key

    Returns:
        Properly quoted identifier, e.g. [MyTable] or "my_table"
    """
    o, c = _QUOTE_CHARS.get(db_type, ('"', '"'))
    return f"{o}{name}{c}"


def quote_table(table_name: str, db_type: str = "sqlite",
                schema: str = None) -> str:
    """
    Build a fully-qualified quoted table reference.

    Handles dotted names: "public.users" is split and each part quoted
    individually, producing "public"."users" instead of "public.users".

    Args:
        table_name: Table name (may contain schema prefix like "schema.table")
        db_type: Database type key
        schema: Optional database/catalog name (prepended as prefix)

    Returns:
        e.g. [mydb].[dbo].[MyTable] or "public"."users"
    """
    # Split dotted table names and quote each part separately
    parts = table_name.split(".")
    quoted_parts = [quote_identifier(p, db_type) for p in parts]
    quoted_name = ".".join(quoted_parts)

    if schema:
        return f"{quote_identifier(schema, db_type)}.{quoted_name}"
    return quoted_name


def build_preview_sql(table_name: str, db_type: str = "sqlite",
                      schema: str = None, limit: int = None) -> str:
    """
    Build a SELECT * query with proper quoting and TOP/LIMIT syntax.

    Args:
        table_name: Table name
        db_type: Database type key
        schema: Optional schema/database name
        limit: Optional row limit

    Returns:
        Complete SQL string, e.g. SELECT TOP 100 * FROM [db].[table]
    """
    quoted = quote_table(table_name, db_type, schema)
    uses_top = db_type in ("sqlserver", "access")

    if limit:
        if uses_top:
            return f"SELECT TOP {limit} * FROM {quoted}"
        return f"SELECT * FROM {quoted} LIMIT {limit}"
    return f"SELECT * FROM {quoted}"
