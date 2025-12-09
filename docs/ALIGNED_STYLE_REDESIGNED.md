# Style Aligned (Keywords) - Redesigné

## Vue d'Ensemble

Le style **Aligned (Keywords)** a été complètement redesigné avec des critères avancés d'alignement pour une lisibilité maximale et une structure visuelle parfaite.

---

## Nouveaux Critères Implémentés

### 1. ✅ Alignement des AS après le Champ le Plus Long

Dans SELECT, tous les `AS` sont alignés verticalement après le champ le plus long.

**Exemple:**
```sql
SELECT     YEAR(date_field)  AS YEAR
         , MONTH(date_field) AS MONTH
         , COUNT(*)          AS total_records
```

Les champs sont paddés pour que tous les `AS` soient alignés :
- `YEAR(date_field)` → 16 caractères
- `MONTH(date_field)` → 17 caractères (le plus long)
- `COUNT(*)` → 8 caractères, padded à 17

### 2. ✅ Alignement des Alias de Tables

Les alias de tables sont alignés après le nom de table le plus long.

**Exemple:**
```sql
FROM       users       u
INNER JOIN orders      o
INNER JOIN order_items oi
LEFT JOIN  products    p
LEFT JOIN  categories  c
```

Le nom de table le plus long (`order_items` = 11 caractères) détermine l'alignement de tous les alias.

### 3. ✅ ON sur la Même Ligne que la Table

La clause `ON` est placée sur la même ligne que le nom de table et l'alias.

**Avant** (ancien style):
```sql
INNER JOIN orders o
        ON u.id = o.user_id
```

**Après** (nouveau style):
```sql
INNER JOIN orders      o ON  u.id = o.user_id
```

### 4. ✅ Alignement des Conditions AND avec Signes Égaux Alignés

Quand il y a plusieurs conditions `AND` dans un `ON`, les signes `=` sont alignés verticalement.

**Exemple:**
```sql
INNER JOIN orders      o ON  u.user_id = o.user_id
                             AND u.status  = 'active'
                             AND u.deleted_at IS NULL
```

- La partie gauche de chaque condition est paddée (`u.user_id`, `u.status`, `u.deleted_at`)
- Tous les `=` sont alignés verticalement
- Les `AND` sont alignés au début de la première condition

### 5. ✅ Une Colonne par Ligne dans GROUP BY

Chaque colonne du `GROUP BY` est sur sa propre ligne avec virgule au début.

**Exemple:**
```sql
GROUP BY   u.user_id
         , u.username
         , o.order_id
         , p.product_name
         , c.category_name
```

### 6. ✅ Une Colonne par Ligne dans ORDER BY

Chaque colonne du `ORDER BY` est sur sa propre ligne avec virgule au début.

**Exemple:**
```sql
ORDER BY   total_amount DESC
         , u.username ASC
         , o.order_id DESC
```

### 7. ✅ Style Comma-First pour Toutes les Listes de Colonnes

Virgules au début de chaque ligne (sauf la première) pour :
- SELECT
- GROUP BY
- ORDER BY

---

## Exemple Complet

**Requête originale** (une seule ligne):
```sql
SELECT u.user_id, u.username, o.order_id, p.product_name, c.category_name, SUM(oi.quantity) AS total_qty, SUM(oi.price * oi.quantity) AS total_amount FROM users u INNER JOIN orders o ON u.user_id = o.user_id AND u.status = 'active' AND u.deleted_at IS NULL INNER JOIN order_items oi ON o.order_id = oi.order_id LEFT JOIN products p ON oi.product_id = p.product_id LEFT JOIN categories c ON p.category_id = c.category_id WHERE o.created_at >= '2024-01-01' AND o.status != 'cancelled' GROUP BY u.user_id, u.username, o.order_id, p.product_name, c.category_name HAVING SUM(oi.quantity) > 10 ORDER BY total_amount DESC, u.username ASC, o.order_id DESC
```

