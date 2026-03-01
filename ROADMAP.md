# DataForge Studio - Roadmap & Analyse

**Version**: 0.6.3
**Objectif**: POC v0.9.xx / Production v1.0
**Date d'analyse**: Janvier 2025 (initiale) / Fevrier 2026 (audit #2) / Mars 2026 (audit #3)

---

## Analyse Globale de la Solution (Audit #3 - 01/03/2026)

### Scores sur 10

| Critere | Score | Evol. | Justification |
|---------|-------|-------|---------------|
| **Structure de l'application** | 8.5/10 | +0.5 | 215 fichiers Python. Les 2 God Objects majeurs ont ete refactores: config_db.py (2547→474L, facade pure) et database_manager.py (2536L→ mixins). Pattern Repository entierement branche (10 repos). Reste: query_tab.py (2061L), 31 fichiers > 500L |
| **Qualite du code** | 7/10 | +0.5 | 341 `except Exception` (vs 386, -45), **0 bare `except:`** (vs 3), ~17 except+pass (vs 46). config_db.py: 46→0 exceptions generiques. Duplications majeures resolues (PostgreSQL parser, Open in Explorer). Reste: DataFrameTableModel x2. 0 dep inutilisee. 6 TODO |
| **Gestion de la securite** | 7/10 | +0.5 | Credentials via keyring (bon). Quoting dialect-specific operationnel pour noms de tables (build_preview_sql). Reste: 4 f-string SQL en fallback (query_gen_mixin, access_dialect, data_loader), 3 `subprocess shell=True` (os_helpers, main_window, scripts_manager). Acceptable pour outil interne |
| **Maintenabilite** | 7.5/10 | +1.0 | **Dette technique majeure resolue**: coexistence config_db.py/repositories eliminee — config_db.py est maintenant une pure facade. 10 repositories actifs. 79 tests passent (0 echec). Couverture estimee ~15% (6 fichiers test, 1463L). 0 fichier mort detecte |
| **Fiabilite** | 7.5/10 | +0.5 | config_db.py utilise desormais ConnectionPool avec context managers (77 `with` dans repos). ~103 sites de fuite connexion elimines. 448 `.connect()` vs 25 `.disconnect()` (ratio 18:1, Qt signals). 24 fichiers avec cleanup/closeEvent (vs 5 manquants avant). SchemaManager: `finally: conn.close()` |
| **Performance** | 7.5/10 | +0.5 | config_db.py ne cree plus de connexion par appel — tout via ConnectionPool (reuse). TTLCache (60s, 100 entries), schema_cache. 4 QThread workers (DB, FTP, scan). 21 fichiers avec lazy loading. Pas d'async generalise |
| **Extensibilite** | 8.5/10 | = | 10 plugins UI, 5 dialects DB (SQLite/PostgreSQL/SQL Server/MySQL/Access), 3-4 themes JSON, Factory pattern. Plugin system bien defini (base_plugin + plugin_manager) |
| **Documentation** | 7/10 | = | 24 guides utilisateur, README 428L. Docstrings ameliorees (repositories, config_db). Toujours pas de documentation API developpeur standalone |
| **UX/UI** | 8.5/10 | = | PySide6, 3-4 themes, i18n EN/FR (659 cles, parite 100%). Pastilles colorees, workspace favori, onglet "+". 30+ widgets reutilisables. Reste: ~50 strings FR hardcodees, ES inexistant |

**Score Global: 7.7/10** (vs 7.3 precedemment) — Le refactoring config_db.py et la resolution de la dette technique ont significativement ameliore la maintenabilite, la fiabilite et la performance

### Historique des scores

| Critere | Audit #1 | Audit #2 | Audit #3 | Tendance |
|---------|----------|----------|----------|----------|
| Structure | 8 | 8 | 8.5 | ↗ |
| Qualite du code | 7 | 6.5 | 7 | ↗ |
| Securite | 7 | 6.5 | 7 | ↗ |
| Maintenabilite | 7 | 6.5 | 7.5 | ↗↗ |
| Fiabilite | 7.5 | 7 | 7.5 | ↗ |
| Performance | 7 | 7 | 7.5 | ↗ |
| Extensibilite | 8.5 | 8.5 | 8.5 | = |
| Documentation | 7.5 | 7 | 7 | = |
| UX/UI | 8 | 8.5 | 8.5 | = |
| **Global** | **7.4** | **7.3** | **7.7** | **↗** |

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
   - 2 langues (EN, FR) — 659 cles chacune, parite 100%
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

