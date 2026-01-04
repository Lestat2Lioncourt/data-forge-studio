"""
Theme Generator - Expands a minimal palette into a complete theme.

Takes a ThemePalette (10 colors) and generates a GeneratedTheme with 90+ properties
suitable for styling all UI components.
"""

from dataclasses import dataclass
from typing import Dict

from .palette import ThemePalette
from .utils import (
    is_dark, lighten, darken, blend, fade,
    contrast_color, subtle_alternate
)


@dataclass
class GeneratedTheme:
    """Complete theme generated from a palette."""

    name: str
    is_dark: bool
    colors: Dict[str, str]
    source_palette: ThemePalette

    def get(self, key: str, default: str = None) -> str:
        """Get a color by key with optional default."""
        return self.colors.get(key, default)

    def __getitem__(self, key: str) -> str:
        """Get a color by key."""
        return self.colors[key]


class ThemeGenerator:
    """
    Generates a complete theme from a minimal palette.

    The generator creates all necessary color properties for UI components:
    - Window and panel backgrounds
    - Text colors (primary, secondary, disabled)
    - Interactive states (hover, pressed, selected, focus)
    - Component-specific colors (tree, grid, input, button, menu, tabs, etc.)
    - Semantic colors (info, warning, error, important)
    - Icon colors
    """

    # Default opacity values (used if palette doesn't specify)
    DEFAULT_HOVER_OPACITY = 15
    DEFAULT_SELECTED_OPACITY = 30

    def generate(self, palette: ThemePalette) -> GeneratedTheme:
        """
        Generate a complete theme from a palette.

        Args:
            palette: The source palette with 10 core colors

        Returns:
            GeneratedTheme with 90+ color properties
        """
        # Determine if this is a dark or light theme
        is_dark_theme = is_dark(palette.background)

        # Generate all colors
        colors = self._generate_colors(palette, is_dark_theme)

        # Apply user overrides
        colors.update(palette.overrides)

        return GeneratedTheme(
            name=palette.name,
            is_dark=is_dark_theme,
            colors=colors,
            source_palette=palette,
        )

    def _generate_colors(self, p: ThemePalette, is_dark_theme: bool) -> Dict[str, str]:
        """Generate all color properties from palette."""

        # Get opacity from palette (0-100) and convert to 0-1
        hover_opacity = getattr(p, 'hover_opacity', self.DEFAULT_HOVER_OPACITY) / 100.0
        selected_opacity = getattr(p, 'selected_opacity', self.DEFAULT_SELECTED_OPACITY) / 100.0
        pressed_opacity = selected_opacity + 0.10  # Pressed is slightly more opaque

        # Pre-calculate common derived colors
        hover_bg = blend(p.surface, p.accent, hover_opacity)
        selected_bg = blend(p.surface, p.accent, selected_opacity)
        pressed_bg = blend(p.surface, p.accent, pressed_opacity)

        # Alternate row color for tables/trees
        alternate_bg = subtle_alternate(p.surface, is_dark_theme)

        # Slightly darker/lighter background for window chrome
        if is_dark_theme:
            window_bg = darken(p.background, 0.1)
            topbar_bg = darken(p.background, 0.15)
        else:
            window_bg = darken(p.background, 0.05)
            topbar_bg = darken(p.background, 0.08)

        # Disabled text (blend with background for muted effect)
        text_disabled = blend(p.background, p.text, 0.4)

        # Selection text (ensure contrast)
        selected_fg = contrast_color(p.accent)

        # Focus border (same as accent or slightly adjusted)
        focus_border = p.accent

        # Icon color (from palette)
        icon_color = p.icon

        return {
            # === META ===
            "is_dark": is_dark_theme,

            # === SOURCE PALETTE (11 colors) ===
            # These are the source colors that generate all others.
            # Editing these will regenerate all derived colors.
            "background": p.background,
            "surface": p.surface,
            "border": p.border,
            "accent": p.accent,
            "text": p.text,
            "text_secondary": p.text_secondary,
            "icon": p.icon,
            "info": p.info,
            "warning": p.warning,
            "error": p.error,
            "important": p.important,

            # === WINDOW / PANELS ===
            "window_bg": window_bg,
            "window_border": p.border,
            "panel_bg": p.background,
            "surface_bg": p.surface,
            "border_color": p.border,

            # === TEXT ===
            "text_primary": p.text,
            "text_disabled": text_disabled,

            # === INTERACTIVE STATES ===
            "hover_bg": hover_bg,
            "selected_bg": selected_bg,
            "selected_fg": selected_fg,
            "pressed_bg": pressed_bg,
            "focus_border": focus_border,

            # === TOP BAR / TITLE BAR ===
            "topbar_bg": topbar_bg,
            "topbar_fg": p.text,

            # === MENU BAR ===
            "menubar_bg": p.background,
            "menubar_fg": p.text,
            "menubar_hover_bg": blend(p.background, p.accent, hover_opacity + 0.10),
            "menubar_hover_fg": p.text,
            "menubar_selected_bg": blend(p.background, p.accent, selected_opacity),
            "menubar_selected_fg": p.text,

            # === DROPDOWN MENUS ===
            "menu_bg": p.surface,
            "menu_fg": p.text,
            "menu_hover_bg": blend(p.surface, p.accent, hover_opacity + 0.10),
            "menu_hover_fg": p.text,
            "menu_selected_bg": blend(p.surface, p.accent, selected_opacity),
            "menu_selected_fg": selected_fg,
            "menu_separator": p.border,

            # === STATUS BAR ===
            "statusbar_bg": topbar_bg,
            "statusbar_fg": p.text,

            # === BUTTONS ===
            "button_bg": p.surface,
            "button_fg": p.text,
            "button_border": p.border,
            "button_hover_bg": hover_bg,
            "button_hover_fg": p.text,
            "button_pressed_bg": pressed_bg,
            "button_disabled_bg": p.background,
            "button_disabled_fg": text_disabled,

            # === TOOLBAR BUTTONS ===
            "toolbar_button_bg": p.background,
            "toolbar_button_fg": p.text,
            "toolbar_button_border": p.background,
            "toolbar_button_hover_bg": hover_bg,
            "toolbar_button_hover_fg": p.text,
            "toolbar_button_pressed_bg": pressed_bg,

            # === INPUT FIELDS ===
            "input_bg": p.surface,
            "input_fg": p.text,
            "input_border": p.border,
            "input_focus_border": focus_border,
            "input_placeholder": p.text_secondary,
            "input_disabled_bg": p.background,
            "input_disabled_fg": text_disabled,

            # === COMBOBOX ===
            "combo_bg": p.surface,
            "combo_fg": p.text,
            "combo_border": p.border,
            "combo_arrow": p.text,

            # === CHECKBOX / RADIO ===
            "checkbox_bg": p.surface,
            "checkbox_border": p.border,
            "checkbox_checked_bg": p.accent,
            "checkbox_checked_border": p.accent,
            "checkbox_fg": p.text,

            # === TREE WIDGET ===
            "tree_bg": p.surface,
            "tree_fg": p.text,
            "tree_line1_bg": p.surface,
            "tree_line1_fg": p.text,
            "tree_line2_bg": alternate_bg,
            "tree_line2_fg": p.text,
            "tree_selected_bg": blend(p.surface, p.accent, selected_opacity + 0.20),
            "tree_selected_fg": selected_fg,
            "tree_hover_bg": blend(p.surface, p.accent, hover_opacity),
            "tree_header_bg": p.background,
            "tree_header_fg": p.text,
            "tree_branch_color": p.text_secondary,

            # === GRID / TABLE WIDGET ===
            "grid_bg": p.surface,
            "grid_fg": p.text,
            "grid_line1_bg": p.surface,
            "grid_line1_fg": p.text,
            "grid_line2_bg": alternate_bg,
            "grid_line2_fg": p.text,
            "grid_selected_bg": blend(p.surface, p.accent, selected_opacity + 0.20),
            "grid_selected_fg": selected_fg,
            "grid_hover_bg": blend(p.surface, p.accent, hover_opacity),
            "grid_header_bg": p.background,
            "grid_header_fg": p.text,
            "grid_gridline": p.border,

            # === TABS ===
            "tab_bg": p.background,
            "tab_fg": p.text_secondary,
            "tab_selected_bg": p.surface,
            "tab_selected_fg": p.text,
            "tab_hover_bg": blend(p.background, p.accent, hover_opacity),

            # === SCROLLBAR ===
            "scrollbar_bg": window_bg,
            "scrollbar_handle": p.border,
            "scrollbar_handle_hover": lighten(p.border, 0.15) if is_dark_theme else darken(p.border, 0.15),

            # === SPLITTER ===
            "splitter_bg": p.border,
            "splitter_hover_bg": p.accent,

            # === GROUPBOX ===
            "groupbox_border": p.border,
            "groupbox_title": p.text,

            # === TOOLTIP ===
            "tooltip_bg": p.background,
            "tooltip_fg": p.text,
            "tooltip_border": p.accent,

            # === EDITOR / CODE ===
            "editor_bg": p.surface,
            "editor_fg": p.text,
            "editor_selection_bg": blend(p.surface, p.accent, 0.4),
            "editor_current_line_bg": hover_bg,
            "editor_line_number_bg": p.background,
            "editor_line_number_fg": p.text_secondary,

            # === SYNTAX HIGHLIGHTING (SQL) ===
            "sql_keyword": p.accent,
            "sql_string": p.important,  # Use important color for strings
            "sql_comment": p.text_secondary,
            "sql_number": p.info,
            "sql_function": p.warning,
            "sql_operator": p.text,
            "sql_identifier": p.info,

            # === LOG PANEL ===
            "log_bg": p.surface,
            "log_fg": p.text,
            "log_info": p.info,
            "log_warning": p.warning,
            "log_error": p.error,
            "log_important": p.important,
            "log_debug": p.text_secondary,

            # === ICON SIDEBAR ===
            "iconsidebar_bg": p.background,
            "iconsidebar_selected_bg": blend(p.background, p.accent, selected_opacity),
            "iconsidebar_hover_bg": blend(p.background, p.text, hover_opacity),
            "iconsidebar_pressed_bg": blend(p.background, p.text, hover_opacity + 0.10),

            # === ICONS ===
            "icon_color": icon_color,

            # === DIALOG ===
            "dialog_bg": p.background,
            "dialog_fg": p.text,
            "dialog_border": p.border,

            # === PROGRESS BAR ===
            "progress_bg": p.background,
            "progress_fg": p.accent,
            "progress_text": p.text,

            # === OPACITY SETTINGS (for reference) ===
            "hover_opacity": int(hover_opacity * 100),
            "selected_opacity": int(selected_opacity * 100),
        }
