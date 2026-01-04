"""
Theme Adapter - Bridge between new theme system and legacy ThemeBridge.

This adapter allows gradual migration from the old theme system to the new one.
It provides backwards compatibility while enabling new code to use the new system.

Usage during migration:
    # Old way (still works)
    from dataforge_studio.ui.core.theme_bridge import ThemeBridge
    theme = ThemeBridge.get_instance()
    colors = theme.get_theme_colors()

    # New way (recommended)
    from dataforge_studio.core.theme import ThemeManager
    manager = ThemeManager.instance()
    colors = manager.get_colors()

The adapter can convert between the two color key formats:
- Legacy keys: TopBar_BG, Frame_BG, Data_BG, etc.
- New keys: topbar_bg, panel_bg, surface_bg, etc.
"""

from typing import Dict

from .palette import ThemePalette
from .generator import GeneratedTheme


# Mapping from legacy keys to new keys
LEGACY_TO_NEW_KEYS = {
    # Window/Frame
    "TopBar_BG": "topbar_bg",
    "TopBar_FG": "topbar_fg",
    "MenuBar_BG": "menubar_bg",
    "MenuBar_FG": "menubar_fg",
    "StatusBar_BG": "statusbar_bg",
    "StatusBar_FG": "statusbar_fg",
    "Frame_BG": "panel_bg",
    "Frame_FG": "text_primary",
    "Frame_FG_Secondary": "text_secondary",

    # Data areas
    "Data_BG": "surface_bg",
    "Data_FG": "text_primary",
    "Data_Border": "border_color",

    # Interactions
    "Hover_BG": "hover_bg",
    "Selected_BG": "selected_bg",
    "Selected_FG": "selected_fg",
    "Accent": "accent",

    # Text colors
    "Normal_FG": "text_primary",
    "Success_FG": "info",  # Legacy used success, now we use info
    "Warning_FG": "warning",
    "Error_FG": "error",
    "Info_FG": "info",

    # Input
    "input_bg": "input_bg",
    "input_fg": "input_fg",
    "input_border": "input_border",
    "input_focus_border": "input_focus_border",

    # Tree
    "tree_line1_bg": "tree_line1_bg",
    "tree_line1_fg": "tree_line1_fg",
    "tree_line2_bg": "tree_line2_bg",
    "tree_line2_fg": "tree_line2_fg",
    "tree_selected_bg": "tree_selected_bg",
    "tree_selected_fg": "tree_selected_fg",
    "tree_hover_bg": "tree_hover_bg",
    "tree_heading_bg": "tree_header_bg",
    "tree_heading_fg": "tree_header_fg",
    "tree_branch_color": "tree_branch_color",

    # Grid/Table
    "grid_line1_bg": "grid_line1_bg",
    "grid_line1_fg": "grid_line1_fg",
    "grid_line2_bg": "grid_line2_bg",
    "grid_line2_fg": "grid_line2_fg",
    "grid_selected_bg": "grid_selected_bg",
    "grid_selected_fg": "grid_selected_fg",
    "grid_hover_bg": "grid_hover_bg",
    "grid_header_bg": "grid_header_bg",
    "grid_header_fg": "grid_header_fg",
    "grid_gridline": "grid_gridline",

    # Tabs
    "tab_bg": "tab_bg",
    "tab_fg": "tab_fg",
    "tab_selected_bg": "tab_selected_bg",
    "tab_selected_fg": "tab_selected_fg",
    "tab_hover_bg": "tab_hover_bg",

    # Buttons
    "button_bg": "button_bg",
    "button_fg": "button_fg",
    "button_border": "button_border",
    "button_hover_bg": "button_hover_bg",
    "button_hover_fg": "button_hover_fg",
    "button_pressed_bg": "button_pressed_bg",

    # Scrollbar
    "scrollbar_bg": "scrollbar_bg",
    "scrollbar_handle_bg": "scrollbar_handle",
    "scrollbar_handle_hover_bg": "scrollbar_handle_hover",

    # Editor
    "editor_bg": "editor_bg",
    "editor_fg": "editor_fg",

    # Tooltip
    "tooltip_bg": "tooltip_bg",
    "tooltip_fg": "tooltip_fg",
    "tooltip_border": "tooltip_border",

    # Checkbox
    "checkbox_bg": "checkbox_bg",
    "checkbox_fg": "checkbox_fg",
    "checkbox_border": "checkbox_border",
    "checkbox_checked_bg": "checkbox_checked_bg",

    # GroupBox
    "groupbox_border": "groupbox_border",
    "groupbox_title_fg": "groupbox_title",

    # ComboBox
    "combo_bg": "combo_bg",
    "combo_fg": "combo_fg",
    "combo_border": "combo_border",

    # Dropdown menu
    "dd_menu_bg": "menu_bg",
    "dd_menu_fg": "menu_fg",
    "dd_menu_hover_bg": "menu_hover_bg",

    # Log colors
    "log_bg": "log_bg",
    "log_fg": "log_fg",
    "log_info_fg": "log_info",
    "log_warning_fg": "log_warning",
    "log_error_fg": "log_error",
    "log_important_fg": "log_important",
    "log_debug_fg": "log_debug",

    # Icon sidebar
    "iconsidebar_bg": "iconsidebar_bg",
    "iconsidebar_selected_bg": "iconsidebar_selected_bg",
    "iconsidebar_hover_bg": "iconsidebar_hover_bg",
    "iconsidebar_pressed_bg": "iconsidebar_pressed_bg",

    # Misc
    "focus_border": "focus_border",
    "border_color": "border_color",
    "window_border": "window_border",
    "panel_bg": "panel_bg",
    "window_bg": "window_bg",
    "text_primary": "text_primary",
    "text_disabled": "text_disabled",
}

