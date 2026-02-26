"""
SQL Formatter - Sophisticated SQL query formatting utilities

Provides multiple formatting styles:
- compact: Multiple columns on same line
- expanded: One column per line
- comma_first: Comma-first style
- ultimate: Full alignment (keywords, AS, aliases, operators)
"""

import re
import sqlparse

import logging
logger = logging.getLogger(__name__)

# Main SQL keywords for section parsing and alignment
MAIN_KEYWORDS = [
    'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY',
    'INNER JOIN', 'LEFT JOIN', 'LEFT OUTER JOIN', 'RIGHT JOIN', 'RIGHT OUTER JOIN',
    'FULL JOIN', 'FULL OUTER JOIN', 'CROSS JOIN', 'JOIN',
    'UNION', 'UNION ALL', 'LIMIT', 'OFFSET',
    'INSERT INTO', 'INSERT', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM', 'DELETE',
    'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE',
    'MERGE INTO', 'MERGE', 'WHEN MATCHED', 'WHEN NOT MATCHED',
    'WITH'
]
MAX_KEYWORD_LEN = max(len(kw) for kw in MAIN_KEYWORDS)
JOIN_TYPES = frozenset({
    'FROM', 'INNER JOIN', 'LEFT JOIN', 'LEFT OUTER JOIN',
    'RIGHT JOIN', 'RIGHT OUTER JOIN', 'FULL JOIN', 'FULL OUTER JOIN',
    'CROSS JOIN', 'JOIN',
})


def format_sql(sql_text: str, style: str = "compact") -> str:
    """
    Format SQL query with specified style.

    Args:
        sql_text: SQL query to format
        style: Format style ("compact", "expanded", "comma_first", "ultimate")

    Returns:
        Formatted SQL string
    """
    if not sql_text or not sql_text.strip():
        return sql_text

    try:
        # Split by GO batch separators (SQL Server), format each batch separately
        batches = re.split(r'(?mi)^\s*GO\s*$', sql_text)
        has_go = len(batches) > 1

        formatted_batches = []
        for batch in batches:
            stripped = batch.strip().rstrip(';').strip()
            if stripped:
                formatted_batches.append(_format_single_batch(stripped, style))

        if has_go:
            return '\nGO\n\n'.join(formatted_batches) + '\nGO\n'
        return formatted_batches[0] if formatted_batches else sql_text

    except Exception as e:
        logger.error(f"SQL formatting error: {e}")
        raise


def _format_single_batch(sql_text: str, style: str) -> str:
    """Format a single SQL batch (no GO separators)."""
    if style == "compact":
        return sqlparse.format(
            sql_text,
            reindent=True,
            keyword_case='upper',
            indent_width=2,
            use_space_around_operators=True,
            wrap_after=120
        )

    elif style == "expanded":
        formatted = sqlparse.format(
            sql_text,
            reindent=True,
            keyword_case='upper',
            indent_width=4,
            use_space_around_operators=True
        )
        return _force_one_column_per_line(formatted)

    elif style == "comma_first":
        return sqlparse.format(
            sql_text,
            reindent=True,
            keyword_case='upper',
            indent_width=4,
            use_space_around_operators=True,
            comma_first=True
        )

    elif style == "ultimate":
        # Try CTE-aware formatting first (handles WITH ... AS queries)
        cte_result = _try_format_cte_ultimate(sql_text)
        if cte_result is not None:
            return cte_result
        # Normal ultimate formatting (no CTEs)
        formatted = sqlparse.format(
            sql_text,
            reindent=True,
            keyword_case='upper',
            indent_width=4,
            use_space_around_operators=True
        )
        return _apply_sophisticated_formatting(formatted)

    else:
        return sqlparse.format(
            sql_text,
            reindent=True,
            keyword_case='upper',
            indent_width=4
        )


def _force_one_column_per_line(sql_text: str) -> str:
    """Force SELECT columns to be on separate lines"""
    lines = sql_text.split('\n')
    result = []
    in_select = False

    for line in lines:
        stripped = line.strip().upper()

        if stripped.startswith('SELECT'):
            in_select = True
            if ',' in line:
                parts = line.split(',')
                result.append(parts[0])
                for part in parts[1:]:
                    result.append(f"    , {part.strip()}")
            else:
                result.append(line)

        elif in_select and (stripped.startswith('FROM') or stripped.startswith('WHERE') or
                           stripped.startswith('ORDER BY') or stripped.startswith('GROUP BY')):
            in_select = False
            result.append(line)

        elif in_select and ',' in line:
            parts = line.split(',')
            for i, part in enumerate(parts):
                if i == 0:
                    result.append(part.rstrip())
                else:
                    indent = len(line) - len(line.lstrip())
                    result.append(f"{' ' * indent}, {part.strip()}")
        else:
            result.append(line)

    return '\n'.join(result)


def _find_top_level_with(sql: str) -> int:
    """Find position of WITH keyword at top level (not inside parens or strings)."""
    upper = sql.upper()
    depth = 0
    in_single = False
    i = 0
    length = len(sql)

    while i < length:
        ch = sql[i]
        if ch == "'" and not in_single:
            in_single = True
        elif ch == "'" and in_single:
            in_single = False
        elif not in_single:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif depth == 0 and upper[i:i + 4] == 'WITH':
                before_ok = (i == 0 or not (upper[i - 1].isalnum() or upper[i - 1] == '_'))
                after_ok = (i + 4 >= length or not (upper[i + 4].isalnum() or upper[i + 4] == '_'))
                if before_ok and after_ok:
                    return i
        i += 1

    return -1


