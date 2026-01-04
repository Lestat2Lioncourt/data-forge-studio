"""
Theme System for DataForge Studio

A simplified, palette-based theme system that generates complete themes
from a minimal set of user-defined colors.

Usage:
    from dataforge_studio.core.theme import ThemePalette, ThemeManager

    # Create a palette
    palette = ThemePalette(
        name="My Theme",
        background="#1e1e1e",
        surface="#2d2d2d",
        border="#3d3d3d",
        accent="#0078d7",
        text="#e0e0e0",
        text_secondary="#808080",
        info="#3498db",
        warning="#f39c12",
        error="#e74c3c",
        important="#9b59b6"
    )

    # Get the theme manager and apply
    manager = ThemeManager.instance()
    manager.apply_palette(palette)
"""

from .palette import ThemePalette, DEFAULT_DARK_PALETTE, DEFAULT_LIGHT_PALETTE
from .generator import ThemeGenerator, GeneratedTheme
from .manager import ThemeManager
from .adapter import LegacyThemeAdapter, new_to_legacy_colors, legacy_to_palette
from .preview_widget import ThemePreviewWidget
from .editor_dialog import ThemeEditorDialog

__all__ = [
    # Core classes
    "ThemePalette",
    "ThemeGenerator",
    "GeneratedTheme",
    "ThemeManager",
    # Default palettes
    "DEFAULT_DARK_PALETTE",
    "DEFAULT_LIGHT_PALETTE",
    # Migration helpers
    "LegacyThemeAdapter",
    "new_to_legacy_colors",
    "legacy_to_palette",
    # UI components
    "ThemePreviewWidget",
    "ThemeEditorDialog",
]
