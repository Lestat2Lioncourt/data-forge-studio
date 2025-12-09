# Projects Feature Documentation

## Vue d'ensemble

La fonctionnalité Projets permet d'organiser les RootFolders et les Databases en groupes logiques pour faciliter la navigation et la gestion des ressources.

## Concepts clés

### Projet
Un projet regroupe :
- **Root Folders** : Répertoires de données à explorer
- **Databases** : Connexions aux bases de données
- **Queries** : Requêtes sauvegardées (fonctionnalité future)

### Relations Many-to-Many
- Une RootFolder peut appartenir à plusieurs projets
- Une Database peut être visible dans plusieurs projets
- Les modifications d'une ressource sont visibles dans tous les projets qui la contiennent

### Projet par défaut
- Un seul projet peut être marqué comme projet par défaut
- Au démarrage, le projet par défaut s'affiche déployé
- Les autres projets restent fermés

### "Tous les projets"
- Projet spécial affichant toutes les ressources
- Ne peut pas être supprimé
- Utile pour avoir une vue globale

## Architecture de la base de données

### Tables

#### `projects`
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_used_at TEXT
)
```

#### `project_file_roots` (Many-to-Many)
```sql
CREATE TABLE project_file_roots (
    project_id TEXT NOT NULL,
    file_root_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, file_root_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (file_root_id) REFERENCES file_roots(id) ON DELETE CASCADE
)
```

#### `project_databases` (Many-to-Many)
```sql
CREATE TABLE project_databases (
    project_id TEXT NOT NULL,
    database_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, database_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (database_id) REFERENCES database_connections(id) ON DELETE CASCADE
)
```

## Modules

### 1. `config_db.py` - Gestion base de données

**Classe ajoutée :**
```python
@dataclass
class Project:
    id: str
    name: str
    description: str
    is_default: bool = False
    created_at: str = None
    updated_at: str = None
    last_used_at: str = None
```

**Méthodes ajoutées :**
- `add_project(project: Project) -> bool`
- `get_project(project_id: str) -> Optional[Project]`
- `get_all_projects(sort_by_usage: bool) -> List[Project]`
- `update_project(project: Project) -> bool`
- `delete_project(project_id: str) -> bool`
- `set_default_project(project_id: str) -> bool`
- `get_default_project() -> Optional[Project]`
- `add_project_file_root(project_id: str, file_root_id: str) -> bool`
- `remove_project_file_root(project_id: str, file_root_id: str) -> bool`
- `get_project_file_roots(project_id: str) -> List[FileRoot]`
- `add_project_database(project_id: str, database_id: str) -> bool`
- `remove_project_database(project_id: str, database_id: str) -> bool`
- `get_project_databases(project_id: str) -> List[DatabaseConnection]`

### 2. `project_manager.py` - Interface de gestion

**Classes :**

#### `ProjectDialog`
Dialog pour créer ou éditer un projet :
- Nom du projet (obligatoire)
- Description
- Checkbox "Set as default project"

#### `ProjectManager`
Frame de gestion avec TreeView :
- Liste tous les projets
- Boutons : New, Edit, Delete, Set Default, Refresh
- Double-clic pour éditer
- Affichage : Name, Description, Default (✓), Created

**Fonction :**
- `show_project_manager(parent)` : Affiche la fenêtre de gestion

### 3. `data_explorer.py` - Navigation par projet

**Structure arborescente :**
```
📁 Tous les projets
   ├─ 📂 RootFolders
   │  ├─ 💾 Folder1
   │  └─ 💾 Folder2
   └─ 🗄️ Databases
      ├─ DB1
      └─ DB2

⭐ Projet Client A (par défaut - déployé)
   ├─ 📂 RootFolders
   │  └─ 💾 Folder1
   │      ├─ 📁 subfolder
   │      └─ 📄 file.csv
   └─ 🗄️ Databases
      └─ DB1

📁 Projet Client B (fermé)
```

**Fonctionnalités :**
- Affichage hiérarchique par projet
- Projet par défaut ouvert automatiquement
- Navigation dans les fichiers des RootFolders
- Affichage des bases de données rattachées

**Menu contextuel (clic droit) :**

Sur un RootFolder :
- **Rattacher à un projet...** - Ajoute le folder à un projet existant
- **Créer nouveau projet et rattacher** - Crée un projet et y ajoute le folder
- **Retirer du projet** - Retire le folder du projet (si dans un projet spécifique)

Sur une Database :
- **Rattacher à un projet...** - Ajoute la DB à un projet existant
- **Créer nouveau projet et rattacher** - Crée un projet et y ajoute la DB
- **Retirer du projet** - Retire la DB du projet (si dans un projet spécifique)

## Interface utilisateur

### Menu Data (gui.py)

```
Data
├── 📂 Data Explorer
├── ──────────────────
├── 📁 Manage Projects...      ← NOUVEAU
└── 💾 Manage Root Folders...
```

**Méthode ajoutée :**
```python
def _manage_projects(self):
    """Open Projects management window"""
    from .project_manager import show_project_manager
    show_project_manager(self.root)
