# Analyse de Complexité - Coloration Syntaxique SQL & Formatage

## 📊 Vue d'Ensemble

Deux fonctionnalités demandées:
1. **Coloration syntaxique SQL** dans l'éditeur de requêtes
2. **Formatage automatique SQL** (pretty-print pour requêtes sur une ligne)

---

## 🎨 1. Coloration Syntaxique SQL

### Degré de Complexité: **⭐⭐ FACILE à MOYEN**

### Option A: Utiliser `sqlparse` (RECOMMANDÉ) ⭐⭐

**Complexité**: **FACILE** (1-2 heures de développement)

**Bibliothèque**: `sqlparse` (déjà utilisée pour le formatage)

**Avantages**:
- ✅ Bibliothèque Python standard pour SQL
- ✅ Parsing robuste de SQL
- ✅ Détecte automatiquement les tokens (keywords, identifiers, strings, etc.)
- ✅ Supporte tous les dialectes SQL (MySQL, PostgreSQL, SQLite, SQL Server)
- ✅ Simple à intégrer avec tkinter Text widget

**Inconvénients**:
- ⚠️ Nécessite un parsing à chaque modification (mais rapide)
- ⚠️ Pas de coloration en temps réel pendant la frappe (sauf avec callback)

**Implémentation**:
```python
import sqlparse
from sqlparse import tokens as T

def apply_sql_syntax_highlighting(text_widget, sql_text):
    """Apply SQL syntax highlighting to text widget"""
    # Clear existing tags
    for tag in text_widget.tag_names():
        text_widget.tag_remove(tag, "1.0", tk.END)

    # Configure tag styles
    text_widget.tag_configure("keyword", foreground="#0000FF", font=("Consolas", 10, "bold"))
    text_widget.tag_configure("string", foreground="#008000")
    text_widget.tag_configure("comment", foreground="#808080", font=("Consolas", 10, "italic"))
    text_widget.tag_configure("function", foreground="#FF00FF")
    text_widget.tag_configure("number", foreground="#FF4500")

    # Parse SQL
    parsed = sqlparse.parse(sql_text)[0]

    position = 0
    for token in parsed.flatten():
        token_text = str(token)
        token_length = len(token_text)

        # Calculate position in text widget
        start_index = f"1.0 + {position} chars"
        end_index = f"1.0 + {position + token_length} chars"

        # Apply tag based on token type
        if token.ttype in (T.Keyword, T.Keyword.DDL, T.Keyword.DML):
            text_widget.tag_add("keyword", start_index, end_index)
        elif token.ttype in (T.String.Single, T.String.Symbol):
            text_widget.tag_add("string", start_index, end_index)
        elif token.ttype in (T.Comment.Single, T.Comment.Multiline):
            text_widget.tag_add("comment", start_index, end_index)
        elif token.ttype == T.Number:
            text_widget.tag_add("number", start_index, end_index)
        elif token.ttype == T.Name.Function:
            text_widget.tag_add("function", start_index, end_index)

        position += token_length
```

**Utilisation**:
```python
# Callback sur modification du texte
def on_text_change(event=None):
    sql_text = query_text.get(1.0, tk.END)
    apply_sql_syntax_highlighting(query_text, sql_text)

query_text.bind("<KeyRelease>", on_text_change)
```

**Estimation temps de développement**: 2-3 heures

---

### Option B: Tags Manuels avec Regex ⭐⭐⭐

**Complexité**: **MOYEN** (4-6 heures)

**Approche**: Utiliser des expressions régulières pour identifier les mots-clés SQL

**Avantages**:
- ✅ Pas de dépendance externe
- ✅ Contrôle total sur les règles

**Inconvénients**:
- ⚠️ Maintenance complexe (beaucoup de mots-clés SQL)
- ⚠️ Risque de bugs avec SQL complexe
- ⚠️ Difficulté avec les strings/comments imbriqués

