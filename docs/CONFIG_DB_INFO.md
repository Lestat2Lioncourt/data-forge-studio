# Configuration Database (SQLite)

## Vue d'ensemble

La configuration de l'application est maintenant stockée dans une base de données SQLite au lieu de fichiers JSON. Cela permet de :
- Consulter la configuration directement dans l'éditeur de requêtes SQL
- Avoir une structure relationnelle cohérente
- Gérer facilement les requêtes sauvegardées avec leurs dépendances
- Exporter/importer facilement la configuration

## Emplacement

```
D:\DEV\Python\Load_Data_Lake\_AppConfig\configuration.db
```

La configuration est stockée dans le dossier de l'application pour la rendre **portable**. Vous pouvez copier tout le dossier de l'application sur un autre ordinateur et la configuration sera conservée.

## Structure de la base de données

### Table: `database_connections`

Stocke les connexions aux bases de données.

| Colonne | Type | Description |
|---------|------|-------------|
| id | TEXT | Identifiant unique (UUID) |
| name | TEXT | Nom de la connexion |
| db_type | TEXT | Type de BD (sqlserver, mysql, postgresql, oracle, sqlite, other) |
| description | TEXT | Description de la connexion |
| connection_string | TEXT | Chaîne de connexion |
| created_at | TEXT | Date de création (ISO format) |
| updated_at | TEXT | Date de dernière modification (ISO format) |

**Exemple de requête:**
```sql
SELECT id, name, db_type, description
FROM database_connections
ORDER BY name;
```

### Table: `file_configs`

Stocke les configurations de fichiers.

| Colonne | Type | Description |
|---------|------|-------------|
| id | TEXT | Identifiant unique (UUID) |
| name | TEXT | Nom du fichier/configuration |
| location | TEXT | Emplacement du fichier |
| description | TEXT | Description |
| created_at | TEXT | Date de création (ISO format) |
| updated_at | TEXT | Date de dernière modification (ISO format) |

**Exemple de requête:**
```sql
SELECT name, location, description
FROM file_configs
ORDER BY name;
```

### Table: `saved_queries`

Stocke les requêtes SQL sauvegardées.

| Colonne | Type | Description |
|---------|------|-------------|
| id | TEXT | Identifiant unique (UUID) |
| project | TEXT | Nom du projet |
| category | TEXT | Catégorie de la requête |
| name | TEXT | Nom de la requête |
| description | TEXT | Description |
| target_database_id | TEXT | ID de la base de données cible (FK) |
| query_text | TEXT | Texte de la requête SQL |
| created_at | TEXT | Date de création (ISO format) |
| updated_at | TEXT | Date de dernière modification (ISO format) |

**Exemple de requête:**
```sql
SELECT
    sq.project,
    sq.category,
    sq.name,
    dc.name as database_name,
    sq.description
FROM saved_queries sq
JOIN database_connections dc ON sq.target_database_id = dc.id
ORDER BY sq.project, sq.category, sq.name;
```

## Accès depuis l'application

### Via Python (API)

```python
from config_db import config_db, DatabaseConnection, FileConfig, SavedQuery

# Ajouter une connexion
conn = DatabaseConnection(
    id="",  # Sera généré automatiquement
    name="Ma Base de Données",
    db_type="sqlserver",
    description="Base de production",
    connection_string="DRIVER={...};SERVER=...;DATABASE=..."
)
config_db.add_database_connection(conn)

# Récupérer toutes les connexions
connections = config_db.get_all_database_connections()

# Ajouter une requête sauvegardée
query = SavedQuery(
    id="",
    project="Data Lake",
    category="Rapports",
    name="Statistiques mensuelles",
    description="Rapport des stats du mois",
    target_database_id=conn.id,
    query_text="SELECT * FROM monthly_stats WHERE month = ?"
)
config_db.add_saved_query(query)
```

### Via l'éditeur de requêtes

1. Ouvrir **Database → Query Manager**
2. Ajouter une connexion vers la base de configuration SQLite:
   - **Nom**: Configuration DB
   - **Type**: SQLite
   - **Connection String**:
     ```
     DRIVER={SQLite3 ODBC Driver};Database=D:\DEV\Python\Load_Data_Lake\_AppConfig\configuration.db
     ```
3. Exécuter des requêtes SQL directement sur la configuration

## Migration depuis JSON

Si vous aviez des connexions dans l'ancien format JSON (`database_connections.json`), elles seront automatiquement migrées vers SQLite au premier lancement. Le fichier JSON sera renommé en `.json.migrated` pour éviter une re-migration.

## Icônes des types de bases de données

- 🗄️ SQL Server (sqlserver)
- 🐬 MySQL (mysql)
- 🐘 PostgreSQL (postgresql)
- 🔶 Oracle (oracle)
- 📁 SQLite (sqlite)
- 💾 Other (other)

## Exemples de requêtes utiles

### Lister toutes les connexions avec leurs types

```sql
SELECT
    CASE db_type
        WHEN 'sqlserver' THEN '🗄️ SQL Server'
        WHEN 'mysql' THEN '🐬 MySQL'
        WHEN 'postgresql' THEN '🐘 PostgreSQL'
        WHEN 'oracle' THEN '🔶 Oracle'
        WHEN 'sqlite' THEN '📁 SQLite'
        ELSE '💾 Other'
    END as type,
    name,
    description,
    datetime(updated_at) as last_updated
FROM database_connections
ORDER BY name;
```

### Compter les requêtes par projet

```sql
SELECT
    project,
    COUNT(*) as query_count,
    COUNT(DISTINCT category) as category_count
FROM saved_queries
GROUP BY project
ORDER BY query_count DESC;
```

### Trouver les requêtes non utilisées récemment

```sql
SELECT
    name,
    project,
    category,
    datetime(updated_at) as last_modified,
    julianday('now') - julianday(updated_at) as days_since_update
FROM saved_queries
WHERE julianday('now') - julianday(updated_at) > 30
ORDER BY days_since_update DESC;
```

## Sauvegarde et restauration

### Sauvegarde
```bash
# Copier simplement le fichier SQLite
cp _AppConfig/configuration.db _AppConfig/configuration.db.backup
```

### Restauration
```bash
# Restaurer depuis une sauvegarde
cp _AppConfig/configuration.db.backup _AppConfig/configuration.db
```

### Portabilité
Pour rendre l'application portable:
1. Copiez tout le dossier `D:\DEV\Python\Load_Data_Lake\` vers un autre ordinateur
2. La configuration dans `_AppConfig\` sera automatiquement disponible
3. Les logs dans `_AppLogs\` seront également préservés

## Export/Import

### Export vers JSON
```python
import json
from config_db import config_db

connections = config_db.get_all_database_connections()
with open('connections_export.json', 'w') as f:
    json.dump([{
        'id': c.id,
        'name': c.name,
        'db_type': c.db_type,
        'description': c.description,
        'connection_string': c.connection_string
    } for c in connections], f, indent=2)
```

### Import depuis JSON
```python
from config_db import config_db
from pathlib import Path

json_file = Path('connections_export.json')
config_db.migrate_from_json(json_file)
```
