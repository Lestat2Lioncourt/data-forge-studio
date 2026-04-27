# ER Diagrams — Roadmap & Suivi

**Fichier dédié au sous-module ER Diagrams**. La roadmap globale de l'app reste dans `ROADMAP.md` à la racine.

---

## Périmètre fonctionnel

Les ER Diagrams permettent à l'utilisateur de créer, sauvegarder, organiser et annoter des vues visuelles des relations entre tables d'une base de données. Composé principalement de :

- `src/dataforge_studio/ui/managers/er_diagram/` — scene, table_item, relationship_line, group_item, dialogs, export
- `src/dataforge_studio/ui/managers/er_diagram_manager.py` — manager principal, toolbar, liste des diagrammes, splitter
- `src/dataforge_studio/database/models/er_diagram.py` — dataclasses (ERDiagram, ERDiagramTable, ERDiagramFKMidpoint, ERDiagramGroup)
- `src/dataforge_studio/database/repositories/er_diagram_repository.py` — CRUD
- `src/dataforge_studio/database/schema_manager.py` — migrations SQL (colonnes et tables `er_diagrams*`)

---

## État actuel (v0.6.12)

### Fonctionnalités livrées

| Fonctionnalité | Statut | Notes |
|---|---|---|
| Tables draggables (QGraphicsProxyWidget) | ✅ | Header Segoe UI, liste colonnes scrollable, style themed |
| Resize tables (3 zones : bas, droite, coin) | ✅ | `set_size()`, persistance width/height en DB (migration 12) |
| Sauvegarde/restauration positions tables | ✅ | Colonnes `pos_x`, `pos_y` |
| Sauvegarde/restauration taille tables | ✅ | Colonnes `width`, `height` (0 = auto) |
| Sauvegarde zoom level | ✅ | Colonne `zoom_level` (migration 9) |
| Toggle `show_column_types` persistant | ✅ | Migration 9 |
| Toggle `group_fks` persistant (FK composite/multi → 1 ligne épaisse avec badge) | ✅ | Migration créant la colonne |
| FK auto-routing orthogonal (Z-path) | ✅ | `_init_vertices` avec stubs et coin |
| Decision de côté position-aware | ✅ | Règle `tt_cy < ft_top → top`, etc. |
| Distribution des ancrages par angle (top/bottom) | ✅ | Évite croisements quand plusieurs dims "deeper" vs "shallower" |
| Pinning ligne-droite + sous-segments uniformes (Option C) | ✅ | Pass 1 |
| Drag-and-drop waypoints | ✅ | `_DragPoint` par segment |
| Split segment intermédiaire | ✅ | Insertion midpoint collinéaire |
| Split segment d'ancrage (jog) | ✅ | Côté conservé, anchor décalé + jog 2 vertices |
| Delete segment | ✅ | Menu contextuel |
| Merge collinear auto après drag | ✅ | `_merge_collinear` |
| Hover popup FK avec liste colonnes (composite) | ✅ | Signal `relation_hovered` |
| Labels FK (toggle) | ✅ | `set_show_fk_names` |
| Cadres visuels ("groupes") avec titre et couleur pastel | ✅ | ERGroupItem, 8 presets, drag déplace les tables à l'intérieur |
| Rename / change color / delete groupe (clic droit) | ✅ | |
| Restauration waypoints preserve les endpoints auto | ✅ | Fix `set_waypoints` + flag `_user_modified` |
| Export PNG / SVG | ✅ | `export.py` |

### Zones de dette technique identifiées (à traiter avant v0.7)

1. **`_compute_line_offsets` trop longue** (~200 lignes) : tri + override sides + pinning + distribution + Z-path mid_ratio + post-traitement ligne-droite. À découper en `_assign_sides`, `_pin_and_distribute`, `_stagger_z_paths`.
2. **Décision de côté éclatée** en 3 endroits : `_auto_sides()` dans `relationship_line.py`, override dans `_compute_line_offsets`, combinaison dans `_get_sides()`. À centraliser.
3. **Post-traitement ligne-droite redondant** avec le pinning de Pass 1. À supprimer ou factoriser.
4. **Pass 1 / Pass 2 asymétriques** : Pass 1 fait pinning + sous-segments, Pass 2 seulement uniforme. Extraire un helper `_distribute_on_edge(lines, edge_start, edge_end, pinning=None)` réutilisable.
5. **Closures redéfinies dans boucle** (`col_idx_local`, `angle_from_source`) : extraire en méthodes ou fonctions module.
6. **`_split_anchor` potentiellement mort** après l'ajout de `_jog_anchor_segment`. À vérifier et supprimer.
7. **Logique de split hétérogène** dans `_split_segment` : n_segs==1 insère 1 corner, n_segs>1 intermédiaire insère midpoint, anchor insère jog 2 vertices. Règles à aligner ou documenter explicitement.
8. **`set_waypoints` contrat implicite** : marque `_user_modified=True` et préserve endpoints auto. Documenter en docstring + idéalement test unitaire pour verrouiller l'invariant.
9. **Aucun test unitaire** sur `_compute_line_offsets`. Tests sur quelques configurations type : dim au-dessus gauche, chaîne de 4 dims parallèles, FK composite, etc.

---

## Évolutions prévues

### Court terme (v0.6.x → v0.7.0)

