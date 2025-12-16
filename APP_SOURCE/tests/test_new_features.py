"""
Test script for new features:
1. Right-click on database connection
2. Queries Manager
"""
print("=" * 70)
print("TESTING NEW FEATURES")
print("=" * 70)

# Test imports
print("\n1. Testing imports...")
try:
    from database_manager import DatabaseManager
    print("   [OK] DatabaseManager imported")
except Exception as e:
    print(f"   [ERROR] DatabaseManager import failed: {e}")
    exit(1)

try:
    from queries_manager import QueriesManager
    print("   [OK] QueriesManager imported")
except Exception as e:
    print(f"   [ERROR] QueriesManager import failed: {e}")
    exit(1)

try:
    from gui import DataLakeLoaderGUI
    print("   [OK] DataLakeLoaderGUI imported")
except Exception as e:
    print(f"   [ERROR] DataLakeLoaderGUI import failed: {e}")
    exit(1)

# Test configuration
print("\n2. Testing configuration...")
try:
    from config_db import config_db
    connections = config_db.get_all_database_connections()
    print(f"   [OK] {len(connections)} database connection(s) configured")

    queries = config_db.get_all_saved_queries()
    print(f"   [OK] {len(queries)} saved query(ies) found")
except Exception as e:
    print(f"   [ERROR] Configuration test failed: {e}")
    exit(1)

print("\n" + "=" * 70)
print("SUCCESS: All components loaded successfully!")
print("=" * 70)

print("\nNew Features Added:")
print("\n1. RIGHT-CLICK MENU ON DATABASE CONNECTION:")
print("   - In Query Manager, right-click on a database name (root node)")
print("   - Options available:")
print("     * Edit Connection")
print("     * Test Connection")
print("     * Refresh Schema")

print("\n2. QUERIES MENU:")
print("   - New menu: Queries -> Manage Saved Queries")
print("   - Opens a TreeView organized by Project > Category > Query")
print("   - Features:")
print("     * View all saved queries")
print("     * Delete query")
print("     * Edit query (Project, Category, Name, Description, Query Text)")
print("     * Load in Query Manager (double-click or button)")
print("     * TreeView structure similar to Database Explorer")

print("\nTo test:")
print("1. Run: uv run python gui.py")
print("2. Go to: Database -> Query Manager")
print("3. Right-click on 'ORBIT_DL' or 'Configuration Database'")
print("4. Try 'Edit Connection' or 'Test Connection'")
print("\n5. Go to: Queries -> Manage Saved Queries")
print("6. Create/View/Edit/Delete saved queries")
print("7. Double-click on a query to load it in Query Manager")
