# Guide des Styles de Formatage SQL

## ✅ Styles Disponibles

L'application propose maintenant **3 styles de formatage SQL configurables** :

---

## 🎨 Style 1 : Expanded (1 column/line) - PAR DÉFAUT

**Description** : Une colonne par ligne - Maximum de lisibilité

**Idéal pour** :
- Requêtes complexes avec beaucoup de colonnes
- Revues de code
- Documentation
- Débogage

### Exemple

**Avant formatage** (sur une seule ligne):
```sql
SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.total) as total FROM users u JOIN orders o ON u.id=o.user_id WHERE u.status='active' GROUP BY u.id, u.name, u.email ORDER BY total DESC
```

**Après formatage** (Expanded):
```sql
SELECT u.id,
       u.name,
       u.email,
       COUNT(o.id) AS order_count,
       SUM(o.total) AS total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active'
GROUP BY u.id,
         u.name,
         u.email
ORDER BY total DESC
```

### Caractéristiques
- ✅ **Une colonne par ligne** dans SELECT
- ✅ **Une colonne par ligne** dans GROUP BY
- ✅ Indentation de 4 espaces
- ✅ Mots-clés en MAJUSCULES
- ✅ Espaces autour des opérateurs

---

## 📦 Style 2 : Compact

**Description** : Plusieurs colonnes sur la même ligne - Plus compact

**Idéal pour** :
- Requêtes simples
- Économiser de l'espace vertical
- Impression
- Logs

### Exemple

**Même requête** formatée en Compact:
```sql
SELECT u.id, u.name, u.email, COUNT(o.id) AS order_count, SUM(o.total) AS total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active'
GROUP BY u.id, u.name, u.email
ORDER BY total DESC
```

### Caractéristiques
- ✅ Plusieurs colonnes par ligne (si elles tiennent)
- ✅ Indentation de 2 espaces (plus compact)
- ✅ Limite de ligne à 120 caractères
- ✅ Mots-clés en MAJUSCULES

---

## 📋 Style 3 : Comma First

**Description** : Virgules au début de chaque ligne - Facile de repérer les virgules manquantes

**Idéal pour** :
- Équipes qui utilisent ce standard
- Détection facile d'erreurs de syntaxe
- Diff Git plus clair

### Exemple

**Même requête** formatée en Comma First:
```sql
SELECT u.id
     , u.name
     , u.email
     , COUNT(o.id) AS order_count
     , SUM(o.total) AS total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active'
GROUP BY u.id
       , u.name
       , u.email
ORDER BY total DESC
```

### Caractéristiques
- ✅ Virgules **au début** de ligne
- ✅ Facile de voir si une virgule manque
- ✅ Indentation de 4 espaces
- ✅ Une colonne par ligne
- ✅ Mots-clés en MAJUSCULES

---

## 🚀 Comment Utiliser

### Dans l'Application

1. Lancer : `uv run python gui.py`
2. Aller dans **Database → Query Manager**
3. Taper ou coller une requête SQL
4. Sélectionner le style dans le menu **"Style:"**
   - Expanded (1 column/line)
   - Compact
   - Comma First
5. Cliquer sur le bouton **"🎨 Format"**
6. La requête est formatée avec le style choisi !

### Interface

```
┌───────────────────────────────────────────────────────────────┐
│ ▶ Execute  💾 Save  Style: [Expanded (1 column/line) ▼] 🎨 Format │
└───────────────────────────────────────────────────────────────┘
```

---

## 📊 Comparaison des Styles

| Caractéristique | Expanded | Compact | Comma First |
|----------------|----------|---------|-------------|
| **Colonnes/ligne** | 1 | Multiple | 1 |
| **Virgules** | Fin de ligne | Fin de ligne | Début de ligne |
| **Indentation** | 4 espaces | 2 espaces | 4 espaces |
| **Lisibilité** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Compacité** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Détection erreurs** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 💡 Recommandations

### Pour des Requêtes Simples (< 5 colonnes)

✅ **Compact** - Économise de l'espace
```sql
SELECT id, name, email
FROM users
WHERE status = 'active'
```

### Pour des Requêtes Complexes (> 5 colonnes)

✅ **Expanded** - Maximum de lisibilité
```sql
SELECT u.id,
       u.name,
       u.email,
       u.created_at,
       u.status,
       u.phone,
       u.address,
       COUNT(o.id) AS order_count
FROM users u
```

### Pour Débogage ou Revues de Code

✅ **Expanded** ou **Comma First**
- Chaque colonne clairement visible
- Erreurs faciles à repérer

---

