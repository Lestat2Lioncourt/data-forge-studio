"""
Plugin Manager - Discovery, registration, and lifecycle management for plugins

The PluginManager is the central registry for all plugins in the application.
It handles:
- Plugin registration (manual and auto-discovery)
- Plugin lifecycle (init, activate, deactivate, cleanup)
- Plugin access by ID
- Signal coordination between plugins
"""

from typing import Dict, List, Optional, Any, Type, Callable
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QObject, Signal

from .base_plugin import BasePlugin, PluginMetadata, PluginCategory

import logging
logger = logging.getLogger(__name__)


class PluginManager(QObject):
    """
    Central manager for all plugins in the application.

    Usage:
        # Create manager
        manager = PluginManager()

        # Register plugins
        manager.register(DatabasePlugin())
        manager.register(QueriesPlugin())

        # Initialize all plugins
        manager.initialize_all(app_context)

        # Create widgets
        for plugin in manager.get_plugins():
            widget = plugin.create_widget(parent)
            stacked_widget.addWidget(widget)

        # Activate a plugin
        manager.activate_plugin("database")

        # Cleanup on shutdown
        manager.cleanup_all()
    """

    # Signals
    plugin_registered = Signal(str)        # Emitted when plugin is registered (plugin_id)
    plugin_activated = Signal(str)         # Emitted when plugin becomes active (plugin_id)
    plugin_deactivated = Signal(str)       # Emitted when plugin becomes inactive (plugin_id)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._plugins: Dict[str, BasePlugin] = {}
        self._active_plugin_id: Optional[str] = None
        self._app_context: Dict[str, Any] = {}
        self._initialized = False

    def register(self, plugin: BasePlugin) -> bool:
        """
        Register a plugin with the manager.

        Args:
            plugin: Plugin instance to register

        Returns:
            True if registration successful, False if plugin ID already exists
        """
        plugin_id = plugin.metadata.id

        if plugin_id in self._plugins:
            logger.warning(f"Plugin '{plugin_id}' already registered, skipping")
            return False

        self._plugins[plugin_id] = plugin
        logger.info(f"Registered plugin: {plugin_id} ({plugin.metadata.name})")
        self.plugin_registered.emit(plugin_id)
        return True

    def register_class(self, plugin_class: Type[BasePlugin]) -> bool:
        """
        Register a plugin by class (creates instance automatically).

        Args:
            plugin_class: Plugin class to instantiate and register

        Returns:
            True if registration successful
        """
        try:
            plugin = plugin_class()
            return self.register(plugin)
        except Exception as e:
            logger.error(f"Failed to instantiate plugin class {plugin_class.__name__}: {e}")
            return False

    def unregister(self, plugin_id: str) -> bool:
        """
        Unregister a plugin.

        Args:
            plugin_id: ID of plugin to unregister

        Returns:
            True if plugin was unregistered
        """
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]

        # Deactivate if active
        if self._active_plugin_id == plugin_id:
            plugin.deactivate()
            self._active_plugin_id = None

        # Cleanup
        plugin.cleanup()

        del self._plugins[plugin_id]
        logger.info(f"Unregistered plugin: {plugin_id}")
        return True

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """
        Get a plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(plugin_id)

    def get_plugin_widget(self, plugin_id: str) -> Optional[QWidget]:
        """
        Get a plugin's widget by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin's widget or None if not found/not created
        """
        plugin = self._plugins.get(plugin_id)
        return plugin.widget if plugin else None

    def get_plugins(self, category: Optional[PluginCategory] = None) -> List[BasePlugin]:
        """
        Get all registered plugins, optionally filtered by category.

        Args:
            category: Optional category to filter by

        Returns:
            List of plugins, sorted by order
        """
        plugins = list(self._plugins.values())

        if category:
            plugins = [p for p in plugins if p.metadata.category == category]

        # Sort by order
        plugins.sort(key=lambda p: p.metadata.order)
        return plugins

    def get_plugin_ids(self) -> List[str]:
        """
        Get all registered plugin IDs.

        Returns:
            List of plugin IDs
        """
        return list(self._plugins.keys())

    def get_sidebar_plugins(self) -> List[BasePlugin]:
        """
        Get plugins that should be shown in the sidebar.

        Returns:
            List of plugins with show_in_sidebar=True, sorted by order
        """
        plugins = [p for p in self._plugins.values() if p.metadata.show_in_sidebar]
        plugins.sort(key=lambda p: p.metadata.order)
        return plugins

    def initialize_all(self, app_context: Dict[str, Any]) -> None:
        """
        Initialize all registered plugins.

        Should be called after all plugins are registered and
        before creating widgets.

        Args:
            app_context: Dictionary containing application services
        """
        self._app_context = app_context
        self._app_context['plugin_manager'] = self

        # Sort by dependencies (simple topological sort)
        sorted_plugins = self._sort_by_dependencies()

        for plugin in sorted_plugins:
            try:
                plugin.initialize(self._app_context)
                logger.debug(f"Initialized plugin: {plugin.metadata.id}")
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin.metadata.id}: {e}")

        self._initialized = True

    def _sort_by_dependencies(self) -> List[BasePlugin]:
        """
        Sort plugins by dependencies (topological sort).

        Returns:
            List of plugins in dependency order
        """
        # Simple implementation - in production, use proper topological sort
        plugins = list(self._plugins.values())

        # Sort by: plugins with no dependencies first
        def dependency_count(p):
            deps = p.get_dependencies()
            return len([d for d in deps if d in self._plugins])

        plugins.sort(key=dependency_count)
        return plugins

    def create_all_widgets(self, parent: Optional[QWidget] = None) -> Dict[str, QWidget]:
        """
        Create widgets for all plugins.

        Args:
            parent: Parent widget for all plugin widgets

        Returns:
            Dictionary mapping plugin_id to widget
        """
        widgets = {}

        for plugin_id, plugin in self._plugins.items():
            try:
                widget = plugin.create_widget(parent)
                plugin._widget = widget
                widgets[plugin_id] = widget
                logger.debug(f"Created widget for plugin: {plugin_id}")
            except Exception as e:
                logger.error(f"Failed to create widget for plugin {plugin_id}: {e}")

        return widgets

    def connect_all_signals(self) -> None:
        """
        Connect signals between plugins after all are initialized.

        Call this after initialize_all() and create_all_widgets().
        """
        for plugin in self._plugins.values():
            try:
                plugin.connect_signals(self)
            except Exception as e:
                logger.error(f"Failed to connect signals for plugin {plugin.metadata.id}: {e}")

    def activate_plugin(self, plugin_id: str) -> bool:
        """
        Activate a plugin (make it the current/visible plugin).

        Deactivates the previously active plugin.

        Args:
            plugin_id: ID of plugin to activate

        Returns:
            True if activation successful
        """
        if plugin_id not in self._plugins:
            logger.warning(f"Cannot activate unknown plugin: {plugin_id}")
            return False

        # Deactivate current plugin
        if self._active_plugin_id and self._active_plugin_id != plugin_id:
            current = self._plugins.get(self._active_plugin_id)
            if current:
                current.deactivate()
                self.plugin_deactivated.emit(self._active_plugin_id)

        # Activate new plugin
        plugin = self._plugins[plugin_id]
        plugin.activate()
        self._active_plugin_id = plugin_id
        self.plugin_activated.emit(plugin_id)

        logger.debug(f"Activated plugin: {plugin_id}")
        return True

    def get_active_plugin(self) -> Optional[BasePlugin]:
        """
        Get the currently active plugin.

        Returns:
            Active plugin or None
        """
        if self._active_plugin_id:
            return self._plugins.get(self._active_plugin_id)
        return None

    def get_active_plugin_id(self) -> Optional[str]:
        """
        Get the ID of the currently active plugin.

        Returns:
            Active plugin ID or None
        """
        return self._active_plugin_id

    def cleanup_all(self) -> None:
        """
        Cleanup all plugins before application shutdown.

        Should be called in the application's close event.
        """
        logger.info("Cleaning up all plugins...")

        for plugin_id, plugin in self._plugins.items():
            try:
                plugin.cleanup()
                logger.debug(f"Cleaned up plugin: {plugin_id}")
            except Exception as e:
                logger.error(f"Error cleaning up plugin {plugin_id}: {e}")

    def refresh_plugin(self, plugin_id: str) -> bool:
        """
        Refresh a specific plugin.

        Args:
            plugin_id: ID of plugin to refresh

        Returns:
            True if refresh successful
        """
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.refresh()
            return True
        return False

    def refresh_all(self) -> None:
        """Refresh all plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.refresh()
            except Exception as e:
                logger.error(f"Error refreshing plugin {plugin.metadata.id}: {e}")

    def get_metadata(self, plugin_id: str) -> Optional[PluginMetadata]:
        """
        Get metadata for a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            PluginMetadata or None if not found
        """
        plugin = self._plugins.get(plugin_id)
        return plugin.metadata if plugin else None

    def get_all_metadata(self) -> List[PluginMetadata]:
        """
        Get metadata for all registered plugins.

        Returns:
            List of PluginMetadata, sorted by order
        """
        metadata = [p.metadata for p in self._plugins.values()]
        metadata.sort(key=lambda m: m.order)
        return metadata

    @property
    def is_initialized(self) -> bool:
        """Check if the plugin manager has been initialized."""
        return self._initialized

    @property
    def plugin_count(self) -> int:
        """Get the number of registered plugins."""
        return len(self._plugins)
