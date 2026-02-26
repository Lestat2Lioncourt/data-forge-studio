# Installation Offline - DataForge Studio

Ce guide explique comment installer DataForge Studio sur une machine **sans acces internet**.

**Principe** : Une personne disposant d'une connexion internet genere un package autonome, puis le transfere (cle USB, partage reseau) a la machine cible.

---

## Etape 1 : Generer le package (machine avec internet)

### Methode 1 : Via l'application (recommandee)

1. Lancer DataForge Studio
2. Menu **Tools > Generate Offline Package**
3. Suivre la progression dans la console integree
4. Le package est genere dans `_packages/` avec le nom `DataForgeStudio_vX.Y.Z.7z`

### Methode 2 : Via le script (alternative CLI)

```powershell
# Depuis la racine du projet
_packages\prepare_package.bat
```

### Resultat

La generation produit :
- **`DataForgeStudio_vX.Y.Z.7z`** - Archive compressée prete a distribuer
- **`DataForgeStudio\`** - Dossier non compresse

Contenu du package :
- `src\` - Code source
- `.venv\` - Environnement Python complet
- `_python\` - Distribution Python embarquee
- `run.bat` - Lanceur de l'application
- `pyproject.toml`, `uv.lock` - Configuration

**Copier l'archive `.7z`** sur une cle USB ou un partage reseau interne.

---

## Etape 2 : Installer sur la machine cible (sans internet)

### 2.1 Extraire l'archive

Extraire `DataForgeStudio_vX.Y.Z.7z` vers l'emplacement souhaite, par exemple :
```
C:\Apps\DataForgeStudio\
```

### 2.2 Lancer l'application

Double-cliquer sur `run.bat`, ou :

```powershell
cd C:\Apps\DataForgeStudio
run.bat
```

> **Note** : Le package inclut Python, toutes les dependances et UV. Aucune installation prealable n'est necessaire sur la machine cible.

---

## Mise a jour

Pour mettre a jour sur une machine sans internet :

1. Sur la machine avec internet : mettre a jour le projet (`git pull && uv sync`) puis regenerer le package (via le menu Tools ou le script)
2. Copier la nouvelle archive `.7z` sur la machine cible et extraire (remplacer l'ancien dossier)

---

## Structure du package

```
DataForgeStudio\
├── src\                    # Code source
├── .venv\                  # Python + dependances (pret a l'emploi)
├── _python\                # Distribution Python embarquee
├── _AppConfig\             # Configuration application (themes, langues)
├── assets\                 # Ressources (icones, images)
├── docs\                   # Documentation
├── pyproject.toml          # Configuration projet
├── uv.lock                 # Versions des dependances
├── run.bat                 # Lanceur Windows
└── run.py                  # Point d'entree Python
```

---

## Troubleshooting

| Probleme | Solution |
|----------|----------|
| "Python not found" | Le .venv est corrompu, regenerer le package |
| Erreur de DLL | Verifier que la machine cible a la meme architecture (x64) |
| Application ne demarre pas | Lancer manuellement : `.venv\Scripts\python.exe run.py` |

---

*DataForge Studio - Guide d'installation offline*
