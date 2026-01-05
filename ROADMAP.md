# DataForge Studio - Roadmap & Analyse

**Version**: 0.5.7
**Objectif**: POC v0.9.xx / Production v1.0
**Date d'analyse**: Janvier 2025

---

## Analyse Globale de la Solution

### Scores sur 10

| Critere | Score | Justification |
|---------|-------|---------------|
| **Structure de l'application** | 8/10 | Architecture plugin bien concue, separation des couches (UI/Core/Database), patterns modernes (Repository, Factory, Observer). Points a ameliorer: fichiers trop volumineux (database_manager.py: 2272 lignes) |
| **Qualite du code** | 7/10 | Code lisible, type hints partiels, docstrings presentes sur les classes principales. Manques: type hints incomplets, quelques TODOs non resolus, magic numbers |
| **Gestion de la securite** | 6.5/10 | Credentials via keyring (bon), YAML safe_load (bon), mais injections SQL potentielles dans PRAGMA statements et f-strings pour noms de tables. Acceptable pour outil DATA interne |
| **Maintenabilite** | 7/10 | Bonne modularite plugin, tests unitaires presents (1517 lignes). A ameliorer: couverture tests (~30%), documentation API |
| **Fiabilite** | 7.5/10 | Gestion d'erreurs presente, transactions DB, cleanup proper. Points faibles: except broad en certains endroits, pas de retry sur connexions |
| **Performance** | 7/10 | Caching (schema_cache, cachetools), lazy loading, connection pooling. Ameliorable: async operations, pagination virtuelle complete |
| **Extensibilite** | 8.5/10 | Excellent systeme de plugins, dialects extensibles, theme system v2 modulaire |
| **Documentation** | 7/10 | 18 guides utilisateur, README complet. Manque: documentation API developpeur |
| **UX/UI** | 8/10 | Interface moderne PySide6, themes personnalisables, i18n (3 langues), splash screen progressif |

**Score Global: 7.4/10** - Solide pour une version Beta pre-POC

---

## Bilan

### Points Positifs (+)

1. **Architecture plugin exemplaire**
   - 9 plugins bien isoles avec lifecycle complet
   - Signal/slot pour communication inter-plugins
   - Lazy widget creation pour performance

2. **Systeme de themes avance (v2)**
   - Architecture Palette/Disposition separee
   - Themes personnalisables via JSON
   - Generation QSS dynamique

3. **Support multi-base de donnees**
   - 5 dialects implementes (SQLite, PostgreSQL, SQL Server, MySQL, Access)
   - Schema loaders specifiques par DB
   - Pattern Factory pour extensibilite

4. **Gestion securisee des credentials**
   - Utilisation du keyring systeme (Windows Credential Manager, etc.)
   - Pas de stockage en clair dans la DB de config

5. **Internationalisation complete**
   - 3 langues (EN, FR, ES)
   - Systeme modulaire par plugin
   - Fallback chain robuste

6. **Code moderne Python**
   - Dataclasses pour les models
   - Type hints partiels
   - Pathlib pour les chemins
   - PySide6 moderne

7. **Tests unitaires presents**
   - 6 fichiers de tests (1517 lignes)
   - Coverage sur repositories, plugins, cache, themes

8. **Documentation utilisateur riche**
   - 18 guides markdown
   - Documentation d'integration

### Points Negatifs (-)

1. **Fichiers trop volumineux**
   - `database_manager.py`: 2272 lignes (60 methodes)
   - `config_db.py`: 2243 lignes
   - `query_tab.py`: 1822 lignes
   - Besoin de refactoring en sous-modules

2. **Injections SQL potentielles**
   - PRAGMA statements avec f-strings (SQLite)
   - Noms de DB dans f-strings (SQL Server)
   - Risque faible car outil interne, mais a corriger

3. **Support MySQL incomplet**
   - Dialog MySQL existe mais backend manquant
   - `mysql_dialect.py` et `mysql_loader.py` a creer
   - Enregistrement dans les factories manquant

4. **Type hints incomplets**
   - ~40% des fonctions sans return type
   - Paramètres non types dans certains constructeurs

