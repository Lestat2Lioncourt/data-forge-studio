"""
ThemedWidget - Mixin for theme-aware widgets

Encapsulates the common pattern for theme registration and updates:
    try:
        from ..core.theme_bridge import ThemeBridge
        theme = ThemeBridge.get_instance()
        theme.register_observer(self._on_theme_changed)
    except Exception:
        pass

Usage:
    class MyWidget(ThemedWidgetMixin, QWidget):
        def __init__(self, parent=None):
            QWidget.__init__(self, parent)
            ThemedWidgetMixin.__init__(self)

        def _on_theme_changed(self, theme_colors):
            # Handle theme change
            pass
"""

from typing import Dict, Any, Optional, Callable
from PySide6.QtGui import QColor


class ThemedWidgetMixin:
    """
    Mixin class for widgets that need to respond to theme changes.

    Provides:
    - Automatic theme observer registration
    - Default color loading with fallbacks
    - Common theme color access methods

    Subclasses should implement:
    - _on_theme_changed(theme_colors: Dict[str, str]) - Called when theme changes
    - _get_default_colors() -> Dict[str, str] - Optional: Return default fallback colors
    """

    # Default fallback colors
    DEFAULT_COLORS = {
        "log_info_fg": "#ffffff",
        "log_warning_fg": "#ffa500",
        "log_error_fg": "#ff4444",
        "log_success_fg": "#4ade80",
        "log_debug_fg": "#888888",
        "fg": "#ffffff",
        "bg": "#2d2d2d",
    }

    def __init__(self):
        """Initialize themed widget mixin."""
        self._theme_colors: Dict[str, str] = {}
        self._theme_bridge = None
        self._register_theme_observer()

    def _register_theme_observer(self):
        """Register as observer for theme changes."""
        try:
            from ..core.theme_bridge import ThemeBridge
            self._theme_bridge = ThemeBridge.get_instance()
            self._theme_bridge.register_observer(self._on_theme_changed)
            # Load initial colors
            self._theme_colors = self._theme_bridge.get_theme_colors()
        except Exception:
            # ThemeBridge not available, use defaults
            self._theme_colors = self._get_default_colors()

    def _get_default_colors(self) -> Dict[str, str]:
        """
        Get default fallback colors.

        Subclasses can override to provide custom defaults.

        Returns:
            Dict of color key to hex color string
        """
        return self.DEFAULT_COLORS.copy()

    def _on_theme_changed(self, theme_colors: Dict[str, str]):
        """
        Called when theme changes.

        Subclasses should override to handle theme updates.

        Args:
            theme_colors: New theme colors dict
        """
        self._theme_colors = theme_colors

    def get_theme_color(self, key: str, default: Optional[str] = None) -> str:
        """
        Get a theme color by key.

        Args:
            key: Color key (e.g., "fg", "bg", "log_error_fg")
            default: Default value if not found

        Returns:
            Hex color string
        """
        if default is None:
            default = self._get_default_colors().get(key, "#ffffff")
        return self._theme_colors.get(key, default)

    def get_theme_qcolor(self, key: str, default: Optional[str] = None) -> QColor:
        """
        Get a theme color as QColor.

        Args:
            key: Color key
            default: Default hex value if not found

        Returns:
            QColor instance
        """
        return QColor(self.get_theme_color(key, default))

    def get_qss_for_widget(self, widget_type: str) -> str:
        """
        Get QSS stylesheet for a widget type from theme.

        Args:
            widget_type: Widget type (e.g., "QTextEdit", "QPushButton")

        Returns:
            QSS stylesheet string
        """
        if self._theme_bridge:
            try:
                return self._theme_bridge.get_qss_for_widget(widget_type)
            except Exception:
                pass
        return ""

    def unregister_theme_observer(self):
        """Unregister from theme observer (call in widget destructor if needed)."""
        if self._theme_bridge:
            try:
                self._theme_bridge.unregister_observer(self._on_theme_changed)
            except Exception:
                pass