# Reverse mapping
NEW_TO_LEGACY_KEYS = {v: k for k, v in LEGACY_TO_NEW_KEYS.items()}


def new_to_legacy_colors(theme: GeneratedTheme) -> Dict[str, str]:
    """
    Convert new theme colors to legacy format.

    Args:
        theme: GeneratedTheme from new system

    Returns:
        Dict with legacy color keys
    """
    legacy = {"is_dark": theme.is_dark}

    for legacy_key, new_key in LEGACY_TO_NEW_KEYS.items():
        if new_key in theme.colors:
            legacy[legacy_key] = theme.colors[new_key]

    return legacy


def legacy_to_palette(legacy_colors: Dict[str, str], name: str = "Imported") -> ThemePalette:
    """
    Convert legacy color dict to a ThemePalette.

    Args:
        legacy_colors: Legacy theme colors dict
        name: Name for the new palette

    Returns:
        ThemePalette instance
    """
    # Get text color for default icon
    text_color = legacy_colors.get("Normal_FG", legacy_colors.get("text_primary", "#e0e0e0"))

    # Map legacy structure colors to palette
    return ThemePalette(
        name=name,
        background=legacy_colors.get("Frame_BG", legacy_colors.get("panel_bg", "#252525")),
        surface=legacy_colors.get("Data_BG", legacy_colors.get("surface_bg", "#2d2d2d")),
        border=legacy_colors.get("Data_Border", legacy_colors.get("border_color", "#3d3d3d")),
        accent=legacy_colors.get("Accent", legacy_colors.get("accent", "#0078d7")),
        text=text_color,
        text_secondary=legacy_colors.get("Frame_FG_Secondary", legacy_colors.get("text_secondary", "#808080")),
        icon=legacy_colors.get("icon_color", legacy_colors.get("Icon_Color", text_color)),
        info=legacy_colors.get("Info_FG", legacy_colors.get("info", "#3498db")),
        warning=legacy_colors.get("Warning_FG", legacy_colors.get("warning", "#f39c12")),
        error=legacy_colors.get("Error_FG", legacy_colors.get("error", "#e74c3c")),
        important=legacy_colors.get("log_important_fg", "#9b59b6"),
    )


class LegacyThemeAdapter:
    """
    Adapter that wraps the new ThemeManager to provide legacy interface.

    This can be used as a drop-in replacement for ThemeBridge during migration.
    """

    def __init__(self, manager):
        """
        Initialize adapter with a ThemeManager.

        Args:
            manager: ThemeManager instance
        """
        self._manager = manager

    def get_theme_colors(self, theme_name: str = None) -> Dict[str, str]:
        """
        Get colors in legacy format.

        Args:
            theme_name: Ignored (uses current theme)

        Returns:
            Dict with legacy color keys
        """
        if self._manager.current_theme:
            return new_to_legacy_colors(self._manager.current_theme)
        return {}

    def register_observer(self, callback):
        """Register observer (adapts to new format)."""
        def adapted_callback(colors):
            # Convert new colors to legacy format for callback
            legacy = {"is_dark": self._manager.is_dark}
            for legacy_key, new_key in LEGACY_TO_NEW_KEYS.items():
                if new_key in colors:
                    legacy[legacy_key] = colors[new_key]
            callback(legacy)

        self._manager.register_observer(adapted_callback)

    def unregister_observer(self, callback):
        """Unregister observer."""
        # Note: this won't work perfectly due to the wrapper
        # In practice, during migration, this is rarely used
        pass

    @property
    def current_theme(self) -> str:
        """Get current theme name."""
        if self._manager.current_theme:
            return self._manager.current_theme.name
        return "unknown"
