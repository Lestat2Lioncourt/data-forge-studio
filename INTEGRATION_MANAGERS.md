# Intégration des Managers - DataForge Studio v0.50

## ✅ Modifications effectuées

### 1. **main_window.py** - Menu de navigation complet

**Modifications:**
- Ajout des références aux 5 managers dans `__init__`
- Mise à jour de `set_frames()` pour accepter les managers en paramètres optionnels
- Mise à jour de `_switch_frame()` pour gérer la navigation vers les managers
- Ajout de "Data Explorer" dans le menu View avec séparateur

**Menu View actualisé:**
```
View
├── Data Lake
├── ──────────── (séparateur)
├── Database
├── Queries
├── Scripts
├── Jobs
└── Data Explorer
```

### 2. **main.py** - Création et injection des managers

**Modifications:**
- Import des 5 managers (QueriesManager, ScriptsManager, JobsManager, DatabaseManager, DataExplorer)
- Création des instances de managers au démarrage
- Injection des managers via `set_frames()`

**Ordre de création:**
1. DataLakeFrame
2. SettingsFrame
3. HelpFrame
4. QueriesManager
5. ScriptsManager
6. JobsManager
7. DatabaseManager
8. DataExplorer

### 3. **i18n_bridge.py** - Traductions complètes

**Nouvelles clés ajoutées (EN + FR):**

**Menu:**
- `menu_data_explorer` : "Data Explorer" / "Explorateur de Données"

**Status bar:**
- `status_viewing_database` : "Database Manager" / "Gestionnaire de Base de Données"
- `status_viewing_queries` : "Queries Manager" / "Gestionnaire de Requêtes"
- `status_viewing_scripts` : "Scripts Manager" / "Gestionnaire de Scripts"
- `status_viewing_jobs` : "Jobs Manager" / "Gestionnaire de Jobs"
- `status_viewing_data_explorer` : "Data Explorer" / "Explorateur de Données"

## 🎯 Navigation disponible

### Via le menu "View" (Affichage):

| Menu Item | Manager/Frame | Status Bar |
|-----------|--------------|------------|
| Data Lake | DataLakeFrame | "Viewing Data Lake" |
| **Database** | **DatabaseManager** | "Database Manager" |
| **Queries** | **QueriesManager** | "Queries Manager" |
| **Scripts** | **ScriptsManager** | "Scripts Manager" |
| **Jobs** | **JobsManager** | "Jobs Manager" |
| **Data Explorer** | **DataExplorer** | "Data Explorer" |
| Preferences (Settings) | SettingsFrame | "Viewing Settings" |
| Documentation (Help) | HelpFrame | "Viewing Help" |

## 🔄 Comportement

### Stacked Widget:
Tous les managers et frames sont ajoutés au `QStackedWidget` central:
- Position 0: DataLakeFrame (vue par défaut)
- Position 1: SettingsFrame
- Position 2: HelpFrame
- Position 3: DatabaseManager
- Position 4: QueriesManager
- Position 5: ScriptsManager
- Position 6: JobsManager
- Position 7: DataExplorer

### Switch de vue:
- Le menu "View" appelle `_switch_frame(nom)`
- `_switch_frame()` utilise `setCurrentWidget()` du QStackedWidget
- La status bar est mise à jour avec le message approprié
- Si un manager n'est pas initialisé (None), affiche "Ready"

## 📊 Structure finale

```
DataForgeMainWindow
├── Menu Bar
│   ├── File
│   ├── View ← Navigation vers tous les managers
│   ├── Settings
│   └── Help
│
├── Central Widget (QStackedWidget)
│   ├── DataLakeFrame
│   ├── SettingsFrame
│   ├── HelpFrame
│   ├── DatabaseManager ← NOUVEAU
│   ├── QueriesManager ← NOUVEAU
│   ├── ScriptsManager ← NOUVEAU
│   ├── JobsManager ← NOUVEAU
│   └── DataExplorer ← NOUVEAU
│
└── Status Bar (affiche le manager actif)
```

## 🧪 Test

### Lancer l'application:
```bash
uv run run.py
```

### Navigation:
1. L'application démarre sur "Data Lake"
2. Menu "View" → "Database" → Affiche le DatabaseManager
3. Menu "View" → "Queries" → Affiche le QueriesManager
4. Menu "View" → "Scripts" → Affiche le ScriptsManager
5. Menu "View" → "Jobs" → Affiche le JobsManager
6. Menu "View" → "Data Explorer" → Affiche le DataExplorer
7. Menu "Settings" → "Preferences" → Affiche SettingsFrame
8. Menu "Help" → "Documentation" → Affiche HelpFrame

### Vérifier:
- ✅ La status bar se met à jour pour chaque vue
- ✅ Le menu "View" affiche toutes les options
- ✅ La navigation fonctionne sans erreur
- ✅ Les managers affichent leurs données de placeholder
- ✅ Le changement de langue met à jour le menu

## 📝 Notes

### Placeholder data:
Tous les managers utilisent des données de placeholder (sample data) pour affichage immédiat:
- **QueriesManager**: 2 requêtes SQL exemples
- **ScriptsManager**: 2 scripts Python exemples
- **JobsManager**: 3 jobs (2 enabled, 1 disabled)
- **DatabaseManager**: 3 connexions placeholder
- **DataExplorer**: 2 projets avec arborescence de fichiers

### Prochaines étapes:
Pour connecter aux vraies données, il faudra:
1. Implémenter la couche database (`config_db.py`)
2. Remplacer les placeholder data par des appels à la DB
3. Implémenter les dialogues Add/Edit pour chaque manager
4. Implémenter l'exécution réelle (queries, scripts, jobs)

### Architecture:
Cette intégration respecte le principe **Open/Closed**:
- Les managers sont indépendants et réutilisables
- La MainWindow les accepte via injection de dépendances
- Facile d'ajouter de nouveaux managers sans modifier le cœur

---

**Créé le**: 2025-12-11
**Version**: DataForge Studio v0.50
**Phase**: 3 (Managers) - Complète avec intégration
