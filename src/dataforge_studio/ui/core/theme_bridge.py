"""
Theme Bridge - Extends window-template ThemeManager with Observer pattern
Fusion of window-template theme system and DataForge Studio theme management
"""

from typing import List, Callable, Dict
from ..window_template.theme_manager import ThemeManager as BaseThemeManager


class ThemeBridge(BaseThemeManager):
    """
    Extended theme manager with Observer pattern for DataForge Studio.

    This class bridges the window-template theme system with DataForge Studio's
    needs, adding:
    - Observer pattern for notifying widgets of theme changes
    - Additional QSS generation methods for custom widgets
    - Support for DataForge-specific color keys
    """

    _instance = None

    def __init__(self, theme_file=None):
        super().__init__(theme_file)
        self._observers: List[Callable] = []

    @classmethod
    def get_instance(cls):
        """Get singleton instance of ThemeBridge"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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
        for observer in self._observers:
            try:
                observer(theme_colors)
            except Exception as e:
                print(f"Error notifying theme observer: {e}")

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
                    background-color: {colors['tree_bg']};
                    color: {colors['tree_fg']};
                    border: 1px solid {colors['border_color']};
                    alternate-background-color: {colors['panel_bg']};
                }}
                QTreeWidget::item:selected {{
                    background-color: {colors['tree_selected_bg']};
                    color: {colors['tree_selected_fg']};
                }}
                QTreeWidget::item:hover {{
                    background-color: {colors['button_hover_bg']};
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
                    background-color: {colors['grid_bg']};
                    color: {colors['grid_fg']};
                    gridline-color: {colors['grid_gridline_color']};
                    border: 1px solid {colors['border_color']};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors['grid_selected_bg']};
                }}
                QTableWidget::item:hover {{
                    background-color: {colors['button_hover_bg']};
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


# Convenience function for global access
def get_theme_bridge():
    """Get the global ThemeBridge instance"""
    return ThemeBridge.get_instance()
