"""
Test the redesigned Aligned style with new criteria:
- Aligned AS after longest field
- Aligned table aliases after longest table name
- AND conditions aligned properly
- One column per line in GROUP BY and ORDER BY
- ON on same line as table
"""
from sql_highlighter import format_sql

print("=" * 80)
print("TESTING REDESIGNED ALIGNED STYLE")
print("=" * 80)

# User's exact example
test_query = """SELECT YEAR(date_field) AS YEAR, MONTH(date_field) AS MONTH, COUNT(*) AS total_records FROM your_table a INNER JOIN test b ON a.id = b.id AND a.code = b.code WHERE date_field >= DATEADD(MONTH, -12, GETDATE()) GROUP BY YEAR(date_field), MONTH(date_field) ORDER BY YEAR DESC, MONTH DESC"""

print("\nORIGINAL QUERY (one line):")
print(test_query)

print("\n" + "=" * 80)
print("FORMATTED WITH NEW ALIGNED STYLE:")
print("=" * 80)

formatted = format_sql(test_query, style='aligned', keyword_case='upper')
print(formatted)

print("\n" + "=" * 80)
print("EXPECTED FORMAT (from user's example):")
print("=" * 80)
expected = """SELECT     YEAR(date_field)  AS YEAR
         , MONTH(date_field) AS MONTH
         , COUNT(*)          AS total_records
FROM       your_table a
INNER JOIN test       b ON  a.id      = b.id
                              AND a.code = b.code
WHERE      date_field >= DATEADD(MONTH, -12, GETDATE())
GROUP BY   YEAR(date_field)
         , MONTH(date_field)
ORDER BY   YEAR DESC
         , MONTH DESC"""
print(expected)

# Test more complex queries
print("\n" + "=" * 80)
print("COMPLEX QUERY TEST:")
print("=" * 80)

complex_query = """SELECT u.id AS user_id, u.name AS user_name, COUNT(o.id) AS order_count, SUM(o.total) AS total_amount FROM users u INNER JOIN orders o ON u.id = o.user_id AND u.status = 'active' LEFT JOIN profiles p ON u.id = p.user_id WHERE o.created_at > '2024-01-01' GROUP BY u.id, u.name HAVING COUNT(o.id) > 5 ORDER BY total_amount DESC, user_name ASC"""

print("\nOriginal:")
print(complex_query)

print("\nFormatted:")
formatted_complex = format_sql(complex_query, style='aligned', keyword_case='upper')
print(formatted_complex)

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)
print("Expected features:")
print("  1. AS aligned after longest field in SELECT")
print("  2. Table aliases aligned after longest table name")
print("  3. ON on same line as table")
print("  4. AND conditions aligned under ON")
print("  5. One column per line in GROUP BY")
print("  6. One column per line in ORDER BY")
print("  7. Comma-first style for columns")
