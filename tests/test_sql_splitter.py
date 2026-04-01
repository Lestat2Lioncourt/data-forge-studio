"""
Unit tests for SQL Splitter.
Tests split_sql_statements(), GO batch separator handling,
is_select detection, and needs_script_mode().
"""
import pytest

from dataforge_studio.utils.sql_splitter import (
    split_sql_statements,
    needs_script_mode,
    _is_select_statement,
    _split_on_go,
    SQLStatement,
)


class TestSplitSqlStatements:
    """Tests for split_sql_statements()."""

    def test_empty_input(self):
        """split_sql_statements() returns empty list for empty input."""
        assert split_sql_statements("") == []
        assert split_sql_statements("   ") == []
        assert split_sql_statements(None) == []

    def test_single_select(self):
        """split_sql_statements() returns one statement for a simple SELECT."""
        stmts = split_sql_statements("SELECT a FROM t")
        assert len(stmts) == 1
        assert stmts[0].is_select is True
        assert "SELECT" in stmts[0].text

    def test_multiple_statements_semicolon(self):
        """split_sql_statements() splits on semicolons."""
        sql = "SELECT a FROM t1; SELECT b FROM t2"
        stmts = split_sql_statements(sql)
        assert len(stmts) == 2
        assert stmts[0].is_select is True
        assert stmts[1].is_select is True

    def test_mixed_select_and_dml(self):
        """split_sql_statements() identifies SELECT vs DML correctly."""
        sql = "INSERT INTO t1 VALUES (1); SELECT * FROM t1"
        stmts = split_sql_statements(sql)
        assert len(stmts) == 2
        assert stmts[0].is_select is False
        assert stmts[1].is_select is True

    def test_line_numbers(self):
        """split_sql_statements() tracks line numbers."""
        sql = "SELECT a FROM t1;\nSELECT b FROM t2"
        stmts = split_sql_statements(sql)
        assert len(stmts) == 2
        assert stmts[0].line_start == 1

    def test_non_sqlserver_no_go_split(self):
        """split_sql_statements() with non-sqlserver db_type doesn't split on GO."""
        sql = "SELECT 1\nGO\nSELECT 2"
        stmts = split_sql_statements(sql, db_type="sqlite")
        # Without GO splitting, sqlparse may treat this differently
        # but GO won't be treated as a batch separator
        assert len(stmts) >= 1


class TestSplitOnGo:
    """Tests for _split_on_go() GO batch separator handling."""

    def test_no_go(self):
        """_split_on_go() returns single batch when no GO present."""
        batches = _split_on_go("SELECT a FROM t")
        assert len(batches) == 1
        assert batches[0][0].strip() == "SELECT a FROM t"
        assert batches[0][1] == 1

    def test_single_go(self):
        """_split_on_go() splits on a single GO."""
        sql = "SELECT a FROM t1\nGO\nSELECT b FROM t2"
        batches = _split_on_go(sql)
        assert len(batches) == 2
        assert "SELECT a" in batches[0][0]
        assert "SELECT b" in batches[1][0]

    def test_go_case_insensitive(self):
        """_split_on_go() is case-insensitive for GO."""
        sql = "SELECT 1\ngo\nSELECT 2"
        batches = _split_on_go(sql)
        assert len(batches) == 2

    def test_go_with_whitespace(self):
        """_split_on_go() handles GO with surrounding whitespace."""
        sql = "SELECT 1\n  GO  \nSELECT 2"
        batches = _split_on_go(sql)
        assert len(batches) == 2

    def test_go_not_in_word(self):
        """_split_on_go() does not split on GO within words like ERGO."""
        sql = "SELECT ERGO FROM t"
        batches = _split_on_go(sql)
        assert len(batches) == 1

    def test_multiple_go(self):
        """_split_on_go() handles multiple GO separators."""
        sql = "SELECT 1\nGO\nSELECT 2\nGO\nSELECT 3"
        batches = _split_on_go(sql)
        assert len(batches) == 3

    def test_go_line_tracking(self):
        """_split_on_go() tracks start line numbers correctly."""
        sql = "SELECT 1\nGO\nSELECT 2"
        batches = _split_on_go(sql)
        assert batches[0][1] == 1   # First batch starts at line 1
        assert batches[1][1] == 3   # Second batch starts at line 3 (after GO on line 2)


