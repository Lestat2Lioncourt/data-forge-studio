"""
RootFolder Plugin - Plugin wrapper for RootFolderManager
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class RootFolderPlugin(BasePlugin):
    """Plugin wrapper for RootFolderManager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="rootfolders",
            name="Root Folders",
            description="File browser and viewer for configured root folders",
            icon="RootFolders.png",
            category=PluginCategory.RESOURCE,
            order=20,
            show_in_sidebar=True,
            status_key="status_viewing_rootfolders",
            menu_group="view"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.rootfolder_manager import RootFolderManager
        self._widget = RootFolderManager(parent)
        return self._widget

    def cleanup(self) -> None:
        if self._widget and hasattr(self._widget, 'cleanup'):
            self._widget.cleanup()
