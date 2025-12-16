# Guide du Visualiseur de Documentation

## 📚 Vue d'Ensemble

Le **Help Viewer** (Visualiseur d'Aide) est un lecteur de documentation intégré qui affiche tous les fichiers Markdown (`.md`) de l'application dans une interface conviviale.

---

## 🎯 Accès

**Menu** : **Help → 📚 Documentation**

---

## 🖥️ Interface

L'interface est divisée en deux parties :

```
┌─────────────────────────────────────────────────────────────────┐
│  📚 Help Documentation                                          │
├──────────────────────┬──────────────────────────────────────────┤
│  Documentation       │  Document Title                          │
│  Topics              │  File: filename.md                       │
│                      │  ─────────────────────────────────────   │
│  ☐ Config Db Info    │                                          │
│  ☑ New Features...   │  # Header 1                              │
│  ☐ Right Click...    │                                          │
│  ☐ Save Queries...   │  Some formatted content with **bold**   │
│  ☐ Sqlite Native...  │  and *italic* text.                     │
│  ☐ Summary All...    │                                          │
│                      │  ```                                     │
│                      │  code block                              │
│                      │  ```                                     │
│                      │                                          │
│                      │  - List item 1                           │
│                      │  - List item 2                           │
│                      │                                          │
└──────────────────────┴──────────────────────────────────────────┘
```

### Panneau Gauche : Liste des Documents

- **Liste des topics** disponibles
- Un clic pour sélectionner
- Le premier document est chargé par défaut
- Navigation facile entre les documents

### Panneau Droit : Contenu du Document

- **Titre** du document
- **Nom du fichier** (en gris)
- **Contenu formaté** avec :
  - Headers (H1, H2, H3)
  - Code blocks
  - Inline code
  - Bold et Italic
  - Listes à puces
  - Lignes horizontales

---

## 📖 Documentation Disponible

Actuellement, **7 fichiers** de documentation sont disponibles :

| Document | Taille | Description |
|----------|--------|-------------|
| **Config Db Info** | 6.5 KB | Structure de la base de configuration SQLite |
| **New Features Queries Db** | 15.1 KB | Nouvelles fonctionnalités (menu contextuel, queries manager) |
| **Right Click Menu** | 7.3 KB | Menu contextuel sur les tables (SELECT Top N) |
| **Save Queries Guide** | 9.2 KB | Guide complet de sauvegarde de requêtes |
| **Sqlite Native Support** | 5.6 KB | Support SQLite natif sans driver ODBC |
| **Summary All Features** | 11.2 KB | Résumé de toutes les fonctionnalités |
| **Readme** | 3.0 KB | Fichier README du projet |

**Total** : ~58 KB de documentation

---

## 🎨 Formatage Markdown

Le visualiseur supporte les éléments Markdown suivants :

### Headers

```markdown
# Header 1     → Police 16pt, bleu foncé
## Header 2    → Police 14pt, bleu moyen
### Header 3   → Police 12pt, bleu clair
```

### Code

**Inline code** : `` `code` ``
- Fond gris clair
- Police Consolas
- Couleur rouge

**Code blocks** :
````markdown
```
code block
multi-line
```
````
- Fond gris clair
- Police Consolas 9pt
- Indentation

### Formatage de Texte

- **`**bold**`** → Texte en gras
- **`*italic*`** → Texte en italique

### Listes

```markdown
- Item 1
- Item 2
* Item 3

1. Numbered item
2. Another item
```

- Bullet automatique (•)
- Indentation

### Lignes Horizontales

```markdown
---
===
```

Affichées comme : ────────────────────────

### Blockquotes

```markdown
> Citation
```

- Indentation
- Couleur grise
- Fond légèrement grisé

---

## ⌨️ Utilisation

### Navigation

1. **Ouvrir** : Help → 📚 Documentation
2. **Sélectionner** : Clic sur un document dans la liste
3. **Lire** : Contenu affiché avec formatage
4. **Défiler** : Scrollbars vertical et horizontal
5. **Fermer** : Bouton "Close"

### Raccourcis

- **Clic simple** : Sélectionne et affiche le document
- **Scroll vertical** : Molette de la souris
- **Scroll horizontal** : Shift + Molette (si nécessaire)

---

## 🔧 Détails Techniques

### Fichier

**Fichier** : `help_viewer.py`

**Classe** : `HelpViewer(tk.Toplevel)`

### Recherche des Fichiers

```python
def _find_documentation_files(self) -> List[Dict]:
    """Find all markdown documentation files"""
    app_folder = Path(__file__).parent
    md_files = list(app_folder.glob("*.md"))
    # Ignore README.md if it's just a placeholder
    # Returns list of dicts with name, filename, path
```

### Formatage Markdown

La méthode `_format_markdown()` parse le contenu ligne par ligne et applique :

- **Tags de texte** : h1, h2, h3, code, code_block, bold, italic
- **Tags de mise en page** : list_item, blockquote
- **Formatage inline** : `_format_inline()` pour le formatage dans les lignes

### Configuration des Tags

```python
# Headers
self.content_text.tag_configure("h1", font=("Arial", 16, "bold"),
                                foreground="#1a5490", spacing1=10)

# Code
self.content_text.tag_configure("code", font=("Consolas", 9),
                                background="#f5f5f5", foreground="#c7254e")

# Code blocks
self.content_text.tag_configure("code_block", font=("Consolas", 9),
                                background="#f8f8f8", lmargin1=20)

# Bold/Italic
self.content_text.tag_configure("bold", font=("Arial", 10, "bold"))
self.content_text.tag_configure("italic", font=("Arial", 10, "italic"))
```

---

## 📋 Exemples de Contenu

### Exemple 1 : Headers et Code

```markdown
# Installation

Pour installer l'application :

```bash
uv sync
uv run python gui.py
```

## Configuration

La configuration est dans `_AppConfig/`.
```

**Résultat** :
- "Installation" en gros, bleu foncé
- Code bash avec fond gris
- "Configuration" en moyen, bleu moyen
- Path avec formatage inline code

### Exemple 2 : Listes et Bold

```markdown
## Fonctionnalités

- **Sauvegarde de requêtes** : Stockage dans SQLite
- **Menu contextuel** : Clic droit sur tables
- *Support SQLite* : Pas de driver ODBC nécessaire
```

**Résultat** :
- "Fonctionnalités" comme H2
- Bullets avec formatage bold/italic

---

## 🎯 Cas d'Usage

### Scénario 1 : Découvrir les Fonctionnalités

1. Ouvrir **Help → Documentation**
2. Sélectionner **"Summary All Features"**
3. Lire le résumé complet
4. Naviguer vers des guides spécifiques

### Scénario 2 : Apprendre à Sauvegarder des Requêtes

1. Ouvrir la Documentation
2. Sélectionner **"Save Queries Guide"**
3. Suivre les instructions pas à pas
4. Tester immédiatement dans l'application

### Scénario 3 : Résoudre un Problème de Connexion

1. Ouvrir la Documentation
2. Sélectionner **"Sqlite Native Support"**
3. Vérifier les instructions d'installation
4. Tester la connexion

### Scénario 4 : Référence Rapide

1. Garder la fenêtre Documentation ouverte
2. Travailler dans l'application principale
3. Consulter la doc au besoin
4. Basculer entre les topics rapidement

---

## ✨ Avantages

### Pour l'Utilisateur

✅ **Accès Immédiat**
- Pas besoin d'ouvrir des fichiers externes
- Tout dans l'application
- Navigation rapide

✅ **Formatage Agréable**
- Code bien visible
- Headers clairs
- Listes organisées

✅ **Auto-Mise à Jour**
- Détecte automatiquement les nouveaux fichiers .md
- Toujours à jour avec le code

### Pour le Développeur

✅ **Simplicité**
- Un fichier Markdown = une documentation
- Syntaxe standard
- Facile à maintenir

✅ **Extensibilité**
- Ajout de nouveaux docs = créer un fichier .md
- Détection automatique
- Pas de configuration nécessaire

---

## 📊 Statistiques

### Documents Actuels (7 fichiers)

```
Config Db Info              ████████ 6.5 KB
New Features Queries Db     ████████████████ 15.1 KB
Right Click Menu            ███████ 7.3 KB
Save Queries Guide          █████████ 9.2 KB
Sqlite Native Support       ██████ 5.6 KB
Summary All Features        ███████████ 11.2 KB
Readme                      ███ 3.0 KB
```

**Total** : 57.9 KB de documentation

---

## 🚀 Ajout de Nouvelle Documentation

Pour ajouter un nouveau document :

1. **Créer un fichier** `.md` dans le dossier racine
   ```bash
   touch MY_NEW_GUIDE.md
   ```

2. **Écrire le contenu** en Markdown
   ```markdown
   # Mon Nouveau Guide

   ## Introduction

   Ceci est un guide sur...

   ```python
   # Code example
   print("Hello")
   ```
   ```

3. **Relancer l'application**
   - Le nouveau document apparaît automatiquement dans la liste
   - Nom affiché : "My New Guide"

**Pas de configuration nécessaire !**

---

## 🔍 Limitations Actuelles

⚠️ **Formatage Markdown Simplifié**
- Pas de support pour les images
- Pas de tableaux complexes
- Pas de liens hypertexte cliquables
- Pas de notes de bas de page

⚠️ **Lecture Seule**
- Impossible d'éditer depuis le viewer
- Éditer les fichiers .md avec un éditeur externe

⚠️ **Pas de Recherche**
- Pas de recherche de texte dans les documents
- Navigation par sélection de document uniquement

---

## 💡 Conseils d'Utilisation

### Pour une Lecture Efficace

1. **Commencez par** "Summary All Features"
2. **Approfondissez** avec les guides spécifiques
3. **Gardez ouvert** pendant l'utilisation
4. **Référez-vous** en cas de doute

### Pour une Documentation de Qualité

1. **Headers clairs** (H1 pour titre, H2 pour sections)
2. **Code blocks** pour les exemples
3. **Listes** pour l'énumération
4. **Bold** pour les points importants
5. **Tables** pour comparer (limitées)

### Organisation Recommandée

```markdown
# Titre Principal

## Vue d'ensemble
Brève introduction

## Fonctionnalités
- Feature 1
- Feature 2

## Utilisation
Instructions pas à pas

## Exemples
```code
example
```

## Résolution de Problèmes
FAQ

## Voir Aussi
Références vers autres docs
```

---

## 🎉 Conclusion

Le Help Viewer offre :
- ✅ **Documentation intégrée** accessible en un clic
- ✅ **Formatage Markdown** pour une lecture agréable
- ✅ **Navigation facile** entre les topics
- ✅ **Auto-mise à jour** avec les nouveaux fichiers
- ✅ **Aucune configuration** nécessaire

**Profitez de la documentation toujours à portée de main !**

---

**Fichier** : `help_viewer.py`
**Menu** : Help → 📚 Documentation
**Formats supportés** : Markdown (`.md`)
**Documentation totale** : ~58 KB (7 fichiers)
