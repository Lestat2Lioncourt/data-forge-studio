# DataForge Studio - Roadmap & Analyse

**Version**: 0.6.2
**Objectif**: POC v0.9.xx / Production v1.0
**Date d'analyse**: Janvier 2025 (initiale) / Fevrier 2026 (audit #2)

---

## Analyse Globale de la Solution (Audit #2 - 28/02/2026)

### Scores sur 10

| Critere | Score | Evol. | Justification |
|---------|-------|-------|---------------|
| **Structure de l'application** | 8/10 | = | Architecture plugin bien concue (10 plugins), separation UI/Core/Database, patterns Repository/Factory/Observer. 201 fichiers Python. Points a ameliorer: 11 fichiers > 500 lignes (config_db.py: 2547, database_manager.py: 2536) |
| **Qualite du code** | 6.5/10 | -0.5 | 386 `except Exception` generiques, 46 except+pass silencieux, 3 bare `except:`. Duplication critique: PostgreSQL URL parser x4, "Open in Explorer" x4, DataFrameTableModel x2. 3 dependances inutilisees (sqlalchemy, tabulate, colorama) |
| **Gestion de la securite** | 6.5/10 | -0.5 | Credentials via keyring (bon). **Nouveau risque**: noms de tables injectes via f-string dans SQL (database_manager.py, data_viewer_widget.py). `subprocess shell=True` avec path utilisateur (scripts_manager.py:413). Acceptable pour outil interne mais a corriger |
| **Maintenabilite** | 6.5/10 | -0.5 | Bonne modularite plugin, mais coexistence config_db.py (legacy) et repositories (moderne) = dette technique majeure. Tests: 7 fichiers (1517 lignes) dont 1 casse (test_theme_patch.py). Couverture estimee ~15% |
| **Fiabilite** | 7/10 | -0.5 | 451 `.connect()` vs 22 `.disconnect()` = risque fuites memoire. 5 managers sans `closeEvent/cleanup`. config_db.py: connexions SQLite sans context manager (risque fuite) |
| **Performance** | 7/10 | = | Caching (schema_cache, cachetools, icon caches), lazy loading, connection pooling (pour repositories). config_db.py cree une connexion a chaque appel (~103 sites). Pas d'async generalise |
| **Extensibilite** | 8.5/10 | = | Excellent systeme de plugins, dialects extensibles, theme system v2 modulaire, pastilles colorees par connexion |
| **Documentation** | 7/10 | -0.5 | 23 guides utilisateur, README complet. Pas de documentation API developpeur. Certaines classes majeures sans docstring (DatabaseManager, QueryTab) |
| **UX/UI** | 8.5/10 | +0.5 | PySide6, themes personnalisables, i18n (3 langues), pastilles colorees par connexion, workspace favori, raccourci bureau, onglet "+" pour requetes. ES incomplet (69/89 cles) |

**Score Global: 7.3/10** (vs 7.4 precedemment) — La croissance rapide des fonctionnalites a creuse la dette technique

---

## Bilan

### Points Positifs (+)

1. **Architecture plugin exemplaire**
   - 10 plugins bien isoles avec lifecycle complet
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
   - 3 langues (EN, FR, ES) — EN/FR parfaitement synchronises (89 cles)
   - Systeme modulaire par plugin
   - Fallback chain robuste

6. **Code moderne Python**
   - Dataclasses pour les models
   - Type hints partiels, pathlib pour les chemins
   - PySide6 moderne, pas d'imports circulaires (TYPE_CHECKING bien utilise)

7. **Deploiement offline**
   - Package offline complet (Python + .venv inclus)
   - Generation automatisee via menu Tools
   - Creation raccourci bureau multi-plateforme

8. **UX enrichie recemment** *(nouveau)*
   - Pastilles colorees par connexion BDD (arbre + onglets)
   - Workspace favori avec auto-expand
   - Onglet "+" pour creation rapide de requetes
   - Nettoyage toolbar (suppression boutons redondants)

