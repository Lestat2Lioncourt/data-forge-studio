"""
Workspaces Plugin - Plugin wrapper for WorkspaceManager
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class WorkspacesPlugin(BasePlugin):
    """Plugin wrapper for WorkspaceManager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="workspaces",
            name="Workspaces",
            description="Manage project workspaces and resource organization",
            icon="Workspace.png",
            category=PluginCategory.UTILITY,
            order=90,
            show_in_sidebar=False,
            status_key="status_viewing_workspaces",
            menu_group="workspaces"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.workspace_manager import WorkspaceManager
        self._widget = WorkspaceManager(parent)
        return self._widget
