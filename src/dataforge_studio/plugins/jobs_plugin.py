"""
Jobs Plugin - Plugin wrapper for JobsManager
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class JobsPlugin(BasePlugin):
    """Plugin wrapper for JobsManager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="jobs",
            name="Jobs Manager",
            description="Manage scheduled jobs and automated tasks",
            icon="jobs.png",
            category=PluginCategory.RESOURCE,
            order=40,
            show_in_sidebar=True,
            status_key="status_viewing_jobs",
            menu_group="view"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.jobs_manager import JobsManager
        self._widget = JobsManager(parent)
        return self._widget

    def cleanup(self) -> None:
        if self._widget and hasattr(self._widget, 'cleanup'):
            self._widget.cleanup()