| # | Item | Priorité | Notes |
|---|---|---|---|
| 1 | Refactor `_compute_line_offsets` en fonctions nommées | Moyenne | après stabilisation des règles de layout |
| 2 | Centraliser la décision de côté d'ancrage | Moyenne | |
| 3 | Supprimer ou factoriser le post-traitement ligne-droite | Moyenne | |
| 4 | Mémo de vocabulaire partagé (user ↔ assistant) | Haute | `docs/ER_DIAGRAMS_GLOSSARY.md` : terme → définition (côté/ancrage/pin/segment/bord/jog/zone/Z-path…) |
| 5 | Bouton "Reset layout" (clear `_user_modified` + waypoints, relance auto-layout) | Moyenne | utile après changements d'algo pour repartir propre |
| 6 | Tests unitaires pour auto-routing sur scénarios typiques | Moyenne | `tests/ui/er_diagram/test_layout.py` |
| 7 | Contract docstring + invariants `set_waypoints` / `get_waypoints` | Basse | |

### Moyen terme (v0.7.x → v0.8.0)

| # | Item | Priorité | Notes |
|---|---|---|---|
| 8 | Mini-map de navigation (thumbnail) pour diagrammes larges | Basse | |
| 9 | Sélection multiple de tables + déplacement groupé | Moyenne | |
| 10 | Aligner tables (gauche/droite/haut/bas, distribuer) | Basse | |
| 11 | Styles de lignes personnalisables par FK (pointillé, couleur) | Basse | |
| 12 | Snap-to-grid optionnel | Basse | |
| 13 | Undo/redo sur actions (déplacement, resize, split, delete, add group) | Haute | |
| 14 | Copier/coller tables entre diagrammes | Basse | |

### Long terme (v0.8+)

| # | Item | Priorité | Notes |
|---|---|---|---|
| 15 | Export Mermaid / DBML / PlantUML | Basse | format texte exploitable par outils tiers |
| 16 | Diff visuel entre deux versions d'un diagramme | Basse | |
| 17 | Auto-layout "one-click" (Dagre, ELK) | Basse | alternative au placement manuel |
| 18 | Annotations libres (post-it, flèches décoratives) | Basse | en plus des groupes |
| 19 | Multi-utilisateur (workspace partagé) — conflits sur modifications concurrentes | Moyenne | dépend de l'infra workspace partagé |

---

## Historique des décisions de design

| Date | Décision | Motivation |
|---|---|---|
| 2026-03 | Vertex-based path model (`_vertices = [from_pt, wp..., to_pt]`) | Simplicité + permet split/merge collinéaires sans cas particuliers |
| 2026-03 | Split par (fact_id, to_table_id) lors de ≥5 FKs composites | Éviter ancrages trop denses sur un côté unique |
| 2026-04 | Toggle `group_fks=True` par défaut | FK composites rendus par une ligne épaisse + badge count — plus lisible |
| 2026-04 | Persistance `width`/`height` des tables | Permet resize manuel conservé entre sessions |
| 2026-04 | Distribution uniforme `L/(n+1)` | Règle simple et prévisible demandée par l'utilisateur |
| 2026-04 | Pinning ligne-droite quand centre cible dans zone | Lignes nearly-aligned restent rectilignes (plus esthétique) |
| 2026-04 | Option C — sous-segments entre pins | Compromis entre "ligne droite prioritaire" et "espacement homogène" |
| 2026-04 | Tri par angle (atan2) pour top/bottom | Évite croisements dims "deeper" vs "shallower" |
| 2026-04 | `set_waypoints` préserve endpoints auto-layout | Évite que les lignes restaurées collapsent sur le centre de l'edge |
| 2026-04 | Cadres visuels (ERGroupItem) | Permet de documenter/organiser visuellement des datamarts |

---

## Glossaire (v0)

À compléter dans `docs/ER_DIAGRAMS_GLOSSARY.md`. Termes en vrac à cadrer :

- **Fact / dim** : table centrale vs tables satellites dans un schéma en étoile
- **Côté d'ancrage** : `top`, `bottom`, `left`, `right` sur une table
- **Ancrage** (ou anchor) : point exact sur un bord de table où une ligne FK commence/finit
- **Bord** (edge) : un des 4 côtés d'une table, considéré comme un segment
- **Zone de ligne droite** (pin zone) : `[edge_start + espacement, edge_end − espacement]`
- **Pinning** : ancrage fixé à la coordonnée du centre de la cible (règle ligne droite)
- **Sous-segment** : portion d'un bord entre deux ancrages pinnés (ou entre edge_start/edge_end et un pin)
- **Espacement** : `longueur_bord / (n_ancrages + 1)`
- **Z-path** / **Z-bend** : chemin orthogonal à 3 segments entre deux points non alignés
- **L-path** : chemin orthogonal à 2 segments (angle droit simple)
- **Jog** : détour en escalier (2 vertices ajoutés) inséré dans un segment d'ancrage
- **Stub** : court prolongement perpendiculaire sortant d'une table avant de tourner (`GAP=25`)
- **Waypoint** / **midpoint** : vertex intermédiaire de `_vertices`, entre `from_pt` et `to_pt`
- **User-modified line** : ligne avec `_user_modified=True`, dont la géométrie est sauvegardée et restaurée telle-quelle
- **Auto line** : ligne dont `_user_modified=False`, re-routée par `_compute_line_offsets` à chaque rafraîchissement
