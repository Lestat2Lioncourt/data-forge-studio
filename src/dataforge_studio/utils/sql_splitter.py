"""
SQL Splitter - Split SQL text into individual statements for batch execution.

Handles:
- Standard semicolon-delimited statements
- T-SQL GO batch separator
- Comments (single-line -- and multi-line /* */)
- Strings with embedded semicolons (via sqlparse)
"""

import re
from dataclasses import dataclass
from typing import List, Tuple

import sqlparse

import logging
logger = logging.getLogger(__name__)


@dataclass
class SQLStatement:
    """Represents a single SQL statement."""
    text: str           # The SQL text
    line_start: int     # Starting line number (1-based)
    line_end: int       # Ending line number (1-based)
    is_select: bool     # True if SELECT statement that returns results


def split_sql_statements(sql_text: str, db_type: str = "sqlserver") -> List[SQLStatement]:
    """
    Split SQL text into individual statements.

    Args:
        sql_text: Full SQL text with multiple statements
        db_type: Database type ("sqlserver", "sqlite", etc.)

    Returns:
        List of SQLStatement objects
    """
    if not sql_text or not sql_text.strip():
        return []

    statements = []

    # For SQL Server, first split on GO statements
    if db_type == "sqlserver":
        batches = _split_on_go(sql_text)
    else:
        batches = [(sql_text, 1)]

    # Then use sqlparse for each batch
    for batch_text, batch_start_line in batches:
        parsed = sqlparse.split(batch_text)

        current_line = batch_start_line
        for stmt_text in parsed:
            stmt_text = stmt_text.strip()
            if not stmt_text:
                continue

            # Count lines in this statement
            stmt_lines = stmt_text.count('\n') + 1

            # Determine if SELECT
            is_select = _is_select_statement(stmt_text)

            statements.append(SQLStatement(
                text=stmt_text,
                line_start=current_line,
                line_end=current_line + stmt_lines - 1,
                is_select=is_select
            ))

            current_line += stmt_lines

    return statements


def _split_on_go(sql_text: str) -> List[Tuple[str, int]]:
    """
    Split T-SQL text on GO batch separators.

    GO must be on its own line (possibly with whitespace).

    Returns:
        List of (batch_text, start_line) tuples
    """
    # Pattern: GO on its own line (case-insensitive)
    # Matches: "GO", "  GO  ", "go", but not "GOING" or "ERGO"
    go_pattern = re.compile(r'^\s*GO\s*$', re.MULTILINE | re.IGNORECASE)

    batches = []
    lines = sql_text.split('\n')

    current_batch_lines = []
    current_start_line = 1

    for i, line in enumerate(lines, 1):
        if go_pattern.match(line):
            # End current batch
            if current_batch_lines:
                batch_text = '\n'.join(current_batch_lines)
                batches.append((batch_text, current_start_line))
            current_batch_lines = []
            current_start_line = i + 1
        else:
            current_batch_lines.append(line)

    # Add final batch
    if current_batch_lines:
        batch_text = '\n'.join(current_batch_lines)
        batches.append((batch_text, current_start_line))

    return batches


def _is_select_statement(stmt_text: str) -> bool:
    """
    Determine if a statement is a SELECT query that returns results.

    Returns True for:
    - SELECT statements
    - WITH ... SELECT (CTEs)
    - EXEC/EXECUTE that might return results

    Returns False for:
    - INSERT/UPDATE/DELETE
    - CREATE/ALTER/DROP
    - DECLARE, SET, USE, etc.
    """
    # Normalize: remove comments and extra whitespace
    try:
        cleaned = sqlparse.format(stmt_text, strip_comments=True).strip().upper()
    except Exception:
        cleaned = stmt_text.strip().upper()

    if not cleaned:
        return False

    # Get first word (skip any leading whitespace)
    words = cleaned.split()
    first_word = words[0] if words else ""

    select_keywords = {'SELECT', 'WITH'}
    non_select_keywords = {
        'INSERT', 'UPDATE', 'DELETE', 'MERGE',
        'CREATE', 'ALTER', 'DROP', 'TRUNCATE',
        'DECLARE', 'SET', 'USE', 'PRINT', 'RAISERROR',
        'BEGIN', 'END', 'IF', 'WHILE', 'GOTO',
        'GRANT', 'REVOKE', 'DENY'
    }

    if first_word in select_keywords:
        return True
    if first_word in non_select_keywords:
        return False

    # EXEC/EXECUTE could return results
    if first_word in {'EXEC', 'EXECUTE'}:
        return True  # Assume it might return results

    return False
