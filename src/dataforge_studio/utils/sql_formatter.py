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
    """
    lines = sql_text.split('\n')

    # Main keywords that should be aligned
    main_keywords = [
        'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY',
        'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN',
        'UNION', 'UNION ALL', 'LIMIT', 'OFFSET'
    ]
    max_keyword_len = max(len(kw) for kw in main_keywords)

    # Parse SQL into sections
    sections = _parse_sql_sections(lines, main_keywords)

    # Calculate max lengths for alignment
    select_sections = [s for s in sections if s['type'] == 'SELECT']
    from_join_sections = [s for s in sections if s['type'] in
                         ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN')]

    # Max field length for SELECT AS alignment
    max_field_len = 0
    for section in select_sections:
        for col_info in section.get('parsed_columns', []):
            max_field_len = max(max_field_len, len(col_info['field']))

    # Max table name length for alias alignment
    max_table_len = 0
    for section in from_join_sections:
        if section.get('table_name'):
            max_table_len = max(max_table_len, len(section['table_name']))

    # Format each section
    result = []
    for section in sections:
        if section['type'] == 'SELECT':
            _format_select_section(result, section, max_keyword_len, max_field_len)
        elif section['type'] in ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN'):
            _format_from_join_section(result, section, max_keyword_len, max_table_len)
        elif section['type'] in ('GROUP BY', 'ORDER BY'):
            _format_group_order_section(result, section, max_keyword_len)
        elif section['type'] == 'WHERE':
            _format_where_section(result, section, max_keyword_len)
        else:
            _format_simple_section(result, section, max_keyword_len)

    return '\n'.join(result)


def _parse_sql_sections(lines: list, main_keywords: list) -> list:
    """Parse SQL lines into sections with pre-parsing."""
    sections = []
    current_section = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if line starts with a main keyword
        keyword_found = None
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
        elif current_section:
            current_section['content'].append(stripped)

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
    """Pre-parse SELECT section to extract columns and AS aliases."""
    all_content = ' '.join(section['content'])
    columns = [c.strip() for c in all_content.split(',') if c.strip()]

    parsed_columns = []
    for col in columns:
        as_match = re.search(r'\s+AS\s+', col, re.IGNORECASE)
        if as_match:
            field = col[:as_match.start()].strip()
            alias = col[as_match.end():].strip()
            parsed_columns.append({'field': field, 'alias': alias, 'has_as': True})
        else:
            parsed_columns.append({'field': col, 'alias': None, 'has_as': False})

    section['parsed_columns'] = parsed_columns


def _preparse_from_join_section(section: dict):
    """Pre-parse FROM/JOIN section to extract table, alias, and ON conditions."""
    all_content = ' '.join(section['content'])

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

    # Parse ON conditions (split by AND)
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
    """Format SELECT section with aligned AS keywords."""
    column_indent = ' ' * (max_keyword_len - 1)

    for i, col_info in enumerate(section.get('parsed_columns', [])):
        if i == 0:
            if col_info['has_as']:
                field_padded = col_info['field'].ljust(max_field_len)
                result.append(f"SELECT     {field_padded} AS {col_info['alias']}")
            else:
                result.append(f"SELECT     {col_info['field']}")
        else:
            if col_info['has_as']:
                field_padded = col_info['field'].ljust(max_field_len)
                result.append(f"{column_indent}, {field_padded} AS {col_info['alias']}")
            else:
                result.append(f"{column_indent}, {col_info['field']}")


def _format_from_join_section(result: list, section: dict, max_keyword_len: int, max_table_len: int):
    """Format FROM/JOIN section with aligned aliases and ON conditions."""
    keyword = section['keyword']
    table_name = section.get('table_name', '')
    table_alias = section.get('table_alias', '')
    parsed_conditions = section.get('parsed_on_conditions', [])
    max_left_len = section.get('max_on_left_len', 0)

    # Build base line
    if table_alias:
        table_padded = table_name.ljust(max_table_len)
        line = f"{keyword.ljust(max_keyword_len)} {table_padded} {table_alias}"
        on_start_pos = max_keyword_len + 1 + max_table_len + 1 + len(table_alias) + 1
    else:
        line = f"{keyword.ljust(max_keyword_len)} {table_name}"
        on_start_pos = max_keyword_len + 1 + len(table_name) + 1

    # Add ON conditions
    if parsed_conditions:
        equals_position = max_left_len + 1

        first_cond = parsed_conditions[0]
        if first_cond.get('has_operator'):
            left = first_cond['left']
            operator = first_cond['operator']
            padding = _calc_operator_padding(left, operator, equals_position)
            line += f" ON  {left}{' ' * padding}{operator} {first_cond['right']}"
        else:
            line += f" ON  {first_cond['full']}"
        result.append(line)

        # Additional AND conditions
        if len(parsed_conditions) > 1:
            and_indent = ' ' * on_start_pos
            for cond_info in parsed_conditions[1:]:
                if cond_info.get('has_operator'):
                    left = cond_info['left']
                    operator = cond_info['operator']
                    padding = _calc_operator_padding(left, operator, equals_position)
                    result.append(f"{and_indent}AND {left}{' ' * padding}{operator} {cond_info['right']}")
                else:
                    result.append(f"{and_indent}AND {cond_info['full']}")
    else:
        result.append(line)


def _format_group_order_section(result: list, section: dict, max_keyword_len: int):
    """Format GROUP BY / ORDER BY with aligned ASC/DESC."""
    all_content = ' '.join(section['content'])
    columns = [c.strip() for c in all_content.split(',') if c.strip()]

    if not columns:
        return

    column_indent = ' ' * (max_keyword_len - 1)
    keyword = section['keyword']

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
            if i == 0:
                if col_info['direction']:
                    col_padded = col_info['col'].ljust(max_col_len)
                    result.append(f"{keyword.ljust(max_keyword_len)} {col_padded} {col_info['direction']}")
                else:
                    result.append(f"{keyword.ljust(max_keyword_len)} {col_info['col']}")
            else:
                if col_info['direction']:
                    col_padded = col_info['col'].ljust(max_col_len)
                    result.append(f"{column_indent}, {col_padded} {col_info['direction']}")
                else:
                    result.append(f"{column_indent}, {col_info['col']}")
    else:
        # GROUP BY - no direction
        for i, col in enumerate(columns):
            if i == 0:
                result.append(f"{keyword.ljust(max_keyword_len)} {col}")
            else:
                result.append(f"{column_indent}, {col}")


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
