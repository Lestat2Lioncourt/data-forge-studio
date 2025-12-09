"""
Test script to verify configuration database connection
"""
from database_manager import DatabaseManager
from config_db import config_db
import sqlite3
import re
from pathlib import Path

def test_sqlite_connection():
    """Test SQLite connection logic"""
    print("=" * 60)
    print("Testing Configuration Database Connection")
    print("=" * 60)

    # Get the config database connection
    conn_config = config_db.get_database_connection('config-db-self-ref')
    if not conn_config:
        print("ERROR: Configuration database connection not found!")
        return False

    print(f"\n[OK] Connection found: {conn_config.name}")
    print(f"     Type: {conn_config.db_type}")
    print(f"     Connection String: {conn_config.connection_string}")

    # Test path extraction
    match = re.search(r'Database=([^;]+)', conn_config.connection_string, re.IGNORECASE)
    if not match:
        print("ERROR: Could not extract database path from connection string!")
        return False

    db_path = Path(match.group(1).strip())
    print(f"\n[OK] Extracted path: {db_path}")
    print(f"     File exists: {db_path.exists()}")

    if not db_path.exists():
        print("ERROR: Database file does not exist!")
        return False

    # Test native sqlite3 connection
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n[OK] Connected successfully!")
        print(f"     Tables: {', '.join(tables)}")

        # Get database connections count
        cursor.execute("SELECT COUNT(*) as count FROM database_connections")
        conn_count = cursor.fetchone()[0]
        print(f"     Database connections configured: {conn_count}")

        # Get saved queries count
        cursor.execute("SELECT COUNT(*) as count FROM saved_queries")
        query_count = cursor.fetchone()[0]
        print(f"     Saved queries: {query_count}")

        # Get file configs count
        cursor.execute("SELECT COUNT(*) as count FROM file_configs")
        file_count = cursor.fetchone()[0]
        print(f"     File configs: {file_count}")

        # List all connections
        cursor.execute("SELECT name, db_type, description FROM database_connections ORDER BY name")
        connections = cursor.fetchall()

        print(f"\n[OK] Database Connections:")
        for row in connections:
            print(f"     - {row[0]} ({row[1]}) - {row[2]}")

        conn.close()

        print("\n" + "=" * 60)
        print("SUCCESS: Configuration database is ready to use!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nERROR: Failed to connect: {e}")
        return False

if __name__ == "__main__":
    test_sqlite_connection()
