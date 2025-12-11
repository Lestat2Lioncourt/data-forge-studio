"""
Theme Manager - Centralized theme management for the application
"""
from typing import Dict, Any, Optional
import logging
import json
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class Theme:
    """Represents a visual theme with color definitions"""

    def __init__(self, name: str, display_name: str, colors: Dict[str, str]):
        self.name = name
        self.display_name = display_name
        self.colors = colors

    def get(self, key: str, default: str = "#000000") -> str:
        """Get a color value by key"""
        return self.colors.get(key, default)


class ThemeManager:
    """
    Manages application themes and provides color values

    All themes are loaded from JSON files in _AppConfig/themes/
    """

    _instance: Optional['ThemeManager'] = None

    def __init__(self):
        """Initialize theme manager - loads all themes from JSON files"""
        self._current_theme_name = 'classic_light'
        self._observers = []  # Widgets that need to be notified of theme changes
        self._themes_dir = self._get_themes_dir()
        self.THEMES = {}  # Will be populated from JSON files
        self._load_all_themes()

        # Set current theme
        if self._current_theme_name in self.THEMES:
            self._current_theme = self.THEMES[self._current_theme_name]
        else:
            # Fallback to first available theme
            if self.THEMES:
                self._current_theme_name = list(self.THEMES.keys())[0]
                self._current_theme = self.THEMES[self._current_theme_name]
            else:
                logger.error("No themes found! Application may not display correctly.")
                # Create a minimal fallback theme
                self._current_theme = Theme('fallback', 'Fallback', {})

        logger.info(f"ThemeManager initialized with theme: {self._current_theme_name}")

    @classmethod
    def get_instance(cls) -> 'ThemeManager':
        """Get singleton instance of ThemeManager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_current_theme(self) -> Theme:
        """Get the current active theme"""
        return self._current_theme

    def get_current_theme_name(self) -> str:
        """Get the name of the current theme"""
        return self._current_theme_name

    def get_available_themes(self) -> Dict[str, str]:
        """Get dictionary of theme names to display names"""
        return {name: theme.display_name for name, theme in self.THEMES.items()}

    def set_theme(self, theme_name: str):
        """
        Change the current theme

        Args:
            theme_name: Name of the theme to activate
        """
        if theme_name not in self.THEMES:
            logger.warning(f"Unknown theme: {theme_name}, keeping current theme")
            return

        self._current_theme_name = theme_name
        self._current_theme = self.THEMES[theme_name]
        logger.info(f"Theme changed to: {theme_name}")

        # Notify all observers
        self._notify_observers()

    def get_color(self, key: str, default: str = "#000000") -> str:
        """
        Get a color value from the current theme

        Args:
            key: Color key (e.g., 'bg', 'fg', 'select_bg')
            default: Default color if key not found

        Returns:
            Color hex string
        """
        return self._current_theme.get(key, default)

    def register_observer(self, callback):
        """
        Register a callback to be notified when theme changes

        Args:
            callback: Function to call when theme changes (no arguments)
        """
        if callback not in self._observers:
            self._observers.append(callback)
            logger.debug(f"Registered theme observer: {callback}")

    def unregister_observer(self, callback):
        """
        Unregister a theme change observer

        Args:
            callback: Previously registered callback
        """
        if callback in self._observers:
            self._observers.remove(callback)
            logger.debug(f"Unregistered theme observer: {callback}")

    def _notify_observers(self):
        """Notify all registered observers of theme change"""
        logger.info(f"Notifying {len(self._observers)} theme observers")
        for callback in self._observers:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error notifying theme observer {callback}: {e}")

    def _get_themes_dir(self) -> Path:
        """Get the directory for storing themes"""
        # Get the application config directory
        app_dir = Path.cwd()
        themes_dir = app_dir / "_AppConfig" / "themes"

        # Create directory if it doesn't exist
        themes_dir.mkdir(parents=True, exist_ok=True)

        # Ensure default themes are present
        self._ensure_default_themes(themes_dir)

        return themes_dir

    def _ensure_default_themes(self, themes_dir: Path):
        """
        Copy default themes to _AppConfig/themes if they don't exist

        Args:
            themes_dir: Path to the themes directory
        """
        # Check if themes directory is empty or missing default themes
        existing_themes = list(themes_dir.glob("*.json"))

        if len(existing_themes) == 0:
            logger.info("No themes found, copying default themes...")

            # Get path to default themes (shipped with the application)
            # The default_themes folder is in src/default_themes/
            src_dir = Path(__file__).parent.parent  # Go up to src/
            default_themes_dir = src_dir / "default_themes"

            if not default_themes_dir.exists():
                logger.error(f"Default themes directory not found: {default_themes_dir}")
                return

            # Copy all JSON theme files
            theme_files = list(default_themes_dir.glob("*.json"))
            if not theme_files:
                logger.warning(f"No default theme files found in {default_themes_dir}")
                return

            for theme_file in theme_files:
                try:
                    dest_file = themes_dir / theme_file.name
                    shutil.copy2(theme_file, dest_file)
                    logger.info(f"Copied default theme: {theme_file.name}")
                except Exception as e:
                    logger.error(f"Error copying theme {theme_file.name}: {e}")

            logger.info(f"Copied {len(theme_files)} default theme(s)")

    def _load_all_themes(self):
        """Load all themes from JSON files"""
        try:
            theme_files = list(self._themes_dir.glob("*.json"))

            if not theme_files:
                logger.warning(f"No theme files found in {self._themes_dir}")
                return

            for theme_file in theme_files:
                theme_name = theme_file.stem
                try:
                    with open(theme_file, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)

                    # Create theme object and add to THEMES
                    display_name = theme_data.get('display_name', theme_name)
                    colors = theme_data.get('colors', {})

                    theme = Theme(theme_name, display_name, colors)
                    self.THEMES[theme_name] = theme

                    logger.info(f"Loaded theme: {theme_name}")

                except Exception as e:
                    logger.error(f"Error loading theme {theme_name}: {e}")

            logger.info(f"Total themes loaded: {len(self.THEMES)}")

        except Exception as e:
            logger.error(f"Error loading themes: {e}")

    def load_theme_from_file(self, theme_name: str) -> Dict[str, str]:
        """
        Load a theme from disk

        Args:
            theme_name: Name of the theme to load

        Returns:
            Dictionary of color values
        """
        theme_file = self._themes_dir / f"{theme_name}.json"

        if not theme_file.exists():
            logger.warning(f"Theme file not found: {theme_file}")
            return {}

        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)

            return theme_data.get('colors', {})

        except Exception as e:
            logger.error(f"Error loading theme {theme_name}: {e}")
            return {}

    def save_theme(self, theme_name: str, colors: Dict[str, str], display_name: str = None):
        """
        Save a theme to disk

        Args:
            theme_name: Name of the theme
            colors: Dictionary of color values
            display_name: Optional display name (defaults to formatted theme_name)
        """
        theme_file = self._themes_dir / f"{theme_name}.json"

        # Prepare theme data
        if not display_name:
            display_name = theme_name.replace('_', ' ').title()

        theme_data = {
            'name': theme_name,
            'display_name': display_name,
            'colors': colors
        }

        try:
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved theme: {theme_name} to {theme_file}")

            # Reload theme in memory
            theme = Theme(theme_name, display_name, colors)
            self.THEMES[theme_name] = theme

        except Exception as e:
            logger.error(f"Error saving theme {theme_name}: {e}")
            raise

    def create_theme(self, theme_name: str, colors: Dict[str, str], display_name: str = None, apply_now: bool = False):
        """
        Create a theme in memory and optionally save to disk

        Args:
            theme_name: Name of the theme
            colors: Dictionary of color values
            display_name: Optional display name
            apply_now: Whether to apply the theme immediately
        """
        if not display_name:
            display_name = theme_name.replace('_', ' ').title()

        theme = Theme(theme_name, display_name, colors)
        self.THEMES[theme_name] = theme

        logger.info(f"Created theme: {theme_name}")

        if apply_now:
            self.set_theme(theme_name)

    def delete_theme(self, theme_name: str):
        """
        Delete a theme

        Args:
            theme_name: Name of the theme to delete
        """
        # Don't allow deleting built-in themes
        if theme_name in ['classic_light', 'dark_professional', 'azure_blue']:
            logger.warning(f"Cannot delete built-in theme: {theme_name}")
            return False

        # Remove from memory
        if theme_name in self.THEMES:
            del self.THEMES[theme_name]

        # Remove from disk
        theme_file = self._themes_dir / f"{theme_name}.json"
        if theme_file.exists():
            try:
                theme_file.unlink()
                logger.info(f"Deleted theme: {theme_name}")
                return True
            except Exception as e:
                logger.error(f"Error deleting theme file {theme_name}: {e}")
                return False

        return True


# Convenience function for global access
def get_theme_manager() -> ThemeManager:
    """Get the global ThemeManager instance"""
    return ThemeManager.get_instance()
