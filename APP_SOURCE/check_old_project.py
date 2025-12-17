"""Vérifier l'ancien projet Load_Data_Lake"""
from pathlib import Path
import sqlite3

old_project = Path(r'D:\DEV\Python\Load_Data_Lake')

print(f"Ancien projet: {old_project}")
print(f"Existe: {old_project.exists()}")

if old_project.exists():
    print(f"Est un dossier: {old_project.is_dir()}")

    # Chercher tous les .db
    db_files = list(old_project.rglob('*.db'))
    print(f"\nFichiers .db trouves: {len(db_files)}")

    for db_file in db_files:
        print(f"\n{'='*60}")
        print(f"DB: {db_file}")
        print(f"Taille: {db_file.stat().st_size} bytes")

        try:
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='database_connections'")
            if cursor.fetchone():
                cursor.execute("SELECT id, name, db_type FROM database_connections")
                connections = cursor.fetchall()
                print(f"Connexions: {len(connections)}")
                for i, (conn_id, name, db_type) in enumerate(connections, 1):
                    print(f"  {i}. {name} ({db_type}) - ID: {conn_id}")

            conn.close()
        except Exception as e:
            print(f"Erreur: {e}")
else:
    print("\nL'ancien projet n'existe pas a cet emplacement!")
    print("Verifiez le chemin correct.")