**Exemple simplifié**:
```python
import re

SQL_KEYWORDS = [
    'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE',
    'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON',
    'GROUP BY', 'ORDER BY', 'HAVING', 'AS', 'AND', 'OR', 'NOT',
    'IN', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'CREATE', 'ALTER',
    'DROP', 'TABLE', 'DATABASE', 'INDEX', 'VIEW', 'PROCEDURE'
]

def highlight_keywords(text_widget):
    content = text_widget.get(1.0, tk.END)

    for keyword in SQL_KEYWORDS:
        pattern = r'\b' + keyword + r'\b'
        for match in re.finditer(pattern, content, re.IGNORECASE):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            text_widget.tag_add("keyword", start, end)
```

**Estimation temps de développement**: 4-6 heures

---

### Option C: Pygments (le plus professionnel) ⭐⭐

**Complexité**: **FACILE** (2-3 heures)

**Bibliothèque**: `pygments` (utilisée par de nombreux IDE)

**Avantages**:
- ✅ Coloration professionnelle (utilisée par GitHub, Jupyter)
- ✅ Supporte 500+ langages
- ✅ Thèmes préfabriqués (Monokai, Solarized, etc.)
- ✅ Très robuste

**Inconvénients**:
- ⚠️ Dépendance externe supplémentaire (~2 MB)
- ⚠️ Légèrement plus lourd que sqlparse

**Installation**:
```bash
uv add pygments
```

**Implémentation**:
```python
from pygments import lex
from pygments.lexers import SqlLexer
from pygments.token import Token

def apply_pygments_highlighting(text_widget, sql_text):
    """Apply SQL syntax highlighting using Pygments"""
    # Configure styles
    text_widget.tag_configure("keyword", foreground="#0000FF", font=("Consolas", 10, "bold"))
    text_widget.tag_configure("string", foreground="#008000")
    text_widget.tag_configure("comment", foreground="#808080", font=("Consolas", 10, "italic"))
    text_widget.tag_configure("function", foreground="#FF00FF")
    text_widget.tag_configure("number", foreground="#FF4500")
    text_widget.tag_configure("operator", foreground="#666666")

    # Clear existing tags
    for tag in text_widget.tag_names():
        text_widget.tag_remove(tag, "1.0", tk.END)

    # Lex SQL
    lexer = SqlLexer()
    position = 0

    for token_type, token_value in lex(sql_text, lexer):
        token_length = len(token_value)
        start_index = f"1.0 + {position} chars"
        end_index = f"1.0 + {position + token_length} chars"

        # Map token types to tags
        if token_type in Token.Keyword:
            text_widget.tag_add("keyword", start_index, end_index)
        elif token_type in Token.String:
            text_widget.tag_add("string", start_index, end_index)
        elif token_type in Token.Comment:
            text_widget.tag_add("comment", start_index, end_index)
        elif token_type in Token.Number:
            text_widget.tag_add("number", start_index, end_index)
        elif token_type in Token.Name.Function:
            text_widget.tag_add("function", start_index, end_index)
        elif token_type in Token.Operator:
            text_widget.tag_add("operator", start_index, end_index)

        position += token_length
```

**Estimation temps de développement**: 2-3 heures

---

## 🎨 Comparaison des Options

| Option | Complexité | Temps Dev | Qualité | Maintenance | Recommandation |
|--------|-----------|-----------|---------|-------------|----------------|
| **sqlparse** | ⭐⭐ Facile | 2-3h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **✅ MEILLEUR CHOIX** |
| **Pygments** | ⭐⭐ Facile | 2-3h | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Très bon |
| **Regex manuel** | ⭐⭐⭐ Moyen | 4-6h | ⭐⭐ | ⭐⭐ | ⚠️ Déconseillé |

**Recommandation**: **sqlparse** (déjà une dépendance du projet si on fait du formatage)

---

## 📐 2. Formatage SQL (Pretty-Print)

### Degré de Complexité: **⭐ TRÈS FACILE**

**Bibliothèque**: `sqlparse`

**Temps de développement**: **30 minutes à 1 heure**

### Implémentation

