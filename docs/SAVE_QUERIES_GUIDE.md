# Guide : Sauvegarder et Charger des Requêtes SQL

## Nouvelle Fonctionnalité

Vous pouvez maintenant **sauvegarder vos requêtes SQL** dans la base de configuration pour les réutiliser plus tard !

## 📝 Sauvegarder une Requête

### 1. Écrire votre requête

Dans le **Query Manager**, écrivez votre requête SQL dans l'éditeur.

```sql
SELECT *
FROM database_connections
WHERE db_type = 'sqlite'
ORDER BY name
```

### 2. Cliquer sur "💾 Save Query"

Dans la toolbar de l'onglet de requête, cliquez sur le bouton **"💾 Save Query"**.

### 3. Remplir les informations

Une boîte de dialogue s'ouvre avec les champs suivants :

| Champ | Description | Exemple |
|-------|-------------|---------|
| **Project** | Nom du projet (obligatoire) | `Data Lake` |
| **Category** | Catégorie de la requête (obligatoire) | `Configuration` |
| **Query Name** | Nom descriptif (obligatoire) | `List SQLite Connections` |
| **Description** | Description détaillée (optionnel) | `Liste toutes les connexions SQLite configurées` |
| **Query** | Votre requête (en lecture seule) | `SELECT * FROM...` |

### 4. Enregistrer

Cliquez sur **"Save"** pour enregistrer la requête dans la base de configuration.

✅ **Succès !** Un message confirme que la requête a été sauvegardée.

## 📂 Charger une Requête Sauvegardée

### 1. Cliquer sur "📂 Load Saved Query"

Dans la toolbar principale du **Query Manager**, cliquez sur **"📂 Load Saved Query"**.

### 2. Sélectionner une requête

Une liste s'affiche avec toutes vos requêtes sauvegardées :

```
┌─────────────┬──────────────┬────────────────────┬──────────────┬─────────────────┐
│ Project     │ Category     │ Name               │ Database     │ Description     │
├─────────────┼──────────────┼────────────────────┼──────────────┼─────────────────┤
│ Data Lake   │ Config       │ List SQLite Conns  │ Config DB    │ Liste toutes... │
│ ORBIT_DL    │ Reports      │ Monthly Stats      │ ORBIT_DL     │ Statistiques... │
│ ORBIT_DL    │ Data Quality │ Check Duplicates   │ ORBIT_DL     │ Vérifie les ... │
└─────────────┴──────────────┴────────────────────┴──────────────┴─────────────────┘
```

### 3. Charger

**Double-cliquez** sur une requête ou sélectionnez-la et cliquez sur **"Load Query"**.

✅ **Résultat** :
- Un nouvel onglet est créé pour la base de données cible
- La requête est insérée dans l'éditeur
- L'onglet est renommé : `Project/Category/Name`
- Vous pouvez exécuter la requête avec **F5**

## 🗂️ Organisation des Requêtes

### Hiérarchie Recommandée

```
Project (ex: "Data Lake", "ORBIT_DL")
  └─ Category (ex: "Reports", "Data Quality", "Monitoring")
      └─ Query Name (ex: "Monthly Stats", "Check Duplicates")
```

### Exemples de Structure

**Projet : Data Lake**
- Category: **Configuration**
  - `List All Connections`
  - `Count Saved Queries by Project`
  - `Find Unused Connections`
- Category: **File Management**
  - `List File Configs`
  - `Check Missing Files`

**Projet : ORBIT_DL**
- Category: **Reports**
  - `Monthly Statistics`
  - `User Activity Report`
- Category: **Data Quality**
  - `Check Duplicates`
  - `Validate Foreign Keys`
  - `Find Orphaned Records`
- Category: **Monitoring**
  - `Table Row Counts`
  - `Database Size`

## 💾 Stockage des Requêtes

### Base de Données

Les requêtes sont stockées dans la table `saved_queries` de la base de configuration SQLite :

```
D:\DEV\Python\Load_Data_Lake\_AppConfig\configuration.db
```

### Schéma

```sql
CREATE TABLE saved_queries (
    id TEXT PRIMARY KEY,              -- UUID auto-généré
    project TEXT NOT NULL,            -- Nom du projet
    category TEXT NOT NULL,           -- Catégorie
    name TEXT NOT NULL,               -- Nom de la requête
    description TEXT,                 -- Description
    target_database_id TEXT NOT NULL, -- ID de la base cible (FK)
    query_text TEXT NOT NULL,         -- Texte SQL
    created_at TEXT NOT NULL,         -- Date de création
    updated_at TEXT NOT NULL,         -- Date de modification
    FOREIGN KEY (target_database_id) REFERENCES database_connections(id)
)
```

### Requêtes Utiles

**Lister toutes les requêtes sauvegardées :**
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

