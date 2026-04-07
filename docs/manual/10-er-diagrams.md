# 10 - Diagrammes ER interactifs

> **Situation** : Vous venez de recevoir l'acces a un datawarehouse de 200 tables. Vous avez besoin de comprendre les relations entre les tables d'un domaine fonctionnel (un "datamart") pour ecrire vos requetes correctement.

---

## Creer un diagramme

1. Cliquez sur l'icone **ER Diagrams** dans la barre laterale
2. Cliquez sur **New Diagram** dans la barre d'outils
3. Si la connexion a un serveur multi-bases (SQL Server), selectionnez la **base de donnees** cible
4. Donnez un **nom** au diagramme (par exemple "Datamart Incidents")
5. Ajoutez une **description** optionnelle
6. **Selectionnez les tables** a inclure dans le diagramme :
   - Utilisez le champ de filtre pour trouver rapidement une table
   - Cochez les tables souhaitees
   - Utilisez **Select All** / **Select None** pour gagner du temps
7. Cliquez sur **Create**

![Dialog de creation d'un diagramme ER](screenshots/10-new-diagram-dialog.png)

Le diagramme s'affiche avec les tables disposees automatiquement en grille. Les **relations FK** sont detectees automatiquement depuis les metadata de la base.

---

## Lire le diagramme

Chaque table affiche :

| Element | Signification |
|---------|---------------|
| **En-tete bleu** | Nom de la table (avec schema si applicable) |
| **PK** (jaune) | Colonne cle primaire |
| **FK** (cyan) | Colonne cle etrangere |
| Colonnes blanches | Colonnes ordinaires |
| Type en gris | Type de donnees de la colonne |

Les **lignes orange** representent les relations FK entre les tables, avec une **fleche** pointant vers la table referencee. Au survol d'une ligne, un **tooltip** affiche le detail de la relation (ex: `fact_Incident.SLA_ID → dim_SLA.SLA_ID`).

![Diagramme ER avec tables et relations FK](screenshots/10-er-diagram-view.png)

---

## Organiser le diagramme

### Deplacer les tables

**Cliquez-glissez** une table pour la repositionner. Les lignes FK se redessinent automatiquement.

### Redimensionner une table

Si une table a beaucoup de colonnes, elle dispose d'un **scroll interne**. Vous pouvez aussi la **redimensionner** en faisant glisser la poignee en bas a droite (petit triangle gris).

### Ajuster les lignes FK

Au **survol** d'une ligne FK, un **point orange** apparait au centre du segment. **Deplacez ce point** pour ajuster manuellement le trace de la relation. Cela est utile quand plusieurs lignes se chevauchent.

> **Note** : quand vous deplacez une table, les ajustements manuels des lignes sont reinitialises au routage automatique.

### Zoom

Utilisez la **molette de la souris** pour zoomer/dezoomer. Maintenez le clic et glissez pour **naviguer** dans le diagramme.

---

## Sauvegarder et restaurer

Cliquez sur **Save Positions** pour sauvegarder :
- Les **positions** de toutes les tables
- Les **ajustements manuels** des lignes FK
- Le **niveau de zoom**

Au prochain chargement du diagramme, tout est restaure exactement comme vous l'aviez laisse.

---

## Ajouter des tables

Pour enrichir un diagramme existant :

1. Ouvrez le diagramme
2. Cliquez sur **Add Tables** dans la barre d'outils
3. Les tables deja presentes sont exclues de la liste
4. Selectionnez les nouvelles tables et cliquez sur **Add**

Les nouvelles tables sont ajoutees et les FK detectees automatiquement.

---

## Exporter

Deux formats d'export sont disponibles :

- **Export PNG** : image bitmap, ideale pour la documentation ou les presentations
- **Export SVG** : image vectorielle, ideale pour l'impression ou l'integration web

L'export capture le diagramme tel qu'il est affiche, avec les positions, le zoom et les relations.

---

## Supprimer un diagramme

Cliquez sur **Delete** dans la barre d'outils. Une confirmation est demandee. La suppression est definitive — les positions et les ajustements sont perdus.

---

## Plusieurs diagrammes par base

Vous pouvez creer **plusieurs diagrammes** pour la meme connexion. Chaque diagramme represente un sous-ensemble de tables — typiquement un domaine fonctionnel ou un "datamart" :

- "Datamart Incidents" : fact_Incident + dimensions associees
- "Datamart RH" : fact_Employee + dim_Department + dim_Site
- "Referentiel Clients" : dim_Client + dim_Contract + dim_Address

Le panneau de gauche liste tous vos diagrammes, filtrable par connexion.

---

## Astuce

- Commencez par la **table de faits** (fact_*) et ajoutez progressivement les tables de dimension liees. C'est plus lisible que d'ajouter toutes les tables d'un coup.
- Sauvegardez regulierement vos positions apres chaque reorganisation. Les positions ne sont pas sauvegardees automatiquement.
- Les diagrammes sont un excellent outil pour **documenter** votre datawarehouse. Exportez-les en PNG et integrez-les dans vos documents de specification.

---

## Ce qui se passe en coulisse

- Les relations FK sont lues depuis les metadata systeme de la base : `sys.foreign_keys` (SQL Server), `INFORMATION_SCHEMA` (PostgreSQL, MySQL), `PRAGMA foreign_key_list` (SQLite), ODBC catalog (Access).
- Les cles primaires sont detectees de la meme maniere pour afficher les indicateurs PK.
- Le rendu utilise `QGraphicsScene` / `QGraphicsView` de PySide6, qui est optimise pour afficher des centaines d'elements graphiques avec un rendu fluide.
- Les diagrammes sont sauvegardes dans 3 tables de la base de configuration locale : `er_diagrams`, `er_diagram_tables` (positions), `er_diagram_fk_midpoints` (ajustements de lignes).

---

[<< Reference rapide](09-reference.md)
