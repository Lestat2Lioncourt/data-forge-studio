# Plan de Migration v0.6.0 - Restructuration Framework

**Date**: 2025-12-20
**Objectif**: Préparer l'architecture pour un framework d'application réutilisable

---

## Vision Long Terme

Créer une séparation claire entre :
- **Framework** : Templates UI, core, theming (réutilisable pour d'autres apps)
- **Application** : Plugins métier, managers spécifiques (DataForge Studio)

---

## Phase 1 : Restructuration `ui/templates/`

### 1.1 Créer la nouvelle structure

```
ui/
├── templates/                    # NOUVEAU - Framework réutilisable
│   ├── __init__.py
│   ├── window/                   # Déplacé depuis window_template/
│   │   ├── __init__.py
│   │   ├── title_bar.py
│   │   ├── menu_bar.py
│   │   ├── status_bar.py
│   │   ├── resize_wrapper.py
│   │   ├── template_window.py
│   │   ├── main_window.py
│   │   ├── resources.py
│   │   ├── theme_manager.py
│   │   ├── themes.json
│   │   └── icons/
│   │       ├── btn_close.png
│   │       ├── btn_minimize.png
│   │       ├── btn_zoom.png
│   │       └── btn_special.png
│   └── dialog/                   # NOUVEAU
│       ├── __init__.py
│       └── selector_dialog.py    # Dialog de sélection avec titre custom
│
├── framework/                    # NOUVEAU - Widgets framework de base
│   ├── __init__.py
│   └── base_widgets.py           # Widgets fondamentaux (futur)
│
└── app/                          # Spécifique DataForge (optionnel pour v0.6.0)
    ├── managers/                 # Déplacé depuis managers/
    ├── frames/                   # Déplacé depuis frames/
    └── dialogs/                  # Déplacé depuis dialogs/
```

### 1.2 Migration des imports

Fichiers à mettre à jour (imports `window_template` → `templates.window`) :

| Fichier | Imports à modifier |
|---------|-------------------|
| `ui/core/main_window.py` | TitleBar, MenuBar, StatusBar, ResizeWrapper |
| `ui/widgets/about_dialog.py` | TitleBar |
| `ui/widgets/distribution_analysis_dialog.py` | TitleBar |
| `ui/core/splash_screen.py` | (vérifier) |

### 1.3 Supprimer l'ancien dossier

- Supprimer `ui/window_template/` après migration complète

---

## Phase 2 : Création de `SelectorDialog`

### 2.1 Spécifications

```python
# ui/templates/dialog/selector_dialog.py

class SelectorDialog(QDialog):
    """
    Dialog de sélection avec barre de titre personnalisée.

    Caractéristiques :
    - FramelessWindowHint (pas de barre native)
    - Barre de titre simplifiée (titre + bouton fermer uniquement)
    - Couleurs personnalisables via thème
    - Bordure visible
    """

    def __init__(self, title: str, parent=None):
        ...
```

### 2.2 Nouvelles clés de thème

Ajouter dans `theme_bridge.py` et les fichiers de thème :

```python
# Valeurs par défaut (couleurs Qt natives approximées)
"selector_titlebar_bg": "#2b2b2b",      # Fond barre de titre
"selector_titlebar_fg": "#ffffff",       # Texte barre de titre
"selector_border_color": "#3d3d3d",      # Bordure du dialog
"selector_close_btn_hover": "#e81123",   # Bouton fermer au survol
```

### 2.3 Composants de SelectorDialog

1. **SelectorTitleBar** (simplifiée)
   - Label titre
   - Bouton fermer (X) avec style rouge au survol
   - Pas de minimize/maximize
   - Draggable

2. **Bordure visible**
   - 1px solid `selector_border_color`

---

## Phase 3 : Migration des dialogs existants

### 3.1 ConnectionSelectorDialog

```python
# Avant
class ConnectionSelectorDialog(QDialog):
    ...

# Après
class ConnectionSelectorDialog(SelectorDialog):
    def __init__(self, parent=None):
        super().__init__(title="New Connection", parent=parent)
        ...
```

### 3.2 AboutDialog

```python
# Avant
class AboutDialog(QDialog):
    # Gère sa propre TitleBar
    ...

# Après
class AboutDialog(SelectorDialog):
    def __init__(self, parent=None):
        super().__init__(title="About DataForge Studio", parent=parent)
        # Pas besoin de gérer TitleBar, c'est fait par SelectorDialog
        ...
```

---

## Phase 4 : Nettoyage et cohérence

### 4.1 Supprimer code mort

- [ ] `connection_dialog_factory.py` : Vérifier si encore utilisé, sinon supprimer
- [ ] Imports inutilisés dans les fichiers modifiés

### 4.2 Mettre à jour les thèmes existants

Ajouter les nouvelles clés dans :
- `_AppConfig/themes/*.json` (thèmes utilisateur)
- Valeurs par défaut dans `theme_bridge.py`

---

## Phase 5 : Tests et validation

### 5.1 Tests fonctionnels

- [ ] Menu Fichier ne contient que "Quitter"
- [ ] Resources → Databases → New Connection ouvre ConnectionSelectorDialog
- [ ] Sélection d'un type de BDD ouvre le bon dialog de connexion
- [ ] About dialog s'ouvre correctement
- [ ] Les couleurs de thème sont appliquées

### 5.2 Tests de régression

- [ ] L'application démarre sans erreur
- [ ] Tous les managers fonctionnent
- [ ] Le changement de thème fonctionne

---

## Ordre d'exécution recommandé

| Étape | Description | Risque | Durée estimée |
|-------|-------------|--------|---------------|
| 1 | Créer structure `ui/templates/` | Faible | 15 min |
| 2 | Déplacer `window_template/` → `templates/window/` | Moyen | 30 min |
| 3 | Mettre à jour tous les imports | Moyen | 45 min |
| 4 | Créer `SelectorDialog` | Faible | 1h |
| 5 | Ajouter clés thème | Faible | 15 min |
| 6 | Migrer `ConnectionSelectorDialog` | Moyen | 30 min |
| 7 | Migrer `AboutDialog` | Moyen | 30 min |
| 8 | Tests et corrections | Variable | 1h |
| 9 | Supprimer `window_template/` | Faible | 5 min |
| 10 | Commit v0.6.0 | - | 5 min |

**Durée totale estimée : 4-5 heures**

---

## Fichiers impactés (liste complète)

### À créer
- `ui/templates/__init__.py`
- `ui/templates/window/__init__.py`
- `ui/templates/dialog/__init__.py`
- `ui/templates/dialog/selector_dialog.py`

### À déplacer
- `ui/window_template/*` → `ui/templates/window/*`

### À modifier
- `ui/core/main_window.py` (imports)
- `ui/core/splash_screen.py` (imports)
- `ui/core/theme_bridge.py` (nouvelles clés thème)
- `ui/widgets/about_dialog.py` (hériter de SelectorDialog)
- `ui/dialogs/connection_dialogs/connection_selector_dialog.py` (hériter de SelectorDialog)

### À supprimer
- `ui/window_template/` (après migration)
- `ui/dialogs/connection_dialog_factory.py` (si inutilisé)

---

## Rollback

En cas de problème majeur :
```bash
git checkout v0.5.1 -- src/dataforge_studio/ui/
```

---

## Notes

- Cette restructuration prépare le terrain pour une future extraction du framework
- Les apps futures pourront réutiliser `ui/templates/` et `ui/framework/`
- Chaque app aura son propre dossier `ui/app/` avec ses managers/dialogs spécifiques
