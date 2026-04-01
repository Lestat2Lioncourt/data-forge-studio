# 06 - Formater et sauvegarder des requetes

> **Situation** : Vous recevez une requete SQL sur une seule ligne dans un email, ou vous voulez sauvegarder vos requetes les plus utilisees pour les retrouver plus tard.

---

## Formater une requete SQL

### Les styles de formatage

DataForge Studio propose **4 styles de formatage** accessibles dans la barre d'outils de l'onglet de requete :

| Style | Description | Ideal pour |
|-------|-------------|------------|
| **Expanded** | Une colonne par ligne, indentation 4 espaces | Requetes complexes, revues de code |
| **Compact** | Plusieurs colonnes par ligne (limite 120 car.) | Requetes simples, logs |
| **Comma First** | Virgules en debut de ligne | Diff Git, detection d'erreurs |
| **Aligned** | Mots-cles et operateurs alignes | Documentation, presentation |

### Utiliser le formateur

1. Redigez ou collez votre requete dans l'editeur
2. Selectionnez le **style** souhaite dans le selecteur de la barre d'outils
3. Cliquez sur le bouton **Format**
4. La requete est reformatee instantanement avec la coloration syntaxique mise a jour

![Avant/apres formatage d'une requete complexe en style Expanded](screenshots/06-format-before-after.png)

### Exemple concret

**Avant** (requete brute recue par email) :

```sql
SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.total) as total FROM users u JOIN orders o ON u.id=o.user_id WHERE u.status='active' AND o.date > '2024-01-01' GROUP BY u.id, u.name, u.email ORDER BY total DESC
```

**Apres** (style Expanded) :

```sql
SELECT u.id,
       u.name,
       u.email,
       COUNT(o.id) AS order_count,
       SUM(o.total) AS total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active'
    AND o.date > '2024-01-01'
GROUP BY u.id,
         u.name,
         u.email
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

Si votre requete contient **plusieurs instructions** separees par `;`, chaque instruction est formatee individuellement :

```sql
-- Avant
SELECT * FROM clients; SELECT COUNT(*) FROM commandes;

-- Apres (chaque instruction formatee separement)
SELECT *
FROM clients;

SELECT COUNT(*)
FROM commandes;
```

### Variables T-SQL

DataForge Studio gere les **variables T-SQL** (`DECLARE`, `SET @variable`) :

```sql
DECLARE @date_debut DATE = '2024-01-01'
DECLARE @date_fin DATE = '2024-12-31'

SELECT client_id,
       SUM(montant) AS total
FROM commandes
WHERE date_commande BETWEEN @date_debut AND @date_fin
GROUP BY client_id
```

- Les variables sont **colorees** distinctement dans l'editeur (orange en theme sombre)
- Dans un meme batch (execution sans separateur), les variables declarees dans le premier statement sont accessibles dans les suivants

---

## SELECT DISTINCT et SELECT TOP

Le formateur reconnait et preserve correctement `DISTINCT` et `TOP N` :

```sql
-- DISTINCT est preserve avec le formatage
SELECT DISTINCT ville,
                code_postal
FROM clients
ORDER BY ville

-- TOP N est preserve aussi
SELECT TOP 100 nom,
               prenom,
               email
FROM clients
WHERE statut = 'actif'
```

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

## Edit Query depuis une grille de resultats

Si un resultat de requete contient une colonne SQL (par exemple une colonne nommee `query` ou `requete`) :

1. **Clic droit** sur la cellule contenant du SQL
2. Selectionnez **Edit Query**
3. Le SQL est automatiquement **formate** en style aligned
4. Un nouvel onglet s'ouvre avec la requete prete a etre executee

Les noms de colonnes declencheurs sont configurables dans les preferences (par defaut : `query`, `requete`). La detection est insensible a la casse.

---

## Astuce

- Choisissez un style de formatage et tenez-vous-y dans votre equipe. Le style **Expanded** est le plus lisible pour les revues de code. **Comma First** est le plus pratique pour les diffs Git.
- Sauvegardez vos requetes **des qu'elles fonctionnent**. Une requete non sauvegardee est une requete perdue au prochain redemarrage.
- Organisez vos requetes avec des noms de projet et de categorie coherents. Par exemple : projet = nom du client, categorie = type de rapport ou frequence.
- Le style de formatage par defaut est configurable dans **Options > Preferences > General > sql_format_style**.

---

## Ce qui se passe en coulisse

- Le formateur utilise **sqlparse** comme moteur de base, avec un post-traitement maison pour le style Expanded (fonction `_force_one_column_per_line`) et le style Aligned.
- Le formatage ne modifie jamais la logique SQL : seuls l'espacement, l'indentation et la casse des mots-cles changent. Les chaines de caracteres et les commentaires sont preserves.
- Les requetes sauvegardees sont stockees dans la table `saved_queries` de `_AppConfig/configuration.db`, liees a la connexion cible par `target_database_id`.
- La coloration syntaxique est un `QSyntaxHighlighter` PySide6 qui applique des regles regex pour les mots-cles, les chaines, les commentaires, les nombres et les variables.

---

[<< Travailler avec des fichiers](05-data-files.md) | [Suivant : Acceder a un serveur FTP >>](07-ftp-access.md)