def _extract_ctes_from_text(text: str):
    """Parse CTE definitions from text after WITH keyword.

    Returns (list_of_ctes, remaining_text_after_ctes).
    Each CTE is {'name': str, 'body': str}.
    """
    ctes = []
    i = 0
    length = len(text)

    while i < length:
        # Skip whitespace and commas
        while i < length and text[i] in (' ', '\t', '\n', '\r', ','):
            i += 1
        if i >= length:
            break

        # Find AS ( pattern
        as_match = re.search(r'\bAS\s*\(', text[i:], re.IGNORECASE)
        if not as_match:
            break

        cte_name = text[i:i + as_match.start()].strip()
        paren_pos = i + as_match.end() - 1  # position of '('

        # Find matching closing paren
        depth = 0
        body_start = paren_pos + 1
        close_pos = -1
        in_single = False
        for j in range(paren_pos, length):
            ch = text[j]
            if ch == "'" and not in_single:
                in_single = True
            elif ch == "'" and in_single:
                in_single = False
            elif not in_single:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        close_pos = j
                        break

        if close_pos < 0:
            body = text[body_start:].strip()
            ctes.append({'name': cte_name, 'body': body})
            return ctes, ''

        body = text[body_start:close_pos].strip()
        ctes.append({'name': cte_name, 'body': body})
        i = close_pos + 1

        # Check if next non-whitespace is a comma (another CTE follows)
        j = i
        while j < length and text[j] in (' ', '\t', '\n', '\r'):
            j += 1

        if j < length and text[j] == ',':
            i = j + 1  # skip comma, continue to next CTE
        else:
            # No more CTEs, remaining text is the main body
            return ctes, text[i:].strip()

    return ctes, text[i:].strip() if i < length else ''


def _try_format_cte_ultimate(sql_text: str) -> str | None:
    """Try to format a CTE query in ultimate style. Returns None if no CTEs found."""
    # Uppercase keywords without reindenting (preserve structure for CTE parsing)
    upper_sql = sqlparse.format(sql_text, keyword_case='upper',
                                use_space_around_operators=True)

    with_pos = _find_top_level_with(upper_sql)
    if with_pos < 0:
        return None

    preamble = upper_sql[:with_pos].strip()
    rest = upper_sql[with_pos + 4:]  # skip "WITH"

    ctes, main_body = _extract_ctes_from_text(rest)
    if not ctes:
        return None

    result_lines = []

    # Preamble (e.g., CREATE VIEW ... AS)
    if preamble:
        result_lines.append(preamble)

    cte_indent = "    "  # 4-space indent for CTE body lines

    for i, cte in enumerate(ctes):
        # CTE header line
        if i == 0:
            result_lines.append(f"WITH {cte['name']} AS (")
        else:
            result_lines.append(f", {cte['name']} AS (")

        # Format CTE body through the full pipeline
        body_formatted = sqlparse.format(
            cte['body'], reindent=True, keyword_case='upper',
            indent_width=4, use_space_around_operators=True
        )
        body_lines = _format_sql_lines(body_formatted.split('\n'))

        for bl in body_lines:
            result_lines.append(cte_indent + bl)

        result_lines.append(")")

    # Format main body (SELECT ... UNION ALL ... etc.)
    if main_body.strip():
        main_formatted = sqlparse.format(
            main_body, reindent=True, keyword_case='upper',
            indent_width=4, use_space_around_operators=True
        )
        main_lines = _format_sql_lines(main_formatted.split('\n'))
        result_lines.extend(main_lines)

    return '\n'.join(result_lines)


def _apply_sophisticated_formatting(sql_text: str) -> str:
    """
    Apply sophisticated formatting with full alignment:
    - Keywords aligned (SELECT, FROM, WHERE, JOIN, etc.)
    - AS keywords aligned in SELECT
    - Table aliases aligned in FROM/JOIN
    - Operators (=) aligned in ON and WHERE conditions
    - ASC/DESC aligned in ORDER BY
    - Subqueries in JOINs formatted inline with hierarchical indentation
    """
    lines = sql_text.split('\n')
    return '\n'.join(_format_sql_lines(lines))


def _format_sql_lines(lines: list) -> list:
    """
    Core formatting logic. Returns list of formatted lines.
    Can be called recursively for subqueries with hierarchical indentation.
    """
    sections = _parse_sql_sections(lines, MAIN_KEYWORDS)

    # Calculate max lengths for alignment
    select_sections = [s for s in sections if s['type'] == 'SELECT']
    from_join_sections = [s for s in sections if s['type'] in
                         JOIN_TYPES]

    # Max field length for SELECT AS alignment
    max_field_len = 0
    for section in select_sections:
        for col_info in section.get('parsed_columns', []):
            max_field_len = max(max_field_len, len(col_info['field']))

    # Max table name length for alias alignment (exclude subqueries)
    max_table_len = 0
    for section in from_join_sections:
        if section.get('table_name') and not section.get('is_subquery'):
            max_table_len = max(max_table_len, len(section['table_name']))

    # Max alias length (for global ON/AND alignment across all JOINs)
    max_alias_len = 0
    for section in from_join_sections:
        alias = section.get('table_alias') or ''
        max_alias_len = max(max_alias_len, len(alias))

    # Global max left-hand side in ON conditions (for operator alignment across JOINs)
    global_max_on_left = 0
    for section in from_join_sections:
        global_max_on_left = max(global_max_on_left, section.get('max_on_left_len', 0))

    # Format each section
    # When INSERT INTO is present, indent all subsequent sections by 4 spaces
    result = []
    insert_indent = ""
    for section in sections:
        lines_before = len(result)

        if section['type'] == '_PREAMBLE':
            _format_preamble_section(result, section)
        elif section['type'] == 'WITH':
            _format_with_section(result, section, MAX_KEYWORD_LEN)
        elif section['type'] == 'SELECT':
            _format_select_section(result, section, MAX_KEYWORD_LEN, max_field_len)
        elif section['type'] in ('INSERT INTO', 'INSERT'):
            _format_insert_section(result, section, MAX_KEYWORD_LEN)
            insert_indent = "    "
        elif section['type'] in JOIN_TYPES:
            _format_from_join_section(result, section, MAX_KEYWORD_LEN, max_table_len,
                                      max_alias_len, global_max_on_left)
        elif section['type'] in ('GROUP BY', 'ORDER BY'):
            _format_group_order_section(result, section, MAX_KEYWORD_LEN)
        elif section['type'] == 'WHERE':
            _format_where_section(result, section, MAX_KEYWORD_LEN)
        elif section['type'] == 'SET':
            _format_set_section(result, section, MAX_KEYWORD_LEN)
        else:
            _format_simple_section(result, section, MAX_KEYWORD_LEN)

        # Indent lines added after INSERT INTO section
        if insert_indent and section['type'] not in ('INSERT INTO', 'INSERT'):
            for i in range(lines_before, len(result)):
                result[i] = insert_indent + result[i]

    return result


