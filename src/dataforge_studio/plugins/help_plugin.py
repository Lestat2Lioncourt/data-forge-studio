"""
Help Plugin - Plugin wrapper for HelpFrame
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class HelpPlugin(BasePlugin):
    """Plugin wrapper for HelpFrame."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="help",
            name="Help",
            description="Documentation and help resources",
            icon="help.png",
            category=PluginCategory.VIEWER,
            order=200,
            show_in_sidebar=False,
            status_key="status_viewing_help",
            menu_group="help"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.frames.help_frame import HelpFrame
        self._widget = HelpFrame(parent)
        return self._widget
