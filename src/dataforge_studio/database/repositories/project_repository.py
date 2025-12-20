"""
Project Repository - CRUD operations for projects/workspaces.
"""
import sqlite3
from typing import List, Optional, Tuple
from datetime import datetime

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import Project, DatabaseConnection, SavedQuery, FileRoot, Job


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
            (id, name, description, is_default, created_at, updated_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE projects
            SET name = ?, description = ?, is_default = ?,
                updated_at = ?, last_used_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: Project) -> tuple:
        return (model.id, model.name, model.description,
                1 if model.is_default else 0,
                model.created_at, model.updated_at, model.last_used_at)

    def _model_to_update_tuple(self, model: Project) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.description,
                1 if model.is_default else 0,
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

    # ==================== Database Relations ====================

    def add_database(self, project_id: str, database_id: str,
                     database_name: str = None) -> bool:
        """Add a database to a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO project_databases
                    (project_id, database_id, database_name, created_at)
                    VALUES (?, ?, ?, ?)
                """, (project_id, database_id, database_name or '',
                      datetime.now().isoformat()))
            return True
        except Exception:
            return False

    def remove_database(self, project_id: str, database_id: str,
                        database_name: str = None) -> bool:
        """Remove a database from a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM project_databases
                    WHERE project_id = ? AND database_id = ? AND database_name = ?
                """, (project_id, database_id, database_name or ''))
            return True
        except Exception:
            return False

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
        """
        Get all database entries in a project with details.

        Returns:
            List of tuples: (database_id, database_name, created_at)
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT database_id, database_name, created_at FROM project_databases
                WHERE project_id = ?
                ORDER BY database_id, database_name
            """, (project_id,))
            return [(row[0], row[1], row[2]) for row in cursor.fetchall()]

    # ==================== Query Relations ====================

    def add_query(self, project_id: str, query_id: str) -> bool:
        """Add a saved query to a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO project_queries
                    (project_id, query_id, created_at)
                    VALUES (?, ?, ?)
                """, (project_id, query_id, datetime.now().isoformat()))
            return True
        except Exception:
            return False

    def remove_query(self, project_id: str, query_id: str) -> bool:
        """Remove a saved query from a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM project_queries
                    WHERE project_id = ? AND query_id = ?
                """, (project_id, query_id))
            return True
        except Exception:
            return False

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

    # ==================== FileRoot Relations ====================

    def add_file_root(self, project_id: str, file_root_id: str,
                      subfolder_path: str = None) -> bool:
        """Add a file root to a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO project_file_roots
                    (project_id, file_root_id, subfolder_path, created_at)
                    VALUES (?, ?, ?, ?)
                """, (project_id, file_root_id, subfolder_path or '',
                      datetime.now().isoformat()))
            return True
        except Exception:
            return False

    def remove_file_root(self, project_id: str, file_root_id: str,
                         subfolder_path: str = None) -> bool:
        """Remove a file root from a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM project_file_roots
                    WHERE project_id = ? AND file_root_id = ? AND subfolder_path = ?
                """, (project_id, file_root_id, subfolder_path or ''))
            return True
        except Exception:
            return False

    def get_file_roots(self, project_id: str) -> List[FileRoot]:
        """Get all file roots in a project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT fr.* FROM file_roots fr
                INNER JOIN project_file_roots pfr ON fr.id = pfr.file_root_id
                WHERE pfr.project_id = ?
                ORDER BY fr.name
            """, (project_id,))
            rows = cursor.fetchall()
            return [FileRoot(**dict(row)) for row in rows]

    # ==================== Job Relations ====================

    def add_job(self, project_id: str, job_id: str) -> bool:
        """Add a job to a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO project_jobs
                    (project_id, job_id, created_at)
                    VALUES (?, ?, ?)
                """, (project_id, job_id, datetime.now().isoformat()))
            return True
        except Exception:
            return False

    def remove_job(self, project_id: str, job_id: str) -> bool:
        """Remove a job from a project."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM project_jobs
                    WHERE project_id = ? AND job_id = ?
                """, (project_id, job_id))
            return True
        except Exception:
            return False

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