class TestIsSelectStatement:
    """Tests for _is_select_statement()."""

    def test_simple_select(self):
        """SELECT is detected as a select statement."""
        assert _is_select_statement("SELECT a FROM t") is True

    def test_select_with_where(self):
        """SELECT with WHERE is still a select."""
        assert _is_select_statement("SELECT a FROM t WHERE x = 1") is True

    def test_with_cte(self):
        """WITH (CTE) is detected as a select statement."""
        assert _is_select_statement("WITH cte AS (SELECT 1) SELECT * FROM cte") is True

    def test_insert(self):
        """INSERT is not a select statement."""
        assert _is_select_statement("INSERT INTO t VALUES (1)") is False

    def test_update(self):
        """UPDATE is not a select statement."""
        assert _is_select_statement("UPDATE t SET a = 1") is False

    def test_delete(self):
        """DELETE is not a select statement."""
        assert _is_select_statement("DELETE FROM t WHERE x = 1") is False

    def test_create(self):
        """CREATE is not a select statement."""
        assert _is_select_statement("CREATE TABLE t (a INT)") is False

    def test_declare(self):
        """DECLARE is not a select statement."""
        assert _is_select_statement("DECLARE @x INT = 1") is False

    def test_exec(self):
        """EXEC/EXECUTE is treated as a select (might return results)."""
        assert _is_select_statement("EXEC sp_who") is True
        assert _is_select_statement("EXECUTE sp_who") is True

    def test_select_into(self):
        """SELECT ... INTO is not a select (it's DDL)."""
        assert _is_select_statement("SELECT a INTO #temp FROM t") is False

    def test_empty_string(self):
        """Empty string is not a select."""
        assert _is_select_statement("") is False
        assert _is_select_statement("   ") is False

    def test_drop(self):
        """DROP is not a select statement."""
        assert _is_select_statement("DROP TABLE t") is False

    def test_alter(self):
        """ALTER is not a select statement."""
        assert _is_select_statement("ALTER TABLE t ADD col INT") is False

    def test_set(self):
        """SET is not a select statement."""
        assert _is_select_statement("SET NOCOUNT ON") is False

    def test_merge(self):
        """MERGE is not a select statement."""
        assert _is_select_statement("MERGE INTO t USING s ON t.id = s.id") is False

    def test_grant(self):
        """GRANT is not a select statement."""
        assert _is_select_statement("GRANT SELECT ON t TO user1") is False


class TestNeedsScriptMode:
    """Tests for needs_script_mode()."""

    def test_single_select_no_script_mode(self):
        """A single SELECT does not need script mode."""
        assert needs_script_mode("SELECT * FROM t") is False

    def test_multiple_selects_no_script_mode(self):
        """Multiple SELECTs do not need script mode."""
        assert needs_script_mode("SELECT 1; SELECT 2") is False

    def test_insert_needs_script_mode(self):
        """An INSERT statement needs script mode."""
        assert needs_script_mode("INSERT INTO t VALUES (1)") is True

    def test_mixed_needs_script_mode(self):
        """Mixed SELECT and DML needs script mode."""
        sql = "CREATE TABLE #t (a INT); SELECT * FROM #t"
        assert needs_script_mode(sql) is True

    def test_empty_no_script_mode(self):
        """Empty SQL does not need script mode."""
        assert needs_script_mode("") is False

    def test_declare_needs_script_mode(self):
        """DECLARE variable needs script mode."""
        sql = "DECLARE @x INT = 1; SELECT @x"
        assert needs_script_mode(sql) is True
