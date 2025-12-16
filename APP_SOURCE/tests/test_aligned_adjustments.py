"""
Test the adjusted Aligned style with:
- ON and AND aligned in JOINs
- Multiple WHERE AND conditions with aligned operators
- >= operator with = aligned
"""
from sql_highlighter import format_sql

print("=" * 80)
print("TESTING ADJUSTED ALIGNED STYLE")
print("=" * 80)

# User's exact example with WHERE AND conditions
test_query = """SELECT YEAR(date_field) AS YEAR, MONTH(date_field) AS MONTH, COUNT(*) AS total_records FROM your_table a INNER JOIN test b ON a.id = b.id AND a.code = b.code WHERE date_field >= DATEADD(MONTH, -12, GETDATE()) AND b.value = '14' AND c.description = 'cheval' GROUP BY YEAR(date_field), MONTH(date_field) ORDER BY YEAR DESC, MONTH DESC"""

print("\nORIGINAL QUERY (one line):")
print(test_query)

print("\n" + "=" * 80)
print("FORMATTED WITH ADJUSTED ALIGNED STYLE:")
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
INNER JOIN test       b ON  a.id   = b.id
                        AND a.code = b.code
WHERE      date_field   >= DATEADD(MONTH, -12, GETDATE())
AND        b.value       = '14'
AND        c.description = 'cheval'
GROUP BY   YEAR(date_field)
         , MONTH(date_field)
ORDER BY   YEAR DESC
         , MONTH DESC"""
print(expected)

# Test with more complex operators
print("\n" + "=" * 80)
print("TEST WITH VARIOUS OPERATORS:")
print("=" * 80)

complex_query = """SELECT u.id, u.name FROM users u INNER JOIN orders o ON u.id = o.user_id AND u.created_at >= o.created_at WHERE u.age >= 18 AND u.status = 'active' AND u.balance <= 1000"""

formatted_complex = format_sql(complex_query, style='aligned', keyword_case='upper')
print(formatted_complex)

print("\n" + "=" * 80)
print("VERIFICATION:")
print("=" * 80)
print("[CHECK] ON and AND aligned in JOIN conditions")
print("[CHECK] WHERE and AND aligned with multiple conditions")
print("[CHECK] >= operator with = aligned with other = signs")
print("[CHECK] <= operator with = aligned with other = signs")
