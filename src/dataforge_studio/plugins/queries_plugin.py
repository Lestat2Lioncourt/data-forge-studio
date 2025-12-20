"""
Queries Plugin - Plugin wrapper for QueriesManager
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class QueriesPlugin(BasePlugin):
    """Plugin wrapper for QueriesManager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="queries",
            name="Queries Manager",
            description="Manage saved SQL queries organized by category",
            icon="queries.png",
            category=PluginCategory.RESOURCE,
            order=30,
            show_in_sidebar=True,
            status_key="status_viewing_queries",
            menu_group="view"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.queries_manager import QueriesManager
        self._widget = QueriesManager(parent)
        return self._widget

    def cleanup(self) -> None:
        if self._widget and hasattr(self._widget, 'cleanup'):
            self._widget.cleanup()

    def connect_signals(self, plugin_manager) -> None:
        """Connect query execution signal to database plugin."""
        # Signal connection handled by main window for now
        pass
