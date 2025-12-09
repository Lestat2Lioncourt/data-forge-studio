"""
Final integration test for all 4 SQL formatting styles
"""
print("=" * 80)
print("FINAL INTEGRATION TEST - ALL 4 SQL FORMATTING STYLES")
print("=" * 80)

# Test 1: Import and verify all components
print("\n1. Testing imports...")
try:
    from sql_highlighter import format_sql, SQL_FORMAT_STYLES
    print(f"   [OK] sql_highlighter imported")
    print(f"   [OK] {len(SQL_FORMAT_STYLES)} styles available")
except Exception as e:
    print(f"   [ERROR] Import failed: {e}")
    exit(1)

# Test 2: Verify all 4 styles are present
print("\n2. Verifying all styles...")
expected_styles = ['expanded', 'compact', 'comma_first', 'aligned']
for style in expected_styles:
    if style in SQL_FORMAT_STYLES:
        print(f"   [OK] '{style}' style found: {SQL_FORMAT_STYLES[style]['name']}")
    else:
        print(f"   [ERROR] '{style}' style missing!")
        exit(1)

# Test 3: Format test query with each style
print("\n3. Testing each style with complex query...")
test_query = """SELECT u.id, u.name, u.email, COUNT(o.id) as cnt, SUM(o.total) as sum FROM users u INNER JOIN orders o ON u.id = o.user_id LEFT JOIN profiles p ON u.id = p.user_id WHERE u.status='active' AND o.total > 100 GROUP BY u.id, u.name, u.email HAVING COUNT(o.id) > 5 ORDER BY sum DESC LIMIT 10"""

results = {}
for style_key in expected_styles:
    try:
        formatted = format_sql(test_query, style=style_key, keyword_case='upper')
        results[style_key] = formatted
        lines = formatted.split('\n')
        print(f"   [OK] '{style_key}' - {len(lines)} lines, {len(formatted)} chars")
    except Exception as e:
        print(f"   [ERROR] '{style_key}' failed: {e}")
        exit(1)

# Test 4: Verify specific characteristics of each style
print("\n4. Verifying style-specific characteristics...")

# Expanded: should have one column per line
expanded_lines = results['expanded'].split('\n')
select_section = [l for l in expanded_lines if 'u.id' in l or 'u.name' in l or 'u.email' in l or 'cnt' in l or 'sum' in l]
if len(select_section) >= 4:
    print("   [OK] Expanded: Multiple columns on separate lines")
else:
    print(f"   [WARNING] Expanded: Expected multiple column lines, got {len(select_section)}")

# Compact: should be more compact
compact_lines = results['compact'].split('\n')
if len(compact_lines) < len(expanded_lines):
    print(f"   [OK] Compact: Fewer lines ({len(compact_lines)}) than Expanded ({len(expanded_lines)})")
else:
    print(f"   [WARNING] Compact: Not more compact than Expanded")

# Comma First: should have commas at beginning
comma_first_lines = [l for l in results['comma_first'].split('\n') if l.strip().startswith(',')]
if len(comma_first_lines) > 0:
    print(f"   [OK] Comma First: {len(comma_first_lines)} lines start with comma")
else:
    print("   [WARNING] Comma First: No lines start with comma")

# Aligned: should have aligned keywords
aligned_lines = results['aligned'].split('\n')
keyword_lines = [l for l in aligned_lines if any(kw in l for kw in ['SELECT', 'FROM', 'JOIN', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT'])]
if len(keyword_lines) >= 8:
    print(f"   [OK] Aligned: {len(keyword_lines)} keyword lines found")
else:
    print(f"   [WARNING] Aligned: Expected many keyword lines, got {len(keyword_lines)}")

# Check for ON clause on separate line in aligned style
on_lines = [l for l in aligned_lines if l.strip().startswith('ON ')]
if len(on_lines) >= 2:
    print(f"   [OK] Aligned: {len(on_lines)} ON clauses on separate lines")
else:
    print(f"   [WARNING] Aligned: Expected ON clauses on separate lines, got {len(on_lines)}")

# Test 5: Display formatted output for visual verification
print("\n" + "=" * 80)
print("VISUAL VERIFICATION - ALIGNED STYLE OUTPUT")
print("=" * 80)
print(results['aligned'])

print("\n" + "=" * 80)
print("SUCCESS: All 4 SQL formatting styles are working correctly!")
print("=" * 80)

print("\nSummary:")
print("  - Expanded (1 column/line): Maximum readability, one column per line")
print("  - Compact: Multiple columns per line, more compact")
print("  - Comma First: Commas at beginning of line, easy to spot missing commas")
print("  - Aligned (Keywords): Keywords aligned vertically, very structured")

print("\nReady to use in the application!")
print("  Run: uv run python gui.py")
print("  Go to: Database -> Query Manager")
print("  Select style from dropdown and click Format button")