**Compter les requêtes par projet :**
```sql
SELECT
    project,
    COUNT(*) as query_count,
    COUNT(DISTINCT category) as category_count
FROM saved_queries
GROUP BY project
ORDER BY query_count DESC;
```

**Rechercher une requête par mot-clé :**
```sql
SELECT project, category, name, description
FROM saved_queries
WHERE query_text LIKE '%SELECT%'
   OR name LIKE '%monthly%'
ORDER BY project, category;
```

## 🎯 Cas d'Usage

### 1. Requêtes Récurrentes

Sauvegardez les requêtes que vous exécutez régulièrement :
- Rapports mensuels
- Vérifications de qualité de données
- Monitoring de performance

### 2. Requêtes Complexes

Conservez vos requêtes SQL complexes pour ne pas les réécrire :
- Jointures multiples
- CTEs (Common Table Expressions)
- Requêtes d'analyse

### 3. Documentation Vivante

Utilisez les requêtes sauvegardées comme documentation :
- Description détaillée de ce que fait la requête
- Organisation par projet et catégorie
- Historique des modifications (created_at, updated_at)

### 4. Partage d'Équipe

Exportez et importez la base de configuration pour partager vos requêtes :

```bash
# Copier la base de configuration
cp _AppConfig/configuration.db _AppConfig/configuration_backup.db

# Ou exporter en JSON
uv run python -c "
from config_db import config_db
import json

queries = config_db.get_all_saved_queries()
with open('saved_queries_export.json', 'w') as f:
    json.dump([{
        'project': q.project,
        'category': q.category,
        'name': q.name,
        'description': q.description,
        'query_text': q.query_text
    } for q in queries], f, indent=2)
"
```

## ⚡ Raccourcis et Astuces

### Raccourcis Clavier

| Action | Raccourci |
|--------|-----------|
| Exécuter la requête | **F5** |
| Sauvegarder la requête | (via bouton "💾 Save Query") |
| Charger une requête | (via bouton "📂 Load Saved Query") |

### Workflow Recommandé

1. **Tester** : Écrivez et testez votre requête dans un onglet
2. **Sauvegarder** : Une fois validée, sauvegardez-la avec des métadonnées claires
3. **Réutiliser** : Chargez la requête quand vous en avez besoin
4. **Modifier** : Chargez, modifiez, et sauvegardez à nouveau (même nom = version mise à jour)

### Bonnes Pratiques

✅ **DO:**
- Utilisez des noms descriptifs pour vos requêtes
- Organisez par projet et catégorie
- Ajoutez des descriptions détaillées
- Testez la requête avant de sauvegarder

❌ **DON'T:**
- Ne sauvegardez pas de requêtes temporaires/test
- Évitez les noms génériques comme "Query1", "Test"
- Ne laissez pas la description vide pour des requêtes complexes

## 🔧 API Programmatique

### Sauvegarder une Requête via Python

```python
from config_db import SavedQuery, config_db

# Créer une requête
query = SavedQuery(
    id="",  # Auto-généré
    project="Data Lake",
    category="Reports",
    name="Monthly Statistics",
    description="Rapport mensuel des statistiques",
    target_database_id="your-database-id",
    query_text="SELECT * FROM stats WHERE month = MONTH(GETDATE())"
)

# Sauvegarder
config_db.add_saved_query(query)
```

### Charger toutes les Requêtes

```python
from config_db import config_db

# Toutes les requêtes
all_queries = config_db.get_all_saved_queries()

# Par projet
project_queries = config_db.get_saved_queries_by_project("Data Lake")

# Par catégorie
category_queries = config_db.get_saved_queries_by_category("Data Lake", "Reports")
```

## 📊 Statistiques

Consultez vos statistiques de requêtes :

```sql
-- Requêtes les plus récentes
SELECT name, project, category, datetime(updated_at) as last_update
FROM saved_queries
ORDER BY updated_at DESC
LIMIT 10;

-- Bases de données les plus utilisées
SELECT dc.name, COUNT(*) as query_count
FROM saved_queries sq
JOIN database_connections dc ON sq.target_database_id = dc.id
GROUP BY dc.name
ORDER BY query_count DESC;

-- Projets actifs
SELECT
    project,
    COUNT(*) as total_queries,
    MAX(datetime(updated_at)) as last_activity
FROM saved_queries
GROUP BY project
ORDER BY last_activity DESC;
```

## 🎉 Profitez !

Vous pouvez maintenant :
- ✅ Sauvegarder vos requêtes SQL
- ✅ Les organiser par projet et catégorie
- ✅ Les charger en un clic
- ✅ Les partager avec votre équipe
- ✅ Construire une bibliothèque de requêtes réutilisables

Pour toute question, consultez la documentation ou les logs dans `_AppLogs/`.