5. **Magic numbers disperses**
   - Timeouts: 3, 5, 20 (non centralises)
   - Limits: 100, 1000, 10000 (inconsistants)

6. **Gestion d'erreurs broad**
   - `except Exception: pass` en plusieurs endroits
   - Swallow d'erreurs sans logging

7. **Couverture de tests limitee**
   - ~30% estime
   - Pas de tests UI
   - Pas de tests d'integration

8. **TODOs non resolus** (6 instances)
   - Dry run non implemente dans scripts
   - Theme dialog manquant
   - MongoDB/Oracle non implementes

---

## Risques Identifies

### Risques Techniques

| Risque | Severite | Impact | Mitigation |
|--------|----------|--------|------------|
| **SQL Injection PRAGMA** | Moyenne | Faible (outil interne) | Echapper les noms de tables |
| **Fichiers monolithiques** | Haute | Maintenabilite reduite | Refactoring progressif |
| **Absence async** | Moyenne | UI freeze possible | QThread existant, a etendre |
| **Deps Windows (pywin32)** | Faible | Cross-platform limite | Conditional imports OK |

### Risques Fonctionnels

| Risque | Severite | Impact | Mitigation |
|--------|----------|--------|------------|
| **Scripts non executables** | Haute | Feature incomplete | Phase 3 prioritaire |
| **MySQL backend manquant** | Haute | Feature incomplete | Creer dialect + loader |
| **MongoDB/Oracle** | Faible | Prevu mais non prioritaire | Implementer quand besoin |
| **Jobs non fonctionnels** | Haute | Feature incomplete | Phase 5 |

---

## Plan de Correctifs par Priorite

### P0 - Critique (POC 0.9.xx)

| Correctif | Fichier(s) | Effort |
|-----------|------------|--------|
| Implementer execution des scripts | Phase 3 complete | 3-4j |
| **Completer support MySQL** | mysql_dialect.py, mysql_loader.py, factories | 1-1.5j |
| Corriger PRAGMA SQL injection | sqlite_loader.py, schema_cache.py, sqlite_dialect.py | 0.5j |

### P1 - Important (v0.9.xx)

| Correctif | Fichier(s) | Effort |
|-----------|------------|--------|
| Aide contextuelle (boutons [?]) | Tous les managers | 1j |
| Fenetre d'aide detachable | ui/frames/help_frame.py | 0.5j |
| Coherence visuelle fenetres | Tous les dialogs | 1j |
| Extraire constants.py | Nouveau fichier + refactoring | 1j |

### P1.5 - Important (v1.0)

| Correctif | Fichier(s) | Effort |
|-----------|------------|--------|
| Refactorer database_manager.py | ui/managers/database_manager.py | 2-3j |
| Completer type hints | Tous les fichiers | 2j |
| Resoudre TODOs restants | main_window.py, scripts | 1j |

### P2 - Amelioration (v1.0+)

| Correctif | Fichier(s) | Effort |
|-----------|------------|--------|
| Augmenter couverture tests (60%) | tests/ | 3-4j |
| Refactorer config_db.py | database/config_db.py | 2j |
| Ajouter docstrings API | Tous les modules publics | 2j |
| Implementer Jobs & Orchestration | Phase 5 complete | 4-5j |

### P3 - Nice to Have (v2.0)

| Correctif | Fichier(s) | Effort |
|-----------|------------|--------|
| Plugin System V2 complet | Phase 6 | 5-6j |
| Support MySQL/Oracle/MongoDB | dialects/ + loaders/ | 3-4j |
| Operations async generalisees | Core refactoring | 3j |

---

## Nouveautes vs Corrections: Recommandation

**Contexte**: Application Beta, profils DATA, POC v0.9.xx

### Recommandation: Equilibre 60% Nouveautes / 40% Corrections

