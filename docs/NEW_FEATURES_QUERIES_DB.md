# Nouvelles Fonctionnalités : Gestion de Requêtes et Connexions

## 📋 Vue d'Ensemble

Deux nouvelles fonctionnalités majeures ont été ajoutées :

1. **Menu contextuel sur les bases de données** - Clic droit sur une connexion dans le Query Manager
2. **Gestionnaire de requêtes** - Vue dédiée pour gérer toutes les requêtes sauvegardées

---

## 1️⃣ Menu Contextuel sur les Bases de Données

### Accès

Dans le **Database → Query Manager**, faites un **clic droit** sur le nom d'une base de données (nœud racine avec icône 🗄️/📁/🐬/etc.)

### Options Disponibles

```
┌─────────────────────────┐
│ Edit Connection         │
│ Test Connection         │
├─────────────────────────┤
│ Refresh Schema          │
└─────────────────────────┘
```

### Edit Connection

- Ouvre la boîte de dialogue d'édition
- Permet de modifier :
  - Nom de la connexion
  - Type de base de données
  - Description
  - Connection String
- Test de connexion intégré
- Sauvegarde automatique dans la base de configuration

**Exemple d'utilisation :**
1. Clic droit sur "ORBIT_DL"
2. Sélectionner "Edit Connection"
3. Modifier le nom → "ORBIT Data Lake"
4. Tester la connexion
5. Sauvegarder

### Test Connection

- Teste la connexion à la base de données
- Affiche un message de succès ou d'erreur
- Timeout de 5 secondes
- Fonctionne pour SQLite et ODBC

**Comportement :**
- ✅ **Succès** : "Connection to 'Database Name' successful!"
- ❌ **Échec** : Affiche le message d'erreur détaillé

### Refresh Schema

- Rafraîchit le schéma de la base de données sélectionnée
- Recharge :
  - Liste des tables
  - Liste des vues
  - Colonnes de chaque table/vue
- Utile après des modifications de structure

---

## 2️⃣ Gestionnaire de Requêtes (Queries Manager)

### Accès

**Menu : Queries → Manage Saved Queries**

### Interface

L'écran est divisé en deux parties :

```
┌────────────────────────────────┬──────────────────────────────────────┐
│  QUERIES TREE (left)           │  QUERY DETAILS (right)               │
│                                │                                      │
│  Project: Data Lake            │  Project: Data Lake                  │
│  ├─ Category: Reports          │  Category: Reports                   │
│  │  ├─ Monthly Stats [...]     │  Name: Monthly Statistics            │
│  │  └─ User Activity [...]     │  Database: ORBIT_DL                  │
│  └─ Category: Monitoring       │  Description: ...                    │
│     └─ Table Counts [...]      │                                      │
│                                │  Query:                              │
│  Project: ORBIT_DL             │  SELECT COUNT(*) ...                 │
│  ├─ Category: Data Quality     │                                      │
│  │  └─ Check Duplicates [...]  │                                      │
│  └─ ...                        │                                      │
└────────────────────────────────┴──────────────────────────────────────┘
```

### Organisation Hiérarchique

```
Project (ex: "Data Lake", "ORBIT_DL")
  └─ Category (ex: "Reports", "Data Quality", "Monitoring")
      └─ Query Name [Database Name]
```

### Fonctionnalités

#### Toolbar

| Bouton | Action |
|--------|--------|
| **Refresh** | Recharge toutes les requêtes depuis la base |
| **Delete Query** | Supprime la requête sélectionnée (avec confirmation) |
| **Edit Query** | Édite la requête sélectionnée |
| **Load in Query Manager** | Ouvre la requête dans le Query Manager |

#### Visualisation

- **Clic simple** : Affiche les détails de la requête à droite
- **Double-clic** : Charge la requête dans le Query Manager

#### Détails Affichés

- **Project** : Nom du projet (bleu)
- **Category** : Catégorie (bleu)
- **Name** : Nom de la requête (bleu)
- **Database** : Base de données cible (vert)
- **Description** : Description détaillée (zone de texte en lecture seule)
- **Query** : Texte SQL complet (zone de texte avec coloration syntaxique Consolas)

### Édition de Requête

Cliquez sur **"Edit Query"** pour modifier une requête sauvegardée.

**Champs modifiables :**
- Project
- Category
- Name
- Description
- Query Text (SQL)

**Notes :**
- Le champ **Database** n'est pas modifiable (créez une nouvelle requête pour une autre base)
- Tous les champs sont obligatoires sauf Description
- La sauvegarde met à jour automatiquement `updated_at`

### Suppression de Requête

1. Sélectionner une requête
2. Cliquer sur **"Delete Query"**
3. Confirmer la suppression
4. La requête est supprimée de la base de configuration

