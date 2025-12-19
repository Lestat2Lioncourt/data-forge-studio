"""Theme manager for loading and applying color themes."""

import json
from pathlib import Path
from typing import Dict, Optional


def _lighten_color(hex_color: str, percent: int) -> str:
    """Lighten a hex color by a percentage."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = min(255, r + int((255 - r) * percent / 100))
    g = min(255, g + int((255 - g) * percent / 100))
    b = min(255, b + int((255 - b) * percent / 100))

    return f"#{r:02x}{g:02x}{b:02x}"


def _darken_color(hex_color: str, percent: int) -> str:
    """Darken a hex color by a percentage."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = max(0, r - int(r * percent / 100))
    g = max(0, g - int(g * percent / 100))
    b = max(0, b - int(b * percent / 100))

    return f"#{r:02x}{g:02x}{b:02x}"


def _expand_minimal_palette(palette: Dict[str, str]) -> Dict[str, str]:
    """
    Expand a minimal palette (~20 colors) into full theme colors (90+ properties).

    Minimal palette structure:
        Window: TopBar_BG/FG, MenuBar_BG/FG, MenuBar_Hover_BG/FG, MenuBar_Selected_BG/FG, StatusBar_BG/FG
        Frames: Frame_BG, Frame_FG, Frame_FG_Secondary
        Data: Data_BG, Data_FG, Data_Border
        Interactive: Hover_BG, Selected_BG, Selected_FG, Accent
        Semantic: Normal_FG, Success_FG, Warning_FG, Error_FG, Info_FG

    Args:
        palette: Minimal palette dict

    Returns:
        Full colors dict compatible with existing theme system
    """
    is_dark = palette.get("is_dark", True)

    # Extract palette colors
    topbar_bg = palette["TopBar_BG"]
    topbar_fg = palette["TopBar_FG"]
    menubar_bg = palette["MenuBar_BG"]
    menubar_fg = palette["MenuBar_FG"]
    statusbar_bg = palette["StatusBar_BG"]
    statusbar_fg = palette["StatusBar_FG"]

    frame_bg = palette["Frame_BG"]
    frame_fg = palette["Frame_FG"]
    frame_fg_secondary = palette["Frame_FG_Secondary"]

    data_bg = palette["Data_BG"]
    data_fg = palette["Data_FG"]
    data_border = palette["Data_Border"]

    hover_bg = palette["Hover_BG"]
    selected_bg = palette["Selected_BG"]
    selected_fg = palette["Selected_FG"]
    accent = palette["Accent"]

    normal_fg = palette["Normal_FG"]
    success_fg = palette["Success_FG"]
    warning_fg = palette["Warning_FG"]
    error_fg = palette["Error_FG"]
    info_fg = palette["Info_FG"]

    # Derive additional colors
    if is_dark:
        pressed_bg = _lighten_color(hover_bg, 10)
        alternate_bg = _lighten_color(data_bg, 3)
        default_menu_hover_bg = _lighten_color(menubar_bg, 15)
        default_menu_selected_bg = _lighten_color(menubar_bg, 25)
        scrollbar_hover = _lighten_color(data_border, 15)
        selection_bg = _darken_color(accent, 30)
        window_bg = _darken_color(frame_bg, 10)
    else:
        pressed_bg = _darken_color(hover_bg, 10)
        alternate_bg = _darken_color(data_bg, 2)
        default_menu_hover_bg = _darken_color(menubar_bg, 10)
        default_menu_selected_bg = _darken_color(menubar_bg, 15)
        scrollbar_hover = _darken_color(data_border, 15)
        selection_bg = _lighten_color(accent, 40)
        window_bg = _darken_color(frame_bg, 5)

    # Get MenuBar hover/selected colors (optional, with defaults)
    menubar_hover_bg = palette.get("MenuBar_Hover_BG", default_menu_hover_bg)
    menubar_hover_fg = palette.get("MenuBar_Hover_FG", menubar_fg)
    menubar_selected_bg = palette.get("MenuBar_Selected_BG", default_menu_selected_bg)
    menubar_selected_fg = palette.get("MenuBar_Selected_FG", menubar_fg)

    # Get Dropdown menu colors (optional, with defaults)
    dd_menu_bg = palette.get("DD_Menu_BG", data_bg)
    dd_menu_fg = palette.get("DD_Menu_FG", data_fg)
    dd_menu_hover_bg = palette.get("DD_Menu_Hover_BG", menubar_hover_bg)
    dd_menu_hover_fg = palette.get("DD_Menu_Hover_FG", data_fg)
    dd_menu_selected_bg = palette.get("DD_Menu_Selected_BG", selected_bg)
    dd_menu_selected_fg = palette.get("DD_Menu_Selected_FG", selected_fg)

    # Get Toolbar Button colors (optional, with defaults)
    toolbarbtn_bg = palette.get("ToolbarBtn_BG", frame_bg)
    toolbarbtn_fg = palette.get("ToolbarBtn_FG", frame_fg)
    toolbarbtn_hover_bg = palette.get("ToolbarBtn_Hover_BG", hover_bg)
    toolbarbtn_hover_fg = palette.get("ToolbarBtn_Hover_FG", normal_fg)
    toolbarbtn_pressed_bg = palette.get("ToolbarBtn_Pressed_BG", selected_bg)
    toolbarbtn_border = palette.get("ToolbarBtn_Border", frame_bg)

    # Get Button colors (optional, with defaults) - for panels/dialogs
    button_bg = palette.get("Button_BG", data_bg)
    button_fg = palette.get("Button_FG", normal_fg)
    button_hover_bg = palette.get("Button_Hover_BG", hover_bg)
    button_hover_fg = palette.get("Button_Hover_FG", normal_fg)
    button_pressed_bg = palette.get("Button_Pressed_BG", selected_bg)
    button_border = palette.get("Button_Border", data_border)

    # Get Grid alternating row colors (optional, with defaults)
    grid_line1_bg = palette.get("Grid_Line1_BG", data_bg)
    grid_line1_fg = palette.get("Grid_Line1_FG", frame_fg)
    grid_line2_bg = palette.get("Grid_Line2_BG", alternate_bg)
    grid_line2_fg = palette.get("Grid_Line2_FG", frame_fg)
    grid_header_bg = palette.get("Grid_Header_BG", frame_bg)
    grid_header_fg = palette.get("Grid_Header_FG", normal_fg)

    # Get TreeView colors (optional, with defaults)
    tree_bg = palette.get("Tree_BG", data_bg)
    tree_fg = palette.get("Tree_FG", frame_fg)
    tree_line1_bg = palette.get("Tree_Line1_BG", data_bg)
    tree_line1_fg = palette.get("Tree_Line1_FG", frame_fg)
    tree_line2_bg = palette.get("Tree_Line2_BG", alternate_bg)
    tree_line2_fg = palette.get("Tree_Line2_FG", frame_fg)
    tree_header_bg = palette.get("Tree_Header_BG", frame_bg)
    tree_header_fg = palette.get("Tree_Header_FG", normal_fg)
    tree_branch_color = palette.get("Tree_Branch_Color", frame_fg_secondary)

    # Get Frame styling (optional, with defaults)
    frame_border_radius = palette.get("Frame_Border_Radius", "0")

    # Get Splitter colors (optional, with defaults - use visible gray)
    splitter_bg = palette.get("Splitter_BG", "#4d4d4d")
    splitter_hover_bg = palette.get("Splitter_Hover_BG", accent)

    # Get Log panel colors (optional, with defaults)
    log_bg = palette.get("Log_BG", data_bg)

    # Get GroupBox colors (optional, with defaults)
    groupbox_border = palette.get("GroupBox_Border", data_border)
    groupbox_title_fg = palette.get("GroupBox_Title_FG", normal_fg)

    # Get Tab/Onglet colors (optional, with defaults)
    tab_bg = palette.get("Tab_BG", frame_bg)
    tab_fg = palette.get("Tab_FG", frame_fg_secondary)
    tab_selected_bg = palette.get("Tab_Selected_BG", data_bg)
    tab_selected_fg = palette.get("Tab_Selected_FG", normal_fg)
    tab_hover_bg = palette.get("Tab_Hover_BG", hover_bg)

    # Get Section Header colors (optional, with defaults)
    sectionheader_bg = palette.get("SectionHeader_BG", frame_bg)
    sectionheader_fg = palette.get("SectionHeader_FG", frame_fg)
    sectionheader_hover_bg = palette.get("SectionHeader_Hover_BG", hover_bg)

    # Build full colors dict
    colors = {
        # Base palette
        "window_bg": window_bg,
        "panel_bg": frame_bg,
        "data_bg": data_bg,
        "border_color": data_border,

        # Text colors
        "text_primary": frame_fg,
        "text_secondary": frame_fg_secondary,
        "text_disabled": frame_fg_secondary,

        # Interactive states
        "hover_bg": hover_bg,
        "pressed_bg": pressed_bg,
        "selected_bg": selected_bg,
        "selected_fg": selected_fg,
        "focus_border": accent,

        # Toolbar Buttons (at top of managers)
        "toolbarbtn_bg": toolbarbtn_bg,
        "toolbarbtn_fg": toolbarbtn_fg,
        "toolbarbtn_hover_bg": toolbarbtn_hover_bg,
        "toolbarbtn_hover_fg": toolbarbtn_hover_fg,
        "toolbarbtn_pressed_bg": toolbarbtn_pressed_bg,
        "toolbarbtn_border": toolbarbtn_border,

        # Buttons (in panels/dialogs)
        "button_bg": button_bg,
        "button_fg": button_fg,
        "button_hover_bg": button_hover_bg,
        "button_hover_fg": button_hover_fg,
        "button_pressed_bg": button_pressed_bg,
        "button_border": button_border,

        # Menus (window-template)
        "main_menu_bar_bg": topbar_bg,
        "main_menu_bar_fg": topbar_fg,
        "feature_menu_bar_bg": menubar_bg,
        "feature_menu_bar_fg": menubar_fg,
        "feature_menu_bar_hover_bg": menubar_hover_bg,
        "feature_menu_bar_hover_fg": menubar_hover_fg,
        "feature_menu_bar_selected_bg": menubar_selected_bg,
        "feature_menu_bar_selected_fg": menubar_selected_fg,
        "dd_menu_bg": dd_menu_bg,
        "dd_menu_fg": dd_menu_fg,
        "dd_menu_hover_bg": dd_menu_hover_bg,
        "dd_menu_hover_fg": dd_menu_hover_fg,
        "dd_menu_selected_bg": dd_menu_selected_bg,
        "dd_menu_selected_fg": dd_menu_selected_fg,
        "dd_menu_separator": data_border,

        # Status bar
        "status_bar_bg": statusbar_bg,
        "status_bar_fg": statusbar_fg,

        # Tree
        "tree_bg": tree_bg,
        "tree_fg": tree_fg,
        "tree_selected_bg": selected_bg,
        "tree_selected_fg": selected_fg,
        "tree_hover_bg": hover_bg,
        "tree_heading_bg": tree_header_bg,
        "tree_heading_fg": tree_header_fg,
        "tree_line1_bg": tree_line1_bg,
        "tree_line1_fg": tree_line1_fg,
        "tree_line2_bg": tree_line2_bg,
        "tree_line2_fg": tree_line2_fg,
        "tree_branch_color": tree_branch_color,

        # Frame styling
        "frame_border_radius": frame_border_radius,

        # Splitter
        "splitter_bg": splitter_bg,
        "splitter_hover_bg": splitter_hover_bg,

        # Grid
        "grid_bg": data_bg,
        "grid_fg": data_fg,
        "grid_gridline": data_border,
        "grid_header_bg": grid_header_bg,
        "grid_header_fg": grid_header_fg,
        "grid_selected_bg": selected_bg,
        "grid_selected_fg": selected_fg,
        "grid_hover_bg": hover_bg,
        "grid_line1_bg": grid_line1_bg,
        "grid_line1_fg": grid_line1_fg,
        "grid_line2_bg": grid_line2_bg,
        "grid_line2_fg": grid_line2_fg,

        # Editor
        "editor_bg": data_bg,
        "editor_fg": data_fg,
        "editor_selection_bg": selection_bg,
        "editor_current_line_bg": hover_bg,
        "editor_line_number_bg": frame_bg,
        "editor_line_number_fg": frame_fg_secondary,

        # Input fields
        "input_bg": data_bg,
        "input_fg": data_fg,
        "input_border": data_border,
        "input_focus_border": accent,
        "input_placeholder_fg": frame_fg_secondary,

        # Combobox
        "combo_bg": data_bg,
        "combo_fg": data_fg,

        # Semantic colors
        "error_fg": error_fg,
        "warning_fg": warning_fg,
        "success_fg": success_fg,
        "info_fg": info_fg,
        "normal_fg": normal_fg,

        # Log panel
        "log_bg": log_bg,
        "log_fg": data_fg,
        "log_info_fg": info_fg,
        "log_warning_fg": warning_fg,
        "log_error_fg": error_fg,
        "log_success_fg": success_fg,
        "log_debug_fg": frame_fg_secondary,

        # SQL syntax highlighting (derived from semantic colors)
        "sql_keyword": accent,
        "sql_string": success_fg,
        "sql_comment": frame_fg_secondary,
        "sql_number": info_fg,
        "sql_function": warning_fg,
        "sql_operator": data_fg,
        "sql_identifier": info_fg,

        # Tabs / Onglets
        "tab_bg": tab_bg,
        "tab_fg": tab_fg,
        "tab_selected_bg": tab_selected_bg,
        "tab_selected_fg": tab_selected_fg,
        "tab_hover_bg": tab_hover_bg,

        # Scrollbars
        "scrollbar_bg": window_bg,
        "scrollbar_handle_bg": data_border,
        "scrollbar_handle_hover_bg": scrollbar_hover,

        # Splitter
        "splitter_bg": splitter_bg,
        "splitter_hover_bg": splitter_hover_bg,

        # Groupbox
        "groupbox_border": groupbox_border,
        "groupbox_title_fg": groupbox_title_fg,

        # Section Headers
        "sectionheader_bg": sectionheader_bg,
        "sectionheader_fg": sectionheader_fg,
        "sectionheader_hover_bg": sectionheader_hover_bg,

        # Checkbox
        "checkbox_bg": data_bg,
        "checkbox_border": data_border,
        "checkbox_checked_bg": accent,
        "checkbox_fg": normal_fg,

        # Tooltip
        "tooltip_bg": menubar_bg,
        "tooltip_fg": menubar_fg,
        "tooltip_border": accent,
    }

    return colors


