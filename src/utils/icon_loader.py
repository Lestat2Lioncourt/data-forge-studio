"""
Icon Loader - Load and resize icons for TreeView
"""
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
from typing import Dict, Optional
from .logger import logger


class IconLoader:
    """Load and manage icons for the application"""

    def __init__(self, icon_size: int = 16):
        """
        Initialize icon loader

        Args:
            icon_size: Target size for icons (default 16x16)
        """
        self.icon_size = icon_size
        self.icons: Dict[str, tk.PhotoImage] = {}
        self.icon_dir = Path(__file__).parent.parent.parent / "assets" / "icons"

    def load_icon(self, name: str, filename: Optional[str] = None) -> Optional[tk.PhotoImage]:
        """
        Load and resize an icon

        Args:
            name: Icon identifier (e.g., 'postgres', 'mysql')
            filename: Optional custom filename (defaults to f"{name}.png")

        Returns:
            PhotoImage object or None if loading failed
        """
        # Return cached icon if available
        if name in self.icons:
            return self.icons[name]

        # Determine file path
        if filename is None:
            filename = f"{name}.png"

        icon_path = self.icon_dir / filename

        # Try alternate extensions if .png not found
        if not icon_path.exists():
            for ext in ['.jpg', '.jpeg', '.gif', '.bmp']:
                alt_path = self.icon_dir / f"{name}{ext}"
                if alt_path.exists():
                    icon_path = alt_path
                    break

        if not icon_path.exists():
            logger.warning(f"Icon not found: {icon_path}")
            return None

        try:
            # Open and resize image
            img = Image.open(icon_path)

            # Resize maintaining aspect ratio
            img.thumbnail((self.icon_size, self.icon_size), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)

            # Cache the icon
            self.icons[name] = photo

            logger.info(f"Loaded icon: {name} from {icon_path}")
            return photo

        except Exception as e:
            logger.error(f"Error loading icon {icon_path}: {e}")
            return None

    def load_database_icon(self, db_type: str) -> Optional[tk.PhotoImage]:
        """
        Load icon for a specific database type

        Args:
            db_type: Database type (e.g., 'PostgreSQL', 'MySQL', 'SQLite')

        Returns:
            PhotoImage object or generic database icon if not found
        """
        # Normalize database type name
        db_type_lower = db_type.lower().replace(" ", "")

        # Try to load specific icon
        icon = self.load_icon(db_type_lower)

        if icon is None:
            # Try alternate names
            alternate_names = {
                'postgresql': 'postgres',
                'mssql': 'sqlserver',
                'sql server': 'sqlserver',
                'mariadb': 'mysql'
            }

            alt_name = alternate_names.get(db_type_lower)
            if alt_name:
                icon = self.load_icon(alt_name)

        if icon is None:
            # Fallback to generic database icon
            icon = self.load_icon('databases', 'databases.jpg')

        return icon

    def load_folder_icon(self) -> Optional[tk.PhotoImage]:
        """Load folder icon"""
        return self.load_icon('rootfolders', 'RootFolders.png')

    def load_databases_section_icon(self) -> Optional[tk.PhotoImage]:
        """Load databases section icon"""
        return self.load_icon('databases', 'databases.jpg')

    def load_rootfolders_section_icon(self) -> Optional[tk.PhotoImage]:
        """Load rootfolders section icon"""
        return self.load_icon('rootfolders', 'RootFolders.png')

    def preload_all(self):
        """Preload all common icons"""
        # Database icons
        db_types = ['postgres', 'mysql', 'sqlite', 'sqlserver', 'oracle', 'mongodb']
        for db_type in db_types:
            self.load_icon(db_type)

        # Generic icons
        self.load_icon('databases', 'databases.jpg')
        self.load_icon('rootfolders', 'RootFolders.png')

        logger.info(f"Preloaded {len(self.icons)} icons")


# Global icon loader instance
icon_loader = IconLoader(icon_size=16)
