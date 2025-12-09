"""
Test different SQL formatting styles with sqlparse
"""
import sqlparse

print("=" * 80)
print("TESTING SQL FORMATTING STYLES")
print("=" * 80)

# Test query
test_query = "SELECT id, name, email, created_at, status, phone FROM users WHERE status='active' AND created_at > '2024-01-01' ORDER BY name"

print("\nORIGINAL QUERY:")
print(test_query)

# Style 1: Default (current behavior)
print("\n" + "=" * 80)
print("STYLE 1: DEFAULT (Current)")
print("=" * 80)
formatted = sqlparse.format(
    test_query,
    reindent=True,
    keyword_case='upper',
    indent_width=4
)
print(formatted)

# Style 2: Compact
print("\n" + "=" * 80)
print("STYLE 2: COMPACT")
print("=" * 80)
formatted = sqlparse.format(
    test_query,
    reindent=True,
    keyword_case='upper',
    indent_width=2,
    wrap_after=80
)
print(formatted)

# Style 3: Expanded (one item per line - need custom processing)
print("\n" + "=" * 80)
print("STYLE 3: EXPANDED (One column per line)")
print("=" * 80)

# Parse the query
parsed = sqlparse.parse(test_query)[0]

# This is a manual approach - let's see what sqlparse gives us first
formatted = sqlparse.format(
    test_query,
    reindent=True,
    keyword_case='upper',
    indent_width=4,
    wrap_after=1,  # Force wrapping
    comma_first=False
)
print(formatted)

# Style 4: Comma First
print("\n" + "=" * 80)
print("STYLE 4: COMMA FIRST")
print("=" * 80)
formatted = sqlparse.format(
    test_query,
    reindent=True,
    keyword_case='upper',
    indent_width=4,
    comma_first=True
)
print(formatted)

# Now let's test with a more complex query
complex_query = """SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.total) as total_amount, AVG(o.total) as avg_order FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.status='active' GROUP BY u.id, u.name, u.email HAVING COUNT(o.id) > 5 ORDER BY total_amount DESC"""

print("\n" + "=" * 80)
print("COMPLEX QUERY - EXPANDED STYLE")
print("=" * 80)

# Custom function to force one column per line
def format_expanded(sql_text):
    """Format SQL with one column per line in SELECT"""
    # First, format normally
    formatted = sqlparse.format(
        sql_text,
        reindent=True,
        keyword_case='upper',
        indent_width=4
    )

    # Parse to identify SELECT columns
    parsed = sqlparse.parse(sql_text)[0]

    # For now, let's try a simple approach:
    # Replace ", " after identifiers in SELECT with ",\n    "
    import re

    lines = formatted.split('\n')
    result = []
    in_select = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('SELECT'):
            in_select = True
            # Get the part after SELECT
            after_select = line[line.upper().index('SELECT') + 6:].strip()
            if after_select:
                # Split by comma
                columns = [col.strip() for col in after_select.split(',')]
                result.append(line[:line.upper().index('SELECT') + 6])
                for i, col in enumerate(columns):
                    if i == 0:
                        result[-1] += ' ' + col
                    else:
                        result.append(' ' * 7 + col)  # 7 spaces = "SELECT "
        elif stripped.startswith('FROM'):
            in_select = False
            result.append(line)
        elif in_select and ',' in line:
            # Split columns
            indent = len(line) - len(line.lstrip())
            columns = [col.strip() for col in line.split(',')]
            for i, col in enumerate(columns):
                if i == 0:
                    result.append(line)
                else:
                    result.append(' ' * indent + col)
        else:
            result.append(line)

    return '\n'.join(result)

formatted_custom = format_expanded(complex_query)
print(formatted_custom)

print("\n" + "=" * 80)
print("SUMMARY OF STYLES")
print("=" * 80)
print("""
Available styles:

1. DEFAULT (current)
   - Standard formatting
   - Multiple columns on same line if they fit
   - Keywords uppercase
   - 4-space indent

2. COMPACT
   - Similar to default
   - 2-space indent
   - More compact

3. EXPANDED
   - One column per line in SELECT
   - One column per line in GROUP BY
   - Maximum readability
   - Good for complex queries

4. COMMA_FIRST
   - Commas at beginning of line
   - Popular in some teams
   - Easy to spot missing commas
""")
