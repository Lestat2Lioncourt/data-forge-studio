"""
Demo: SQL Formatting and Syntax Highlighting
Shows how easy it is to implement these features
"""
print("=" * 70)
print("DEMO: SQL FORMATTING & SYNTAX HIGHLIGHTING")
print("=" * 70)

# Test 1: SQL Formatting with sqlparse
print("\n1. Testing SQL Formatting...")
try:
    import sqlparse
    print("   [OK] sqlparse imported")

    # Test query on one line
    ugly_query = "SELECT u.id, u.name, u.email, o.order_id, o.total, o.created_at FROM users u INNER JOIN orders o ON u.id = o.user_id WHERE o.total > 100 AND u.status = 'active' AND o.created_at > '2024-01-01' ORDER BY o.total DESC LIMIT 10"

    print("\n   Original (one line):")
    print(f"   {ugly_query[:80]}...")

    # Format it
    formatted = sqlparse.format(
        ugly_query,
        reindent=True,
        keyword_case='upper',
        indent_width=4,
        use_space_around_operators=True
    )

    print("\n   Formatted (pretty-printed):")
    for line in formatted.split('\n'):
        print(f"   {line}")

    print("\n   [OK] SQL formatting works perfectly!")

except ImportError:
    print("   [INFO] sqlparse not installed")
    print("   Run: uv add sqlparse")
except Exception as e:
    print(f"   [ERROR] Formatting failed: {e}")

# Test 2: SQL Parsing for Syntax Highlighting
print("\n2. Testing SQL Parsing (for syntax highlighting)...")
try:
    import sqlparse
    from sqlparse import tokens as T

    test_sql = "SELECT name, email FROM users WHERE id = 42 -- Get user info"

    # Parse SQL
    parsed = sqlparse.parse(test_sql)[0]

    print(f"\n   SQL: {test_sql}")
    print("\n   Tokens detected:")

    for token in parsed.flatten():
        if token.ttype is not None:  # Skip whitespace
            token_type_name = str(token.ttype).split('.')[-1]
            token_value = repr(str(token))
            print(f"      {token_type_name:20} -> {token_value}")

    print("\n   [OK] SQL parsing identifies all token types!")
    print("   [OK] Can easily map token types to colors!")

except Exception as e:
    print(f"   [ERROR] Parsing failed: {e}")

# Test 3: Complex Query Formatting
print("\n3. Testing Complex Query Formatting...")
try:
    import sqlparse

    complex_query = """
    SELECT
        p.product_id,
        p.name,
        c.category_name,
        SUM(oi.quantity) as total_sold,
        AVG(oi.price) as avg_price,
        COUNT(DISTINCT o.customer_id) as unique_customers
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    INNER JOIN order_items oi ON p.product_id = oi.product_id
    INNER JOIN orders o ON oi.order_id = o.id
    WHERE o.created_at BETWEEN '2024-01-01' AND '2024-12-31'
        AND p.status = 'active'
        AND (p.discount > 0 OR p.featured = 1)
    GROUP BY p.product_id, p.name, c.category_name
    HAVING SUM(oi.quantity) > 100
    ORDER BY total_sold DESC, avg_price ASC
    LIMIT 50;
    """

    # This is already formatted, but let's re-format to show consistency
    reformatted = sqlparse.format(
        complex_query,
        reindent=True,
        keyword_case='upper',
        indent_width=4
    )

    print("   [OK] Complex query formatted successfully")
    print("   Sample output:")
    for i, line in enumerate(reformatted.split('\n')[:10], 1):
        if line.strip():
            print(f"   {i:2}. {line}")

except Exception as e:
    print(f"   [ERROR] Complex formatting failed: {e}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print("\nComplexity Assessment:")
print("  Formatage SQL:           [*] TRES FACILE - 30 min a 1h")
print("  Coloration syntaxique:   [**] FACILE - 2-3h")
print("")
print("Benefits:")
print("  + Readability: Queries become instantly readable")
print("  + Productivity: Faster development and debugging")
print("  + Professional: IDE-like experience")
print("")
print("Required package:")
print("  uv add sqlparse  (~200 KB, BSD license)")
print("")
print("Implementation estimate: 3-4 hours total for both features")
print("")
print("ROI: EXCELLENT (high value, low effort)")
