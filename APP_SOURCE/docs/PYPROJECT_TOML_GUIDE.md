# Guide du pyproject.toml

## 📋 Vue d'Ensemble

Le fichier `pyproject.toml` a été mis à jour pour **v2.0.0** avec la nouvelle structure modulaire.

---

## 📝 Contenu Actuel

### Métadonnées du Projet

```toml
[project]
name = "load-data-lake"
version = "2.0.0"
description = "Application Python pour charger et gérer des données..."
readme = "README.md"
requires-python = ">=3.14"
```

**Changements v2.0** :
- ✅ Version passée de `0.1.0` à `2.0.0`
- ✅ Description complète et détaillée
- ✅ Métadonnées ajoutées (auteurs, licence, keywords)

### Dépendances

```toml
dependencies = [
    "colorama>=0.4.6",      # Couleurs console
    "pandas>=2.3.3",        # Manipulation de données
    "pyodbc>=5.3.0",        # Connexion SQL Server
    "sqlalchemy>=2.0.44",   # ORM et abstraction DB
    "sqlparse>=0.5.4",      # Parsing et formatage SQL
    "tabulate>=0.9.0",      # Affichage tableaux
]
```

**Toutes présentes et à jour** ✅

### Dépendances de Développement

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",        # Framework de tests
    "pytest-cov>=4.0.0",    # Couverture de code
]
```

**Installation** :
```bash
uv sync --extra dev
```

### Configuration Build

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

**Configure le package pour utiliser la structure `src/`** ✅

### Configuration Pytest

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

**Lancer les tests** :
```bash
uv run pytest
```

---

## 🚀 Utilisation

### Installation du Projet

```bash
# Installation des dépendances
uv sync

# Installation avec dépendances de dev
uv sync --extra dev
```

### Lancement de l'Application

**Méthode 1 : Via run.py (RECOMMANDÉ)**
```bash
uv run run.py
```

**Méthode 2 : Via main.py**
```bash
uv run src/main.py
```

**Méthode 3 : Via CLI**
```bash
uv run cli.py help
```

### Tests

```bash
# Tous les tests
uv run pytest

# Test avec couverture
uv run pytest --cov=src

# Test spécifique
uv run python tests/test_sql_features.py
```

---

## 📦 Build et Distribution

### Créer un Package

```bash
# Build le package
uv build

# Crée des fichiers dans dist/:
# - load_data_lake-2.0.0-py3-none-any.whl
# - load_data_lake-2.0.0.tar.gz
```

### Installation Locale

```bash
# Installer le package en mode éditable
uv pip install -e .

# Après installation, vous pouvez lancer:
python -m src.main
```

---

## ⚙️ Entry Points (Désactivés)

Les entry points sont actuellement **commentés** car l'application utilise directement `run.py` et `cli.py`.

Pour les activer (si nécessaire) :

```toml
[project.scripts]
load-data-lake = "src.main:main"
load-data-lake-cli = "cli:main"
```

Puis après installation :
```bash
load-data-lake        # Lance la GUI
load-data-lake-cli    # Lance le CLI
```

**Note** : Nécessite que le package soit installé (`uv pip install -e .`)

---

## 🔧 Configurations Additionnelles Possibles

### Ajout de Classifiers

Les classifiers sont déjà configurés :

```toml
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.14",
    "Topic :: Database :: Front-Ends",
]
```

### Ajout d'URLs

Vous pouvez ajouter :

```toml
[project.urls]
Homepage = "https://github.com/votre-org/load-data-lake"
Documentation = "https://load-data-lake.readthedocs.io"
Repository = "https://github.com/votre-org/load-data-lake.git"
Issues = "https://github.com/votre-org/load-data-lake/issues"
```

### Configuration de Black (Formatter)

```toml
[tool.black]
line-length = 100
target-version = ["py314"]
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

### Configuration de Ruff (Linter)

```toml
[tool.ruff]
line-length = 100
target-version = "py314"
select = ["E", "F", "I", "N", "W", "UP"]
ignore = []

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports in __init__
```

---

## ✅ Vérification

### Vérifier que tout fonctionne

```bash
# 1. Sync des dépendances
uv sync

# 2. Lancer l'application
uv run run.py

# 3. Lancer les tests
uv run pytest tests/

# 4. Vérifier le build
uv build
```

**Résultat attendu** :
```
✅ Resolved 21 packages
✅ Installed load-data-lake==2.0.0
✅ Application démarre
✅ Tests passent
```

---

## 📊 Résumé

| Élément | Status | Description |
|---------|--------|-------------|
| **Version** | ✅ 2.0.0 | Mise à jour pour nouvelle structure |
| **Dépendances** | ✅ OK | Toutes présentes et à jour |
| **Build System** | ✅ OK | Hatchling configuré pour src/ |
| **Tests** | ✅ OK | Pytest configuré |
| **Entry Points** | ⚠️ Désactivés | Utilisez run.py à la place |
| **Metadata** | ✅ OK | Auteurs, licence, keywords |

---

## 🎯 Recommandations

1. **Utilisation actuelle** : Parfaitement fonctionnel avec `uv run run.py`
2. **Entry points** : Activez-les si vous voulez distribuer le package
3. **Tests** : Configurez pytest-cov pour la couverture de code
4. **Linting** : Ajoutez ruff ou black pour le formatage

**Le pyproject.toml est maintenant complet et adapté à la structure v2.0 !** ✅

---

**Version** : 2.0.0
**Date** : 2025-12-07
**Status** : ✅ Validé et Testé
