"""
User Preferences Repository - Key-value store for user settings.
"""
import sqlite3
from typing import Optional, Dict
from datetime import datetime

from ..connection_pool import ConnectionPool


class UserPreferencesRepository:
    """
    Repository for user preferences (key-value store).

    Unlike other repositories, this doesn't use a model class
    since preferences are simple key-value pairs.
    """

    def __init__(self, pool: ConnectionPool):
        """
        Initialize repository with connection pool.

        Args:
            pool: ConnectionPool instance for database access
        """
        self.pool = pool

    def get(self, key: str, default: str = None) -> Optional[str]:
        """
        Get a preference value by key.

        Args:
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value or default
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set(self, key: str, value: str) -> bool:
        """
        Set a preference value (insert or update).

        Args:
            key: Preference key
            value: Preference value

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_preferences (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
                """, (key, value, datetime.now().isoformat(),
                      value, datetime.now().isoformat()))
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a preference by key.

        Args:
            key: Preference key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_preferences WHERE key = ?", (key,))
            return True
        except Exception:
            return False

    def get_all(self) -> Dict[str, str]:
        """
        Get all preferences as a dictionary.

        Returns:
            Dictionary of all preferences
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_preferences")
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}

    def exists(self, key: str) -> bool:
        """
        Check if a preference exists.

        Args:
            key: Preference key to check

        Returns:
            True if exists, False otherwise
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_preferences WHERE key = ? LIMIT 1",
                (key,)
            )
            return cursor.fetchone() is not None
