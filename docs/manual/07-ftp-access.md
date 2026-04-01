# 07 - Acceder a un serveur FTP distant

> **Situation** : Des fichiers de donnees sont deposes regulierement sur un serveur FTP par un partenaire ou un systeme automatise. Vous devez les consulter et les telecharger sans quitter DataForge Studio.

---

## Configurer une racine FTP

1. Ouvrez le **FTP Root Manager** via la barre laterale gauche (ou depuis le menu)
2. Cliquez sur **New** dans la barre d'outils
3. Renseignez les informations de connexion :

   | Champ | Description | Exemple |
   |-------|-------------|---------|
   | **Nom** | Nom d'affichage | FTP Partenaire Alpha |
   | **Hote** | Adresse du serveur FTP | ftp.partenaire.com |
   | **Port** | Port FTP (21 par defaut) | 21 |
   | **Utilisateur** | Login FTP | data_user |
   | **Mot de passe** | Mot de passe FTP | ******** |
   | **Repertoire distant** | Dossier de depart | /exports/quotidiens |
   | **Description** | (optionnel) | Fichiers CSV quotidiens du partenaire Alpha |

4. Cliquez sur **Test** pour verifier la connexion
5. **Save**

[Screenshot: Dialogue de configuration FTP avec les champs remplis]

---

## Naviguer dans les fichiers distants

Une fois la racine FTP configuree, elle apparait dans l'arbre de navigation :

```
FTP Partenaire Alpha
  /exports/quotidiens/
    2024-01/
      ventes_20240101.csv
      ventes_20240102.csv
    2024-02/
      ventes_20240201.csv
```

- **Depliez les dossiers** pour explorer l'arborescence distante
- Le **nombre de fichiers** dans chaque dossier est affiche a cote du nom
- La navigation se fait de maniere asynchrone : l'interface reste reactive pendant le chargement

[Screenshot: Arbre FTP avec dossiers deplies et compteurs de fichiers]

---

## Telecharger des fichiers

Pour telecharger un fichier depuis le serveur FTP :

1. **Clic droit** sur le fichier dans l'arbre FTP
2. Selectionnez **Telecharger** (Download)
3. Choisissez le repertoire de destination local
4. Le fichier est telecharge

Pour un dossier complet, la meme procedure s'applique : tous les fichiers du dossier sont telecharges recursivement.

---

## Rattacher un FTP a un workspace

Tout comme les RootFolders locaux, les racines FTP peuvent etre rattachees a un workspace :

1. Ouvrez le **Workspace Manager**
2. **Clic droit** sur le workspace cible
3. Selectionnez **Ajouter un FTP Root**
4. Choisissez la racine FTP a rattacher

Au demarrage, si le workspace par defaut contient des racines FTP, elles sont connectees automatiquement en arriere-plan.

---

## Verification de joignabilite

Avant de deployer l'arbre FTP complet, DataForge Studio effectue une **verification rapide** :

- Timeout de **3 secondes** pour tester si le serveur repond
- Si le serveur est injoignable, un message d'avertissement s'affiche dans l'arbre sans bloquer l'interface
- Vous pouvez relancer la connexion manuellement via **clic droit > Reconnecter**

---

## Astuce

- Rattachez vos FTP roots aux workspaces correspondants pour retrouver rapidement les fichiers dans leur contexte projet.
- Si un serveur FTP est lent a repondre, naviguez d'abord dans vos ressources locales : la connexion FTP se fait en arriere-plan et l'arbre se completera automatiquement.
- Combinez FTP et RootFolders locaux : telechargez les fichiers depuis le FTP dans un RootFolder local pour pouvoir utiliser la vue combinee et les filtres de colonnes.

---

## Ce qui se passe en coulisse

- La connexion FTP est geree par la classe `FTPClient` qui encapsule les operations standard (login, list, download).
- Le chargement de l'arbre FTP est asynchrone : un `QThread` worker (`ftp_workers.py`) effectue les operations reseau sans bloquer le thread UI.
- Les racines FTP sont stockees dans une table dediee de la base de configuration, avec les memes mecanismes de persistance que les connexions de bases de donnees.
- La verification de joignabilite utilise un test de socket sur le port FTP avec un timeout de 3 secondes, avant d'initier la connexion complete.

---

[<< Formater et sauvegarder des requetes](06-format-queries.md) | [Suivant : Personnaliser l'environnement >>](08-customize.md)
