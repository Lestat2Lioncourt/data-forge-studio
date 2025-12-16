# Support Natif SQLite - Plus besoin de driver ODBC !

## Problème Résolu

Vous rencontriez une erreur "Connection Failed" sur la base de configuration car le **driver ODBC SQLite** n'était pas installé.

## Solution Implémentée

Le `database_manager.py` a été modifié pour **détecter automatiquement les bases SQLite** et utiliser le **module natif Python `sqlite3`** au lieu de `pyodbc`. Cela signifie :

- ✅ **Aucun driver ODBC nécessaire** pour SQLite
- ✅ **Connexion automatique** à la base de configuration
- ✅ **Support natif Python** (sqlite3 est inclus dans Python)
- ✅ **Fonctionnalité complète** : schéma, requêtes, exploration

## Changements Techniques

### 1. Détection du Type de Base de Données

```python
# Dans _load_all_connections()
if db_conn.db_type == 'sqlite':
    conn = self._connect_sqlite(db_conn.connection_string)
else:
    conn = pyodbc.connect(db_conn.connection_string)
```

### 2. Extraction du Chemin SQLite

```python
def _connect_sqlite(self, connection_string: str) -> sqlite3.Connection:
    # Extrait le chemin depuis: DRIVER={SQLite3 ODBC Driver};Database=path
    match = re.search(r'Database=([^;]+)', connection_string, re.IGNORECASE)
    db_path = match.group(1).strip()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

### 3. Requêtes Adaptées pour SQLite

**Tables:**
```python
# SQLite
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name

# Autres BDD
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'
```

**Colonnes:**
```python
# SQLite
PRAGMA table_info([table_name])

# Autres BDD
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?
```

**Requêtes avec limite:**
```python
# SQLite
SELECT * FROM [table_name] LIMIT 100

# SQL Server
SELECT TOP 100 * FROM [table_name]
```

## Test de Connexion

Utilisez le script de test pour vérifier que tout fonctionne :

```bash
uv run python test_config_db_connection.py
```

**Résultat attendu:**
```
============================================================
Testing Configuration Database Connection
============================================================

[OK] Connection found: Configuration Database
     Type: sqlite
     Connection String: DRIVER={SQLite3 ODBC Driver};Database=D:\DEV\Python\Load_Data_Lake\_AppConfig\configuration.db

[OK] Extracted path: D:\DEV\Python\Load_Data_Lake\_AppConfig\configuration.db
     File exists: True

[OK] Connected successfully!
     Tables: database_connections, file_configs, saved_queries
     Database connections configured: 1
     Saved queries: 0
     File configs: 0

[OK] Database Connections:
     - Configuration Database (sqlite) - Application configuration database (self-reference)

============================================================
SUCCESS: Configuration database is ready to use!
============================================================
```

## Utilisation

### Dans le Query Manager

1. Lancez l'application : `uv run python gui.py`
2. Menu **Database → Query Manager**
3. La base **"📁 Configuration Database"** apparaît dans l'explorateur à gauche
4. Double-cliquez sur une table pour générer une requête
5. Créez un nouvel onglet de requête et sélectionnez la base de configuration
6. Exécutez vos requêtes SQL normalement

### Requêtes Utiles

```sql
-- Voir toutes les connexions configurées
SELECT name, db_type, description
FROM database_connections
ORDER BY name;

-- Voir les requêtes sauvegardées
SELECT project, category, name, description
FROM saved_queries
ORDER BY project, category, name;

-- Compter les requêtes par projet
SELECT project, COUNT(*) as count
FROM saved_queries
GROUP BY project;

-- Voir les fichiers configurés
SELECT name, location, description
FROM file_configs
ORDER BY name;
```

## Support Multi-Base de Données

Le `database_manager.py` supporte maintenant **deux modes de connexion** :

| Type de BDD | Méthode de Connexion | Besoin Driver ODBC |
|-------------|---------------------|-------------------|
| SQLite      | `sqlite3.connect()` | ❌ Non            |
| SQL Server  | `pyodbc.connect()`  | ✅ Oui (ODBC Driver 17) |
| MySQL       | `pyodbc.connect()`  | ✅ Oui (MySQL ODBC Driver) |
| PostgreSQL  | `pyodbc.connect()`  | ✅ Oui (PostgreSQL ODBC Driver) |
| Oracle      | `pyodbc.connect()`  | ✅ Oui (Oracle ODBC Driver) |

## Dépendances Mises à Jour

Le `pyproject.toml` inclut maintenant :

```toml
dependencies = [
    "colorama>=0.4.6",
    "pandas>=2.3.3",
    "pyodbc>=5.3.0",
    "sqlalchemy>=2.0.44",
    "tabulate>=0.9.0",  # Ajouté pour query_config.py
]
```

## Scripts Disponibles

1. **test_config_db_connection.py** - Teste la connexion à la base de configuration
2. **query_config.py** - Interroge la base de configuration en ligne de commande

```bash
# Test complet
uv run python test_config_db_connection.py

# Consultation rapide
uv run python query_config.py
```

## Avantages

✅ **Pas d'installation externe** - sqlite3 est inclus dans Python
✅ **Portable** - Fonctionne sur Windows, Linux, macOS
✅ **Performances** - Accès direct sans couche ODBC
✅ **Simple** - Pas de configuration de drivers
✅ **Compatible** - Les autres types de BDD continuent d'utiliser ODBC

## Prochaines Étapes

La base de configuration est maintenant accessible ! Vous pouvez :

1. Ajouter d'autres connexions de bases de données via **Database → Manage Connections**
2. Créer des requêtes sauvegardées pour vos projets
3. Configurer des fichiers pour le Data Lake
4. Tout cela sera stocké dans la base SQLite portable

Profitez de votre Query Manager pleinement fonctionnel ! 🎉