class ThemeManager:
    """Manages color themes for the application."""

    def __init__(self, theme_file: Optional[str] = None):
        """
        Initialize theme manager.

        Args:
            theme_file: Path to themes JSON file. If None, uses default themes.json
        """
        if theme_file is None:
            theme_file = Path(__file__).parent / "themes.json"
        else:
            theme_file = Path(theme_file)

        self.themes = self._load_themes(theme_file)
        self.current_theme = "dark_mode"
        self._expanded_cache: Dict[str, Dict[str, str]] = {}  # Cache for expanded palettes

    def _load_themes(self, theme_file: Path) -> Dict:
        """Load themes from JSON file."""
        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Theme file not found: {theme_file}")
            return self._get_default_theme()
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in theme file: {e}")
            return self._get_default_theme()

    def _get_default_theme(self) -> Dict:
        """Return minimal default theme if file can't be loaded."""
        return {
            "dark_mode": {
                "name": "Thème Sombre",
                "colors": {
                    "main_menu_bar_bg": "#2b2b2b",
                    "main_menu_bar_fg": "#ffffff",
                    "feature_menu_bar_bg": "#3d3d3d",
                    "feature_menu_bar_fg": "#ffffff",
                    "status_bar_bg": "#2b2b2b",
                    "status_bar_fg": "#ffffff",
                    "dd_menu_bg": "#3d3d3d",
                    "dd_menu_fg": "#ffffff",
                    "dd_menu_hover_bg": "#4d4d4d",
                    "dd_menu_separator": "#4d4d4d",
                    "window_bg": "#1e1e1e",
                    "panel_bg": "#2d2d2d",
                    "border_color": "#3d3d3d",
                    "button_hover_bg": "#4d4d4d",
                    "button_pressed_bg": "#5d5d5d",
                    "error_fg": "#e74c3c",
                    "warning_fg": "#f39c12",
                    "success_fg": "#2ecc71",
                    "normal_fg": "#ffffff"
                }
            }
        }

    def get_available_themes(self) -> Dict[str, str]:
        """
        Get list of available theme names.

        Returns:
            Dict mapping theme_id to display name
        """
        return {
            theme_id: theme_data.get("name", theme_id)
            for theme_id, theme_data in self.themes.items()
            if isinstance(theme_data, dict) and not theme_id.startswith("_comment")
        }

    def get_theme_colors(self, theme_name: str = None) -> Dict[str, str]:
        """
        Get color dictionary for a theme.

        Supports:
        - Traditional themes (with "colors" dict)
        - Minimal themes (with "palette" dict, ~20 colors expanded to 90+)

        Args:
            theme_name: Theme identifier (e.g., "dark_mode", "minimal_dark").
                       If None, uses current_theme.

        Returns:
            Dictionary of color variables
        """
        if theme_name is None:
            theme_name = self.current_theme

        if theme_name not in self.themes:
            print(f"Warning: Theme '{theme_name}' not found, using 'dark_mode'")
            theme_name = "dark_mode"

        theme_data = self.themes[theme_name]

        # Check if this is a minimal theme (has "palette" instead of "colors")
        if theme_data.get("type") == "minimal" and "palette" in theme_data:
            # Use cache if available
            if theme_name in self._expanded_cache:
                return self._expanded_cache[theme_name]

            # Expand minimal palette to full colors
            palette = theme_data["palette"]
            expanded = _expand_minimal_palette(palette)

            # Cache the result
            self._expanded_cache[theme_name] = expanded
            return expanded

        # Traditional theme with full colors dict
        colors = theme_data["colors"]

        # Ensure tab_* values exist with fallbacks
        if "tab_bg" not in colors:
            colors["tab_bg"] = colors.get("panel_bg", colors.get("frame_bg", "#252525"))
        if "tab_fg" not in colors:
            colors["tab_fg"] = colors.get("text_secondary", colors.get("fg", "#b0b0b0"))
        if "tab_selected_bg" not in colors:
            colors["tab_selected_bg"] = colors.get("data_bg", colors.get("bg", "#2d2d2d"))
        if "tab_selected_fg" not in colors:
            colors["tab_selected_fg"] = colors.get("text_primary", colors.get("fg", "#ffffff"))
        if "tab_hover_bg" not in colors:
            colors["tab_hover_bg"] = colors.get("hover_bg", "#383838")

        return colors

    def is_minimal_theme(self, theme_name: str) -> bool:
        """Check if a theme uses the minimal palette format."""
        if theme_name not in self.themes:
            return False
        return self.themes[theme_name].get("type") == "minimal"

    def clear_cache(self, theme_name: str = None):
        """Clear the expanded palette cache.

        Args:
            theme_name: Specific theme to clear, or None to clear all
        """
        if theme_name:
            self._expanded_cache.pop(theme_name, None)
        else:
            self._expanded_cache.clear()

    def apply_theme(self, window, theme_name: str):
        """
        Apply a theme to a TemplateWindow.

        Args:
            window: TemplateWindow instance
            theme_name: Theme identifier (e.g., "dark_mode")
        """
        colors = self.get_theme_colors(theme_name)
        self.current_theme = theme_name

        # Apply to title bar
        if hasattr(window, 'title_bar'):
            window.title_bar.setStyleSheet(f"""
                TitleBar {{
                    background-color: {colors['main_menu_bar_bg']};
                    border-bottom: 1px solid {colors['border_color']};
                }}
                QLabel {{
                    background-color: transparent;
                    color: {colors['main_menu_bar_fg']};
                    padding-left: 10px;
                }}
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {colors['main_menu_bar_fg']};
                    font-size: 16px;
                    padding: 0px;
                    margin: 0px;
                }}
            """)

        # Apply to menu bar
        if hasattr(window, 'menu_bar'):
            menu_hover_bg = colors.get('feature_menu_bar_hover_bg', colors['button_hover_bg'])
            menu_hover_fg = colors.get('feature_menu_bar_hover_fg', colors['feature_menu_bar_fg'])
            menu_selected_bg = colors.get('feature_menu_bar_selected_bg', colors['button_pressed_bg'])
            menu_selected_fg = colors.get('feature_menu_bar_selected_fg', colors['feature_menu_bar_fg'])

            window.menu_bar.setStyleSheet(f"""
                MenuBar {{
                    background-color: {colors['feature_menu_bar_bg']};
                    border-bottom: 1px solid {colors['border_color']};
                }}
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {colors['feature_menu_bar_fg']};
                    padding: 5px 15px;
                    text-align: center;
                    text-transform: uppercase;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {menu_hover_bg};
                    color: {menu_hover_fg};
                }}
                QPushButton:pressed, QPushButton:checked {{
                    background-color: {menu_selected_bg};
                    color: {menu_selected_fg};
                }}
                QPushButton::menu-indicator {{
                    width: 0px;
                }}
            """)

            # Update dropdown menus styling
            self._update_menu_styles(window.menu_bar, colors)

        # Apply to status bar
        if hasattr(window, 'status_bar'):
            window.status_bar.setStyleSheet(f"""
                StatusBar {{
                    background-color: {colors['status_bar_bg']};
                    border-top: 1px solid {colors['border_color']};
                }}
                QLabel {{
                    color: {colors['status_bar_fg']};
                    padding: 5px 10px;
                }}
            """)

        # Apply to main window background (only the central widget itself, not children)
        if hasattr(window, 'centralWidget'):
            central = window.centralWidget()
            if central:
                # Use specific class name to avoid overriding child widgets
                central.setObjectName("CentralWidget")
                central.setStyleSheet(f"""
                    #CentralWidget {{
                        background-color: {colors['window_bg']};
                    }}
                """)

        # Apply to panels (override hardcoded inline styles)
        if hasattr(window, 'left_panel'):
            window.left_panel.setStyleSheet(f"background-color: {colors['panel_bg']};")
        if hasattr(window, 'right_top_panel'):
            window.right_top_panel.setStyleSheet(f"background-color: {colors['panel_bg']};")
        if hasattr(window, 'right_bottom_panel'):
            window.right_bottom_panel.setStyleSheet(f"background-color: {colors['panel_bg']};")

        # Apply to splitters - explicit styling to ensure visibility
        # Use a visible default if not defined in theme
        splitter_bg = colors.get('splitter_bg', '#5a5a5a')  # Lighter gray for visibility
        splitter_hover_bg = colors.get('splitter_hover_bg', colors['focus_border'])
        splitter_style = f"""
            QSplitter::handle {{
                background-color: {splitter_bg};
            }}
            QSplitter::handle:hover {{
                background-color: {splitter_hover_bg};
            }}
        """
        if hasattr(window, 'main_splitter'):
            window.main_splitter.setStyleSheet(splitter_style)
        if hasattr(window, 'right_splitter'):
            window.right_splitter.setStyleSheet(splitter_style)

        # Update wrapper background if exists
        parent = window.parent()
        if parent:
            if hasattr(parent, 'set_background_color'):
                parent.set_background_color(colors['window_bg'])
            if hasattr(parent, 'update'):
                parent.update()

    def _update_menu_styles(self, menu_bar, colors: Dict[str, str]):
        """Update styles for all dropdown menus in the menu bar."""
        dd_hover_bg = colors.get('dd_menu_hover_bg', colors['button_hover_bg'])
        dd_hover_fg = colors.get('dd_menu_hover_fg', colors['dd_menu_fg'])
        dd_selected_bg = colors.get('dd_menu_selected_bg', colors['selected_bg'])
        dd_selected_fg = colors.get('dd_menu_selected_fg', colors['selected_fg'])

        for button in menu_bar.buttons.values():
            menu = button.menu()
            if menu:
                menu.setStyleSheet(f"""
                    QMenu {{
                        background-color: {colors['dd_menu_bg']};
                        border: 1px solid {colors['border_color']};
                        color: {colors['dd_menu_fg']};
                        padding: 5px;
                    }}
                    QMenu::item {{
                        padding: 5px 20px;
                        background-color: transparent;
                    }}
                    QMenu::item:selected {{
                        background-color: {dd_hover_bg};
                        color: {dd_hover_fg};
                    }}
                    QMenu::item:pressed {{
                        background-color: {dd_selected_bg};
                        color: {dd_selected_fg};
                    }}
                    QMenu::separator {{
                        height: 1px;
                        background-color: {colors['dd_menu_separator']};
                        margin: 5px 0px;
                    }}
                """)
