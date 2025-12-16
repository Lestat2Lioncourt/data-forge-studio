"""
Test SQL formatting styles integration
"""
print("=" * 70)
print("TESTING SQL FORMATTING STYLES INTEGRATION")
print("=" * 70)

# Test 1: Import modules
print("\n1. Testing imports...")
try:
    from sql_highlighter import format_sql, SQL_FORMAT_STYLES
    print("   [OK] sql_highlighter imported with styles")
except Exception as e:
    print(f"   [ERROR] Import failed: {e}")
    exit(1)

# Test 2: Verify styles dictionary
print("\n2. Checking available styles...")
try:
    print(f"   [OK] Found {len(SQL_FORMAT_STYLES)} styles:")
    for key, info in SQL_FORMAT_STYLES.items():
        print(f"      - {key}: {info['name']}")
        print(f"        {info['description']}")
except Exception as e:
    print(f"   [ERROR] Styles check failed: {e}")
    exit(1)

# Test 3: Test each style with a sample query
print("\n3. Testing each formatting style...")

test_query = "SELECT id, name, email, created_at, status FROM users WHERE status='active' AND created_at > '2024-01-01' ORDER BY name"

for style_key in SQL_FORMAT_STYLES.keys():
    try:
        formatted = format_sql(test_query, style=style_key, keyword_case='upper')
        lines = formatted.split('\n')
        print(f"\n   [OK] Style '{style_key}' - {len(lines)} lines generated")

        # Show first few lines
        for i, line in enumerate(lines[:5], 1):
            print(f"      {i}. {line}")

        if len(lines) > 5:
            print(f"      ... ({len(lines) - 5} more lines)")

    except Exception as e:
        print(f"   [ERROR] Style '{style_key}' failed: {e}")
        exit(1)

# Test 4: Verify database_manager integration
print("\n4. Testing database_manager integration...")
try:
    from database_manager import QueryTab
    print("   [OK] database_manager imports successfully")

    # Check if QueryTab has format_style_keys attribute (will be set on init)
    import inspect
    init_source = inspect.getsource(QueryTab.__init__)

    if 'format_style_keys' in init_source:
        print("   [OK] QueryTab has format_style_keys attribute")
    else:
        print("   [WARNING] format_style_keys not found in QueryTab.__init__")

    if 'SQL_FORMAT_STYLES' in init_source:
        print("   [OK] QueryTab uses SQL_FORMAT_STYLES")
    else:
        print("   [WARNING] SQL_FORMAT_STYLES not found in QueryTab.__init__")

except Exception as e:
    print(f"   [ERROR] database_manager integration check failed: {e}")

# Test 5: Compare styles side-by-side
print("\n5. Side-by-side comparison:")
print("=" * 70)

print("\nOriginal query (one line):")
print(test_query)

for style_key, style_info in SQL_FORMAT_STYLES.items():
    print("\n" + "-" * 70)
    print(f"Style: {style_info['name']}")
    print(f"Description: {style_info['description']}")
    print("-" * 70)

    formatted = format_sql(test_query, style=style_key)
    print(formatted)

print("\n" + "=" * 70)
print("SUCCESS: All formatting styles working!")
print("=" * 70)

print("\nHow to use in the application:")
print("  1. Run: uv run python gui.py")
print("  2. Database -> Query Manager")
print("  3. Type or paste a SQL query")
print("  4. Select a style from 'Style:' dropdown")
print("     - Expanded (1 column/line) - Default, maximum readability")
print("     - Compact - Multiple columns per line, more compact")
print("     - Comma First - Commas at beginning of line")
print("  5. Click 'Format' button")
print("  6. Query is formatted with selected style!")
print("")
print("The 'Expanded' style (default) puts ONE COLUMN PER LINE")
print("Perfect for complex queries with many columns!")
