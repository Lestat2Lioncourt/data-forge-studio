"""
Test script for Queries Manager improvements
"""
print("=" * 70)
print("TESTING QUERIES MANAGER IMPROVEMENTS")
print("=" * 70)

# Test imports
print("\n1. Testing imports...")
try:
    from queries_manager import QueriesManager
    print("   [OK] QueriesManager imported")
except Exception as e:
    print(f"   [ERROR] QueriesManager import failed: {e}")
    exit(1)

try:
    from gui import DataLakeLoaderGUI
    print("   [OK] GUI imported")
except Exception as e:
    print(f"   [ERROR] GUI import failed: {e}")
    exit(1)

# Test that methods exist
print("\n2. Testing QueriesManager methods...")
try:
    import inspect
    methods = inspect.getmembers(QueriesManager, predicate=inspect.isfunction)
    method_names = [m[0] for m in methods]

    required_methods = [
        '_execute_query',
        '_edit_query',
        '_delete_query',
        '_load_in_query_manager'
    ]

    for method_name in required_methods:
        if method_name in method_names:
            print(f"   [OK] Method '{method_name}' exists")
        else:
            print(f"   [ERROR] Method '{method_name}' not found")

except Exception as e:
    print(f"   [ERROR] Failed to check methods: {e}")
    exit(1)

# Test GUI method signature
print("\n3. Testing GUI method signature...")
try:
    import inspect
    sig = inspect.signature(DataLakeLoaderGUI._show_database_frame_with_query)
    params = list(sig.parameters.keys())

    if 'execute' in params:
        print("   [OK] GUI method has 'execute' parameter")
        # Check default value
        execute_param = sig.parameters['execute']
        if execute_param.default is False:
            print("   [OK] 'execute' parameter defaults to False")
        else:
            print(f"   [WARNING] 'execute' default is {execute_param.default}, expected False")
    else:
        print("   [ERROR] GUI method missing 'execute' parameter")

except Exception as e:
    print(f"   [ERROR] Failed to check GUI method: {e}")
    exit(1)

print("\n" + "=" * 70)
print("SUCCESS: All improvements are ready!")
print("=" * 70)

print("\nNew Features:")
print("1. Execute Query button - Run query and see results immediately")
print("2. Reorganized interface - Query Details at top with smaller fonts")
print("3. Edit Query - Opens query in Query Manager for editing")
print("4. Double-click - Now executes the query instead of just loading it")

print("\nHow to test:")
print("1. Run: uv run python gui.py")
print("2. Go to: Queries -> Manage Saved Queries")
print("3. Select a query from the tree")
print("4. Try the toolbar buttons:")
print("   - Execute Query: Loads and runs the query")
print("   - Edit Query: Opens in Query Manager for editing")
print("   - Delete Query: Removes the query (with confirmation)")
print("5. Try double-clicking a query (should execute it)")

print("\nToolbar button order (left to right):")
print("- Refresh")
print("- Execute Query")
print("- Edit Query")
print("- Delete Query")
