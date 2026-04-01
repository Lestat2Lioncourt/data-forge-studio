# 05 - Arborescence de fichiers

> **Situation** : Vous recevez regulierement des fichiers CSV, Excel ou JSON avec la meme structure (exports mensuels, feeds quotidiens). Vous avez besoin de les explorer, les combiner et les filtrer.

---

## Configurer un RootFolder

Un **RootFolder** (racine de fichiers) est un repertoire local que DataForge Studio surveille et permet d'explorer dans son arbre de navigation.

### Ajouter un RootFolder

1. Ouvrez le **RootFolder Manager** via la barre laterale gauche
2. Cliquez sur **New** dans la barre d'outils
3. Renseignez :
   - **Nom** : un nom descriptif (ex : "Exports mensuels - Ventes")
   - **Chemin** : le repertoire contenant vos fichiers (ex : `C:\Data\exports\ventes`)
   - **Description** : (optionnel) contexte ou provenance des fichiers
4. **Save**

Le repertoire et son contenu apparaissent dans l'arbre de navigation.

![Arbre du RootFolder avec sous-dossiers et fichiers](screenshots/05-rootfolder-tree.png)

---

## Explorer les fichiers

### Naviguer dans l'arbre

Depliez le RootFolder pour voir la hierarchie de dossiers et fichiers. DataForge Studio reconnait les types suivants :

| Type | Extensions | Affichage |
|------|-----------|-----------|
| CSV | `.csv` | Grille de donnees |
| Excel | `.xlsx`, `.xls` | Grille de donnees |
| JSON | `.json` | Grille (si tabulaire) ou vue formatee |
| Texte | `.txt`, `.log`, `.sql` | Vue texte avec coloration |

### Ouvrir un fichier

**Cliquez** sur un fichier dans l'arbre. Le contenu s'affiche dans le panneau de droite :

- Pour les fichiers tabulaires (CSV, Excel) : une grille interactive avec tri et filtres
- Pour les fichiers texte : un viewer avec coloration syntaxique
- Pour les fichiers JSON : detection automatique du format (tableau d'objets, objets imbriques)

![Fichier CSV ouvert dans la grille avec en-tetes et donnees](screenshots/05-csv-file-grid.png)

---

## Detection automatique de l'encodage

Un des atouts de DataForge Studio : l'encodage des fichiers est **detecte automatiquement**. Plus besoin de deviner si un fichier est en UTF-8, Latin-1 ou Windows-1252.

Le processus :

1. L'application lit un echantillon du fichier (100 Ko)
2. Elle identifie l'encodage le plus probable
3. Le fichier est ouvert avec le bon encodage
4. L'encodage detecte est affiche dans la barre d'information (ex : "Encoding: UTF-8")

De meme, le **separateur CSV** (virgule, point-virgule, tabulation) est detecte automatiquement.

---

## Vue combinee : fusionner les fichiers d'un dossier

Quand un dossier contient plusieurs fichiers de meme structure (par exemple des exports mensuels), vous pouvez les voir tous dans une seule grille :

1. **Clic droit** sur un dossier dans l'arbre
2. Selectionnez **"Voir tous les fichiers combines"** (View all data files combined)
3. DataForge Studio charge tous les fichiers CSV, Excel et JSON du dossier
4. Les donnees sont fusionnees dans une grille unique

L'application gere intelligemment les cas ou les fichiers n'ont pas exactement les memes colonnes : les colonnes manquantes sont remplies avec des valeurs vides.

![Vue combinee de plusieurs fichiers CSV dans une seule grille](screenshots/05-combined-view.png)

---

## Filtres de colonnes

La grille de donnees dispose de **filtres par colonne** pour analyser rapidement un sous-ensemble :

1. Les filtres sont accessibles dans l'en-tete de la grille
2. Tapez un texte dans le champ filtre d'une colonne
3. La grille affiche uniquement les lignes correspondantes
4. Les filtres sont combinables sur plusieurs colonnes (ET logique)

Les filtres fonctionnent aussi bien sur les fichiers locaux que sur les resultats de requetes SQL.

---

## Ouvrir l'emplacement dans l'explorateur systeme

Pour acceder rapidement au fichier sur le disque :

1. **Clic droit** sur un fichier dans l'arbre
2. Selectionnez **"Open in file explorer"**
3. L'explorateur systeme s'ouvre directement dans le dossier contenant le fichier

Cette fonctionnalite est disponible sur Windows, macOS et Linux.

---

## Rattacher un RootFolder a un workspace

Pour organiser vos dossiers par projet (voir [chapitre 03](03-multi-projects.md)) :

1. **Clic droit** sur le RootFolder dans l'arbre du Workspace Manager
2. Selectionnez **Ajouter a un workspace**
3. Choisissez le workspace cible

Le meme RootFolder peut appartenir a plusieurs workspaces.

---

## Astuce

- Nommez vos RootFolders par leur source et leur frequence : "FTP Alpha - Quotidien", "Export Sage - Mensuel". Vous retrouverez ainsi rapidement le bon dossier.
- La vue combinee est ideale pour verifier la coherence entre des fichiers successifs : si une colonne manque dans un fichier, elle apparait vide dans la grille combinee, ce qui saute aux yeux.
- Utilisez le tri multi-colonnes (**Ctrl+Clic** sur les en-tetes) pour reperer les doublons ou les anomalies dans les fichiers combines.

---

## Ce qui se passe en coulisse

- La detection d'encodage utilise un echantillon de 100 Ko analyse par une heuristique statistique. Les encodages testes incluent UTF-8 (avec et sans BOM), Latin-1, Windows-1252, et ISO-8859-15.
- La detection du separateur CSV analyse les 5 premieres lignes et compte les occurrences de `,`, `;`, `\t` et `|` pour determiner le separateur le plus probable.
- La vue combinee (`merge_folder_files`) charge chaque fichier individuellement, detecte l'union de toutes les colonnes, puis concatene les DataFrames avec `pandas.concat`.
- Les fichiers JSON avec structure "row-keyed" (`{"id1": {...}, "id2": {...}}`) sont automatiquement convertis en table avec une colonne `_id` contenant les cles originales.
- Les filtres de colonnes fonctionnent en memoire sur le DataFrame charge, sans relire le fichier.

---

[<< Requetes multi-onglets](04-compare-data.md) | [Suivant : Formater et sauvegarder des requetes >>](06-format-queries.md)