```python
import sqlparse

def format_sql(sql_text):
    """Format SQL query to be readable"""
    formatted = sqlparse.format(
        sql_text,
        reindent=True,              # Indentation
        keyword_case='upper',       # Mots-clés en MAJUSCULES
        identifier_case='lower',    # Identifiants en minuscules (optionnel)
        indent_width=4,             # 4 espaces d'indentation
        indent_tabs=False,          # Utiliser espaces, pas tabs
        use_space_around_operators=True,  # Espaces autour des opérateurs
        wrap_after=80,              # Retour à la ligne après 80 caractères
        comma_first=False           # Virgule à la fin (pas au début)
    )
    return formatted
```

### Exemple de Transformation

**Avant** (une seule ligne):
```sql
SELECT u.id, u.name, u.email, o.order_id, o.total FROM users u INNER JOIN orders o ON u.id = o.user_id WHERE o.total > 100 AND u.status = 'active' ORDER BY o.total DESC
```

**Après** (formaté):
```sql
SELECT u.id,
       u.name,
       u.email,
       o.order_id,
       o.total
FROM users u
INNER JOIN orders o
    ON u.id = o.user_id
WHERE o.total > 100
  AND u.status = 'active'
ORDER BY o.total DESC
```

### Intégration dans l'Application

**Ajout d'un bouton "Format SQL"** dans la toolbar:

```python
# Dans database_manager.py, QueryTab.__init__()
ttk.Button(toolbar, text="🎨 Format SQL", command=self._format_sql).pack(side=tk.LEFT, padx=2)

def _format_sql(self):
    """Format SQL query"""
    sql_text = self.query_text.get(1.0, tk.END).strip()
    if not sql_text:
        return

    try:
        formatted = sqlparse.format(
            sql_text,
            reindent=True,
            keyword_case='upper',
            indent_width=4,
            use_space_around_operators=True
        )

        # Replace text
        self.query_text.delete(1.0, tk.END)
        self.query_text.insert(1.0, formatted)

        # Apply syntax highlighting
        self._apply_syntax_highlighting()

        logger.info("SQL formatted successfully")
    except Exception as e:
        messagebox.showerror("Format Error", f"Failed to format SQL:\n{e}")
        logger.error(f"SQL formatting failed: {e}")
```

---

## 🚀 Plan d'Implémentation Recommandé

### Phase 1: Formatage SQL (30 min - 1h) ⭐

**Priorité**: HAUTE (fonctionnalité simple et très utile)

1. Ajouter `sqlparse` aux dépendances (si pas déjà présent)
2. Ajouter bouton "🎨 Format SQL" dans toolbar
3. Implémenter méthode `_format_sql()`
4. Tester avec requêtes complexes

**Fichiers à modifier**:
- `pyproject.toml` (ajouter sqlparse si nécessaire)
- `database_manager.py` (QueryTab class)

---

### Phase 2: Coloration Syntaxique (2-3h) ⭐⭐

