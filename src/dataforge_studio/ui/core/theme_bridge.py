"""
Theme Bridge - Extends window-template ThemeManager with Observer pattern
Fusion of window-template theme system and DataForge Studio theme management

New Theme System (v2):
- Palette: 15 named colors
- Disposition: Vectors mapping palette colors to UI properties
- Theme: Palette + Disposition + optional overrides
"""

import json
import logging
from pathlib import Path
from typing import List, Callable, Dict, Optional
from ..templates.window.theme_manager import ThemeManager as BaseThemeManager

logger = logging.getLogger(__name__)
from .theme_image_generator import generate_dropdown_arrow, generate_branch_images

# Paths
APP_CONFIG_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig"
CUSTOM_THEMES_PATH = APP_CONFIG_PATH / "themes"
PALETTES_PATH = APP_CONFIG_PATH / "palettes"
DISPOSITIONS_PATH = APP_CONFIG_PATH / "dispositions"
ASSETS_PATH = Path(__file__).parent.parent / "assets" / "images"

# New theme system imports
from ...core.theme.models import Palette, Disposition, Theme, BUILTIN_PALETTES, BUILTIN_DISPOSITIONS
from ...core.theme.disposition_engine import DispositionEngine


class ThemeBridge(BaseThemeManager):
    """
    Extended theme manager with Observer pattern for DataForge Studio.

    This class bridges the window-template theme system with DataForge Studio's
    needs, adding:
    - Observer pattern for notifying widgets of theme changes
    - Additional QSS generation methods for custom widgets
    - Support for DataForge-specific color keys
    - Auto-loading of custom themes from _AppConfig/themes/
    """

    _instance = None

    def __init__(self, theme_file=None):
        super().__init__(theme_file)
        self._observers: List[Callable] = []

        # New theme system (v2)
        self._palettes: Dict[str, Palette] = {}
        self._dispositions: Dict[str, Disposition] = {}
        self._themes_v2: Dict[str, Theme] = {}
        self._engine = DispositionEngine()
        self._colors_cache: Dict[str, Dict[str, str]] = {}
        self._dark_mode: bool = True  # Current mode (True=dark, False=light)

        # Load new system data
        self._load_palettes()
        self._load_dispositions()
        self._load_themes_v2()

        # Load legacy custom themes (for backward compatibility)
        self._load_custom_themes()

    def _load_palettes(self):
        """Load all palettes from _AppConfig/palettes/ directory."""
        if not PALETTES_PATH.exists():
            logger.warning(f"Palettes directory not found: {PALETTES_PATH}")
            return

        for palette_file in PALETTES_PATH.glob("*.json"):
            palette_id = palette_file.stem
            try:
                with open(palette_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Only load new-format palettes (with "colors" dict)
                    if "colors" in data:
                        palette = Palette.from_dict(palette_id, data)
                        self._palettes[palette_id] = palette
                        logger.debug(f"Loaded palette '{palette_id}'")
            except Exception as e:
                logger.warning(f"Failed to load palette '{palette_id}': {e}")

    def _load_dispositions(self):
        """Load all dispositions from _AppConfig/dispositions/ directory."""
        if not DISPOSITIONS_PATH.exists():
            logger.warning(f"Dispositions directory not found: {DISPOSITIONS_PATH}")
            return

        for disposition_file in DISPOSITIONS_PATH.glob("*.json"):
            disposition_id = disposition_file.stem
            try:
                with open(disposition_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Filter out _comment keys from vectors
                    if "vectors" in data:
                        data["vectors"] = {
                            k: v for k, v in data["vectors"].items()
                            if not k.startswith("_")
                        }
                    disposition = Disposition.from_dict(disposition_id, data)
                    self._dispositions[disposition_id] = disposition
                    logger.debug(f"Loaded disposition '{disposition_id}'")
            except Exception as e:
                logger.warning(f"Failed to load disposition '{disposition_id}': {e}")

    def _load_themes_v2(self):
        """Load new-format themes (palette + disposition + overrides)."""
        if not CUSTOM_THEMES_PATH.exists():
            return

        for theme_file in CUSTOM_THEMES_PATH.glob("*.json"):
            theme_id = theme_file.stem
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check if this is a v2 theme:
                    # - Has "disposition" key
                    # - Has palette reference (palette, or legacy palette_dark/palette_light)
                    has_disposition = "disposition" in data
                    has_palette = "palette" in data or "palette_dark" in data or "palette_light" in data

                    if has_disposition and has_palette:
                        theme = Theme.from_dict(theme_id, data)
                        self._themes_v2[theme_id] = theme
                        logger.debug(f"Loaded v2 theme '{theme_id}'")
            except Exception as e:
                logger.warning(f"Failed to load v2 theme '{theme_id}': {e}")

    def _load_custom_themes(self):
        """Load legacy custom themes from _AppConfig/themes/ directory.

        Custom themes OVERRIDE built-in themes with the same ID.
        This allows users to customize built-in themes like 'minimal_dark'.
        Skips v2 themes (already loaded by _load_themes_v2).
        """
        if not CUSTOM_THEMES_PATH.exists():
            return

        for theme_file in CUSTOM_THEMES_PATH.glob("*.json"):
            theme_id = theme_file.stem

            # Skip if already loaded as v2 theme
            if theme_id in self._themes_v2:
                continue

            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)

                    # Handle "patch" type themes - expand to minimal
                    if theme_data.get("type") == "patch":
                        theme_data = self._expand_patch_theme(theme_data)

                    # Custom themes override built-in themes
                    self.themes[theme_id] = theme_data
                    logger.debug(f"Loaded legacy theme '{theme_id}' from {theme_file}")
            except Exception as e:
                logger.warning(f"Failed to load legacy theme '{theme_id}': {e}")

    def _expand_patch_theme(self, patch_data: Dict) -> Dict:
        """
        Expand a patch theme to a minimal theme.

        Patch themes reference a base theme and override specific colors.

        Args:
            patch_data: Theme data with type="patch", base, and overrides

        Returns:
            Theme data as type="minimal" with merged palette
        """
        base_id = patch_data.get("base", "minimal_dark")
        overrides = patch_data.get("overrides", {})

        # Get base theme palette
        if base_id in self.themes:
            base_theme = self.themes[base_id]
            base_palette = dict(base_theme.get("palette", {}))
        else:
            # Fallback to minimal_dark defaults
            base_palette = {
                "is_dark": True,
                "TopBar_BG": "#2b2b2b",
                "TopBar_FG": "#ffffff",
                "MenuBar_BG": "#3d3d3d",
                "MenuBar_FG": "#ffffff",
                "StatusBar_BG": "#2b2b2b",
                "StatusBar_FG": "#ffffff",
                "Frame_BG": "#252525",
                "Frame_FG": "#e0e0e0",
                "Frame_FG_Secondary": "#808080",
                "Data_BG": "#2d2d2d",
                "Data_FG": "#e0e0e0",
                "Data_Border": "#3d3d3d",
                "Hover_BG": "#383838",
                "Selected_BG": "#0078d7",
                "Selected_FG": "#ffffff",
                "Accent": "#0078d7",
                "Normal_FG": "#ffffff",
                "Success_FG": "#2ecc71",
                "Warning_FG": "#f39c12",
                "Error_FG": "#e74c3c",
                "Info_FG": "#3498db",
            }

        # Apply overrides
        for key, value in overrides.items():
            base_palette[key] = value
            # Accent also affects Selected_BG for selection colors
            if key == "Accent":
                base_palette["Selected_BG"] = value

        # Return as minimal theme
        return {
            "name": patch_data.get("name", "Custom Theme"),
            "type": "minimal",
            "palette": base_palette
        }

    @classmethod
    def get_instance(cls):
        """Get singleton instance of ThemeBridge"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ==================== OVERRIDES FOR V2 THEME COMPATIBILITY ====================

    def get_theme_colors(self, theme_name: str = None) -> Dict[str, str]:
        """
        Get color dictionary for a theme.

        Overrides base class to support v2 themes and add legacy mappings.

        Args:
            theme_name: Theme identifier. If None, uses current_theme.

        Returns:
            Dictionary of color variables with all legacy keys present
        """
        if theme_name is None:
            theme_name = self.current_theme

        # Check if this is a v2 theme first
        if self.is_v2_theme(theme_name):
            return self.get_theme_colors_v2(theme_name)

        # Use base class for legacy themes
        colors = super().get_theme_colors(theme_name)

        # Ensure all required keys exist for legacy themes too
        colors = self._normalize_legacy_colors(colors)

        return colors

    # ==================== NEW THEME SYSTEM (v2) API ====================

    def get_palettes(self) -> Dict[str, Palette]:
        """Get all available palettes."""
        return self._palettes

    def get_palette(self, palette_id: str) -> Optional[Palette]:
        """Get a specific palette by ID."""
        return self._palettes.get(palette_id)

    def get_dispositions(self) -> Dict[str, Disposition]:
        """Get all available dispositions."""
        return self._dispositions

    def get_disposition(self, disposition_id: str) -> Optional[Disposition]:
        """Get a specific disposition by ID."""
        return self._dispositions.get(disposition_id)

    def get_themes_v2(self) -> Dict[str, Theme]:
        """Get all v2 themes."""
        return self._themes_v2

    def get_theme_v2(self, theme_id: str) -> Optional[Theme]:
        """Get a specific v2 theme by ID."""
        return self._themes_v2.get(theme_id)

    def is_v2_theme(self, theme_id: str) -> bool:
        """Check if a theme uses the v2 system."""
        return theme_id in self._themes_v2

    def get_theme_colors_v2(self, theme_id: str, dark_mode: Optional[bool] = None) -> Dict[str, str]:
        """
        Generate colors for a v2 theme using the disposition engine.

        Args:
            theme_id: The theme identifier
            dark_mode: True for dark mode, False for light mode.
                      If None, uses current mode setting.

        Returns:
            Dictionary of color property names to hex values
        """
        if dark_mode is None:
            dark_mode = self._dark_mode

        # Cache key includes mode
        cache_key = f"{theme_id}:{'dark' if dark_mode else 'light'}"
        if cache_key in self._colors_cache:
            return self._colors_cache[cache_key]

        theme = self._themes_v2.get(theme_id)
        if not theme:
            logger.warning(f"V2 theme not found: {theme_id}")
            return {}

        # Get palette
        palette = self._palettes.get(theme.palette_id)
        if not palette:
            logger.warning(f"Palette not found: {theme.palette_id}")
            return {}

        disposition = self._dispositions.get(theme.disposition_id)
        if not disposition:
            logger.warning(f"Disposition not found: {theme.disposition_id}")
            return {}

        # Generate colors using the engine
        colors = self._engine.apply(palette, disposition)

        # Apply theme overrides
        if theme.overrides:
            colors.update(theme.overrides)

        # Add legacy key mappings for backward compatibility
        colors = self._add_legacy_mappings(colors)

        # Cache and return
        self._colors_cache[cache_key] = colors
        return colors

    def set_dark_mode(self, dark_mode: bool):
        """Set dark/light mode and clear cache."""
        if self._dark_mode != dark_mode:
            self._dark_mode = dark_mode
            self._colors_cache.clear()

    def is_dark_mode(self) -> bool:
        """Get current dark/light mode."""
        return self._dark_mode

    def _add_legacy_mappings(self, colors: Dict[str, str]) -> Dict[str, str]:
        """
        Add legacy key mappings for backward compatibility with old QSS and ThemeManager.

        The old system used keys like 'main_menu_bar_bg', 'feature_menu_bar_bg', etc.
        This maps new v2 keys to old keys so existing code continues to work.
        """
        mappings = {
            # Window-template menu bar keys (required by base ThemeManager.apply_theme)
            'main_menu_bar_bg': colors.get('topbar_bg', colors.get('panel_bg', '#252525')),
            'main_menu_bar_fg': colors.get('topbar_fg', colors.get('text_primary', '#e0e0e0')),
            'feature_menu_bar_bg': colors.get('menubar_bg', colors.get('panel_bg', '#252525')),
            'feature_menu_bar_fg': colors.get('menubar_fg', colors.get('text_primary', '#e0e0e0')),
            'feature_menu_bar_hover_bg': colors.get('menubar_hover_bg', colors.get('hover_bg', '#383838')),
            'feature_menu_bar_hover_fg': colors.get('menubar_hover_fg', colors.get('text_primary', '#e0e0e0')),
            'feature_menu_bar_selected_bg': colors.get('menubar_selected_bg', colors.get('selected_bg', '#0078d7')),
            'feature_menu_bar_selected_fg': colors.get('menubar_selected_fg', colors.get('text_primary', '#e0e0e0')),

            # Status bar
            'status_bar_bg': colors.get('statusbar_bg', colors.get('panel_bg', '#252525')),
            'status_bar_fg': colors.get('statusbar_fg', colors.get('text_primary', '#e0e0e0')),

            # Dropdown menu (legacy dd_menu_* keys)
            'dd_menu_bg': colors.get('menu_bg', colors.get('surface_bg', '#2d2d2d')),
            'dd_menu_fg': colors.get('menu_fg', colors.get('text_primary', '#e0e0e0')),
            'dd_menu_hover_bg': colors.get('menu_hover_bg', colors.get('hover_bg', '#383838')),
            'dd_menu_hover_fg': colors.get('menu_hover_fg', colors.get('text_primary', '#e0e0e0')),
            'dd_menu_selected_bg': colors.get('menu_selected_bg', colors.get('selected_bg', '#0078d7')),
            'dd_menu_selected_fg': colors.get('menu_selected_fg', colors.get('selected_fg', '#ffffff')),
            'dd_menu_separator': colors.get('menu_separator', colors.get('border_color', '#3d3d3d')),

            # Tree widget
            'tree_heading_bg': colors.get('tree_header_bg', colors.get('panel_bg', '#252525')),
            'tree_heading_fg': colors.get('tree_header_fg', colors.get('text_primary', '#e0e0e0')),

            # Grid widget
            'grid_heading_bg': colors.get('grid_header_bg', colors.get('panel_bg', '#252525')),
            'grid_heading_fg': colors.get('grid_header_fg', colors.get('text_primary', '#e0e0e0')),

            # Text colors
            'normal_fg': colors.get('text_primary', '#e0e0e0'),
            'text_secondary': colors.get('text_secondary', '#808080'),

            # Scrollbar
            'scrollbar_handle_bg': colors.get('scrollbar_handle', colors.get('border_color', '#3d3d3d')),
            'scrollbar_handle_hover_bg': colors.get('scrollbar_handle_hover', colors.get('text_secondary', '#808080')),

            # Toolbar
            'toolbar_bg': colors.get('toolbar_bg', colors.get('panel_bg', '#252525')),
            'toolbarbtn_bg': colors.get('toolbar_button_bg', colors.get('panel_bg', '#252525')),
            'toolbarbtn_fg': colors.get('toolbar_button_fg', colors.get('text_primary', '#e0e0e0')),
            'toolbarbtn_hover_bg': colors.get('toolbar_button_hover_bg', colors.get('hover_bg', '#383838')),
            'toolbarbtn_hover_fg': colors.get('toolbar_button_hover_fg', colors.get('text_primary', '#e0e0e0')),
            'toolbarbtn_pressed_bg': colors.get('toolbar_button_pressed_bg', colors.get('selected_bg', '#0078d7')),
            'toolbarbtn_border': colors.get('toolbar_button_border', colors.get('panel_bg', '#252525')),

            # GroupBox
            'groupbox_title_fg': colors.get('groupbox_title', colors.get('text_primary', '#e0e0e0')),

            # Tree icon color
            'tree_icon_color': colors.get('tree_icon_color', colors.get('tree_line1_fg', colors.get('text_primary', '#e0e0e0'))),

            # Icon Sidebar
            'iconsidebar_bg': colors.get('iconsidebar_bg', colors.get('window_bg', '#252525')),
            'iconsidebar_selected_bg': colors.get('iconsidebar_selected_bg', colors.get('selected_bg', '#0078d7')),
            'iconsidebar_hover_bg': colors.get('iconsidebar_hover_bg', colors.get('hover_bg', '#383838')),
            'iconsidebar_pressed_bg': colors.get('iconsidebar_pressed_bg', colors.get('pressed_bg', '#0078d7')),

            # Ensure basic colors are present
            'data_bg': colors.get('surface_bg', colors.get('surface', '#2d2d2d')),
            'frame_fg': colors.get('text_primary', '#e0e0e0'),
        }

        # Add mappings to colors (don't overwrite existing keys)
        for key, value in mappings.items():
            if key not in colors:
                colors[key] = value

        return colors

    def clear_cache(self, theme_id: str = None):
        """Clear the colors cache for a theme or all themes."""
        if theme_id:
            self._colors_cache.pop(theme_id, None)
        else:
            self._colors_cache.clear()

    def reload_palette(self, palette_id: str):
        """Reload a palette from file."""
        palette_file = PALETTES_PATH / f"{palette_id}.json"
        if palette_file.exists():
            try:
                with open(palette_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "colors" in data:
                    palette = Palette.from_dict(palette_id, data)
                    self._palettes[palette_id] = palette
                    self._colors_cache.clear()  # Clear all cache when palette changes
                    logger.debug(f"Reloaded palette: {palette_id}")
            except Exception as e:
                logger.warning(f"Failed to reload palette '{palette_id}': {e}")

    def _normalize_legacy_colors(self, colors: Dict[str, str]) -> Dict[str, str]:
        """
        Normalize legacy theme colors to include all required key names.

        Maps old key names to new key names so QSS templates and ThemeManager
        work with both old and new theme formats.
        """
        result = dict(colors)

        # Get common base values for fallbacks
        panel_bg = colors.get('panel_bg', colors.get('Frame_BG', '#252525'))
        frame_fg = colors.get('Frame_FG', colors.get('normal_fg', '#e0e0e0'))
        data_bg = colors.get('Data_BG', colors.get('data_bg', '#2d2d2d'))
        data_fg = colors.get('Data_FG', colors.get('data_fg', '#e0e0e0'))
        data_border = colors.get('Data_Border', colors.get('border_color', '#3d3d3d'))
        hover_bg = colors.get('Hover_BG', colors.get('hover_bg', '#383838'))
        selected_bg = colors.get('Selected_BG', colors.get('selected_bg', '#0078d7'))
        selected_fg = colors.get('Selected_FG', colors.get('selected_fg', '#ffffff'))
        accent = colors.get('Accent', colors.get('accent', '#0078d7'))
        frame_fg_secondary = colors.get('Frame_FG_Secondary', colors.get('text_secondary', '#808080'))

        # Map legacy keys to new keys
        mappings = {
            # Window-template menu bar keys (required by ThemeManager.apply_theme)
            'main_menu_bar_bg': colors.get('main_menu_bar_bg', colors.get('TopBar_BG', panel_bg)),
            'main_menu_bar_fg': colors.get('main_menu_bar_fg', colors.get('TopBar_FG', frame_fg)),
            'feature_menu_bar_bg': colors.get('feature_menu_bar_bg', colors.get('MenuBar_BG', panel_bg)),
            'feature_menu_bar_fg': colors.get('feature_menu_bar_fg', colors.get('MenuBar_FG', frame_fg)),
            'feature_menu_bar_hover_bg': colors.get('feature_menu_bar_hover_bg', colors.get('MenuBar_Hover_BG', hover_bg)),
            'feature_menu_bar_hover_fg': colors.get('feature_menu_bar_hover_fg', colors.get('MenuBar_Hover_FG', frame_fg)),
            'feature_menu_bar_selected_bg': colors.get('feature_menu_bar_selected_bg', colors.get('MenuBar_Selected_BG', selected_bg)),
            'feature_menu_bar_selected_fg': colors.get('feature_menu_bar_selected_fg', colors.get('MenuBar_Selected_FG', frame_fg)),

            # Status bar
            'status_bar_bg': colors.get('status_bar_bg', colors.get('StatusBar_BG', panel_bg)),
            'status_bar_fg': colors.get('status_bar_fg', colors.get('StatusBar_FG', frame_fg)),

            # Window/Panel
            'window_bg': colors.get('window_bg', panel_bg),
            'panel_bg': panel_bg,
            'surface_bg': colors.get('surface_bg', data_bg),
            'border_color': colors.get('border_color', data_border),

            # Text
            'text_primary': colors.get('text_primary', frame_fg),
            'text_secondary': colors.get('text_secondary', frame_fg_secondary),
            'text_disabled': colors.get('text_disabled', '#606060'),
            'normal_fg': colors.get('normal_fg', frame_fg),

            # Interactive states
            'hover_bg': hover_bg,
            'selected_bg': selected_bg,
            'selected_fg': selected_fg,
            'focus_border': colors.get('focus_border', accent),

            # Buttons
            'button_bg': colors.get('button_bg', panel_bg),
            'button_fg': colors.get('button_fg', frame_fg),
            'button_border': colors.get('button_border', data_border),
            'button_hover_bg': colors.get('button_hover_bg', hover_bg),
            'button_hover_fg': colors.get('button_hover_fg', frame_fg),
            'button_pressed_bg': colors.get('button_pressed_bg', selected_bg),

            # Input fields
            'input_bg': colors.get('input_bg', data_bg),
            'input_fg': colors.get('input_fg', data_fg),
            'input_border': colors.get('input_border', data_border),
            'input_focus_border': colors.get('input_focus_border', accent),

            # Combo
            'combo_bg': colors.get('combo_bg', data_bg),
            'combo_fg': colors.get('combo_fg', data_fg),

            # Editor
            'editor_bg': colors.get('editor_bg', data_bg),
            'editor_fg': colors.get('editor_fg', data_fg),

            # Tree
            'tree_line1_bg': colors.get('tree_line1_bg', data_bg),
            'tree_line1_fg': colors.get('tree_line1_fg', data_fg),
            'tree_line2_bg': colors.get('tree_line2_bg', data_bg),
            'tree_line2_fg': colors.get('tree_line2_fg', data_fg),
            'tree_selected_bg': colors.get('tree_selected_bg', selected_bg),
            'tree_selected_fg': colors.get('tree_selected_fg', selected_fg),
            'tree_hover_bg': colors.get('tree_hover_bg', hover_bg),
            'tree_header_bg': colors.get('tree_header_bg', colors.get('tree_heading_bg', panel_bg)),
            'tree_header_fg': colors.get('tree_header_fg', colors.get('tree_heading_fg', frame_fg)),
            'tree_heading_bg': colors.get('tree_heading_bg', colors.get('tree_header_bg', panel_bg)),
            'tree_heading_fg': colors.get('tree_heading_fg', colors.get('tree_header_fg', frame_fg)),
            'tree_branch_color': colors.get('tree_branch_color', '#808080'),

            # Grid
            'grid_line1_bg': colors.get('grid_line1_bg', data_bg),
            'grid_line1_fg': colors.get('grid_line1_fg', data_fg),
            'grid_line2_bg': colors.get('grid_line2_bg', data_bg),
            'grid_line2_fg': colors.get('grid_line2_fg', data_fg),
            'grid_selected_bg': colors.get('grid_selected_bg', selected_bg),
            'grid_selected_fg': colors.get('grid_selected_fg', selected_fg),
            'grid_hover_bg': colors.get('grid_hover_bg', hover_bg),
            'grid_header_bg': colors.get('grid_header_bg', panel_bg),
            'grid_header_fg': colors.get('grid_header_fg', frame_fg),
            'grid_gridline': colors.get('grid_gridline', data_border),

            # Tabs
            'tab_bg': colors.get('tab_bg', panel_bg),
            'tab_fg': colors.get('tab_fg', frame_fg_secondary),
            'tab_selected_bg': colors.get('tab_selected_bg', data_bg),
            'tab_selected_fg': colors.get('tab_selected_fg', frame_fg),
            'tab_hover_bg': colors.get('tab_hover_bg', hover_bg),

            # Scrollbar
            'scrollbar_bg': colors.get('scrollbar_bg', panel_bg),
            'scrollbar_handle_bg': colors.get('scrollbar_handle_bg', colors.get('scrollbar_handle', data_border)),
            'scrollbar_handle_hover_bg': colors.get('scrollbar_handle_hover_bg', colors.get('scrollbar_handle_hover', '#606060')),

            # Dropdown menu
            'dd_menu_bg': colors.get('dd_menu_bg', colors.get('DD_Menu_BG', data_bg)),
            'dd_menu_fg': colors.get('dd_menu_fg', colors.get('DD_Menu_FG', data_fg)),
            'dd_menu_hover_bg': colors.get('dd_menu_hover_bg', colors.get('DD_Menu_Hover_BG', hover_bg)),
            'dd_menu_hover_fg': colors.get('dd_menu_hover_fg', colors.get('DD_Menu_Hover_FG', data_fg)),
            'dd_menu_selected_bg': colors.get('dd_menu_selected_bg', colors.get('DD_Menu_Selected_BG', selected_bg)),
            'dd_menu_selected_fg': colors.get('dd_menu_selected_fg', colors.get('DD_Menu_Selected_FG', selected_fg)),
            'dd_menu_separator': colors.get('dd_menu_separator', colors.get('DD_Menu_Separator', data_border)),

            # Checkbox
            'checkbox_bg': colors.get('checkbox_bg', data_bg),
            'checkbox_fg': colors.get('checkbox_fg', frame_fg),
            'checkbox_border': colors.get('checkbox_border', data_border),
            'checkbox_checked_bg': colors.get('checkbox_checked_bg', accent),

            # GroupBox
            'groupbox_title_fg': colors.get('groupbox_title_fg', colors.get('groupbox_title', frame_fg)),
            'groupbox_border': colors.get('groupbox_border', data_border),

            # Tooltip
            'tooltip_bg': colors.get('tooltip_bg', panel_bg),
            'tooltip_fg': colors.get('tooltip_fg', frame_fg),
            'tooltip_border': colors.get('tooltip_border', accent),

            # Splitter
            'splitter_bg': colors.get('splitter_bg', data_border),
            'splitter_hover_bg': colors.get('splitter_hover_bg', accent),

            # Toolbar buttons
            'toolbarbtn_bg': colors.get('toolbarbtn_bg', colors.get('ToolbarBtn_BG', panel_bg)),
            'toolbarbtn_fg': colors.get('toolbarbtn_fg', colors.get('ToolbarBtn_FG', frame_fg)),
            'toolbarbtn_hover_bg': colors.get('toolbarbtn_hover_bg', colors.get('ToolbarBtn_Hover_BG', hover_bg)),
            'toolbarbtn_hover_fg': colors.get('toolbarbtn_hover_fg', colors.get('ToolbarBtn_Hover_FG', frame_fg)),
            'toolbarbtn_pressed_bg': colors.get('toolbarbtn_pressed_bg', colors.get('ToolbarBtn_Pressed_BG', selected_bg)),
            'toolbarbtn_border': colors.get('toolbarbtn_border', colors.get('ToolbarBtn_Border', panel_bg)),

            # Basic fallbacks
            'data_bg': data_bg,
            'frame_fg': frame_fg,
        }

        # Add all mappings to result
        for key, value in mappings.items():
            if key not in result or result[key] is None:
                result[key] = value

        return result

    def create_theme_v2(self, name: str, palette_id: str, disposition_id: str,
                        overrides: Dict[str, str] = None) -> str:
        """
        Create a new v2 theme.

        Args:
            name: Display name for the theme
            palette_id: ID of the palette to use
            disposition_id: ID of the disposition to use
            overrides: Optional color overrides

        Returns:
            The theme ID
        """
        # Generate ID from name
        theme_id = name.lower().replace(" ", "_").replace("-", "_")

        # Create theme object
        theme = Theme(
            id=theme_id,
            name=name,
            palette_id=palette_id,
            disposition_id=disposition_id,
            overrides=overrides or {}
        )

        # Add to registry
        self._themes_v2[theme_id] = theme

        # Save to file
        self._save_theme_v2(theme)

        return theme_id

    def _save_theme_v2(self, theme: Theme):
        """Save a v2 theme to disk."""
        CUSTOM_THEMES_PATH.mkdir(parents=True, exist_ok=True)
        theme_file = CUSTOM_THEMES_PATH / f"{theme.id}.json"

        with open(theme_file, 'w', encoding='utf-8') as f:
            json.dump(theme.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved v2 theme '{theme.id}' to {theme_file}")

    # ==================== END NEW THEME SYSTEM API ====================

    def register_observer(self, callback: Callable):
        """
        Register a callback to be notified of theme changes.

        Args:
            callback: Function to call when theme changes.
                     Will receive theme_colors dict as argument.
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def unregister_observer(self, callback: Callable):
        """
        Unregister a callback.

        Args:
            callback: Previously registered callback
        """
        if callback in self._observers:
            self._observers.remove(callback)

    def apply_theme(self, window, theme_name: str):
        """
        Apply theme and notify observers.

        Args:
            window: TemplateWindow instance
            theme_name: Theme identifier (e.g., "dark_mode")
        """
        # Apply base theme to window-template components
        super().apply_theme(window, theme_name)

        # Notify all observers
        theme_colors = self.get_theme_colors(theme_name)
        self._notify_observers(theme_colors)

    def _notify_observers(self, theme_colors: Dict[str, str]):
        """Notify all registered observers of theme change"""
        logger.debug(f"_notify_observers called, is_dark={theme_colors.get('is_dark')}")

        # Update ImageLoader with new theme colors
        try:
            from ...utils.image_loader import ImageLoader
            ImageLoader.update_theme(theme_colors)
        except Exception as e:
            logger.error(f"Error updating ImageLoader theme: {e}")

        # Notify custom observers
        for observer in self._observers:
            try:
                observer(theme_colors)
            except Exception as e:
                logger.error(f"Error notifying theme observer: {e}")

    def get_qss_for_widget(self, widget_type: str, theme_name: str = None) -> str:
        """
        Generate QSS stylesheet for specific widget type.

        Args:
            widget_type: Type of widget ("QTreeWidget", "QTableWidget", etc.)
            theme_name: Theme to use (uses current if None)

        Returns:
            QSS stylesheet string
        """
        if theme_name is None:
            theme_name = self.current_theme

        colors = self.get_theme_colors(theme_name)

        if widget_type == "QTreeWidget":
            return f"""
                QTreeWidget {{
                    background-color: {colors['tree_line1_bg']};
                    color: {colors['tree_line1_fg']};
                    border: 1px solid {colors['border_color']};
                    alternate-background-color: {colors['tree_line2_bg']};
                }}
                QTreeWidget::item {{
                    color: {colors['tree_line1_fg']};
                }}
                QTreeWidget::item:alternate {{
                    background-color: {colors['tree_line2_bg']};
                    color: {colors['tree_line2_fg']};
                }}
                QTreeWidget::item:selected {{
                    background-color: {colors['tree_selected_bg']};
                    color: {colors['tree_selected_fg']};
                }}
                QTreeWidget::item:hover {{
                    background-color: {colors['tree_hover_bg']};
                }}
                QTreeWidget::branch {{
                    background: {colors['tree_line1_bg']};
                }}
                QTreeWidget::branch:has-siblings:!adjoins-item {{
                    background: url({str(ASSETS_PATH / 'branch-vline.png').replace(chr(92), '/')}) center center no-repeat;
                }}
                QTreeWidget::branch:has-siblings:adjoins-item {{
                    background: url({str(ASSETS_PATH / 'branch-more.png').replace(chr(92), '/')}) center center no-repeat;
                }}
                QTreeWidget::branch:!has-siblings:adjoins-item {{
                    background: url({str(ASSETS_PATH / 'branch-end.png').replace(chr(92), '/')}) center center no-repeat;
                }}
                QHeaderView::section {{
                    background-color: {colors['tree_heading_bg']};
                    color: {colors['tree_heading_fg']};
                    padding: 4px;
                    border: 1px solid {colors['border_color']};
                }}
            """
        elif widget_type == "QTableWidget":
            return f"""
                QTableWidget {{
                    background-color: {colors['grid_line1_bg']};
                    color: {colors['grid_line1_fg']};
                    gridline-color: {colors['grid_gridline']};
                    border: 1px solid {colors['border_color']};
                    alternate-background-color: {colors['grid_line2_bg']};
                }}
                QTableWidget::item {{
                    color: {colors['grid_line1_fg']};
                }}
                QTableWidget::item:alternate {{
                    background-color: {colors['grid_line2_bg']};
                    color: {colors['grid_line2_fg']};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors['grid_selected_bg']};
                    color: {colors['grid_selected_fg']};
                }}
                QTableWidget::item:hover {{
                    background-color: {colors['grid_hover_bg']};
                }}
                QHeaderView::section {{
                    background-color: {colors['grid_header_bg']};
                    color: {colors['grid_header_fg']};
                    padding: 4px;
                    border: 1px solid {colors['border_color']};
                }}
            """
        elif widget_type == "QTextEdit":
            return f"""
                QTextEdit {{
                    background-color: {colors['input_bg']};
                    color: {colors['input_fg']};
                    border: 1px solid {colors['input_border']};
                    padding: 4px;
                }}
                QTextEdit:focus {{
                    border: 2px solid {colors['input_focus_border']};
                }}
            """
        elif widget_type == "QLineEdit":
            return f"""
                QLineEdit {{
                    background-color: {colors['input_bg']};
                    color: {colors['input_fg']};
                    border: 1px solid {colors['input_border']};
                    padding: 4px;
                    border-radius: 2px;
                }}
                QLineEdit:focus {{
                    border: 2px solid {colors['input_focus_border']};
                }}
            """
        elif widget_type == "QComboBox":
            return f"""
                QComboBox {{
                    background-color: {colors['input_bg']};
                    color: {colors['input_fg']};
                    border: 1px solid {colors['input_border']};
                    padding: 4px;
                    border-radius: 2px;
                }}
                QComboBox:focus {{
                    border: 2px solid {colors['input_focus_border']};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox::down-arrow {{
                    /* Arrow image set by global QSS */
                    width: 10px;
                    height: 10px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {colors['dd_menu_bg']};
                    color: {colors['dd_menu_fg']};
                    selection-background-color: {colors['dd_menu_hover_bg']};
                    border: 1px solid {colors['border_color']};
                }}
            """
        elif widget_type == "QPushButton":
            return f"""
                QPushButton {{
                    background-color: {colors['panel_bg']};
                    color: {colors['normal_fg']};
                    border: 1px solid {colors['border_color']};
                    padding: 5px 15px;
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    background-color: {colors['button_hover_bg']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['button_pressed_bg']};
                }}
                QPushButton:disabled {{
                    background-color: {colors['border_color']};
                    color: {colors['border_color']};
                }}
            """
        elif widget_type == "QCheckBox":
            return f"""
                QCheckBox {{
                    color: {colors['normal_fg']};
                    spacing: 5px;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 1px solid {colors['border_color']};
                    background-color: {colors['input_bg']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {colors['tree_selected_bg']};
                    border: 1px solid {colors['tree_selected_bg']};
                }}
                QCheckBox::indicator:hover {{
                    border: 1px solid {colors['input_focus_border']};
                }}
            """
        elif widget_type == "QGroupBox":
            return f"""
                QGroupBox {{
                    color: {colors['normal_fg']};
                    border: 1px solid {colors['border_color']};
                    border-radius: 4px;
                    margin-top: 10px;
                    padding-top: 10px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }}
            """
        elif widget_type == "QLabel":
            return f"""
                QLabel {{
                    color: {colors['normal_fg']};
                    background-color: transparent;
                }}
            """
        else:
            # Default widget styling
            return f"""
                QWidget {{
                    background-color: {colors['window_bg']};
                    color: {colors['normal_fg']};
                }}
            """

    def generate_global_qss(self, theme_name: str = None) -> str:
        """
        Generate complete global QSS stylesheet for the entire application.

        This creates a comprehensive stylesheet that can be applied to QApplication
        to theme all widgets consistently.

        Args:
            theme_name: Theme to use (uses current if None)

        Returns:
            Complete QSS stylesheet string
        """
        if theme_name is None:
            theme_name = self.current_theme
        else:
            # Update current_theme when explicitly specified
            self.current_theme = theme_name

        # Get theme colors (handles both v2 and legacy themes with all mappings)
        colors = self.get_theme_colors(theme_name)

        # DEBUG: Log QSS generation
        logger.debug(f"generate_global_qss called for theme: {theme_name}, is_v2={self.is_v2_theme(theme_name)}")

        # Notify observers (including ImageLoader) of the theme
        self._notify_observers(colors)

        # Get border radius (default to 0 if not specified)
        border_radius = colors.get('frame_border_radius', '0')
        # Ensure it's a number with 'px' suffix
        if isinstance(border_radius, str) and not border_radius.endswith('px'):
            border_radius = f"{border_radius}px"

        # Get tree branch color and generate/use cached images
        branch_color = colors.get('tree_branch_color', '#E6E6E6')
        theme_assets_dir = CUSTOM_THEMES_PATH / theme_name / "assets"

        # Check if color matches cached version (stored in color.txt)
        color_file = theme_assets_dir / "branch_color.txt"
        cached_color = None
        if color_file.exists():
            try:
                cached_color = color_file.read_text().strip()
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Could not read branch color cache: {e}")

        # Generate images if custom color and (no cache or color changed)
        if branch_color.upper() != '#E6E6E6':
            if cached_color != branch_color or not (theme_assets_dir / "branch-vline.png").exists():
                # Generate images with custom color
                branch_images = generate_branch_images(branch_color, theme_assets_dir)
                # Save color for cache check
                try:
                    color_file.write_text(branch_color)
                except OSError as e:
                    logger.debug(f"Could not write branch color cache: {e}")
            else:
                # Use cached custom images
                branch_images = {
                    "vline": str(theme_assets_dir / "branch-vline.png"),
                    "more": str(theme_assets_dir / "branch-more.png"),
                    "end": str(theme_assets_dir / "branch-end.png"),
                    "arrow_closed": str(theme_assets_dir / "branch-closed.png"),
                    "arrow_open": str(theme_assets_dir / "branch-open.png"),
                }
        else:
            # Use default images
            branch_images = {
                "vline": str(ASSETS_PATH / "branch-vline.png"),
                "more": str(ASSETS_PATH / "branch-more.png"),
                "end": str(ASSETS_PATH / "branch-end.png"),
                "arrow_closed": str(ASSETS_PATH / "branch-closed.png"),
                "arrow_open": str(ASSETS_PATH / "branch-open.png"),
            }

        # Generate dropdown arrow for ComboBox
        combo_fg = colors.get('combo_fg', colors.get('text_primary', '#E6E6E6'))
        dropdown_arrow_color_file = theme_assets_dir / "dropdown_arrow_color.txt"
        cached_dropdown_color = None
        if dropdown_arrow_color_file.exists():
            try:
                cached_dropdown_color = dropdown_arrow_color_file.read_text().strip()
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Could not read dropdown arrow cache: {e}")

        # Generate dropdown arrow if color changed or not exists
        dropdown_arrow_path = theme_assets_dir / "dropdown-arrow.png"
        if cached_dropdown_color != combo_fg or not dropdown_arrow_path.exists():
            dropdown_arrow = generate_dropdown_arrow(combo_fg, theme_assets_dir)
            try:
                dropdown_arrow_color_file.write_text(combo_fg)
            except OSError as e:
                logger.debug(f"Could not write dropdown arrow cache: {e}")
        else:
            dropdown_arrow = str(dropdown_arrow_path)

        # Convert to CSS-friendly paths
        branch_vline = branch_images["vline"].replace("\\", "/")
        branch_more = branch_images["more"].replace("\\", "/")
        branch_end = branch_images["end"].replace("\\", "/")
        arrow_closed = branch_images["arrow_closed"].replace("\\", "/")
        arrow_open = branch_images["arrow_open"].replace("\\", "/")
        dropdown_arrow_css = dropdown_arrow.replace("\\", "/") if dropdown_arrow else ""

        # Build comprehensive QSS
        qss = f"""
        /* ========== BASE WIDGET ========== */
        QWidget {{
            background-color: {colors['window_bg']};
            color: {colors['text_primary']};
            font-size: 9pt;
        }}

        /* ========== MAIN WINDOW CONTAINER ========== */
        #CentralWidget {{
            border-radius: {border_radius};
        }}

        /* ========== FRAMES/PANELS ========== */
        QFrame {{
            border-radius: {border_radius};
        }}
        QGroupBox {{
            border: 1px solid {colors['border_color']};
            border-radius: {border_radius};
            margin-top: 8px;
            padding-top: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: {colors['text_primary']};
        }}

        /* ========== LABELS ========== */
        QLabel {{
            color: {colors['text_primary']};
            background-color: transparent;
        }}

        /* ========== BUTTONS (panels/dialogs) ========== */
        QPushButton {{
            background-color: {colors['button_bg']};
            color: {colors['button_fg']};
            border: 1px solid {colors['button_border']};
            padding: 5px 15px;
            border-radius: 2px;
        }}
        QPushButton:hover {{
            background-color: {colors['button_hover_bg']};
            color: {colors['button_hover_fg']};
        }}
        QPushButton:pressed {{
            background-color: {colors['button_pressed_bg']};
        }}
        QPushButton:disabled {{
            background-color: {colors['panel_bg']};
            color: {colors['text_disabled']};
        }}

        /* ========== TOOLBAR ========== */
        #ToolbarWidget {{
            background-color: {colors.get('toolbar_bg', colors['panel_bg'])};
            border: none;
        }}
        #ToolbarWidget QPushButton {{
            background-color: {colors.get('toolbarbtn_bg', colors['panel_bg'])};
            color: {colors.get('toolbarbtn_fg', colors['text_primary'])};
            border: 1px solid {colors.get('toolbarbtn_border', colors['panel_bg'])};
            padding: 4px 10px;
            border-radius: 2px;
        }}
        #ToolbarWidget QPushButton:hover {{
            background-color: {colors.get('toolbarbtn_hover_bg', colors['hover_bg'])};
            color: {colors.get('toolbarbtn_hover_fg', colors['text_primary'])};
        }}
        #ToolbarWidget QPushButton:pressed {{
            background-color: {colors.get('toolbarbtn_pressed_bg', colors['selected_bg'])};
        }}
        #ToolbarWidget QPushButton:disabled {{
            background-color: {colors['panel_bg']};
            color: {colors['text_disabled']};
        }}

        /* ========== INPUT FIELDS ========== */
        QLineEdit {{
            background-color: {colors['input_bg']};
            color: {colors['input_fg']};
            border: 1px solid {colors['input_border']};
            padding: 4px;
            border-radius: 2px;
        }}
        QLineEdit:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}
        QLineEdit:disabled {{
            background-color: {colors['panel_bg']};
            color: {colors['text_disabled']};
        }}

        QTextEdit {{
            background-color: {colors['editor_bg']};
            color: {colors['editor_fg']};
            border: 1px solid {colors['input_border']};
            padding: 4px;
            selection-background-color: {colors.get('editor_selection_bg', colors['selected_bg'])};
            selection-color: {colors.get('editor_selection_fg', colors['text_primary'])};
        }}
        QTextEdit:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}

        QPlainTextEdit {{
            background-color: {colors['editor_bg']};
            color: {colors['editor_fg']};
            border: 1px solid {colors['input_border']};
            padding: 4px;
            selection-background-color: {colors.get('editor_selection_bg', colors['selected_bg'])};
            selection-color: {colors.get('editor_selection_fg', colors['text_primary'])};
        }}
        QPlainTextEdit:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}

        /* ========== COMBOBOX ========== */
        QComboBox {{
            background-color: {colors['combo_bg']};
            color: {colors['combo_fg']};
            border: 1px solid {colors['input_border']};
            padding: 4px;
            border-radius: 2px;
        }}
        QComboBox:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: url({dropdown_arrow_css});
            width: 10px;
            height: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors['dd_menu_bg']};
            color: {colors['dd_menu_fg']};
            selection-background-color: {colors['dd_menu_hover_bg']};
            border: 1px solid {colors['border_color']};
            outline: none;
        }}

        /* ========== TREE WIDGET ========== */
        QTreeWidget {{
            background-color: {colors['tree_line1_bg']};
            color: {colors['tree_line1_fg']};
            border: 1px solid {colors['border_color']};
            border-radius: {border_radius};
            alternate-background-color: {colors['tree_line2_bg']};
            outline: none;
        }}
        QTreeWidget::item {{
            padding: 0px;
            color: {colors['tree_line1_fg']};
        }}
        QTreeWidget::item:alternate {{
            background-color: {colors['tree_line2_bg']};
            color: {colors['tree_line2_fg']};
        }}
        QTreeWidget::item:selected {{
            background-color: {colors['tree_selected_bg']};
            color: {colors['tree_selected_fg']};
        }}
        QTreeWidget::item:hover {{
            background-color: {colors['tree_hover_bg']};
        }}
        /* Tree branch lines using centered SVG images */
        QTreeWidget::branch {{
            background: {colors['tree_line1_bg']};
        }}
        /* Vertical line continuation (│) */
        QTreeWidget::branch:has-siblings:!adjoins-item {{
            background: url({branch_vline}) center center no-repeat;
        }}
        /* Intermediate children (├) */
        QTreeWidget::branch:has-siblings:adjoins-item {{
            background: url({branch_more}) center center no-repeat;
        }}
        /* Last child (└) */
        QTreeWidget::branch:!has-siblings:adjoins-item {{
            background: url({branch_end}) center center no-repeat;
        }}
        /* Expand/collapse arrows */
        /* Override background to transparent so arrows are visible */
        QTreeWidget::branch:has-children:closed {{
            background: {colors['tree_line1_bg']};
            image: url({arrow_closed});
        }}
        QTreeWidget::branch:has-children:open {{
            background: {colors['tree_line1_bg']};
            image: url({arrow_open});
        }}

        /* ========== TABLE WIDGET ========== */
        QTableWidget {{
            background-color: {colors['grid_line1_bg']};
            color: {colors['grid_line1_fg']};
            border: 1px solid {colors['border_color']};
            border-radius: {border_radius};
            alternate-background-color: {colors['grid_line2_bg']};
            outline: none;
            font-family: Consolas;
            font-size: 9pt;
            gridline-color: transparent;
        }}
        QTableWidget::item {{
            padding: 0px;
            margin: 0px;
            border: none;
            color: {colors['grid_line1_fg']};
        }}
        QTableWidget::item:alternate {{
            background-color: {colors['grid_line2_bg']};
            color: {colors['grid_line2_fg']};
        }}
        QTableWidget::item:selected {{
            background-color: {colors['grid_selected_bg']};
            color: {colors['grid_selected_fg']};
        }}
        QTableWidget::item:hover {{
            background-color: {colors['grid_hover_bg']};
        }}

        /* ========== HEADER VIEWS ========== */
        /* Default header style (used by tables) */
        QHeaderView::section {{
            background-color: {colors['grid_header_bg']};
            color: {colors['grid_header_fg']};
            padding: 4px;
            border: 1px solid {colors['border_color']};
            border-top: none;
            border-left: none;
        }}
        QHeaderView::section:hover {{
            background-color: {colors['hover_bg']};
        }}
        /* TreeWidget specific header */
        QTreeWidget QHeaderView::section {{
            background-color: {colors['tree_heading_bg']};
            color: {colors['tree_heading_fg']};
        }}

        /* ========== TABS ========== */
        QTabWidget::pane {{
            border: 1px solid {colors['border_color']};
            background-color: {colors['window_bg']};
        }}
        QTabBar::tab {{
            background-color: {colors['tab_bg']};
            color: {colors['tab_fg']};
            border: 1px solid {colors['border_color']};
            padding: 6px 12px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {colors['tab_selected_bg']};
            color: {colors['tab_selected_fg']};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {colors['tab_hover_bg']};
        }}

        /* ========== SCROLLBARS ========== */
        QScrollBar:vertical {{
            background-color: {colors['scrollbar_bg']};
            width: 14px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background-color: {colors['scrollbar_handle_bg']};
            min-height: 20px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['scrollbar_handle_hover_bg']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QScrollBar:horizontal {{
            background-color: {colors['scrollbar_bg']};
            height: 14px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {colors['scrollbar_handle_bg']};
            min-width: 20px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['scrollbar_handle_hover_bg']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        /* ========== SPLITTER ========== */
        QSplitter::handle {{
            background-color: {colors.get('splitter_bg', '#5a5a5a')};
        }}
        QSplitter::handle:hover {{
            background-color: {colors.get('splitter_hover_bg', colors['focus_border'])};
        }}
        QSplitter::handle:horizontal {{
            width: 4px;
        }}
        QSplitter::handle:vertical {{
            height: 4px;
        }}

        /* ========== GROUPBOX ========== */
        QGroupBox {{
            color: {colors['groupbox_title_fg']};
            border: 1px solid {colors['groupbox_border']};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }}

        /* ========== CHECKBOX ========== */
        QCheckBox {{
            color: {colors['checkbox_fg']};
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors['checkbox_border']};
            background-color: {colors['checkbox_bg']};
            border-radius: 2px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors['checkbox_checked_bg']};
            border: 1px solid {colors['checkbox_checked_bg']};
        }}
        QCheckBox::indicator:hover {{
            border: 1px solid {colors['focus_border']};
        }}

        /* ========== RADIO BUTTON ========== */
        QRadioButton {{
            color: {colors['checkbox_fg']};
            spacing: 5px;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors['checkbox_border']};
            background-color: {colors['checkbox_bg']};
            border-radius: 8px;
        }}
        QRadioButton::indicator:checked {{
            background-color: {colors['checkbox_checked_bg']};
            border: 1px solid {colors['checkbox_checked_bg']};
        }}

        /* ========== TOOLTIP ========== */
        QToolTip {{
            background-color: {colors['tooltip_bg']};
            color: {colors['tooltip_fg']};
            border: 1px solid {colors['tooltip_border']};
            padding: 4px;
        }}

        /* ========== PROGRESS BAR ========== */
        QProgressBar {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            border-radius: 2px;
            text-align: center;
            color: {colors['text_primary']};
        }}
        QProgressBar::chunk {{
            background-color: {colors['selected_bg']};
        }}

        /* ========== MENU BAR (custom from window-template) ========== */
        /* Handled by window-template, but ensure consistency */

        /* ========== MESSAGE BOX / DIALOG ========== */
        QDialog {{
            background-color: {colors['window_bg']};
            color: {colors['text_primary']};
        }}
        QMessageBox {{
            background-color: {colors['window_bg']};
        }}
        """

        return qss


# Convenience function for global access
def get_theme_bridge():
    """Get the global ThemeBridge instance"""
    return ThemeBridge.get_instance()
