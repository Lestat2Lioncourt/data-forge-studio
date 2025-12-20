"""
DataForge Studio Plugins

This package contains all plugin implementations for the application.
Each plugin wraps a manager or frame and provides standardized lifecycle management.
"""

from .database_plugin import DatabasePlugin
from .rootfolder_plugin import RootFolderPlugin
from .queries_plugin import QueriesPlugin
from .jobs_plugin import JobsPlugin
from .scripts_plugin import ScriptsPlugin
from .images_plugin import ImagesPlugin
from .settings_plugin import SettingsPlugin
from .workspaces_plugin import WorkspacesPlugin
from .help_plugin import HelpPlugin

# All available plugins
ALL_PLUGINS = [
    DatabasePlugin,
    RootFolderPlugin,
    QueriesPlugin,
    JobsPlugin,
    ScriptsPlugin,
    ImagesPlugin,
    SettingsPlugin,
    WorkspacesPlugin,
    HelpPlugin,
]

__all__ = [
    'DatabasePlugin',
    'RootFolderPlugin',
    'QueriesPlugin',
    'JobsPlugin',
    'ScriptsPlugin',
    'ImagesPlugin',
    'SettingsPlugin',
    'WorkspacesPlugin',
    'HelpPlugin',
    'ALL_PLUGINS',
]
