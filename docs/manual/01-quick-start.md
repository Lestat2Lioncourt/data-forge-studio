# 01 - Demarrage rapide

> **Situation** : Vous venez d'installer DataForge Studio et vous voulez executer votre premiere requete SQL en moins de 5 minutes.

---

## Installation

### Prerequis

- Un poste Windows, macOS ou Linux
- Aucune installation de Python requise (UV s'en charge)

### Etapes

1. **Installer UV** (gestionnaire de paquets Python ultra-rapide) :

   ```powershell
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Cloner et lancer** :

   ```bash
   git clone https://github.com/Lestat2Lioncourt/data-forge-studio.git
   cd data-forge-studio
   uv sync
   uv run python run.py
   ```

   UV telecharge automatiquement Python 3.10+ si necessaire, puis installe toutes les dependances.

   > **En entreprise** : si `uv sync` echoue avec une erreur `invalid peer certificate: UnknownIssuer`, votre proxy d'entreprise intercepte le TLS. Utilisez :
   > ```bash
   > uv --system-certs sync
   > uv --system-certs run python run.py
   > ```
   > Le flag `--system-certs` utilise les certificats du systeme (incluant ceux de l'entreprise).
   > Pour eviter de le taper a chaque fois, definissez la variable d'environnement : `UV_SYSTEM_CERTS=1`

3. **(Optionnel) Creer un raccourci bureau** :

   ```bash
   uv run python scripts/create_shortcut.py
   ```

![Splash screen au lancement de l'application](screenshots/01-splash-screen.png)

---

## Premiere connexion a une base de donnees

Au premier lancement, DataForge Studio cree automatiquement une base de configuration interne (`_AppConfig/configuration.db`). Elle est visible dans le Database Manager et sert a stocker vos connexions, requetes et preferences.

Pour ajouter votre propre base de donnees :

1. Ouvrez le **Database Manager** via la barre laterale gauche (icone base de donnees)
2. Dans le panneau de gauche, cliquez sur le bouton **+ New Connection** dans la barre d'outils
3. Renseignez les informations :
   - **Nom** : un nom parlant (ex : "Prod - Clients")
   - **Type** : SQL Server, PostgreSQL, MySQL, SQLite ou Oracle
   - **Connection string** : la chaine de connexion adaptee a votre type de base
4. Cliquez sur **Test Connection** pour verifier la connectivite
5. Cliquez sur **Save**

![Dialogue de creation de connexion avec les champs remplis](screenshots/01-new-connection-dialog.png)

Le schema de la base (tables, vues, colonnes) se charge automatiquement dans l'arbre de navigation a gauche.

---

## Premiere requete SQL

1. Dans l'arbre du Database Manager, **depliez votre connexion** pour voir les tables
2. **Double-cliquez sur une table** : un `SELECT TOP 100 *` s'insere dans l'editeur
3. Appuyez sur **F5** (ou cliquez sur le bouton **Execute**) pour lancer la requete
4. Les resultats s'affichent dans la grille en dessous de l'editeur

Vous pouvez aussi ecrire directement votre SQL dans l'editeur :

```sql
SELECT *
FROM clients
WHERE ville = 'Paris'
ORDER BY nom
```

Puis **F5** pour executer.

![Editeur SQL avec resultats dans la grille](screenshots/01-sql-editor-with-results.png)

---

## Naviguer dans l'interface

L'interface se compose de trois zones principales :

| Zone | Emplacement | Role |
|------|-------------|------|
| **Barre laterale** (IconSidebar) | Gauche | Naviguer entre les managers (Database, Workspace, RootFolders, etc.) |
| **Panneau principal** | Centre/Droite | Afficher le manager actif avec son arbre et son contenu |
| **Barre de statut** | Bas | Informations de version et notifications de mise a jour |

La barre laterale utilise des icones SVG et change de couleur selon le theme actif. Cliquez sur une icone pour basculer vers le manager correspondant.

---

## Astuce

- **Clic droit sur une table** dans l'arbre : un menu contextuel propose directement `SELECT TOP 100`, `TOP 1000`, `TOP 10000`, `ALL` ou `COUNT(*)`. La requete est executee instantanement.
- Le type de base est detecte automatiquement : `TOP` pour SQL Server, `LIMIT` pour PostgreSQL/MySQL/SQLite, `FETCH FIRST` pour Oracle.
- Pensez a utiliser **Ctrl+Espace** dans l'editeur SQL pour declencher l'auto-completion sur les noms de tables et de colonnes.

---

## Ce qui se passe en coulisse

- La configuration est stockee dans `_AppConfig/configuration.db` (une base SQLite locale). Chaque connexion, requete sauvegardee et preference y reside.
- Les logs applicatifs sont ecrits dans `_AppLogs/`. En cas de probleme, c'est le premier endroit a consulter.
- La coloration syntaxique SQL est assuree par un `QSyntaxHighlighter` personnalise qui reconnait les mots-cles SQL, les variables T-SQL (`@variable`), les chaines et les commentaires.

---

[Suivant : Explorer une base inconnue >>](02-explore-database.md)
