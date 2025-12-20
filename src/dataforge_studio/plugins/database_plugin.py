"""
Database Plugin - Plugin wrapper for DatabaseManager
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class DatabasePlugin(BasePlugin):
    """Plugin wrapper for DatabaseManager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="database",
            name="Database Manager",
            description="Multi-tab SQL query interface with SSMS-style database explorer",
            icon="databases.png",
            category=PluginCategory.RESOURCE,
            order=10,
            show_in_sidebar=True,
            status_key="status_viewing_database",
            menu_group="view"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.database_manager import DatabaseManager
        self._widget = DatabaseManager(parent)
        return self._widget

    def initialize(self, app_context: Dict[str, Any]) -> None:
        super().initialize(app_context)
        # Store context for later use
        self._app_context = app_context

    def cleanup(self) -> None:
        if self._widget and hasattr(self._widget, 'cleanup'):
            self._widget.cleanup()

    def connect_signals(self, plugin_manager) -> None:
        """Connect query_saved signal to refresh queries in other plugins."""
        if self._widget:
            # Connect to resources plugin if available
            resources_plugin = plugin_manager.get_plugin("resources")
            if resources_plugin and resources_plugin.widget:
                if hasattr(resources_plugin.widget, 'refresh_queries'):
                    self._widget.query_saved.connect(resources_plugin.widget.refresh_queries)
