# 09 - Reference rapide

> Raccourcis clavier, bases supportees, glossaire et questions frequentes.

---

## Raccourcis clavier

### Editeur SQL

| Raccourci | Action |
|-----------|--------|
| **F5** | Executer la requete (onglet actif dans le Database Manager) |
| **F6** | Executer la requete (onglet actif dans un workspace) |
| **Tab** | Inserer 4 espaces (pas de caractere tabulation) |
| **Entree** | Nouvelle ligne avec auto-indent (reprend l'indentation de la ligne courante) |
| **Ctrl+Espace** | Declencher l'auto-completion (noms de tables, colonnes) |
| **Echap** | Fermer l'auto-completion / quitter le plein ecran |

### Grille de resultats

| Raccourci | Action |
|-----------|--------|
| **Clic sur en-tete** | Trier par cette colonne (ascendant > descendant) |
| **Ctrl+Clic sur en-tete** | Ajouter la colonne au tri multi-colonnes |
| **Clic droit sur en-tete** | Filtrer la colonne (contains), effacer les filtres |
| **Double-clic sur la grille** | Ouvrir en plein ecran |
| **Echap** | Fermer la vue plein ecran |

### Navigation

| Raccourci | Action |
|-----------|--------|
| **Double-clic sur une table** (arbre) | Inserer `SELECT TOP 100 *` dans l'editeur |
| **Clic droit sur une table** (arbre) | Menu contextuel (SELECT TOP N, COUNT, etc.) |
| **Double-clic sur un onglet** | Renommer l'onglet |
| **Clic droit sur un onglet** | Options de l'onglet (detacher, fermer, etc.) |

---

## Bases de donnees supportees

### Vue d'ensemble

| Base | Driver | Connection string | Particularites |
|------|--------|-------------------|----------------|
| **SQL Server** | pyodbc (ODBC 17/18) | `Driver={ODBC Driver 18 for SQL Server};Server=...;Database=...;Trusted_Connection=yes` | `TOP N`, schemas `dbo.`, Windows Auth possible |
| **PostgreSQL** | psycopg2 | `postgresql://host:5432/db` | `LIMIT N`, schemas `public.`, guillemets doubles pour casse. Credentials via keyring |
| **MySQL** | pymysql | `mysql+pymysql://host:3306/db` | `LIMIT N`, backticks pour les identifiants. Credentials via keyring |
| **SQLite** | sqlite3 (natif) | Chemin du fichier `.db` | `LIMIT N`, pas de driver ODBC requis, module Python natif |
| **Oracle** | oracledb | `oracle+oracledb://host:1521/service` | `FETCH FIRST N ROWS ONLY`, schemas owner.table. Credentials via keyring |
| **Access** | pyodbc | `Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=path.accdb` | `TOP N`, fichier local uniquement |

### Installation des drivers

| Base | Windows | macOS | Linux |
|------|---------|-------|-------|
| SQL Server | ODBC Driver 18 (installateur Microsoft) | `brew install msodbcsql18` | `apt install msodbcsql18` |
| PostgreSQL | Aucun driver supplementaire | Aucun | Aucun |
| MySQL | Aucun driver supplementaire | Aucun | Aucun |
| SQLite | Aucun (natif Python) | Aucun | Aucun |
| Oracle | Oracle Instant Client | Oracle Instant Client | Oracle Instant Client |

### Adaptation automatique du SQL

Le menu contextuel (clic droit sur une table) genere du SQL adapte au type de base :

```sql
-- SQL Server
SELECT TOP 1000 * FROM [dbo].[clients]

-- PostgreSQL
SELECT * FROM "public"."clients" LIMIT 1000

-- SQLite
SELECT * FROM [clients] LIMIT 1000

-- Oracle
SELECT * FROM clients FETCH FIRST 1000 ROWS ONLY
```

Les identifiants sont **automatiquement echappes** avec la syntaxe du moteur cible (brackets, guillemets doubles, backticks).

---

## Formats de fichiers supportes

| Format | Extensions | Lecture | Vue combinee | Detection encodage |
|--------|-----------|---------|-------------|-------------------|
| CSV | `.csv` | Grille | Oui | Oui (auto) |
| Excel | `.xlsx`, `.xls` | Grille | Oui | N/A |
| JSON | `.json` | Grille ou texte | Oui | Oui (auto) |
| Texte | `.txt`, `.log` | Vue texte | Non | Oui (auto) |
| SQL | `.sql` | Vue texte coloree | Non | Oui (auto) |

---

## Glossaire

| Terme | Definition |
|-------|-----------|
| **Workspace** | Conteneur logique regroupant des bases, dossiers, requetes, scripts et jobs pour un projet ou contexte donne |
| **RootFolder** | Repertoire local configure comme racine de navigation dans DataForge Studio |
| **FTP Root** | Serveur FTP distant configure comme racine de navigation |
| **Query Tab** | Onglet de requete SQL dans le Database Manager, avec son editeur et sa grille de resultats |
| **Split View** | Mode d'affichage ou l'editeur et les resultats sont places cote a cote au lieu d'etre empiles |
| **PopupWindow** | Fenetre independante creee lors du detachement d'un onglet |
| **Schema** | Structure d'une base de donnees : tables, vues, colonnes et types |
| **Theme** | Jeu de couleurs applique a l'ensemble de l'interface |
| **IconSidebar** | Barre laterale gauche avec les icones de navigation entre managers |
| **Configuration DB** | Base SQLite interne (`_AppConfig/configuration.db`) stockant connexions, requetes et preferences |
| **Vue combinee** | Fusion de tous les fichiers de donnees d'un dossier dans une seule grille |
| **Filtres de colonnes** | Champs de filtrage dans l'en-tete de la grille pour restreindre les lignes affichees |

---

## FAQ

### L'application ne demarre pas

**Symptome** : Erreur d'import PySide6.

**Solution** :
```bash
uv pip install --force-reinstall PySide6
```

### Je ne peux pas me connecter a SQL Server

**Symptome** : "ODBC driver not found".

**Solution** : Installez le driver ODBC 17 ou 18 de Microsoft. Voir la section "Installation des drivers" ci-dessus.

### Le schema ne se charge pas

**Symptome** : L'arbre est vide apres connexion.

**Solutions** :
- Verifiez que la connexion fonctionne : **clic droit > Test Connection**
- Rafraichissez manuellement : **clic droit > Refresh Schema**
- Verifiez les permissions SQL de l'utilisateur sur les vues systeme (`INFORMATION_SCHEMA`)

### Les accents sont mal affiches dans un fichier CSV

**Symptome** : Caracteres remplaces par des `?` ou des symboles.

**Solution** : DataForge Studio detecte l'encodage automatiquement, mais en cas de mauvaise detection, verifiez l'encodage source avec un editeur de texte (Notepad++, VS Code) et renseignez l'encodage correct dans la configuration du fichier.

### Comment partager ma configuration avec un collegue ?

**Solution** : Exportez votre workspace en JSON (**clic droit > Exporter**) et transmettez le fichier. Votre collegue pourra l'importer via le Workspace Manager.

### Puis-je utiliser l'application hors ligne ?

**Oui.** DataForge Studio peut generer un **package offline** via **Tools > Generate Offline Package**. Le package contient Python, toutes les dependances et l'application. Voir `_packages/README_OFFLINE.md` pour les instructions.

### Comment mettre a jour sans perdre ma configuration ?

La configuration est stockee dans `_AppConfig/` qui n'est **pas affecte** par les mises a jour. Pour mettre a jour :

```bash
git pull
uv sync
```

Vos connexions, requetes sauvegardees, preferences et workspaces sont preserves.

---

## Structure des fichiers de configuration

```
_AppConfig/
  configuration.db    -- Toutes les donnees (connexions, requetes, preferences, workspaces)

_AppLogs/
  dataforge_*.log     -- Logs applicatifs (rotation quotidienne)
```

Pour sauvegarder toute votre configuration, copiez le dossier `_AppConfig/`. Pour la restaurer, replacez-le au meme emplacement.

---

[<< Personnaliser l'environnement](08-customize.md) | [Retour a la table des matieres](README.md)
