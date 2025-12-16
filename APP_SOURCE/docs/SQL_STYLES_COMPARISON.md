# Comparaison Visuelle des 4 Styles de Formatage SQL

## Requête de Test

**Requête originale** (une seule ligne, illisible) :
```sql
SELECT u.id, u.name, u.email, COUNT(o.id) as cnt, SUM(o.total) as sum FROM users u INNER JOIN orders o ON u.id = o.user_id LEFT JOIN profiles p ON u.id = p.user_id WHERE u.status='active' AND o.total > 100 GROUP BY u.id, u.name, u.email HAVING COUNT(o.id) > 5 ORDER BY sum DESC LIMIT 10
```

---

## Style 1 : Expanded (1 column/line)

**Avantages** : Maximum de lisibilité, une colonne par ligne
**Lignes** : 16 | **Caractères** : 338

```sql
SELECT u.id,
       u.name,
       u.email,
       COUNT(o.id) AS cnt,
       SUM(o.total) AS SUM
FROM users u
INNER JOIN orders o ON u.id = o.user_id
LEFT JOIN profiles p ON u.id = p.user_id
WHERE u.status = 'active'
    AND o.total > 100
GROUP BY u.id,
         u.name,
         u.email
HAVING COUNT(o.id) > 5
ORDER BY SUM DESC
LIMIT 10
```

---

## Style 2 : Compact

**Avantages** : Plus compact, économise l'espace vertical
**Lignes** : 10 | **Caractères** : 290

```sql
SELECT u.id, u.name, u.email, COUNT(o.id) AS cnt, SUM(o.total) AS SUM
FROM users u
INNER JOIN orders o ON u.id = o.user_id
LEFT JOIN profiles p ON u.id = p.user_id
WHERE u.status = 'active'
  AND o.total > 100
GROUP BY u.id, u.name, u.email
HAVING COUNT(o.id) > 5
ORDER BY SUM DESC
LIMIT 10
```

---

## Style 3 : Comma First

**Avantages** : Virgules au début, facile de repérer les manquantes
**Lignes** : 16 | **Caractères** : 332

```sql
SELECT u.id
     , u.name
     , u.email
     , COUNT(o.id) AS cnt
     , SUM(o.total) AS SUM
FROM users u
INNER JOIN orders o ON u.id = o.user_id
LEFT JOIN profiles p ON u.id = p.user_id
WHERE u.status = 'active'
    AND o.total > 100
GROUP BY u.id
       , u.name
       , u.email
HAVING COUNT(o.id) > 5
ORDER BY SUM DESC
LIMIT 10
```

---

## Style 4 : Aligned (Keywords) - NOUVEAU

**Avantages** : Keywords alignés, ON clauses séparées, très structuré
**Lignes** : 18 | **Caractères** : 397

```sql
SELECT     u.id
         , u.name
         , u.email
         , COUNT(o.id) AS cnt
         , SUM(o.total) AS SUM
FROM       users u
INNER JOIN orders o
        ON u.id = o.user_id
LEFT JOIN  profiles p
        ON u.id = p.user_id
WHERE      u.status = 'active'
    AND o.total > 100
GROUP BY   u.id
         , u.name
         , u.email
HAVING     COUNT(o.id) > 5
ORDER BY   SUM DESC
LIMIT      10
```

---

## Tableau Comparatif

| Critère | Expanded | Compact | Comma First | Aligned |
|---------|----------|---------|-------------|---------|
| **Lignes** | 16 | 10 | 16 | 18 |
| **Caractères** | 338 | 290 | 332 | 397 |
| **Colonnes/ligne** | 1 | Multiple | 1 | 1 |
| **Virgules** | Fin | Fin | Début | Début |
| **Keywords** | Standard | Standard | Standard | **Alignés** |
| **ON clause** | Même ligne | Même ligne | Même ligne | **Ligne séparée** |
| **Lisibilité** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Compacité** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Structure** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **JOINs** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Recommandations d'Utilisation

### 📋 Expanded (1 column/line)
**Utilisez pour :**
- Requêtes complexes avec beaucoup de colonnes
- Débogage et revues de code
- Documentation détaillée

**Évitez pour :**
- Requêtes simples (surcharge visuelle)
- Logs (trop de lignes)

---

### 📦 Compact
**Utilisez pour :**
- Requêtes simples (< 5 colonnes)
- Logs et scripts
- Économiser l'espace vertical

**Évitez pour :**
- Requêtes très complexes (difficile à lire)
- Code reviews (manque de clarté)

---

### 📝 Comma First
**Utilisez pour :**
- Équipes utilisant ce standard
- Détection d'erreurs de syntaxe
- Git diffs plus clairs

**Évitez pour :**
- Si l'équipe n'est pas habituée (peut surprendre)
- Présentation externe (moins conventionnel)

---

### 🎯 Aligned (Keywords) - NOUVEAU
**Utilisez pour :**
- **Requêtes avec multiples JOINs** (chaque JOIN bien visible)
- **Documentation technique professionnelle**
- **Présentations** (structure claire même de loin)
- **Standards d'équipe stricts** (alignement parfait)

**Évitez pour :**
- Requêtes très simples (surcharge visuelle)
- Logs (plus de lignes que Compact)

---

## Cas d'Usage Pratiques

### Cas 1 : Requête Reçue par Email (illisible)

**Problème** : Requête collée sur une ligne
**Solution** : Sélectionner **Expanded** ou **Aligned**, cliquer Format

**Avant** :
```sql
SELECT id, name, email FROM users WHERE status='active' ORDER BY name
```

**Après (Aligned)** :
```sql
SELECT     id
         , name
         , email
FROM       users
WHERE      status = 'active'
ORDER BY   name
```

---

### Cas 2 : Debug d'un JOIN Complexe

**Problème** : 5 JOINs, difficile de voir la structure
**Solution** : Style **Aligned** - chaque JOIN et ON clause visible

**Avant** :
```sql
SELECT u.name, o.total FROM users u JOIN orders o ON u.id=o.user_id JOIN items i ON o.id=i.order_id
```

**Après (Aligned)** :
```sql
SELECT     u.name
         , o.total
FROM       users u
JOIN       orders o
        ON u.id = o.user_id
JOIN       items i
        ON o.id = i.order_id
```

---

### Cas 3 : Logs de Requêtes

**Problème** : Besoin de logger sans prendre trop de place
**Solution** : Style **Compact**

**Avant** : 150 caractères sur 1 ligne
**Après** : 10 lignes courtes, faciles à grep

---

## Comment Utiliser

1. **Lancer l'application** : `uv run python gui.py`
2. **Ouvrir Query Manager** : Database → Query Manager
3. **Coller une requête SQL**
4. **Sélectionner un style** : Dropdown "Style:"
   - Expanded (1 column/line)
   - Compact
   - Comma First
   - **Aligned (Keywords)** ← NOUVEAU
5. **Cliquer sur "🎨 Format"**
6. **Profiter de la requête formatée** avec coloration syntaxique automatique !

---

## Résumé

✅ **4 styles de formatage SQL disponibles**
✅ **Chaque style adapté à un cas d'usage spécifique**
✅ **Nouveau style Aligned parfait pour JOINs complexes**
✅ **Coloration syntaxique automatique sur tous les styles**
✅ **Un clic pour formatter n'importe quelle requête**

**Flexibilité maximale pour tous les besoins !**

---

**Version** : 1.0
**Date** : 2025-12-07
**Status** : ✅ IMPLÉMENTÉ ET TESTÉ
