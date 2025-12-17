# Icons Directory

Ce dossier contient les icônes embarquées pour le template.

## Icônes pour la barre de titre

Placez ici les icônes pour les boutons de la barre de titre :

- `minimize.png` - Bouton minimiser
- `maximize.png` - Bouton maximiser
- `restore.png` - Bouton restaurer (quand la fenêtre est maximisée)
- `close.png` - Bouton fermer
- `app_icon.png` - Icône de l'application (optionnel)

## Format recommandé

- **Format** : PNG avec transparence
- **Taille** : 16x16, 20x20 ou 24x24 pixels
- **Couleur** : Blanc ou couleur adaptée au thème sombre
- **Fond** : Transparent

## Utilisation

Les icônes sont automatiquement chargées via `resources.get_icon_path()`.

Exemple :
```python
from window_template.resources import get_icon_path

icon_path = get_icon_path("close.png")
if icon_path:
    button.setIcon(QIcon(icon_path))
```
