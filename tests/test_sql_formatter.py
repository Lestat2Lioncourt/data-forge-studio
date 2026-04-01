"""
Unit tests for SQL Formatter.
Tests format_sql() with all styles, _TopLevelScanner utilities,
CTE formatting, multi-statement splitting, and comment preservation.
"""
import pytest

from dataforge_studio.utils.sql_formatter import (
    format_sql,
    _TopLevelScanner,
)


class TestTopLevelScanner:
    """Tests for the _TopLevelScanner utility class."""

    def test_iter_simple(self):
        """iter() yields correct (index, char, depth, in_string) tuples."""
        result = list(_TopLevelScanner.iter("a(b)"))
        assert len(result) == 4
        # a at depth 0
        assert result[0] == (0, 'a', 0, False)
        # ( at depth 0, but after processing it depth becomes 1
        assert result[1] == (1, '(', 1, False)
        # b at depth 1
        assert result[2] == (2, 'b', 1, False)
        # ) at depth 0
        assert result[3] == (3, ')', 0, False)

    def test_iter_string_literal(self):
        """iter() correctly tracks string literal boundaries."""
        result = list(_TopLevelScanner.iter("'a(b)'"))
        # Parens inside strings should not affect depth
        for _, ch, depth, _ in result:
            assert depth == 0

    def test_paren_delta_balanced(self):
        """paren_delta() returns 0 for balanced parens."""
        assert _TopLevelScanner.paren_delta("(a + b)") == 0

    def test_paren_delta_unbalanced(self):
        """paren_delta() returns positive for unmatched open parens."""
        assert _TopLevelScanner.paren_delta("(a + (b") == 2

    def test_paren_delta_ignores_strings(self):
        """paren_delta() ignores parens inside string literals."""
        assert _TopLevelScanner.paren_delta("'(' + x") == 0

    def test_split_by_comma_simple(self):
        """split_by_comma() splits on top-level commas."""
        result = _TopLevelScanner.split_by_comma("a, b, c")
        assert result == ["a", " b", " c"]

    def test_split_by_comma_nested_parens(self):
        """split_by_comma() does not split inside parentheses."""
        result = _TopLevelScanner.split_by_comma("a, fn(b, c), d")
        assert len(result) == 3
        assert result[0] == "a"
        assert "fn(b, c)" in result[1]
        assert result[2].strip() == "d"

    def test_split_by_comma_string_literal(self):
        """split_by_comma() does not split on commas inside strings."""
        result = _TopLevelScanner.split_by_comma("a, 'b,c', d")
        assert len(result) == 3

    def test_find_keyword_basic(self):
        """find_keyword() finds a keyword at top level."""
        sql = "SELECT a FROM b WHERE c = 1"
        assert _TopLevelScanner.find_keyword(sql, "FROM") == 9
        assert _TopLevelScanner.find_keyword(sql, "WHERE") == 16

    def test_find_keyword_not_found(self):
        """find_keyword() returns -1 when keyword is absent."""
        assert _TopLevelScanner.find_keyword("SELECT a FROM b", "WHERE") == -1

    def test_find_keyword_respects_word_boundaries(self):
        """find_keyword() does not match partial words."""
        # PERFORM contains 'FROM' but should not match
        assert _TopLevelScanner.find_keyword("SELECT PERFORM FROM t", "FROM") == 15

    def test_find_keyword_inside_parens(self):
        """find_keyword() ignores keywords inside parentheses."""
        sql = "SELECT (SELECT FROM x) FROM y"
        pos = _TopLevelScanner.find_keyword(sql, "FROM")
        # Should find the outer FROM, not the one inside parens
        assert pos == 23

    def test_find_equals_basic(self):
        """find_equals() finds standalone = sign."""
        assert _TopLevelScanner.find_equals("a = b") == 2

    def test_find_equals_ignores_comparison_operators(self):
        """find_equals() skips >=, <=, != operators."""
        assert _TopLevelScanner.find_equals("a >= b") == -1
        assert _TopLevelScanner.find_equals("a <= b") == -1
        assert _TopLevelScanner.find_equals("a != b") == -1

    def test_find_equals_after_comparison(self):
        """find_equals() finds = after a comparison operator."""
        text = "a >= b AND c = d"
        pos = _TopLevelScanner.find_equals(text)
        assert pos == 13

    def test_extract_paren_content_basic(self):
        """extract_paren_content() extracts content between matching parens."""
        text = "fn(a, b)"
        result = _TopLevelScanner.extract_paren_content(text, 2)
        assert result == "a, b"

    def test_extract_paren_content_nested(self):
        """extract_paren_content() handles nested parens."""
        text = "fn(a, (b, c))"
        result = _TopLevelScanner.extract_paren_content(text, 2)
        assert result == "a, (b, c)"

    def test_extract_paren_content_unmatched(self):
        """extract_paren_content() returns None for unmatched paren."""
        text = "(a, b"
        result = _TopLevelScanner.extract_paren_content(text, 0)
        assert result is None

    def test_extract_paren_content_not_a_paren(self):
        """extract_paren_content() returns None if position is not '('."""
        result = _TopLevelScanner.extract_paren_content("abc", 0)
        assert result is None

    def test_extract_paren_content_past_end(self):
        """extract_paren_content() returns None if open_pos >= len(text)."""
        result = _TopLevelScanner.extract_paren_content("abc", 10)
        assert result is None


