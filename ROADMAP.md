# DataForge Studio - Roadmap & Analyse

**Version**: 0.6.9
**Objectif**: POC v0.9.xx / Production v1.0
**Date d'analyse**: Janvier 2025 (initiale) / Fevrier 2026 (audit #2) / Mars 2026 (audits #3, #4 & #5) / Avril 2026 (audits #6 & #7)

---

## Analyse Globale de la Solution (Audit #7 - 02/04/2026)

### Scores sur 10

| Critere | Score | Evol. | Justification |
|---------|-------|-------|---------------|
| **Structure de l'application** | 9.5/10 | +0.5 | 233 fichiers Python (63,304L). **11 plugins** (nouveau: ER Diagram). 11 repositories. Nouveau package `er_diagram/` (5 modules: scene, table_item, relationship_line, dialogs, export). FK/PK loaders dans les 5 dialects. Architecture modulaire: chaque nouvelle feature est un package isole |
| **Qualite du code** | 8.5/10 | = | 188 `except Exception` (+11, nouvelles features), **0 bare `except:`**. 0 dep inutilisee. 6 TODO. 11 `get_*_context_actions()` publiques. SQL formatter: `_TopLevelScanner`, `_sqlparse_format` wrapper, `expandtabs`. Mixed alias detection. Auto-indent editor |
| **Gestion de la securite** | 8/10 | = | Credentials via keyring. **0 `shell=True`**, **0 `eval()`/`exec()`**. 35 f-string SQL securisees. Smart reconnect (TCP ping avant reconnexion). Connection strings sans credentials dans la doc |
| **Maintenabilite** | 9/10 | +0.5 | **201 tests** (couverture ~25%). Delegation complete: context menus, affichage, FTP icons. Manuel utilisateur 10 chapitres + site mkdocs. Critere audit #11 applique. Tout nouveau type est automatiquement disponible partout |
| **Fiabilite** | 8/10 | +0.5 | 479 `.connect()` vs 26 `.disconnect()` (Qt signals). 24 fichiers avec cleanup/closeEvent. 20 `deleteLater()`. **Smart reconnect**: TCP ping serveur, auto-reconnexion si joignable, popup VPN sinon. ER Diagram sauvegarde positions + midpoints + zoom |
| **Performance** | 7.5/10 | = | ConnectionPool reuse. TTLCache, schema_cache. QSvgRenderer SVG. QGraphicsScene pour ER Diagrams (rendu natif Qt, performant meme avec 50+ tables). Pas d'async generalise |
| **Extensibilite** | 9.5/10 | +0.5 | **11 plugins**, 5 dialects DB, 4 themes. ER Diagram complet (data layer + UI + plugin). FK/PK loaders extensibles par dialect. SQL formatter extensible (`_TopLevelScanner`, OUTER APPLY via wrapper). Systeme de diagrammes nommes/sauvegardables |
| **Documentation** | 8/10 | +1 | Manuel utilisateur **10 chapitres** (scenarios metier, FR). Site mkdocs-material local. 20 screenshots nommes. ROADMAP avec EVO-3 ER Diagrams detaillee. Changelog complet. Aide integree dans l'app. Encore pas de doc API developpeur |
| **UX/UI** | 9.5/10 | +0.5 | **ER Diagrams interactifs** (tables draggables, FK auto-routees, midpoints, zoom, export PNG/SVG). SQL formatter: CTE hierarchie, alias =, DISTINCT/TOP, OUTER APPLY. Auto-indent + tab→espaces. Smart reconnect transparent. Workspace bouton "+". i18n EN/FR (656 cles) |

