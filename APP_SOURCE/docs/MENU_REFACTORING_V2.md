# Menu Refactoring v2.0

## Vue d'ensemble

Refonte complète du menu de l'interface Data Lake Loader pour une meilleure organisation et navigation.

## Changements du Menu

### ❌ SUPPRIMÉ
- **Menu "File"** - Supprimé complètement (Exit déplacé vers Help)
- **Menu "Data Lake"** - Remplacé par "Data"

### ✅ NOUVEAU

#### 1. Menu **Data**
```
📂 Data Explorer          - Nouveau module de navigation dans les fichiers
────────────────────
💾 Manage Root Folders... - Gestion des répertoires racines
```

**Fonctionnalités Data Explorer:**
- Navigation arborescente dans les RootFolders configurés
- Affichage du contenu des fichiers (texte, CSV, JSON)
- Détection automatique de l'encodage (utf-8, latin-1, cp1252, iso-8859-1)
- Support des gros fichiers (avec limite configurable)
- Viewer de contenu avec coloration syntaxique basique

#### 2. Menu **Scripts**
```
📥 Dispatch Files         - Dispatch des fichiers
📤 Load to Database       - Chargement en base de données
```

**Fonctionnalités:**
- Exécution des scripts de traitement de données
- Dispatch automatique des fichiers dans les dossiers appropriés
- Chargement de données dans la base de données configurée

#### 3. Menu **Databases** (refactorisé)
```
🗄️ Query Manager         - Gestionnaire de requêtes multi-onglets
────────────────────
➕ New Connection...      - Nouvelle connexion base de données
⚙️ Manage Connections... - Gestion des connexions
```

#### 4. Menu **Queries** (simplifié)
```
📝 Manage Saved Queries   - Gestionnaire de requêtes sauvegardées
```

#### 5. Menu **Jobs** (nouveau, vide)
```
📋 Job Manager (Coming Soon)    [Désactivé]
────────────────────
⚙️ Configure Jobs... [Désactivé]
```
Ce menu est préparé pour les fonctionnalités futures de planification de tâches.

#### 6. Menu **Help** (amélioré)
```
📚 Documentation          - Viewer de documentation
────────────────────
About                     - À propos
────────────────────
Exit                      - Quitter l'application
```

## Nouveaux Modules

### 1. `data_explorer.py` (460 lignes)

Module complet pour explorer les données :

**Composants principaux:**
- `DataExplorer` - Frame principal avec arborescence et viewer
- Navigation par RootFolders
- Treeview hiérarchique avec icônes
- Viewer de contenu multi-format

**Formats supportés:**
- Fichiers texte (.txt, .log, .md, .py, .js, .sql, etc.)
- CSV/TSV avec détection de séparateur
- JSON avec formatage
- Binaires (info seulement)

**Fonctionnalités:**
- 🔄 Refresh - Recharger l'arborescence
- ⬆️ Up Level - Monter d'un niveau
- 🏠 Root - Retour au répertoire racine
- Sélection d'encodage (utf-8, latin-1, cp1252, iso-8859-1)
- Affichage taille des fichiers
- Limite à 10,000 lignes pour les gros fichiers

### 2. `file_root_manager.py` (déjà existant, 320 lignes)

Module de gestion des RootFolders :

**Fonctionnalités:**
- CRUD complet pour les RootFolders
- `FileRootDialog` - Dialog add/edit avec browse
- `FileRootManager` - Manager avec TreeView
- Création automatique de dossiers si inexistants
- Validation de chemins

## Modifications dans `gui.py`

### Imports ajoutés:
```python
from .data_explorer import DataExplorer
from .file_root_manager import show_file_root_manager
```

### Méthodes ajoutées:
```python
def _show_data_explorer(self)      # Afficher Data Explorer
def _manage_root_folders(self)     # Ouvrir gestionnaire RootFolders
```

### Configuration par défaut:
- Vue par défaut : **Data Explorer** (au lieu de Data Lake Frame)
- Taille fenêtre : `1200x800` (au lieu de 1000x750)
- Titre : `Data Lake Loader v2.0`

