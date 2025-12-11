"""Theme manager for loading and applying color themes."""

import json
from pathlib import Path
from typing import Dict, Optional


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
        }

    def get_theme_colors(self, theme_name: str) -> Dict[str, str]:
        """
        Get color dictionary for a theme.

        Args:
            theme_name: Theme identifier (e.g., "dark_mode")

        Returns:
            Dictionary of color variables
        """
        if theme_name not in self.themes:
            print(f"Warning: Theme '{theme_name}' not found, using 'dark_mode'")
            theme_name = "dark_mode"

        return self.themes[theme_name]["colors"]

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
                }}
                QPushButton:hover {{
                    background-color: {colors['button_hover_bg']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['button_pressed_bg']};
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

        # Apply to main window background
        if hasattr(window, 'centralWidget'):
            central = window.centralWidget()
            if central:
                central.setStyleSheet(f"""
                    QWidget {{
                        background-color: {colors['window_bg']};
                    }}
                """)

        # Apply to splitters
        if hasattr(window, 'main_splitter'):
            window.main_splitter.setStyleSheet(f"""
                QSplitter::handle {{
                    background-color: {colors['border_color']};
                }}
                QSplitter::handle:hover {{
                    background-color: {colors['button_hover_bg']};
                }}
            """)

        if hasattr(window, 'right_splitter'):
            window.right_splitter.setStyleSheet(f"""
                QSplitter::handle {{
                    background-color: {colors['border_color']};
                }}
                QSplitter::handle:hover {{
                    background-color: {colors['button_hover_bg']};
                }}
            """)

        # Update wrapper background if exists
        parent = window.parent()
        if parent:
            if hasattr(parent, 'set_background_color'):
                parent.set_background_color(colors['window_bg'])
            if hasattr(parent, 'update'):
                parent.update()

    def _update_menu_styles(self, menu_bar, colors: Dict[str, str]):
        """Update styles for all dropdown menus in the menu bar."""
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
                        background-color: {colors['dd_menu_hover_bg']};
                    }}
                    QMenu::separator {{
                        height: 1px;
                        background-color: {colors['dd_menu_separator']};
                        margin: 5px 0px;
                    }}
                """)