**Score Global: 8.6/10** (+0.4 vs audit #6) — Progression majeure: ER Diagrams (feature complete), documentation doublée, fiabilite en hausse (tests + smart reconnect). 5 criteres en hausse, 4 stables, 0 en baisse.

### Historique des scores

| Critere | Audit #1 | Audit #2 | Audit #3 | Audit #4 | Audit #5 | Audit #6 | Audit #7 | Tendance |
|---------|----------|----------|----------|----------|----------|----------|----------|----------|
| Structure | 8 | 8 | 8.5 | 9 | 9 | 9 | 9.5 | ↑ |
| Qualite du code | 7 | 6.5 | 7 | 8 | 8 | 8.5 | 8.5 | = |
| Securite | 7 | 6.5 | 7 | 8 | 8 | 8 | 8 | = |
| Maintenabilite | 7 | 6.5 | 7.5 | 8 | 8 | 8.5 | 9 | ↑ |
| Fiabilite | 7.5 | 7 | 7.5 | 7.5 | 7.5 | 7.5 | 8 | ↑ |
| Performance | 7 | 7 | 7.5 | 7.5 | 7.5 | 7.5 | 7.5 | = |
| Extensibilite | 8.5 | 8.5 | 8.5 | 8.5 | 8.5 | 9 | 9.5 | ↑ |
| Documentation | 7.5 | 7 | 7 | 7 | 7 | 7 | 8 | ↑ |
| UX/UI | 8 | 8.5 | 8.5 | 8.5 | 8.5 | 9 | 9.5 | ↑ |
| **Global** | **7.4** | **7.3** | **7.7** | **7.9** | **7.9** | **8.2** | **8.6** | **↑** |

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

1. ~~**Fichiers trop volumineux (config_db, database_manager, query_tab)**~~ **CORRIGE (audits #3 & #4)** — config_db.py: 2547→474L (facade), database_manager.py: 2536→209L (mixins), query_tab.py: 2061→417L (6 mixins). 29 fichiers > 500L

2. ~~**Injections SQL PRAGMA**~~ **CORRIGE (Phase 3.1)**

3. ~~**Support MySQL incomplet**~~ **CORRIGE (Phase 3.1)**

4. ~~**Injection SQL via noms de tables**~~ **CORRIGE** (quoting dialect-specific via `build_preview_sql()`)

5. ~~**Duplication de code significative**~~ **LARGEMENT CORRIGE** — PostgreSQL parser factorise, Open in Explorer factorise, DataFrameTableModel: reste 2 copies (ui/widgets + core/)

6. **Gestion d'erreurs a ameliorer** (ameliore significativement)
   - ~~341 `except Exception` generiques~~ **172** (vs 341, -50%) — 169 convertis en exceptions specifiques (sqlite3.Error, ftplib.all_errors, OSError, ValueError, KeyError, json.JSONDecodeError, KeyringError, DbError, etc.)
   - 58 `except` + `pass` (dont 22 avec exceptions specifiques, 36 avec Exception — majoritairement teardown/cleanup legitimes)
   - **0 bare `except:`** (vs 3, -100%)
   - config_db.py: 46→0 exceptions generiques
   - Les 172 restants sont des catch-alls legitimes: teardown (~34), theme/observers (~24), plugins (~6), QThread (~4), per-item loops (~9), multi-driver DB (~15)

7. ~~**Fuites memoire managers**~~ **CORRIGE** — 24 fichiers avec cleanup/closeEvent. config_db.py utilise ConnectionPool (77 context managers). Reste: ratio connect/disconnect 448:25 (Qt signals)

8. **Couverture de tests faible**
   - 7 fichiers de tests (1463 lignes) pour 222 fichiers source (59,542 lignes)
   - 79/79 tests passent, 0 echec
   - Pas de tests pour: managers, dialogs, sql_formatter, ftp_client
   - Couverture estimee: ~15%

9. ~~**Dependances inutilisees**~~ **CORRIGE** (sqlalchemy, tabulate, colorama supprimes)

10. ~~**Coexistence config_db.py / repositories**~~ **CORRIGE (audit #3)** — config_db.py est desormais une pure facade delegant a 10 repositories. 0 SQL inline. ConnectionPool partage. 59 appels `get_config_db()` dans 28 fichiers

11. **i18n incomplete** (ameliore)
    - ES n'existe pas (seulement EN/FR)
    - ~50 strings hardcodees en francais dans le code source
    - EN/FR: 652 cles, parite 100%

12. **Configuration stockee dans l'arbre source** (`_AppConfig/`)
    - Pas de chemin OS standard (`%APPDATA%`, `~/.config/`)
    - Perdue en cas de reinstallation

13. ~~**query_tab.py reste volumineux**~~ **CORRIGE (audit #4)** — 2061→417L, 6 mixins dans query/ subpackage

---

## Risques Identifies

### Risques Techniques

| Risque | Severite | Impact | Mitigation |
|--------|----------|--------|------------|
| ~~**SQL Injection PRAGMA**~~ | ~~Moyenne~~ | ~~Faible~~ | **CORRIGE** (Phase 3.1) |
| ~~**SQL Injection noms de tables**~~ | ~~Moyenne~~ | ~~Faible~~ | **CORRIGE** (build_preview_sql) |
| ~~**Fichiers monolithiques (config_db, database_manager)**~~ | ~~Haute~~ | ~~Maintenabilite tres reduite~~ | **CORRIGE** (config_db→facade, database_manager→mixins) |
| ~~**query_tab.py monolithique**~~ | ~~Moyenne~~ | ~~Maintenabilite reduite~~ | **CORRIGE** (audit #4: 2061→417L, 6 mixins) |
| ~~**Fuites memoire managers**~~ | ~~Haute~~ | ~~Degradation RAM~~ | **CORRIGE** (cleanup ajoute, 24 fichiers) |
| ~~**config_db.py sans context manager**~~ | ~~Moyenne~~ | ~~Fuite connexions SQLite~~ | **CORRIGE** (audit #3: ConnectionPool + 77 context managers) |
| **Absence async** | Moyenne | UI freeze possible | 4 QThread workers existants, a etendre |
| ~~**Test casse (test_theme_patch.py)**~~ | ~~Faible~~ | ~~CI cassee~~ | **CORRIGE** |
| ~~**Deps inutilisees**~~ | ~~Faible~~ | ~~Taille install~~ | **CORRIGE** |
| ~~**subprocess shell=True**~~ | ~~Faible~~ | ~~Injection si path malicieux~~ | **CORRIGE** (os.startfile, CREATE_NEW_CONSOLE, shutil.which) |
| ~~**f-string SQL query_gen_mixin**~~ | ~~Faible~~ | ~~Injection theorique~~ | **CORRIGE** (parametres ? + sanitize db_name ]] ) |
| ~~**f-string SQL access_dialect, data_loader**~~ | ~~Faible~~ | ~~Injection theorique~~ | **CORRIGE** (quote_identifier escape + _quote_id helper) |

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
| ~~Refactorer query_tab.py en mixins (2061L)~~ | ~~ui/managers/query_tab.py~~ | ~~2-3j~~ | **Done** (audit #4: 6 mixins) |
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
| Implementer Scripts & Jobs | Phase 3 + Phase 5 | 4-5j | **Specifie** |
| ~~Reducer except generiques (cibler 50%)~~ | ~~51 fichiers~~ | ~~2j~~ | **Done** (341→172, -50%) |
| ~~Supprimer `shell=True` dans subprocess~~ | ~~os_helpers, main_window, scripts_manager~~ | ~~0.5j~~ | **Done** |
| ~~Parametrer SQL query_gen_mixin~~ | ~~query_gen_mixin, connection_mixin~~ | ~~0.5j~~ | **Done** |
| ~~Ajouter quoting SQL access_dialect, data_loader~~ | ~~access_dialect, data_loader, base dialect~~ | ~~0.5j~~ | **Done** |

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
4. Le score est passe de 7.3 a 7.9 — la base est saine pour accelerer les fonctionnalites

**Priorites immediates**:
1. ~~**Refactoring query_tab.py**~~ **Done** (audit #4)
2. ~~**Reducer except generiques** de 341 a ~170 (-50%)~~ **Done** (341→172)
3. ~~**Supprimer `shell=True`**~~ **Done**
4. ~~**Parametrer/quoting SQL**~~ **Done** (query_gen_mixin, access_dialect, data_loader, base dialect)

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

### Phase 3: Scripts & Jobs (Specification definie - En attente)

#### Modele de donnees

**Cycle de vie d'un script** :

```
Pseudo-script → Declare → Valide → Job
     |               |          |        |
  Fichier seul   + Manifest  + Test OK  + Params figes
  Non executable  Params types Eligible   Planifiable
```

- **Pseudo-script** : fichier present mais sans manifest. Visible dans l'explorateur, non executable comme job.
- **Script declare** : manifest cree (via template ou manuellement). Parametres types definis, mais pas encore valide.
- **Script valide** : une execution standalone reussie avec des parametres de test, confirmee par l'utilisateur. Hash SHA-256 du fichier enregistre. Si le script est modifie (hash different), le statut repasse a "declare" — revalidation necessaire.
- **Job** : script valide + parametres figes + eventuellement planification.

#### Manifest

Chaque script executable doit avoir un manifest (YAML ou JSON) qui declare :

| Champ | Description | Obligatoire |
|-------|-------------|-------------|
| `name` | Nom du script | Oui |
| `description` | Description fonctionnelle | Oui |
| `interpreter` | Interpreteur (`python`, `pwsh`, `cscript`, etc.) | Oui |
| `os_compatible` | OS supportes (`windows`, `linux`, `macos`) | Oui |
| `parameters` | Liste de parametres types | Non |

**Types de parametres supportes** : `string`, `int`, `float`, `bool`, `path`, `connection`, `query`

Chaque parametre : `name`, `type`, `label`, `required`, `default`, `description`

#### Scripts embarques vs utilisateur

| | Scripts embarques | Scripts utilisateur |
|---|---|---|
| Provenance | Livres avec l'app | Crees par l'utilisateur |
| Emplacement | Dans la solution | Dossier utilisateur |
| Langages | Python | Python, PowerShell, VBScript |
| Maintenance | Versionnes avec l'app | Responsabilite utilisateur |
| Validation | Pre-valides | Validation obligatoire |

#### Import / Export de scripts

- **Export** : archive (zip) contenant le script + son manifest
- **Import** : l'app depose les fichiers au bon endroit. Le script arrive en statut "declare" — l'utilisateur doit le valider sur son environnement.
- **Ce qui ne voyage PAS** : hash de validation (propre a chaque environnement), parametres figes des jobs (connexions, chemins — specifiques a chaque poste)
- **Securite** : aucune sandbox, aucune analyse statique. L'utilisateur est responsable de ce qu'il execute. Un script personnel est par definition personnel ; s'il est transmis a un tiers, c'est la responsabilite du destinataire de verifier et valider.

#### Templates

Des squelettes prets a l'emploi par langage pour faciliter la creation :
- "Script Python avec connexion DB"
- "PowerShell d'export CSV"
- etc.

Les templates imposent la structure et facilitent la declaration des parametres.

#### Taches d'implementation

| Tache | Status | Priorite |
|-------|--------|----------|
| Format manifest (YAML/JSON) + schema | Todo | P0 |
| Formulaire dynamique depuis manifest | Todo | P0 |
| Widgets par type (connection selector, file picker, etc.) | Todo | P0 |
| Detection interpreteur disponible sur l'OS | Todo | P1 |
| Execution standalone (validation) | Todo | P0 |
| Hash SHA-256 + detection modification | Todo | P0 |
| Cycle de vie (pseudo → declare → valide) | Todo | P0 |
| Bouton "Run" fonctionnel | Todo | P0 |
| Logs temps reel dans onglet "Log" | Todo | P1 |
| Gestion erreurs et code retour | Todo | P1 |
| Templates de scripts (Python, PowerShell) | Todo | P1 |
| Import / Export archives | Todo | P2 |

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

### Phase 4: Theming & App Icons (En cours)

| Tache | Status | Effort |
|-------|--------|--------|
| icon_generator.py (recoloration PNG) | **Done** | 3h |
| Modifier image_loader.py (cache + QSvgRenderer) | **Done** | 2h |
| Convertir icones en monochromes SVG (37 icones) | **Done** (v0.6.5) | 4h |
| Support SVG (recoloration texte, rendu Qt) | **Done** (v0.6.5) | 3h |
| Etendre format theme (icon_color par contexte) | Todo | 1h |
| Taille d'icones variable par contexte | Todo | 1h |

---

### Phase 5: Jobs & Orchestration (v1.0)

*Prerequis : Phase 3 (Scripts) terminee — un Job est une configuration d'execution d'un script valide.*

**Job = Script valide + Parametres figes + Planification (optionnelle)**

L'utilisateur cree un job via l'UI en selectionnant un script valide et en remplissant les parametres types (avec des widgets adaptes : selecteur de connexion, file picker, etc.). Le job ne peut etre cree que si le script est au statut "valide".

| Tache | Status | Priorite |
|-------|--------|----------|
| Creation de Job depuis script valide | Todo | P0 |
| UI parametres figes (widgets types) | Todo | P0 |
| Execution manuelle de Job | Todo | P0 |
| Historique des executions (date, code retour, logs) | Todo | P1 |
| Statut execution (pending, running, success, error) | Todo | P1 |
| Planification cron-like | Todo | P2 |
| Chainage de Jobs (workflow) | Todo | P3 |

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
| ~~Reducer except generiques~~ | **Done** (341→172, -50%) | P2 |
| ~~Refactorer query_tab.py en mixins~~ | **Done** (audit #4) | P1.5 |
| ~~Supprimer `shell=True` subprocess~~ | **Done** | P2 |
| ~~Parametrer SQL query_gen_mixin~~ | **Done** | P2 |
| ~~Quoting SQL access_dialect, data_loader~~ | **Done** | P2 |

---

## Statistiques du Projet

| Metrique | Valeur | Evolution |
|----------|--------|-----------|
| Fichiers Python | 233 | +10 (ER Diagram package, tests) |
| Lignes de code (src/) | 63,304 | +2,759 |
| Fichiers de tests | 7 | = |
| Lignes de tests | 1,463 | = |
| Tests en echec | 0 (79 passed) | = |
| Plugins | 10 | = |
| Dialects DB | 5 (SQLite, PostgreSQL, SQL Server, MySQL/MariaDB, Access) | = |
| Langues i18n | 2 (EN: 656 cles, FR: 656 cles) | +1 cle |
| Themes | 4 | = |
| Guides documentation | 24 | = |
| Commits depuis Dec 2025 | ~177 | +20 |
| `except Exception` generiques | 188 | +11 (ER Diagrams, smart reconnect) |
| bare `except:` | 0 | = |
| `except` + `pass` | 69 | +11 (nouvelles features) |
| `shell=True` | 0 | = |
| `eval()`/`exec()` | 0 | = |
| f-string SQL | 35 (toutes securisees) | = |
| `.connect()` / `.disconnect()` | 479 / 26 | ratio 18:1 (Qt signals) |
| `deleteLater()` | 20 | +1 |
| cleanup/closeEvent | 24 | +1 |
| Fichiers > 500 lignes | 30 | +1 |
| Fichiers > 1000 lignes | 8 | = |
| Repositories actifs | 11 | +1 (ERDiagramRepository) |
| TODO/FIXME | 6 | = |
| Deps (pyproject.toml) | 15 | = (toutes utilisees) |
| SVG icones | 37 (+ 15 PNG base conserves) | *(nouveau)* |
| `get_*_context_actions()` publiques | 11 | +1 |
| Plugins UI | 11 | +1 (ER Diagram) |

*Statistiques mises a jour: 02 Avril 2026 (audit #7)*

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
|-- Refactoring query_tab.py → 6 mixins (2061→417L)
|-- Audit #4 (7.7→7.9/10) — 3 God Objects majeurs tous refactores
|-- Suppression shell=True, parametrisation/quoting SQL
|-- Reduction except Exception generiques: 341→172 (-50%, 51 fichiers)
|-- Audit #5 (7.9/10) — base technique mature, tous correctifs P1/P2 resolus
|-- v0.6.5
|
Avril 2026
|-- Migration SVG (37 icones), DB logos dans connection selector
|-- Split toggle, detachable query tabs, PopupWindow resize
|-- Column filters (clic droit header, contains, cumulatif AND)
|-- SQL formatter: multi-statement, DISTINCT/TOP, standalone comments, _TopLevelScanner
|-- Variables SQL (DECLARE/SET) en batch unique, coloration syntaxique @variables
|-- Delegation context menus (10 get_*_context_actions), tree_item_builders.py
|-- FTP icon status dot (vert/rouge), mise a jour dynamique
|-- Combined file view (CSV/Excel/JSON dans un grid)
|-- Audit #6 (8.2/10) — maintenabilite, extensibilite, UX en hausse
|-- v0.6.9 (actuel)
```

### Projection (estimee)

```
Q1 2026 (en cours)
|-- Refactoring query_tab.py en mixins (2061L) — DONE
|-- Reducer except generiques (-50%) — DONE (341→172)
|-- Phase 4 (Migration SVG) — DONE (v0.6.5)
|-- Phase 4 (icon_color par contexte) — En reflexion
|-- v0.7.0
|
Q2 2026
|-- Phase 3 (Scripts & Jobs) — specification definie
|-- Couverture tests 25%
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

DataForge Studio est une **application bien architecturee** avec un potentiel solide. Depuis Decembre 2025, le developpement est intensif avec ~140 commits en 4 mois, portant le projet de v0.2.0 a v0.6.9.

**Score global: 8.6/10** (+0.4 vs audit #6) — Progression majeure: ER Diagrams interactifs, documentation doublee (manuel + mkdocs), fiabilite en hausse (201 tests, smart reconnect). L'application evolue vers une plateforme DATA complete.

**Bilan des corrections realisees**:
- ~~MySQL backend (dialect + loader + factories)~~ Done
- ~~PRAGMA injection (securite)~~ Done
- ~~Aide contextuelle + fenetre detachable~~ Done
- ~~Coherence visuelle des fenetres~~ Done
- Navigation FTP, pytds fallback, package offline Done
- Pastilles colorees, workspace favori, onglet "+", raccourci bureau Done
- **config_db.py refactore en facade** (2547→474L, 10 repos, 0 SQL inline) Done *(audit #3)*
- **database_manager.py refactore en mixins** Done
- **query_tab.py refactore en 6 mixins** (2061→417L) Done *(audit #4)*
- **except Exception reduits de 50%** (341→172, 51 fichiers, 169 sites specifiques) Done *(audit #5)*
- **Securite SQL complete**: 0 shell=True, 0 eval/exec, SQL parametrise/quote Done

**Actions immediates recommandees**:
1. ~~Refactorer query_tab.py en mixins~~ **Done**
2. ~~Reducer `except Exception` generiques de 341 a ~170~~ **Done** (341→172, -50%)
3. ~~Supprimer `shell=True` dans 3 subprocess~~ **Done**
4. ~~Parametrer/quoting SQL~~ **Done** (query_gen_mixin, access_dialect, data_loader)
5. ~~**Phase 4 (Theming Icons)**~~ **En cours** — Migration SVG done (v0.6.5), reste icon_color par contexte
6. **Phase 3 (Scripts & Jobs)** — specification definie, implementation a planifier
7. **Augmenter couverture tests** (15% → 25%) — P2

**Prochaine etape majeure**: Phase 3 (Scripts & Jobs) — le modele est maintenant defini (cycle de vie pseudo→declare→valide→job, manifest type, hash SHA-256, import/export). C'est la fonctionnalite qui transforme l'outil d'un "explorateur de DB" en une "plateforme DATA complete".

**A ne PAS faire maintenant**:
- MongoDB/Oracle (pas de base de test, pas de besoin immediat)
- Tests exhaustifs au-dela de 25% (incrementer progressivement, viser 40% pour v1.0)
- Operations async generalisees (4 QThread workers suffisent pour l'instant)

Le ratio **70% nouveautes / 30% corrections** est desormais recommande — la dette technique est quasiment resolue, priorite aux fonctionnalites.

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

### EVO-3: Diagrammes ER Interactifs

**Objectif**: Visualiser les relations entre tables (FK) sous forme de diagramme interactif. Permet de creer des vues "datamart" : un sous-ensemble de tables d'un datawarehouse avec les FK auto-detectees.

**Priorite**: Haute (prochain step majeur)

**Principe**: L'utilisateur selectionne des tables dans le schema tree, DataForge genere un diagramme ER draggable. Les diagrammes sont nommes et sauvegardes (plusieurs par base, un par datamart/sujet).

#### Modele de donnees

Un diagramme contient :

| Champ | Description |
|-------|-------------|
| `name` | Nom du diagramme ("Datamart Ventes", "Datamart RH") |
| `connection_id` | Connexion DB source |
| `tables` | Liste des tables selectionnees |
| `positions` | Coordonnees x,y de chaque table dans le canvas |
| `description` | Description optionnelle |

#### Rendu visuel (QGraphicsScene)

- [ ] Tables draggables avec header colore, colonnes, types, indicateurs PK/FK
- [ ] Relations FK auto-detectees depuis les metadata DB (INFORMATION_SCHEMA / sys.foreign_keys / pg_constraint)
- [ ] **Routage intelligent des lignes FK** : choix du cote optimal (gauche, droite, haut, bas) selon la position relative des tables. Pas de traversee de tables. Connexion verticale quand les tables sont alignees
- [ ] **Deplacer les points d'ancrage** des lignes FK manuellement (option avancee pour ajuster le trace)
- [ ] Zoom / dezoom (molette)
- [ ] Fond sombre/clair selon le theme actif

#### Sauvegarde et export

- [ ] Sauvegarder le diagramme (nom, tables, positions, ancrage FK) dans la config DB
- [ ] Charger un diagramme sauvegarde — retrouver le meme layout
- [ ] Plusieurs diagrammes par connexion
- [ ] Export PNG / SVG pour documentation

#### Selection des tables

- [ ] Multi-selection dans le schema tree (Ctrl+Clic) + clic droit "Creer un diagramme"
- [ ] Ou dialog de selection avec checkboxes (liste de toutes les tables)
- [ ] Ajouter/retirer des tables a un diagramme existant

#### Points techniques
- PySide6 `QGraphicsScene` / `QGraphicsView` natif, pas de dependance externe
- FK lues via `INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS` (SQL Server), `pg_constraint` (PostgreSQL), `PRAGMA foreign_key_list` (SQLite)
- Algorithme de layout initial : placement en grille puis optimisation par proximite des FK
- `QGraphicsItem.ItemIsMovable` pour le drag & drop natif

---

## Backlog (Idees non priorisees)

*Idees a explorer, sans engagement ni planning. A remonter dans les phases quand le besoin se confirme.*

| Idee | Description | Complexite estimee | Notes |
|------|-------------|-------------------|-------|
| **Dialect DAX / Power BI** | Connexion aux datasets Power BI via endpoint XMLA, requetes DAX, exploration des tables/mesures | Moyenne-Haute | Necessite licence Power BI Pro/Premium + lib XMLA Python (pyadomd). Meme modele qu'un dialect SQL classique : connexion → schema → requetes → resultats tabulaires. Cible : profils DATA travaillant sur les deux mondes (SQL + Power BI) |
| **Dependances entre scripts** | Champ `dependencies` dans le manifest pour referencer d'autres scripts. Cas d'usage principal : un script de logging embarque, reutilisable par tous les scripts metier, configure par projet (serveur de logs, table, projet). Au deploiement, DataForge embarque les dependances avec la configuration du projet cible | Moyenne | Compatible avec le logging centralise existant (SSIS, scripts SQL). Le script de logging serait un script embarque valide, livre avec DataForge |
| **Diagrammes ER interactifs** | Visualisation des relations FK entre tables selectionnees. Details ci-dessous | Moyenne-Haute | Probablement le prochain step majeur apres la mise en forme SQL |
| **Partage de ressources workspace** | Specification detaillee ci-dessous (EVO-4) | Haute | Prochaine evolution majeure apres stabilisation des diagrammes ER |
| **Support Oracle** | Nouveau dialect + loader Oracle | Moyenne | Pas de base de test disponible actuellement |
| **Support MongoDB** | Nouveau dialect + loader MongoDB (NoSQL) | Moyenne | Pas de base de test disponible actuellement |

---

### EVO-4: Partage de Ressources Workspace

**Objectif**: Permettre le partage de diagrammes ER, requetes sauvegardees et configurations entre les membres d'un workspace, via un dossier partage (OneDrive, SharePoint, filer reseau).

**Priorite**: Haute (prochaine evolution majeure)

**Principe**: Les ressources restent en local par defaut. L'utilisateur choisit explicitement ce qu'il partage via une action "Partager". Les elements partages sont stockes en fichiers JSON dans un dossier configure au niveau du workspace.

#### Architecture

**Fonctionnement local inchange** :
- Les ressources (diagrammes, queries, connexions) sont stockees dans `_AppConfig/configuration.db` comme aujourd'hui
- Les credentials restent dans le keyring local de chaque utilisateur

**Partage optionnel par workspace** :
- Chaque workspace peut definir un **chemin de partage** (OneDrive, SharePoint, filer reseau)
- L'action **"Partager"** (clic droit sur un diagramme/query) ecrit un fichier JSON dans le dossier partage
- OneDrive/SharePoint gere la synchronisation entre les membres — pas besoin de serveur

**Structure du dossier partage** :
```
\\share\workspaces\Projet Alpha\
+-- diagrams\
|   +-- datamart-incidents.json
|   +-- datamart-rh.json
+-- queries\
|   +-- ventes-mensuelles.json
|   +-- rapport-clients.json
+-- connections\
    +-- dwh-production.json       (connection string SANS credentials)
```

#### Parametres workspace

| Parametre | Description | Defaut |
|-----------|-------------|--------|
| Chemin de partage | Dossier partage (UNC, OneDrive, local) | Vide (pas de partage) |
| Publier auto | Comportement a la modification d'un element partage | Demander |

Options de publication automatique : **Non** (re-partage manuel) / **Demander** (notification) / **Toujours** (auto)

#### Affichage

- Les elements partages sont affiches avec un **indicateur visuel** (couleur de la pastille de connexion DB associee) pour les distinguer des elements locaux
- **Deduplication** : si un element existe en local ET en partage, seule la version partagee est affichee
- **Notification de publication** : quand un element partage est modifie localement, une notification demande "Cet element est partage. Publier les modifications ?"

#### Diagrammes dans le workspace

Les diagrammes ER apparaissent dans l'arbre du workspace sous la connexion DB :
```
Workspace "Projet Alpha"
+-- Databases
|   +-- DWH Production
|   |   +-- Tables
|   |   +-- Views
|   |   +-- Diagrammes
|   |       +-- Datamart Incidents    (indicateur partage)
|   |       +-- Datamart RH           (indicateur partage)
+-- Queries
+-- RootFolders
```

Le double-clic sur un diagramme l'affiche dans un onglet du workspace (meme principe que les queries).

#### Choix techniques

- **JSON fichier par fichier** (pas de SQLite partage — risque de corruption sur reseau)
- Un fichier par objet permet la synchro incrementale OneDrive/SharePoint
- Conflits geres par OneDrive (copie de conflit, pas de corruption)
- Pas de credentials dans les fichiers partages (keyring local uniquement)

#### Acces au dossier partage

Si le dossier partage n'est pas accessible (permissions, chemin introuvable) :
- L'app affiche une notification : "Le dossier partage n'est pas accessible. Contactez la personne qui vous a partage ce workspace pour obtenir l'acces."
- Le workspace fonctionne normalement avec les ressources locales — seul le partage est desactive
- Pas d'automatisation de demande d'acces (c'est un processus humain, variable selon l'infrastructure)

#### Points ouverts

- [ ] Gestion des conflits : que faire si OneDrive cree une copie de conflit ?
- [ ] Droit d'ecriture : qui peut publier/modifier les elements partages ?
- [ ] Versionning : historique des modifications d'un element partage ?
- [ ] Migration : comment migrer un workspace local vers un workspace partage ?

---

*Derniere mise a jour: 2026-04-02*
