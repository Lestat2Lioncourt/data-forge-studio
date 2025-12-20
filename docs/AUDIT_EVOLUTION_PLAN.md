# DataForge Studio - Audit Complet et Plan d'Evolution v3

**Date**: 2025-12-20
**Version**: 0.60.0
**Audit**: Complet (post-Migration v0.6.0)

---

## 0. MIGRATIONS RECENTES

### v0.6.0 - Restructuration Framework (2025-12-20) ✅ TERMINE

```
ui/window_template/ → ui/templates/window/
ui/templates/dialog/ (nouveau)
  └── SelectorDialog (base class pour dialogs de selection)
```

**Changements**:
- ConnectionSelectorDialog herite de SelectorDialog
- AboutDialog herite de SelectorDialog
- Theme keys: selector_titlebar_bg/fg, selector_border_color
- Vision long terme: separation Framework vs Application

---

## 1. STATISTIQUES GLOBALES

```
Fichiers Python totaux:     170
Lignes de code totales:     33,302
Fichiers de test:           25
Documentation (markdown):   23 fichiers
```

---

## 2. FICHIERS VOLUMINEUX (>500 lignes)

| Fichier | Lignes | Severite | Probleme |
|---------|--------|----------|----------|
| `config_db.py` | 1,967 | CRITIQUE | Monolithique: schema + migrations + CRUD |
| `resources_manager.py` | 1,739 | HAUTE | Orchestration complexe mais necessaire |
| `database_manager.py` | 1,469 | HAUTE | N'herite pas de BaseManagerView |
| `query_tab.py` | 1,233 | MOYENNE | Deja splitte (vs 1,707 avant) |
| `settings_frame.py` | 968 | MOYENNE | Deja splitte (vs 1,124 avant) |
| `image_library_manager.py` | 963 | MOYENNE | Scanning + caching + display |
| `rootfolder_manager.py` | 946 | MOYENNE | N'herite pas de BaseManagerView |
| `custom_datagridview.py` | 912 | MOYENNE | Grid + export + styling |
| `theme_bridge.py` | 819 | BASSE | Deja splitte (vs 932 avant) |
| `main_window.py` | 672 | BASSE | Acceptable pour fenetre principale |

---

## 3. PROBLEMES DE QUALITE CODE

### A. Gestion d'exceptions deficiente (213 instances)

**CRITIQUE** - Clauses `except:` et `except Exception:` nues:

| Fichier | Occurrences | Exemple |
|---------|-------------|---------|
| settings_frame.py | 15+ | `except: pass` (ligne 489) |
| theme_bridge.py | 10+ | `except Exception:` sans logging |
| database_manager.py | 8+ | Exceptions silencieuses |
| file_reader.py | 5+ | Masque les vraies erreurs |
| toolbar_builder.py | 3+ | `except:` vide |

**Impact**: Debugging difficile, erreurs masquees, KeyboardInterrupt capture

### B. Chaines UI non internationalisees (215 instances)

**HAUTE** - Textes hardcodes au lieu de `tr()`:

```python
# settings_frame.py - Exemple
THEME_CATEGORIES = {
    "Barre de titre": [...],      # Devrait etre tr("theme_cat_titlebar")
    "Menu": [...],                 # Devrait etre tr("theme_cat_menu")
    "Sous-menus": [...],          # Devrait etre tr("theme_cat_submenus")
}
```

| Fichier | Chaines hardcodees |
|---------|-------------------|
| settings_frame.py | 50+ |
| custom_datagridview.py | 30+ |
| rootfolder_manager.py | 25+ |
| database_manager.py | 40+ |
| resources_manager.py | 35+ |

### C. Imports tardifs (67 instances)

**MOYENNE** - Imports a l'interieur des fonctions:

```python
# resources_manager.py
def _setup_manager_pages(self):
    from PySide6.QtWidgets import QTabWidget  # Ligne 148

def _get_or_create_query_tab(self, db_id):
    from .query_tab import QueryTab  # Lignes 1161, 1207, 1263
```

**Impact**: Performance degradee, chargement modules inconsistant

### D. Commentaires TODO/FIXME (12 instances)

| Fichier | Ligne | Contenu |
|---------|-------|---------|
| main_window.py | 374 | TODO: Implement import dialog |
| main_window.py | 379 | TODO: Implement export dialog |
| data_explorer.py | 355 | TODO: Load actual CSV file |
| data_explorer.py | 430 | TODO: Open dialog to create new project |
| connection_selector_dialog.py | 69, 77 | TODO non specifie |

