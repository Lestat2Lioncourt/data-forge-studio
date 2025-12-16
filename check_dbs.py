"""Script pour vérifier toutes les bases de données configuration.db"""
import sqlite3
import os

db_paths = [
    r'APP_SOURCE\src\database\_AppConfig\configuration.db',
    r'_AppConfig\config.db',
    r'_AppConfig\configuration.db',
    r'src\_AppConfig\configuration.db'
]

for db_path in db_paths:
    print(f"\n{'='*60}")
    print(f"DB: {db_path}")
    print(f"{'='*60}")

    if not os.path.exists(db_path):
        print("File does not exist")
        continue

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # List tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {tables}")

        # Check database_connections table
        if 'database_connections' in tables:
            cursor.execute("SELECT COUNT(*) FROM database_connections")
            count = cursor.fetchone()[0]
            print(f"\nDatabase connections: {count}")

            if count > 0:
                cursor.execute("SELECT id, name, db_type FROM database_connections")
                for i, row in enumerate(cursor.fetchall(), 1):
                    print(f"  {i}. {row[1]} ({row[2]}) - ID: {row[0]}")

        # Check saved_queries table
        if 'saved_queries' in tables:
            cursor.execute("SELECT COUNT(*) FROM saved_queries")
            count = cursor.fetchone()[0]
            print(f"\nSaved queries: {count}")

        # Check scripts table
        if 'scripts' in tables:
            cursor.execute("SELECT COUNT(*) FROM scripts")
            count = cursor.fetchone()[0]
            print(f"\nScripts: {count}")

        # Check jobs table
        if 'jobs' in tables:
            cursor.execute("SELECT COUNT(*) FROM jobs")
            count = cursor.fetchone()[0]
            print(f"\nJobs: {count}")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")
