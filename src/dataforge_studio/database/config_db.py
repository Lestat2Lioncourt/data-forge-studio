"""
Configuration Database Module - Facade for all configuration database operations.

Delegates to repository classes and SchemaManager for actual implementation.
Models are defined in database/models/ package.
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .models import (
    DatabaseConnection,
    FileConfig,
    SavedQuery,
    Project,
    Workspace,
    FileRoot,
    FTPRoot,
    Script,
    Job,
    ImageRootfolder,
    SavedImage,
)
from .models.workspace_resource import WorkspaceFileRoot, WorkspaceDatabase, WorkspaceFTPRoot
from .schema_manager import SchemaManager
from .connection_pool import ConnectionPool
from .repositories import (
    DatabaseConnectionRepository,
    SavedQueryRepository,
    ProjectRepository,
    FileRootRepository,
    FTPRootRepository,
    ScriptRepository,
    JobRepository,
    ImageRootfolderRepository,
    SavedImageRepository,
    UserPreferencesRepository,
)

logger = logging.getLogger(__name__)


class ConfigDatabase:
    """
    SQLite database for configuration management.

    Facade that delegates all operations to specialized repositories.
    Public API is unchanged for backward compatibility.
    """

    # Configuration database internal ID
    CONFIG_DB_ID = "config-db-self-ref"
    CONFIG_DB_NAME = "Configuration Database"

    def __init__(self):
        # Store config in project root/_AppConfig/
        project_root = Path(__file__).parent.parent.parent.parent
        self.db_path = project_root / "_AppConfig" / "configuration.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema (creates tables + runs migrations)
        self._schema = SchemaManager(self.db_path)
        self._schema.initialize()

        # Initialize connection pool and repositories
        self._pool = ConnectionPool(self.db_path)
        self._db_conn_repo = DatabaseConnectionRepository(self._pool)
        self._query_repo = SavedQueryRepository(self._pool)
        self._project_repo = ProjectRepository(self._pool)
        self._file_root_repo = FileRootRepository(self._pool)
        self._ftp_root_repo = FTPRootRepository(self._pool)
        self._script_repo = ScriptRepository(self._pool)
        self._job_repo = JobRepository(self._pool)
        self._image_rootfolder_repo = ImageRootfolderRepository(self._pool)
        self._image_repo = SavedImageRepository(self._pool)
        self._prefs_repo = UserPreferencesRepository(self._pool)

    # ==================== Database Connections ====================

    def get_all_database_connections(self) -> List[DatabaseConnection]:
        return self._db_conn_repo.get_all_connections()

    def get_business_database_connections(self) -> List[DatabaseConnection]:
        return self._db_conn_repo.get_business_connections()

    def is_config_database(self, connection_id: str) -> bool:
        return self._db_conn_repo.is_config_database(connection_id)

    def get_database_connection(self, conn_id: str) -> Optional[DatabaseConnection]:
        return self._db_conn_repo.get_by_id(conn_id)

    def add_database_connection(self, conn: DatabaseConnection) -> bool:
        return self._db_conn_repo.add(conn)

    def update_database_connection(self, conn: DatabaseConnection) -> bool:
        return self._db_conn_repo.update(conn)

    def delete_database_connection(self, conn_id: str) -> bool:
        return self._db_conn_repo.delete(conn_id)

    def save_database_connection(self, conn: DatabaseConnection) -> bool:
        return self._db_conn_repo.save(conn)

    # ==================== Saved Queries ====================

    def get_all_saved_queries(self) -> List[SavedQuery]:
        return self._query_repo.get_all_queries()

    def get_saved_query(self, query_id: str) -> Optional[SavedQuery]:
        return self._query_repo.get_by_id(query_id)

    def add_saved_query(self, query: SavedQuery) -> bool:
        return self._query_repo.add(query)

    def update_saved_query(self, query: SavedQuery) -> bool:
        return self._query_repo.update(query)

    def delete_saved_query(self, query_id: str) -> bool:
        return self._query_repo.delete(query_id)

    # ==================== Scripts ====================

    def get_all_scripts(self) -> List[Script]:
        return self._script_repo.get_all()

    def get_script(self, script_id: str) -> Optional[Script]:
        return self._script_repo.get_by_id(script_id)

    def add_script(self, script: Script) -> bool:
        return self._script_repo.add(script)

    def update_script(self, script: Script) -> bool:
        return self._script_repo.update(script)

    def delete_script(self, script_id: str) -> bool:
        return self._script_repo.delete(script_id)

    # ==================== Jobs ====================

    def get_all_jobs(self) -> List[Job]:
        return self._job_repo.get_all()

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._job_repo.get_by_id(job_id)

    def add_job(self, job: Job) -> bool:
        return self._job_repo.add(job)

    def update_job(self, job: Job) -> bool:
        return self._job_repo.update(job)

    def delete_job(self, job_id: str) -> bool:
        return self._job_repo.delete(job_id)

    # ==================== Projects ====================

    def get_all_projects(self, sort_by_usage: bool = True) -> List[Project]:
        return self._project_repo.get_all_projects(sort_by_usage)

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._project_repo.get_by_id(project_id)

    # Aliases for CachedConfigDB compatibility
    def add_project(self, project: Project) -> bool:
        return self._project_repo.add(project)

    def update_project(self, project: Project) -> bool:
        return self._project_repo.update(project)

    def delete_project(self, project_id: str) -> bool:
        return self._project_repo.delete(project_id)

    # ==================== Workspaces (aliases for Projects) ====================

    def get_all_workspaces(self, sort_by_usage: bool = True) -> List[Project]:
        return self._project_repo.get_all_projects(sort_by_usage)

    def get_workspace(self, workspace_id: str) -> Optional[Project]:
        return self._project_repo.get_by_id(workspace_id)

    def add_workspace(self, workspace: Project) -> bool:
        return self._project_repo.add(workspace)

    def update_workspace(self, workspace: Project) -> bool:
        return self._project_repo.update(workspace)

    def delete_workspace(self, workspace_id: str) -> bool:
        return self._project_repo.delete(workspace_id)

    def touch_workspace(self, workspace_id: str) -> bool:
        return self._project_repo.touch(workspace_id)

    def get_auto_connect_workspace(self) -> Optional[Project]:
        return self._project_repo.get_auto_connect()

    def set_workspace_auto_connect(self, workspace_id: str, auto_connect: bool) -> bool:
        return self._project_repo.set_auto_connect(workspace_id, auto_connect)

    # ==================== Workspace-Database Relations ====================

    def add_database_to_workspace(self, workspace_id: str, database_id: str,
                                   database_name: str = None) -> bool:
        return self._project_repo.add_database(workspace_id, database_id, database_name)

    def remove_database_from_workspace(self, workspace_id: str, database_id: str,
                                        database_name: str = None) -> bool:
        return self._project_repo.remove_database(workspace_id, database_id, database_name)

    def get_workspace_databases(self, workspace_id: str) -> List[DatabaseConnection]:
        return self._project_repo.get_databases(workspace_id)

    def get_workspace_databases_with_context(self, workspace_id: str) -> List[WorkspaceDatabase]:
        return self._project_repo.get_databases_with_context(workspace_id)

    def get_workspace_database_entries(self, workspace_id: str) -> List[Tuple[str, str, str]]:
        return self._project_repo.get_database_entries(workspace_id)

    def get_workspace_database_ids(self, workspace_id: str) -> List[str]:
        return self._project_repo.get_database_ids(workspace_id)

    def get_database_workspaces(self, database_id: str, database_name: str = None) -> List[Project]:
        return self._project_repo.get_database_workspaces(database_id, database_name)

    def is_database_in_workspace(self, workspace_id: str, database_id: str,
                                  database_name: str = None) -> bool:
        return self._project_repo.is_database_in_project(workspace_id, database_id, database_name)

    # ==================== Workspace-Query Relations ====================

    def add_query_to_workspace(self, workspace_id: str, query_id: str) -> bool:
        return self._project_repo.add_query(workspace_id, query_id)

    def remove_query_from_workspace(self, workspace_id: str, query_id: str) -> bool:
        return self._project_repo.remove_query(workspace_id, query_id)

    def get_workspace_queries(self, workspace_id: str) -> List[SavedQuery]:
        return self._project_repo.get_queries(workspace_id)

    def get_workspace_query_ids(self, workspace_id: str) -> List[str]:
        return self._project_repo.get_query_ids(workspace_id)

    def get_query_workspaces(self, query_id: str) -> List[Project]:
        return self._project_repo.get_query_workspaces(query_id)

    # ==================== File Roots ====================

    def get_all_file_roots(self) -> List[FileRoot]:
        return self._file_root_repo.get_all_file_roots()

    def get_file_root(self, root_id: str) -> Optional[FileRoot]:
        return self._file_root_repo.get_by_id(root_id)

    def add_file_root(self, root: FileRoot) -> bool:
        return self._file_root_repo.add(root)

    def update_file_root(self, root: FileRoot) -> bool:
        return self._file_root_repo.update(root)

    def delete_file_root(self, root_id: str) -> bool:
        return self._file_root_repo.delete(root_id)

    def get_project_file_roots(self, project_id: str) -> List[FileRoot]:
        return self._project_repo.get_file_roots(project_id)

    def _save_file_root(self, file_root: FileRoot):
        """Save or update a file root (used internally by rootfolder_manager)."""
        self._file_root_repo.save(file_root)

    def _delete_file_root(self, file_root_id: str):
        """Delete a file root (used internally by rootfolder_manager)."""
        self._file_root_repo.delete(file_root_id)

    # ==================== Workspace-FileRoot Relations ====================

    def add_file_root_to_workspace(self, workspace_id: str, file_root_id: str,
                                    subfolder_path: str = None) -> bool:
        return self._project_repo.add_file_root(workspace_id, file_root_id, subfolder_path)

    def remove_file_root_from_workspace(self, workspace_id: str, file_root_id: str) -> bool:
        return self._project_repo.remove_file_root_all(workspace_id, file_root_id)

    def get_workspace_file_roots(self, workspace_id: str) -> List[FileRoot]:
        return self._project_repo.get_file_roots(workspace_id)

    def get_workspace_file_roots_with_context(self, workspace_id: str) -> List[WorkspaceFileRoot]:
        return self._project_repo.get_file_roots_with_context(workspace_id)

    def get_workspace_file_root_ids(self, workspace_id: str) -> List[str]:
        return self._project_repo.get_file_root_ids(workspace_id)

    def get_file_root_workspaces(self, file_root_id: str, subfolder_path: str = None) -> List[Project]:
        return self._project_repo.get_file_root_workspaces(file_root_id, subfolder_path)

    # ==================== Workspace-Job Relations ====================

    def add_job_to_workspace(self, workspace_id: str, job_id: str) -> bool:
        return self._project_repo.add_job(workspace_id, job_id)

    def remove_job_from_workspace(self, workspace_id: str, job_id: str) -> bool:
        return self._project_repo.remove_job(workspace_id, job_id)

    def get_workspace_jobs(self, workspace_id: str) -> List[Job]:
        return self._project_repo.get_jobs(workspace_id)

    def get_workspace_job_ids(self, workspace_id: str) -> List[str]:
        return self._project_repo.get_job_ids(workspace_id)

    def get_job_workspaces(self, job_id: str) -> List[Project]:
        return self._project_repo.get_job_workspaces(job_id)

    # ==================== Workspace-Script Relations ====================

    def add_script_to_workspace(self, workspace_id: str, script_id: str) -> bool:
        return self._project_repo.add_script(workspace_id, script_id)

    def remove_script_from_workspace(self, workspace_id: str, script_id: str) -> bool:
        return self._project_repo.remove_script(workspace_id, script_id)

    def get_workspace_scripts(self, workspace_id: str) -> List[Script]:
        return self._project_repo.get_scripts(workspace_id)

    def get_workspace_script_ids(self, workspace_id: str) -> List[str]:
        return self._project_repo.get_script_ids(workspace_id)

    def get_script_workspaces(self, script_id: str) -> List[Project]:
        return self._project_repo.get_script_workspaces(script_id)

    # ==================== FTP Roots ====================

    def get_all_ftp_roots(self) -> List[FTPRoot]:
        return self._ftp_root_repo.get_all()

    def get_ftp_root(self, ftp_root_id: str) -> Optional[FTPRoot]:
        return self._ftp_root_repo.get_by_id(ftp_root_id)

    def save_ftp_root(self, ftp_root: FTPRoot) -> bool:
        return self._ftp_root_repo.save(ftp_root)

    def delete_ftp_root(self, ftp_root_id: str) -> bool:
        return self._ftp_root_repo.delete(ftp_root_id)

    # ==================== Workspace-FTP Relations ====================

    def add_ftp_root_to_workspace(self, workspace_id: str, ftp_root_id: str,
                                   subfolder_path: str = None) -> bool:
        return self._project_repo.add_ftp_root(workspace_id, ftp_root_id, subfolder_path)

    def remove_ftp_root_from_workspace(self, workspace_id: str, ftp_root_id: str) -> bool:
        return self._project_repo.remove_ftp_root(workspace_id, ftp_root_id)

    def get_workspace_ftp_roots(self, workspace_id: str) -> List[FTPRoot]:
        return self._project_repo.get_ftp_roots(workspace_id)

    def get_workspace_ftp_roots_with_context(self, workspace_id: str) -> List[WorkspaceFTPRoot]:
        return self._project_repo.get_ftp_roots_with_context(workspace_id)

    def get_ftp_root_workspaces(self, ftp_root_id: str, subfolder_path: str = None) -> List[Workspace]:
        return self._project_repo.get_ftp_root_workspaces(ftp_root_id, subfolder_path)

    # ==================== User Preferences ====================

    def get_preference(self, key: str, default: str = None) -> Optional[str]:
        return self._prefs_repo.get(key, default)

    def set_preference(self, key: str, value: str) -> bool:
        return self._prefs_repo.set(key, value)

    def get_all_preferences(self) -> dict:
        return self._prefs_repo.get_all()

    # ==================== Image Rootfolders ====================

    def get_all_image_rootfolders(self) -> List[ImageRootfolder]:
        return self._image_rootfolder_repo.get_all()

    def get_image_rootfolder(self, rootfolder_id: str) -> Optional[ImageRootfolder]:
        return self._image_rootfolder_repo.get_by_id(rootfolder_id)

    def add_image_rootfolder(self, rootfolder: ImageRootfolder) -> bool:
        return self._image_rootfolder_repo.add(rootfolder)

    def update_image_rootfolder(self, rootfolder: ImageRootfolder) -> bool:
        return self._image_rootfolder_repo.update(rootfolder)

    def delete_image_rootfolder(self, rootfolder_id: str) -> bool:
        return self._image_rootfolder_repo.delete(rootfolder_id)

    # ==================== Saved Images ====================

    def get_all_saved_images(self) -> List[SavedImage]:
        return self._image_repo.get_all_images()

    def get_images_by_rootfolder(self, rootfolder_id: str) -> List[SavedImage]:
        return self._image_repo.get_by_rootfolder(rootfolder_id)

    def get_images_by_physical_path(self, rootfolder_id: str, physical_path: str) -> List[SavedImage]:
        return self._image_repo.get_by_physical_path(rootfolder_id, physical_path)

    def get_saved_image(self, image_id: str) -> Optional[SavedImage]:
        return self._image_repo.get_by_id(image_id)

    def get_saved_image_by_filepath(self, filepath: str) -> Optional[SavedImage]:
        return self._image_repo.get_by_filepath(filepath)

    def add_saved_image(self, name: str, filepath: str, rootfolder_id: str = None,
                        physical_path: str = "", description: str = "") -> Optional[str]:
        return self._image_repo.add_image(name, filepath, rootfolder_id, physical_path, description)

    def update_saved_image(self, image: SavedImage) -> bool:
        return self._image_repo.update(image)

    def delete_saved_image(self, image_id: str) -> bool:
        return self._image_repo.delete(image_id)

    def delete_images_by_rootfolder(self, rootfolder_id: str) -> int:
        return self._image_repo.delete_by_rootfolder(rootfolder_id)

    # ==================== Image Categories ====================

    def get_image_categories(self, image_id: str) -> List[str]:
        return self._image_repo.get_categories(image_id)

    def get_all_image_category_names(self) -> List[str]:
        return self._image_repo.get_all_category_names()

    def get_images_by_category(self, category_name: str) -> List[SavedImage]:
        return self._image_repo.get_by_category(category_name)

    def add_image_category(self, image_id: str, category_name: str) -> bool:
        return self._image_repo.add_category(image_id, category_name)

    def remove_image_category(self, image_id: str, category_name: str) -> bool:
        return self._image_repo.remove_category(image_id, category_name)

    def set_image_categories(self, image_id: str, category_names: List[str]) -> bool:
        return self._image_repo.set_categories(image_id, category_names)

    # ==================== Image Tags ====================

    def get_image_tags(self, image_id: str) -> List[str]:
        return self._image_repo.get_tags(image_id)

    def get_all_image_tag_names(self) -> List[str]:
        return self._image_repo.get_all_tag_names()

    def get_images_by_tag(self, tag_name: str) -> List[SavedImage]:
        return self._image_repo.get_by_tag(tag_name)

    def add_image_tag(self, image_id: str, tag_name: str) -> bool:
        return self._image_repo.add_tag(image_id, tag_name)

    def remove_image_tag(self, image_id: str, tag_name: str) -> bool:
        return self._image_repo.remove_tag(image_id, tag_name)

    def set_image_tags(self, image_id: str, tag_names: List[str]) -> bool:
        return self._image_repo.set_tags(image_id, tag_names)

    # ==================== Image Search ====================

    def search_images(self, query: str, search_name: bool = True,
                      search_categories: bool = True, search_tags: bool = True) -> List[SavedImage]:
        return self._image_repo.search(query, search_name, search_categories, search_tags)

    def get_image_physical_paths(self, rootfolder_id: str) -> List[str]:
        return self._image_repo.get_physical_paths(rootfolder_id)


# Global configuration database instance
def get_config_db() -> ConfigDatabase:
    """Get the global configuration database instance"""
    global _config_db_instance
    if '_config_db_instance' not in globals():
        _config_db_instance = ConfigDatabase()
    return _config_db_instance
