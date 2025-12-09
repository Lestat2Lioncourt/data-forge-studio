"""
Test script to verify right-click context menu on database tables
"""
print("Right-Click Menu Test")
print("=" * 60)

# Test imports
try:
    import tkinter as tk
    from tkinter import ttk
    print("[OK] tkinter imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import tkinter: {e}")
    exit(1)

# Test database_manager module
try:
    from database_manager import DatabaseManager
    print("[OK] DatabaseManager imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import DatabaseManager: {e}")
    exit(1)

# Test config_db
try:
    from config_db import config_db
    connections = config_db.get_all_database_connections()
    print(f"[OK] Configuration database accessible: {len(connections)} connection(s) configured")
except Exception as e:
    print(f"[ERROR] Failed to access config_db: {e}")
    exit(1)

print("\n" + "=" * 60)
print("SUCCESS: All components loaded successfully!")
print("=" * 60)
print("\nTo test the right-click menu:")
print("1. Run: uv run python gui.py")
print("2. Go to: Database -> Query Manager")
print("3. Right-click on any table in the Database Explorer")
print("4. You should see a context menu with options:")
print("   - SELECT Top 100 rows")
print("   - SELECT Top 1000 rows")
print("   - SELECT Top 10000 rows")
print("   - SELECT ALL rows (no limit)")
print("   - COUNT(*) rows")
print("\nThese options will:")
print("- Create a query tab if needed (or use existing tab for same DB)")
print("- Insert the appropriate SELECT query")
print("- Execute the query automatically")
print("- Show results in the results grid")