def _count_paren_delta(text: str) -> int:
    """Count net parenthesis depth change, ignoring parens inside string literals."""
    depth = 0
    in_single = False
    for ch in text:
        if ch == "'" and not in_single:
            in_single = True
        elif ch == "'" and in_single:
            in_single = False
        elif not in_single:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
    return depth


def _parse_sql_sections(lines: list, main_keywords: list) -> list:
    """Parse SQL lines into sections with pre-parsing.
    Tracks parenthesis depth so keywords inside () don't start new sections."""
    sections = []
    current_section = None
    paren_depth = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Only check for keywords at paren depth 0
        keyword_found = None
        if paren_depth == 0:
            for keyword in sorted(main_keywords, key=len, reverse=True):
                if stripped.upper().startswith(keyword + ' ') or stripped.upper() == keyword:
                    keyword_found = keyword
                    break

        if keyword_found:
            if current_section:
                sections.append(current_section)

            rest = stripped[len(keyword_found):].strip()
            current_section = {
                'type': keyword_found,
                'keyword': keyword_found,
                'content': [rest] if rest else []
            }
            paren_depth += _count_paren_delta(rest)
        elif current_section:
            current_section['content'].append(stripped)
            paren_depth += _count_paren_delta(stripped)
        else:
            # Lines before any keyword match – preserve as preamble
            if not sections or sections[-1]['type'] != '_PREAMBLE':
                sections.append({
                    'type': '_PREAMBLE',
                    'keyword': '',
                    'content': [],
                })
            sections[-1]['content'].append(stripped)
            paren_depth += _count_paren_delta(stripped)

    if current_section:
        sections.append(current_section)

    # Pre-parse sections
    for section in sections:
        if section['type'] == 'SELECT':
            _preparse_select_section(section)
        elif section['type'] in JOIN_TYPES:
            _preparse_from_join_section(section)

    return sections


def _split_by_comma_respecting_parens(text: str) -> list:
    """Split text by commas at top level only (not inside parentheses or strings)."""
    parts = []
    current: list[str] = []
    depth = 0
    in_single = False

    for ch in text:
        if ch == "'" and not in_single:
            in_single = True
            current.append(ch)
        elif ch == "'" and in_single:
            in_single = False
            current.append(ch)
        elif not in_single:
            if ch == '(':
                depth += 1
                current.append(ch)
            elif ch == ')':
                depth -= 1
                current.append(ch)
            elif ch == ',' and depth == 0:
                parts.append(''.join(current))
                current = []
            else:
                current.append(ch)
        else:
            current.append(ch)

    if current:
        parts.append(''.join(current))

    return parts


def _find_top_level_as(text: str):
    """Find the last AS keyword at paren depth 0. Returns (start, end) or None."""
    upper = text.upper()
    depth = 0
    in_single = False
    result = None

    for i, ch in enumerate(text):
        if ch == "'" and not in_single:
            in_single = True
        elif ch == "'" and in_single:
            in_single = False
        elif not in_single:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif (depth == 0 and upper[i:i + 2] == 'AS'
                  and (i == 0 or not (upper[i - 1].isalnum() or upper[i - 1] == '_'))
                  and (i + 2 >= len(text) or not (upper[i + 2].isalnum() or upper[i + 2] == '_'))):
                result = (i, i + 2)

    return result


def _find_top_level_equals(text: str) -> int | None:
    """Find position of first '=' at paren depth 0, ignoring >=, <=, !=, <>.
    Returns index of '=' or None."""
    depth = 0
    in_single = False
    length = len(text)
    i = 0
    while i < length:
        ch = text[i]
        if ch == "'" and not in_single:
            in_single = True
        elif ch == "'" and in_single:
            in_single = False
        elif not in_single:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif depth == 0 and ch == '=':
                # Skip compound operators: >=, <=, !=
                if i > 0 and text[i - 1] in ('>', '<', '!'):
                    pass
                # Skip <> (already handled since < is not =)
                elif i + 1 < length and text[i + 1] in ('>', '<'):
                    pass
                else:
                    return i
        i += 1
    return None


def _extract_paren_content(text: str, open_pos: int) -> str | None:
    """Extract content between '(' at open_pos and its matching ')'.
    Returns the content (without outer parens) or None if unmatched."""
    if open_pos >= len(text) or text[open_pos] != '(':
        return None
    depth = 0
    in_single = False
    for i in range(open_pos, len(text)):
        ch = text[i]
        if ch == "'" and not in_single:
            in_single = True
        elif ch == "'" and in_single:
            in_single = False
        elif not in_single:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return text[open_pos + 1:i]
    return None


def _split_case_clauses(text: str) -> list[str]:
    """Split CASE body into WHEN/ELSE clauses respecting parens and strings.
    Input: text between CASE and END (exclusive).
    Returns list of clause strings like ['WHEN ... THEN ...', 'ELSE ...']."""
    clauses = []
    upper = text.upper()
    depth = 0
    in_single = False
    current_start = 0
    i = 0
    length = len(text)

    # Skip leading whitespace to find first WHEN
    while current_start < length and text[current_start] in (' ', '\t', '\n', '\r'):
        current_start += 1
    i = current_start

    while i < length:
        ch = text[i]
        if ch == "'" and not in_single:
            in_single = True
        elif ch == "'" and in_single:
            in_single = False
        elif not in_single:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif depth == 0:
                # Check for WHEN or ELSE keyword boundary
                for kw in ('WHEN', 'ELSE'):
                    kw_len = len(kw)
                    if upper[i:i + kw_len] == kw:
                        before_ok = (i == 0 or not (upper[i - 1].isalnum() or upper[i - 1] == '_'))
                        after_ok = (i + kw_len >= length or not (upper[i + kw_len].isalnum() or upper[i + kw_len] == '_'))
                        if before_ok and after_ok and i > current_start:
                            clause = text[current_start:i].strip()
                            if clause:
                                clauses.append(clause)
                            current_start = i
                            break
        i += 1

    # Last clause
    remaining = text[current_start:].strip()
    if remaining:
        clauses.append(remaining)
    return clauses


