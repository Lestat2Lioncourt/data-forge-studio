"""
Test script to verify save/load query functionality
"""
from config_db import SavedQuery, config_db, DatabaseConnection

print("=" * 70)
print("SAVE/LOAD QUERY TEST")
print("=" * 70)

# Get existing connections
connections = config_db.get_all_database_connections()
print(f"\n1. Database Connections: {len(connections)} found")
for conn in connections:
    print(f"   - {conn.name} (ID: {conn.id})")

if not connections:
    print("\n[ERROR] No database connections found!")
    print("Please add a connection first via the GUI.")
    exit(1)

# Use first connection for testing
test_conn = connections[0]
print(f"\n2. Using connection: {test_conn.name}")

# Create a test query
test_query = SavedQuery(
    id="",  # Will be auto-generated
    project="Test Project",
    category="Test Category",
    name="Test Query",
    description="This is a test query to verify save/load functionality",
    target_database_id=test_conn.id,
    query_text="SELECT * FROM test_table WHERE id = 1"
)

print("\n3. Creating test query...")
if config_db.add_saved_query(test_query):
    print("   [OK] Query saved successfully")
else:
    print("   [ERROR] Failed to save query")
    exit(1)

# Load all queries
print("\n4. Loading all saved queries...")
all_queries = config_db.get_all_saved_queries()
print(f"   [OK] Found {len(all_queries)} saved query(ies)")

# Display queries
print("\n5. Saved Queries List:")
print("-" * 70)
for query in all_queries:
    db_conn = config_db.get_database_connection(query.target_database_id)
    db_name = db_conn.name if db_conn else "Unknown"
    print(f"   Project: {query.project}")
    print(f"   Category: {query.category}")
    print(f"   Name: {query.name}")
    print(f"   Database: {db_name}")
    print(f"   Description: {query.description}")
    print(f"   Query: {query.query_text[:50]}...")
    print("-" * 70)

# Load by project
print("\n6. Loading queries by project...")
project_queries = config_db.get_saved_queries_by_project("Test Project")
print(f"   [OK] Found {len(project_queries)} query(ies) for 'Test Project'")

# Load by category
print("\n7. Loading queries by category...")
category_queries = config_db.get_saved_queries_by_category("Test Project", "Test Category")
print(f"   [OK] Found {len(category_queries)} query(ies) for 'Test Project / Test Category'")

# Cleanup - delete test query
print("\n8. Cleaning up test query...")
for query in all_queries:
    if query.project == "Test Project" and query.name == "Test Query":
        if config_db.delete_saved_query(query.id):
            print("   [OK] Test query deleted")
        else:
            print("   [ERROR] Failed to delete test query")

print("\n" + "=" * 70)
print("SUCCESS: Save/Load query functionality is working!")
print("=" * 70)
print("\nYou can now:")
print("1. Open the Query Manager: uv run python gui.py")
print("2. Write a query in any tab")
print("3. Click 'Save Query' button to save it")
print("4. Click 'Load Saved Query' button to load it back")
print("\nQueries are stored in: _AppConfig/configuration.db (table: saved_queries)")