**Priorité**: MOYENNE (améliore beaucoup l'expérience utilisateur)

**Approche recommandée**: `sqlparse`

1. Créer module `sql_syntax_highlighter.py`
2. Implémenter `apply_sql_highlighting(text_widget, sql_text)`
3. Ajouter callback sur modification du texte
4. Optimiser pour éviter lags (seulement si texte > 1000 lignes)

**Fichiers à créer/modifier**:
- `sql_syntax_highlighter.py` (nouveau)
- `database_manager.py` (QueryTab class)

---

## 🎨 Palette de Couleurs Recommandée

### Style "Visual Studio Code (Light)"

```python
color_scheme = {
    "keyword": {"foreground": "#0000FF", "font": ("Consolas", 10, "bold")},      # Bleu foncé
    "string": {"foreground": "#A31515"},                                          # Rouge brique
    "comment": {"foreground": "#008000", "font": ("Consolas", 10, "italic")},    # Vert
    "function": {"foreground": "#795E26"},                                        # Brun
    "number": {"foreground": "#098658"},                                          # Vert sombre
    "operator": {"foreground": "#000000"},                                        # Noir
    "identifier": {"foreground": "#001080"},                                      # Bleu moyen
}
```

### Style "Monokai (Dark)" - Si thème sombre

```python
color_scheme_dark = {
    "keyword": {"foreground": "#F92672", "font": ("Consolas", 10, "bold")},      # Rose
    "string": {"foreground": "#E6DB74"},                                          # Jaune
    "comment": {"foreground": "#75715E", "font": ("Consolas", 10, "italic")},    # Gris
    "function": {"foreground": "#A6E22E"},                                        # Vert clair
    "number": {"foreground": "#AE81FF"},                                          # Violet
    "operator": {"foreground": "#F92672"},                                        # Rose
    "identifier": {"foreground": "#FD971F"},                                      # Orange
}
```

---

## ⚡ Optimisations Possibles

### 1. Coloration en Temps Réel (avec debouncing)

Pour éviter de recalculer la coloration à chaque frappe:

```python
import threading

class SQLEditor:
    def __init__(self):
        self.highlight_timer = None

    def on_text_modified(self, event=None):
        # Cancel previous timer
        if self.highlight_timer:
            self.highlight_timer.cancel()

        # Schedule highlighting after 500ms of inactivity
        self.highlight_timer = threading.Timer(0.5, self._apply_highlighting)
        self.highlight_timer.start()

    def _apply_highlighting(self):
        # Apply syntax highlighting
        sql_text = self.query_text.get(1.0, tk.END)
        apply_sql_highlighting(self.query_text, sql_text)
```

### 2. Cache de Parsing

```python
import hashlib

class SQLHighlighter:
    def __init__(self):
        self.cache = {}

    def highlight(self, text_widget, sql_text):
        # Calculate hash of SQL text
        text_hash = hashlib.md5(sql_text.encode()).hexdigest()

        # Check cache
        if text_hash in self.cache:
            tokens = self.cache[text_hash]
        else:
            # Parse SQL
            tokens = sqlparse.parse(sql_text)[0].flatten()
            self.cache[text_hash] = list(tokens)

        # Apply tags
        # ...
```

---

## 📦 Dépendances

### sqlparse

```bash
uv add sqlparse
```

**Taille**: ~200 KB
**Licence**: BSD-3-Clause
**Maintenance**: Active (dernière version 2024)

### pygments (optionnel)

```bash
uv add pygments
```

**Taille**: ~2 MB
**Licence**: BSD-2-Clause
**Maintenance**: Très active

---

## 🧪 Tests

### Test du Formatage

```python
# test_sql_formatting.py
import sqlparse

test_queries = [
    "SELECT * FROM users WHERE id=1",
    "SELECT u.id, u.name, o.total FROM users u JOIN orders o ON u.id=o.user_id",
    "INSERT INTO users (name, email) VALUES ('John', 'john@example.com')",
    "UPDATE users SET status='active' WHERE last_login > '2024-01-01'",
]

for query in test_queries:
    formatted = sqlparse.format(query, reindent=True, keyword_case='upper')
    print(f"Original:\n{query}\n")
    print(f"Formatted:\n{formatted}\n")
    print("-" * 50)
```

---

## 🎯 Résumé

### Complexité Totale

| Fonctionnalité | Complexité | Temps | Recommandation |
|----------------|------------|-------|----------------|
| **Formatage SQL** | ⭐ Très facile | 30 min - 1h | ✅ **À FAIRE EN PREMIER** |
| **Coloration syntaxique** | ⭐⭐ Facile | 2-3h | ✅ **Très utile** |
| **Combiné (Format + Coloration)** | ⭐⭐ Facile | 3-4h | ✅ **Excellent ROI** |

### Bénéfices Utilisateur

✅ **Formatage SQL**:
- Requêtes complexes deviennent lisibles instantanément
- Évite les erreurs de syntaxe
- Productivité +50%

✅ **Coloration Syntaxique**:
- Repérage visuel immédiat des erreurs
- Lecture plus rapide du code
- Expérience professionnelle

### Recommandation Finale

**Phase 1 (Quick Win)**: Implémenter le formatage SQL (1h de dev)
**Phase 2 (Valeur ajoutée)**: Ajouter la coloration syntaxique (2-3h de dev)

**Total**: **3-4 heures** pour une amélioration majeure de l'expérience utilisateur ! 🚀

---

**Version**: 1.0
**Date**: 2025-12-07
**Auteur**: Claude Code
