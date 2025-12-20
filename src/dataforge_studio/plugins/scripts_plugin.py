"""
Scripts Plugin - Plugin wrapper for ScriptsManager
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class ScriptsPlugin(BasePlugin):
    """Plugin wrapper for ScriptsManager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="scripts",
            name="Scripts Manager",
            description="Manage Python scripts for data processing",
            icon="scripts.png",
            category=PluginCategory.RESOURCE,
            order=50,
            show_in_sidebar=True,
            status_key="status_viewing_scripts",
            menu_group="view"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.scripts_manager import ScriptsManager
        self._widget = ScriptsManager(parent)
        return self._widget

    def cleanup(self) -> None:
        if self._widget and hasattr(self._widget, 'cleanup'):
            self._widget.cleanup()
