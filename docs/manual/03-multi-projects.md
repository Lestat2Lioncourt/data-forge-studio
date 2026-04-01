# 03 - Travailler sur plusieurs projets en parallele

> **Situation** : Vous gerez plusieurs clients ou environnements (dev, staging, production) et vous avez besoin d'organiser vos connexions, dossiers et requetes par contexte.

---

## Comprendre les Workspaces

Un **Workspace** est un conteneur logique qui regroupe :

- **Databases** : les connexions aux bases de donnees
- **Root Folders** : les repertoires de fichiers de donnees
- **Queries** : les requetes SQL sauvegardees
- **Scripts** : les scripts Python associes
- **Jobs** : les taches planifiees

Les Workspaces fonctionnent en **many-to-many** : une meme ressource peut etre rattachee a plusieurs workspaces. Modifier une connexion dans un workspace la met a jour partout.

---

## Creer un workspace

1. Ouvrez le **Workspace Manager** via la barre laterale gauche
2. Cliquez sur **New** dans la barre d'outils
3. Renseignez :
   - **Nom** : un nom parlant (ex : "Client Alpha - Production")
   - **Description** : contexte du workspace (optionnel)
4. Cochez **Set as default** si vous voulez qu'il s'ouvre automatiquement au demarrage
5. **Save**

![Dialogue de creation de workspace](screenshots/03-new-workspace-dialog.png)

---

## Organiser les ressources par workspace

### Rattacher une base de donnees

1. Dans le Workspace Manager, depliez votre workspace
2. **Clic droit** sur le noeud **Databases**
3. Choisissez **Ajouter une base existante** et selectionnez la connexion
4. La base apparait dans l'arbre sous ce workspace

### Rattacher un dossier de fichiers

1. **Clic droit** sur le noeud **Root Folders** du workspace
2. Choisissez **Ajouter un RootFolder existant** ou creez-en un nouveau
3. Le dossier et son contenu deviennent accessibles depuis ce workspace

### Retirer une ressource

- **Clic droit** sur la ressource dans le workspace > **Retirer du workspace**
- La ressource n'est pas supprimee, seulement detachee de ce workspace

---

## Cas pratique : gestion multi-clients

Imaginons trois clients avec des bases de donnees differentes :

```
Workspace "Client Alpha"
  Databases
    Prod - Alpha_DB
    Staging - Alpha_DB
  Root Folders
    //serveur/data/alpha/
  Queries
    Report mensuel ventes
    Controle qualite donnees

Workspace "Client Beta"
  Databases
    Prod - Beta_DB
  Root Folders
    C:\Data\beta\imports\

Workspace "Transversal"
  Databases
    Prod - Alpha_DB      (partagee avec Client Alpha)
    Prod - Beta_DB       (partagee avec Client Beta)
    DWH - Reporting
```

Chaque workspace isole le contexte de travail. Basculer d'un client a l'autre se fait en un clic dans l'arbre.

---

## Filtrer l'arbre du workspace

Quand un workspace contient beaucoup de ressources, utilisez le **filtre** en haut de l'arbre :

1. Tapez un terme de recherche dans le champ filtre
2. L'arbre se filtre automatiquement apres un court delai (debounce de 400 ms)
3. Seuls les noeuds correspondants restent visibles

Le filtre fonctionne sur les noms de bases, dossiers, fichiers et requetes.

![Arbre du workspace filtre avec le terme de recherche](screenshots/03-workspace-tree-filtered.png)

---

## Workspace par defaut et auto-connexion

- Un seul workspace peut etre marque comme **workspace par defaut**
- Au demarrage, ce workspace s'ouvre automatiquement avec ses branches deployees
- Les connexions FTP du workspace par defaut se connectent de maniere asynchrone (avec un timeout de 3 secondes pour la verification de joignabilite)

Pour definir le workspace par defaut :

1. **Clic droit** sur le workspace > **Set as Default**
2. Ou lors de la creation/edition, cochez **Set as default**

---

## Exporter et importer un workspace

Pour partager une configuration de workspace avec un collegue ou la sauvegarder :

### Export

1. **Clic droit** sur le workspace > **Exporter**
2. Choisissez l'emplacement du fichier JSON
3. Le fichier contient toutes les connexions, dossiers et requetes du workspace

### Import

1. Cliquez sur **Importer** dans la barre d'outils du Workspace Manager
2. Selectionnez le fichier JSON
3. En cas de conflit de nom, choisissez le mode de resolution (ecraser, renommer, ignorer)

---

## Astuce

- Creez un workspace **"Tous les projets"** (ou utilisez la vue globale) quand vous avez besoin de chercher une ressource sans savoir dans quel contexte elle se trouve.
- Les onglets de requete ouverts dans un workspace restent dans le contexte de ce workspace : les resultats de `Edit Query` (clic droit sur une cellule contenant du SQL) s'ouvrent dans le meme workspace.
- Utilisez des noms de workspace explicites avec le client et l'environnement : "Alpha - Prod", "Alpha - Dev", "Beta - Staging".

---

## Ce qui se passe en coulisse

- Les workspaces sont stockes dans la table `projects` de la base de configuration (`_AppConfig/configuration.db`).
- Les associations workspace-ressources sont gerees par des tables de jointure many-to-many (`project_file_roots`, `project_databases`).
- Le filtre de l'arbre utilise un systeme de debounce pour eviter des rafraichissements excessifs pendant la frappe.
- L'export JSON inclut un resume (`get_export_summary`) qui liste le nombre de connexions, dossiers et requetes exportes.

---

[<< Explorer une base inconnue](02-explore-database.md) | [Suivant : Requetes multi-onglets >>](04-compare-data.md)
