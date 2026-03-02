"""
File Root Repository - CRUD operations for file roots.
"""
import sqlite3
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import FileRoot


class FileRootRepository(BaseRepository[FileRoot]):
    """Repository for FileRoot entities."""

    @property
    def table_name(self) -> str:
        return "file_roots"

    def _row_to_model(self, row: sqlite3.Row) -> FileRoot:
        return FileRoot(**dict(row))

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO file_roots
            (id, path, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE file_roots
            SET path = ?, name = ?, description = ?, updated_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: FileRoot) -> tuple:
        return (model.id, model.path, model.name or '',
                model.description or '', model.created_at, model.updated_at)

    def _model_to_update_tuple(self, model: FileRoot) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.path, model.name or '', model.description or '',
                model.updated_at, model.id)

    def get_all_file_roots(self) -> List[FileRoot]:
        """Get all file roots ordered by path."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_roots ORDER BY path")
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_by_path(self, path: str) -> Optional[FileRoot]:
        """Get a file root by its path."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_roots WHERE path = ?", (path,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None

    def save(self, file_root: FileRoot) -> bool:
        """
        Save or update a file root using INSERT OR REPLACE.

        Args:
            file_root: FileRoot object to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            now = datetime.now().isoformat()
            created_at = file_root.created_at or now
            updated_at = now

            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO file_roots
                    (id, path, name, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (file_root.id, file_root.path, file_root.name or '',
                      file_root.description or '', created_at, updated_at))
            return True
        except sqlite3.Error:
            return False