### E. Fichiers morts/backup (8 fichiers)

Dans `APP_SOURCE/`:
- `database_manager_old.py` (469 lignes)
- `database_manager_old2.py` (623 lignes)
- `data_explorer_backup.py`
- Autres fichiers legacy

---

## 4. ARCHITECTURE - ANALYSE

### A. Systeme Plugin ✅ BIEN CONCU

```
core/
├── base_plugin.py      (206 lignes) - Interface abstraite
└── plugin_manager.py   (392 lignes) - Gestionnaire central

plugins/
├── database_plugin.py
├── rootfolder_plugin.py
├── queries_plugin.py
├── jobs_plugin.py
├── scripts_plugin.py
├── images_plugin.py
├── settings_plugin.py
├── workspaces_plugin.py
└── help_plugin.py
```

**Points forts**:
- Cycle de vie clair: init → create_widget → activate → deactivate → cleanup
- Signaux pour evenements lifecycle
- Metadata structure (id, name, icon, category, order)

**Points faibles**:
- Resolution dependances simplifiee (pas de tri topologique reel)
- Pas de detection de dependances circulaires

### B. Hierarchie Managers ⚠️ INCONSISTANTE

```
BaseManagerView (344 lignes)
    └── ResourcesManager, DataExplorer

HierarchicalManagerView (485 lignes)
    └── QueriesManager, JobsManager, ScriptsManager

QWidget (direct) ❌
    └── DatabaseManager (1,469 lignes)
    └── RootFolderManager (946 lignes)
    └── WorkspaceManager (426 lignes)
    └── ImageLibraryManager (963 lignes)
```

**Probleme**: 4 managers n'heritent pas des classes de base
**Impact**: Duplication de code, comportements inconsistants

### C. Couche Base de Donnees ⚠️ MONOLITHIQUE

**config_db.py (1,967 lignes)** - Responsabilites multiples:

| Responsabilite | Lignes estimees |
|----------------|-----------------|
| Schema creation (CREATE TABLE) | ~290 |
| Migrations | ~500 |
| Connection management | ~100 |
| CRUD operations (10+ entites) | ~800 |
| Cleanup/maintenance | ~100 |
| Import/export | ~150 |

**Problemes**:
1. Single Responsibility Violation
2. Pas de gestion de transactions (commits eparpilles)
3. Pattern singleton global (`get_config_db()` appele 39+ fois)
4. Couplage fort, difficile a tester

**Models (database/models/)** ✅ Bien organise:
- 9 dataclasses propres
- Auto-generation ID et timestamps

**Schema Loaders** ✅ Bonne abstraction:
- Pattern Factory
- Extensible (SQLServer, SQLite, Access)

### D. Workspaces ✅ COMPLETE

- Filtrage unifie dans tous les managers
- WorkspaceSelector dans toolbar principale
- Tables de liaison dans config_db

---

## 5. PERFORMANCE

### A. Connexions Base de Donnees

**Probleme**: Pas de connection pooling
```python
def _get_connection(self) -> sqlite3.Connection:
    conn = sqlite3.connect(self.db_path)  # Nouvelle connexion a chaque fois
```

**Impact**: 39+ appels par session, overhead significatif

### B. Chargement Donnees

**Status**: Correct
- `LARGE_DATASET_THRESHOLD = 100,000` lignes
- `BackgroundRowLoader` pour chargement async
- Batching dans QueryTab

**Amelioration possible**: Seuil configurable

### C. Affichage Grilles

**Probleme** dans `custom_datagridview.py`:
- Charge dataset entier en memoire
- Pas de pagination pour tres gros datasets (500k+ lignes)
- Pas de virtual scrolling

### D. Requetes Dupliquees

**Probleme**: Pas de cache pour donnees frequentes
- ResourcesManager charge databases, queries, jobs...
- Chaque manager fait ses propres appels a config_db
- Memes donnees rechargees plusieurs fois

---

## 6. TESTS

### Couverture Actuelle

| Zone | Tests | Couverture estimee |
|------|-------|-------------------|
| SQL Formatting | 5 fichiers | ~70% |
| Config Database | 2 fichiers | ~30% |
| UI Managers | 3 fichiers | ~10% |
| Plugins | 0 fichiers | 0% |
| Integration | 0 fichiers | 0% |

