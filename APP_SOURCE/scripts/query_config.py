"""
Quick script to query the configuration database directly
"""
import sqlite3
from pathlib import Path
from tabulate import tabulate

# Connect to configuration database
# Navigate from src/core/ up to src/ to find _AppConfig
app_folder = Path(__file__).parent.parent
db_path = app_folder / "_AppConfig" / "configuration.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Query all database connections
cursor = conn.cursor()
cursor.execute("SELECT name, db_type, description FROM database_connections ORDER BY name")
rows = cursor.fetchall()

print("\n=== Database Connections ===")
headers = ["Name", "Type", "Description"]
data = [[row['name'], row['db_type'], row['description']] for row in rows]

try:
    print(tabulate(data, headers=headers, tablefmt='grid'))
except ImportError:
    # Fallback if tabulate not installed
    for row in rows:
        print(f"  - {row['name']} ({row['db_type']}): {row['description']}")

# Query saved queries count
cursor.execute("SELECT COUNT(*) as count FROM saved_queries")
query_count = cursor.fetchone()['count']
print(f"\nSaved Queries: {query_count}")

# Query file configs count
cursor.execute("SELECT COUNT(*) as count FROM file_configs")
file_count = cursor.fetchone()['count']
print(f"File Configs: {file_count}")

conn.close()
