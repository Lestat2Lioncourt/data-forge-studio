# DataForge Studio - Roadmap

## Vue d'ensemble

Ce document trace l'avancement des développements sur DataForge Studio.

---

## ✅ Phase 1: DatabaseDialect Pattern (Terminé - Janvier 2025)

### Objectif
Remplacer les if/else chains dans `database_manager.py` par un pattern DatabaseDialect.

### Structure
```
src/dataforge_studio/database/dialects/
    __init__.py
    base.py                  # DatabaseDialect, ColumnInfo, ParameterInfo
    factory.py               # DialectFactory
    sqlite_dialect.py
    sqlserver_dialect.py
    postgresql_dialect.py
    access_dialect.py
```

### Avancement
| Tâche | Status |
|-------|--------|
| Infrastructure (base.py, factory.py) | ✅ |
| SQLite Dialect | ✅ |
| SQL Server Dialect | ✅ |
| PostgreSQL Dialect | ✅ |
| Access Dialect | ✅ |
| Intégration `_load_view_code()` | ✅ |
| Intégration `_load_routine_code()` | ✅ |
| Intégration `_generate_exec_template()` | ✅ |
| Intégration `_generate_select_function()` | ✅ |
| `_generate_select_query()` | ⬜ Optionnel |
| `_generate_select_columns_query()` | ⬜ Optionnel |

---

## ✅ Phase 2: Script Template System (Terminé - Janvier 2025)

### Objectif
Système de templates de scripts basé sur YAML avec découverte automatique.

### Structure
```
src/dataforge_studio/
├── core/
│   └── script_template_loader.py    # ScriptTemplateLoader
├── plugins/scripts/
│   ├── manifest.yaml
│   └── available/
│       ├── file_dispatcher.py
│       ├── file_dispatcher.yaml
│       ├── data_loader.py
│       └── data_loader.yaml
└── ui/widgets/
    └── code_viewer.py               # CodeViewerWidget
```

### Avancement
| Tâche | Status |
|-------|--------|
| Créer `ScriptTemplateLoader` | ✅ |
| Fichiers YAML pour templates | ✅ |
| Support des aliases | ✅ |
| `CodeViewerWidget` avec syntax highlighting | ✅ |
| Affichage du source dans ScriptsManager | ✅ |
| Champ `file_path` dans Script model | ✅ |
| Migration DB pour `file_path` | ✅ |
| `BUILTIN_SCRIPTS` dynamique depuis YAML | ✅ |
| Layout tabulé (Details/Parameters + Source/Log) | ✅ |

---

## 🔲 Phase 3: Exécution des Scripts (À faire)

### Objectif
Permettre l'exécution des scripts avec formulaire de paramètres dynamique.

### Tâches
| Tâche | Status |
|-------|--------|
| Formulaire dynamique depuis paramètres YAML | ⬜ |
| Widgets par type (RootFolderSelector, DatabaseSelector, etc.) | ⬜ |
| Bouton "Run" fonctionnel | ⬜ |
| Résolution des paramètres (RootFolder → path, Database → connection) | ⬜ |
| Affichage logs en temps réel dans onglet "Log" | ⬜ |
| Gestion des erreurs et affichage | ⬜ |
| Mode dry-run | ⬜ |

---

## 🔲 Phase 4: Jobs & Orchestration (À faire)

### Objectif
Système de Jobs pour configurer et planifier l'exécution des scripts.

### Tâches
| Tâche | Status |
|-------|--------|
| Lier Job à Script + valeurs paramètres | ⬜ |
| Exécution manuelle de Job | ⬜ |
| Historique des exécutions | ⬜ |
| Statut d'exécution (pending, running, success, failed) | ⬜ |
| Chaînage de Jobs (workflow) | ⬜ |
| Planification (cron-like) | ⬜ |

---

## 🔲 Phase 5: Plugin System V2 (À faire)

### Objectif
Architecture plugin complète avec activation/désactivation et dépendances.

### Structure cible
```
src/dataforge_studio/plugins/
├── databases/
│   ├── manifest.yaml
│   └── ...
├── rootfolders/
│   ├── manifest.yaml
│   └── ...
├── scripts/
│   ├── manifest.yaml
│   └── ...
└── ...
```

### Tâches
| Tâche | Status |
|-------|--------|
| Manifest.yaml par plugin (id, requires, provides) | ⬜ |
| Résolution dépendances inter-plugins | ⬜ |
| Activation/désactivation de plugins | ⬜ |
| UI de gestion des plugins | ⬜ |
| Hot-reload des plugins | ⬜ |

---

## 🔲 Améliorations futures

- [ ] Support MySQL dialect
- [ ] Support Oracle dialect
- [ ] Tests unitaires pour les dialects
- [ ] Tests unitaires pour ScriptTemplateLoader
- [ ] Marketplace de plugins/scripts
- [ ] Export/Import de configurations