**Justification**:
1. L'application est fonctionnelle pour le use case principal (exploration DB, queries)
2. Les risques de securite sont faibles (outil interne, pas d'exposition web)
3. Le POC doit demontrer les fonctionnalites cles (Scripts executables = critique)
4. Les refactorings peuvent attendre v1.0

**Priorites pour POC v0.9.xx**:
1. **Phase 3**: Execution des Scripts (nouveaute critique)
2. **MySQL**: Completer le support backend (dialect + loader)
3. **Phase 3.2**: Aide contextuelle + fenetre detachable (UX)
4. **Phase 3.3**: Coherence visuelle des fenetres (UI)
5. **Securite**: PRAGMA injection fix (correction importante)

**Reporter a v1.0**:
- Refactoring database_manager.py
- Couverture tests 60%
- Documentation API

---

## Phases du Roadmap

### Phase 1: DatabaseDialect Pattern (Termine - Janvier 2025)

| Tache | Status |
|-------|--------|
| Infrastructure (base.py, factory.py) | Done |
| SQLite Dialect | Done |
| SQL Server Dialect | Done |
| PostgreSQL Dialect | Done |
| Access Dialect | Done |
| Integration `_load_view_code()` | Done |
| Integration `_load_routine_code()` | Done |
| `_generate_select_query()` | Optionnel |

---

### Phase 2: Script Template System (Termine - Janvier 2025)

| Tache | Status |
|-------|--------|
| ScriptTemplateLoader | Done |
| Fichiers YAML templates | Done |
| Support aliases | Done |
| CodeViewerWidget syntax highlighting | Done |
| Layout tabule (Details/Source/Log) | Done |
| Champ file_path + migration | Done |

---

### Phase 3: Execution des Scripts (REPORTE - En reflexion)

*Note: Le modele final d'execution est encore en cours de reflexion. Cette phase sera reprise ulterieurement.*

| Tache | Status | Priorite |
|-------|--------|----------|
| Formulaire dynamique depuis YAML | Todo | - |
| Widgets par type (RootFolderSelector, etc.) | Todo | - |
| Bouton "Run" fonctionnel | Todo | - |
| Resolution parametres | Todo | - |
| Logs temps reel dans onglet "Log" | Todo | - |
| Gestion erreurs et affichage | Todo | - |
| Mode dry-run | Todo | - |

---

### Phase 3.2: Aide Contextuelle & Documentation Integree (TERMINE)

**Objectif**: Rendre la documentation accessible directement depuis l'interface

| Tache | Status |
|-------|--------|
| HelpFrame ameliore avec navigation markdown | Done |
| DocumentationLoader + manifest YAML | Done |
| Fenetre d'aide detachable (pop-out flottant) | Done |
| Recherche dans la documentation | Done |

*Note: Les boutons [?] contextuels dans les toolbars sont optionnels - l'aide actuelle est suffisante.*

---

### Phase 3.3: Coherence Visuelle des Fenetres (EN COURS)

**Objectif**: Appliquer le theme de l'application a toutes les fenetres (principales et enfants)

| Tache | Status | Priorite |
|-------|--------|----------|
| Identifier les fenetres sans style applique | Done | P1 |
| Creer template PopupWindow avec theme | Done | P1 |
| Migrer HelpWindow vers PopupWindow | Done | P1 |
| Migrer ImageFullscreenDialog | Todo | P1 |
| Migrer SaveImageDialog | Todo | P1 |
| Corriger AboutDialog (couleurs hardcodees) | Todo | P1 |
| Corriger ScriptFormatDialog | Todo | P1 |
| Corriger dialogs restants (SaveQuery, Edit*, etc.) | Todo | P2 |

**Templates disponibles:**
- `PopupWindow` - Fenetre popup avec title bar complete (min/max/close)
- `SelectorDialog` - Dialog de selection simple (close uniquement)

---

### Phase 3.1: Corrections Critiques (POC v0.9.xx)

| Tache | Status | Priorite |
|-------|--------|----------|
| **Creer mysql_dialect.py** | Done | P0 |
| **Creer mysql_loader.py** | Done | P0 |
| **Enregistrer MySQL dans factories** | Done | P0 |
| Fix PRAGMA SQL injection | Done | P0 |
| Extraire constants (timeouts, limits) | Todo | P1 |

*Note: MongoDB et Oracle sont des fonctionnalites planifiees pour le futur (pas de base de test disponible actuellement).*
*Note: MariaDB utilise le meme backend que MySQL (alias enregistre).*

---

### Phase 4: Theming & App Icons (Post-POC)

| Tache | Status | Effort |
|-------|--------|--------|
| icon_generator.py (recoloration PNG) | Todo | 3h |
| Modifier image_loader.py (cache) | Todo | 2h |
| Etendre format theme (icon_color_*) | Todo | 1h |
| Convertir icones en monochromes | Todo | 4h |
| Support SVG (optionnel) | Todo | 3h |

---

### Phase 5: Jobs & Orchestration (v1.0)

| Tache | Status |
|-------|--------|
| Lier Job a Script + parametres | Todo |
| Execution manuelle de Job | Todo |
| Historique des executions | Todo |
| Statut execution (pending, running, etc.) | Todo |
| Chainage de Jobs (workflow) | Todo |
| Planification cron-like | Todo |

---

### Phase 6: Plugin System V2 (v2.0)

| Tache | Status |
|-------|--------|
| Manifest.yaml par plugin | Todo |
| Resolution dependances inter-plugins | Todo |
| Activation/desactivation plugins | Todo |
| UI gestion des plugins | Todo |
| Hot-reload plugins | Todo |
| Plugin Manager externe | Todo |

---

### Phase 7: Qualite Code (v1.0)

| Tache | Status | Priorite |
|-------|--------|----------|
| Refactorer DatabaseManager (~2272 lignes) | Todo | P1 |
| Creer constants.py | Todo | P1 |
| Deduplication code connexion | Todo | P2 |
| Parametrer requetes schema loaders | Todo | P2 |
| Couverture tests (60%) | Todo | P2 |
| Thread-safe singletons | Todo | P2 |
| Completer type hints | Todo | P1 |
| Ajouter docstrings API | Todo | P2 |

---

## Statistiques du Projet

| Metrique | Valeur |
|----------|--------|
| Fichiers Python | 185 |
| Lignes de code (src/) | ~52,000 |
| Fichiers de tests | 6 |
| Lignes de tests | 1,517 |
| Plugins | 9 |
| Dialects DB | 5 (SQLite, PostgreSQL, SQL Server, MySQL/MariaDB, Access) |
| Langues i18n | 3 |
| Themes | 4 |
| Guides documentation | 18 |
| TODOs restants | 6 |

---

## Timeline Suggeree

```
Janvier 2025 (actuel)
|-- Phase 1 & 2 terminees
|-- Analyse globale & ROADMAP mis a jour
|
Fevrier 2025
|-- Phase 3 (Execution Scripts)
|-- Phase 3.1 (MySQL backend + PRAGMA fix)
|-- v0.8.0 release
|
Mars 2025
|-- Phase 3.2 (Aide contextuelle + fenetre detachable)
|-- Phase 3.3 (Coherence visuelle fenetres)
|-- v0.9.0 POC Release
|
Avril-Mai 2025
|-- Phase 4 (Theming Icons)
|-- Phase 7 partiel (Refactoring)
|
Juin 2025
|-- Phase 5 (Jobs)
|-- Phase 7 complete
|-- v1.0 Production Release
|
2025-2026
|-- Phase 6 (Plugin System V2)
|-- Nouveaux dialects (Oracle, MongoDB)
|-- v2.0
```

---

## Conclusion

DataForge Studio est une **application bien architecturee** avec un potentiel solide. Les phases 1 et 2 demontrent une bonne capacite d'execution. Pour le POC v0.9.xx:

**Priorite absolue**: Phase 3 (Execution des Scripts) - c'est la fonctionnalite qui transforme l'outil d'un "explorateur de DB" en une "plateforme DATA complete".

**Corrections realisees (Janvier 2025)**:
- ~~Completer support MySQL (dialect + loader + factories)~~ Done
- ~~Fix PRAGMA injection (securite)~~ Done

**A ne PAS faire maintenant**:
- Refactoring massif (attendre v1.0)
- MongoDB/Oracle (pas de base de test, pas de besoin immediat)
- Tests exhaustifs (incrementer progressivement)

Le ratio **60% nouveautes / 40% corrections** est optimal pour cette phase de developpement.
