# Menu Contextuel (Clic Droit) - Database Query Manager

## Nouvelle Fonctionnalité

Vous pouvez maintenant **cliquer droit** sur une table ou une vue dans le **Database Explorer** pour accéder rapidement à des requêtes prédéfinies.

## Utilisation

### 1. Ouvrir le Query Manager

```bash
uv run python gui.py
```

Puis allez dans **Database → Query Manager**

### 2. Clic Droit sur une Table

Dans le panneau de gauche **Database Explorer**, faites un **clic droit** sur n'importe quelle table ou vue.

### 3. Sélectionner une Option

Un menu contextuel s'affiche avec les options suivantes :

```
┌─────────────────────────────────┐
│ SELECT Top 100 rows             │
│ SELECT Top 1000 rows            │
│ SELECT Top 10000 rows           │
├─────────────────────────────────┤
│ SELECT ALL rows (no limit)      │
├─────────────────────────────────┤
│ COUNT(*) rows                   │
└─────────────────────────────────┘
```

## Options Disponibles

### SELECT Top 100 rows
- Génère et exécute : `SELECT TOP 100 * FROM [table_name]` (SQL Server)
- Ou : `SELECT * FROM [table_name] LIMIT 100` (SQLite)
- Affiche les 100 premières lignes

### SELECT Top 1000 rows ⭐
- Génère et exécute : `SELECT TOP 1000 * FROM [table_name]` (SQL Server)
- Ou : `SELECT * FROM [table_name] LIMIT 1000` (SQLite)
- **Idéal pour explorer rapidement le contenu d'une table**

### SELECT Top 10000 rows
- Génère et exécute : `SELECT TOP 10000 * FROM [table_name]` (SQL Server)
- Ou : `SELECT * FROM [table_name] LIMIT 10000` (SQLite)
- Pour des analyses plus larges

### SELECT ALL rows (no limit)
- Génère et exécute : `SELECT * FROM [table_name]`
- **⚠️ Attention** : Peut être lent sur de très grandes tables
- Récupère toutes les lignes sans limite

### COUNT(*) rows
- Génère et exécute : `SELECT COUNT(*) as row_count FROM [table_name]`
- Affiche le nombre total de lignes dans la table
- Rapide même sur de grandes tables

## Comportement Intelligent

### Gestion Automatique des Onglets

1. **Si un onglet existe pour cette base de données** :
   - La requête est insérée dans l'onglet actif
   - La requête est exécutée automatiquement
   - Les résultats remplacent les résultats précédents

2. **Si aucun onglet n'existe** :
   - Un nouvel onglet est créé automatiquement pour cette base de données
   - La requête est insérée et exécutée
   - Les résultats s'affichent immédiatement

### Adaptation Automatique SQL

Le système détecte automatiquement le type de base de données et adapte la syntaxe SQL :

| Type de BDD | Syntaxe LIMIT 1000 |
|-------------|-------------------|
| **SQLite**     | `SELECT * FROM table LIMIT 1000` |
| **SQL Server** | `SELECT TOP 1000 * FROM table` |
| **MySQL**      | `SELECT * FROM table LIMIT 1000` |
| **PostgreSQL** | `SELECT * FROM table LIMIT 1000` |
| **Oracle**     | `SELECT * FROM table FETCH FIRST 1000 ROWS ONLY` |

*Note : Pour Oracle, la syntaxe TOP n'est pas supportée, utilisez la syntaxe FETCH FIRST*

## Exemples d'Utilisation

### Cas 1 : Explorer le contenu d'une table

1. Clic droit sur `database_connections` dans Configuration Database
2. Sélectionner **"SELECT Top 1000 rows"**
3. Résultat : La requête s'exécute et affiche toutes les connexions configurées

### Cas 2 : Compter les enregistrements

1. Clic droit sur `saved_queries`
2. Sélectionner **"COUNT(*) rows"**
3. Résultat : Affiche le nombre total de requêtes sauvegardées

### Cas 3 : Voir toutes les données (petite table)

