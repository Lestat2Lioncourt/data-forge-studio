"""
Job Repository - CRUD operations for jobs.
"""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import Job


class JobRepository(BaseRepository[Job]):
    """Repository for Job entities."""

    @property
    def table_name(self) -> str:
        return "jobs"

    def _row_to_model(self, row: sqlite3.Row) -> Job:
        return Job(**dict(row))

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO jobs
            (id, name, description, job_type, script_id, project_id, parent_job_id,
             previous_job_id, parameters, enabled, created_at, updated_at, last_run_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE jobs
            SET name = ?, description = ?, job_type = ?, script_id = ?, project_id = ?,
                parent_job_id = ?, previous_job_id = ?, parameters = ?, enabled = ?,
                updated_at = ?, last_run_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: Job) -> tuple:
        return (model.id, model.name, model.description, model.job_type,
                model.script_id, model.project_id, model.parent_job_id,
                model.previous_job_id, model.parameters, model.enabled,
                model.created_at, model.updated_at, model.last_run_at)

    def _model_to_update_tuple(self, model: Job) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.description, model.job_type, model.script_id,
                model.project_id, model.parent_job_id, model.previous_job_id,
                model.parameters, model.enabled, model.updated_at, model.last_run_at,
                model.id)

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs ordered by name."""
        return self.get_all(order_by="name")

    def get_by_project(self, project_id: str) -> List[Job]:
        """Get all jobs for a specific project."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE project_id = ? ORDER BY name",
                (project_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_by_script(self, script_id: str) -> List[Job]:
        """Get all jobs that use a specific script."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE script_id = ? ORDER BY name",
                (script_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_children(self, parent_job_id: str) -> List[Job]:
        """Get all child jobs of a parent job (workflow)."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE parent_job_id = ? ORDER BY name",
                (parent_job_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_enabled(self) -> List[Job]:
        """Get all enabled jobs."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE enabled = 1 ORDER BY name"
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def set_enabled(self, job_id: str, enabled: bool) -> bool:
        """Enable or disable a job."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE jobs SET enabled = ?, updated_at = ?
                    WHERE id = ?
                """, (1 if enabled else 0, datetime.now().isoformat(), job_id))
            return True
        except Exception:
            return False

    def update_last_run(self, job_id: str) -> bool:
        """Update the last_run_at timestamp for a job."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE jobs SET last_run_at = ?, updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), datetime.now().isoformat(), job_id))
            return True
        except Exception:
            return False
