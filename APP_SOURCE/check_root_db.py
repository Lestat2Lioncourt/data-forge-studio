"""Vérifier la base de données à la racine"""
import sqlite3
import os

db_path = r'_AppConfig\configuration.db'

print(f"Checking: {db_path}")
print(f"Full path: {os.path.abspath(db_path)}")
print(f"Exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, db_type, connection_string FROM database_connections")
    connections = cursor.fetchall()

    print(f"\nTotal connections: {len(connections)}")
    for i, row in enumerate(connections, 1):
        print(f"\n{i}. {row[1]} ({row[2]})")
        print(f"   ID: {row[0]}")
        print(f"   Connection: {row[3][:100]}...")

    conn.close()
