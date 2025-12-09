"""
SQL Syntax Highlighter Module
Provides SQL syntax highlighting and formatting for tkinter Text widgets
"""
import tkinter as tk
import sqlparse
from sqlparse import tokens as T


class SQLHighlighter:
    """SQL syntax highlighter for tkinter Text widgets"""

    # Color scheme (VS Code Light theme inspired)
    COLORS = {
        "keyword": {"foreground": "#0000FF", "font": ("Consolas", 10, "bold")},
        "string": {"foreground": "#A31515"},
        "comment": {"foreground": "#008000", "font": ("Consolas", 10, "italic")},
        "function": {"foreground": "#795E26"},
        "number": {"foreground": "#098658"},
        "operator": {"foreground": "#000000"},
        "name": {"foreground": "#001080"},
    }

    def __init__(self, text_widget):
        """Initialize highlighter

        Args:
            text_widget: tkinter Text widget to highlight
        """
        self.text_widget = text_widget
        self._configure_tags()

    def _configure_tags(self):
        """Configure text tags for syntax highlighting"""
        for tag_name, style in self.COLORS.items():
            self.text_widget.tag_configure(tag_name, **style)

    def highlight(self, sql_text=None):
        """Apply syntax highlighting to SQL text

        Args:
            sql_text: SQL text to highlight. If None, uses current widget content.
        """
        if sql_text is None:
            sql_text = self.text_widget.get(1.0, tk.END)

        # Clear existing tags
        for tag in self.COLORS.keys():
            self.text_widget.tag_remove(tag, "1.0", tk.END)

        if not sql_text.strip():
            return

        try:
            # Parse SQL
            parsed = sqlparse.parse(sql_text)
            if not parsed:
                return

            position = 0
            for token in parsed[0].flatten():
                token_text = str(token)
                token_length = len(token_text)

                if token_length == 0:
                    continue

                # Calculate position in text widget
                start_index = f"1.0 + {position} chars"
                end_index = f"1.0 + {position + token_length} chars"

                # Apply tag based on token type
                tag = self._get_tag_for_token(token)
                if tag:
                    self.text_widget.tag_add(tag, start_index, end_index)

                position += token_length

        except Exception as e:
            # Silently fail - don't interrupt user if highlighting fails
            pass

    def _get_tag_for_token(self, token):
        """Get appropriate tag for a token

        Args:
            token: sqlparse token

        Returns:
            Tag name or None
        """
        if token.ttype in (T.Keyword, T.Keyword.DDL, T.Keyword.DML, T.Keyword.Order):
            return "keyword"
        elif token.ttype in (T.String.Single, T.String.Symbol, T.String):
            return "string"
        elif token.ttype in (T.Comment.Single, T.Comment.Multiline):
            return "comment"
        elif token.ttype in (T.Number.Integer, T.Number.Float, T.Number):
            return "number"
        elif token.ttype == T.Name.Function:
            return "function"
        elif token.ttype in (T.Operator, T.Operator.Comparison):
            return "operator"
        elif token.ttype in (T.Name, T.Name.Builtin):
            return "name"

        return None


