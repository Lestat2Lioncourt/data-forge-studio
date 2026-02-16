# Guide Administrateur - Ajouter un Paramètre Général

Ce document explique comment ajouter un nouveau paramètre utilisateur dans la section **Preferences > Général** de l'application.

---

## Principe

Les paramètres généraux sont **data-driven** : l'interface (treeview + éditeur) se génère automatiquement à partir de définitions déclaratives. Ajouter un paramètre ne nécessite aucun code UI.

**Deux fichiers à modifier :**

| Fichier | Rôle |
|---------|------|
| `src/dataforge_studio/config/user_preferences.py` | Valeur par défaut + persistance |
| `src/dataforge_studio/ui/frames/settings_frame.py` | Définition UI (treeview + éditeur) |

---

## Étape 1 : Déclarer la valeur par défaut

**Fichier** : `src/dataforge_studio/config/user_preferences.py`

Ajouter la clé et sa valeur par défaut dans le dictionnaire `DEFAULT_PREFERENCES` :

```python
DEFAULT_PREFERENCES = {
    "objects_borders": "false",
    "theme": "minimal_dark",
    "language": "fr",
    "sql_format_style": "expanded",
    "export_language": "python",
    "query_column_names": "query, requête",
    "mon_nouveau_param": "valeur_par_defaut",   # ← Ajouter ici
}
```

### Pourquoi c'est nécessaire

Au démarrage, la méthode `_ensure_defaults()` vérifie chaque clé de `DEFAULT_PREFERENCES`. Si elle n'existe pas encore dans la base SQLite (`_AppConfig/configuration.db`, table `user_preferences`), elle est créée automatiquement avec la valeur par défaut.

Cela garantit que :
- Un **nouvel utilisateur** (installation offline) a toutes les valeurs initiales
- Un **utilisateur existant** qui met à jour l'application récupère les nouveaux paramètres sans perdre ses valeurs personnalisées

### Règles de typage

Toutes les valeurs sont stockées en `str` dans la base. La conversion est automatique à la lecture :

| Valeur stockée | Type retourné par `get()` |
|----------------|--------------------------|
| `"true"` / `"false"` | `bool` |
| `"123"` (chiffres uniquement) | `int` |
| Tout autre texte | `str` |

---

## Étape 2 : Déclarer l'entrée dans l'interface

**Fichier** : `src/dataforge_studio/ui/frames/settings_frame.py`

Ajouter un dictionnaire dans la liste `GENERAL_PREFERENCES` :

```python
GENERAL_PREFERENCES = [
    {
        "key": "query_column_names",
        ...
    },
    # ← Ajouter ici :
    {
        "key": "mon_nouveau_param",        # Doit correspondre à la clé dans DEFAULT_PREFERENCES
        "label": "Mon paramètre",          # Texte affiché dans le treeview et comme label du champ
        "type": "text",                     # Type de widget : "text", "bool" ou "choice"
        "group": "Titre du GroupBox",       # Titre du cadre dans le panneau droit
        "description": "Explication...",    # Texte italique affiché au-dessus du champ
        "placeholder": "exemple...",        # Texte grisé dans le champ (type "text" uniquement)
        "default": "valeur_par_defaut",     # Valeur par défaut (cohérente avec DEFAULT_PREFERENCES)
    },
]
```

### Résultat automatique

Sans écrire de code UI supplémentaire :
- Un **noeud enfant** apparaît sous `Preferences > Général` dans le treeview
- Un clic sur ce noeud affiche le **panneau d'édition** adapté au type
- Le bouton **Appliquer** sauvegarde la valeur dans la base SQLite

---

## Types de widgets supportés

### `"text"` — Champ de saisie libre

```python
{
    "key": "query_column_names",
    "label": "Noms de colonnes (Edit Query)",
    "type": "text",
    "group": "Edit Query - Noms de colonnes",
    "description": "Liste des noms de colonnes séparés par des virgules...",
    "placeholder": "query, requête, sql, ...",
    "default": "query, requête",
}
```

Widget généré : `QLineEdit`

### `"bool"` — Case à cocher

```python
{
    "key": "auto_format_on_load",
    "label": "Formater automatiquement les requêtes",
    "type": "bool",
    "group": "Mise en forme SQL",
    "description": "Applique le formatage automatique lors du chargement d'une requête.",
    "default": "false",
}
```

Widget généré : `QCheckBox`

### `"choice"` — Liste déroulante

```python
{
    "key": "default_row_limit",
    "label": "Nombre de lignes par défaut",
    "type": "choice",
    "group": "Résultats de requêtes",
    "description": "Nombre maximum de lignes affichées par défaut dans les résultats.",
    "choices": ["100", "1000", "5000", "10000", "Illimité"],
    "default": "1000",
}
```

Widget généré : `QComboBox`

---

## Champs de la définition

| Champ | Obligatoire | Description |
|-------|:-----------:|-------------|
| `key` | oui | Clé de la préférence (identique à celle dans `DEFAULT_PREFERENCES`) |
| `label` | oui | Texte affiché dans le treeview et comme label du champ de saisie |
| `type` | oui | Type de widget : `"text"`, `"bool"` ou `"choice"` |
| `group` | non | Titre du `QGroupBox` (si absent, utilise `label`) |
| `description` | non | Texte explicatif affiché en italique au-dessus du champ |
| `placeholder` | non | Texte indicatif grisé (type `"text"` uniquement) |
| `choices` | non | Liste des valeurs proposées (type `"choice"` uniquement) |
| `default` | non | Valeur par défaut (doit correspondre à `DEFAULT_PREFERENCES`) |

---

## Lire un paramètre dans le code

Pour utiliser un paramètre dans n'importe quel module de l'application :

```python
from dataforge_studio.config.user_preferences import UserPreferences

prefs = UserPreferences.instance()
value = prefs.get("mon_nouveau_param", "valeur_par_defaut")
```

---

## Résumé visuel

```
Utilisateur ouvre Preferences
│
├─ Général                          ← catégorie (GENERAL_PREFERENCES)
│   ├─ Noms de colonnes (Edit Query)   ← noeud généré depuis GENERAL_PREFERENCES[0]
│   └─ Mon paramètre                   ← noeud généré depuis GENERAL_PREFERENCES[1]
├─ Langue
├─ Thèmes
│   ├─ minimal_dark
│   └─ ...
└─ Debug
    └─ Contours
```

Clic sur un noeud → panneau droit = éditeur auto-généré :

```
┌─────────────────────────────────────────────┐
│ ┌─ Titre du GroupBox ─────────────────────┐ │
│ │  Description en italique...             │ │
│ │                                         │ │
│ │  Label : [__________champ_de_saisie__]  │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ [ Appliquer ]                               │
│                                             │
│ Options appliquées ✓                        │
└─────────────────────────────────────────────┘
```

---

## Checklist rapide

- [ ] Clé ajoutée dans `DEFAULT_PREFERENCES` (`user_preferences.py`)
- [ ] Entrée ajoutée dans `GENERAL_PREFERENCES` (`settings_frame.py`)
- [ ] Les deux `key` sont identiques
- [ ] Les deux `default` sont cohérents
- [ ] Le code consommateur utilise `UserPreferences.instance().get("ma_clé", "défaut")`
