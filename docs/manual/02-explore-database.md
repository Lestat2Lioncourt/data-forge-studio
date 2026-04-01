# 02 - Explorer une base de donnees inconnue

> **Situation** : On vous donne acces a une base de donnees que vous ne connaissez pas. Vous devez comprendre sa structure, identifier les tables importantes et analyser la distribution des donnees.

---

## Se connecter a la base

1. Ouvrez le **Database Manager** (barre laterale gauche)
2. Cliquez sur **+ New Connection** dans la barre d'outils
3. Configurez la connexion :

   | Champ | Exemple SQL Server | Exemple PostgreSQL |
   |-------|--------------------|--------------------|
   | Nom | Prod - Analytics | Staging - DWH |
   | Type | SQL Server | PostgreSQL |
   | Connection string | `Driver={ODBC Driver 18 for SQL Server};Server=srv01;Database=Analytics;Trusted_Connection=yes` | `postgresql://srv01:5432/dwh` |

4. **Test Connection** pour valider (timeout de 5 secondes)
5. **Save** -- le schema se charge automatiquement

![Arbre du schema avec tables et vues deplies](screenshots/02-schema-tree-expanded.png)

---

## Naviguer dans le schema

Une fois connecte, l'arbre de gauche affiche la hierarchie :

```
Connexion (ex: Prod - Analytics)
  Tables
    clients
      id (int)
      nom (varchar)
      ville (varchar)
    commandes
      id (int)
      client_id (int)
      montant (decimal)
  Views
    v_clients_actifs
    v_ventes_mensuelles
```

- **Depliez une table** pour voir ses colonnes avec leurs types
- **Depliez "Views"** pour voir les vues disponibles
- Pour rafraichir le schema apres des modifications : **clic droit sur la connexion > Refresh Schema**

---

## Decouvrir le contenu des tables

### Methode rapide : clic droit

1. **Clic droit sur une table** dans l'arbre
2. Choisissez **COUNT(\*) rows** pour connaitre le volume
3. Puis **SELECT Top 1000 rows** pour voir un echantillon

Le resultat s'affiche dans la grille. Les colonnes sont triables (clic sur l'en-tete) et supportent le **tri multi-colonnes** avec **Ctrl+Clic**.

### Methode detaillee : ecrire une requete

Tapez directement dans l'editeur SQL :

```sql
-- Comprendre la distribution des villes
SELECT ville,
       COUNT(*) AS nb_clients
FROM clients
GROUP BY ville
ORDER BY nb_clients DESC
```

Puis **F5** pour executer.

![Grille de resultats avec tri actif sur une colonne](screenshots/02-results-grid-sorted.png)

---

## Analyser la distribution des donnees

Voici une demarche type pour comprendre une table inconnue :

### Etape 1 -- Volume et structure

```sql
-- Nombre de lignes
SELECT COUNT(*) AS total FROM ma_table

-- Apercu des donnees
SELECT TOP 100 * FROM ma_table
```

### Etape 2 -- Valeurs distinctes par colonne

```sql
-- Combien de valeurs differentes ?
SELECT COUNT(DISTINCT ville) AS nb_villes,
       COUNT(DISTINCT statut) AS nb_statuts
FROM clients
```

Le formateur SQL de DataForge Studio gere `SELECT DISTINCT` et `SELECT TOP N` correctement lors du formatage.

### Etape 3 -- Distribution detaillee

```sql
SELECT statut,
       COUNT(*) AS nb,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM clients
GROUP BY statut
ORDER BY nb DESC
```

---

## Travailler avec plusieurs connexions

Vous pouvez ouvrir **plusieurs onglets de requete** en parallele, chacun connecte a une base differente :

1. Cliquez sur le **+** a cote des onglets pour creer un nouvel onglet
2. Selectionnez la base de donnees cible dans le selecteur de connexion de l'onglet
3. Redigez et executez votre requete

Chaque onglet conserve son propre editeur SQL, sa connexion et ses resultats. Les onglets sont **renommables** par double-clic sur leur titre.

---

## Exporter les resultats

Une fois les resultats affiches dans la grille :

1. **Clic droit** sur la grille de resultats
2. Choisissez le format d'export : **CSV**, **Excel** ou **JSON**
3. Selectionnez le dossier de destination

L'export tient compte des filtres et du tri actuellement appliques.

---

## Astuce

- Utilisez **COUNT(\*)** en premier sur les grosses tables pour eviter de lancer un `SELECT *` sur des millions de lignes.
- La syntaxe SQL s'adapte automatiquement au type de base. Vous pouvez ecrire `TOP 1000` pour SQL Server et `LIMIT 1000` pour PostgreSQL -- mais le menu contextuel gere cette adaptation pour vous.
- Si le schema semble incomplet, pensez a faire **clic droit > Refresh Schema** sur la connexion.

---

## Ce qui se passe en coulisse

- Le schema est recupere via les vues systeme de chaque moteur (INFORMATION_SCHEMA pour SQL Server/PostgreSQL, sqlite_master pour SQLite, etc.).
- Les connexions SQL Server passent par **pyodbc** et le driver ODBC 17 ou 18. PostgreSQL, MySQL et Oracle passent par **SQLAlchemy**.
- SQLite utilise le module natif Python `sqlite3`, sans driver ODBC necessaire.
- Les identifiants SQL (noms de tables, schemas) sont **sanitises** automatiquement pour eviter les injections SQL dans les requetes generees par le menu contextuel.

---

[<< Demarrage rapide](01-quick-start.md) | [Suivant : Travailler sur plusieurs projets >>](03-multi-projects.md)