def _preparse_select_section(section: dict):
    """Pre-parse SELECT section to extract columns, AS aliases, and inline comments."""
    # Join all content to handle expressions spanning multiple lines (e.g. COALESCE)
    full_content = ' '.join(section['content'])

    # Split by top-level commas (respects parentheses and string literals)
    parts = _split_by_comma_respecting_parens(full_content)

    parsed_columns = []
    for part in parts:
        clean = part.strip()
        if not clean:
            continue

        # Extract inline comment (-- ...)
        comment_idx = clean.find('--')
        if comment_idx >= 0:
            comment = clean[comment_idx:].strip()
            clean = clean[:comment_idx].strip()
        else:
            comment = None

        if not clean:
            continue

        # Find AS keyword at top level (not inside CAST/COALESCE parens)
        as_pos = _find_top_level_as(clean)
        if as_pos:
            # Check there's whitespace before and after AS
            start, end = as_pos
            before_ok = start > 0 and clean[start - 1] in (' ', '\t')
            after_ok = end < len(clean) and clean[end] in (' ', '\t')
            if before_ok and after_ok:
                field = clean[:start].strip()
                alias = clean[end:].strip()
                col_info = {'field': field, 'alias': alias, 'has_as': True}
            else:
                col_info = {'field': clean, 'alias': None, 'has_as': False}
        else:
            col_info = {'field': clean, 'alias': None, 'has_as': False}

        col_info['comment'] = comment
        parsed_columns.append(col_info)

    section['parsed_columns'] = parsed_columns


def _preparse_from_join_section(section: dict):
    """Pre-parse FROM/JOIN section to extract table, alias, and ON conditions.
    Detects subquery table sources (content starting with '(')."""
    all_content = ' '.join(section['content'])
    content_stripped = all_content.strip()

    # Detect subquery table: content starts with "("
    if content_stripped.startswith('('):
        _preparse_subquery_join(section, content_stripped)
        return

    # Parse ON condition
    on_match = re.search(r'\s+ON\s+', all_content, re.IGNORECASE)
    if on_match:
        table_part = all_content[:on_match.start()].strip()
        on_part = all_content[on_match.end():].strip()
    else:
        table_part = all_content
        on_part = None

    # Split table and alias
    table_parts = table_part.split()
    if len(table_parts) >= 2:
        table_name = table_parts[0]
        table_alias = ' '.join(table_parts[1:])
    elif len(table_parts) == 1:
        table_name = table_parts[0]
        table_alias = None
    else:
        table_name = table_part
        table_alias = None

    section['table_name'] = table_name
    section['table_alias'] = table_alias
    section['on_condition'] = on_part
    section['is_subquery'] = False

    _parse_on_conditions(section, on_part)


def _preparse_subquery_join(section: dict, content: str):
    """Pre-parse a JOIN with a subquery table source: (SELECT ... ) alias ON ..."""
    # Find matching closing paren
    depth = 0
    subquery_end = -1
    in_single = False
    for i, ch in enumerate(content):
        if ch == "'" and not in_single:
            in_single = True
        elif ch == "'" and in_single:
            in_single = False
        elif not in_single:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    subquery_end = i
                    break

    if subquery_end < 0:
        # Malformed - treat as regular table
        section['table_name'] = content
        section['table_alias'] = None
        section['on_condition'] = None
        section['is_subquery'] = False
        section['parsed_on_conditions'] = []
        section['max_on_left_len'] = 0
        return

    subquery_sql = content[1:subquery_end].strip()
    after_subquery = content[subquery_end + 1:].strip()

    # Parse alias and ON from after_subquery
    on_match = re.search(r'\bON\b', after_subquery, re.IGNORECASE)
    if on_match:
        alias_part = after_subquery[:on_match.start()].strip()
        on_part = after_subquery[on_match.end():].strip()
    else:
        alias_part = after_subquery
        on_part = None

    section['is_subquery'] = True
    section['subquery_sql'] = subquery_sql
    section['table_name'] = None  # No regular table name for subqueries
    section['table_alias'] = alias_part if alias_part else None
    section['on_condition'] = on_part

    _parse_on_conditions(section, on_part)


def _parse_on_conditions(section: dict, on_part: str):
    """Parse ON conditions (split by AND) and compute max left-hand side length."""
    if on_part:
        and_conditions = re.split(r'\s+AND\s+', on_part, flags=re.IGNORECASE)
        parsed_conditions = []
        max_left_len = 0

        for cond in and_conditions:
            cond = cond.strip()
            op_match = re.search(r'\s*(>=|<=|!=|<>|=|<|>|IN|NOT IN|LIKE|NOT LIKE|IS NOT|IS)\s+',
                                cond, re.IGNORECASE)
            if op_match:
                left = cond[:op_match.start()].strip()
                operator = op_match.group(1).strip().upper()
                right = cond[op_match.end():].strip()
                parsed_conditions.append({
                    'left': left, 'operator': operator, 'right': right, 'has_operator': True
                })
                max_left_len = max(max_left_len, len(left))
            else:
                parsed_conditions.append({'full': cond, 'has_operator': False})

        section['parsed_on_conditions'] = parsed_conditions
        section['max_on_left_len'] = max_left_len
    else:
        section['parsed_on_conditions'] = []
        section['max_on_left_len'] = 0


def _format_preamble_section(result: list, section: dict):
    """Output preamble lines (e.g., CREATE VIEW ... AS) as-is."""
    for line in section['content']:
        result.append(line)


