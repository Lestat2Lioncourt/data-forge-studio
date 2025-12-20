"""
Cached Configuration Database wrapper.

Provides a caching layer on top of ConfigDatabase for frequently accessed data.
Uses TTLCache for automatic expiration and invalidation on write operations.
"""
from typing import List, Optional, Tuple, Any
from cachetools import TTLCache
import threading

from .config_db import ConfigDatabase, get_config_db
from .models import (
    DatabaseConnection,
    SavedQuery,
    Project,
    FileRoot,
    Script,
    Job,
    ImageRootfolder,
    SavedImage,
)


class CachedConfigDB:
    """
    Cached wrapper around ConfigDatabase.

    Caches read operations with TTL expiration.
    Automatically invalidates cache on write operations.

    Usage:
        cached_db = get_cached_config_db()
        databases = cached_db.get_all_database_connections()  # Cached
        cached_db.add_database_connection(conn)  # Invalidates cache
    """

    # Cache configuration
    DEFAULT_TTL = 60  # seconds
    DEFAULT_MAXSIZE = 100

    def __init__(self, config_db: Optional[ConfigDatabase] = None,
                 ttl: int = DEFAULT_TTL, maxsize: int = DEFAULT_MAXSIZE):
        """
        Initialize cached config database.

        Args:
            config_db: ConfigDatabase instance (uses singleton if not provided)
            ttl: Cache time-to-live in seconds
            maxsize: Maximum number of cached entries
        """
        self._db = config_db or get_config_db()
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.RLock()

    def _cache_key(self, method: str, *args) -> str:
        """Generate cache key from method name and arguments."""
        if args:
            return f"{method}:{':'.join(str(a) for a in args)}"
        return method

    def _get_cached(self, key: str, loader: callable) -> Any:
        """Get from cache or load and cache."""
        with self._lock:
            if key in self._cache:
                return self._cache[key]
            result = loader()
            self._cache[key] = result
            return result

    def invalidate(self, *prefixes: str) -> None:
        """
        Invalidate cache entries matching prefixes.

        Args:
            prefixes: Cache key prefixes to invalidate. If empty, clears all.
        """
        with self._lock:
            if not prefixes:
                self._cache.clear()
                return

            keys_to_remove = [
                k for k in self._cache.keys()
                if any(k.startswith(p) for p in prefixes)
            ]
            for key in keys_to_remove:
                self._cache.pop(key, None)

    def invalidate_all(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()

    # -------------------------------------------------------------------------
    # Cached Read Operations - Database Connections
    # -------------------------------------------------------------------------

    def get_all_database_connections(self) -> List[DatabaseConnection]:
        """Get all database connections (cached)."""
        key = self._cache_key("get_all_database_connections")
        return self._get_cached(key, self._db.get_all_database_connections)

    def get_database_connection(self, conn_id: str) -> Optional[DatabaseConnection]:
        """Get database connection by ID (not cached - single item lookup)."""
        return self._db.get_database_connection(conn_id)

    def get_workspace_databases(self, workspace_id: str) -> List[DatabaseConnection]:
        """Get databases for a workspace (cached)."""
        key = self._cache_key("get_workspace_databases", workspace_id)
        return self._get_cached(key, lambda: self._db.get_workspace_databases(workspace_id))

    def get_workspace_database_ids(self, workspace_id: str) -> List[str]:
        """Get database IDs for a workspace (cached)."""
        key = self._cache_key("get_workspace_database_ids", workspace_id)
        return self._get_cached(key, lambda: self._db.get_workspace_database_ids(workspace_id))

    def add_database_connection(self, connection: DatabaseConnection) -> bool:
        """Add database connection (invalidates cache)."""
        result = self._db.add_database_connection(connection)
        if result:
            self.invalidate("get_all_database", "get_workspace_database")
        return result

    def update_database_connection(self, connection: DatabaseConnection) -> bool:
        """Update database connection (invalidates cache)."""
        result = self._db.update_database_connection(connection)
        if result:
            self.invalidate("get_all_database", "get_workspace_database")
        return result

    def delete_database_connection(self, conn_id: str) -> bool:
        """Delete database connection (invalidates cache)."""
        result = self._db.delete_database_connection(conn_id)
        if result:
            self.invalidate("get_all_database", "get_workspace_database")
        return result

    # -------------------------------------------------------------------------
    # Cached Read Operations - Saved Queries
    # -------------------------------------------------------------------------

    def get_all_saved_queries(self) -> List[SavedQuery]:
        """Get all saved queries (cached)."""
        key = self._cache_key("get_all_saved_queries")
        return self._get_cached(key, self._db.get_all_saved_queries)

    def get_saved_query(self, query_id: str) -> Optional[SavedQuery]:
        """Get saved query by ID (not cached)."""
        return self._db.get_saved_query(query_id)

    def get_workspace_queries(self, workspace_id: str) -> List[SavedQuery]:
        """Get queries for a workspace (cached)."""
        key = self._cache_key("get_workspace_queries", workspace_id)
        return self._get_cached(key, lambda: self._db.get_workspace_queries(workspace_id))

    def get_workspace_query_ids(self, workspace_id: str) -> List[str]:
        """Get query IDs for a workspace (cached)."""
        key = self._cache_key("get_workspace_query_ids", workspace_id)
        return self._get_cached(key, lambda: self._db.get_workspace_query_ids(workspace_id))

    def add_saved_query(self, query: SavedQuery) -> bool:
        """Add saved query (invalidates cache)."""
        result = self._db.add_saved_query(query)
        if result:
            self.invalidate("get_all_saved_queries", "get_workspace_quer")
        return result

    def update_saved_query(self, query: SavedQuery) -> bool:
        """Update saved query (invalidates cache)."""
        result = self._db.update_saved_query(query)
        if result:
            self.invalidate("get_all_saved_queries", "get_workspace_quer")
        return result

    def delete_saved_query(self, query_id: str) -> bool:
        """Delete saved query (invalidates cache)."""
        result = self._db.delete_saved_query(query_id)
        if result:
            self.invalidate("get_all_saved_queries", "get_workspace_quer")
        return result

    # -------------------------------------------------------------------------
    # Cached Read Operations - Projects/Workspaces
    # -------------------------------------------------------------------------

    def get_all_projects(self, sort_by_usage: bool = True) -> List[Project]:
        """Get all projects (cached)."""
        key = self._cache_key("get_all_projects", sort_by_usage)
        return self._get_cached(key, lambda: self._db.get_all_projects(sort_by_usage))

    def get_all_workspaces(self, sort_by_usage: bool = True) -> List[Project]:
        """Get all workspaces (cached)."""
        key = self._cache_key("get_all_workspaces", sort_by_usage)
        return self._get_cached(key, lambda: self._db.get_all_workspaces(sort_by_usage))

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID (not cached)."""
        return self._db.get_project(project_id)

    def add_project(self, project: Project) -> bool:
        """Add project (invalidates cache)."""
        result = self._db.add_project(project)
        if result:
            self.invalidate("get_all_projects", "get_all_workspaces")
        return result

    def update_project(self, project: Project) -> bool:
        """Update project (invalidates cache)."""
        result = self._db.update_project(project)
        if result:
            self.invalidate("get_all_projects", "get_all_workspaces")
        return result

    def delete_project(self, project_id: str) -> bool:
        """Delete project (invalidates cache)."""
        result = self._db.delete_project(project_id)
        if result:
            self.invalidate("get_all_projects", "get_all_workspaces")
        return result

    # -------------------------------------------------------------------------
    # Cached Read Operations - File Roots
    # -------------------------------------------------------------------------

    def get_all_file_roots(self) -> List[FileRoot]:
        """Get all file roots (cached)."""
        key = self._cache_key("get_all_file_roots")
        return self._get_cached(key, self._db.get_all_file_roots)

    def get_file_root(self, root_id: str) -> Optional[FileRoot]:
        """Get file root by ID (not cached)."""
        return self._db.get_file_root(root_id)

    def get_workspace_file_roots(self, workspace_id: str) -> List[FileRoot]:
        """Get file roots for a workspace (cached)."""
        key = self._cache_key("get_workspace_file_roots", workspace_id)
        return self._get_cached(key, lambda: self._db.get_workspace_file_roots(workspace_id))

    def get_workspace_file_root_ids(self, workspace_id: str) -> List[str]:
        """Get file root IDs for a workspace (cached)."""
        key = self._cache_key("get_workspace_file_root_ids", workspace_id)
        return self._get_cached(key, lambda: self._db.get_workspace_file_root_ids(workspace_id))

    def add_file_root(self, root: FileRoot) -> bool:
        """Add file root (invalidates cache)."""
        result = self._db.add_file_root(root)
        if result:
            self.invalidate("get_all_file_roots", "get_workspace_file_root")
        return result

    def update_file_root(self, root: FileRoot) -> bool:
        """Update file root (invalidates cache)."""
        result = self._db.update_file_root(root)
        if result:
            self.invalidate("get_all_file_roots", "get_workspace_file_root")
        return result

    def delete_file_root(self, root_id: str) -> bool:
        """Delete file root (invalidates cache)."""
        result = self._db.delete_file_root(root_id)
        if result:
            self.invalidate("get_all_file_roots", "get_workspace_file_root")
        return result

    # -------------------------------------------------------------------------
    # Cached Read Operations - Scripts & Jobs
    # -------------------------------------------------------------------------

    def get_all_scripts(self) -> List[Script]:
        """Get all scripts (cached)."""
        key = self._cache_key("get_all_scripts")
        return self._get_cached(key, self._db.get_all_scripts)

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs (cached)."""
        key = self._cache_key("get_all_jobs")
        return self._get_cached(key, self._db.get_all_jobs)

    def get_workspace_jobs(self, workspace_id: str) -> List[Job]:
        """Get jobs for a workspace (cached)."""
        key = self._cache_key("get_workspace_jobs", workspace_id)
        return self._get_cached(key, lambda: self._db.get_workspace_jobs(workspace_id))

    def add_script(self, script: Script) -> bool:
        """Add script (invalidates cache)."""
        result = self._db.add_script(script)
        if result:
            self.invalidate("get_all_scripts")
        return result

    def update_script(self, script: Script) -> bool:
        """Update script (invalidates cache)."""
        result = self._db.update_script(script)
        if result:
            self.invalidate("get_all_scripts")
        return result

    def delete_script(self, script_id: str) -> bool:
        """Delete script (invalidates cache)."""
        result = self._db.delete_script(script_id)
        if result:
            self.invalidate("get_all_scripts")
        return result

    def add_job(self, job: Job) -> bool:
        """Add job (invalidates cache)."""
        result = self._db.add_job(job)
        if result:
            self.invalidate("get_all_jobs", "get_workspace_jobs")
        return result

    def update_job(self, job: Job) -> bool:
        """Update job (invalidates cache)."""
        result = self._db.update_job(job)
        if result:
            self.invalidate("get_all_jobs", "get_workspace_jobs")
        return result

    def delete_job(self, job_id: str) -> bool:
        """Delete job (invalidates cache)."""
        result = self._db.delete_job(job_id)
        if result:
            self.invalidate("get_all_jobs", "get_workspace_jobs")
        return result

    # -------------------------------------------------------------------------
    # Cached Read Operations - Images
    # -------------------------------------------------------------------------

    def get_all_image_rootfolders(self) -> List[ImageRootfolder]:
        """Get all image root folders (cached)."""
        key = self._cache_key("get_all_image_rootfolders")
        return self._get_cached(key, self._db.get_all_image_rootfolders)

    def get_all_saved_images(self) -> List[SavedImage]:
        """Get all saved images (cached)."""
        key = self._cache_key("get_all_saved_images")
        return self._get_cached(key, self._db.get_all_saved_images)

    def get_all_image_category_names(self) -> List[str]:
        """Get all image category names (cached)."""
        key = self._cache_key("get_all_image_category_names")
        return self._get_cached(key, self._db.get_all_image_category_names)

    def get_all_image_tag_names(self) -> List[str]:
        """Get all image tag names (cached)."""
        key = self._cache_key("get_all_image_tag_names")
        return self._get_cached(key, self._db.get_all_image_tag_names)

    def add_image_rootfolder(self, rootfolder: ImageRootfolder) -> bool:
        """Add image root folder (invalidates cache)."""
        result = self._db.add_image_rootfolder(rootfolder)
        if result:
            self.invalidate("get_all_image_rootfolders")
        return result

    def update_image_rootfolder(self, rootfolder: ImageRootfolder) -> bool:
        """Update image root folder (invalidates cache)."""
        result = self._db.update_image_rootfolder(rootfolder)
        if result:
            self.invalidate("get_all_image_rootfolders")
        return result

    def delete_image_rootfolder(self, rootfolder_id: str) -> bool:
        """Delete image root folder (invalidates cache)."""
        result = self._db.delete_image_rootfolder(rootfolder_id)
        if result:
            self.invalidate("get_all_image_rootfolders", "get_all_saved_images")
        return result

    # -------------------------------------------------------------------------
    # Pass-through methods (no caching needed)
    # -------------------------------------------------------------------------

    def __getattr__(self, name: str):
        """
        Delegate unknown methods to underlying ConfigDatabase.

        This allows CachedConfigDB to be used as a drop-in replacement
        for ConfigDatabase while only caching specific methods.
        """
        return getattr(self._db, name)

    # -------------------------------------------------------------------------
    # Cache Statistics (for debugging/monitoring)
    # -------------------------------------------------------------------------

    @property
    def cache_info(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "maxsize": self._cache.maxsize,
                "ttl": self._cache.ttl,
                "keys": list(self._cache.keys()),
            }


# Singleton instance
_cached_config_db: Optional[CachedConfigDB] = None
_cached_config_lock = threading.Lock()


def get_cached_config_db() -> CachedConfigDB:
    """
    Get the singleton CachedConfigDB instance.

    Returns:
        CachedConfigDB: Cached configuration database wrapper
    """
    global _cached_config_db
    if _cached_config_db is None:
        with _cached_config_lock:
            if _cached_config_db is None:
                _cached_config_db = CachedConfigDB()
    return _cached_config_db


def invalidate_config_cache(*prefixes: str) -> None:
    """
    Invalidate config cache entries.

    Convenience function to invalidate cache from anywhere.

    Args:
        prefixes: Cache key prefixes to invalidate. If empty, clears all.
    """
    if _cached_config_db is not None:
        _cached_config_db.invalidate(*prefixes)
