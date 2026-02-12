# Installation Offline - DataForge Studio

Ce guide explique comment installer DataForge Studio sur une machine **sans acces internet**.

---

## Prerequis

Une machine **avec internet** pour preparer le package (une seule fois).

---

## Etape 1 : Preparer le package (machine avec internet)

### 1.1 Installer UV et les dependances

```powershell
# Installer UV
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Cloner le projet
git clone https://github.com/Lestat2Lioncourt/data-forge-studio.git
cd data-forge-studio

# Installer toutes les dependances (cree le .venv)
uv sync
```

### 1.2 Executer le script de preparation

```powershell
# Genere le dossier _packages\DataForgeStudio\ et l'archive DataForgeStudio.7z
_packages\prepare_package.bat
```

### 1.3 Recuperer le package

Le script produit :
- **`DataForgeStudio.7z`** - Archive prete a distribuer
- **`DataForgeStudio\`** - Dossier non compresse

Contenu du package :
- `src\` - Code source
- `.venv\` - Environnement Python complet
- `_python\` - Distribution Python embarquee
- `uv.exe` - Binaire UV (optionnel)
- `run.bat` - Lanceur de l'application
- `pyproject.toml`, `uv.lock` - Configuration

**Copier l'archive `.7z`** sur une cle USB ou un partage reseau interne.

---

## Etape 2 : Installer sur la machine cible (sans internet)

### 2.1 Extraire l'archive

Extraire `DataForgeStudio.7z` vers l'emplacement souhaite, par exemple :
```
C:\Apps\DataForgeStudio\
```

### 2.2 Lancer l'application

```powershell
cd C:\Apps\DataForgeStudio
run.bat
```

Ou double-cliquer sur `run.bat`.

---

## Mise a jour

Pour mettre a jour sur une machine sans internet :

1. Sur la machine avec internet :
   ```powershell
   cd data-forge-studio
   git pull
   uv sync
   _packages\prepare_package.bat
   ```

2. Copier le nouveau `DataForgeStudio.7z` sur la machine cible et extraire (remplacer l'ancien dossier)

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
├── run.py                  # Point d'entree Python
└── uv.exe                  # Binaire UV (optionnel, pour futures MAJ)
```

---

## Troubleshooting

| Probleme | Solution |
|----------|----------|
| "Python not found" | Le .venv est corrompu, regenerer le package |
| Erreur de DLL | Verifier que la machine cible a la meme architecture (x64) |
| Application ne demarre pas | Lancer manuellement : `.venv\Scripts\python.exe run.py` |

---

*Genere pour DataForge Studio - Installation Offline*