def _parse_cte_definitions(content_lines: list) -> list:
    """Parse CTE definitions from WITH section content.

    Returns list of dicts: {'name': str, 'body': str}
    """
    full = '\n'.join(content_lines)
    ctes = []
    i = 0
    length = len(full)

    while i < length:
        # Skip whitespace and commas
        while i < length and full[i] in (' ', '\t', '\n', '\r', ','):
            i += 1
        if i >= length:
            break

        # Find AS ( pattern for CTE definition
        as_match = re.search(r'\bAS\s*\(', full[i:], re.IGNORECASE)
        if not as_match:
            break

        cte_name = full[i:i + as_match.start()].strip()
        paren_pos = i + as_match.end() - 1  # position of '('

        # Find matching closing paren
        depth = 0
        body_start = paren_pos + 1
        close_pos = -1
        in_single = False
        for j in range(paren_pos, length):
            ch = full[j]
            if ch == "'" and not in_single:
                in_single = True
            elif ch == "'" and in_single:
                in_single = False
            elif not in_single:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        close_pos = j
                        break

        if close_pos < 0:
            body = full[body_start:].strip()
            ctes.append({'name': cte_name, 'body': body})
            break

        body = full[body_start:close_pos].strip()
        ctes.append({'name': cte_name, 'body': body})
        i = close_pos + 1

    return ctes


def _format_with_section(result: list, section: dict, max_keyword_len: int):
    """Format WITH (CTE) section with comma-first CTE names and indented bodies."""
    ctes = _parse_cte_definitions(section['content'])

    if not ctes:
        _format_simple_section(result, section, max_keyword_len)
        return

    cte_indent = "    "  # 4-space indent for CTE body lines

    for i, cte in enumerate(ctes):
        # CTE header line
        if i == 0:
            result.append(f"WITH {cte['name']} AS (")
        else:
            result.append(f", {cte['name']} AS (")

        # Format CTE body recursively through the full pipeline
        body_formatted = sqlparse.format(
            cte['body'], reindent=True, keyword_case='upper',
            indent_width=4, use_space_around_operators=True
        )
        body_lines = _format_sql_lines(body_formatted.split('\n'))

        for bl in body_lines:
            result.append(cte_indent + bl)

        # Close paren on its own line
        result.append(")")


def _format_select_section(result: list, section: dict, max_keyword_len: int, max_field_len: int):
    """Format SELECT section: columns aligned at keyword width, with comment alignment."""
    keyword_pad = "SELECT".ljust(max_keyword_len)
    col_indent = ' ' * (max_keyword_len - 1)  # align ", " so column names match

    columns = section.get('parsed_columns', [])
    has_comments = any(col.get('comment') for col in columns)

    # Build display texts for each column
    display_texts = []
    for col_info in columns:
        if col_info['has_as']:
            field_padded = col_info['field'].ljust(max_field_len)
            display_texts.append(f"{field_padded} AS {col_info['alias']}")
        else:
            display_texts.append(col_info['field'])

    # Compute max display length for comment alignment
    max_display_len = max((len(d) for d in display_texts), default=0) if has_comments else 0

    for i, (col_info, display) in enumerate(zip(columns, display_texts)):
        if has_comments and col_info.get('comment'):
            col_text = f"{display.ljust(max_display_len)}    {col_info['comment']}"
        else:
            col_text = display

        if i == 0:
            result.append(f"{keyword_pad} {col_text}")
        else:
            result.append(f"{col_indent}, {col_text}")


def _format_insert_section(result: list, section: dict, max_keyword_len: int):
    """Format INSERT INTO section with columns one per line, comma-first."""
    content = ' '.join(section['content'])
    keyword = section['keyword']

    # Check for parenthesized column list
    paren_start = content.find('(')
    if paren_start == -1:
        # No column list (e.g., INSERT INTO table SELECT ...)
        result.append(f"{keyword} {content}")
        return

    table_name = content[:paren_start].strip()
    paren_end = content.rfind(')')
    if paren_end == -1:
        result.append(f"{keyword} {content}")
        return

    columns_str = content[paren_start + 1:paren_end].strip()
    after_paren = content[paren_end + 1:].strip()

    columns = [c.strip() for c in columns_str.split(',') if c.strip()]

    if not columns:
        result.append(f"{keyword} {content}")
        return

    # Parse columns and inline comments (-- ...)
    parsed_cols = []
    has_comments = False
    for col in columns:
        comment_idx = col.find('--')
        if comment_idx >= 0:
            col_name = col[:comment_idx].strip()
            comment = col[comment_idx:]
            has_comments = True
        else:
            col_name = col.strip()
            comment = None
        parsed_cols.append({'name': col_name, 'comment': comment})

    # Build display text (name + closing paren for last column)
    display_cols = []
    for i, pc in enumerate(parsed_cols):
        display_cols.append(pc['name'] + (')' if i == len(parsed_cols) - 1 else ''))
    max_display_len = max(len(d) for d in display_cols)

    # Columns aligned on "(" position: ", " aligns with "( "
    header = f"{keyword} {table_name} ("
    paren_pos = len(header) - 1  # position of "("
    col_indent = ' ' * paren_pos  # align ", " under "( "

    for i, (dc, pc) in enumerate(zip(display_cols, parsed_cols)):
        if has_comments and pc['comment']:
            col_text = f"{dc.ljust(max_display_len)}    {pc['comment']}"
        else:
            col_text = dc

        if i == 0:
            result.append(f"{header} {col_text}")  # "INSERT INTO table ( col1"
        else:
            result.append(f"{col_indent}, {col_text}")  # align ", " under "( "

    if after_paren:
        result.append(after_paren)