**Attention :** La suppression est définitive et ne peut pas être annulée.

### Chargement dans Query Manager

**Méthode 1 : Bouton**
1. Sélectionner une requête
2. Cliquer sur **"Load in Query Manager"**
3. L'application bascule vers le Query Manager
4. Un nouvel onglet est créé avec la requête chargée

**Méthode 2 : Double-clic**
1. Double-cliquer sur une requête
2. L'application bascule automatiquement vers le Query Manager
3. La requête est chargée dans un nouvel onglet

**Résultat :**
- Création d'un onglet pour la base de données cible
- Insertion du texte SQL dans l'éditeur
- Renommage de l'onglet : `Project/Category/Name`
- Requête prête à être exécutée (F5)

---

## 🎯 Cas d'Usage

### Scénario 1 : Organiser vos Requêtes

1. **Créer des requêtes** via le Query Manager (💾 Save Query)
2. **Visualiser** toutes vos requêtes dans le Queries Manager
3. **Organiser** par Project et Category
4. **Rechercher** facilement dans le TreeView

### Scénario 2 : Éditer une Connexion

1. Ouvrir le Query Manager
2. Clic droit sur la base de données
3. "Edit Connection"
4. Modifier les paramètres (ex: changer de serveur)
5. Tester la connexion
6. Sauvegarder

### Scénario 3 : Bibliothèque de Requêtes

1. Sauvegarder toutes vos requêtes fréquentes
2. Ouvrir le Queries Manager
3. Parcourir le TreeView par projet
4. Double-cliquer pour charger une requête
5. Exécuter et obtenir les résultats

### Scénario 4 : Maintenance des Connexions

1. Tester régulièrement vos connexions
2. Clic droit → "Test Connection"
3. Rafraîchir le schéma si des tables ont été ajoutées
4. Clic droit → "Refresh Schema"

---

## 🔧 Détails Techniques

### Menu Contextuel - Base de Données

**Fichier** : `database_manager.py`

**Méthode** : `_on_tree_right_click(event)`

**Détection du type de nœud :**
```python
if item_type == "database":
    # Show database context menu
    self._show_database_context_menu(event, db_conn_id)
elif item_type in ["table", "view"]:
    # Show table context menu
    self._show_table_context_menu(event, db_conn_id, item_type, table_name)
```

**Méthodes associées :**
- `_edit_database_connection(db_conn_id)` - Édite la connexion
- `_test_database_connection(db_conn_id)` - Teste la connexion
- `_refresh_database_schema(db_conn_id)` - Rafraîchit le schéma

### Queries Manager

**Fichier** : `queries_manager.py`

**Classe** : `QueriesManager(ttk.Frame)`

**Structure :**
```python
# Left panel: TreeView
queries_tree = ttk.Treeview(...)

# Right panel: Details
project_label, category_label, name_label, database_label
description_text (ScrolledText, read-only)
query_text (ScrolledText, read-only, Consolas font)

# Toolbar buttons
Refresh, Delete Query, Edit Query, Load in Query Manager
```

**Méthodes principales :**
- `_load_queries()` - Charge toutes les requêtes
- `_on_query_select(event)` - Gère la sélection
- `_show_query_details(query_id)` - Affiche les détails
- `_delete_query()` - Supprime une requête
- `_edit_query()` - Édite une requête
- `_load_in_query_manager()` - Charge dans le Query Manager

### Intégration avec GUI

**Fichier** : `gui.py`

**Menu ajouté :**
```python
# Queries menu
self.queries_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Queries", menu=self.queries_menu)
self.queries_menu.add_command(label="Manage Saved Queries", command=self._show_queries_frame)
```

**Méthodes ajoutées :**
- `_show_queries_frame()` - Affiche le Queries Manager
- `_show_database_frame_with_query(query)` - Charge une requête dans le Query Manager

---

## 📊 Base de Données

### Table : saved_queries

Les requêtes sont stockées dans `_AppConfig/configuration.db` :

```sql
SELECT
    sq.id,
    sq.project,
    sq.category,
    sq.name,
    dc.name as database_name,
    sq.description,
    sq.query_text,
    datetime(sq.created_at) as created,
    datetime(sq.updated_at) as updated
FROM saved_queries sq
JOIN database_connections dc ON sq.target_database_id = dc.id
ORDER BY sq.project, sq.category, sq.name;
```

### Requêtes Utiles

**Lister les requêtes par projet :**
```sql
SELECT project, COUNT(*) as count
FROM saved_queries
GROUP BY project
ORDER BY count DESC;
```

**Requêtes récemment modifiées :**
```sql
SELECT project, category, name, datetime(updated_at) as last_update
FROM saved_queries
ORDER BY updated_at DESC
LIMIT 10;
```

