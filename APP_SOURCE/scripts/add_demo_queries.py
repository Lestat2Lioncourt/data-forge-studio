"""
Add demo queries to test the Queries Manager
"""
from config_db import SavedQuery, config_db

print("=" * 70)
print("ADDING DEMO QUERIES")
print("=" * 70)

# Get database connections
connections = config_db.get_all_database_connections()
if not connections:
    print("\n[ERROR] No database connections found!")
    print("Please add a database connection first.")
    exit(1)

print(f"\n1. Found {len(connections)} database connection(s):")
for conn in connections:
    print(f"   - {conn.name} (ID: {conn.id})")

# Use first connection for demo
demo_conn = connections[0]
print(f"\n2. Using '{demo_conn.name}' for demo queries")

# Demo queries to add
demo_queries = [
    {
        "project": "Data Lake",
        "category": "Configuration",
        "name": "List All Connections",
        "description": "Liste toutes les connexions de bases de données configurées",
        "query": "SELECT name, db_type, description FROM database_connections ORDER BY name"
    },
    {
        "project": "Data Lake",
        "category": "Configuration",
        "name": "Count Saved Queries",
        "description": "Compte le nombre de requêtes sauvegardées par projet",
        "query": "SELECT project, COUNT(*) as query_count FROM saved_queries GROUP BY project ORDER BY query_count DESC"
    },
    {
        "project": "Data Lake",
        "category": "Monitoring",
        "name": "Recent Queries",
        "description": "Affiche les 10 dernières requêtes modifiées",
        "query": "SELECT project, category, name, datetime(updated_at) as last_update FROM saved_queries ORDER BY updated_at DESC LIMIT 10"
    },
    {
        "project": "ORBIT_DL",
        "category": "Reports",
        "name": "Monthly Statistics",
        "description": "Rapport mensuel des statistiques (exemple)",
        "query": "-- Example query for ORBIT_DL\nSELECT \n    YEAR(date_field) as year,\n    MONTH(date_field) as month,\n    COUNT(*) as total_records\nFROM your_table\nWHERE date_field >= DATEADD(month, -12, GETDATE())\nGROUP BY YEAR(date_field), MONTH(date_field)\nORDER BY year DESC, month DESC"
    },
    {
        "project": "ORBIT_DL",
        "category": "Data Quality",
        "name": "Check Duplicates",
        "description": "Vérifie les doublons dans une table",
        "query": "-- Example duplicate check\nSELECT \n    column1,\n    column2,\n    COUNT(*) as duplicate_count\nFROM your_table\nGROUP BY column1, column2\nHAVING COUNT(*) > 1\nORDER BY duplicate_count DESC"
    }
]

print(f"\n3. Adding {len(demo_queries)} demo queries...")
added_count = 0
skipped_count = 0

for query_data in demo_queries:
    # Check if query already exists
    existing = config_db.get_saved_queries_by_category(
        query_data["project"],
        query_data["category"]
    )

    exists = any(q.name == query_data["name"] for q in existing)

    if exists:
        print(f"   [SKIP] {query_data['project']}/{query_data['category']}/{query_data['name']} - already exists")
        skipped_count += 1
        continue

    # Create query
    query = SavedQuery(
        id="",  # Auto-generated
        project=query_data["project"],
        category=query_data["category"],
        name=query_data["name"],
        description=query_data["description"],
        target_database_id=demo_conn.id,
        query_text=query_data["query"]
    )

    # Save
    if config_db.add_saved_query(query):
        print(f"   [OK] {query_data['project']}/{query_data['category']}/{query_data['name']}")
        added_count += 1
    else:
        print(f"   [ERROR] Failed to add {query_data['name']}")

print(f"\n4. Summary:")
print(f"   Added: {added_count}")
print(f"   Skipped (already exists): {skipped_count}")
print(f"   Total queries in database: {len(config_db.get_all_saved_queries())}")

print("\n" + "=" * 70)
print("SUCCESS: Demo queries added!")
print("=" * 70)

print("\nYou can now:")
print("1. Run: uv run python gui.py")
print("2. Go to: Queries -> Manage Saved Queries")
print("3. Explore the demo queries organized by Project and Category")
print("4. Double-click on a query to load it in Query Manager")
print("5. Edit or delete queries as needed")