def _format_from_join_section(result: list, section: dict, max_keyword_len: int, max_table_len: int,
                              max_alias_len: int, global_max_on_left: int):
    """Format FROM/JOIN section with globally aligned aliases, ON and AND conditions.
    Handles subquery table sources with recursive inline formatting."""
    keyword = section['keyword']
    table_alias = section.get('table_alias', '')
    parsed_conditions = section.get('parsed_on_conditions', [])

    # Handle subquery table source
    if section.get('is_subquery'):
        _format_subquery_join(result, section, max_keyword_len, max_table_len,
                              max_alias_len, global_max_on_left)
        return

    table_name = section.get('table_name', '')

    # Build base line with padded keyword, table, and alias
    base = f"{keyword.ljust(max_keyword_len)} {table_name.ljust(max_table_len)}"
    if max_alias_len > 0:
        alias_str = (table_alias or '').ljust(max_alias_len)
        base += f" {alias_str}"
    elif table_alias:
        base += f" {table_alias}"

    # Add ON conditions (globally aligned)
    if parsed_conditions:
        equals_position = global_max_on_left + 1
        on_pos = len(base) + 1  # position where ON/AND start

        first_cond = parsed_conditions[0]
        if first_cond.get('has_operator'):
            left = first_cond['left']
            operator = first_cond['operator']
            padding = _calc_operator_padding(left, operator, equals_position)
            result.append(f"{base} ON  {left}{' ' * padding}{operator} {first_cond['right']}")
        else:
            result.append(f"{base} ON  {first_cond['full']}")

        # AND conditions aligned under ON
        and_indent = ' ' * on_pos
        for cond_info in parsed_conditions[1:]:
            if cond_info.get('has_operator'):
                left = cond_info['left']
                operator = cond_info['operator']
                padding = _calc_operator_padding(left, operator, equals_position)
                result.append(f"{and_indent}AND {left}{' ' * padding}{operator} {cond_info['right']}")
            else:
                result.append(f"{and_indent}AND {cond_info['full']}")
    else:
        result.append(base.rstrip())


def _format_subquery_join(result: list, section: dict, max_keyword_len: int, max_table_len: int,
                          max_alias_len: int, global_max_on_left: int):
    """Format a JOIN with a subquery table source, e.g.:
    LEFT JOIN        (SELECT           col1
                      FROM             subtable)    alias ON  cond = val
    """
    keyword = section['keyword']
    subquery_sql = section['subquery_sql']
    table_alias = section.get('table_alias', '')
    parsed_conditions = section.get('parsed_on_conditions', [])

    # Pre-process subquery through sqlparse to get proper line breaks
    subquery_formatted = sqlparse.format(
        subquery_sql, reindent=True, keyword_case='upper',
        indent_width=4, use_space_around_operators=True
    )

    # Format subquery recursively using the same formatting pipeline
    subquery_lines = _format_sql_lines(subquery_formatted.split('\n'))

    # Build prefix: "LEFT JOIN        ("
    keyword_padded = keyword.ljust(max_keyword_len)
    paren_prefix = f"{keyword_padded} ("
    cont_indent = ' ' * len(paren_prefix)

    if not subquery_lines:
        result.append(f"{paren_prefix})")
    elif len(subquery_lines) == 1:
        # Single-line subquery
        result.append(f"{paren_prefix}{subquery_lines[0]})")
    else:
        # Multi-line subquery: first line on same line as "("
        result.append(f"{paren_prefix}{subquery_lines[0]}")
        # Continuation lines indented to align under first char after "("
        for sq_line in subquery_lines[1:]:
            result.append(f"{cont_indent}{sq_line}")
        # Close paren on last line
        result[-1] += ')'

    # Add alias + ON conditions after ")"
    if table_alias or parsed_conditions:
        # Compute target alias position (same as regular JOINs)
        target_pos = max_keyword_len + 1 + max_table_len + 1
        cur_len = len(result[-1])
        pad = max(4, target_pos - cur_len)

        if table_alias:
            if max_alias_len > 0:
                alias_str = table_alias.ljust(max_alias_len)
            else:
                alias_str = table_alias
            result[-1] += ' ' * pad + alias_str

        if parsed_conditions:
            equals_position = global_max_on_left + 1
            base_len = len(result[-1]) + 1  # position for AND alignment

            first_cond = parsed_conditions[0]
            if first_cond.get('has_operator'):
                left = first_cond['left']
                operator = first_cond['operator']
                padding = _calc_operator_padding(left, operator, equals_position)
                result[-1] += f" ON  {left}{' ' * padding}{operator} {first_cond['right']}"
            else:
                result[-1] += f" ON  {first_cond['full']}"

            # AND conditions aligned under ON
            and_indent = ' ' * base_len
            for cond_info in parsed_conditions[1:]:
                if cond_info.get('has_operator'):
                    left = cond_info['left']
                    operator = cond_info['operator']
                    padding = _calc_operator_padding(left, operator, equals_position)
                    result.append(f"{and_indent}AND {left}{' ' * padding}{operator} {cond_info['right']}")
                else:
                    result.append(f"{and_indent}AND {cond_info['full']}")


def _format_group_order_section(result: list, section: dict, max_keyword_len: int):
    """Format GROUP BY / ORDER BY: columns aligned at keyword width."""
    all_content = ' '.join(section['content'])
    columns = [c.strip() for c in all_content.split(',') if c.strip()]

    if not columns:
        return

    keyword = section['keyword']
    keyword_pad = keyword.ljust(max_keyword_len)
    col_indent = ' ' * (max_keyword_len - 1)

    if keyword == 'ORDER BY':
        # Parse and align ASC/DESC
        parsed_columns = []
        max_col_len = 0

        for col in columns:
            dir_match = re.search(r'\s+(ASC|DESC)\s*$', col, re.IGNORECASE)
            if dir_match:
                col_name = col[:dir_match.start()].strip()
                direction = dir_match.group(1).upper()
                parsed_columns.append({'col': col_name, 'direction': direction})
                max_col_len = max(max_col_len, len(col_name))
            else:
                parsed_columns.append({'col': col, 'direction': None})
                max_col_len = max(max_col_len, len(col))

        for i, col_info in enumerate(parsed_columns):
            if col_info['direction']:
                col_padded = col_info['col'].ljust(max_col_len)
                col_text = f"{col_padded} {col_info['direction']}"
            else:
                col_text = col_info['col']

            if i == 0:
                result.append(f"{keyword_pad} {col_text}")
            else:
                result.append(f"{col_indent}, {col_text}")
    else:
        # GROUP BY - no direction
        for i, col in enumerate(columns):
            if i == 0:
                result.append(f"{keyword_pad} {col}")
            else:
                result.append(f"{col_indent}, {col}")


