"""
Connection Pool Module - Manages SQLite connections with pooling and transactions.

Provides:
- ConnectionPool: Reusable connection pool for SQLite
- Transaction context manager for atomic operations
"""
import sqlite3
import queue
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    SQLite connection pool for efficient connection reuse.

    Features:
    - Connection reuse to avoid overhead of repeated connect/disconnect
    - Thread-safe connection management
    - Automatic connection health checks
    - Transaction support with context manager

    Usage:
        pool = ConnectionPool(db_path, max_connections=5)

        # Simple usage
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")

        # Transaction
        with pool.transaction() as conn:
            conn.execute("INSERT INTO table VALUES (?)", (value,))
            conn.execute("UPDATE other_table SET x = ?", (value,))
            # Auto-commit on success, auto-rollback on exception
    """

    def __init__(self, db_path: Path, max_connections: int = 5):
        """
        Initialize the connection pool.

        Args:
            db_path: Path to SQLite database file
            max_connections: Maximum number of connections to keep in pool
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: queue.Queue = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._created_count = 0

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with standard settings."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _validate_connection(self, conn: sqlite3.Connection) -> bool:
        """Check if a connection is still valid."""
        try:
            conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.

        Yields a connection that will be returned to the pool when done.
        Use this for read operations or when you manage transactions manually.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None

        # Try to get from pool first
        try:
            conn = self._pool.get_nowait()
            # Validate the connection
            if not self._validate_connection(conn):
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
        except queue.Empty:
            pass

        # Create new connection if needed
        if conn is None:
            with self._lock:
                if self._created_count < self.max_connections:
                    conn = self._create_connection()
                    self._created_count += 1
                    logger.debug(f"Created new connection ({self._created_count}/{self.max_connections})")
                else:
                    # Wait for a connection from the pool
                    conn = self._pool.get(timeout=30)

        try:
            yield conn
        finally:
            # Return connection to pool
            try:
                self._pool.put_nowait(conn)
            except queue.Full:
                # Pool is full, close this connection
                try:
                    conn.close()
                    with self._lock:
                        self._created_count -= 1
                except Exception:
                    pass

    @contextmanager
    def transaction(self):
        """
        Get a connection with automatic transaction management.

        Commits on successful exit, rolls back on exception.
        Use this for write operations that need atomicity.

        Yields:
            sqlite3.Connection: Database connection with transaction

        Example:
            with pool.transaction() as conn:
                conn.execute("INSERT INTO table VALUES (?)", (value,))
                conn.execute("UPDATE other_table SET x = ?", (value,))
            # Auto-commit here
        """
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def close_all(self):
        """Close all connections in the pool."""
        while True:
            try:
                conn = self._pool.get_nowait()
                try:
                    conn.close()
                except Exception:
                    pass
            except queue.Empty:
                break

        with self._lock:
            self._created_count = 0

        logger.debug("Closed all pooled connections")

    def __del__(self):
        """Cleanup on garbage collection."""
        self.close_all()


# Global pool instance (lazy initialization)
_global_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_pool(db_path: Optional[Path] = None) -> ConnectionPool:
    """
    Get the global connection pool instance.

    Args:
        db_path: Path to database (required on first call)

    Returns:
        ConnectionPool instance
    """
    global _global_pool

    with _pool_lock:
        if _global_pool is None:
            if db_path is None:
                raise ValueError("db_path required for first initialization")
            _global_pool = ConnectionPool(db_path)
        return _global_pool


def reset_pool():
    """Reset the global pool (useful for testing)."""
    global _global_pool

    with _pool_lock:
        if _global_pool is not None:
            _global_pool.close_all()
            _global_pool = None
