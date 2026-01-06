"""
FTPRoot Plugin - Plugin wrapper for FTPRootManager
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import QWidget

from ..core.base_plugin import BasePlugin, PluginMetadata, PluginCategory


class FTPRootPlugin(BasePlugin):
    """Plugin wrapper for FTPRootManager."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="ftproots",
            name="FTP Connections",
            description="FTP/FTPS/SFTP browser for remote file access",
            icon="ftp.png",
            category=PluginCategory.RESOURCE,
            order=25,  # After RootFolders (20)
            show_in_sidebar=True,
            status_key="status_viewing_ftproots",
            menu_group="view"
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        from ..ui.managers.ftproot_manager import FTPRootManager
        self._widget = FTPRootManager(parent)
        return self._widget

    def cleanup(self) -> None:
        if self._widget:
            # Close FTP connections
            if hasattr(self._widget, 'closeEvent'):
                from PySide6.QtCore import QEvent
                self._widget.closeEvent(QEvent(QEvent.Type.Close))
            if hasattr(self._widget, 'cleanup'):
                self._widget.cleanup()