```

## Workflows utilisateur

### 1. Créer un projet

**Méthode A : Via le menu**
1. Data → Manage Projects...
2. Cliquer sur "➕ New"
3. Remplir le formulaire :
   - Name : "Client A"
   - Description : "Projet pour le client A"
   - ☑ Set as default project (optionnel)
4. Cliquer sur "Save"

**Méthode B : Via le menu contextuel**
1. Data → Data Explorer
2. Clic droit sur un RootFolder ou Database
3. Choisir "Créer nouveau projet et rattacher"
4. Remplir le formulaire
5. La ressource est automatiquement rattachée

### 2. Rattacher une ressource à un projet

1. Data → Data Explorer
2. Clic droit sur un RootFolder ou Database
3. Choisir "Rattacher à un projet..."
4. Sélectionner le projet dans la liste
5. Cliquer sur "Attach"

### 3. Retirer une ressource d'un projet

1. Data → Data Explorer
2. Développer le projet concerné
3. Clic droit sur le RootFolder ou Database
4. Choisir "Retirer du projet"
5. Confirmer

### 4. Définir un projet par défaut

**Méthode A : Via le gestionnaire**
1. Data → Manage Projects...
2. Sélectionner le projet
3. Cliquer sur "⭐ Set Default"

**Méthode B : Lors de la création/édition**
1. Dans le ProjectDialog
2. Cocher "Set as default project"
3. Save

### 5. Naviguer dans un projet

1. Data → Data Explorer
2. Le projet par défaut est déjà ouvert
3. Développer les autres projets en cliquant sur ▶
4. Développer "📂 RootFolders" pour voir les dossiers
5. Développer "🗄️ Databases" pour voir les bases
6. Double-cliquer sur un fichier pour l'afficher

## Cas d'usage

### Cas 1 : Gestion multi-clients

Créez un projet par client :
- **Projet "Client A"** : Contient les RootFolders et DB du client A
- **Projet "Client B"** : Contient les RootFolders et DB du client B
- **Projet "Tous les projets"** : Vue globale pour les tâches transverses

### Cas 2 : Gestion par environnement

Organisez par environnement :
- **Projet "Production"** : Accès production
- **Projet "Staging"** : Tests pré-production
- **Projet "Development"** : Développement local

### Cas 3 : Partage de ressources

Une base de données peut être dans plusieurs projets :
- **Projet "Analytics"** : BD Analytics + BD Clients
- **Projet "CRM"** : BD Clients + BD Ventes
- BD Clients est visible dans les deux projets

## Avantages

### Organisation améliorée
- ✅ Regroupement logique des ressources
- ✅ Navigation simplifiée
- ✅ Séparation claire des contextes

### Flexibilité
- ✅ Relations many-to-many
- ✅ Pas de duplication de ressources
- ✅ Réutilisation des connexions

### Productivité
- ✅ Projet par défaut pour démarrage rapide
- ✅ Vue "Tous les projets" pour recherche globale
- ✅ Menu contextuel pour gestion rapide

### Évolutivité
- ✅ Structure préparée pour Jobs (planification)
- ✅ Structure préparée pour Queries (requêtes sauvegardées)
- ✅ Extensible à d'autres types de ressources

## Limitations actuelles

1. **Pas de hiérarchie de projets** : Les projets sont au même niveau
2. **Pas de tags/catégories** : Organisation uniquement par projet
3. **Pas de permissions** : Tous les projets sont accessibles
4. **Pas d'import/export** : Configuration manuelle uniquement

## Développements futurs

### Phase 2
- [ ] Import/Export de projets (JSON/YAML)
- [ ] Templates de projets
- [ ] Clonage de projets
- [ ] Recherche dans les projets

### Phase 3
- [ ] Tags et catégories
- [ ] Vues personnalisées
- [ ] Favoris
- [ ] Historique de navigation

### Phase 4
- [ ] Collaboration multi-utilisateurs
- [ ] Permissions par projet
- [ ] Synchronisation cloud

## Migration

### Depuis v2.0 (sans projets)

Toutes les ressources existantes (RootFolders, Databases) restent accessibles via "Tous les projets".

**Pas d'action requise** - La migration est transparente.

**Actions recommandées :**
1. Créer des projets selon vos besoins
2. Rattacher les ressources existantes aux projets
3. Définir un projet par défaut

## Tests

### Test 1 : Création de projet
```bash
uv run run.py
```
1. Data → Manage Projects...
2. Créer un projet "Test"
3. Vérifier qu'il apparaît dans la liste

### Test 2 : Projet par défaut
1. Créer 2 projets
2. Set "Projet A" as default
3. Redémarrer l'app
4. Vérifier que "Projet A" est ouvert par défaut

### Test 3 : Rattachement de ressources
1. Créer un projet
2. Clic droit sur un RootFolder
3. Rattacher au projet
4. Vérifier qu'il apparaît dans le projet

### Test 4 : Many-to-Many
1. Créer 2 projets
2. Rattacher la même DB aux 2 projets
3. Vérifier qu'elle apparaît dans les deux
4. Modifier un paramètre de la DB
5. Vérifier que le changement est visible partout

## Fichiers modifiés/créés

**Nouveaux fichiers :**
- `src/ui/project_manager.py` (270 lignes)
- `src/ui/data_explorer_backup.py` (backup avant refonte)
- `docs/PROJECTS_FEATURE.md` (ce fichier)

**Fichiers modifiés :**
- `src/database/config_db.py` - Ajout champ is_default, méthodes projets
- `src/ui/data_explorer.py` - Refonte complète pour affichage par projet
- `src/ui/gui.py` - Ajout menu "Manage Projects..."
- `src/ui/__init__.py` - Export ProjectManager et show_project_manager

## Support

Pour toute question ou problème :
1. Consulter cette documentation
2. Vérifier les logs : `logs/data_loader_YYYYMMDD_HHMMSS.log`
3. Ouvrir un ticket si nécessaire

---

**Version:** 2.1.0
**Date:** 2025-12-08
**Auteur:** Développé avec Claude Code
