# Guide du Style Aligned (Keywords)

## ✅ Nouveau Style Disponible

L'application propose maintenant **4 styles de formatage SQL**, incluant le nouveau style **Aligned (Keywords)**.

---

## 🎨 Style 4 : Aligned (Keywords) - NOUVEAU

**Description** : Mots-clés alignés verticalement - Très structuré

**Idéal pour** :
- Requêtes avec beaucoup de JOINs
- Équipes préférant l'alignement visuel des keywords
- Code reviews nécessitant une structure claire
- Documentation technique professionnelle

### Exemple

**Avant formatage** (sur une seule ligne):
```sql
SELECT id, name, email, created_at, status FROM users a INNER JOIN ddfssf b ON a.id = b.id WHERE status='active' GROUP BY id, name
```

**Après formatage** (Aligned):
```sql
SELECT     id
         , name
         , email
         , created_at
         , status
FROM       users a
INNER JOIN ddfssf b
        ON a.id = b.id
WHERE      status = 'active'
GROUP BY   id
         , name
```

### Caractéristiques Principales

#### 1. Alignement des Mots-Clés
- ✅ Tous les mots-clés principaux sont alignés à gauche
- ✅ Largeur fixe de 10 caractères pour les keywords
- ✅ Le contenu commence toujours à la position 11

**Mots-clés alignés** :
- `SELECT     ` (6 + 5 espaces)
- `FROM       ` (4 + 7 espaces)
- `INNER JOIN ` (10 + 1 espace)
- `LEFT JOIN  ` (9 + 2 espaces)
- `WHERE      ` (5 + 6 espaces)
- `GROUP BY   ` (8 + 3 espaces)
- `HAVING     ` (6 + 5 espaces)
- `ORDER BY   ` (8 + 3 espaces)

#### 2. Style Comma-First pour les Colonnes
- ✅ Virgule au début de chaque ligne (sauf la première)
- ✅ Virgule positionnée à la colonne 9
- ✅ Facile de repérer les virgules manquantes
- ✅ Git diffs plus clairs

#### 3. Indentation des Clauses ON
- ✅ Clause ON sur ligne séparée
- ✅ Indentée sous le mot-clé JOIN
- ✅ Position 8 (2 espaces avant "ON")

---

## 📊 Exemple Complexe

**Requête originale** :
```sql
SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.total) as total FROM users u LEFT JOIN orders o ON u.id = o.user_id INNER JOIN profiles p ON u.id = p.user_id WHERE u.status='active' AND o.created_at > '2024-01-01' GROUP BY u.id, u.name, u.email HAVING COUNT(o.id) > 5 ORDER BY total DESC
```

**Formaté avec Aligned** :
```sql
SELECT     u.id
         , u.name
         , u.email
         , COUNT(o.id) AS order_count
         , SUM(o.total) AS total
FROM       users u
LEFT JOIN  orders o
        ON u.id = o.user_id
INNER JOIN profiles p
        ON u.id = p.user_id
WHERE      u.status = 'active'
    AND o.created_at > '2024-01-01'
GROUP BY   u.id
         , u.name
         , u.email
HAVING     COUNT(o.id) > 5
ORDER BY   total DESC
```

### Avantages Visibles

1. **Structure Claire** : Les keywords alignés créent une "colonne" visuelle
2. **JOINs Lisibles** : Chaque JOIN et sa clause ON sont clairement visibles
3. **Colonnes Faciles à Compter** : Virgules alignées facilitent le décompte
4. **Professionnel** : Aspect très soigné pour documentation

---

## 🚀 Comment Utiliser

### Dans l'Application

1. Lancer : `uv run python gui.py`
2. Aller dans **Database → Query Manager**
3. Taper ou coller une requête SQL
4. Sélectionner **"Aligned (Keywords)"** dans le menu **"Style:"**
5. Cliquer sur le bouton **"🎨 Format"**
6. La requête est formatée avec les keywords alignés !

### Interface

```
┌────────────────────────────────────────────────────────────────┐
│ ▶ Execute  💾 Save  Style: [Aligned (Keywords) ▼] 🎨 Format │
└────────────────────────────────────────────────────────────────┘
```

---

## 📋 Comparaison avec les Autres Styles

### Même Requête - 4 Styles Différents

**Requête** : `SELECT id, name, email FROM users WHERE status='active' ORDER BY name`

#### Style 1: Expanded (1 column/line)
```sql
SELECT id,
       name,
       email
FROM users
WHERE status = 'active'
ORDER BY name
```

#### Style 2: Compact
```sql
SELECT id, name, email
FROM users
WHERE status = 'active'
ORDER BY name
```

#### Style 3: Comma First
```sql
SELECT id
     , name
     , email
FROM users
WHERE status = 'active'
ORDER BY name
```

#### Style 4: Aligned (Keywords)
```sql
SELECT     id
         , name
         , email
FROM       users
WHERE      status = 'active'
ORDER BY   name
```

---

## 💡 Quand Utiliser le Style Aligned ?

### ✅ Recommandé Pour

1. **Requêtes avec Multiples JOINs**
   - Chaque JOIN et ON clause clairement visible
   - Structure hiérarchique évidente

2. **Documentation Technique**
   - Aspect professionnel et soigné
   - Facile à expliquer dans des slides ou README

