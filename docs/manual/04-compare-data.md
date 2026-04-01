# 04 - Requetes multi-onglets

> **Situation** : Vous devez executer plusieurs requetes en parallele, comparer des resultats entre deux bases, ou lancer un batch de requetes et visualiser chaque resultat dans son propre onglet.

---

## Plusieurs requetes dans un seul editeur

Vous pouvez saisir **plusieurs requetes dans le meme editeur**, separees par `;`. Chaque requete produit son propre onglet de resultat :

```sql
SELECT COUNT(*) FROM clients;

SELECT COUNT(*) FROM commandes;

SELECT TOP 10  *
FROM           clients
ORDER BY       date_creation DESC;
```

A l'execution (**F5**), DataForge Studio :

1. Detecte les 3 requetes (separees par `;`)
2. Cree un onglet de resultat pour chaque SELECT
3. Affiche un onglet **Messages** avec le journal d'execution

Le mode d'execution est selectionnable dans la barre d'outils :

| Mode | Comportement |
|------|-------------|
| **Auto** | Detecte automatiquement : si toutes les requetes sont des SELECT, mode parallele. Sinon, mode script |
| **Query** | Chaque SELECT s'execute sur sa propre connexion (parallele, plus rapide) |
| **Script** | Toutes les requetes s'executent sequentiellement sur la meme connexion (preserve les variables) |

---

## Variables partagees entre requetes

Si votre batch utilise des **variables T-SQL**, le mode Script est automatiquement active pour que les variables persistent :

```sql
DECLARE @seuil INT = 1000;

SELECT           client_id
               , SUM(montant) AS total
FROM             commandes
GROUP BY         client_id
HAVING           SUM(montant) > @seuil;

SELECT           COUNT(*) AS nb_gros_clients
FROM             commandes
GROUP BY         client_id
HAVING           SUM(montant) > @seuil;
```

Les deux SELECT ont acces a `@seuil`. Chacun produit son propre onglet de resultat.

---

## Ouvrir plusieurs onglets de requete

Le Database Manager supporte les **onglets multiples**. Chaque onglet est independant : sa propre connexion, son propre editeur SQL, ses propres resultats.

1. Ouvrez le **Database Manager**
2. Un premier onglet est deja present
3. Cliquez sur le **+** pour ajouter un deuxieme onglet
4. Dans chaque onglet, selectionnez la base de donnees cible dans le selecteur de connexion

![Deux onglets de requete avec des connexions differentes](screenshots/04-two-query-tabs.png)

### Renommer les onglets

Double-cliquez sur le titre d'un onglet pour le renommer. Utilisez des noms explicites comme "Prod - clients" et "Staging - clients".

---

## Split view : editeur et resultats cote a cote

Par defaut, l'editeur SQL est au-dessus et les resultats en dessous (mode empile). Pour passer en mode **cote a cote** :

1. Cliquez sur le bouton **Split Toggle** dans la barre d'outils de l'onglet (icone de disposition)
2. L'editeur passe a gauche et les resultats a droite
3. Cliquez a nouveau pour revenir au mode empile

Ce mode est utile sur un ecran large pour garder la requete visible tout en consultant les resultats.

![Split view en mode cote a cote avec editeur a gauche et resultats a droite](screenshots/04-split-view-side-by-side.png)

---

## Detacher un onglet dans une fenetre separee

Pour comparer visuellement deux jeux de resultats, vous pouvez **detacher un onglet** :

1. Cliquez sur le bouton **Detach** dans la barre d'outils de l'onglet
2. L'onglet s'ouvre dans une fenetre independante, redimensionnable
3. Positionnez les fenetres cote a cote sur votre ecran

La fenetre detachee conserve toutes les fonctionnalites : execution, formatage, export, split view.

Pour **re-attacher** l'onglet, fermez la fenetre : l'onglet revient automatiquement dans la fenetre principale et le panel Database s'active.

![Deux fenetres cote a cote, chacune avec une requete sur une base differente](screenshots/04-detached-tabs-side-by-side.png)

---

## Tri multi-colonnes dans les resultats

Pour affiner l'analyse dans la grille de resultats :

- **Clic** sur un en-tete de colonne : tri ascendant, puis descendant
- **Ctrl+Clic** sur un autre en-tete : ajoute cette colonne au tri (multi-colonnes)
- Des indicateurs numerotes (1▲, 2▼...) montrent l'ordre de priorite du tri

### Filtrer les resultats

Clic droit sur un en-tete de colonne pour filtrer :

- **Filter "NomColonne"...** : saisir un texte — seules les lignes contenant ce texte (insensible a la casse) sont affichees
- Les filtres sont **cumulatifs** (AND) : filtrer sur deux colonnes affine le resultat
- Une loupe (🔍) s'affiche dans l'en-tete des colonnes filtrees
- **Clear filter** / **Clear all filters** pour retirer les filtres

Les filtres n'affectent que l'affichage — les donnees et l'export CSV restent complets.

---

## Vue plein ecran

Pour examiner un jeu de resultats volumineux :

1. Cliquez sur le bouton **Fullscreen** dans la barre d'outils de la grille
2. La grille s'ouvre en plein ecran
3. Appuyez sur **Echap** pour revenir a la vue normale

Le tri et le filtrage fonctionnent aussi en mode plein ecran.

---

## Astuce

- Utilisez des noms d'onglets explicites : "Prod - COUNT clients" vs "Staging - COUNT clients". Les onglets detaches conservent leur nom dans la barre de titre.
- Pour comparer les memes donnees entre deux bases, ecrivez la requete une fois, copiez-la dans le deuxieme onglet, et changez la connexion.
- Si vous comparez regulierement les memes jeux de donnees, sauvegardez vos requetes (voir [chapitre 06](06-format-queries.md)).

---

## Ce qui se passe en coulisse

- Chaque onglet de requete est une instance de `QueryTab` avec son propre `QSplitter` et sa propre connexion.
- En mode **Query**, chaque SELECT s'execute sur une connexion parallele pour ne pas bloquer les autres. En mode **Script**, tout passe par la meme connexion sequentiellement.
- Quand des `DECLARE`/`SET` sont detectes, le batch entier est envoye au serveur en une seule commande via `cursor.execute()`, et les result sets sont recuperes via `cursor.nextset()`.
- Les onglets detaches utilisent `PopupWindow` avec reparentage du widget — la connexion, le curseur et les resultats restent intacts.

---

[<< Travailler sur plusieurs projets](03-multi-projects.md) | [Suivant : Arborescence de fichiers >>](05-data-files.md)
