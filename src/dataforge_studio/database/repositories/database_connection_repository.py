"""
Database Connection Repository - CRUD operations for database connections.
"""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import DatabaseConnection


class DatabaseConnectionRepository(BaseRepository[DatabaseConnection]):
    """Repository for DatabaseConnection entities."""

    # Configuration database internal ID
    CONFIG_DB_ID = "config-db-self-ref"

    @property
    def table_name(self) -> str:
        return "database_connections"

    def _row_to_model(self, row: sqlite3.Row) -> DatabaseConnection:
        return DatabaseConnection(**dict(row))

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO database_connections
            (id, name, db_type, description, connection_string, created_at, updated_at, color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE database_connections
            SET name = ?, db_type = ?, description = ?,
                connection_string = ?, updated_at = ?, color = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: DatabaseConnection) -> tuple:
        return (model.id, model.name, model.db_type, model.description,
                model.connection_string, model.created_at, model.updated_at, model.color)

    def _model_to_update_tuple(self, model: DatabaseConnection) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.db_type, model.description,
                model.connection_string, model.updated_at, model.color, model.id)

    def get_all_connections(self) -> List[DatabaseConnection]:
        """Get all database connections (including configuration.db)."""
        return self.get_all(order_by="name")

    def get_business_connections(self) -> List[DatabaseConnection]:
        """
        Get business database connections only (excludes configuration.db).
        Use this for script/job configuration where config DB should not be proposed.
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM database_connections
                WHERE id != ?
                ORDER BY name
            """, (self.CONFIG_DB_ID,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def is_config_database(self, connection_id: str) -> bool:
        """Check if a database connection is the configuration database."""
        return connection_id == self.CONFIG_DB_ID

    def save(self, conn: DatabaseConnection) -> bool:
        """
        Save a database connection (add if new, update if exists).

        Args:
            conn: DatabaseConnection object to save

        Returns:
            True if saved successfully, False otherwise
        """
        existing = self.get_by_id(conn.id)
        if existing:
            return self.update(conn)
        else:
            return self.add(conn)