### Lacunes Critiques

1. Aucun test pour le systeme de plugins
2. Aucun test d'integration (workflow complet)
3. Tests UI limites (managers de 1,469 lignes sans tests dedies)
4. Pas de tests de performance/charge

---

## 7. DOCUMENTATION

### Points Forts
- 23 fichiers markdown
- PATTERNS.md (11 KB) - Architecture
- Documentation features complete

### Lacunes
- Pas de docstrings dans config_db.py (1,967 lignes)
- Pas de guide d'installation
- Pas de documentation API (Sphinx)
- Pas de guide de contribution

---

## 8. RESUME DES PROBLEMES

| Priorite | Probleme | Quantite | Impact |
|----------|----------|----------|--------|
| CRITIQUE | Clauses except nues | 213 | Fiabilite, debugging |
| CRITIQUE | config_db.py monolithique | 1,967 LOC | Maintenabilite |
| HAUTE | Chaines non i18n | 215 | Localisation |
| HAUTE | Managers sans heritage | 4 managers | Duplication code |
| HAUTE | get_config_db() global | 39+ appels | Couplage, tests |
| HAUTE | Pas de connection pooling | N/A | Performance |
| MOYENNE | Imports tardifs | 67 | Performance |
| MOYENNE | TODOs non resolus | 12 | Completude |
| MOYENNE | Tests insuffisants | 25 fichiers | Fiabilite |
| BASSE | Fichiers backup | 8 | Proprete code |

---

## 9. PLAN D'ACTION - NOUVELLE VERSION

### PHASE 1: QUALITE CODE IMMEDIATE (2-3 jours)

**1.1 Nettoyer fichiers morts**
- [ ] Supprimer APP_SOURCE/ ou le deplacer hors repo
- [ ] Verifier qu'aucun import ne pointe vers ces fichiers

**1.2 Corriger gestion exceptions (213 cas)**
- [ ] Remplacer `except:` par exceptions specifiques
- [ ] Ajouter logging dans les handlers
- [ ] Pattern recommande:
```python
except (ValueError, TypeError) as e:
    logger.error(f"Operation failed: {e}")
    DialogHelper.error(tr("error_message"), parent=self)
```

**1.3 Consolider imports tardifs (67 cas)**
- [ ] Deplacer imports au niveau module
- [ ] Garder imports tardifs uniquement pour dependances circulaires

### PHASE 2: INTERNATIONALISATION MODULAIRE (3-4 jours)

**Probleme actuel**:
- Fichier monolithique `config/i18n.py` (655 lignes)
- Toutes les traductions EN/FR hardcodees
- Pas de modularite par plugin/module
- 215 chaines UI non internationalisees

**2.1 Architecture i18n modulaire**

```
config/
├── i18n/
│   ├── __init__.py           # I18nManager (registry central)
│   ├── base.py               # ModuleTranslations (classe de base)
│   └── core/                 # Traductions globales
│       ├── common_en.json    # yes, no, ok, cancel, error...
│       ├── common_fr.json
│       ├── menu_en.json      # Menu principal
│       └── menu_fr.json

plugins/
└── database_manager/
    └── i18n/                 # Traductions du plugin
        ├── __init__.py       # Auto-register au manager
        ├── en.json           # {"db_title": "Database Manager", ...}
        └── fr.json
```

**2.2 Mecanisme**:
- Chaque plugin s'enregistre aupres de I18nManager avec son namespace
- `t("db.title")` → cherche dans database_manager
- `t("ok")` → cherche dans common (global)
- Une nouvelle langue dans un plugin apparait automatiquement dans l'interface

**2.3 Extraire chaines hardcodees (215 cas)**
- [ ] Migrer `config/i18n.py` vers nouvelle architecture
- [ ] Creer fichiers JSON par module
- [ ] Remplacer textes hardcodes par `tr("key")`

**Fichiers prioritaires**:
1. settings_frame.py (50+ chaines)
2. database_manager.py (40+ chaines)
3. resources_manager.py (35+ chaines)
4. custom_datagridview.py (30+ chaines)

### PHASE 3: REFACTORING config_db.py (3-4 jours)

