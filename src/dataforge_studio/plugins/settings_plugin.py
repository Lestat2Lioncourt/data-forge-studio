"""
Settings Plugin - Plugin wrapper for SettingsFrame
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class SettingsPlugin(BasePlugin):
    """Plugin wrapper for SettingsFrame."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="settings",
            name="Settings",
            description="Application preferences and theme configuration",
            icon="settings.png",
            category=PluginCategory.UTILITY,
            order=100,
            show_in_sidebar=False,
            status_key="status_viewing_settings",
            menu_group="options"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.frames.settings_frame import SettingsFrame
        self._widget = SettingsFrame(parent)
        return self._widget

    def get_frame(self):
        """Get the settings frame for signal connections."""
        return self._widget
