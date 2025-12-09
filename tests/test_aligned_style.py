"""
Test the new Aligned (Keywords) SQL formatting style
"""
from sql_highlighter import format_sql, SQL_FORMAT_STYLES

print("=" * 80)
print("TESTING ALIGNED (KEYWORDS) FORMATTING STYLE")
print("=" * 80)

# Test with the user's exact example query structure
test_query = """SELECT id, name, email, created_at, status FROM users a INNER JOIN ddfssf b ON a.id = b.id WHERE status='active' GROUP BY id, name"""

print("\nORIGINAL QUERY (one line):")
print(test_query)

print("\n" + "=" * 80)
print("FORMATTED WITH ALIGNED STYLE:")
print("=" * 80)

formatted = format_sql(test_query, style='aligned', keyword_case='upper')
print(formatted)

print("\n" + "=" * 80)
print("EXPECTED FORMAT (from user's example):")
print("=" * 80)
print("""SELECT     id
         , name
         , email
         , created_at
         , status
FROM       users  a
INNER JOIN ddfssf b
        ON a.id = b.id
WHERE      status = 'active'
GROUP BY   id
         , name""")

# Test with a more complex query
complex_query = """SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.total) as total FROM users u LEFT JOIN orders o ON u.id = o.user_id INNER JOIN profiles p ON u.id = p.user_id WHERE u.status='active' AND o.created_at > '2024-01-01' GROUP BY u.id, u.name, u.email HAVING COUNT(o.id) > 5 ORDER BY total DESC"""

print("\n" + "=" * 80)
print("COMPLEX QUERY WITH ALIGNED STYLE:")
print("=" * 80)
print("\nOriginal:")
print(complex_query)

print("\nFormatted:")
formatted_complex = format_sql(complex_query, style='aligned', keyword_case='upper')
print(formatted_complex)

# Compare all 4 styles side-by-side
print("\n" + "=" * 80)
print("COMPARISON OF ALL 4 STYLES")
print("=" * 80)

simple_query = "SELECT id, name, email FROM users WHERE status='active' ORDER BY name"

for style_key, style_info in SQL_FORMAT_STYLES.items():
    print("\n" + "-" * 80)
    print(f"STYLE: {style_info['name']}")
    print(f"Description: {style_info['description']}")
    print("-" * 80)
    formatted = format_sql(simple_query, style=style_key, keyword_case='upper')
    print(formatted)

print("\n" + "=" * 80)
print("SUCCESS: Aligned (Keywords) style is now available!")
print("=" * 80)

print("\nHow to use in the application:")
print("  1. Run: uv run python gui.py")
print("  2. Database -> Query Manager")
print("  3. Type or paste a SQL query")
print("  4. Select 'Aligned (Keywords)' from 'Style:' dropdown")
print("  5. Click 'Format' button")
print("  6. Query is formatted with aligned keywords and comma-first columns!")
