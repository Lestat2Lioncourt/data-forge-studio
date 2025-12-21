"""UI Managers - Manager views for different sections"""

from .base_manager_view import BaseManagerView
from .queries_manager import QueriesManager
from .scripts_manager import ScriptsManager
from .jobs_manager import JobsManager
from .database_manager import DatabaseManager
from .rootfolder_manager import RootFolderManager
from .workspace_manager import WorkspaceManager
from .resources_manager import ResourcesManager

__all__ = [
    "BaseManagerView",
    "QueriesManager",
    "ScriptsManager",
    "JobsManager",
    "DatabaseManager",
    "RootFolderManager",
    "WorkspaceManager",
    "ResourcesManager"
]
