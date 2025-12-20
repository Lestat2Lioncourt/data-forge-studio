"""
Base Repository - Abstract base class for all repositories.

Provides common CRUD operations and database access patterns.
"""
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar, Generic, List, Optional, Any
from datetime import datetime
import logging

from ..connection_pool import ConnectionPool

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common database operations.

    Subclasses must implement:
    - table_name: Name of the database table
    - _row_to_model: Convert database row to model instance
    - _model_to_tuple: Convert model to tuple for INSERT/UPDATE
    """

    def __init__(self, pool: ConnectionPool):
        """
        Initialize repository with connection pool.

        Args:
            pool: ConnectionPool instance for database access
        """
        self.pool = pool

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the name of the database table."""
        pass

    @abstractmethod
    def _row_to_model(self, row: sqlite3.Row) -> T:
        """Convert a database row to a model instance."""
        pass

    @abstractmethod
    def _get_insert_sql(self) -> str:
        """Return the INSERT SQL statement."""
        pass

    @abstractmethod
    def _get_update_sql(self) -> str:
        """Return the UPDATE SQL statement."""
        pass

    @abstractmethod
    def _model_to_insert_tuple(self, model: T) -> tuple:
        """Convert model to tuple for INSERT."""
        pass

    @abstractmethod
    def _model_to_update_tuple(self, model: T) -> tuple:
        """Convert model to tuple for UPDATE (values + id)."""
        pass

    def get_all(self, order_by: str = "name") -> List[T]:
        """
        Get all records from the table.

        Args:
            order_by: Column to order by (default: "name")

        Returns:
            List of model instances
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name} ORDER BY {order_by}")
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_by_id(self, id: str) -> Optional[T]:
        """
        Get a record by ID.

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None

    def add(self, model: T) -> bool:
        """
        Add a new record.

        Args:
            model: Model instance to add

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(self._get_insert_sql(), self._model_to_insert_tuple(model))
            return True
        except Exception as e:
            logger.error(f"Error adding {self.table_name} record: {e}")
            return False

    def update(self, model: T) -> bool:
        """
        Update an existing record.

        Args:
            model: Model instance with updated values

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(self._get_update_sql(), self._model_to_update_tuple(model))
            return True
        except Exception as e:
            logger.error(f"Error updating {self.table_name} record: {e}")
            return False

    def delete(self, id: str) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting {self.table_name} record: {e}")
            return False

    def exists(self, id: str) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record ID to check

        Returns:
            True if exists, False otherwise
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT 1 FROM {self.table_name} WHERE id = ? LIMIT 1", (id,))
            return cursor.fetchone() is not None

    def count(self) -> int:
        """
        Count all records in the table.

        Returns:
            Number of records
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cursor.fetchone()[0]
