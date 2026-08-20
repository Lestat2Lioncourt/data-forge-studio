# Checklist de publication d'une version

> **Le point qui a déjà été manqué plusieurs fois : `git push` ne publie rien.**
> L'application détecte les mises à jour via l'API GitHub `releases/latest`. Tant
> qu'aucune **release taguée** n'existe, aucun utilisateur ne voit la nouvelle
> version — et rien n'échoue, la publication *semble* réussie.

---

## 1. Bump de version

Modifier la version dans **tous** ces fichiers :

| Fichier | Emplacement | Format |
|---|---|---|
| `pyproject.toml` | ligne 3 | `version = "X.Y.Z"` |
| `src/dataforge_studio/__init__.py` | ligne 12 | `__version__ = "X.Y.Z"` |
| `src/dataforge_studio/main.py` | ligne 30 | `app.setApplicationVersion("X.Y.Z")` |
| `src/dataforge_studio/main.py` | ligne 46 | `'dataforge.studio.vXYZ'` (AppUserModelID, **sans points**) |
| `scripts/create_shortcut.py` | ~249-251 | `<string>X.Y.Z</string>` (×2 : CFBundleVersion + CFBundleShortVersionString) |
| `README.md` | ligne 1 | `# DataForge Studio vX.Y.Z` |
| `README.md` | ligne 6 | badge `version-X.Y.Z` |
| `ROADMAP.md` | ligne 3 | `**Version**: X.Y.Z` |
| `ROADMAP.md` | timeline | `vX.Y.Z (actuel)` |
| `ROADMAP.md` | conclusion | `portant le projet de v0.2.0 a vX.Y.Z` |

Ne **pas** toucher : `_packages/`, `saved_versions/`, `docs/MIGRATION_V0.6.0.md`.

Vérification :

```bash
grep -rn "X\.Y\.<ancienne>" --include=*.py --include=*.toml --include=*.md . \
  | grep -v "_packages/\|saved_versions/\|CHANGELOG.md\|uv.lock\|\.venv"
```

## 2. Dépendances

```bash
uv lock && uv sync
```

`uv sync` est **obligatoire** : il réinstalle le package dans le venv. Sans lui,
`importlib.metadata.version()` renvoie l'ancienne version et l'application se
croit périmée alors qu'elle est à jour.

```bash
python -c "import importlib.metadata as m; print(m.version('data-forge-studio'))"
```

## 3. CHANGELOG

Ajouter une entrée `## [X.Y.Z] - AAAA-MM-JJ` sous `## [Unreleased]`, au format
Keep a Changelog (`### Added` / `### Changed` / `### Fixed`).

## 4. Contrôles

```bash
python -m pytest -q                                    # tous verts
QT_QPA_PLATFORM=offscreen python -c "import sys;sys.path.insert(0,'src');import dataforge_studio.main"
```

## 5. Commit et push

```bash
git add -A
git commit -F <message>
git push origin main
```

## 6. Release GitHub — **l'étape sans laquelle rien n'est publié**

```bash
gh release create vX.Y.Z \
  --target main \
  --title "DataForge Studio vX.Y.Z" \
  --notes-file notes.md
```

Conventions du projet : tag `vX.Y.Z`, titre `DataForge Studio vX.Y.Z`, notes
**en français** structurées par thèmes, ni draft ni prerelease.

## 7. Vérifier que l'application verra la version

```bash
curl -s https://api.github.com/repos/Lestat2Lioncourt/data-forge-studio/releases/latest \
  | python -c "import sys,json; print(json.load(sys.stdin)['tag_name'])"
```

La sortie doit être le tag qui vient d'être créé. **Tant que ce n'est pas
vérifié, la version n'est pas publiée.**

---

## Ce que verra l'utilisateur

`utils/update_checker.py` compare le `tag_name` de `releases/latest` à la version
locale, puis :

- **barre de statut** — inconditionnelle : `🔔 vX.Y.Z disponible - Aide → Vérifier les Mises à Jour`
- **popup** — soumis à un **cooldown de 24 h** stocké dans
  `_AppConfig/update_check.json` (`last_dismissed`). Si l'utilisateur a écarté une
  notification dans les 24 h, le popup ne réapparaît pas ; supprimer ce fichier
  pour le forcer.

Le menu **Aide → Vérifier les Mises à Jour** fonctionne toujours, sans cooldown.
