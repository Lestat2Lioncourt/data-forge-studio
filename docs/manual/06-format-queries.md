# 06 - Formater et sauvegarder des requetes

> **Situation** : Vous recevez une requete SQL sur une seule ligne dans un email, ou vous voulez sauvegarder vos requetes les plus utilisees pour les retrouver plus tard.

---

## Formater une requete SQL

### Les styles de formatage

DataForge Studio propose **4 styles de formatage** accessibles dans la barre d'outils de l'onglet de requete :

| Style | Description | Ideal pour |
|-------|-------------|------------|
| **Ultimate** | Mots-cles, AS, alias et operateurs tous alignes sur des colonnes fixes | Usage quotidien, lisibilite maximale |
| **Compact** | Plusieurs colonnes par ligne (limite 120 car.) | Requetes simples, logs |
| **Comma First** | Virgules en debut de ligne | Diff Git, detection d'erreurs |
| **Expanded** | Identique a Ultimate | Alias de Ultimate |

### Utiliser le formateur

1. Redigez ou collez votre requete dans l'editeur
2. Selectionnez le **style** souhaite dans le selecteur de la barre d'outils
3. Cliquez sur le bouton **Format**
4. La requete est reformatee instantanement avec la coloration syntaxique mise a jour

![Avant/apres formatage d'une requete complexe en style Ultimate](screenshots/06-format-before-after.png)

### Exemple concret

**Avant** (requete brute recue par email) :

```sql
SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.total) as total FROM users u JOIN orders o ON u.id=o.user_id WHERE u.status='active' AND o.date > '2024-01-01' GROUP BY u.id, u.name, u.email ORDER BY total DESC
```

**Apres** (style **Ultimate** — recommande) :

```sql
SELECT           u.id
               , u.name
               , u.email
               , COUNT(o.id)  AS order_count
               , SUM(o.total) AS total
FROM             users  u
JOIN             orders o ON  u.id = o.user_id
WHERE            u.status = 'active'
AND              o.date   > '2024-01-01'
GROUP BY         u.id
               , u.name
               , u.email
ORDER BY         total DESC
```

Points cles du style Ultimate :

- Tous les **mots-cles** (`SELECT`, `FROM`, `JOIN`, `WHERE`, `AND`, `ORDER BY`...) sont alignes sur la meme colonne (17 caracteres)
- Les **alias** sont alignes via `AS` sur une colonne commune
- Les **operateurs** (`=`, `>`, `IS NULL`...) sont alignes dans les conditions `WHERE`/`AND` et `ON`
- Les **tables** et **alias de table** sont alignes dans les `JOIN`

**Apres** (style Compact) :

```sql
SELECT u.id, u.name, u.email, COUNT(o.id) AS order_count, SUM(o.total) AS total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active'
  AND o.date > '2024-01-01'
GROUP BY u.id, u.name, u.email
ORDER BY total DESC
```

**Apres** (style Comma First) :

```sql
SELECT u.id
     , u.name
     , u.email
     , COUNT(o.id) AS order_count
     , SUM(o.total) AS total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active'
    AND o.date > '2024-01-01'
GROUP BY u.id
       , u.name
       , u.email
ORDER BY total DESC
```

---

## Multi-statements et variables

### Formatage multi-statements

Si votre requete contient **plusieurs instructions** separees par `;`, chaque instruction est formatee individuellement avec un saut de ligne entre elles :

```sql
-- Avant
SELECT * FROM clients; SELECT COUNT(*) FROM commandes;

-- Apres
SELECT           *
FROM             clients;

SELECT           COUNT(*)
FROM             commandes;
```

### Commentaires en ligne

Les lignes commentees (commencant par `--`) sont preservees sur leur propre ligne. Utile pour desactiver temporairement une clause :

```sql
SELECT TOP 5     a.Contract_ID
               , a.Name          AS DisplayName
--INTO             #TempTable
FROM             contracts a
WHERE            a.Status = 'Active'
```

### Variables T-SQL

DataForge Studio gere les **variables T-SQL** (`DECLARE`, `SET @variable`) :

```sql
DECLARE @date_debut DATE = '2024-01-01';

SELECT           client_id
               , SUM(montant) AS total
FROM             commandes
WHERE            date_commande >= @date_debut
GROUP BY         client_id;
```

- Les variables sont **colorees** distinctement dans l'editeur (orange en theme sombre, bordeaux en theme clair)
- Lors de l'execution, si un `DECLARE` est detecte, tout le batch est envoye en une seule fois au serveur pour que les variables persistent entre les statements

---

## SELECT DISTINCT et SELECT TOP

Le formateur traite `DISTINCT` et `TOP N` comme faisant partie du mot-cle `SELECT`, pour garder l'alignement :

```sql
SELECT DISTINCT  ville
               , code_postal
FROM             clients
ORDER BY         ville

SELECT TOP 100   nom
               , prenom
               , email
FROM             clients
WHERE            statut = 'actif'
```

---

## Alias T-SQL avec =

Le formateur reconnait le style d'alias T-SQL `alias = expression` (en plus du standard `expression AS alias`) et aligne les signes `=` :

```sql
SELECT           s.session_id
               , blocked_by    = r.blocking_session_id
               , database_name = DB_NAME(r.database_id)
               , wait_type     = r.wait_type
               , status        = r.status
FROM             sys.dm_exec_sessions s
```

> **Important** : ne melangez pas les deux styles (`=` et `AS`) dans le meme SELECT. Le formateur affichera un avertissement si une telle combinaison est detectee.

---

## OUTER APPLY et CROSS APPLY

Les clauses T-SQL `OUTER APPLY` et `CROSS APPLY` sont reconnues et alignees comme des JOINs :

```sql
FROM             sys.dm_exec_sessions                   s
LEFT JOIN        sys.dm_exec_requests                   r        ON  r.session_id = s.session_id
OUTER APPLY      sys.dm_exec_sql_text(r.sql_handle)     t
OUTER APPLY      sys.dm_exec_input_buffer(s.session_id, NULL) ib
```

---

## CTE et CREATE VIEW

Les requetes avec des CTEs (`WITH ... AS`) sont formatees avec une indentation hierarchique :

- Si la requete commence par `CREATE OR ALTER VIEW ... AS`, tout le bloc est indente de 4 espaces
- Le mot-cle `WITH` est isole sur sa ligne
- Chaque CTE est indentee, son contenu (SELECT/FROM/WHERE) indente d'un cran supplementaire
- La requete principale est au meme niveau que le WITH

```sql
CREATE OR ALTER VIEW v_Locks AS
    WITH
        cte_blockers AS (
            SELECT           blocking_session_id
                           , COUNT(*) AS nb
            FROM             sys.dm_exec_requests
            WHERE            blocking_session_id > 0
            GROUP BY         blocking_session_id
        )
    SELECT           s.session_id
    FROM             sys.dm_exec_sessions s
```

---

## Editeur SQL : confort de saisie

L'editeur SQL integre deux fonctions de confort :

- **Auto-indent** : quand vous appuyez sur Entree, la nouvelle ligne reprend automatiquement l'indentation de la ligne precedente
- **Tab → espaces** : la touche Tab insere 4 espaces au lieu d'un caractere tabulation, evitant les problemes d'alignement

---

## Sauvegarder une requete

Pour retrouver une requete rapidement plus tard :

1. Redigez et testez votre requete dans l'editeur
2. Cliquez sur le bouton **Save Query** dans la barre d'outils
3. Remplissez le formulaire :

   | Champ | Exemple |
   |-------|---------|
   | **Project** | Client Alpha |
   | **Category** | Rapports mensuels |
   | **Name** | Ventes par region |
   | **Description** | Synthese des ventes par region pour le reporting mensuel |

4. Cliquez sur **Save**

La requete est stockee dans la base de configuration, organisee par projet et categorie.

![Dialogue de sauvegarde de requete avec les champs remplis](screenshots/06-save-query-dialog.png)

---

## Charger une requete sauvegardee

### Depuis le Database Manager

1. Cliquez sur le bouton **Load Saved Query** dans la barre d'outils
2. La liste de toutes les requetes sauvegardees s'affiche avec les colonnes : Project, Category, Name, Database, Description
3. **Double-cliquez** sur la requete souhaitee
4. Elle est chargee dans un nouvel onglet, prete a etre executee

### Depuis le Queries Manager

1. Ouvrez le **Queries Manager** via la barre laterale
2. Naviguez dans l'arbre : **Project > Category > Query**
3. Cliquez sur une requete pour voir ses details dans le panneau droit
4. **Double-cliquez** pour la charger dans le Database Manager

![Queries Manager avec l'arbre et le panneau de details](screenshots/06-queries-manager.png)

---

## Astuce

- Le style **Ultimate** est recommande pour un usage quotidien : il produit le SQL le plus lisible grace a l'alignement complet des mots-cles, alias et operateurs.
- Sauvegardez vos requetes **des qu'elles fonctionnent**. Une requete non sauvegardee est une requete perdue au prochain redemarrage.
- Organisez vos requetes avec des noms de projet et de categorie coherents. Par exemple : projet = nom du client, categorie = type de rapport ou frequence.
- Le style de formatage par defaut est configurable dans les preferences.

---

## Ce qui se passe en coulisse

- Le formateur utilise **sqlparse** comme moteur de base, puis applique un post-traitement avance via `_TopLevelScanner` (parsing des parentheses et chaines) et des fonctions specialisees par section (SELECT, FROM/JOIN, WHERE, GROUP BY, ORDER BY).
- Le formatage ne modifie jamais la logique SQL : seuls l'espacement, l'indentation et la casse des mots-cles changent. Les chaines de caracteres et les commentaires sont preserves.
- Les requetes sauvegardees sont stockees dans la table `saved_queries` de `_AppConfig/configuration.db`, liees a la connexion cible par `target_database_id`.
- La coloration syntaxique est un `QSyntaxHighlighter` PySide6 qui applique des regles regex pour les mots-cles, les chaines, les commentaires, les nombres et les variables.

---

[<< Travailler avec des fichiers](05-data-files.md) | [Suivant : Acceder a un serveur FTP >>](07-ftp-access.md)
