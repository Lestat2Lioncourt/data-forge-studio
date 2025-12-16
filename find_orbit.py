"""Script pour trouver la connexion ORBIT_DL"""
import sqlite3
import os

db_paths = [
    r'APP_SOURCE\src\database\_AppConfig\configuration.db',
    r'_AppConfig\config.db',
    r'_AppConfig\configuration.db',
    r'src\_AppConfig\configuration.db'
]

for db_path in db_paths:
    print(f"\nChecking: {db_path}")

    if not os.path.exists(db_path):
        print("  -> Does not exist")
        continue

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='database_connections'")
        if not cursor.fetchone():
            print("  -> No database_connections table")
            conn.close()
            continue

        # Search for ORBIT_DL
        cursor.execute("SELECT * FROM database_connections WHERE name LIKE '%ORBIT%' OR id LIKE '%777d23b2%'")
        results = cursor.fetchall()

        if results:
            print(f"  -> FOUND! {len(results)} matching row(s)")
            for row in results:
                print(f"     ID: {row[0]}")
                print(f"     Name: {row[1]}")
                print(f"     Type: {row[2]}")
                print(f"     Connection: {row[3]}")
        else:
            print("  -> Not found")

        # Also show all connections
        cursor.execute("SELECT id, name, db_type FROM database_connections")
        all_conns = cursor.fetchall()
        print(f"  -> Total connections: {len(all_conns)}")
        for conn_row in all_conns:
            print(f"     - {conn_row[1]} ({conn_row[2]})")

        conn.close()

    except Exception as e:
        print(f"  -> Error: {e}")
