# ER Diagrams — Vocabulaire et règles de routage

Document normatif du routage automatique des liens FK. Sert de référence partagée
(utilisateur ↔ assistant) et de spécification pour `_compute_line_offsets`.

Statut : R1, R2, R3.1, R3.3, R4 et l'ordonnancement R5 sur un bord sont
**implémentés** (`scene.py`). R3.2 tourne sur un critère provisoire (§4, R3.2)
en attendant la conscience des obstacles (§7.1).

Cas de référence : diagramme `test` (6 tables, 5 liens), captures avant/après
dans `debug/test.png`.

---

## 1. Vocabulaire

| Terme | Définition |
|---|---|
| **Bord** (edge) | Un des 4 côtés d'une table, vu comme un segment de longueur L |
| **Côté** | Désignation d'un bord : `top`, `bottom`, `left`, `right` |
| **Ancrage** (anchor) | Point exact sur un bord où un lien commence ou finit |
| **Marge** | Distance entre un ancrage et l'extrémité la plus proche de son bord |
| **Pas** | `L / (n + 1)` pour un bord portant n ancrages — l'espacement homogène de référence |
| **Forme** | Géométrie du lien : **droite** (1 segment), **L** (2), **Z** (4) |
| **Stub** | Court prolongement perpendiculaire sortant d'une table avant de tourner (`GAP = 25`) |
| **Waypoint** | Vertex intermédiaire de `_vertices`, entre `from_pt` et `to_pt` |
| **Jog** | Détour en escalier (2 vertices) inséré dans un segment d'ancrage |
| **Inclusion** | Une plage de bord entièrement contenue dans celle du bord d'en face |
| **Ancrage contraint** | Ancrage dont la position est imposée par une inclusion (R2), et non par la répartition |
| **Couloir** | Espace libre entre deux tables voisines, traversé par un segment |
| **Ligne auto** | `_user_modified = False` — re-routée à chaque rafraîchissement |
| **Ligne modifiée** | `_user_modified = True` — géométrie sauvegardée et restaurée telle quelle, jamais recalculée |

---

## 2. R1 — Hiérarchie des formes

Par ordre de préférence : **droite > L > Z**.

Une forme n'est retenue que si elle est *atteignable* et *propre* (R3).
Le Z est un dernier recours, pas un défaut.

> **Défaut actuel** — `scene.py:227-234` assigne systématiquement des côtés
> **parallèles** (`top`/`bottom` ou `left`/`right`) sur toute paire en diagonale,
> ce qui force un Z. Les 4 liens corrigés du diagramme `test` sont tous dans ce cas.

---

## 3. R2 — Ancrages contraints par inclusion

Quand les plages de deux bords en vis-à-vis se recouvrent et que **l'une est
incluse dans l'autre**, la plage incluse impose son milieu ; l'autre s'aligne
dessus. Le lien est droit et les deux ancrages sont bien placés.

**Exemple** — `dim_WII_Contract_Type` y[347.71 ; 434.71] est inclus dans
`fact_WII_Contract` y[300.60 ; 489.60] :

- Contract_Type est prioritaire → ancrage à son milieu, **y = 391.21**
- fact s'aligne → même y

**Effet de bord** : l'ancrage contraint découpe le bord de fact en sous-segments.
Les ancrages restants se répartissent *à l'intérieur* de ces sous-segments (R4).
Ici →Agency est seul dans [300.60 ; 391.21], donc à son milieu, **y = 345.90**.

---

## 4. R3 — Choix de la forme et du côté

### R3.1 — La droite ne prime que si elle ne dégrade pas la répartition

Un recouvrement partiel autorise géométriquement une droite, mais peut tasser
les ancrages dans les coins. Test :

```
min(marge) / pas  >=  0.5
```

Si le critère échoue sur l'un des deux bords, on abandonne la droite pour un L.

**Exemple** — bord haut de fact (x de -328.86 à -153.86, L = 175). Les deux
liens vers Agency et Client se recouvrent chacun d'environ 50 px sur X, donc
deux verticales droites sont possibles. Elles donneraient :

```
25.04  |———— 125.09 ————|  24.87     droites   → min(marge)/pas = 24.87/58.33 = 0.43  ✗
58.33  |———— 58.33 ————|  58.33      homogène
```

→ rejet, on bascule en L. C'est ce que montre l'image corrigée.

Contre-exemple à conserver — bord gauche de fact (L = 189, 2 ancrages) :