8. **UX enrichie**
   - Pastilles colorees par connexion BDD (arbre + onglets)
   - Workspace favori avec auto-expand
   - Onglet "+" pour creation rapide de requetes
   - 30+ widgets reutilisables

9. **Pattern Repository complet** *(nouveau audit #3)*
   - 10 repositories specialises actifs (DB, Query, Project, FileRoot, FTPRoot, Script, Job, ImageRootfolder, SavedImage, UserPreferences)
   - config_db.py = pure facade (474L), zero SQL inline
   - ConnectionPool avec context managers pour toutes les operations DB
   - Helpers generiques pour relations workspace-ressource (4 methodes, 30 delegations)

### Points Negatifs (-)

1. ~~**Fichiers trop volumineux (config_db, database_manager)**~~ **CORRIGE (audit #3)** — config_db.py: 2547→474L (facade), database_manager.py: 2536L→ mixins. Reste: query_tab.py (2061L), 31 fichiers > 500L

2. ~~**Injections SQL PRAGMA**~~ **CORRIGE (Phase 3.1)**

3. ~~**Support MySQL incomplet**~~ **CORRIGE (Phase 3.1)**

4. ~~**Injection SQL via noms de tables**~~ **CORRIGE** (quoting dialect-specific via `build_preview_sql()`)

5. ~~**Duplication de code significative**~~ **LARGEMENT CORRIGE** — PostgreSQL parser factorise, Open in Explorer factorise, DataFrameTableModel: reste 2 copies (ui/widgets + core/)

6. **Gestion d'erreurs a ameliorer** (ameliore)
   - 341 `except Exception` generiques (vs 386, -12%)
   - ~17 `except` + `pass` (vs 46, -63%)
   - **0 bare `except:`** (vs 3, -100%)
   - config_db.py: 46→0 exceptions generiques

7. ~~**Fuites memoire managers**~~ **CORRIGE** — 24 fichiers avec cleanup/closeEvent. config_db.py utilise ConnectionPool (77 context managers). Reste: ratio connect/disconnect 448:25 (Qt signals)

8. **Couverture de tests faible**
   - 6 fichiers de tests (1463 lignes) pour 215 fichiers source (59,343 lignes)
   - 79/79 tests passent, 0 echec
   - Pas de tests pour: managers, dialogs, sql_formatter, ftp_client
   - Couverture estimee: ~15%

9. ~~**Dependances inutilisees**~~ **CORRIGE** (sqlalchemy, tabulate, colorama supprimes)

10. ~~**Coexistence config_db.py / repositories**~~ **CORRIGE (audit #3)** — config_db.py est desormais une pure facade delegant a 10 repositories. 0 SQL inline. ConnectionPool partage. 59 appels `get_config_db()` dans 28 fichiers

11. **i18n incomplete** (ameliore)
    - ES n'existe pas (seulement EN/FR)
    - ~50 strings hardcodees en francais dans le code source
    - EN/FR: 659 cles, parite 100%

12. **Configuration stockee dans l'arbre source** (`_AppConfig/`)
    - Pas de chemin OS standard (`%APPDATA%`, `~/.config/`)
    - Perdue en cas de reinstallation

13. **query_tab.py reste volumineux** (2061L, 68 methodes)
    - Plus gros fichier du projet
    - Candidat prioritaire pour un refactoring en mixins

---

## Risques Identifies

### Risques Techniques

| Risque | Severite | Impact | Mitigation |
|--------|----------|--------|------------|
| ~~**SQL Injection PRAGMA**~~ | ~~Moyenne~~ | ~~Faible~~ | **CORRIGE** (Phase 3.1) |
| ~~**SQL Injection noms de tables**~~ | ~~Moyenne~~ | ~~Faible~~ | **CORRIGE** (build_preview_sql) |
| ~~**Fichiers monolithiques (config_db, database_manager)**~~ | ~~Haute~~ | ~~Maintenabilite tres reduite~~ | **CORRIGE** (config_db→facade, database_manager→mixins) |
| **query_tab.py monolithique** (2061L) | Moyenne | Maintenabilite reduite | Refactoring en mixins — priorite P1.5 |
| ~~**Fuites memoire managers**~~ | ~~Haute~~ | ~~Degradation RAM~~ | **CORRIGE** (cleanup ajoute, 24 fichiers) |
| ~~**config_db.py sans context manager**~~ | ~~Moyenne~~ | ~~Fuite connexions SQLite~~ | **CORRIGE** (audit #3: ConnectionPool + 77 context managers) |
| **Absence async** | Moyenne | UI freeze possible | 4 QThread workers existants, a etendre |
| ~~**Test casse (test_theme_patch.py)**~~ | ~~Faible~~ | ~~CI cassee~~ | **CORRIGE** |
| ~~**Deps inutilisees**~~ | ~~Faible~~ | ~~Taille install~~ | **CORRIGE** |
| **subprocess shell=True** | Faible | Injection si path malicieux | Supprimer `shell=True` (3 sites: os_helpers, main_window, scripts_manager) |
| **4 f-string SQL en fallback** | Faible | Injection theorique | Ajouter quoting dans query_gen_mixin, access_dialect, data_loader |

### Risques Fonctionnels

| Risque | Severite | Impact | Mitigation |
|--------|----------|--------|------------|
| **Scripts non executables** | Haute | Feature incomplete | Phase 3 prioritaire |
| ~~**MySQL backend manquant**~~ | ~~Haute~~ | ~~Feature incomplete~~ | **CORRIGE** (Phase 3.1) |
| **MongoDB/Oracle** | Faible | Prevu mais non prioritaire | Implementer quand besoin |
| **Jobs non fonctionnels** | Haute | Feature incomplete | Phase 5 |
| **i18n ES inexistant** | Faible | Pas de support espagnol | Creer config/i18n/core/es.json |

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
| ~~Refactorer database_manager.py~~ | ~~ui/managers/database_manager.py~~ | ~~2-3j~~ | **Done** (mixins) |
| ~~Migrer config_db.py vers repositories~~ | ~~database/config_db.py → repositories/~~ | ~~3-4j~~ | **Done** (audit #3) |
| Quoting dialect-specific pour noms de tables | constants.py + database_manager.py + data_viewer_widget.py | 1j | **Done** |
| Refactorer query_tab.py en mixins (2061L) | ui/tabs/query_tab.py | 2-3j | Todo *(nouveau, prioritaire)* |
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
| Reducer except generiques (cibler 50%) | Principaux offenseurs | 2j | Todo (341→~170, 0 bare except) |
| Supprimer `shell=True` dans subprocess | os_helpers, main_window, scripts_manager | 0.5j | Todo *(nouveau)* |
| Ajouter quoting aux 4 f-string SQL | query_gen_mixin, access_dialect, data_loader | 0.5j | Todo *(nouveau)* |

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

### Recommandation: 60% Nouveautes / 40% Corrections

**Justification** (evolution vs 50/50 precedent):
1. La dette technique majeure est resolue (config_db + database_manager refactores, deps nettoyees, cleanup managers)
2. Les correctifs P1 restants sont mineurs (type hints, TODOs)
3. Les fonctionnalites de base sont solides et bien architecturees (10 repos, facade, ConnectionPool)
4. Le score est passe de 7.3 a 7.7 — la base est assez saine pour accelerer les fonctionnalites

**Priorites immediates**:
1. **Refactoring query_tab.py** en mixins (2061L, dernier gros fichier) — P1.5
2. **Phase 3** : Execution des Scripts (nouveaute critique) - **REPORTE, en reflexion**
3. **Reducer except generiques** de 341 a ~170 (-50%) — P2

**Fonctionnalites livrees depuis (Dec 2025 - Mars 2026)**:
- Navigation FTP dans les workspaces (ftproot_plugin)
- Fallback pytds pour SQL Server (quand pyodbc indisponible)
- Package offline avec generation automatisee (menu Tools)
- Ameliorations saved queries (execution, edit/update)
- Formatage SQL dans l'editeur de requetes
- Connexions DB en thread separe (pas de freeze UI)
- Pastilles colorees par connexion BDD (arbre + onglets)
- Workspace favori avec auto-expand
- Onglet "+" pour creation rapide de requetes
- Creation raccourci bureau (Windows/macOS/Linux)
- Nettoyage toolbar et tab Info workspace
- **Refactoring config_db.py** : facade pure (2547→474L, -81%) *(audit #3)*
- **10 repositories actifs** avec ConnectionPool et context managers *(audit #3)*

**Reporter a v1.0**:
- Couverture tests 40%
- Documentation API
- Operations async generalisees

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
| ~~Refactorer DatabaseManager (~2536 lignes)~~ | **Done** (mixins) | P1 |
| ~~Migrer config_db.py vers repositories~~ | **Done** (facade, audit #3) | P1 |
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
| Reducer except generiques | Todo | P2 |
| Refactorer query_tab.py en mixins | Todo *(nouveau)* | P1.5 |
| Supprimer `shell=True` subprocess | Todo *(nouveau)* | P2 |
| Quoting 4 f-string SQL restantes | Todo *(nouveau)* | P2 |

---

## Statistiques du Projet

| Metrique | Valeur | Evolution |
|----------|--------|-----------|
| Fichiers Python | 215 | +14 |
| Lignes de code (src/) | 59,343 | -1,466 |
| Fichiers de tests | 6 | -1 |
| Lignes de tests | 1,463 | -54 |
| Tests en echec | 0 (79 passed) | = |
| Plugins | 10 | = |
| Dialects DB | 5 (SQLite, PostgreSQL, SQL Server, MySQL/MariaDB, Access) | = |
| Langues i18n | 2 (EN: 659 cles, FR: 659 cles) | +570 cles/langue |
| Themes | 4 | = |
| Guides documentation | 24 | +1 |
| Commits depuis Dec 2025 | ~140 | +7 |
| `except Exception` generiques | 341 | -45 (-12%) |
| `.connect()` / `.disconnect()` | 448 / 25 | ratio 18:1 (Qt signals) |
| Fichiers > 500 lignes | 31 | +20 (croissance code) |
| Repositories actifs | 10 | *(nouveau)* |
| ConnectionPool context managers | 77 | *(nouveau)* |

*Statistiques mises a jour: 01 Mars 2026 (audit #3)*

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
|-- v0.6.3
|
Mars 2026
|-- Refactoring config_db.py → facade (2547→474L)
|-- 10 repositories actifs, ConnectionPool branche
|-- FTPRootRepository cree, ProjectRepository complete
|-- Audit #3 complet (7.3→7.7/10)
|-- v0.6.3 (actuel)
```

### Projection (estimee)

```
Q1 2026 (en cours)
|-- Refactoring query_tab.py en mixins (2061L)
|-- Phase 4 (Theming Icons)
|-- v0.7.0
|
Q2 2026
|-- Phase 3 (Execution Scripts) - si modele defini
|-- Couverture tests 25%
|-- Reducer except generiques (-50%)
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

DataForge Studio est une **application bien architecturee** avec un potentiel solide. Depuis Decembre 2025, le developpement est intensif avec ~140 commits en 4 mois, portant le projet de v0.2.0 a v0.6.3.

**Score global: 7.7/10** (+0.4 vs audit #2) — Le refactoring config_db.py (2547→474L) et la resolution de la dette technique majeure (coexistence config_db/repos, fuites connexion, duplications) ont significativement ameliore la maintenabilite (+1.0), la fiabilite (+0.5) et la performance (+0.5). La base est desormais saine pour accelerer les fonctionnalites.

**Bilan des corrections realisees**:
- ~~MySQL backend (dialect + loader + factories)~~ Done
- ~~PRAGMA injection (securite)~~ Done
- ~~Aide contextuelle + fenetre detachable~~ Done
- ~~Coherence visuelle des fenetres~~ Done
- Navigation FTP, pytds fallback, package offline Done
- Pastilles colorees, workspace favori, onglet "+", raccourci bureau Done
- **config_db.py refactore en facade** (2547→474L, 10 repos, 0 SQL inline) Done *(audit #3)*
- **database_manager.py refactore en mixins** Done

**Actions immediates recommandees** (2-3 jours):
1. Refactorer query_tab.py en mixins (2061L, dernier God Object)
2. Reducer `except Exception` generiques de 341 a ~170
3. Supprimer `shell=True` dans 3 subprocess (os_helpers, main_window, scripts_manager)
4. Ajouter quoting aux 4 f-string SQL restantes

**Prochaine etape majeure**: Phase 3 (Execution des Scripts) — quand le modele d'execution sera defini. C'est la fonctionnalite qui transforme l'outil d'un "explorateur de DB" en une "plateforme DATA complete".

**A ne PAS faire maintenant**:
- MongoDB/Oracle (pas de base de test, pas de besoin immediat)
- Tests exhaustifs (incrementer progressivement, viser 25% pour Q2, 40% pour v1.0)
- Operations async generalisees (4 QThread workers suffisent pour l'instant)

Le ratio **60% nouveautes / 40% corrections** est desormais recommande — la base technique est assez saine pour prioriser les fonctionnalites.

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

*Derniere mise a jour: 2026-03-01*
