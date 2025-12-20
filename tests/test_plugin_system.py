"""
Unit tests for the Plugin System.
Tests BasePlugin, PluginManager, and plugin lifecycle.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Optional, List

from PySide6.QtWidgets import QWidget, QLabel

from dataforge_studio.core.base_plugin import (
    BasePlugin, PluginMetadata, PluginCategory
)
from dataforge_studio.core.plugin_manager import PluginManager


class MockPlugin(BasePlugin):
    """Mock plugin for testing."""

    def __init__(self, plugin_id: str = "mock", name: str = "Mock Plugin",
                 order: int = 100, show_in_sidebar: bool = True,
                 category: PluginCategory = PluginCategory.RESOURCE,
                 dependencies: List[str] = None):
        super().__init__()
        self._id = plugin_id
        self._name = name
        self._order = order
        self._show_in_sidebar = show_in_sidebar
        self._category = category
        self._dependencies = dependencies or []
        self.initialize_called = False
        self.activate_called = False
        self.deactivate_called = False
        self.cleanup_called = False

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id=self._id,
            name=self._name,
            description="Mock plugin for testing",
            icon="mock.png",
            category=self._category,
            order=self._order,
            show_in_sidebar=self._show_in_sidebar
        )

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        return QLabel(f"Mock Widget: {self._name}", parent)

    def initialize(self, app_context: dict) -> None:
        super().initialize(app_context)
        self.initialize_called = True

    def activate(self) -> None:
        super().activate()
        self.activate_called = True

    def deactivate(self) -> None:
        super().deactivate()
        self.deactivate_called = True

    def cleanup(self) -> None:
        super().cleanup()
        self.cleanup_called = True

    def get_dependencies(self) -> List[str]:
        return self._dependencies


class TestPluginMetadata:
    """Test PluginMetadata dataclass."""

    def test_default_values(self):
        """Test metadata with minimal required fields."""
        meta = PluginMetadata(id="test", name="Test Plugin")

        assert meta.id == "test"
        assert meta.name == "Test Plugin"
        assert meta.description == ""
        assert meta.icon == ""
        assert meta.category == PluginCategory.RESOURCE
        assert meta.version == "1.0.0"
        assert meta.order == 100
        assert meta.show_in_sidebar is True

    def test_custom_values(self):
        """Test metadata with all custom values."""
        meta = PluginMetadata(
            id="custom",
            name="Custom Plugin",
            description="A custom plugin",
            icon="custom.png",
            category=PluginCategory.UTILITY,
            version="2.0.0",
            order=50,
            show_in_sidebar=False
        )

        assert meta.id == "custom"
        assert meta.category == PluginCategory.UTILITY
        assert meta.order == 50
        assert meta.show_in_sidebar is False


class TestBasePlugin:
    """Test BasePlugin abstract class."""

    def test_initial_state(self):
        """Test plugin initial state."""
        plugin = MockPlugin()

        assert plugin._widget is None
        assert plugin._is_initialized is False
        assert plugin._is_active is False

    def test_metadata_property(self):
        """Test metadata property."""
        plugin = MockPlugin(plugin_id="test", name="Test")

        assert plugin.metadata.id == "test"
        assert plugin.metadata.name == "Test"

    def test_initialize(self):
        """Test plugin initialization."""
        plugin = MockPlugin()
        context = {"config": "value"}

        plugin.initialize(context)

        assert plugin._is_initialized is True
        assert plugin.initialize_called is True

    def test_activate_deactivate(self):
        """Test plugin activation/deactivation."""
        plugin = MockPlugin()

        plugin.activate()
        assert plugin._is_active is True
        assert plugin.activate_called is True

        plugin.deactivate()
        assert plugin._is_active is False
        assert plugin.deactivate_called is True

    def test_cleanup(self):
        """Test plugin cleanup."""
        plugin = MockPlugin()

        plugin.cleanup()
        assert plugin.cleanup_called is True

    def test_widget_property(self, qapp):
        """Test widget property."""
        plugin = MockPlugin()

        assert plugin.widget is None

        # Create widget
        widget = plugin.create_widget()
        plugin._widget = widget

        assert plugin.widget is widget


class TestPluginManager:
    """Test PluginManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh plugin manager."""
        return PluginManager()

    def test_register_plugin(self, manager):
        """Test registering a plugin."""
        plugin = MockPlugin(plugin_id="test1")

        result = manager.register(plugin)

        assert result is True
        assert "test1" in manager.get_plugin_ids()

    def test_register_duplicate(self, manager):
        """Test registering duplicate plugin ID."""
        plugin1 = MockPlugin(plugin_id="dup")
        plugin2 = MockPlugin(plugin_id="dup", name="Duplicate")

        manager.register(plugin1)
        result = manager.register(plugin2)

        assert result is False  # Should fail
        assert len(manager.get_plugin_ids()) == 1

    def test_register_class(self, manager):
        """Test registering plugin by class."""
        result = manager.register_class(MockPlugin)

        assert result is True
        assert "mock" in manager.get_plugin_ids()

    def test_unregister_plugin(self, manager):
        """Test unregistering a plugin."""
        plugin = MockPlugin(plugin_id="to_remove")
        manager.register(plugin)

        result = manager.unregister("to_remove")

        assert result is True
        assert "to_remove" not in manager.get_plugin_ids()
        assert plugin.cleanup_called is True

    def test_unregister_nonexistent(self, manager):
        """Test unregistering non-existent plugin."""
        result = manager.unregister("nonexistent")
        assert result is False

    def test_get_plugin(self, manager):
        """Test getting plugin by ID."""
        plugin = MockPlugin(plugin_id="get_test")
        manager.register(plugin)

        result = manager.get_plugin("get_test")
        assert result is plugin

        result = manager.get_plugin("nonexistent")
        assert result is None

    def test_get_plugins_all(self, manager):
        """Test getting all plugins."""
        plugin1 = MockPlugin(plugin_id="p1", order=2)
        plugin2 = MockPlugin(plugin_id="p2", order=1)
        manager.register(plugin1)
        manager.register(plugin2)

        plugins = manager.get_plugins()

        assert len(plugins) == 2
        # Should be sorted by order
        assert plugins[0].metadata.id == "p2"
        assert plugins[1].metadata.id == "p1"

    def test_get_plugins_by_category(self, manager):
        """Test filtering plugins by category."""
        plugin1 = MockPlugin(plugin_id="res", category=PluginCategory.RESOURCE)
        plugin2 = MockPlugin(plugin_id="util", category=PluginCategory.UTILITY)
        manager.register(plugin1)
        manager.register(plugin2)

        resource_plugins = manager.get_plugins(PluginCategory.RESOURCE)
        utility_plugins = manager.get_plugins(PluginCategory.UTILITY)

        assert len(resource_plugins) == 1
        assert resource_plugins[0].metadata.id == "res"
        assert len(utility_plugins) == 1
        assert utility_plugins[0].metadata.id == "util"

    def test_get_sidebar_plugins(self, manager):
        """Test getting sidebar plugins."""
        plugin1 = MockPlugin(plugin_id="show", show_in_sidebar=True)
        plugin2 = MockPlugin(plugin_id="hide", show_in_sidebar=False)
        manager.register(plugin1)
        manager.register(plugin2)

        sidebar_plugins = manager.get_sidebar_plugins()

        assert len(sidebar_plugins) == 1
        assert sidebar_plugins[0].metadata.id == "show"

    def test_initialize_all(self, manager):
        """Test initializing all plugins."""
        plugin1 = MockPlugin(plugin_id="init1")
        plugin2 = MockPlugin(plugin_id="init2")
        manager.register(plugin1)
        manager.register(plugin2)

        context = {"app": "test"}
        manager.initialize_all(context)

        assert plugin1.initialize_called is True
        assert plugin2.initialize_called is True
        assert manager._initialized is True

    def test_activate_plugin(self, manager):
        """Test activating a plugin."""
        plugin = MockPlugin(plugin_id="activate_test")
        manager.register(plugin)
        manager.initialize_all({})

        result = manager.activate_plugin("activate_test")

        assert result is True
        assert plugin.activate_called is True
        assert manager._active_plugin_id == "activate_test"

    def test_activate_switches_from_previous(self, manager):
        """Test that activating a new plugin deactivates the previous."""
        plugin1 = MockPlugin(plugin_id="first")
        plugin2 = MockPlugin(plugin_id="second")
        manager.register(plugin1)
        manager.register(plugin2)
        manager.initialize_all({})

        manager.activate_plugin("first")
        manager.activate_plugin("second")

        assert plugin1.deactivate_called is True
        assert plugin2.activate_called is True
        assert manager._active_plugin_id == "second"

    def test_cleanup_all(self, manager):
        """Test cleaning up all plugins."""
        plugin1 = MockPlugin(plugin_id="clean1")
        plugin2 = MockPlugin(plugin_id="clean2")
        manager.register(plugin1)
        manager.register(plugin2)

        manager.cleanup_all()

        assert plugin1.cleanup_called is True
        assert plugin2.cleanup_called is True

    def test_plugin_signals(self, manager):
        """Test that signals are emitted correctly."""
        registered_ids = []
        activated_ids = []

        manager.plugin_registered.connect(lambda id: registered_ids.append(id))
        manager.plugin_activated.connect(lambda id: activated_ids.append(id))

        plugin = MockPlugin(plugin_id="signal_test")
        manager.register(plugin)
        manager.initialize_all({})
        manager.activate_plugin("signal_test")

        assert "signal_test" in registered_ids
        assert "signal_test" in activated_ids


class TestPluginDependencies:
    """Test plugin dependency handling."""

    @pytest.fixture
    def manager(self):
        return PluginManager()

    def test_sort_by_dependencies(self, manager):
        """Test that plugins with dependencies are sorted correctly."""
        # Plugin with dependency should come after its dependency
        plugin_base = MockPlugin(plugin_id="base", dependencies=[])
        plugin_dependent = MockPlugin(plugin_id="dependent", dependencies=["base"])

        manager.register(plugin_dependent)
        manager.register(plugin_base)

        sorted_plugins = manager._sort_by_dependencies()

        # Base should come before dependent
        base_idx = next(i for i, p in enumerate(sorted_plugins) if p.metadata.id == "base")
        dep_idx = next(i for i, p in enumerate(sorted_plugins) if p.metadata.id == "dependent")

        assert base_idx < dep_idx
