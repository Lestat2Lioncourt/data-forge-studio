"""
Database Repositories Package

Provides repository classes for all database entities following the Repository pattern.
Each repository handles CRUD operations for a specific entity type.
"""

from .base_repository import BaseRepository
from .database_connection_repository import DatabaseConnectionRepository
from .saved_query_repository import SavedQueryRepository
from .project_repository import ProjectRepository
from .file_root_repository import FileRootRepository
from .ftp_root_repository import FTPRootRepository
from .script_repository import ScriptRepository
from .job_repository import JobRepository
from .image_repository import ImageRootfolderRepository, SavedImageRepository
from .user_preferences_repository import UserPreferencesRepository

__all__ = [
    'BaseRepository',
    'DatabaseConnectionRepository',
    'SavedQueryRepository',
    'ProjectRepository',
    'FileRootRepository',
    'FTPRootRepository',
    'ScriptRepository',
    'JobRepository',
    'ImageRootfolderRepository',
    'SavedImageRepository',
    'UserPreferencesRepository',
]