## 🎯 Cas d'Usage Spécifiques

### Cas 1 : Requête Collée d'un Email

**Problème** : Requête sur une seule ligne, illisible

```sql
SELECT u.id, u.name, u.email, u.created_at, o.order_id, o.total, o.created_at FROM users u INNER JOIN orders o ON u.id = o.user_id WHERE u.status='active' AND o.total > 100 ORDER BY o.created_at DESC
```

**Solution** : Sélectionner "Expanded", cliquer "Format"

**Résultat** :
```sql
SELECT u.id,
       u.name,
       u.email,
       u.created_at,
       o.order_id,
       o.total,
       o.created_at
FROM users u
INNER JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active'
    AND o.total > 100
ORDER BY o.created_at DESC
```

---

### Cas 2 : Requête pour Documentation

**Besoin** : Documenter une requête dans un README

**Solution** : Utiliser "Expanded" pour maximum de lisibilité

**Avantage** :
- Chaque colonne visible
- Facile à expliquer
- Professionnell

---

### Cas 3 : Requête pour Logs

**Besoin** : Logger une requête dans des fichiers

**Solution** : Utiliser "Compact" pour économiser l'espace

**Avantage** :
- Moins de lignes dans les logs
- Toujours lisible
- Recherche plus facile

---

## ⚙️ Détails Techniques

### Implémentation

- **Bibliothèque** : `sqlparse`
- **Post-traitement** : Fonction custom `_force_one_column_per_line()` pour style Expanded
- **Paramètres configurables** :
  - `reindent` : Active l'indentation
  - `keyword_case` : UPPER/lower/Capitalize
  - `indent_width` : Nombre d'espaces
  - `comma_first` : Virgules au début/fin
  - `wrap_after` : Limite de caractères par ligne

### Code

```python
# Style Expanded
formatted = format_sql(sql_text, style='expanded', keyword_case='upper')

# Style Compact
formatted = format_sql(sql_text, style='compact', keyword_case='upper')

# Style Comma First
formatted = format_sql(sql_text, style='comma_first', keyword_case='upper')
```

---

## 🔧 Configuration Avancée

### Changer le Style par Défaut

Le style par défaut est **Expanded**. Pour le changer, modifier dans `database_manager.py` :

```python
self.format_style_var = tk.StringVar(value=style_names[0])  # Expanded
# Changer en:
self.format_style_var = tk.StringVar(value=style_names[1])  # Compact
```

### Ajouter un Nouveau Style

1. Ajouter dans `sql_highlighter.py` :
```python
SQL_FORMAT_STYLES = {
    # ... existing styles ...
    'custom': {
        'name': 'My Custom Style',
        'description': 'Description of custom style'
    }
}
```

2. Ajouter le code de formatage :
```python
elif style == 'custom':
    formatted = sqlparse.format(
        sql_text,
        # ... custom parameters ...
    )
```

---

## 📝 Notes

### Coloration Syntaxique

La coloration syntaxique est **indépendante** du formatage :
- ✅ Appliquée **automatiquement** après formatage
- ✅ Fonctionne avec tous les styles
- ✅ Pas d'action utilisateur requise

### Préservation du SQL

- ✅ Le formatage ne change **pas** la logique SQL
- ✅ Seuls l'espacement et l'indentation changent
- ✅ Les commentaires sont préservés
- ✅ Les chaînes de caractères restent identiques

---

## ✨ Avantages des Styles Configurables

### Flexibilité

✅ Adapter le formatage selon le contexte
✅ Chaque utilisateur peut choisir sa préférence
✅ Différents styles pour différents cas d'usage

### Productivité

✅ Un clic pour formatter
✅ Cohérence visuelle
✅ Moins d'erreurs de syntaxe

### Collaboration

✅ Standardisation d'équipe possible
✅ Code reviews plus faciles
✅ Documentation cohérente

---

## 🎉 Résumé

**Question initiale** : "Peut-on configurer le mode de fonctionnement pour n'avoir par exemple qu'une colonne par ligne ?"

**Réponse** : ✅ **OUI !**

Le style **"Expanded (1 column/line)"** fait exactement cela :
- ✅ Une colonne par ligne dans SELECT
- ✅ Une colonne par ligne dans GROUP BY
- ✅ Maximum de lisibilité
- ✅ **Activé par défaut**

**Bonus** : 2 autres styles disponibles (Compact et Comma First) pour différents cas d'usage !

---

**Version** : 1.0
**Date** : 2025-12-07
**Développement** : Claude Code
**Status** : ✅ IMPLÉMENTÉ ET TESTÉ