def _force_one_column_per_line(formatted_sql):
    """Post-process SQL to force one column per line in SELECT and GROUP BY

    Args:
        formatted_sql: Already formatted SQL text

    Returns:
        SQL with one column per line
    """
    lines = formatted_sql.split('\n')
    result = []
    i = 0
    collecting_select = False
    collecting_group_by = False
    select_columns = []
    group_by_columns = []
    select_indent = 0
    group_indent = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Start collecting SELECT columns
        if stripped.upper().startswith('SELECT '):
            collecting_select = True
            select_indent = len(line) - len(line.lstrip())
            after_select = stripped[7:].strip()  # Part after "SELECT "
            if after_select:
                select_columns.append(after_select)

        # Continue collecting SELECT columns (lines with commas or column names)
        elif collecting_select and not stripped.upper().startswith(('FROM', 'WHERE', 'GROUP', 'ORDER', 'LIMIT', 'HAVING', 'UNION')):
            if stripped:
                select_columns.append(stripped)

        # End of SELECT, output columns
        elif collecting_select:
            # Output SELECT with one column per line
            if select_columns:
                # Join all columns and split by comma
                all_cols = ' '.join(select_columns)
                cols = [c.strip() for c in all_cols.split(',') if c.strip()]

                base_indent = ' ' * select_indent

                if cols:
                    result.append(f"{base_indent}SELECT {cols[0]},")
                    for col in cols[1:-1]:
                        result.append(f"{base_indent}       {col},")
                    if len(cols) > 1:
                        result.append(f"{base_indent}       {cols[-1]}")

            collecting_select = False
            select_columns = []
            result.append(line)

        # Start collecting GROUP BY columns
        elif stripped.upper().startswith('GROUP BY '):
            collecting_group_by = True
            group_indent = len(line) - len(line.lstrip())
            after_group = stripped[9:].strip()  # Part after "GROUP BY "
            if after_group:
                group_by_columns.append(after_group)

        # Continue collecting GROUP BY columns
        elif collecting_group_by and not stripped.upper().startswith(('HAVING', 'ORDER', 'LIMIT', 'UNION')):
            if stripped:
                group_by_columns.append(stripped)

        # End of GROUP BY, output columns
        elif collecting_group_by:
            # Output GROUP BY with one column per line
            if group_by_columns:
                all_cols = ' '.join(group_by_columns)
                cols = [c.strip() for c in all_cols.split(',') if c.strip()]

                base_indent = ' ' * group_indent

                if cols:
                    result.append(f"{base_indent}GROUP BY {cols[0]},")
                    for col in cols[1:-1]:
                        result.append(f"{base_indent}         {col},")
                    if len(cols) > 1:
                        result.append(f"{base_indent}         {cols[-1]}")

            collecting_group_by = False
            group_by_columns = []
            result.append(line)

        else:
            result.append(line)

        i += 1

    # Handle case where SELECT/GROUP BY is at the end
    if collecting_select and select_columns:
        all_cols = ' '.join(select_columns)
        cols = [c.strip() for c in all_cols.split(',') if c.strip()]
        base_indent = ' ' * select_indent
        if cols:
            result.append(f"{base_indent}SELECT {cols[0]},")
            for col in cols[1:-1]:
                result.append(f"{base_indent}       {col},")
            if len(cols) > 1:
                result.append(f"{base_indent}       {cols[-1]}")

    if collecting_group_by and group_by_columns:
        all_cols = ' '.join(group_by_columns)
        cols = [c.strip() for c in all_cols.split(',') if c.strip()]
        base_indent = ' ' * group_indent
        if cols:
            result.append(f"{base_indent}GROUP BY {cols[0]},")
            for col in cols[1:-1]:
                result.append(f"{base_indent}         {col},")
            if len(cols) > 1:
                result.append(f"{base_indent}         {cols[-1]}")

    return '\n'.join(result)


