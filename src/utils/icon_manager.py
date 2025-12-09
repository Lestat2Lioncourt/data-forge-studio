"""
Icon Manager - Centralized icon loading with dynamic resizing
"""
from pathlib import Path
from typing import Optional, Dict, Tuple
import tkinter as tk

# PIL/Pillow for image processing
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not installed. Icons will not be available.")


class IconManager:
    """
    Gestionnaire centralisé des icônes avec redimensionnement dynamique

    Usage:
        # Initialisation (une seule fois au démarrage)
        IconManager.initialize()

        # Récupérer une icône redimensionnée
        icon = IconManager.get_icon("play", size=24)
        button = ttk.Button(frame, image=icon, text="Play", compound="left")

        # Garder une référence pour éviter le garbage collection
        button.image = icon
    """

    _icons_path: Optional[Path] = None
    _cache: Dict[Tuple[str, int], tk.PhotoImage] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls, custom_path: Optional[Path] = None):
        """
        Initialiser le gestionnaire d'icônes

        Args:
            custom_path: Chemin personnalisé vers le dossier icons
                        Si None, utilise assets/icons/ à la racine du projet
        """
        if custom_path:
            cls._icons_path = custom_path
        else:
            # Remonter de src/utils/ vers la racine puis assets/icons/
            project_root = Path(__file__).parent.parent.parent
            cls._icons_path = project_root / "assets" / "icons"

        # Créer le dossier s'il n'existe pas
        cls._icons_path.mkdir(parents=True, exist_ok=True)
        cls._initialized = True

        if not PIL_AVAILABLE:
            print(f"Warning: Icons path set to {cls._icons_path} but Pillow is not available")
        else:
            print(f"IconManager initialized. Icons path: {cls._icons_path}")

    @classmethod
    def get_icon(cls, name: str, size: int = 24, color: Optional[str] = None) -> Optional[tk.PhotoImage]:
        """
        Récupérer une icône avec redimensionnement automatique

        Args:
            name: Nom du fichier icône (sans extension)
            size: Taille désirée en pixels (défaut: 24)
            color: Couleur optionnelle pour teinter l'icône (futur)

        Returns:
            PhotoImage redimensionnée ou None si non disponible
        """
        if not cls._initialized:
            cls.initialize()

        if not PIL_AVAILABLE:
            return None

        # Vérifier le cache
        cache_key = (name, size, color)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # Chercher le fichier icône
        icon_path = cls._icons_path / f"{name}.png"

        if not icon_path.exists():
            print(f"Warning: Icon '{name}.png' not found in {cls._icons_path}")
            return None

        try:
            # Charger l'image source
            image = Image.open(icon_path)

            # Convertir en RGBA pour supporter la transparence
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            # Redimensionner avec antialiasing de qualité
            # LANCZOS est le meilleur algorithme pour downscaling
            resized = image.resize((size, size), Image.Resampling.LANCZOS)

            # Appliquer une couleur si demandé (futur feature)
            if color:
                # TODO: Implémenter le tinting
                pass

            # Convertir en PhotoImage pour Tkinter
            photo = ImageTk.PhotoImage(resized)

            # Mettre en cache
            cls._cache[cache_key] = photo

            return photo

        except Exception as e:
            print(f"Error loading icon '{name}': {e}")
            return None

    @classmethod
    def clear_cache(cls):
        """Vider le cache d'icônes (utile pour libérer de la mémoire)"""
        cls._cache.clear()

    @classmethod
    def preload_icons(cls, icon_names: list, sizes: list = None):
        """
        Précharger des icônes pour améliorer les performances

        Args:
            icon_names: Liste des noms d'icônes à précharger
            sizes: Liste des tailles à précharger (défaut: [16, 24, 32])
        """
        if sizes is None:
            sizes = [16, 24, 32]

        for name in icon_names:
            for size in sizes:
                cls.get_icon(name, size)

        print(f"Preloaded {len(icon_names)} icons in {len(sizes)} sizes")

    @classmethod
    def get_available_icons(cls) -> list:
        """Retourner la liste des icônes disponibles"""
        if not cls._initialized:
            cls.initialize()

        if not cls._icons_path.exists():
            return []

        return [f.stem for f in cls._icons_path.glob("*.png")]


# Fonction helper pour simplifier l'utilisation
def get_icon(name: str, size: int = 24) -> Optional[tk.PhotoImage]:
    """
    Raccourci pour récupérer une icône

    Usage:
        from utils.icon_manager import get_icon

        icon = get_icon("play", 24)
        button = ttk.Button(frame, image=icon, compound="left")
        button.image = icon  # Garder la référence !
    """
    return IconManager.get_icon(name, size)
