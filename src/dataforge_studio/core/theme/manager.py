"""
Theme Manager - Central theme management singleton.

Handles:
- Loading and saving themes/palettes
- Theme generation from palettes
- Observer pattern for theme changes
- QSS application to the application
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional
import json

from PySide6.QtWidgets import QApplication

from .palette import ThemePalette, DEFAULT_DARK_PALETTE, DEFAULT_LIGHT_PALETTE
from .generator import ThemeGenerator, GeneratedTheme


class ThemeManager:
    """
    Singleton manager for application theming.

    Usage:
        manager = ThemeManager.instance()
        manager.apply_palette(my_palette)

        # Or use a built-in theme
        manager.apply_dark_theme()
        manager.apply_light_theme()

        # Register for theme changes
        manager.register_observer(my_callback)
    """

    _instance: Optional["ThemeManager"] = None

    def __init__(self):
        """Initialize the theme manager."""
        if ThemeManager._instance is not None:
            raise RuntimeError("Use ThemeManager.instance() instead")

        self._generator = ThemeGenerator()
        self._current_theme: Optional[GeneratedTheme] = None
        self._current_palette: Optional[ThemePalette] = None
        self._observers: List[Callable[[Dict[str, str]], None]] = []
        self._qss_builder = None  # Lazy import to avoid circular deps

    @classmethod
    def instance(cls) -> "ThemeManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (mainly for testing)."""
        cls._instance = None

    # === THEME APPLICATION ===

    def apply_palette(self, palette: ThemePalette, apply_qss: bool = True) -> GeneratedTheme:
        """
        Apply a palette as the current theme.

        Args:
            palette: The palette to apply
            apply_qss: Whether to apply QSS to the application (default True)

        Returns:
            The generated theme
        """
        self._current_palette = palette
        self._current_theme = self._generator.generate(palette)

        if apply_qss:
            self._apply_qss()

        # Notify observers
        self._notify_observers()

        return self._current_theme

    def apply_dark_theme(self) -> GeneratedTheme:
        """Apply the default dark theme."""
        return self.apply_palette(DEFAULT_DARK_PALETTE)

    def apply_light_theme(self) -> GeneratedTheme:
        """Apply the default light theme."""
        return self.apply_palette(DEFAULT_LIGHT_PALETTE)

    def refresh(self) -> None:
        """Re-apply the current theme (useful after widget changes)."""
        if self._current_palette:
            self.apply_palette(self._current_palette)

    # === QSS APPLICATION ===

    def _apply_qss(self) -> None:
        """Apply QSS to the application."""
        if self._current_theme is None:
            return

        app = QApplication.instance()
        if app is None:
            return

        # Lazy import QSS builder
        if self._qss_builder is None:
            from .qss_builder import QSSBuilder
            self._qss_builder = QSSBuilder()

        qss = self._qss_builder.build(self._current_theme)
        app.setStyleSheet(qss)

    def get_qss(self) -> str:
        """Get the current QSS without applying it."""
        if self._current_theme is None:
            return ""

        if self._qss_builder is None:
            from .qss_builder import QSSBuilder
            self._qss_builder = QSSBuilder()

        return self._qss_builder.build(self._current_theme)

    # === OBSERVERS ===

    def register_observer(self, callback: Callable[[Dict[str, str]], None]) -> None:
        """
        Register a callback to be notified of theme changes.

        Args:
            callback: Function that receives the theme colors dict
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def unregister_observer(self, callback: Callable[[Dict[str, str]], None]) -> None:
        """
        Unregister a theme change callback.

        Args:
            callback: The callback to remove
        """
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self) -> None:
        """Notify all observers of theme change."""
        if self._current_theme is None:
            return

        colors = self._current_theme.colors
        for callback in self._observers:
            try:
                callback(colors)
            except Exception as e:
                # Log but don't fail on observer errors
                print(f"Theme observer error: {e}")

    # === GETTERS ===

    @property
    def current_theme(self) -> Optional[GeneratedTheme]:
        """Get the current generated theme."""
        return self._current_theme

    @property
    def current_palette(self) -> Optional[ThemePalette]:
        """Get the current palette."""
        return self._current_palette

    @property
    def is_dark(self) -> bool:
        """Check if current theme is dark."""
        if self._current_theme:
            return self._current_theme.is_dark
        return True  # Default to dark

    def get_color(self, key: str, default: str = "#000000") -> str:
        """
        Get a color from the current theme.

        Args:
            key: Color key (e.g., "text_primary", "accent")
            default: Default color if key not found

        Returns:
            Color value
        """
        if self._current_theme:
            return self._current_theme.get(key, default)
        return default

    def get_colors(self) -> Dict[str, str]:
        """Get all colors from the current theme."""
        if self._current_theme:
            return self._current_theme.colors.copy()
        return {}

    # === PERSISTENCE ===

    def save_palette(self, path: Path) -> None:
        """
        Save the current palette to a file.

        Args:
            path: Path to save to (JSON format)
        """
        if self._current_palette:
            self._current_palette.save(path)

    def load_palette(self, path: Path, apply: bool = True) -> ThemePalette:
        """
        Load a palette from a file.

        Args:
            path: Path to load from
            apply: Whether to apply the palette immediately

        Returns:
            The loaded palette
        """
        palette = ThemePalette.load(path)
        if apply:
            self.apply_palette(palette)
        return palette

    def save_theme(self, path: Path) -> None:
        """
        Save the full generated theme to a file.

        Args:
            path: Path to save to (JSON format)
        """
        if self._current_theme:
            data = {
                "name": self._current_theme.name,
                "is_dark": self._current_theme.is_dark,
                "colors": self._current_theme.colors,
                "source_palette": self._current_palette.to_dict() if self._current_palette else None,
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    # === UTILITY ===

    def preview_palette(self, palette: ThemePalette) -> GeneratedTheme:
        """
        Generate a theme preview without applying it.

        Useful for theme editors to show what a palette would look like.

        Args:
            palette: The palette to preview

        Returns:
            The generated theme (not applied)
        """
        return self._generator.generate(palette)
