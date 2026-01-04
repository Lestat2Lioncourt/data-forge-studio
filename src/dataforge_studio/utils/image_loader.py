"""
Image Loader for DataForge Studio
Loads images and icons for PySide6 applications

Supports themed icons:
- Base icons (black + transparency) in ui/assets/icons/base/
- Automatically recolored for light/dark themes
- Falls back to legacy images in ui/assets/images/
"""

from pathlib import Path
from typing import Optional, Dict
import logging

from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class ImageLoader:
    """Singleton class for loading images and icons with theme support."""

    _instance = None
    _images_cache: Dict[str, QPixmap] = {}

    # Theme state
    _is_dark_theme: bool = True
    _icon_color: str = "#e0e0e0"  # Default for dark theme
    _theme_initialized: bool = False

    def __init__(self):
        # Get images directory path
        self.images_dir = Path(__file__).parent.parent / "ui" / "assets" / "images"
        self.icons_dir = Path(__file__).parent.parent / "ui" / "assets" / "icons"

        if not self.images_dir.exists():
            logger.warning(f"Images directory not found: {self.images_dir}")

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def update_theme(cls, theme_colors: dict):
        """
        Update theme settings from theme colors dict.

        Called by ThemeBridge when theme changes.

        Args:
            theme_colors: Dict with theme color values
        """
        cls._is_dark_theme = theme_colors.get('is_dark', True)
        # Icon color: use Icon_Color if defined, else derive from Frame_FG or text_primary
        cls._icon_color = theme_colors.get(
            'icon_color',
            theme_colors.get('frame_fg', theme_colors.get('text_primary', '#e0e0e0'))
        )
        cls._theme_initialized = True
        # Clear cache to force reload with new colors
        cls._images_cache.clear()

    def get_image_path(self, image_name: str, use_themed: bool = True) -> Optional[Path]:
        """
        Get full path to an image file.

        Tries themed icons first (from icons/base/ recolored), then falls back
        to legacy images folder.

        Args:
            image_name: Name of the image file (with or without extension)
            use_themed: If True, try to use themed icon first

        Returns:
            Path to the image file, or None if not found
        """
        # Add .png extension if not present
        if not image_name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            image_name = f"{image_name}.png"

        # Try themed icon first
        if use_themed:
            from ..ui.core.theme_image_generator import get_themed_icon_path
            themed_path = get_themed_icon_path(
                image_name,
                self._is_dark_theme,
                self._icon_color
            )
            if themed_path:
                return Path(themed_path)

        # Fallback to legacy images folder
        image_path = self.images_dir / image_name
        if image_path.exists():
            return image_path

        logger.warning(f"Image not found: {image_name}")
        return None

    def get_pixmap(self, image_name: str, width: Optional[int] = None,
                   height: Optional[int] = None) -> Optional[QPixmap]:
        """
        Get a QPixmap for an image, optionally scaled.

        Args:
            image_name: Name of the image file
            width: Target width (optional)
            height: Target height (optional)

        Returns:
            QPixmap object, or None if image not found
        """
        # Include theme variant in cache key
        theme_key = "dark" if self._is_dark_theme else "light"
        cache_key = f"{image_name}_{width}_{height}_{theme_key}"

        # Check cache
        if cache_key in self._images_cache:
            return self._images_cache[cache_key]

        # Load image
        image_path = self.get_image_path(image_name)
        if not image_path:
            return None

        pixmap = QPixmap(str(image_path))

        if pixmap.isNull():
            logger.warning(f"Failed to load image: {image_path}")
            return None

        # Scale if requested
        if width or height:
            if width and height:
                pixmap = pixmap.scaled(
                    width, height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            elif width:
                pixmap = pixmap.scaledToWidth(
                    width,
                    Qt.TransformationMode.SmoothTransformation
                )
            elif height:
                pixmap = pixmap.scaledToHeight(
                    height,
                    Qt.TransformationMode.SmoothTransformation
                )

        # Cache the result
        self._images_cache[cache_key] = pixmap

        return pixmap

    def get_icon(self, image_name: str, size: int = 24) -> Optional[QIcon]:
        """
        Get a QIcon for an image.

        Args:
            image_name: Name of the image file
            size: Icon size in pixels (default: 24)

        Returns:
            QIcon object, or None if image not found
        """
        pixmap = self.get_pixmap(image_name, width=size, height=size)

        if pixmap:
            return QIcon(pixmap)
        else:
            return None


# Convenience functions
_loader = None

def get_image_loader() -> ImageLoader:
    """Get the global ImageLoader instance."""
    global _loader
    if _loader is None:
        _loader = ImageLoader.get_instance()
    return _loader


def get_image_path(image_name: str) -> Optional[Path]:
    """Get path to an image file."""
    return get_image_loader().get_image_path(image_name)


def get_pixmap(image_name: str, width: Optional[int] = None,
               height: Optional[int] = None) -> Optional[QPixmap]:
    """Get a QPixmap for an image."""
    return get_image_loader().get_pixmap(image_name, width, height)


def get_icon(image_name: str, size: int = 24) -> Optional[QIcon]:
    """Get a QIcon for an image."""
    return get_image_loader().get_icon(image_name, size)


def get_database_icon(db_type: str, size: int = 16) -> Optional[QIcon]:
    """
    Get icon for a database type.

    Args:
        db_type: Database type (sqlite, sqlserver, postgresql, mysql, mongodb, oracle)
        size: Icon size in pixels

    Returns:
        QIcon for the database type, or None if not found
    """
    # Map database types to image file names
    db_icon_map = {
        "sqlite": "sqlite.png",
        "sqlserver": "sqlserver.png",
        "sql server": "sqlserver.png",
        "postgresql": "postgres.png",
        "postgres": "postgres.png",
        "mysql": "mysql.png",
        "mongodb": "mongodb.png",
        "mongo": "mongodb.png",
        "oracle": "Oracle.png"
    }

    image_name = db_icon_map.get(db_type.lower(), "database.png")
    return get_icon(image_name, size)