def _format_where_section(result: list, section: dict, max_keyword_len: int):
    """Format WHERE section with aligned operators."""
    content = ' '.join(section['content'])
    and_conditions = re.split(r'\s+AND\s+', content, flags=re.IGNORECASE)

    if len(and_conditions) == 1:
        result.append(f"{section['keyword'].ljust(max_keyword_len)} {content}")
    else:
        parsed_conditions = []
        max_left_len = 0

        for cond in and_conditions:
            cond = cond.strip()
            op_match = re.search(r'\s*(>=|<=|!=|<>|=|<|>|IN|NOT IN|LIKE|NOT LIKE|IS NOT|IS)\s+',
                                cond, re.IGNORECASE)
            if op_match:
                left = cond[:op_match.start()].strip()
                operator = op_match.group(1).strip().upper()
                right = cond[op_match.end():].strip()
                parsed_conditions.append({
                    'left': left, 'operator': operator, 'right': right, 'has_operator': True
                })
                max_left_len = max(max_left_len, len(left))
            else:
                parsed_conditions.append({'full': cond, 'has_operator': False})

        equals_position = max_left_len + 1

        first_cond = parsed_conditions[0]
        if first_cond.get('has_operator'):
            left = first_cond['left']
            operator = first_cond['operator']
            padding = _calc_operator_padding(left, operator, equals_position)
            result.append(f"WHERE      {left}{' ' * padding}{operator} {first_cond['right']}")
        else:
            result.append(f"WHERE      {first_cond['full']}")

        for cond_info in parsed_conditions[1:]:
            if cond_info.get('has_operator'):
                left = cond_info['left']
                operator = cond_info['operator']
                padding = _calc_operator_padding(left, operator, equals_position)
                result.append(f"AND        {left}{' ' * padding}{operator} {cond_info['right']}")
            else:
                result.append(f"AND        {cond_info['full']}")


def _format_function_args_multiline(func_text: str, base_indent: int, line_limit: int = 80) -> list[str]:
    """Format a function call (e.g. COALESCE(...)) with multiline args if needed.

    Returns list of lines. If it fits on one line, returns [func_text].
    Otherwise expands arguments with leading commas aligned after '('.
    """
    # Find function name and opening paren
    paren_pos = func_text.find('(')
    if paren_pos < 0:
        return [func_text]

    func_name = func_text[:paren_pos].strip()
    inner = _extract_paren_content(func_text, paren_pos)
    if inner is None:
        return [func_text]

    # Check if it fits on one line
    one_line = f"{func_name}({inner})"
    if base_indent + len(one_line) <= line_limit:
        return [one_line]

    # Expand arguments multiline with leading commas
    args = _split_by_comma_respecting_parens(inner)
    args = [a.strip() for a in args if a.strip()]
    if not args:
        return [func_text]

    # Format: COALESCE( arg1
    #                 , arg2
    #                 , arg3)
    # "COALESCE( " = name + "( ", first arg at pos len(name)+2
    # ", " must start at pos len(name) so arg after ", " is at pos len(name)+2
    header = f"{func_name}( "
    cont_indent = ' ' * len(func_name)  # align ", " so args match "( " position
    lines = [f"{header}{args[0]}"]
    for arg in args[1:]:
        lines.append(f"{cont_indent}, {arg}")
    # Close paren on last arg
    lines[-1] += ')'
    return lines


