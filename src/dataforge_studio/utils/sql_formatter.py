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
    'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN',
    'UNION', 'UNION ALL', 'LIMIT', 'OFFSET',
    'INSERT INTO', 'INSERT', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM', 'DELETE',
    'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE',
    'MERGE INTO', 'MERGE', 'WHEN MATCHED', 'WHEN NOT MATCHED',
    'WITH'
]
MAX_KEYWORD_LEN = max(len(kw) for kw in MAIN_KEYWORDS)


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
        if style == "compact":
            # Compact: multiple columns on same line
            return sqlparse.format(
                sql_text,
                reindent=True,
                keyword_case='upper',
                indent_width=2,
                use_space_around_operators=True,
                wrap_after=120
            )

        elif style == "expanded":
            # Expanded: one column per line
            formatted = sqlparse.format(
                sql_text,
                reindent=True,
                keyword_case='upper',
                indent_width=4,
                use_space_around_operators=True
            )
            return _force_one_column_per_line(formatted)

        elif style == "comma_first":
            # Comma first
            return sqlparse.format(
                sql_text,
                reindent=True,
                keyword_case='upper',
                indent_width=4,
                use_space_around_operators=True,
                comma_first=True
            )

        elif style == "ultimate":
            # Ultimate: sophisticated alignment (keywords, AS, aliases, operators)
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

    except Exception as e:
        logger.error(f"SQL formatting error: {e}")
        raise


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
                         ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN')]

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

        if section['type'] == 'SELECT':
            _format_select_section(result, section, MAX_KEYWORD_LEN, max_field_len)
        elif section['type'] in ('INSERT INTO', 'INSERT'):
            _format_insert_section(result, section, MAX_KEYWORD_LEN)
            insert_indent = "    "
        elif section['type'] in ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN'):
            _format_from_join_section(result, section, MAX_KEYWORD_LEN, max_table_len,
                                      max_alias_len, global_max_on_left)
        elif section['type'] in ('GROUP BY', 'ORDER BY'):
            _format_group_order_section(result, section, MAX_KEYWORD_LEN)
        elif section['type'] == 'WHERE':
            _format_where_section(result, section, MAX_KEYWORD_LEN)
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

    if current_section:
        sections.append(current_section)

    # Pre-parse sections
    for section in sections:
        if section['type'] == 'SELECT':
            _preparse_select_section(section)
        elif section['type'] in ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN'):
            _preparse_from_join_section(section)

    return sections


def _preparse_select_section(section: dict):
    """Pre-parse SELECT section to extract columns, AS aliases, and inline comments."""
    parsed_columns = []

    for line in section['content']:
        # Extract inline comment (-- ...)
        comment_idx = line.find('--')
        if comment_idx >= 0:
            clean = line[:comment_idx].strip()
            comment = line[comment_idx:].strip()
        else:
            clean = line.strip()
            comment = None

        if not clean:
            continue

        # Split by comma (a line may have multiple columns)
        parts = [p.strip() for p in clean.split(',') if p.strip()]

        for j, part in enumerate(parts):
            as_match = re.search(r'\s+AS\s+', part, re.IGNORECASE)
            if as_match:
                field = part[:as_match.start()].strip()
                alias = part[as_match.end():].strip()
                col_info = {'field': field, 'alias': alias, 'has_as': True}
            else:
                col_info = {'field': part, 'alias': None, 'has_as': False}

            # Comment goes to the last column on this line
            col_info['comment'] = comment if (j == len(parts) - 1 and comment) else None
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
