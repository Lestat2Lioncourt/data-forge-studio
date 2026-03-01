"""
Project Repository - CRUD operations for projects/workspaces.

Handles:
- Project CRUD operations (with auto_connect support)
- All workspace-resource junction tables (database, query, fileroot, job, script, ftp)
- Reverse lookups (resource → workspaces)
- "With context" queries (resource + junction metadata)
"""
import sqlite3
from typing import List, Optional, Tuple
from datetime import datetime
import logging

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import Project, DatabaseConnection, SavedQuery, FileRoot, FTPRoot, Script, Job
from ..models.workspace_resource import WorkspaceFileRoot, WorkspaceDatabase, WorkspaceFTPRoot

logger = logging.getLogger(__name__)


class ProjectRepository(BaseRepository[Project]):
    """
    Repository for Project entities (also known as Workspaces).

    Handles:
    - Project CRUD operations
    - Project-Database junction table
    - Project-Query junction table
    - Project-FileRoot junction table
    - Project-Job junction table
    """

    @property
    def table_name(self) -> str:
        return "projects"

    def _row_to_model(self, row: sqlite3.Row) -> Project:
        return Project(**dict(row))

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO projects
            (id, name, description, is_default, auto_connect, created_at, updated_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE projects
            SET name = ?, description = ?, is_default = ?, auto_connect = ?,
                updated_at = ?, last_used_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: Project) -> tuple:
        return (model.id, model.name, model.description,
                1 if model.is_default else 0,
                1 if model.auto_connect else 0,
                model.created_at, model.updated_at, model.last_used_at)

    def _model_to_update_tuple(self, model: Project) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.description,
                1 if model.is_default else 0,
                1 if model.auto_connect else 0,
                model.updated_at, model.last_used_at, model.id)

    def get_all_projects(self, sort_by_usage: bool = True) -> List[Project]:
        """Get all projects, optionally sorted by last usage."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            if sort_by_usage:
                cursor.execute("""
                    SELECT * FROM projects
                    ORDER BY last_used_at DESC, name ASC
                """)
            else:
                cursor.execute("SELECT * FROM projects ORDER BY name")
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def touch(self, project_id: str) -> bool:
        """Update last_used_at timestamp for a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE projects
                    SET last_used_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), project_id))
            return True
        except Exception:
            return False

    # Workspace aliases
    def get_all_workspaces(self, sort_by_usage: bool = True) -> List[Project]:
        """Alias for get_all_projects."""
        return self.get_all_projects(sort_by_usage)

    def get_workspace(self, workspace_id: str) -> Optional[Project]:
        """Alias for get_by_id."""
        return self.get_by_id(workspace_id)

    def add_workspace(self, workspace: Project) -> bool:
        """Alias for add."""
        return self.add(workspace)

    def update_workspace(self, workspace: Project) -> bool:
        """Alias for update."""
        return self.update(workspace)

    def delete_workspace(self, workspace_id: str) -> bool:
        """Alias for delete."""
        return self.delete(workspace_id)

    def touch_workspace(self, workspace_id: str) -> bool:
        """Alias for touch."""
        return self.touch(workspace_id)

    # ==================== Auto-connect ====================

    def get_auto_connect(self) -> Optional[Project]:
        """Get the workspace with auto_connect enabled (only one at a time)."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE auto_connect = 1 LIMIT 1")
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None

    def set_auto_connect(self, project_id: str, auto_connect: bool) -> bool:
        """Set auto_connect for a workspace. If enabling, disables all others first."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                if auto_connect:
                    cursor.execute("UPDATE projects SET auto_connect = 0")
                cursor.execute(
                    "UPDATE projects SET auto_connect = ?, updated_at = ? WHERE id = ?",
                    (1 if auto_connect else 0, datetime.now().isoformat(), project_id)
                )
            return True
        except Exception:
            return False

    # ==================== Generic Relation Helpers ====================

    def _add_relation(self, junction_table: str, resource_col: str,
                      project_id: str, resource_id: str,
                      extra_cols: str = "", extra_vals: tuple = ()) -> bool:
        """Add a resource to a project via junction table."""
        try:
            cols = f"project_id, {resource_col}{extra_cols}, created_at"
            placeholders = ", ".join(["?"] * (2 + len(extra_vals) + 1))
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"INSERT OR IGNORE INTO {junction_table} ({cols}) VALUES ({placeholders})",
                    (project_id, resource_id, *extra_vals, datetime.now().isoformat())
                )
            return True
        except Exception:
            return False

    def _remove_relation(self, junction_table: str, resource_col: str,
                         project_id: str, resource_id: str,
                         extra_where: str = "", extra_vals: tuple = ()) -> bool:
        """Remove a resource from a project via junction table."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"DELETE FROM {junction_table} WHERE project_id = ? AND {resource_col} = ?{extra_where}",
                    (project_id, resource_id, *extra_vals)
                )
            return True
        except Exception:
            return False

    def _get_resource_ids(self, junction_table: str, resource_col: str,
                          project_id: str) -> List[str]:
        """Get all resource IDs for a project from a junction table."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT {resource_col} FROM {junction_table} WHERE project_id = ?",
                (project_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def _get_resource_workspaces(self, junction_table: str, resource_col: str,
                                 resource_id: str) -> List[Project]:
        """Get all workspaces that contain a resource."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT DISTINCT p.* FROM projects p
                INNER JOIN {junction_table} j ON p.id = j.project_id
                WHERE j.{resource_col} = ?
                ORDER BY p.name
            """, (resource_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    # ==================== Database Relations ====================

    def add_database(self, project_id: str, database_id: str,
                     database_name: str = None) -> bool:
        """Add a database to a project."""
        return self._add_relation(
            "project_databases", "database_id", project_id, database_id,
            extra_cols=", database_name", extra_vals=(database_name or '',)
        )

    def remove_database(self, project_id: str, database_id: str,
                        database_name: str = None) -> bool:
        """Remove a database from a project."""
        return self._remove_relation(
            "project_databases", "database_id", project_id, database_id,
            extra_where=" AND database_name = ?", extra_vals=(database_name or '',)
        )

    def get_databases(self, project_id: str) -> List[DatabaseConnection]:
        """Get all database connections in a project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT dc.* FROM database_connections dc
                INNER JOIN project_databases pd ON dc.id = pd.database_id
                WHERE pd.project_id = ?
                ORDER BY dc.name
            """, (project_id,))
            rows = cursor.fetchall()
            return [DatabaseConnection(**dict(row)) for row in rows]

    def get_database_entries(self, project_id: str) -> List[Tuple[str, str, str]]:
        """Get all database entries (database_id, database_name, created_at)."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT database_id, database_name, created_at FROM project_databases
                WHERE project_id = ?
                ORDER BY database_id, database_name
            """, (project_id,))
            return [(row[0], row[1], row[2]) for row in cursor.fetchall()]

    def get_database_ids(self, project_id: str) -> List[str]:
        """Get all database IDs in a project."""
        return self._get_resource_ids("project_databases", "database_id", project_id)

    def get_databases_with_context(self, project_id: str) -> List[WorkspaceDatabase]:
        """Get all databases in a project WITH their database_name context."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dc.*, pd.database_name
                FROM database_connections dc
                INNER JOIN project_databases pd ON dc.id = pd.database_id
                WHERE pd.project_id = ?
                ORDER BY dc.name, pd.database_name
            """, (project_id,))
            rows = cursor.fetchall()

        result = []
        for row in rows:
            row_dict = dict(row)
            database_name = row_dict.pop('database_name', '') or ''
            connection = DatabaseConnection(**row_dict)
            result.append(WorkspaceDatabase(connection=connection, database_name=database_name))
        return result

    def get_database_workspaces(self, database_id: str, database_name: str = None) -> List[Project]:
        """Get all workspaces that contain a database."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            if database_name is not None:
                cursor.execute("""
                    SELECT p.* FROM projects p
                    INNER JOIN project_databases pd ON p.id = pd.project_id
                    WHERE pd.database_id = ? AND pd.database_name = ?
                    ORDER BY p.name
                """, (database_id, database_name))
            else:
                cursor.execute("""
                    SELECT DISTINCT p.* FROM projects p
                    INNER JOIN project_databases pd ON p.id = pd.project_id
                    WHERE pd.database_id = ?
                    ORDER BY p.name
                """, (database_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def is_database_in_project(self, project_id: str, database_id: str,
                               database_name: str = None) -> bool:
        """Check if a database is in a project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM project_databases
                WHERE project_id = ? AND database_id = ? AND database_name = ?
                LIMIT 1
            """, (project_id, database_id, database_name or ''))
            return cursor.fetchone() is not None

    # ==================== Query Relations ====================

    def add_query(self, project_id: str, query_id: str) -> bool:
        """Add a saved query to a project."""
        return self._add_relation("project_queries", "query_id", project_id, query_id)

    def remove_query(self, project_id: str, query_id: str) -> bool:
        """Remove a saved query from a project."""
        return self._remove_relation("project_queries", "query_id", project_id, query_id)

    def get_queries(self, project_id: str) -> List[SavedQuery]:
        """Get all saved queries in a project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sq.* FROM saved_queries sq
                INNER JOIN project_queries pq ON sq.id = pq.query_id
                WHERE pq.project_id = ?
                ORDER BY sq.category, sq.name
            """, (project_id,))
            rows = cursor.fetchall()
            return [SavedQuery(**dict(row)) for row in rows]

    def get_query_ids(self, project_id: str) -> List[str]:
        """Get all query IDs in a project."""
        return self._get_resource_ids("project_queries", "query_id", project_id)

    def get_query_workspaces(self, query_id: str) -> List[Project]:
        """Get all workspaces that contain a query."""
        return self._get_resource_workspaces("project_queries", "query_id", query_id)

    # ==================== FileRoot Relations ====================

    def add_file_root(self, project_id: str, file_root_id: str,
                      subfolder_path: str = None) -> bool:
        """Add a file root to a project."""
        return self._add_relation(
            "project_file_roots", "file_root_id", project_id, file_root_id,
            extra_cols=", subfolder_path", extra_vals=(subfolder_path or '',)
        )

    def remove_file_root(self, project_id: str, file_root_id: str,
                         subfolder_path: str = None) -> bool:
        """Remove a file root from a project."""
        return self._remove_relation(
            "project_file_roots", "file_root_id", project_id, file_root_id,
            extra_where=" AND subfolder_path = ?", extra_vals=(subfolder_path or '',)
        )

    def remove_file_root_all(self, project_id: str, file_root_id: str) -> bool:
        """Remove a file root from a project (all subfolder variants)."""
        return self._remove_relation("project_file_roots", "file_root_id", project_id, file_root_id)

    def get_file_roots(self, project_id: str) -> List[FileRoot]:
        """Get all file roots in a project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT fr.* FROM file_roots fr
                INNER JOIN project_file_roots pfr ON fr.id = pfr.file_root_id
                WHERE pfr.project_id = ?
                ORDER BY fr.path
            """, (project_id,))
            rows = cursor.fetchall()
            return [FileRoot(**dict(row)) for row in rows]

    def get_file_root_ids(self, project_id: str) -> List[str]:
        """Get all file root IDs in a project."""
        return self._get_resource_ids("project_file_roots", "file_root_id", project_id)

    def get_file_roots_with_context(self, project_id: str) -> List[WorkspaceFileRoot]:
        """Get all file roots in a project WITH their subfolder context."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fr.*, pfr.subfolder_path
                FROM file_roots fr
                INNER JOIN project_file_roots pfr ON fr.id = pfr.file_root_id
                WHERE pfr.project_id = ?
                ORDER BY pfr.subfolder_path, fr.path
            """, (project_id,))
            rows = cursor.fetchall()

        result = []
        for row in rows:
            row_dict = dict(row)
            subfolder_path = row_dict.pop('subfolder_path', '') or ''
            file_root = FileRoot(**row_dict)
            result.append(WorkspaceFileRoot(file_root=file_root, subfolder_path=subfolder_path))
        return result

    def get_file_root_workspaces(self, file_root_id: str, subfolder_path: str = None) -> List[Project]:
        """Get all workspaces that contain a file root."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            if subfolder_path:
                cursor.execute("""
                    SELECT p.* FROM projects p
                    INNER JOIN project_file_roots pfr ON p.id = pfr.project_id
                    WHERE pfr.file_root_id = ? AND pfr.subfolder_path = ?
                    ORDER BY p.name
                """, (file_root_id, subfolder_path))
            else:
                cursor.execute("""
                    SELECT p.* FROM projects p
                    INNER JOIN project_file_roots pfr ON p.id = pfr.project_id
                    WHERE pfr.file_root_id = ?
                    ORDER BY p.name
                """, (file_root_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    # ==================== Job Relations ====================

    def add_job(self, project_id: str, job_id: str) -> bool:
        """Add a job to a project."""
        return self._add_relation("project_jobs", "job_id", project_id, job_id)

    def remove_job(self, project_id: str, job_id: str) -> bool:
        """Remove a job from a project."""
        return self._remove_relation("project_jobs", "job_id", project_id, job_id)

    def get_jobs(self, project_id: str) -> List[Job]:
        """Get all jobs in a project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT j.* FROM jobs j
                INNER JOIN project_jobs pj ON j.id = pj.job_id
                WHERE pj.project_id = ?
                ORDER BY j.name
            """, (project_id,))
            rows = cursor.fetchall()
            return [Job(**dict(row)) for row in rows]

    def get_job_ids(self, project_id: str) -> List[str]:
        """Get all job IDs in a project."""
        return self._get_resource_ids("project_jobs", "job_id", project_id)

    def get_job_workspaces(self, job_id: str) -> List[Project]:
        """Get all workspaces that contain a job."""
        return self._get_resource_workspaces("project_jobs", "job_id", job_id)

    # ==================== Script Relations ====================

    def add_script(self, project_id: str, script_id: str) -> bool:
        """Add a script to a project."""
        return self._add_relation("project_scripts", "script_id", project_id, script_id)

    def remove_script(self, project_id: str, script_id: str) -> bool:
        """Remove a script from a project."""
        return self._remove_relation("project_scripts", "script_id", project_id, script_id)

    def get_scripts(self, project_id: str) -> List[Script]:
        """Get all scripts in a project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.* FROM scripts s
                INNER JOIN project_scripts ps ON s.id = ps.script_id
                WHERE ps.project_id = ?
                ORDER BY s.script_type, s.name
            """, (project_id,))
            rows = cursor.fetchall()
            return [Script(**dict(row)) for row in rows]

    def get_script_ids(self, project_id: str) -> List[str]:
        """Get all script IDs in a project."""
        return self._get_resource_ids("project_scripts", "script_id", project_id)

    def get_script_workspaces(self, script_id: str) -> List[Project]:
        """Get all workspaces that contain a script."""
        return self._get_resource_workspaces("project_scripts", "script_id", script_id)

    # ==================== FTP Root Relations ====================

    def add_ftp_root(self, project_id: str, ftp_root_id: str,
                     subfolder_path: str = None) -> bool:
        """Add an FTP root to a project."""
        return self._add_relation(
            "project_ftp_roots", "ftp_root_id", project_id, ftp_root_id,
            extra_cols=", subfolder_path", extra_vals=(subfolder_path or '',)
        )

    def remove_ftp_root(self, project_id: str, ftp_root_id: str) -> bool:
        """Remove an FTP root from a project."""
        return self._remove_relation("project_ftp_roots", "ftp_root_id", project_id, ftp_root_id)

    def get_ftp_roots(self, project_id: str) -> List[FTPRoot]:
        """Get all FTP roots in a project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fr.* FROM ftp_roots fr
                INNER JOIN project_ftp_roots pfr ON fr.id = pfr.ftp_root_id
                WHERE pfr.project_id = ?
                ORDER BY fr.name
            """, (project_id,))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = dict(row)
                row_dict['passive_mode'] = bool(row_dict.get('passive_mode', 1))
                result.append(FTPRoot(**row_dict))
            return result

    def get_ftp_roots_with_context(self, project_id: str) -> List[WorkspaceFTPRoot]:
        """Get all FTP roots in a project with subfolder context."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fr.*, pfr.subfolder_path FROM ftp_roots fr
                INNER JOIN project_ftp_roots pfr ON fr.id = pfr.ftp_root_id
                WHERE pfr.project_id = ?
                ORDER BY fr.name
            """, (project_id,))
            rows = cursor.fetchall()

        result = []
        for row in rows:
            row_dict = dict(row)
            subfolder_path = row_dict.pop('subfolder_path', '')
            row_dict['passive_mode'] = bool(row_dict.get('passive_mode', 1))
            ftp_root = FTPRoot(**row_dict)
            result.append(WorkspaceFTPRoot(ftp_root=ftp_root, subfolder_path=subfolder_path))
        return result

    def get_ftp_root_workspaces(self, ftp_root_id: str, subfolder_path: str = None) -> List[Project]:
        """Get all workspaces that contain an FTP root."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            if subfolder_path:
                cursor.execute("""
                    SELECT p.* FROM projects p
                    INNER JOIN project_ftp_roots pfr ON p.id = pfr.project_id
                    WHERE pfr.ftp_root_id = ? AND pfr.subfolder_path = ?
                    ORDER BY p.name
                """, (ftp_root_id, subfolder_path))
            else:
                cursor.execute("""
                    SELECT p.* FROM projects p
                    INNER JOIN project_ftp_roots pfr ON p.id = pfr.project_id
                    WHERE pfr.ftp_root_id = ?
                    ORDER BY p.name
                """, (ftp_root_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
