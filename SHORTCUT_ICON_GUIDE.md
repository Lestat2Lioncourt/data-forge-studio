# Guide : Icône et Raccourci Bureau
## DataForge Studio v0.50

---

## 📋 Vue d'ensemble

Ce guide explique comment gérer l'icône de l'application et créer un raccourci bureau pour DataForge Studio.

---

## 🎨 Icône de l'application

### Emplacement

L'icône de l'application se trouve à :
```
src/dataforge_studio/ui/assets/images/DataForge Studio.ico
```

### Utilisation

L'icône est utilisée pour :
- **Barre des tâches Windows** : Affichée quand l'application est lancée
- **Fenêtre de l'application** : Coin supérieur gauche (si supporté)
- **Raccourci bureau** : Icône du fichier .lnk
- **Alt+Tab** : Miniature de l'application

### Remplacement de l'icône

Pour remplacer l'icône par une nouvelle version :

1. **Créer une nouvelle icône** :
   - Format : `.ico` (Windows Icon)
   - Tailles recommandées incluses dans le .ico :
     - 16×16 pixels (menu système)
     - 32×32 pixels (barre des tâches)
     - 48×48 pixels (icônes moyennes)
     - 256×256 pixels (haute résolution)
   - Style : Simplifié, contraste élevé, peu de détails
   - Fond : Transparent

2. **Remplacer le fichier** :
   ```bash
   # Copier la nouvelle icône
   cp nouvelle_icone.ico "src/dataforge_studio/ui/assets/images/DataForge Studio.ico"
   ```

3. **Mettre à jour le raccourci bureau** :
   ```bash
   uv run python create_shortcut.py
   ```

### Conversion PNG → ICO (optionnel)

Si vous avez seulement un fichier PNG, le script `create_shortcut.py` peut le convertir automatiquement en .ico :

```bash
# Placer le PNG à :
# src/dataforge_studio/ui/assets/images/DataForge Studio.png

# Lancer la conversion et création du raccourci
uv run python create_shortcut.py
```

**Note** : La conversion nécessite la bibliothèque `Pillow` (déjà incluse dans les dépendances).

---

## 🖱️ Raccourci Bureau

### Création automatique

Le script `create_shortcut.py` crée automatiquement :
1. Un fichier batch `DataForgeStudio.bat` pour lancer l'application
2. Un raccourci `.lnk` sur le bureau avec l'icône

**Commande** :
```bash
uv run python create_shortcut.py
```

**Résultat** :
```
✓ Fichier batch créé : DataForgeStudio.bat
✓ Raccourci créé : C:\Users\Public\Desktop\DataForgeStudio.lnk
```

### Emplacement du raccourci

Le raccourci est créé dans le **bureau public** de Windows :
- `C:\Users\Public\Desktop\DataForgeStudio.lnk`

Cela permet à tous les utilisateurs de la machine d'accéder au raccourci.

### Utilisation

1. **Double-clic** sur le raccourci pour lancer l'application
2. **Clic droit** → "Épingler à la barre des tâches" pour un accès rapide
3. **Clic droit** → "Épingler à l'écran de démarrage" (Windows 10/11)

### Suppression du raccourci

Pour supprimer le raccourci :
```bash
# Windows
del "C:\Users\Public\Desktop\DataForgeStudio.lnk"

# Ou directement depuis l'explorateur
# Clic droit > Supprimer
```

---

## 🔧 Configuration avancée

### Fichier batch de lancement

Le fichier `DataForgeStudio.bat` contient :
```batch
@echo off
cd /d "D:\DEV\Python\data-forge-studio"
".venv\Scripts\pythonw.exe" run.py
```

**Important** : Le script utilise `pythonw.exe` au lieu de `python.exe` pour **masquer la fenêtre console**. Ceci est la méthode standard pour les applications GUI Python.

**Multi-plateforme** : Sur Linux/macOS, l'équivalent est `pythonw` (sans extension .exe).

Vous pouvez le modifier pour :
- Ajouter des paramètres de lancement : `pythonw.exe run.py --debug`
- Configurer des variables d'environnement
- Rediriger les logs vers un fichier : `pythonw.exe run.py > app.log 2>&1`

### Modification du raccourci

Pour modifier manuellement le raccourci :
1. **Clic droit** sur le raccourci → **Propriétés**
2. Modifier :
   - **Cible** : Commande à exécuter
   - **Démarrer dans** : Répertoire de travail
   - **Icône** : Changer l'icône
   - **Raccourci clavier** : Ajouter un raccourci (ex: Ctrl+Alt+D)
   - **Fenêtre** : Normale, Réduite, Agrandie

---

## 💡 Console vs Pas de Console

### Pourquoi pas de console ?

**Par défaut, le raccourci lance l'application SANS fenêtre console** (fenêtre noire DOS).

**Avantages** :
- ✅ Interface propre et professionnelle
- ✅ Pas de fenêtre noire qui reste ouverte en arrière-plan
- ✅ Expérience utilisateur standard pour une application GUI