def _format_aligned_style(formatted_sql):
    """Format SQL with aligned keywords, AS, table aliases, and ON conditions

    Args:
        formatted_sql: Already formatted SQL text

    Returns:
        SQL with advanced alignment
    """
    import re

    lines = formatted_sql.split('\n')

    # Keywords that should be aligned at the start
    main_keywords = [
        'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY',
        'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN',
        'UNION', 'UNION ALL', 'LIMIT', 'OFFSET'
    ]
    max_keyword_len = max(len(kw) for kw in main_keywords)

    # Parse SQL into sections
    sections = _parse_sql_sections_advanced(lines, main_keywords)

    # First pass: collect all sections and calculate max lengths
    select_sections = [s for s in sections if s['type'] == 'SELECT']
    from_join_sections = [s for s in sections if s['type'] in ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN')]

    # Calculate max field length for SELECT AS alignment
    max_field_len = 0
    if select_sections:
        for section in select_sections:
            for col_info in section['parsed_columns']:
                max_field_len = max(max_field_len, len(col_info['field']))

    # Calculate max table name length for table alias alignment
    max_table_len = 0
    if from_join_sections:
        for section in from_join_sections:
            if section.get('table_name'):
                max_table_len = max(max_table_len, len(section['table_name']))

    # Second pass: format each section with calculated alignments
    result = []
    for section in sections:
        if section['type'] == 'SELECT':
            _format_select_with_alignment(result, section, max_keyword_len, max_field_len)
        elif section['type'] in ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN'):
            _format_from_join_with_alignment(result, section, max_keyword_len, max_table_len)
        elif section['type'] in ('GROUP BY', 'ORDER BY'):
            _format_group_order_section(result, section, max_keyword_len)
        elif section['type'] == 'WHERE':
            _format_where_section(result, section, max_keyword_len)
        else:
            # Other sections (HAVING, LIMIT, etc.)
            _format_simple_section(result, section, max_keyword_len)

    return '\n'.join(result)


def _parse_sql_sections_advanced(lines, main_keywords):
    """Parse SQL lines into sections with pre-parsing for SELECT and FROM/JOIN"""
    import re

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
            # Start new section
            if current_section:
                sections.append(current_section)

            rest = stripped[len(keyword_found):].strip()
            current_section = {
                'type': keyword_found,
                'keyword': keyword_found,
                'content': [rest] if rest else []
            }
        elif current_section:
            # Add to current section
            current_section['content'].append(stripped)

    # Add last section
    if current_section:
        sections.append(current_section)

    # Pre-parse SELECT sections
    for section in sections:
        if section['type'] == 'SELECT':
            _preparse_select_section(section)
        elif section['type'] in ('FROM', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'JOIN'):
            _preparse_from_join_section(section)

    return sections


def _preparse_select_section(section):
    """Pre-parse SELECT section to extract columns and AS aliases"""
    import re

    # Join all content and split by commas
    all_content = ' '.join(section['content'])
    columns = [c.strip() for c in all_content.split(',') if c.strip()]

    # Parse each column
    parsed_columns = []
    for col in columns:
        # Check if column has AS
        as_match = re.search(r'\s+AS\s+', col, re.IGNORECASE)
        if as_match:
            field = col[:as_match.start()].strip()
            alias = col[as_match.end():].strip()
            parsed_columns.append({'field': field, 'alias': alias, 'has_as': True})
        else:
            parsed_columns.append({'field': col, 'alias': None, 'has_as': False})

    section['parsed_columns'] = parsed_columns


def _preparse_from_join_section(section):
    """Pre-parse FROM/JOIN section to extract table, alias, and ON conditions"""
    import re

    all_content = ' '.join(section['content'])

    # Parse table and alias
    # Format: "table_name alias ON condition" or "table_name alias"
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
        # Split by AND (case-insensitive)
        and_conditions_raw = re.split(r'\s+AND\s+', on_part, flags=re.IGNORECASE)

        # Parse each condition to find operator for alignment
        parsed_conditions = []
        max_left_len = 0

        for cond in and_conditions_raw:
            cond = cond.strip()
            # Try to detect operator (=, >=, <=, !=, <>, <, >, IN, LIKE, IS, etc.)
            operator_match = re.search(r'\s*(>=|<=|!=|<>|=|<|>|IN|NOT IN|LIKE|NOT LIKE|IS NOT|IS)\s+', cond, re.IGNORECASE)

            if operator_match:
                left = cond[:operator_match.start()].strip()
                operator = operator_match.group(1).strip().upper()
                right = cond[operator_match.end():].strip()

                parsed_conditions.append({
                    'left': left,
                    'operator': operator,
                    'right': right,
                    'has_operator': True
                })
                max_left_len = max(max_left_len, len(left))
            else:
                parsed_conditions.append({
                    'full': cond,
                    'has_operator': False
                })

        section['on_conditions'] = and_conditions_raw
        section['parsed_on_conditions'] = parsed_conditions
        section['max_on_left_len'] = max_left_len
    else:
        section['on_conditions'] = []
        section['parsed_on_conditions'] = []
        section['max_on_left_len'] = 0


def _format_select_with_alignment(result, section, max_keyword_len, max_field_len):
    """Format SELECT section with aligned AS keywords"""
    column_indent = ' ' * (max_keyword_len - 1)

    for i, col_info in enumerate(section['parsed_columns']):
        if i == 0:
            # First column with keyword
            if col_info['has_as']:
                field_padded = col_info['field'].ljust(max_field_len)
                result.append(f"SELECT     {field_padded} AS {col_info['alias']}")
            else:
                result.append(f"SELECT     {col_info['field']}")
        else:
            # Subsequent columns with comma-first
            if col_info['has_as']:
                field_padded = col_info['field'].ljust(max_field_len)
                result.append(f"{column_indent}, {field_padded} AS {col_info['alias']}")
            else:
                result.append(f"{column_indent}, {col_info['field']}")


def _format_from_join_with_alignment(result, section, max_keyword_len, max_table_len):
    """Format FROM/JOIN section with aligned table aliases and ON/AND aligned"""
    keyword = section['keyword']
    table_name = section.get('table_name', '')
    table_alias = section.get('table_alias', '')
    parsed_conditions = section.get('parsed_on_conditions', [])
    max_left_len = section.get('max_on_left_len', 0)

    # Format: KEYWORD table_name alias ON condition
    if table_alias:
        table_padded = table_name.ljust(max_table_len)
        line = f"{keyword.ljust(max_keyword_len)} {table_padded} {table_alias}"
        # Position where ON starts
        on_start_pos = max_keyword_len + 1 + max_table_len + 1 + len(table_alias) + 1
    else:
        line = f"{keyword.ljust(max_keyword_len)} {table_name}"
        on_start_pos = max_keyword_len + 1 + len(table_name) + 1

    # Add ON conditions with aligned operators
    if parsed_conditions:
        # Calculate position where = sign should be
        equals_position = max_left_len + 1  # +1 = one space after longest field

        # First condition on same line
        first_cond = parsed_conditions[0]
        if first_cond.get('has_operator'):
            left = first_cond['left']
            operator = first_cond['operator']
            padding = _calculate_operator_padding(left, operator, equals_position)
            line += f" ON  {left}{' ' * padding}{operator} {first_cond['right']}"
        else:
            line += f" ON  {first_cond['full']}"
        result.append(line)

        # Additional AND conditions on separate lines
        # AND aligned with ON, then operators aligned
        if len(parsed_conditions) > 1:
            # Align AND with ON (not with the condition)
            and_indent = ' ' * on_start_pos

            for cond_info in parsed_conditions[1:]:
                if cond_info.get('has_operator'):
                    left = cond_info['left']
                    operator = cond_info['operator']
                    padding = _calculate_operator_padding(left, operator, equals_position)
                    result.append(f"{and_indent}AND {left}{' ' * padding}{operator} {cond_info['right']}")
                else:
                    result.append(f"{and_indent}AND {cond_info['full']}")
    else:
        result.append(line)


def _format_group_order_section(result, section, max_keyword_len):
    """Format GROUP BY / ORDER BY with one column per line and aligned ASC/DESC"""
    import re

    # Join all content and split by commas
    all_content = ' '.join(section['content'])
    columns = [c.strip() for c in all_content.split(',') if c.strip()]

    if not columns:
        return

    column_indent = ' ' * (max_keyword_len - 1)
    keyword = section['keyword']

    # For ORDER BY, parse columns to extract ASC/DESC and align them
    if keyword == 'ORDER BY':
        parsed_columns = []
        max_col_len = 0

        for col in columns:
            # Check for ASC or DESC at the end
            asc_match = re.search(r'\s+(ASC|DESC)\s*$', col, re.IGNORECASE)
            if asc_match:
                col_name = col[:asc_match.start()].strip()
                direction = asc_match.group(1).upper()
                parsed_columns.append({'col': col_name, 'direction': direction})
                max_col_len = max(max_col_len, len(col_name))
            else:
                parsed_columns.append({'col': col, 'direction': None})
                max_col_len = max(max_col_len, len(col))

        # Format with aligned ASC/DESC
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
        # GROUP BY - no direction alignment needed
        for i, col in enumerate(columns):
            if i == 0:
                result.append(f"{keyword.ljust(max_keyword_len)} {col}")
            else:
                result.append(f"{column_indent}, {col}")


def _format_where_section(result, section, max_keyword_len):
    """Format WHERE section with multiple AND conditions and aligned operators"""
    import re

    content = ' '.join(section['content'])

    # Split by AND (case-insensitive)
    and_conditions = re.split(r'\s+AND\s+', content, flags=re.IGNORECASE)

    if len(and_conditions) == 1:
        # Single condition, output as-is
        result.append(f"{section['keyword'].ljust(max_keyword_len)} {content}")
    else:
        # Multiple conditions - parse and align operators
        parsed_conditions = []
        max_left_len = 0

        for cond in and_conditions:
            cond = cond.strip()
            # Try to detect operator (=, >=, <=, !=, <>, <, >, IN, LIKE, IS, etc.)
            operator_match = re.search(r'\s*(>=|<=|!=|<>|=|<|>|IN|NOT IN|LIKE|NOT LIKE|IS NOT|IS)\s+', cond, re.IGNORECASE)

            if operator_match:
                left = cond[:operator_match.start()].strip()
                operator = operator_match.group(1).strip().upper()
                right = cond[operator_match.end():].strip()

                parsed_conditions.append({
                    'left': left,
                    'operator': operator,
                    'right': right,
                    'has_operator': True
                })
                max_left_len = max(max_left_len, len(left))
            else:
                parsed_conditions.append({
                    'full': cond,
                    'has_operator': False
                })

        # Calculate position where = sign should be
        # This ensures the = is always at the same column
        equals_position = max_left_len + 1  # +1 = one space after longest field

        # Output first condition with WHERE
        first_cond = parsed_conditions[0]
        if first_cond.get('has_operator'):
            left = first_cond['left']
            operator = first_cond['operator']
            # Calculate padding to align = signs
            padding = _calculate_operator_padding(left, operator, equals_position)
            result.append(f"WHERE      {left}{' ' * padding}{operator} {first_cond['right']}")
        else:
            result.append(f"WHERE      {first_cond['full']}")

        # Output remaining conditions with AND
        for cond_info in parsed_conditions[1:]:
            if cond_info.get('has_operator'):
                left = cond_info['left']
                operator = cond_info['operator']
                padding = _calculate_operator_padding(left, operator, equals_position)
                result.append(f"AND        {left}{' ' * padding}{operator} {cond_info['right']}")
            else:
                result.append(f"AND        {cond_info['full']}")


def _calculate_operator_padding(left_field, operator, equals_position):
    """Calculate padding before operator to align = signs at a fixed position

    Args:
        left_field: The left side of the condition (e.g., "date_field")
        operator: The operator (=, >=, <=, !=, etc.)
        equals_position: The absolute position where = should appear

    Returns:
        Number of spaces to add after left_field and before operator
    """
    # For "=", the = is the operator itself, so it should be at equals_position
    # We need: len(left_field) + padding + 0 = equals_position
    # So padding = equals_position - len(left_field)

    # For ">=", the = is the second character, so >= should start at equals_position - 1
    # We need: len(left_field) + padding + 1 = equals_position
    # So padding = equals_position - len(left_field) - 1

    if operator == '=':
        padding = equals_position - len(left_field)
    elif '=' in operator and len(operator) >= 2 and operator[1] == '=':
        # Operators like >=, <=, !=, == where = is at position 1
        padding = equals_position - len(left_field) - 1
    else:
        # Other operators - just ensure at least one space
        padding = equals_position - len(left_field)

    # Ensure at least one space
    return max(1, padding)


def _format_simple_section(result, section, max_keyword_len):
    """Format simple sections (HAVING, LIMIT, etc.)"""
    content = ' '.join(section['content'])
    if content:
        result.append(f"{section['keyword'].ljust(max_keyword_len)} {content}")
    else:
        result.append(section['keyword'].ljust(max_keyword_len))


def format_sql(sql_text, style='expanded', keyword_case='upper'):
    """Format SQL text for readability

    Args:
        sql_text: SQL text to format
        style: Formatting style - 'expanded', 'compact', 'comma_first'
        keyword_case: 'upper', 'lower', or 'capitalize' for SQL keywords

    Returns:
        Formatted SQL text
    """
    if not sql_text or not sql_text.strip():
        return sql_text

    try:
        # Style presets
        if style == 'expanded':
            # One column per line (maximum readability)
            # First format normally
            formatted = sqlparse.format(
                sql_text,
                reindent=True,
                keyword_case=keyword_case,
                indent_width=4,
                indent_tabs=False,
                use_space_around_operators=True,
                comma_first=False
            )
            # Post-process to force one column per line
            formatted = _force_one_column_per_line(formatted)
        elif style == 'compact':
            # Multiple columns on same line (more compact)
            formatted = sqlparse.format(
                sql_text,
                reindent=True,
                keyword_case=keyword_case,
                indent_width=2,
                indent_tabs=False,
                use_space_around_operators=True,
                wrap_after=120,  # Longer lines allowed
                comma_first=False
            )
        elif style == 'comma_first':
            # Commas at beginning of line
            formatted = sqlparse.format(
                sql_text,
                reindent=True,
                keyword_case=keyword_case,
                indent_width=4,
                indent_tabs=False,
                use_space_around_operators=True,
                comma_first=True
            )
        elif style == 'sophisticated':
            # Sophisticated aligned style
            formatted = sqlparse.format(
                sql_text,
                reindent=True,
                keyword_case=keyword_case,
                indent_width=4,
                indent_tabs=False,
                use_space_around_operators=True
            )
            # Post-process to align keywords
            formatted = _format_aligned_style(formatted)
        else:
            # Default to expanded
            formatted = sqlparse.format(
                sql_text,
                reindent=True,
                keyword_case=keyword_case,
                indent_width=4,
                indent_tabs=False,
                use_space_around_operators=True
            )

        return formatted
    except Exception:
        # If formatting fails, return original
        return sql_text


# Predefined formatting styles
SQL_FORMAT_STYLES = {
    'expanded': {
        'name': 'Expanded (1 column/line)',
        'description': 'One column per line - Maximum readability'
    },
    'compact': {
        'name': 'Compact',
        'description': 'Multiple columns on same line - More compact'
    },
    'comma_first': {
        'name': 'Comma First',
        'description': 'Commas at beginning of line - Easy to spot missing commas'
    },
    'sophisticated': {
        'name': 'Sophisticated',
        'description': 'Advanced alignment - Keywords, AS, and sort orders aligned'
    }
}
