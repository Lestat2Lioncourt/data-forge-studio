"""
Base Plugin - Abstract interface for DataForge Studio plugins

A plugin represents a functional module that can be loaded into the application.
Examples: DatabaseManager, QueriesManager, RootFolderManager, etc.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtWidgets import QWidget


class PluginCategory(Enum):
    """Categories for organizing plugins."""
    RESOURCE = "resource"       # Database, RootFolders, Queries, etc.
    UTILITY = "utility"         # Settings, Workspaces, etc.
    VIEWER = "viewer"           # Help, About, etc.


@dataclass
class PluginMetadata:
    """
    Metadata describing a plugin.

    Attributes:
        id: Unique identifier (e.g., "database", "queries")
        name: Display name (e.g., "Database Manager")
        description: Short description of plugin functionality
        icon: Icon filename (e.g., "database.png")
        category: Plugin category for organization
        version: Plugin version string
        author: Plugin author
        order: Display order (lower = first)
        show_in_sidebar: Whether to show in icon sidebar
        status_key: i18n key for status bar message
        menu_group: Menu group this plugin belongs to ("view", "options", etc.)
    """
    id: str
    name: str
    description: str = ""
    icon: str = ""
    category: PluginCategory = PluginCategory.RESOURCE
    version: str = "1.0.0"
    author: str = "DataForge Studio"
    order: int = 100
    show_in_sidebar: bool = True
    status_key: str = ""
    menu_group: str = "view"


class BasePlugin(ABC):
    """
    Abstract base class for all plugins.

    Plugins provide modular functionality that can be loaded into the application.
    Each plugin creates a widget that is displayed in the main window's stacked widget.

    Lifecycle:
    1. __init__() - Plugin instance created
    2. initialize() - Called after all plugins are loaded
    3. create_widget() - Widget created and added to stacked widget
    4. activate() - Called when plugin becomes visible
    5. deactivate() - Called when switching away from plugin
    6. cleanup() - Called on application shutdown

    Example:
        class MyPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    id="my_plugin",
                    name="My Plugin",
                    icon="my_icon.png",
                    category=PluginCategory.RESOURCE
                )

            def create_widget(self, parent=None) -> QWidget:
                return MyPluginWidget(parent)
    """

    def __init__(self):
        self._widget: Optional[QWidget] = None
        self._is_initialized = False
        self._is_active = False

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Returns:
            PluginMetadata describing this plugin
        """
        pass

    @abstractmethod
    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """
        Create and return the plugin's main widget.

        This method is called once when the plugin is first loaded.
        The widget will be added to the application's stacked widget.

        Args:
            parent: Parent widget (optional)

        Returns:
            QWidget instance
        """
        pass

    def initialize(self, app_context: Dict[str, Any]) -> None:
        """
        Initialize the plugin after all plugins are loaded.

        Override this method to perform initialization that depends
        on other plugins or application services.

        Args:
            app_context: Dictionary containing application services:
                - theme_bridge: ThemeBridge instance
                - i18n_bridge: I18nBridge instance
                - config_db: ConfigDB instance
                - plugin_manager: PluginManager instance
        """
        self._is_initialized = True

    def activate(self) -> None:
        """
        Called when the plugin becomes the active/visible plugin.

        Override to perform actions when the plugin is shown,
        such as refreshing data or starting background tasks.
        """
        self._is_active = True

    def deactivate(self) -> None:
        """
        Called when switching away from this plugin.

        Override to perform cleanup when the plugin is hidden,
        such as stopping background tasks or saving state.
        """
        self._is_active = False

    def cleanup(self) -> None:
        """
        Cleanup resources before application shutdown.

        Override to cleanup resources such as:
        - Stop background threads
        - Close database connections
        - Save unsaved state
        """
        pass

    def refresh(self) -> None:
        """
        Refresh the plugin's data/view.

        Override to implement refresh functionality.
        Default implementation calls refresh() on the widget if it exists.
        """
        if self._widget and hasattr(self._widget, 'refresh'):
            self._widget.refresh()

    @property
    def widget(self) -> Optional[QWidget]:
        """Get the plugin's widget (None if not yet created)."""
        return self._widget

    @property
    def is_initialized(self) -> bool:
        """Check if plugin has been initialized."""
        return self._is_initialized

    @property
    def is_active(self) -> bool:
        """Check if plugin is currently active/visible."""
        return self._is_active

    def get_dependencies(self) -> List[str]:
        """
        Return list of plugin IDs this plugin depends on.

        Override to declare dependencies on other plugins.
        The plugin manager will ensure dependencies are loaded first.

        Returns:
            List of plugin IDs
        """
        return []

    def connect_signals(self, plugin_manager: 'PluginManager') -> None:
        """
        Connect signals to other plugins or application components.

        Override to establish signal connections after all plugins are loaded.

        Args:
            plugin_manager: PluginManager instance for accessing other plugins
        """
        pass