**3.1 Extraire en modules separes**:
```
database/
├── config_db.py          (facade ~300 lignes)
├── schema_manager.py     (creation + migrations ~400 lignes)
├── connection_pool.py    (pooling connexions ~100 lignes)
└── repositories/
    ├── database_repo.py
    ├── query_repo.py
    ├── job_repo.py
    ├── script_repo.py
    ├── workspace_repo.py
    └── image_repo.py
```

**3.2 Implementer connection pooling**:
```python
class ConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 5):
        self._pool = queue.Queue(maxsize=max_connections)

    def get_connection(self) -> sqlite3.Connection:
        # Retourne connexion du pool ou en cree une nouvelle
```

**3.3 Ajouter gestion transactions**:
```python
@contextmanager
def transaction(self):
    conn = self.get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

### PHASE 4: HARMONISER MANAGERS (3-4 jours)

**4.1 Creer interface commune**:
```python
# managers/protocols.py
class ManagerProtocol(Protocol):
    def refresh(self) -> None: ...
    def set_workspace_filter(self, workspace_id: Optional[str]) -> None: ...
    def get_current_item(self) -> Optional[Any]: ...
```

**4.2 Adapter managers existants**:
- [ ] DatabaseManager: implementer ManagerProtocol
- [ ] RootFolderManager: implementer ManagerProtocol
- [ ] ImageLibraryManager: implementer ManagerProtocol
- [ ] WorkspaceManager: implementer ManagerProtocol

### PHASE 5: TESTS (4-5 jours)

**5.1 Tests unitaires prioritaires**:
- [ ] Plugin system (base_plugin.py, plugin_manager.py)
- [ ] config_db.py (apres refactoring)
- [ ] Managers critiques (database_manager, resources_manager)

**5.2 Tests integration**:
- [ ] Workflow: connexion DB → execution requete → sauvegarde
- [ ] Workflow: creation workspace → filtrage → suppression

**5.3 Objectif**: 50% couverture code critique

### PHASE 6: PERFORMANCE (2-3 jours)

**6.1 Cache donnees frequentes**:
```python
class CachedConfigDB:
    def __init__(self):
        self._cache = TTLCache(maxsize=100, ttl=60)

    def get_all_databases(self):
        if "databases" not in self._cache:
            self._cache["databases"] = self._db.get_all_database_connections()
        return self._cache["databases"]