def _format_case_expression(case_text: str, base_indent: int) -> list[str]:
    """Format a CASE expression with aligned WHEN/THEN/ELSE/END.

    case_text: full text starting with CASE and ending with END.
    base_indent: column position where CASE starts.
    Returns list of lines (without base_indent prefix - caller adds that).
    """
    upper = case_text.upper().strip()
    text = case_text.strip()

    # Find CASE keyword
    if not upper.startswith('CASE'):
        return [text]

    # Find END keyword (last occurrence at top level)
    end_pos = None
    depth = 0
    in_single = False
    for i in range(len(text)):
        ch = text[i]
        if ch == "'" and not in_single:
            in_single = True
        elif ch == "'" and in_single:
            in_single = False
        elif not in_single:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif depth == 0 and upper[i:i + 3] == 'END':
                before_ok = (i == 0 or not (upper[i - 1].isalnum() or upper[i - 1] == '_'))
                after_ok = (i + 3 >= len(text) or not (upper[i + 3].isalnum() or upper[i + 3] == '_'))
                if before_ok and after_ok:
                    end_pos = i

    if end_pos is None:
        return [text]

    # Extract body between CASE and END
    case_body = text[4:end_pos].strip()  # skip "CASE"

    # Split into clauses
    clauses = _split_case_clauses(case_body)
    if not clauses:
        return [text]

    # Parse each clause into (type, condition, result)
    parsed = []
    for clause in clauses:
        clause_upper = clause.upper().strip()
        if clause_upper.startswith('WHEN'):
            # Find THEN at top level
            then_pos = None
            c_depth = 0
            c_single = False
            c_upper = clause.upper()
            for i in range(len(clause)):
                ch = clause[i]
                if ch == "'" and not c_single:
                    c_single = True
                elif ch == "'" and c_single:
                    c_single = False
                elif not c_single:
                    if ch == '(':
                        c_depth += 1
                    elif ch == ')':
                        c_depth -= 1
                    elif c_depth == 0 and c_upper[i:i + 4] == 'THEN':
                        before_ok = (i == 0 or not (c_upper[i - 1].isalnum() or c_upper[i - 1] == '_'))
                        after_ok = (i + 4 >= len(clause) or not (c_upper[i + 4].isalnum() or c_upper[i + 4] == '_'))
                        if before_ok and after_ok:
                            then_pos = i
                            break
            if then_pos is not None:
                condition = clause[4:then_pos].strip()  # skip "WHEN"
                then_value = clause[then_pos + 4:].strip()  # skip "THEN"
                parsed.append({'type': 'WHEN', 'condition': condition, 'result': then_value})
            else:
                parsed.append({'type': 'WHEN', 'condition': clause[4:].strip(), 'result': ''})
        elif clause_upper.startswith('ELSE'):
            parsed.append({'type': 'ELSE', 'result': clause[4:].strip()})

    if not parsed:
        return [text]

    # Parse each WHEN condition into left / operator / right for operator alignment
    for p in parsed:
        if p['type'] != 'WHEN':
            continue
        cond = p['condition']
        matched = False
        # Check IS NOT NULL / IS NULL first (no right-hand side)
        for op_pat in [r'\bIS\s+NOT\s+NULL\b', r'\bIS\s+NULL\b']:
            m = re.search(op_pat, cond, re.IGNORECASE)
            if m:
                p['cond_left'] = cond[:m.start()].strip()
                p['cond_op'] = re.sub(r'\s+', ' ', m.group(0)).upper()
                p['cond_right'] = cond[m.end():].strip()
                matched = True
                break
        if not matched:
            # General operators
            m = re.search(
                r'\s*(>=|<=|!=|<>|=|<|>|NOT\s+IN|IN|NOT\s+LIKE|LIKE|IS\s+NOT|IS)\s+',
                cond, re.IGNORECASE)
            if m:
                p['cond_left'] = cond[:m.start()].strip()
                p['cond_op'] = re.sub(r'\s+', ' ', m.group(1)).strip().upper()
                p['cond_right'] = cond[m.end():].strip()
            else:
                p['cond_left'] = cond
                p['cond_op'] = None
                p['cond_right'] = None

    # Max left-hand side length (for operator alignment)
    max_left_len = 0
    for p in parsed:
        if p['type'] == 'WHEN' and p.get('cond_op'):
            max_left_len = max(max_left_len, len(p['cond_left']))

    # Build aligned conditions and compute max for THEN alignment
    max_cond_len = 0
    for p in parsed:
        if p['type'] != 'WHEN':
            continue
        if p.get('cond_op'):
            left_padded = p['cond_left'].ljust(max_left_len)
            if p['cond_right']:
                aligned = f"{left_padded} {p['cond_op']} {p['cond_right']}"
            else:
                aligned = f"{left_padded} {p['cond_op']}"
        else:
            aligned = p['condition']
        p['aligned_condition'] = aligned
        max_cond_len = max(max_cond_len, len(aligned))

    # Build lines
    # CASE on first line, WHEN indented by 2 from CASE position
    when_indent = '  '  # relative to CASE
    lines = ['CASE']

    for p in parsed:
        if p['type'] == 'WHEN':
            cond_padded = p['aligned_condition'].ljust(max_cond_len)
            lines.append(f"{when_indent}WHEN {cond_padded} THEN {p['result']}")
        elif p['type'] == 'ELSE':
            lines.append(f"{when_indent}ELSE {p['result']}")

    lines.append('END')
    return lines


def _format_set_value(value: str, indent_pos: int) -> list[str]:
    """Format a SET assignment value. Dispatches to CASE or function formatter.

    value: the right-hand side of col = value
    indent_pos: column position where the value starts
    Returns list of lines (first line is the value itself, continuation lines are indented).
    """
    stripped = value.strip()
    upper = stripped.upper()

    # Detect CASE expression
    if upper.startswith('CASE'):
        case_lines = _format_case_expression(stripped, indent_pos)
        return case_lines

    # Detect function call (COALESCE, ISNULL, etc.)
    paren_pos = stripped.find('(')
    if paren_pos > 0 and stripped[:paren_pos].strip().isidentifier():
        func_lines = _format_function_args_multiline(stripped, indent_pos)
        return func_lines

    return [stripped]


def _format_set_section(result: list, section: dict, max_keyword_len: int):
    """Format SET section with leading commas and CASE/COALESCE support."""
    content = ' '.join(section['content'])
    assignments = _split_by_comma_respecting_parens(content)
    assignments = [a.strip() for a in assignments if a.strip()]

    if not assignments:
        return

    keyword_pad = "SET".ljust(max_keyword_len)
    col_indent = ' ' * (max_keyword_len - 1)  # for leading comma alignment

    for i, assignment in enumerate(assignments):
        eq_pos = _find_top_level_equals(assignment)
        if eq_pos is not None:
            col_name = assignment[:eq_pos].strip()
            raw_value = assignment[eq_pos + 1:].strip()

            # Compute position where value starts on the line
            if i == 0:
                prefix = f"{keyword_pad} {col_name} = "
            else:
                prefix = f"{col_indent}, {col_name} = "

            value_lines = _format_set_value(raw_value, len(prefix))

            if len(value_lines) == 1:
                result.append(f"{prefix}{value_lines[0]}")
            else:
                # First value line on same line as col =
                result.append(f"{prefix}{value_lines[0]}")
                # Continuation lines indented to align under value start
                val_indent = ' ' * len(prefix)
                for vl in value_lines[1:]:
                    result.append(f"{val_indent}{vl}")
        else:
            # No = found, output as-is
            if i == 0:
                result.append(f"{keyword_pad} {assignment}")
            else:
                result.append(f"{col_indent}, {assignment}")


def _format_simple_section(result: list, section: dict, max_keyword_len: int):
    """Format simple sections (HAVING, LIMIT, etc.)."""
    content = ' '.join(section['content'])
    if content:
        result.append(f"{section['keyword'].ljust(max_keyword_len)} {content}")
    else:
        result.append(section['keyword'].ljust(max_keyword_len))


def _calc_operator_padding(left_field: str, operator: str, equals_position: int) -> int:
    """Calculate padding to align operators (= signs)."""
    if operator == '=':
        padding = equals_position - len(left_field)
    elif '=' in operator and len(operator) >= 2 and operator[1] == '=':
        padding = equals_position - len(left_field) - 1
    else:
        padding = equals_position - len(left_field)
    return max(1, padding)
