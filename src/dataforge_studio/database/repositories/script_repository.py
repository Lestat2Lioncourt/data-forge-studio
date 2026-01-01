"""
Script Repository - CRUD operations for scripts.
"""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import Script


class ScriptRepository(BaseRepository[Script]):
    """Repository for Script entities."""

    @property
    def table_name(self) -> str:
        return "scripts"

    def _row_to_model(self, row: sqlite3.Row) -> Script:
        return Script(**dict(row))

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO scripts
            (id, name, description, script_type, file_path, parameters_schema, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE scripts
            SET name = ?, description = ?, script_type = ?, file_path = ?,
                parameters_schema = ?, updated_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: Script) -> tuple:
        return (model.id, model.name, model.description, model.script_type,
                model.file_path, model.parameters_schema, model.created_at, model.updated_at)

    def _model_to_update_tuple(self, model: Script) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.description, model.script_type, model.file_path,
                model.parameters_schema, model.updated_at, model.id)

    def get_all_scripts(self) -> List[Script]:
        """Get all scripts ordered by name."""
        return self.get_all(order_by="name")

    def get_by_type(self, script_type: str) -> List[Script]:
        """Get all scripts of a specific type."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM scripts WHERE script_type = ? ORDER BY name",
                (script_type,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_by_name(self, name: str) -> Optional[Script]:
        """Get a script by its unique name."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scripts WHERE name = ?", (name,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
