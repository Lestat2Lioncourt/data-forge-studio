# DataForge Studio - Roadmap

**Version**: 0.5.7
**Objectif**: POC à v0.9.xx, Production à v1.0

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

## 🔲 Phase 4: Theming & App Icons (À faire - Post-POC)

### Objectif
Système d'icônes dynamiques adaptées aux thèmes clair/sombre.

### Concept
```
┌─────────────────────────────────────────────────────────────────────┐
│  ICONES SOURCE (noir)  →  GENERATION  →  ICONES THEMEES (cache)    │
│  icons/base/*.png         au lancement   icons/generated/light/    │
│                                          icons/generated/dark/     │
└─────────────────────────────────────────────────────────────────────┘
```

### Architecture
| Composant | Description |
|-----------|-------------|
| **Icônes source** | Un seul jeu d'icônes en couleur de base (noir) |
| **Configuration thème** | `icon_color_light` et `icon_color_dark` dans chaque thème |
| **Générateur** | Utilitaire de recoloration (PIL pour PNG ou XML pour SVG) |
| **Cache** | Icônes générées stockées dans `icons/generated/{theme}/` |
| **Loader** | `image_loader.py` vérifie le cache, génère si nécessaire |

### Tâches
| Tâche | Status | Effort |
|-------|--------|--------|
| Créer `icon_generator.py` (recoloration PNG avec PIL) | ⬜ | 3h |
| Modifier `image_loader.py` (vérification cache + génération) | ⬜ | 2h |
| Étendre format thème (`icon_color_light`, `icon_color_dark`) | ⬜ | 1h |
| Convertir icônes existantes en versions monochromes (base noire) | ⬜ | 4h |
| Support SVG avec manipulation XML (optionnel) | ⬜ | 3h |

### Avantages
- **Maintenance simplifiée**: Un seul jeu d'icônes à gérer
- **Thèmes personnalisables**: Couleur d'icônes configurable par thème
- **Performance**: Génération une seule fois, puis cache
- **Cohérence visuelle**: Icônes adaptées automatiquement au thème actif

---

## 🔲 Phase 5: Jobs & Orchestration (À faire)

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

## 🔲 Phase 6: Plugin System V2 (Vision v2.0)

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
| Plugin Manager externe | ⬜ |
| Marketplace de plugins | ⬜ |

---

## 🔲 Phase 7: Qualité Code (v1.0)

### Tâches
| Tâche | Status |
|-------|--------|
| Refactorer DatabaseManager (~1965 lignes) | ⬜ |
| Créer constants.py (magic numbers) | ⬜ |
| Déduplication code connexion | ⬜ |
| Paramétrer requêtes schema loaders | ⬜ |
| Augmenter couverture tests (60%) | ⬜ |
| Thread-safe singletons | ⬜ |

---

## 🔲 Améliorations futures

- [ ] Support MySQL dialect
- [ ] Support Oracle dialect
- [ ] Support MongoDB
- [ ] Tests unitaires pour les dialects
- [ ] Tests unitaires pour ScriptTemplateLoader
- [ ] Documentation utilisateur
- [ ] Export/Import de configurations

---

## Priorités

```
✅ FAIT
├── Phase 1: DatabaseDialect Pattern
└── Phase 2: Script Template System

PRIORITAIRE (Pour POC v0.9.xx)
├── Phase 3: Exécution des Scripts
└── Persistance état UI (splitters)

POST-POC (v1.0)
├── Phase 4: Theming & App Icons
├── Phase 5: Jobs & Orchestration
└── Phase 7: Qualité Code

VISION (v2.0)
└── Phase 6: Plugin System V2
```