```
45.30  |—— 45.31 ——|  98.39          → min(marge)/pas = 45.30/63.00 = 0.72  ✓
```

L'inclusion (R2) satisfait toujours ce test ; seul le recouvrement partiel est à
vérifier.

### R3.2 — Entre les deux L possibles

Une paire en diagonale admet exactement deux L :
« vertical d'abord » (sortie `top`/`bottom`, arrivée `left`/`right`) et
« horizontal d'abord » (sortie `left`/`right`, arrivée `top`/`bottom`).

Critères, dans l'ordre :

1. **Éviter les couloirs chargés.** Écarter le L dont un segment traverse un
   couloir étroit entre deux tables voisines.
   *Exemple* : Agency finit à x = -278.78, Client commence à x = -203.60 — un
   couloir de 75 px. Le L « vertical d'abord » pour fact→Agency y passerait ;
   le L « horizontal d'abord » sort par la gauche de fact et remonte à x = -366,
   à l'écart. C'est celui retenu.
2. **Côté le moins chargé** de la table (nombre d'ancrages déjà posés).

Conséquence observée sur `test` : la table de fait étale ses liens sur ses côtés
latéraux et garde son sommet dégagé ; les dimensions intermédiaires deviennent
des traversées verticales (entrée `bottom`, sortie `top`), chaque ancrage au
milieu de son bord.

### R3.3 — Côté d'arrivée

La cible est toujours abordée par le côté qui **fait face** à la source.

---

## 5. R4 — Répartition sur un bord

n ancrages sur un bord de longueur L → positions `i × L / (n + 1)`, i de 1 à n.
1 ancrage au milieu, 2 ancrages à 1/3 et 2/3.

La répartition s'applique **par sous-segment**, les sous-segments étant délimités
par les ancrages contraints (R2).

> Déjà implémenté et correct : `scene.py:442-467` (PASS M, `segments_to_fill`
> puis `sub_step = (s_end - s_start) / (m + 1)`). PASS M / PASS S et la
> distribution n'ont pas à être modifiés.

---

## 5bis. R5 — Croisements prohibés

Deux liens ne doivent pas se croiser. L'algorithme ne doit **jamais produire un
croisement** qu'un autre choix valide aurait évité — ce qui contraint à la fois le
choix du L (R3.2) et l'ordre des ancrages sur un bord (R4).

Sur des modèles très denses, un croisement peut devenir géométriquement
inévitable. Ce n'est alors **pas** à l'algorithme de le résoudre par un détour :
c'est à l'utilisateur de repositionner ses tables. Le placement des tables reste
sa responsabilité, le routage celle de l'algorithme.

> Partiellement couvert : le tri par angle (`atan2`) de PASS M
> (`scene.py:396-412`) sert déjà à éviter les croisements entre liens partageant
> un même bord. Il ne couvre pas les croisements entre liens de bords différents.

---

## 5ter. R6 — Orthogonalité et sortie perpendiculaire

Invariant dur, valable pour **toute** géométrie affichée, auto ou restaurée :

1. Chaque segment est aligné sur un axe. **Aucun segment oblique**, jamais.
2. Le premier segment d'un lien est **perpendiculaire au côté d'ancrage** et
   dirigé **vers l'extérieur** de la table. Idem pour le dernier.

Conséquence sur la parité : un lien à côtés **perpendiculaires** (L) a un nombre
**pair** de segments, un lien à côtés **parallèles** (droite, Z) un nombre
**impair**. Une chaîne de waypoints dont la parité ne correspond pas aux côtés
courants ne peut pas être rendue orthogonale.

> **Bug corrigé (2026-08-19)** — `set_waypoints` ne réalignait que les deux
> extrémités de la chaîne restaurée. Des waypoints sauvegardés sous l'ancien
> routage (côtés parallèles, 4 segments) rejoués sur les nouveaux côtés
> perpendiculaires produisaient un segment oblique et un premier segment
> repartant *dans* la table. `_orthogonalize` valide désormais la parité et le
> sens de sortie, aligne toute la chaîne, et rejette celles qui ne peuvent pas
> satisfaire l'invariant — la ligne garde alors sa géométrie auto.

> **Chaîne sans intention utilisateur (2026-08-19)** — une chaîne restaurée qui
> reproduit exactement le tracé auto ne marque plus la ligne `_user_modified`.
> Elle reste donc une *ligne auto* et continue d'être re-routée quand les tables
> bougent, au lieu de se figer sur une géométrie qu'aucun utilisateur n'a voulue.

---

## 6. Périmètre du changement

| Zone | État |
|---|---|
| `scene.py:202-351` — décision des côtés | **à réécrire** (R1, R2, R3) |
| `relationship_line.py:190-203` — test de ligne droite | **à durcir** : exige aujourd'hui un simple recouvrement de 20 px, doit appliquer R3.1 |
| `relationship_line.py` — `set_waypoints` / `_orthogonalize` | **ajouté** : validation R6 des waypoints restaurés |
| `scene.py:442-467` — répartition en sous-segments | inchangé (implémente R4) |

---

## 7. Points ouverts

### 7.1 — Conscience des obstacles (step suivant)

Deux besoins distincts en apparence, **un seul mécanisme** en réalité : un segment
doit pouvoir traverser de l'espace libre sans frôler ni couper une table.

- **Visée d'une droite (R2 en zone dense).** La règle « la plus courte plage
  impose son milieu » est validée **dans le cas simple**. Dès qu'il y a
  encombrement, le milieu ne suffit plus : il faut décaler l'ancrage pour que la
  droite passe *entre* les tables, et non derrière ou par-dessus.
- **Couloirs (R3.2.1).** Écarter un L dont un segment s'engage dans une fente
  étroite entre deux tables.
  *Exemple* : le couloir entre Agency (fin à x = -278.78) et Client (début à
  x = -203.60) fait **75.18 px**. Le L « vertical d'abord » pour fact→Agency y
  monterait puis longerait le flanc d'Agency ; le L retenu sort par la gauche de
  fact et remonte à x = -366, à l'écart.

> Le seuil `2 × GAP` (50 px) d'abord envisagé est **invalidé** : le couloir de ce
> cas fait 75 px, la règle ne l'aurait donc pas rejeté et aurait choisi le mauvais L.
> Le critère est à reconstruire avec la mécanique d'obstacles, pas comme un seuil isolé.

**Cas de test reproductible** — scénario « étoile » (un fait de 180×200 en (0,0),
8 dimensions de 160×110 en couronne). Les 4 dimensions cardinales reçoivent des
liens droits, les 4 diagonales des L, sans aucun croisement. Mais le L vers la
dimension haut-gauche sort du fait par la gauche à y = 27.5 et tourne à
x = -240 : il **empiète de 20 px sur le coin de la dimension de gauche**
(x[-380 ; -220], y[0 ; 110]), sur ses deux segments. Idem par symétrie sur les
trois autres diagonales. C'est précisément ce que la mécanique d'obstacles doit
corriger.

### 7.2 — Ordre d'évaluation

R3.1 a besoin du *pas*, donc du nombre d'ancrages par bord, qui dépend lui-même
des côtés choisis — circulaire. Résolution proposée : itérer (côtés provisoires →
comptage → test R3.1 → déclassement des droites invalides → recomptage) jusqu'à
stabilisation, avec un plafond de 2 ou 3 passes.

## 8. Historique des décisions

| Date | Décision | Motivation |
|---|---|---|
| 2026-08-19 | Hiérarchie droite > L > Z (R1) | Le Z à 4 segments est illisible quand un L à 2 suffit |
| 2026-08-19 | Inclusion → la plage incluse impose son milieu (R2) | Garantit droite *et* ancrage propre |
| 2026-08-19 | Métrique `min(marge)/pas`, seuil 0.5 (R3.1) | Cible le défaut réel (ancrage tassé dans un coin) ; `max/min` avec seuil 2 aurait cassé le cas Contract_Type qui score 2.17 |
| 2026-08-19 | Couloirs chargés prioritaires sur « côté le moins chargé » (R3.2) | Un lien qui traverse un espace étroit entre deux tables reste illisible même si le côté est libre |
| 2026-08-19 | Visée de droite et évitement de couloir traités par une seule mécanique d'obstacles | Même problème sous deux formes ; évite deux seuils réglés séparément |
| 2026-08-19 | Croisements prohibés (R5), résolus par repositionnement utilisateur si inévitables | L'algorithme ne doit pas dégrader le tracé pour compenser un mauvais placement de tables |
| 2026-08-19 | R6 : orthogonalité + sortie perpendiculaire vers l'extérieur, waypoints incompatibles rejetés | Mieux vaut retomber sur l'auto-layout que rendre une chaîne oblique |
| 2026-08-19 | Une chaîne restaurée identique au tracé auto ne marque pas `_user_modified` | Une géométrie que personne n'a choisie ne doit pas figer la ligne |
