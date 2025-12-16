"""Chercher ORBIT_DL dans toutes les bases possibles"""
import sqlite3
from pathlib import Path
import os

# Tous les chemins possibles de bases de données
possible_paths = [
    Path(r'D:\DEV\Python\data-forge-studio\APP_SOURCE\_AppConfig\configuration.db'),
    Path(r'D:\DEV\Python\data-forge-studio\APP_SOURCE\src\database\_AppConfig\configuration.db'),
    Path(r'D:\DEV\Python\data-forge-studio\_AppConfig\configuration.db'),
    Path(r'D:\DEV\Python\data-forge-studio\src\_AppConfig\configuration.db'),
]

# Chercher aussi dans le dossier courant et parent
current_dir = Path(__file__).parent
possible_paths.append(current_dir / 'APP_SOURCE' / '_AppConfig' / 'configuration.db')
possible_paths.append(current_dir.parent / '_AppConfig' / 'configuration.db')

print("RECHERCHE DE ORBIT_DL DANS TOUTES LES BASES DE DONNEES")
print("="*70)

orbit_found = False

for db_path in possible_paths:
    if not db_path.exists():
        continue

    print(f"\nVérification: {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Vérifier si la table existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='database_connections'")
        if not cursor.fetchone():
            print("  -> Pas de table database_connections")
            conn.close()
            continue

        # Chercher toutes les connexions
        cursor.execute("SELECT id, name, db_type, connection_string FROM database_connections")
        connections = cursor.fetchall()

        print(f"  -> {len(connections)} connexion(s) trouvée(s)")

        for conn_id, name, db_type, conn_str in connections:
            print(f"     - {name} ({db_type})")
            if 'ORBIT' in name.upper() or 'ORBIT' in conn_str.upper():
                print(f"\n*** ORBIT_DL TROUVEE! ***")
                print(f"Fichier: {db_path}")
                print(f"ID: {conn_id}")
                print(f"Nom: {name}")
                print(f"Type: {db_type}")
                print(f"Connection string: {conn_str}")
                orbit_found = True

        conn.close()

    except Exception as e:
        print(f"  -> Erreur: {e}")

if not orbit_found:
    print("\n" + "="*70)
    print("ORBIT_DL NON TROUVEE dans aucune base de données!")
    print("\nPeut-être que:")
    print("1. La connexion est ajoutée dynamiquement au démarrage de l'app")
    print("2. Elle est stockée dans un fichier JSON")
    print("3. Elle est dans une base à un autre emplacement")
    print("\nCherchons des fichiers JSON...")

    # Chercher des fichiers JSON
    for root_path in [Path('APP_SOURCE'), Path('.')]:
        if root_path.exists():
            json_files = list(root_path.rglob('*connection*.json'))
            json_files.extend(list(root_path.rglob('*database*.json')))
            if json_files:
                print(f"\nFichiers JSON trouvés dans {root_path}:")
                for jf in json_files:
                    print(f"  - {jf}")
else:
    print("\n" + "="*70)
    print("ORBIT_DL TROUVEE!")