3. **Code Reviews Exigeants**
   - Structure parfaitement alignée
   - Zéro ambiguïté sur les clauses

4. **Standards d'Équipe Stricts**
   - Cohérence visuelle totale
   - Alignement parfait de tous les keywords

### ❌ Moins Adapté Pour

1. **Requêtes Très Simples**
   - Style Compact plus adapté pour SELECT simple

2. **Logs/Scripts Automatisés**
   - Expanded ou Compact prennent moins de place

3. **Modifications Fréquentes**
   - Si vous ajoutez/retirez souvent des colonnes, Expanded peut être plus pratique

---

## ⚙️ Détails Techniques

### Implémentation

Le style Aligned est implémenté dans `sql_highlighter.py` :

1. **Fonction principale** : `_format_aligned_style(formatted_sql)`
   - Analyse les lignes formatées par sqlparse
   - Détecte les mots-clés principaux
   - Aligne chaque keyword à 10 caractères
   - Collecte les colonnes SELECT et GROUP BY
   - Output avec comma-first

2. **Fonction helper** : `_output_columns(result, keyword, columns, max_keyword_len)`
   - Première ligne : keyword + première colonne
   - Lignes suivantes : 9 espaces + ", " + colonne

3. **Gestion des JOINs** :
   - Détection si ON est sur même ligne que JOIN
   - Séparation automatique via regex case-insensitive
   - ON indenté à position 8 (max_keyword_len - 2)

### Code

```python
# Utiliser le style Aligned
from sql_highlighter import format_sql

formatted = format_sql(sql_text, style='aligned', keyword_case='upper')
```

### Paramètres sqlparse Utilisés

```python
formatted = sqlparse.format(
    sql_text,
    reindent=True,
    keyword_case='upper',
    indent_width=4,
    indent_tabs=False,
    use_space_around_operators=True
)
# Puis post-traitement pour alignement
formatted = _format_aligned_style(formatted)
```

---

## 🎯 Cas d'Usage Spécifique

### Cas 1 : Requête avec 5 JOINs

**Problème** : Requête complexe avec multiples JOINs illisible

**Solution** : Style Aligned rend chaque JOIN distinct

**Avant** :
```sql
SELECT u.id, u.name, o.total FROM users u JOIN orders o ON u.id=o.user_id JOIN order_items oi ON o.id=oi.order_id JOIN products p ON oi.product_id=p.id JOIN categories c ON p.category_id=c.id WHERE u.status='active'
```

**Après** :
```sql
SELECT     u.id
         , u.name
         , o.total
FROM       users u
JOIN       orders o
        ON u.id = o.user_id
JOIN       order_items oi
        ON o.id = oi.order_id
JOIN       products p
        ON oi.product_id = p.id
JOIN       categories c
        ON p.category_id = c.id
WHERE      u.status = 'active'
```

**Avantage** : Chaque JOIN est une "section" visuellement distincte

---

### Cas 2 : Présentation Technique

**Besoin** : Inclure requête SQL dans présentation PowerPoint

**Solution** : Style Aligned donne aspect professionnel

**Avantages** :
- Alignement parfait pour slides
- Structure claire même de loin
- Keywords en "colonne" facilement repérables

---

## 📊 Tableau Comparatif

| Caractéristique | Expanded | Compact | Comma First | **Aligned** |
|----------------|----------|---------|-------------|-------------|
| **Colonnes/ligne** | 1 | Multiple | 1 | 1 |
| **Virgules** | Fin | Fin | Début | **Début** |
| **Keywords** | Standard | Standard | Standard | **Alignés** |
| **Indentation** | 4 espaces | 2 espaces | 4 espaces | **Fixe (10 car)** |
| **Lisibilité** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | **⭐⭐⭐⭐⭐** |
| **Structure** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | **⭐⭐⭐⭐⭐** |
| **JOINs** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | **⭐⭐⭐⭐⭐** |
| **Compacité** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |

---

## 📝 Notes Importantes

### Coloration Syntaxique
- ✅ Fonctionne **automatiquement** avec le style Aligned
- ✅ Appliquée après formatage
- ✅ Keywords en bleu, strings en rouge, etc.

### Préservation du SQL
- ✅ La logique SQL reste **identique**
- ✅ Seuls l'espacement et l'indentation changent
- ✅ Pas de modification des noms de tables/colonnes
- ✅ Commentaires préservés

### Performance
- ✅ Formatage instantané même pour requêtes longues
- ✅ Post-traitement optimisé
- ✅ Pas d'impact sur l'exécution de la requête

---

## ✨ Résumé

**Question** : "est il possible d'avoir une mise en forme sur ce modele ?"

**Réponse** : ✅ **OUI, maintenant implémenté !**

Le style **"Aligned (Keywords)"** :
- ✅ Keywords parfaitement alignés verticalement
- ✅ Comma-first pour les colonnes
- ✅ ON clauses sur lignes séparées et indentées
- ✅ Structure professionnelle et très lisible
- ✅ **Disponible dès maintenant dans l'application**

**Total** : 4 styles de formatage SQL disponibles pour couvrir tous les besoins !

---

**Version** : 1.0
**Date** : 2025-12-07
**Développement** : Claude Code
**Status** : ✅ IMPLÉMENTÉ ET TESTÉ
