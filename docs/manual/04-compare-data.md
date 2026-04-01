# 04 - Comparer des donnees entre deux bases

> **Situation** : Vous devez comparer les donnees entre un environnement de staging et la production, ou entre deux bases clients, pour identifier les ecarts.

---

## Ouvrir plusieurs onglets de requete

Le Database Manager supporte les **onglets multiples**. Chaque onglet est independant : sa propre connexion, son propre editeur SQL, ses propres resultats.

1. Ouvrez le **Database Manager**
2. Un premier onglet est deja present
3. Cliquez sur le **+** pour ajouter un deuxieme onglet
4. Dans chaque onglet, selectionnez la base de donnees cible dans le selecteur de connexion

![Deux onglets de requete avec des connexions differentes](screenshots/04-two-query-tabs.png)

### Renommer les onglets

Double-cliquez sur le titre d'un onglet pour le renommer. Utilisez des noms explicites comme "Prod - clients" et "Staging - clients" pour savoir lequel est lequel.

---

## Split view : editeur et resultats cote a cote

Par defaut, l'editeur SQL est au-dessus et les resultats en dessous (mode empile). Pour passer en mode **cote a cote** :

1. Cliquez sur le bouton **Split Toggle** dans la barre d'outils de l'onglet (icone de disposition)
2. L'editeur passe a gauche et les resultats a droite
3. Cliquez a nouveau pour revenir au mode empile

Ce mode est particulierement utile sur un ecran large pour garder la requete visible tout en consultant les resultats.

![Split view en mode cote a cote avec editeur a gauche et resultats a droite](screenshots/04-split-view-side-by-side.png)

---

## Detacher un onglet dans une fenetre separee

Pour comparer visuellement deux jeux de resultats, vous pouvez **detacher un onglet** :

1. **Clic droit** sur l'onglet de requete
2. Selectionnez **Detach tab** (ou faites glisser l'onglet hors de la fenetre)
3. L'onglet s'ouvre dans une **PopupWindow** independante avec sa propre barre de titre
4. Redimensionnez et positionnez les fenetres cote a cote

La fenetre detachee conserve toutes les fonctionnalites : execution, formatage, export, split view.

Pour **re-attacher** l'onglet, fermez la fenetre detachee : l'onglet revient dans la fenetre principale.

![Deux fenetres cote a cote, chacune avec une requete sur une base differente](screenshots/04-detached-tabs-side-by-side.png)

---

## Scenario pas a pas : comparer les clients entre staging et prod

### Etape 1 -- Preparer les onglets

1. Creez deux onglets dans le Database Manager
2. Onglet 1 : connectez-vous a **Prod - ClientDB**
3. Onglet 2 : connectez-vous a **Staging - ClientDB**

### Etape 2 -- Executer la meme requete

Dans chaque onglet, executez :

```sql
SELECT statut,
       COUNT(*) AS nb_clients,
       MIN(date_creation) AS premiere_creation,
       MAX(date_creation) AS derniere_creation
FROM clients
GROUP BY statut
ORDER BY nb_clients DESC
```

### Etape 3 -- Comparer visuellement

1. Detachez le deuxieme onglet dans une fenetre separee
2. Placez les deux fenetres cote a cote sur votre ecran
3. Comparez les chiffres ligne par ligne

### Etape 4 -- Exporter pour analyse croisee

Si les volumes sont importants :

1. Exportez les resultats de chaque onglet en **CSV**
2. Chargez les deux fichiers dans un outil de comparaison (Excel, Python, etc.)

---

## Tri multi-colonnes dans les resultats

Pour affiner l'analyse dans la grille de resultats :

- **Clic** sur un en-tete de colonne : tri ascendant, puis descendant, puis aucun tri
- **Ctrl+Clic** sur un autre en-tete : ajoute cette colonne au tri (multi-colonnes)
- Des indicateurs numerotes (1, 2, 3...) montrent l'ordre de priorite du tri

Cela permet par exemple de trier par statut puis par date de creation, directement dans la grille.

---

## Vue plein ecran

Pour examiner un jeu de resultats volumineux :

1. **Double-cliquez** sur la grille de resultats (ou utilisez le bouton plein ecran)
2. La grille s'ouvre dans une fenetre plein ecran
3. Appuyez sur **Echap** pour revenir a la vue normale

Le tri multi-colonnes fonctionne aussi en mode plein ecran.

---

## Astuce

- Utilisez des noms d'onglets avec le contexte : "Prod - COUNT clients" vs "Staging - COUNT clients". Quand les onglets sont detaches, vous saurez immediatement a quoi correspond chaque fenetre.
- Le bouton **Format** permet de formater les deux requetes de la meme maniere, ce qui facilite la comparaison visuelle du SQL lui-meme.
- Si vous comparez regulierement les memes jeux de donnees, sauvegardez vos requetes (voir [chapitre 06](06-format-queries.md)) pour les retrouver instantanement.

---

## Ce qui se passe en coulisse

- Chaque onglet de requete est une instance de `QueryTab` avec son propre `QSplitter` (pour le split view) et sa propre connexion a la base.
- Les onglets detaches utilisent la classe `PopupWindow`, une fenetre thematique avec barre de titre personnalisee et support du redimensionnement par les bords.
- Le tri multi-colonnes repose sur le tri stable de Python : on trie sequentiellement par chaque colonne dans l'ordre inverse de priorite, ce qui garantit un resultat correct.
- Le `QSplitter` gere dynamiquement la repartition de l'espace entre editeur et resultats. La barre separatrice peut etre deplacee a la souris.

---

[<< Travailler sur plusieurs projets](03-multi-projects.md) | [Suivant : Travailler avec des fichiers >>](05-data-files.md)
