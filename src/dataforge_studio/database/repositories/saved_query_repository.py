"""
Saved Query Repository - CRUD operations for saved queries.
"""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import SavedQuery


class SavedQueryRepository(BaseRepository[SavedQuery]):
    """Repository for SavedQuery entities."""

    @property
    def table_name(self) -> str:
        return "saved_queries"

    def _row_to_model(self, row: sqlite3.Row) -> SavedQuery:
        return SavedQuery(**dict(row))

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO saved_queries
            (id, name, target_database_id, query_text, category, description,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE saved_queries
            SET name = ?, target_database_id = ?, query_text = ?,
                category = ?, description = ?, updated_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: SavedQuery) -> tuple:
        return (model.id, model.name, model.target_database_id, model.query_text,
                model.category, model.description, model.created_at, model.updated_at)

    def _model_to_update_tuple(self, model: SavedQuery) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.target_database_id, model.query_text,
                model.category, model.description, model.updated_at, model.id)

    def get_all_queries(self) -> List[SavedQuery]:
        """Get all saved queries ordered by category then name."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_queries ORDER BY category, name")
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_queries_by_category(self, category: str) -> List[SavedQuery]:
        """Get all saved queries in a specific category."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM saved_queries WHERE category = ? ORDER BY name",
                (category,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_queries_by_database(self, database_id: str) -> List[SavedQuery]:
        """Get all saved queries for a specific database."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM saved_queries WHERE target_database_id = ? ORDER BY category, name",
                (database_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_all_categories(self) -> List[str]:
        """Get all unique category names."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT category FROM saved_queries ORDER BY category"
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows if row[0]]