### Points Negatifs (-)

1. **Fichiers trop volumineux** (aggrave)
   - `config_db.py`: 2547 lignes (+304 vs audit #1)
   - `database_manager.py`: 2536 lignes (+264 vs audit #1)
   - `query_tab.py`: 2090 lignes (+268)
   - 11 fichiers > 500 lignes au total
   - Besoin urgent de refactoring en sous-modules

2. ~~**Injections SQL PRAGMA**~~ **CORRIGE (Phase 3.1)**

3. ~~**Support MySQL incomplet**~~ **CORRIGE (Phase 3.1)**

4. ~~**Injection SQL via noms de tables**~~ **CORRIGE** (quoting dialect-specific via `build_preview_sql()`)

5. **Duplication de code significative** *(nouveau)*
   - PostgreSQL URL parser copie-colle 4 fois (~100 lignes)
   - "Open in File Explorer" copie-colle 4 fois
   - DataFrameTableModel defini dans 2 fichiers paralleles
   - SELECT query generation dupliquee dans database_manager.py

6. **Gestion d'erreurs degradee**
   - 386 `except Exception` generiques vs ~116 exceptions specifiques
   - 46 `except` + `pass` (erreurs avalees silencieusement)
   - 3 bare `except:` (data_viewer_widget.py:263,271 + rootfolder_manager.py:244)
   - config_db.py est le pire offenseur (46 except generiques)

7. **Fuites memoire potentielles** *(nouveau)*
   - 451 `.connect()` vs 22 `.disconnect()` (ratio 20:1)
   - 5 managers sans `closeEvent`/`cleanup` (workspace, image_library, queries, scripts, settings)
   - Seulement 18 `deleteLater()` pour une app avec creation dynamique de widgets

8. **Couverture de tests tres faible**
   - 7 fichiers de tests (1517 lignes) pour 201 fichiers source (60,809 lignes)
   - test_theme_patch.py reference un module inexistant (`quick_theme_frame`) → test casse
   - Pas de tests pour: managers, dialogs, sql_formatter, ftp_client, config_db
   - Couverture estimee: ~15% (revue a la baisse vs estimation precedente de 30%)

9. **Dependances inutilisees** *(nouveau)*
   - `sqlalchemy` (~20MB) — aucun import dans le code source
   - `tabulate` — aucun import dans le code source
   - `colorama` — aucun import dans le code source

10. **Coexistence config_db.py / repositories** *(nouveau)*
    - Deux systemes de persistence paralleles pour la meme base SQLite
    - config_db.py: connexions manuelles sans context manager, `.close()` oubliable
    - repositories: ConnectionPool avec context manager (propre)
    - 88 appels `get_config_db()` dans 37 fichiers

11. **i18n incomplete**
    - ES manque 20 cles vs EN/FR
    - Strings hardcodees en francais dans le code source (database_manager.py: "pyodbc requis pour les bases Access", "Fichier Access introuvable")
    - Strings hardcodees en anglais (query_tab.py:668, divers DialogHelper)

12. **Configuration stockee dans l'arbre source** (`_AppConfig/`)
    - Pas de chemin OS standard (`%APPDATA%`, `~/.config/`)
    - Perdue en cas de reinstallation
    - `UserPreferences.get()`: bug sur nombres negatifs (`"-1".isdigit()` = False)

---

## Risques Identifies

### Risques Techniques

| Risque | Severite | Impact | Mitigation |
|--------|----------|--------|------------|
| ~~**SQL Injection PRAGMA**~~ | ~~Moyenne~~ | ~~Faible~~ | **CORRIGE** (Phase 3.1) |
| ~~**SQL Injection noms de tables**~~ | ~~Moyenne~~ | ~~Faible~~ | **CORRIGE** (build_preview_sql) |
| **Fichiers monolithiques** (aggrave) | Haute | Maintenabilite tres reduite | Refactoring progressif — **urgent pour database_manager.py** |
| ~~**Fuites memoire managers**~~ | ~~Haute~~ | ~~Degradation RAM~~ | **CORRIGE** (cleanup ajoute a 5 managers) |
| **config_db.py sans context manager** *(nouveau)* | Moyenne | Fuite connexions SQLite | Migration progressive vers repositories |
| **Absence async** | Moyenne | UI freeze possible | QThread existant, a etendre |
| ~~**Test casse (test_theme_patch.py)**~~ | ~~Faible~~ | ~~CI cassee~~ | **CORRIGE** (tests supprimes) |
| ~~**Deps inutilisees**~~ | ~~Faible~~ | ~~Taille install~~ | **CORRIGE** (sqlalchemy, tabulate, colorama supprimes) |
| **subprocess shell=True** *(nouveau)* | Faible | Injection si path malicieux | Supprimer `shell=True` dans scripts_manager.py |

### Risques Fonctionnels

| Risque | Severite | Impact | Mitigation |
|--------|----------|--------|------------|
| **Scripts non executables** | Haute | Feature incomplete | Phase 3 prioritaire |
| ~~**MySQL backend manquant**~~ | ~~Haute~~ | ~~Feature incomplete~~ | **CORRIGE** (Phase 3.1) |
| **MongoDB/Oracle** | Faible | Prevu mais non prioritaire | Implementer quand besoin |
| **Jobs non fonctionnels** | Haute | Feature incomplete | Phase 5 |
| **i18n ES incomplete** *(nouveau)* | Faible | UX degradee pour utilisateurs ES | Completer les 20 cles manquantes |

---

## Plan de Correctifs par Priorite

### P0 - Critique (POC 0.9.xx)

| Correctif | Fichier(s) | Effort | Status |
|-----------|------------|--------|--------|
| Implementer execution des scripts | Phase 3 complete | 3-4j | **REPORTE** |
| ~~Completer support MySQL~~ | ~~mysql_dialect.py, mysql_loader.py, factories~~ | ~~1-1.5j~~ | **Done** |
| ~~Corriger PRAGMA SQL injection~~ | ~~sqlite_loader.py, schema_cache.py, sqlite_dialect.py~~ | ~~0.5j~~ | **Done** |

### P1 - Important (v0.9.xx)

| Correctif | Fichier(s) | Effort | Status |
|-----------|------------|--------|--------|
| ~~Aide contextuelle~~ | ~~ui/frames/help_frame.py~~ | ~~1j~~ | **Done** (Phase 3.2) |
| ~~Fenetre d'aide detachable~~ | ~~ui/frames/help_frame.py~~ | ~~0.5j~~ | **Done** (Phase 3.2) |
| ~~Coherence visuelle fenetres~~ | ~~Tous les dialogs~~ | ~~1j~~ | **Done** (Phase 3.3) |
| Extraire constants.py | constants.py + 15 fichiers | 1j | **Done** |
| Factoriser PostgreSQL URL parser | utils/connection_helpers.py + 4 fichiers | 0.5j | **Done** |
| Factoriser "Open in Explorer" | utils/os_helpers.py + 4 managers | 0.5j | **Done** |
| Supprimer deps inutilisees | pyproject.toml | 10min | **Done** |
| Fixer test_theme_patch.py | tests/test_theme_patch.py | 15min | **Done** |
| Ajouter cleanup aux managers | workspace, image_library, queries, scripts, settings | 1j | **Done** |

### P1.5 - Important (v1.0)

| Correctif | Fichier(s) | Effort | Status |
|-----------|------------|--------|--------|
| Refactorer database_manager.py | ui/managers/database_manager.py | 2-3j | Todo |
| Migrer config_db.py vers repositories | database/config_db.py → repositories/ | 3-4j | Todo *(nouveau)* |
| Quoting dialect-specific pour noms de tables | constants.py + database_manager.py + data_viewer_widget.py | 1j | **Done** |
| Completer type hints | Tous les fichiers | 2j | Todo |
| Resoudre TODOs restants | main_window.py, scripts | 1j | Todo |
| Fusionner DataFrameTableModel (2 copies) | core/ dead code supprime | 0.5j | **Done** |
| Supprimer code deprecie (I18n class) | config/i18n/__init__.py | 0.5j | **Done** |

### P2 - Amelioration (v1.0+)

| Correctif | Fichier(s) | Effort | Status |
|-----------|------------|--------|--------|
| Augmenter couverture tests (40%) | tests/ | 3-4j | Todo |
| Creer i18n ES | config/i18n/core/es.json | 2h | Todo *(corrige: ES n'existait pas)* |
| Supprimer strings hardcodees FR/EN | 5 fichiers + en.json/fr.json | 1j | **Done** (35+ strings) |
| Ajouter docstrings API | Tous les modules publics | 2j | Todo |
| Implementer Jobs & Orchestration | Phase 5 complete | 4-5j | Todo |
| Reducer except generiques (cibler 50%) | Principaux offenseurs | 2j | Todo (3 bare except: corriges) |

### P3 - Nice to Have (v2.0)

| Correctif | Fichier(s) | Effort | Status |
|-----------|------------|--------|--------|
| Plugin System V2 complet | Phase 6 | 5-6j | Todo |
| Support Oracle/MongoDB | dialects/ + loaders/ | 3-4j | Todo |
| Operations async generalisees | Core refactoring | 3j | Todo |
| Config vers chemin OS standard | database/config_db.py | 1j | Todo *(nouveau)* |

---

## Nouveautes vs Corrections: Recommandation

**Contexte**: Application Beta, profils DATA, POC v0.9.xx

### Recommandation: Equilibre 50% Nouveautes / 50% Corrections

**Justification** (evolution vs 60/40 precedent):
1. La dette technique s'est accumulee (fichiers + volumineux, duplications, fuites memoire potentielles)
2. Les correctifs P1 sont rapides a implementer (factorisation, deps, test casse) = quick wins
3. La fiabilite doit etre consolider avant le POC v0.9.xx
4. Les fonctionnalites de base sont desormais solides (DB, workspaces, FTP, queries, themes)

**Priorites immediates**:
1. **Quick wins P1** : factorisation code, suppression deps, fix test (2j)
2. **Phase 3** : Execution des Scripts (nouveaute critique) - **REPORTE, en reflexion**
3. **Cleanup managers** : ajouter cleanup/disconnect aux 5 managers (1j)

**Fonctionnalites livrees depuis (Dec 2025 - Fev 2026)**:
- Navigation FTP dans les workspaces (ftproot_plugin)
- Fallback pytds pour SQL Server (quand pyodbc indisponible)
- Package offline avec generation automatisee (menu Tools)
- Ameliorations saved queries (execution, edit/update)
- Formatage SQL dans l'editeur de requetes
- Connexions DB en thread separe (pas de freeze UI)
- Pastilles colorees par connexion BDD (arbre + onglets) *(nouveau)*
- Workspace favori avec auto-expand *(nouveau)*
- Onglet "+" pour creation rapide de requetes *(nouveau)*
- Creation raccourci bureau (Windows/macOS/Linux) *(nouveau)*
- Nettoyage toolbar et tab Info workspace *(nouveau)*

**Reporter a v1.0**:
- Refactoring database_manager.py et config_db.py
- Couverture tests 40%
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

---

### Phase 3.3: Coherence Visuelle des Fenetres (TERMINE)

**Objectif**: Appliquer le theme de l'application a toutes les fenetres (principales et enfants)

| Tache | Status | Priorite |
|-------|--------|----------|
| Identifier les fenetres sans style applique | Done | P1 |
| Creer template PopupWindow avec theme | Done | P1 |
| Migrer HelpWindow vers PopupWindow | Done | P1 |
| Migrer ImageFullscreenDialog | Differe | P3 |
| Migrer SaveImageDialog | Differe | P3 |
| Corriger AboutDialog (couleurs hardcodees) | Done | P1 |
| Corriger ScriptFormatDialog | Done | P1 |
| Corriger dialogs restants (SaveQuery, DistributionAnalysis) | Done | P2 |

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
| Extraire constants (timeouts, limits) | **Done** | P1 |

*Note: MongoDB et Oracle sont des fonctionnalites planifiees pour le futur (pas de base de test disponible actuellement).*
*Note: MariaDB utilise le meme backend que MySQL (alias enregistre).*

---

### Phase 3.4: Ameliorations UX Connexions (TERMINE - Fevrier 2026)

**Objectif**: Ameliorer l'identification visuelle des connexions BDD

| Tache | Status |
|-------|--------|
| Pastilles colorees par connexion (arbre + onglets) | Done |
| Palette 7 couleurs distinctes auto-assignees | Done |
| Color picker dans dialogs (edit + creation) | Done |
| Clic droit "Changer la couleur" | Done |
| Onglet "+" pour creation rapide de requetes | Done |
| Workspace favori (auto-expand, clic droit toggle) | Done |
| Creation raccourci bureau multi-plateforme | Done |
| Nettoyage toolbar (suppression boutons redondants) | Done |

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
| Refactorer DatabaseManager (~2536 lignes) | Todo | P1 |
| Migrer config_db.py vers repositories | Todo *(nouveau)* | P1 |
| Creer constants.py | **Done** | P1 |
| Factoriser PostgreSQL URL parser (x4) | **Done** | P1 |
| Factoriser "Open in Explorer" (x4) | **Done** | P1 |
| Fusionner DataFrameTableModel (x2) | **Done** | P2 |
| Deduplication code connexion | Todo | P2 |
| Parametrer requetes schema loaders | Todo | P2 |
| Couverture tests (40%) | Todo | P2 |
| Thread-safe singletons | Todo | P2 |
| Completer type hints | Todo | P1 |
| Ajouter docstrings API | Todo | P2 |
| Ajouter cleanup aux 5 managers | **Done** | P1 |
| Supprimer deps inutilisees | **Done** | P1 |
| Fixer test_theme_patch.py | **Done** | P1 |
| Supprimer code deprecie (I18n) | **Done** | P2 |
| Quoting SQL noms de tables | **Done** | P2 |
| Reducer except generiques | Todo *(nouveau)* | P2 |

---

## Statistiques du Projet

| Metrique | Valeur | Evolution |
|----------|--------|-----------|
| Fichiers Python | 201 | +1 |
| Lignes de code (src/) | 60,809 | +809 |
| Fichiers de tests | 7 | = |
| Lignes de tests | 1,517 | = |
| Tests en echec | 0 (79 passed) | *(corrige)* |
| Plugins | 10 | = |
| Dialects DB | 5 (SQLite, PostgreSQL, SQL Server, MySQL/MariaDB, Access) | = |
| Langues i18n | 2 (EN: 89 cles, FR: 89 cles) | *(ES n'existait pas)* |
| Themes | 4 | = |
| Guides documentation | 23 | = |
| Commits depuis Dec 2025 | 133 | +14 |
| `except Exception` generiques | 386 | *(nouveau metrique)* |
| `.connect()` sans `.disconnect()` | 429 | *(nouveau metrique)* |
| Fichiers > 500 lignes | 11 | *(nouveau metrique)* |

*Statistiques mises a jour: 28 Fevrier 2026*

---

## Timeline

### Historique reel

```
Janvier 2025
|-- Phase 1 & 2 terminees (dev local, pre-git)
|-- Analyse globale & ROADMAP initial redige
|-- Phase 3.1 (MySQL backend + PRAGMA fix)
|
Fevrier - Novembre 2025
|-- PAUSE (~10 mois)
|-- Projet en standby, pas de commits
|
Decembre 2025
|-- Publication sur Git (v0.2.0 initial release)
|-- Migration PySide6 (v0.5.0)
|-- Themes, DataExplorer, query formatting
|-- Phases 3.2 & 3.3 terminees
|-- v0.5.3
|
Janvier 2026
|-- Support FTP, workspace ameliorations
|-- Package offline, pytds fallback
|-- v0.5.8 / v0.5.9
|
Fevrier 2026
|-- Menu Tools, generation package offline
|-- SQL formatting, settings
|-- Phase 3.4 (pastilles colorees, workspace favori, onglet "+")
|-- Raccourci bureau, nettoyage UI
|-- Audit #2 complet
|-- v0.6.2 (actuel)
```

### Projection (estimee)

```
Q1 2026 (en cours)
|-- Quick wins Phase 7 (factorisation, deps, cleanup managers)
|-- Phase 4 (Theming Icons)
|-- v0.7.0
|
Q2 2026
|-- Phase 3 (Execution Scripts) - si modele defini
|-- Phase 7 suite (refactoring database_manager.py)
|-- Migration config_db.py → repositories
|-- v0.8.0 - v0.9.0 POC Release
|
S2 2026
|-- Phase 5 (Jobs & Orchestration)
|-- EVO-1 (Mode CLI)
|-- Couverture tests 40%
|-- v1.0 Production Release
|
2027+
|-- Phase 6 (Plugin System V2)
|-- Nouveaux dialects (Oracle, MongoDB)
|-- EVO-2 (Tunnel SSH)
|-- v2.0
```

---

## Conclusion

DataForge Studio est une **application bien architecturee** avec un potentiel solide. Depuis Decembre 2025, le developpement est intensif avec 133 commits en 3 mois, portant le projet de v0.2.0 a v0.6.2.

**Score global: 7.3/10** (leger recul vs 7.4) — La croissance rapide des fonctionnalites (+5 features majeures en fevrier) a creuse la dette technique. Les fichiers monolithiques continuent de grossir, la duplication de code s'accumule, et les metriques de fiabilite (connect/disconnect, cleanup, tests) revelent des fragilites structurelles.

**Bilan des corrections realisees**:
- ~~MySQL backend (dialect + loader + factories)~~ Done
- ~~PRAGMA injection (securite)~~ Done
- ~~Aide contextuelle + fenetre detachable~~ Done
- ~~Coherence visuelle des fenetres~~ Done
- Navigation FTP, pytds fallback, package offline Done
- Pastilles colorees, workspace favori, onglet "+", raccourci bureau Done *(nouveau)*

**Actions immediates recommandees** (2-3 jours):
1. Supprimer deps inutilisees: sqlalchemy, tabulate, colorama (10min)
2. Factoriser PostgreSQL URL parser dans utils/ (2h)
3. Factoriser "Open in Explorer" dans utils/ (1h)
4. Fixer ou supprimer test_theme_patch.py (15min)
5. Ajouter cleanup/disconnect aux 5 managers (1j)

**Prochaine etape majeure**: Phase 3 (Execution des Scripts) — quand le modele d'execution sera defini. C'est la fonctionnalite qui transforme l'outil d'un "explorateur de DB" en une "plateforme DATA complete".

**A ne PAS faire maintenant**:
- Refactoring massif config_db.py (attendre v1.0, prevoir 3-4j)
- MongoDB/Oracle (pas de base de test, pas de besoin immediat)
- Tests exhaustifs (incrementer progressivement, viser 40% pour v1.0)

Le ratio **50% nouveautes / 50% corrections** est desormais recommande pour consolider la base avant le POC.

---

## Evolutions Futures - Nouvelles Fonctionnalites

*Cette section regroupe les nouvelles fonctionnalites planifiees, distinctes des corrections et ameliorations du code existant.*

### EVO-1: Mode CLI & Scripts Serveur

**Objectif**: Execution de scripts en ligne de commande pour deploiement sur serveurs (Windows puis Unix)

#### Modele conceptuel : Script vs Instance

| Concept | Script | Instance de Script |
|---------|--------|-------------------|
| Nature | Code reutilisable (template) | Configuration specifique |
| Exemple | "File Dispatcher" | "GRDF_Dispatch_Metrics" |
| Rattachement workspace | Non | Oui |
| Deploiement serveur | Non (dans la solution) | Oui (dossier externe) |
| Parametres | Definition (YAML) | Valeurs concretes |

**Principe** : C'est une *instance* de script (et non un script) qui est rattachee a un workspace et deployee sur serveur.

#### EVO-1.1 Infrastructure CLI
- [ ] Point d'entree `dataforge_cli.py`
- [ ] Parser d'arguments (argparse)
- [ ] Commandes : `dispatch`, `getdata`, `help`
- [ ] Codes retour standardises (0=OK, 1=ERR, 2=WARN)
- [ ] Logging fichier + console

#### EVO-1.2 Gestion des Credentials
- [ ] Fichier `credentials.json` pour stocker les acces FTP
- [ ] Mot de passe en clair (serveur isole) + permissions fichier restrictives

#### EVO-1.3 DispatchFiles - Ameliorations
- [ ] Fichier `dispatch_config.json` a la racine du noeud
- [ ] Regles wildcard : `pattern` → `target`
- [ ] Option `fallback_to_auto` vers logique Contrat_Dataset existante
- [ ] Options CLI : `--dry-run`, `--config`

#### EVO-1.4 GetData - Nouveau Script
- [ ] Copie de fichiers entre noeuds (FTP ↔ RootFolder)
- [ ] Fichier `getdata_config.json` (source, destination, options)
- [ ] Options : delete_after_copy, overwrite, file_pattern

#### EVO-1.5 Deploiement Serveur
- [ ] Copie complete de la solution (src + .venv inclus) pour serveurs isoles
- [ ] Dossiers de lancement externes (scripts qui pointent vers l'installation)
- [ ] Script wrapper Windows (`dataforge-cli.bat`)
- [ ] Script wrapper Unix (`dataforge-cli.sh`)
- [ ] Documentation deploiement : structure dossiers, permissions, Task Scheduler / crontab
- [ ] Compatibilite chemins Unix (pathlib)

---

### EVO-2: Tunnel SSH pour connexions SQL Server

**Objectif**: Permettre les connexions SQL Server via un tunnel SSH (port forwarding local), pour les environnements ou les ports SQL ne sont pas exposes directement.

**Priorite**: Basse (en attente)

**Principe**: Ouvrir un tunnel SSH (paramiko) vers un serveur bastion, redirigeant un port local vers le SQL Server distant. La connexion SQL (pyodbc/pytds) se fait ensuite sur `localhost:{port_local}`.

```
[App] → localhost:port_local → (tunnel SSH) → bastion → serveur-sql:1433
```

#### Fonctionnalites prevues
- [ ] Option "Via tunnel SSH" dans le dialog de connexion SQL Server
- [ ] Configuration : hote SSH, port (22), utilisateur SSH
- [ ] Authentification SSH par mot de passe ou par cle privee (.pem/.ppk)
- [ ] Ouverture automatique du tunnel a la connexion, fermeture a la deconnexion
- [ ] Gestion du cycle de vie du tunnel (timeout, reconnexion)
- [ ] Stockage du chemin de la cle privee (pas la cle elle-meme) dans la config

#### Points techniques
- `paramiko` est deja dans les dependances (utilise pour FTP)
- Passphrase de cle : demander a chaque connexion ou stocker dans keyring
- Un tunnel par connexion SQL (pas de mutualisation)

---

*Derniere mise a jour: 2026-02-28*