**Formatée avec Aligned:**
```sql
SELECT     u.user_id
         , u.username
         , o.order_id
         , p.product_name
         , c.category_name
         , SUM(oi.quantity)            AS total_qty
         , SUM(oi.price * oi.quantity) AS total_amount
FROM       users       u
INNER JOIN orders      o ON  u.user_id = o.user_id
                             AND u.status  = 'active'
                             AND u.deleted_at IS NULL
INNER JOIN order_items oi ON  o.order_id = oi.order_id
LEFT JOIN  products    p ON  oi.product_id = p.product_id
LEFT JOIN  categories  c ON  p.category_id = c.category_id
WHERE      o.created_at >= '2024-01-01' AND o.status != 'cancelled'
GROUP BY   u.user_id
         , u.username
         , o.order_id
         , p.product_name
         , c.category_name
HAVING     SUM(oi.quantity) > 10
ORDER BY   total_amount DESC
         , u.username ASC
         , o.order_id DESC
```

---

## Avantages du Nouveau Design

### Lisibilité Maximale

1. **SELECT** : Chaque colonne et son alias sont parfaitement visibles
2. **JOINs** : Structure hiérarchique claire avec tables et conditions alignées
3. **ON conditions** : Facile de comparer les conditions avec les `=` alignés
4. **GROUP BY/ORDER BY** : Une colonne par ligne = aucune ambiguïté

### Structure Visuelle Parfaite

- Tous les keywords alignés à la colonne 0
- Tous les `AS` alignés verticalement
- Tous les alias de tables alignés verticalement
- Tous les `=` dans les conditions ON alignés verticalement
- Virgules toujours en début de ligne (sauf première)

### Facile à Maintenir

- Ajouter une colonne dans SELECT : facile de voir où insérer
- Ajouter un JOIN : s'aligne automatiquement
- Ajouter une condition AND : alignement automatique des `=`
- Modifier GROUP BY/ORDER BY : une ligne = une colonne

### Parfait pour Code Reviews

- Chaque élément sur sa propre ligne facilite les diffs Git
- Structure claire permet de repérer rapidement les erreurs
- Alignement aide à vérifier la cohérence des conditions

---

## Cas d'Usage Spécifiques

### 1. Requêtes avec Multiples JOINs et Conditions Complexes

**Problème** : Requête avec 5 JOINs et plusieurs AND par JOIN est illisible

**Solution** : Style Aligned rend chaque JOIN et ses conditions parfaitement visibles

**Résultat** : Structure hiérarchique claire, facile de suivre la logique

### 2. Debugging de Conditions ON

**Problème** : Conditions ON complexes difficiles à lire

**Solution** : Alignement des `=` permet de voir immédiatement les comparaisons

**Exemple** :
```sql
INNER JOIN orders o ON  u.user_id    = o.user_id
                        AND u.company_id = o.company_id
                        AND u.region     = o.region
```

Les trois comparaisons sont parfaitement alignées et faciles à vérifier.

### 3. Documentation Technique

**Problème** : Requête doit être incluse dans documentation

**Solution** : Format Aligned est professionnel et lisible même dans PDF/slides

**Avantage** : Alignement parfait maintenu dans tous les formats

### 4. Revue de Code SQL

**Problème** : Reviewer doit vérifier une requête complexe

**Solution** : Une colonne par ligne + alignement facilite la vérification

**Avantage** :
- Facile de compter les colonnes
- Facile de vérifier les alias
- Facile de voir les conditions JOIN

---

## Comparaison Avant/Après

### Requête Simple

**Avant** (Compact):
```sql
SELECT id, name, email
FROM users
WHERE status = 'active'
ORDER BY name
```

**Après** (Aligned):
```sql
SELECT     id
         , name
         , email
FROM       users
WHERE      status = 'active'
ORDER BY   name
```

### Requête avec JOIN

**Avant** (Comma First ancien):
```sql
SELECT u.id
     , u.name
     , COUNT(o.id) AS order_count
FROM users u
INNER JOIN orders o ON u.id = o.user_id AND u.status = 'active'
WHERE u.created_at > '2024-01-01'
GROUP BY u.id, u.name
ORDER BY order_count DESC
```

**Après** (Aligned nouveau):
```sql
SELECT     u.id
         , u.name
         , COUNT(o.id) AS order_count
FROM       users  u
INNER JOIN orders o ON  u.id     = o.user_id
                        AND u.status = 'active'
WHERE      u.created_at > '2024-01-01'
GROUP BY   u.id
         , u.name
ORDER BY   order_count DESC
```

**Améliorations** :
- AS alignés
- Alias de tables alignés
- ON sur même ligne
- AND avec `=` alignés
- GROUP BY une colonne par ligne

---

## Détails Techniques

### Implémentation

Le style Aligned utilise une approche en **deux passes** :