**Rechercher une requête :**
```sql
SELECT project, category, name
FROM saved_queries
WHERE query_text LIKE '%SELECT%COUNT%'
   OR name LIKE '%statistics%';
```

---

## 🎨 Interface Visuelle

### Queries Manager - Exemple

```
┌──────────────────────────────────────────────────────────────────────┐
│  Saved Queries Manager                                               │
├──────────────────────────────────────────────────────────────────────┤
│ [Refresh] [Delete Query] [Edit Query] [Load in Query Manager]       │
├──────────────────────────────────────────────────────────────────────┤
│                                    │                                 │
│  Queries Tree                      │  Query Details                  │
│                                    │                                 │
│  📁 Project: Data Lake             │  Project: Data Lake             │
│   ├─ 📂 Category: Configuration    │  Category: Configuration        │
│   │   └─ 📄 List Connections [..] │  Name: List SQLite Connections  │
│   └─ 📂 Category: Monitoring       │  Database: Configuration DB     │
│       └─ 📄 Table Sizes [...]      │                                 │
│                                    │  Description:                   │
│  📁 Project: ORBIT_DL               │  Liste toutes les connexions   │
│   ├─ 📂 Category: Reports          │  SQLite configurées dans ...   │
│   │   ├─ 📄 Monthly Stats [...]    │                                 │
│   │   └─ 📄 User Activity [...]    │  Query:                         │
│   └─ 📂 Category: Data Quality     │  ┌────────────────────────────┐│
│       └─ 📄 Check Dupes [...]      │  │ SELECT * FROM database_... ││
│                                    │  │ WHERE db_type = 'sqlite'   ││
│                                    │  │ ORDER BY name              ││
│                                    │  └────────────────────────────┘│
├──────────────────────────────────────────────────────────────────────┤
│ Ready                                                                │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⌨️ Raccourcis et Actions

| Action | Méthode |
|--------|---------|
| **Query Manager** | Database → Query Manager |
| **Clic droit sur DB** | Menu contextuel (Edit/Test/Refresh) |
| **Queries Manager** | Queries → Manage Saved Queries |
| **Voir détails** | Clic simple sur une requête |
| **Charger requête** | Double-clic ou bouton "Load in Query Manager" |
| **Éditer requête** | Bouton "Edit Query" |
| **Supprimer requête** | Bouton "Delete Query" |
| **Rafraîchir liste** | Bouton "Refresh" |

---

## ✅ Avantages

### Menu Contextuel Base de Données
- ✅ Édition rapide des connexions
- ✅ Test de connexion en un clic
- ✅ Rafraîchissement du schéma sans redémarrer
- ✅ Accès direct sans passer par "Manage Connections"

### Queries Manager
- ✅ Vue d'ensemble de toutes vos requêtes
- ✅ Organisation hiérarchique claire
- ✅ Recherche visuelle rapide dans le TreeView
- ✅ Édition en place sans passer par le Query Manager
- ✅ Suppression facile avec confirmation
- ✅ Chargement direct dans le Query Manager
- ✅ Interface similaire au Database Explorer (cohérence)

---

## 🚀 Workflow Recommandé

### 1. Créer et Organiser

1. Créer vos requêtes dans le Query Manager
2. Les sauvegarder avec Project/Category/Name cohérents
3. Visualiser la structure dans le Queries Manager

### 2. Maintenance

1. Ouvrir régulièrement le Queries Manager
2. Vérifier les requêtes obsolètes
3. Mettre à jour les descriptions
4. Supprimer les requêtes inutilisées

### 3. Utilisation Quotidienne

1. Ouvrir le Queries Manager
2. Parcourir le TreeView par projet
3. Double-cliquer pour charger
4. Exécuter dans le Query Manager

### 4. Gestion des Connexions

1. Tester régulièrement les connexions (clic droit)
2. Éditer si changement de serveur
3. Rafraîchir le schéma après modifications

---

## 📝 Notes Importantes

⚠️ **Édition de requête :**
- La base de données cible ne peut pas être modifiée
- Pour changer de base, créez une nouvelle requête

⚠️ **Suppression :**
- La suppression est définitive
- Aucun système d'annulation
- Confirmation obligatoire

⚠️ **Performance :**
- Le TreeView charge toutes les requêtes au démarrage
- Utilisez "Refresh" pour recharger après modifications externes

---

## 🎉 Profitez !

Vous disposez maintenant d'un système complet de gestion de requêtes avec :
- ✅ Sauvegarde facile depuis le Query Manager
- ✅ Gestion centralisée dans le Queries Manager
- ✅ Édition rapide des connexions
- ✅ Test de connexion en un clic
- ✅ Organisation hiérarchique
- ✅ Interface cohérente et intuitive

Pour toute question, consultez les logs dans `_AppLogs/` ou la documentation.
