# Icons Directory

Ce dossier contient les icônes de l'application.

## 📋 Format

- **Format** : PNG avec transparence alpha
- **Taille source recommandée** : 256x256 ou 512x512 pixels
- **Redimensionnement** : Automatique via `IconManager`

## 🎨 Icônes Disponibles

Placez vos fichiers PNG directement dans ce dossier :

```
assets/icons/
├── play.png           # Exécuter une requête
├── stop.png           # Arrêter l'exécution
├── save.png           # Sauvegarder
├── refresh.png        # Rafraîchir
├── database.png       # Base de données
├── table.png          # Table
├── column.png         # Colonne
├── add.png            # Ajouter
├── edit.png           # Éditer
├── delete.png         # Supprimer
├── copy.png           # Copier
├── export.png         # Exporter
├── settings.png       # Paramètres
└── help.png           # Aide
```

## 💡 Utilisation dans le Code

```python
from utils.icon_manager import get_icon

# Dans votre classe GUI
def create_button(self):
    # Récupérer une icône (redimensionnée automatiquement)
    icon = get_icon("play", size=24)

    # Créer le bouton avec icône et texte
    button = ttk.Button(
        frame,
        image=icon,
        text="Execute",
        compound="left"  # Icône à gauche du texte
    )

    # IMPORTANT: Garder une référence pour éviter le garbage collection
    button.image = icon

    return button
```

## 🔍 Sources d'Icônes Recommandées

### Open Source & Gratuites

1. **[Feather Icons](https://feathericons.com/)** ⭐ Recommandé
   - Minimaliste et moderne
   - Format SVG (convertir en PNG 256x256)
   - Licence MIT

2. **[Material Icons](https://fonts.google.com/icons)**
   - Google Material Design
   - Très complet
   - Licence Apache 2.0

3. **[Lucide](https://lucide.dev/)**
   - Fork de Feather avec plus d'icônes
   - Format SVG
   - Licence ISC

4. **[Tabler Icons](https://tabler-icons.io/)**
   - 4000+ icônes
   - Style cohérent
   - Licence MIT

### Conversion SVG → PNG

Si vous téléchargez des SVG, convertissez-les en PNG 256x256 :

**En ligne** :
- [CloudConvert](https://cloudconvert.com/svg-to-png)
- [SVG to PNG Converter](https://svgtopng.com/)

**Ligne de commande** (avec Inkscape) :
```bash
inkscape icon.svg -w 256 -h 256 -o icon.png
```

**Python** (avec cairosvg) :
```bash
pip install cairosvg
cairosvg icon.svg -o icon.png -W 256 -H 256
```

## 📐 Tailles Utilisées

L'`IconManager` redimensionne automatiquement, mais voici les tailles courantes :

- **16x16** : Menu items, petits indicateurs
- **24x24** : Boutons normaux (par défaut) ⭐
- **32x32** : Gros boutons, toolbar principale
- **48x48** : Headers, titres de sections

## ⚠️ Important

- **Nommage** : Utilisez des noms descriptifs en snake_case
  - ✅ `execute_query.png`, `save_file.png`
  - ❌ `icon1.png`, `img.png`

- **Transparence** : Assurez-vous que vos PNG ont un canal alpha

- **Cohérence** : Utilisez le même style pour toutes vos icônes

## 🎨 Exemple de Palette pour Cohérence

Si vous créez vos propres icônes :
- **Stroke width** : 2px
- **Couleur principale** : #2c3e50 (gris foncé)
- **Fond** : Transparent
- **Corner radius** : 2px