class TestFormatSqlCompact:
    """Tests for format_sql() with compact style."""

    def test_empty_input(self):
        """format_sql() returns empty/whitespace input unchanged."""
        assert format_sql("") == ""
        assert format_sql("   ") == "   "
        assert format_sql(None) is None

    def test_simple_select(self):
        """Compact style formats a simple SELECT."""
        sql = "select a, b from t where x = 1"
        result = format_sql(sql, style="compact")
        # Keywords should be uppercased
        assert "SELECT" in result
        assert "FROM" in result
        assert "WHERE" in result

    def test_keywords_uppercased(self):
        """Compact style uppercases SQL keywords."""
        result = format_sql("select * from table1", style="compact")
        assert "SELECT" in result
        assert "FROM" in result


class TestFormatSqlExpanded:
    """Tests for format_sql() with expanded/ultimate style."""

    def test_simple_select_expanded(self):
        """Expanded style formats a simple SELECT with keywords aligned."""
        sql = "select a, b from t where x = 1"
        result = format_sql(sql, style="expanded")
        assert "SELECT" in result
        assert "FROM" in result
        assert "WHERE" in result

    def test_ultimate_style(self):
        """Ultimate style applies sophisticated formatting."""
        sql = "select a, b, c from t1 inner join t2 on t1.id = t2.id where x = 1"
        result = format_sql(sql, style="ultimate")
        assert "SELECT" in result
        assert "FROM" in result
        assert "INNER JOIN" in result
        assert "WHERE" in result


class TestFormatSqlCommaFirst:
    """Tests for format_sql() with comma_first style."""

    def test_comma_first_basic(self):
        """Comma-first style places commas at beginning of lines."""
        sql = "select a, b, c from t"
        result = format_sql(sql, style="comma_first")
        assert "SELECT" in result
        # Commas should appear at the beginning of continuation lines
        lines = result.strip().split('\n')
        # At least some lines should start with a comma (after whitespace)
        comma_lines = [l for l in lines if l.strip().startswith(',')]
        assert len(comma_lines) > 0


class TestFormatSqlMultiStatement:
    """Tests for multi-statement SQL formatting."""

    def test_semicolon_splitting(self):
        """format_sql() handles multiple statements separated by semicolons."""
        sql = "select a from t1; select b from t2"
        result = format_sql(sql, style="compact")
        # Both statements should be formatted
        assert "SELECT" in result
        # Should contain semicolons as statement separators
        assert ";" in result

    def test_go_batch_separator(self):
        """format_sql() handles GO batch separators."""
        sql = "select a from t1\nGO\nselect b from t2"
        result = format_sql(sql, style="compact")
        assert "GO" in result
        assert "SELECT" in result


class TestFormatSqlSelectModifiers:
    """Tests for SELECT DISTINCT and SELECT TOP N formatting."""

    def test_select_distinct(self):
        """format_sql() preserves SELECT DISTINCT."""
        sql = "select distinct a, b from t"
        result = format_sql(sql, style="expanded")
        upper = result.upper()
        assert "SELECT" in upper
        assert "DISTINCT" in upper

    def test_select_top(self):
        """format_sql() preserves SELECT TOP N."""
        sql = "select top 10 a, b from t"
        result = format_sql(sql, style="expanded")
        upper = result.upper()
        assert "SELECT" in upper
        assert "TOP" in upper
        assert "10" in result


class TestFormatSqlCommentPreservation:
    """Tests for standalone comment preservation."""

    def test_standalone_comment_preserved(self):
        """format_sql() preserves standalone comment lines."""
        sql = "-- This is a comment\nSELECT a FROM t"
        result = format_sql(sql, style="compact")
        assert "-- This is a comment" in result

    def test_into_comment_preserved(self):
        """format_sql() preserves --INTO style comments."""
        sql = "--INTO #temp\nSELECT a FROM t"
        result = format_sql(sql, style="compact")
        assert "--INTO #temp" in result


class TestFormatSqlCTE:
    """Tests for CTE (WITH ... AS) formatting."""

    def test_simple_cte(self):
        """format_sql() formats a simple CTE query."""
        sql = "WITH cte AS (SELECT a FROM t) SELECT * FROM cte"
        result = format_sql(sql, style="ultimate")
        assert "WITH" in result
        assert "AS (" in result or "AS(" in result
        assert "SELECT" in result

    def test_multiple_ctes(self):
        """format_sql() formats multiple CTEs."""
        sql = (
            "WITH cte1 AS (SELECT a FROM t1), "
            "cte2 AS (SELECT b FROM t2) "
            "SELECT * FROM cte1 JOIN cte2 ON cte1.a = cte2.b"
        )
        result = format_sql(sql, style="ultimate")
        assert "cte1" in result
        assert "cte2" in result


class TestFormatSqlWhereAlignment:
    """Tests for WHERE/AND alignment."""

    def test_where_and_formatting(self):
        """format_sql() formats WHERE with AND conditions."""
        sql = "SELECT a FROM t WHERE x = 1 AND y = 2 AND z = 3"
        result = format_sql(sql, style="expanded")
        assert "WHERE" in result
        assert "AND" in result
        # Multiple conditions should be on separate lines
        lines = [l.strip() for l in result.split('\n') if l.strip()]
        and_lines = [l for l in lines if l.startswith('AND')]
        assert len(and_lines) >= 1


class TestFormatSqlUnknownStyle:
    """Tests for unknown/default style fallback."""

    def test_unknown_style_still_formats(self):
        """format_sql() with an unknown style still produces valid output."""
        sql = "select a from t"
        result = format_sql(sql, style="nonexistent_style")
        assert "SELECT" in result
        assert "FROM" in result
