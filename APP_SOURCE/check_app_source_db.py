"""Vérifier APP_SOURCE\_AppConfig\configuration.db en détail"""
import sqlite3
from pathlib import Path

# Tous les chemins possibles
db_paths = [
    r'APP_SOURCE\_AppConfig\configuration.db',
    r'APP_SOURCE\_AppConfig\configuration_db',
    r'APP_SOURCE\src\database\_AppConfig\configuration.db',
]

for db_path in db_paths:
    full_path = Path(db_path)
    print(f"\n{'='*70}")
    print(f"Chemin: {db_path}")
    print(f"Complet: {full_path.absolute()}")
    print(f"Existe: {full_path.exists()}")

    if not full_path.exists():
        continue

    print(f"Taille: {full_path.stat().st_size} bytes")

    try:
        conn = sqlite3.connect(str(full_path))
        cursor = conn.cursor()

        # Lister toutes les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {tables}")

        # Vérifier database_connections
        if 'database_connections' in tables:
            print(f"\n--- TABLE database_connections ---")
            cursor.execute("SELECT * FROM database_connections")
            connections = cursor.fetchall()
            print(f"Nombre total de connexions: {len(connections)}")

            if connections:
                # Afficher les colonnes
                cursor.execute("PRAGMA table_info(database_connections)")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"Colonnes: {columns}")

                # Afficher chaque connexion
                for i, conn_row in enumerate(connections, 1):
                    print(f"\n*** Connexion #{i} ***")
                    for col_name, value in zip(columns, conn_row):
                        if col_name == 'connection_string' and value and len(str(value)) > 100:
                            print(f"  {col_name}: {str(value)[:100]}...")
                        else:
                            print(f"  {col_name}: {value}")

        conn.close()

    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*70)