## Architecture

```
Menu Structure:
├── Data
│   ├── Data Explorer (Vue principale)
│   └── Manage Root Folders
├── Scripts
│   ├── Dispatch Files
│   └── Load to Database
├── Databases
│   ├── Query Manager
│   ├── New Connection
│   └── Manage Connections
├── Queries
│   └── Manage Saved Queries
├── Jobs
│   ├── Job Manager (disabled)
│   └── Configure Jobs (disabled)
└── Help
    ├── Documentation
    ├── About
    └── Exit
```

## Workflow Utilisateur

### 1. Configuration initiale:
1. **Data → Manage Root Folders** - Ajouter répertoires racines
2. **Databases → New Connection** - Configurer bases de données

### 2. Exploration de données:
1. **Data → Data Explorer** - Naviguer dans les fichiers
2. Sélectionner un RootFolder dans l'arborescence
3. Parcourir dossiers et fichiers
4. Double-cliquer pour afficher le contenu

### 3. Gestion des données:
1. **Scripts → Dispatch Files** - Organiser les fichiers
2. **Scripts → Load to Database** - Charger en BDD

### 4. Requêtes SQL:
1. **Databases → Query Manager** - Exécuter requêtes
2. **Queries → Manage Saved Queries** - Gérer requêtes sauvegardées

## Avantages de la Refonte

### Organisation améliorée:
- ✅ Séparation claire Data / Scripts / Databases / Queries
- ✅ Menu plus intuitif et logique
- ✅ Suppression du menu "File" redondant
- ✅ Regroupement des scripts de traitement dans menu dédié

### Nouvelles fonctionnalités:
- ✅ Data Explorer pour navigation fichiers
- ✅ Viewer de contenu multi-format
- ✅ Détection automatique d'encodage (utf-8, latin-1, cp1252, iso-8859-1)
- ✅ Gestion centralisée des RootFolders
- ✅ Menu Scripts pour opérations de traitement
- ✅ Structure Jobs préparée pour l'avenir

### Expérience utilisateur:
- ✅ Navigation plus rapide
- ✅ Accès direct aux fonctionnalités principales
- ✅ Icônes dans les menus pour meilleure lisibilité
- ✅ Vue par défaut pertinente (Data Explorer)

## Migration depuis v1.0

Aucune migration nécessaire - Toutes les fonctionnalités existantes sont conservées :
- Dispatch Files et Load to Database déplacés dans le menu Scripts
- Database Manager conserve toutes ses fonctionnalités
- Queries Manager inchangé
- Connexions et requêtes sauvegardées intactes

## Prochaines Étapes

### Menu Jobs (Phase suivante):
- Job Manager pour planification de tâches
- Configuration de jobs récurrents
- Historique d'exécution
- Notifications et alertes

### Améliorations Data Explorer:
- Édition de fichiers
- Recherche dans les fichiers
- Comparaison de fichiers
- Export de données

## Tests

Pour tester la nouvelle interface :

```bash
uv run run.py
```

Vérifier :
1. Menu Data → Data Explorer s'affiche par défaut
2. Navigation dans RootFolders fonctionne
3. Affichage de fichiers CSV/JSON/TXT correct
4. Menu Databases → Query Manager fonctionne
5. Menu Queries → Saved Queries fonctionne
6. Menu Jobs affiche options désactivées

## Fichiers Modifiés

- `src/ui/gui.py` - Menu refactorisé, nouvelles méthodes
- `src/ui/__init__.py` - Exports mis à jour
- **NOUVEAU:** `src/ui/data_explorer.py` - Module Data Explorer
- **EXISTANT:** `src/ui/file_root_manager.py` - Déjà créé précédemment

## Documentation

Ce document : `docs/MENU_REFACTORING_V2.md`

---

**Version:** 2.0.0
**Date:** 2025-12-08
**Auteur:** Développé avec Claude Code
