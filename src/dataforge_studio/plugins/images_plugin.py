"""
Images Plugin - Plugin wrapper for ImageLibraryManager
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class ImagesPlugin(BasePlugin):
    """Plugin wrapper for ImageLibraryManager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="images",
            name="Image Library",
            description="Browse and manage image collections",
            icon="images.png",
            category=PluginCategory.RESOURCE,
            order=60,
            show_in_sidebar=True,
            status_key="status_viewing_images",
            menu_group="view"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.image_library_manager import ImageLibraryManager
        self._widget = ImageLibraryManager(parent)
        return self._widget

    def cleanup(self) -> None:
        if self._widget and hasattr(self._widget, 'cleanup'):
            self._widget.cleanup()