**Inconvénient** :
- ⚠️ Les messages de démarrage et d'erreur ne sont plus visibles dans la console

### Voir les logs malgré tout

Si vous avez besoin de voir les logs pour débugger :

**Option 1 : Lancer avec console pour debug**
```batch
# Éditer DataForgeStudio.bat et remplacer pythonw.exe par python.exe
".venv\Scripts\python.exe" run.py
```

**Option 2 : Lancer depuis terminal (recommandé pour debug)**
```bash
# Ouvrir un terminal dans le projet
cd "D:\DEV\Python\data-forge-studio"
uv run run.py
```

**Option 3 : Vérifier les fichiers de log**
L'application utilise le module `logger.py` qui écrit dans des fichiers de log (vérifier `_AppLogs/` ou selon configuration).

---

## 🐛 Dépannage

### L'icône n'apparaît pas dans la barre des tâches

**Vérifications** :

1. **Fichier .ico existe** :
   ```bash
   # Vérifier la présence du fichier
   ls "src/dataforge_studio/ui/assets/images/DataForge Studio.ico"
   ```

2. **Message console** :
   Lancer l'application et vérifier le message :
   ```
   Application icon loaded: D:\...\DataForge Studio.ico
   ```

3. **Cache Windows** :
   Parfois Windows met en cache les anciennes icônes. Pour forcer le rafraîchissement :
   - Redémarrer l'explorateur Windows
   - Ou redémarrer le PC

### Le raccourci ne se crée pas

**Erreurs possibles** :

1. **pywin32 non installé** :
   ```bash
   uv sync
   ```

2. **Permissions insuffisantes** :
   Lancer le terminal en **Administrateur** et réessayer

3. **Bureau introuvable** :
   Le script cherche dans plusieurs emplacements. Vérifier les chemins :
   - `C:\Users\Public\Desktop`
   - `C:\Users\[VotreNom]\Desktop`
   - `C:\Users\[VotreNom]\Bureau` (Windows français)

### Le raccourci lance l'application mais sans icône

1. **Vérifier l'icône dans les propriétés** :
   - Clic droit sur le raccourci → Propriétés → Changer l'icône
   - Vérifier que le chemin pointe vers le bon fichier .ico

2. **Recréer le raccourci** :
   ```bash
   # Supprimer l'ancien
   del "C:\Users\Public\Desktop\DataForgeStudio.lnk"

   # Recréer
   uv run python create_shortcut.py
   ```

---

## 📦 Distribution

### Pour partager l'application avec l'icône

Si vous distribuez l'application à d'autres utilisateurs :

1. **Inclure le fichier .ico** dans le package
2. **Fournir le script** `create_shortcut.py`
3. **Instructions** :
   ```bash
   # Installation
   uv sync

   # Créer le raccourci
   uv run python create_shortcut.py
   ```

### Création d'un installeur (futur)

Pour une distribution professionnelle, envisager :
- **PyInstaller** : Créer un .exe avec l'icône intégrée
- **Inno Setup** : Créer un installeur Windows
- **NSIS** : Alternative pour les installeurs

---

## 🎯 Recommandations pour l'icône

### Design

- **Simplicité** : Éviter trop de détails (illisible en 16×16)
- **Contraste** : Couleurs contrastées pour bien voir sur fond clair/sombre
- **Symbole clair** : Reconnaissable instantanément
- **Cohérence** : Garder le même style que le logo principal

### Exemples de bonnes icônes

- **Lettre "D"** stylisée avec une base de données
- **Symbole de base de données** (cylindre) simplifié
- **Engrenage + DB** pour "data forge"
- **Table/grille** stylisée

### Outils recommandés

- **GIMP** : Gratuit, export .ico natif
- **Paint.NET** : Gratuit, avec plugin ICO
- **Greenfish Icon Editor** : Gratuit, spécialisé icônes
- **IcoFX** : Payant, professionnel
- **Convertisseurs en ligne** :
  - https://convertio.co/png-ico/
  - https://www.icoconverter.com/

---

## ✅ Checklist

Avant de publier une nouvelle version :

- [ ] Icône .ico finalisée et optimisée pour petit format
- [ ] Icône testée en 16×16, 32×32, 48×48, 256×256
- [ ] Icône visible dans la barre des tâches
- [ ] Raccourci bureau créé et fonctionnel
- [ ] Raccourci épinglable à la barre des tâches
- [ ] Icône cohérente avec l'identité visuelle
- [ ] Documentation à jour

---

## 📞 Support

En cas de problème :
1. Vérifier les messages d'erreur dans la console
2. Consulter la section **Dépannage** ci-dessus
3. Ouvrir une issue sur GitHub : https://github.com/Lestat2Lioncourt/data-forge-studio/issues

---

*Guide créé le 2025-12-12 pour DataForge Studio v0.50*
