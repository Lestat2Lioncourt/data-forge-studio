"""Script pour ajouter la connexion ORBIT_DL à la base de données"""
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dataforge_studio.database.config_db import get_config_db
from datetime import datetime

# Récupérer l'instance de ConfigDatabase
config_db = get_config_db()

print("="*70)
print("AJOUT DE LA CONNEXION ORBIT_DL")
print("="*70)
print(f"Base de données: {config_db.db_path}")
print(f"Existe: {config_db.db_path.exists()}")

# Données de la connexion ORBIT_DL
orbit_data = {
    'id': '777d23b2-452a-440c-bbc7-1a668c54711e',
    'name': 'ORBIT_DL',
    'db_type': 'sqlserver',
    'description': 'SQL Server Database - ORBIT Data Lake',
    'connection_string': 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=ORBIT_DL;Trusted_Connection=yes;',
    'created_at': '2025-12-07T10:52:10.605911',
    'updated_at': '2025-12-07T10:52:10.605922'
}

print(f"\nConnexion à ajouter:")
print(f"  ID: {orbit_data['id']}")
print(f"  Nom: {orbit_data['name']}")
print(f"  Type: {orbit_data['db_type']}")
print(f"  Server: localhost")
print(f"  Database: ORBIT_DL")

# Verifier si la connexion existe deja
existing = config_db.get_all_database_connections()
orbit_exists = any(conn.id == orbit_data['id'] for conn in existing)

if orbit_exists:
    print(f"\nLa connexion ORBIT_DL existe deja!")
else:
    # Ajouter la connexion
    print(f"\nAjout de la connexion...")

    import sqlite3
    conn = sqlite3.connect(str(config_db.db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO database_connections
        (id, name, db_type, description, connection_string, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        orbit_data['id'],
        orbit_data['name'],
        orbit_data['db_type'],
        orbit_data['description'],
        orbit_data['connection_string'],
        orbit_data['created_at'],
        orbit_data['updated_at']
    ))

    conn.commit()
    conn.close()

    print(f"Connexion ORBIT_DL ajoutee avec succes!")

# Verifier
print(f"\n" + "="*70)
print("VERIFICATION")
print("="*70)

all_connections = config_db.get_all_database_connections()
print(f"Nombre total de connexions: {len(all_connections)}")

for i, conn in enumerate(all_connections, 1):
    print(f"\n{i}. {conn.name} ({conn.db_type})")
    print(f"   ID: {conn.id}")
    if conn.name == 'ORBIT_DL':
        print(f"   ORBIT_DL trouvee!")

print("\n" + "="*70)
print("TERMINE!")
print("Vous pouvez maintenant lancer l'application et voir ORBIT_DL dans DatabaseManager")
print("="*70)
