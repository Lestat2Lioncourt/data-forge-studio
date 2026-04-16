"""
ER Diagram Plugin - Plugin wrapper for ERDiagramManager
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class ERDiagramPlugin(BasePlugin):
    """Plugin wrapper for ER Diagram Manager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="er_diagram",
            name="ER Diagrams",
            description="Interactive Entity-Relationship diagrams with FK visualization",
            icon="diagram.png",
            category=PluginCategory.RESOURCE,
            order=15,  # After database (10)
            show_in_sidebar=True,
            status_key="status_viewing_er_diagram",
            menu_group="view"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.er_diagram_manager import ERDiagramManager
        self._widget = ERDiagramManager(parent)
        return self._widget

    def initialize(self, app_context: Dict[str, Any]) -> None:
        super().initialize(app_context)

    def cleanup(self) -> None:
        pass

    def connect_signals(self, plugin_manager) -> None:
        """Connect to DatabaseManager for shared connections."""
        if self._widget:
            database_plugin = plugin_manager.get_plugin("database")
            if database_plugin and database_plugin.widget:
                self._widget.set_database_manager(database_plugin.widget)
