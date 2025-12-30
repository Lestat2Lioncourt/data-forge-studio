"""
Image Loader for DataForge Studio
Loads images and icons for PySide6 applications
"""

from pathlib import Path
from typing import Optional
import logging

from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QSize, Qt

logger = logging.getLogger(__name__)


class ImageLoader:
    """Singleton class for loading images and icons."""

    _instance = None
    _images_cache = {}

    def __init__(self):
        # Get images directory path
        self.images_dir = Path(__file__).parent.parent / "ui" / "assets" / "images"

        if not self.images_dir.exists():
            logger.warning(f"Images directory not found: {self.images_dir}")

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_image_path(self, image_name: str) -> Optional[Path]:
        """
        Get full path to an image file.

        Args:
            image_name: Name of the image file (with or without extension)

        Returns:
            Path to the image file, or None if not found
        """
        # Add .png extension if not present
        if not image_name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            image_name = f"{image_name}.png"

        image_path = self.images_dir / image_name

        if image_path.exists():
            return image_path
        else:
            logger.warning(f"Image not found: {image_path}")
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
        cache_key = f"{image_name}_{width}_{height}"

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