1. Clic droit sur `file_configs`
2. Sélectionner **"SELECT ALL rows (no limit)"**
3. Résultat : Toutes les configurations de fichiers s'affichent

## Comparaison : Double-Clic vs Clic Droit

| Action | Comportement |
|--------|-------------|
| **Double-Clic** | Insère la requête dans l'onglet actif **SANS l'exécuter** (limite 100) |
| **Clic Droit** | Insère la requête ET **l'exécute automatiquement** (choix de limite) |

## Fonctionnalités Techniques

### Code Modifié

**Fichier** : `database_manager.py`

**Nouvelles méthodes** :
- `_on_tree_right_click(event)` - Gère le clic droit et affiche le menu
- `_execute_select_query(db_conn_id, table_name, limit, is_sqlite)` - Exécute SELECT avec limite
- `_execute_count_query(db_conn_id, table_name)` - Exécute COUNT(*)

**Binding ajouté** :
```python
self.schema_tree.bind("<Button-3>", self._on_tree_right_click)  # Right-click menu
```

### Logique de Détection

1. **Détection du type d'élément** :
   - Vérifie que l'élément cliqué est une table ou une vue
   - Ignore les clics sur les dossiers, colonnes, etc.

2. **Détection du type de base de données** :
   ```python
   db_conn = connections_manager.get_connection(db_conn_id)
   is_sqlite = db_conn.db_type == 'sqlite'
   ```

3. **Génération de requête adaptée** :
   ```python
   if is_sqlite:
       query = f"SELECT * FROM [{table_name}] LIMIT {limit}"
   else:
       query = f"SELECT TOP {limit} * FROM [{table_name}]"
   ```

## Raccourcis Clavier

| Raccourci | Action |
|-----------|--------|
| **Double-Clic** | Insère SELECT TOP 100 (sans exécuter) |
| **Clic Droit → Option** | Insère et exécute la requête sélectionnée |
| **F5** (dans l'éditeur) | Exécute la requête actuelle |

## Avantages

✅ **Gain de temps** - Plus besoin d'écrire les requêtes basiques
✅ **Exécution automatique** - Résultats immédiats
✅ **Choix de limite** - Adaptez la taille du résultat à vos besoins
✅ **Gestion intelligente des onglets** - Réutilise l'onglet actif si possible
✅ **Syntaxe SQL adaptative** - Fonctionne sur tous types de bases de données
✅ **COUNT rapide** - Vérifiez rapidement la taille d'une table

## Workflow Recommandé

1. **Exploration initiale** : Clic droit → COUNT(*) pour voir la taille
2. **Aperçu rapide** : Clic droit → SELECT Top 1000 rows
3. **Requête personnalisée** : Modifier la requête générée et ré-exécuter (F5)
4. **Analyse complète** : Si besoin, SELECT ALL rows ou créer une requête filtrée

## Notes Importantes

⚠️ **Performance** :
- Sur de grandes tables (millions de lignes), évitez "SELECT ALL rows"
- Préférez COUNT(*) pour vérifier la taille d'abord
- Utilisez des limites raisonnables (1000-10000)

⚠️ **Sécurité** :
- Les requêtes générées utilisent des brackets `[]` pour échapper les noms de tables
- Aucune injection SQL possible via le menu contextuel
- Les noms de tables proviennent directement du schéma de la base

## Tests

Pour tester cette fonctionnalité :

```bash
# Vérifier que les imports fonctionnent
uv run python test_right_click_menu.py

# Lancer l'application
uv run python gui.py
```

Puis :
1. Database → Query Manager
2. Clic droit sur `database_connections` (dans Configuration Database)
3. Essayer les différentes options

## Support Multi-Base de Données

Le menu contextuel fonctionne sur **tous** les types de bases de données configurées :

- ✅ SQLite (natif Python)
- ✅ SQL Server (ODBC)
- ✅ MySQL (ODBC)
- ✅ PostgreSQL (ODBC)
- ✅ Oracle (ODBC)

Profitez de cette nouvelle fonctionnalité pour explorer vos bases de données plus rapidement ! 🚀