```

**6.2 Virtual scrolling pour gros datasets**:
- [ ] Implementer dans custom_datagridview.py
- [ ] Seuil: 50,000+ lignes

### PHASE 7: SYSTEME DE THEMES SIMPLIFIE (2-3 jours)

**Probleme actuel**:
- Theme Editor permet d'editer 90+ couleurs individuellement
- Complexe pour l'utilisateur final
- Le systeme `_expand_minimal_palette()` existe mais n'est pas expose

**7.1 Concept "Color Patch"**

L'utilisateur definit seulement 5-8 couleurs, le systeme derive le reste:

```
┌─────────────────────────────────────────────────────┐
│  Quick Theme Creator                                │
├─────────────────────────────────────────────────────┤
│  Base Theme: [Dark Mode ▼]                          │
│                                                     │
│  Override Colors (optional):                        │
│  ┌──────────────────┬────────────────────────────┐  │
│  │ Accent           │ [■ #0078d4] [Pick...]      │  │
│  │ Primary BG       │ [■ #1e1e1e] [Pick...]      │  │
│  │ Secondary BG     │ [■ #252525] [Pick...]      │  │
│  │ Text Primary     │ [■ #ffffff] [Pick...]      │  │
│  │ Text Secondary   │ [■ #808080] [Pick...]      │  │
│  │ Border           │ [■ #3d3d3d] [Pick...]      │  │
│  │ Success          │ [■ #2ecc71] [Pick...]      │  │
│  │ Error            │ [■ #e74c3c] [Pick...]      │  │
│  └──────────────────┴────────────────────────────┘  │
│                                                     │
│  [Preview] [Reset to Base] [Save as New Theme]      │
└─────────────────────────────────────────────────────┘
```

**7.2 Structure technique**

```python
# Theme Patch = Base Theme + Overrides
class ThemePatch:
    base_theme: str        # "minimal_dark", "minimal_light"
    overrides: Dict[str, str]  # {"Accent": "#ff6600", ...}

# Sauvegarde dans _AppConfig/themes/my_custom.json
{
    "type": "patch",
    "base": "minimal_dark",
    "overrides": {
        "Accent": "#ff6600",
        "Primary_BG": "#1a1a2e"
    }
}
```

**7.3 Mapping des couleurs utilisateur → palette minimale**

| Couleur utilisateur | Cle palette minimale |
|---------------------|----------------------|
| Accent              | Accent               |
| Primary BG          | Frame_BG             |
| Secondary BG        | Data_BG              |
| Text Primary        | Normal_FG            |
| Text Secondary      | Frame_FG_Secondary   |
| Border              | Data_Border          |
| Success             | Success_FG           |
| Error               | Error_FG             |

**7.4 Implementation**:
- [ ] Creer `ui/frames/quick_theme_frame.py`
- [ ] Ajouter onglet "Quick Theme" dans Settings
- [ ] Modifier `theme_manager.py` pour supporter les patches
- [ ] Preview en temps reel
- [ ] Garder Theme Editor avance pour utilisateurs experts

### PHASE 8: DOCUMENTATION (2 jours)

**8.1 Docstrings**:
- [ ] config_db.py (apres refactoring)
- [ ] Managers principaux
- [ ] Plugin system

**8.2 Guides**:
- [ ] docs/INSTALLATION.md
- [ ] docs/CONTRIBUTING.md
- [ ] docs/API.md (ou Sphinx)

---

## 10. ESTIMATION EFFORT

| Phase | Duree | Priorite | Dependances |
|-------|-------|----------|-------------|
| 1. Qualite code | 2-3 jours | CRITIQUE | Aucune |
| 2. Internationalisation modulaire | 3-4 jours | HAUTE | Aucune |
| 3. Refactoring config_db | 3-4 jours | HAUTE | Phase 1 |
| 4. Harmoniser managers | 3-4 jours | MOYENNE | Phase 3 |
| 5. Tests | 4-5 jours | MOYENNE | Phases 3, 4 |
| 6. Performance | 2-3 jours | BASSE | Phase 3 |
| 7. Themes simplifies (Color Patch) | 2-3 jours | MOYENNE | Aucune |
| 8. Documentation | 2 jours | BASSE | Phases 3, 4 |
| **TOTAL** | **21-28 jours** | | |

---

## 11. PROGRESSION

### Termine (Historique)
- [x] Phase 1 ancien: Nettoyage code mort (1,862 lignes)
- [x] Phase 2 ancien: Split fichiers monolithiques
- [x] Phase 3 ancien: Consolidation duplications
- [x] Phase 4 ancien: Standardisation et documentation
- [x] Phase 5 ancien: Architecture plugin
- [x] Phase 6 ancien: Unification workspaces
- [x] **v0.6.0**: Restructuration Framework (ui/templates/, SelectorDialog)

### A faire (Plan actuel v3)
- [ ] Phase 1: Qualite code immediate (213 bare except, 67 late imports)
- [ ] Phase 2: Internationalisation modulaire (architecture + 215 chaines)
- [ ] Phase 3: Refactoring config_db.py (1,967 lignes → modules)
- [ ] Phase 4: Harmoniser managers (4 managers sans heritage)
- [ ] Phase 5: Tests (objectif 50% couverture)
- [ ] Phase 6: Performance (pooling, cache, virtual scroll)
- [ ] Phase 7: Themes simplifies (Color Patch system)
- [ ] Phase 8: Documentation

---

## 12. ORDRE RECOMMANDE

Pour minimiser les risques et maximiser la valeur:

```
Phase 1 (Qualite) ──┐
                    ├──→ Phase 3 (config_db) ──→ Phase 4 (Managers) ──→ Phase 5 (Tests)
Phase 2 (i18n) ─────┘                                                        │
                                                                             ↓
Phase 7 (Themes) ─────────────────────────────────────────────────→ Phase 8 (Docs)
                                                                             ↑
Phase 6 (Performance) ───────────────────────────────────────────────────────┘
```

**Phases independantes** (peuvent etre faites en parallele):
- Phase 1 + Phase 2 (qualite + i18n)
- Phase 7 (themes) - independante du reste

---

## Notes

Ce document est la version 3 du plan d'evolution.
- v1: Audit initial et 6 phases completees
- v2: Nouvel audit post-Phase 6 (2025-12-19)
- v3: Ajout migration v0.6.0, i18n modulaire, themes simplifies (2025-12-20)