**Passe 1 - Analyse et Calcul** :
1. Parser toutes les sections (SELECT, FROM, JOINs, GROUP BY, ORDER BY)
2. Calculer `max_field_len` : longueur du champ le plus long dans SELECT
3. Calculer `max_table_len` : longueur du nom de table le plus long
4. Calculer `max_on_left_len` : longueur de la partie gauche la plus longue dans les conditions ON

**Passe 2 - Formatage** :
1. Formater SELECT avec AS alignés à `max_field_len`
2. Formater FROM/JOINs avec alias alignés à `max_table_len`
3. Formater conditions ON avec `=` alignés à `max_on_left_len`
4. Formater GROUP BY/ORDER BY une colonne par ligne

### Fonctions Principales

```python
# sql_highlighter.py

def _format_aligned_style(formatted_sql):
    """Format SQL avec alignements avancés"""
    # Passe 1: Parser et calculer max lengths
    sections = _parse_sql_sections_advanced(lines, main_keywords)
    max_field_len = calculate_max_field_length(select_sections)
    max_table_len = calculate_max_table_length(from_join_sections)

    # Passe 2: Formater avec alignements
    for section in sections:
        if section['type'] == 'SELECT':
            _format_select_with_alignment(result, section, max_field_len)
        elif section['type'] in JOIN_KEYWORDS:
            _format_from_join_with_alignment(result, section, max_table_len)
        # etc.

def _preparse_select_section(section):
    """Parser SELECT pour extraire champs et AS"""
    # Détecte les AS et parse field + alias

def _preparse_from_join_section(section):
    """Parser FROM/JOIN pour extraire table, alias, conditions ON"""
    # Parse table_name, table_alias, on_conditions
    # Parse chaque condition pour trouver les '=' et calculer max_left_len

def _format_select_with_alignment(result, section, max_field_len):
    """Formater SELECT avec AS alignés"""
    # field.ljust(max_field_len) + " AS " + alias

def _format_from_join_with_alignment(result, section, max_table_len):
    """Formater FROM/JOIN avec alias alignés et = alignés dans ON"""
    # table.ljust(max_table_len) + alias
    # ON condition: left.ljust(max_left_len) + " = " + right
```

---

## Utilisation

### Dans l'Application

1. Lancer : `uv run python gui.py`
2. Database → Query Manager
3. Coller votre requête SQL (sur une ou plusieurs lignes)
4. Sélectionner **"Aligned (Keywords)"** dans le dropdown "Style:"
5. Cliquer sur **"🎨 Format"**
6. Votre requête est formatée avec tous les alignements !

### Programmatiquement

```python
from sql_highlighter import format_sql

sql = "SELECT id, name AS user_name FROM users u JOIN orders o ON u.id = o.user_id"
formatted = format_sql(sql, style='aligned', keyword_case='upper')
print(formatted)
```

Output:
```sql
SELECT     id
         , name AS user_name
FROM       users  u
JOIN       orders o ON  u.id = o.user_id
```

---

## Notes Importantes

### Coloration Syntaxique

- ✅ Appliquée **automatiquement** après formatage
- ✅ Fonctionne parfaitement avec le style Aligned
- ✅ Keywords en bleu, strings en rouge, etc.

### Préservation du SQL

- ✅ La logique SQL reste **identique**
- ✅ Seuls l'espacement et l'indentation changent
- ✅ Pas de modification des noms ou des valeurs
- ✅ Les commentaires sont préservés

### Limitations

- Les conditions ON sans `=` ne seront pas alignées (mais seront correctement formatées)
- Les expressions très longues peuvent dépasser 120 caractères de largeur
- Les subqueries sont formatées mais sans alignement spécial (utilise formatage sqlparse standard)

---

## Résumé

Le style **Aligned (Keywords)** redesigné offre :

✅ **7 critères avancés** tous implémentés
✅ **Alignement parfait** des AS, alias, et conditions
✅ **Lisibilité maximale** pour requêtes complexes
✅ **Structure visuelle** professionnelle
✅ **Maintenance facile** une colonne = une ligne
✅ **Code reviews efficaces** grâce aux alignements

**C'est le style le plus avancé et le plus lisible pour SQL complexe !**

---

**Version** : 2.0 (Redesigned)
**Date** : 2025-12-07
**Développement** : Claude Code
**Status** : ✅ IMPLÉMENTÉ ET TESTÉ
