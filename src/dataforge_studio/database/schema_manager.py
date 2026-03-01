"""
Schema Manager Module - Database schema initialization and migrations.

Extracted from config_db.py for better separation of concerns.
Handles:
- CREATE TABLE statements
- Index creation
- Schema migrations
- Config DB self-reference
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

from .models import DatabaseConnection

logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Manages SQLite database schema for configuration database.

    Responsibilities:
    - Initialize database schema (CREATE TABLE)
    - Create indexes for performance
    - Apply migrations for schema updates
    - Ensure config DB self-reference exists
    """

    # Configuration database internal ID
    CONFIG_DB_ID = "config-db-self-ref"
    CONFIG_DB_NAME = "Configuration Database"

    # Current schema version (increment when adding migrations)
    SCHEMA_VERSION = 5

    def __init__(self, db_path: Path):
        """
        Initialize schema manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with standard settings."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self):
        """
        Initialize database schema and run migrations.

        Call this once during application startup.
        """
        self._init_database()
        self._migrate_database()

    def _init_database(self):
        """Initialize database schema with all tables."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Database Connections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS database_connections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    db_type TEXT NOT NULL,
                    description TEXT,
                    connection_string TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    color TEXT
                )
            """)

            # File Configurations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_configs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Saved Queries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_queries (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    target_database_id TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    category TEXT DEFAULT 'No category',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (target_database_id) REFERENCES database_connections(id)
                )
            """)

            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT
                )
            """)

            # File Roots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_roots (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    name TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Project-Database junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_databases (
                    project_id TEXT NOT NULL,
                    database_id TEXT NOT NULL,
                    database_name TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, database_id, database_name),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (database_id) REFERENCES database_connections(id) ON DELETE CASCADE
                )
            """)

            # Project-Query junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_queries (
                    project_id TEXT NOT NULL,
                    query_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, query_id),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (query_id) REFERENCES saved_queries(id) ON DELETE CASCADE
                )
            """)

            # Project-FileRoot junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_file_roots (
                    project_id TEXT NOT NULL,
                    file_root_id TEXT NOT NULL,
                    subfolder_path TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, file_root_id, subfolder_path),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (file_root_id) REFERENCES file_roots(id) ON DELETE CASCADE
                )
            """)

            # Project-Job junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_jobs (
                    project_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, job_id),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            """)

            # Scripts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    script_type TEXT NOT NULL,
                    file_path TEXT DEFAULT '',
                    parameters_schema TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    job_type TEXT NOT NULL CHECK(job_type IN ('script', 'workflow')),
                    script_id TEXT,
                    project_id TEXT,
                    parent_job_id TEXT,
                    previous_job_id TEXT,
                    parameters TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_run_at TEXT,
                    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                    FOREIGN KEY (previous_job_id) REFERENCES jobs(id) ON DELETE SET NULL
                )
            """)

            # Image Rootfolders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_rootfolders (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    name TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Saved Images table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_images (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    filepath TEXT NOT NULL UNIQUE,
                    rootfolder_id TEXT,
                    physical_path TEXT DEFAULT '',
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (rootfolder_id) REFERENCES image_rootfolders(id) ON DELETE CASCADE
                )
            """)

            # Image Categories junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_categories (
                    image_id TEXT NOT NULL,
                    category_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (image_id, category_name),
                    FOREIGN KEY (image_id) REFERENCES saved_images(id) ON DELETE CASCADE
                )
            """)

            # Image Tags junction table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_tags (
                    image_id TEXT NOT NULL,
                    tag_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (image_id, tag_name),
                    FOREIGN KEY (image_id) REFERENCES saved_images(id) ON DELETE CASCADE
                )
            """)

            # User Preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create indexes
            self._create_indexes(cursor)

            conn.commit()

            # Ensure config DB self-reference exists
            self._ensure_config_db_connection(cursor, conn)

        finally:
            conn.close()

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Create all database indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_db_name ON database_connections(name)",
            "CREATE INDEX IF NOT EXISTS idx_file_name ON file_configs(name)",
            "CREATE INDEX IF NOT EXISTS idx_query_category ON saved_queries(category)",
            "CREATE INDEX IF NOT EXISTS idx_project_name ON projects(name)",
            "CREATE INDEX IF NOT EXISTS idx_file_root_path ON file_roots(path)",
            "CREATE INDEX IF NOT EXISTS idx_script_name ON scripts(name)",
            "CREATE INDEX IF NOT EXISTS idx_job_project ON jobs(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_image_category_name ON image_categories(category_name)",
            "CREATE INDEX IF NOT EXISTS idx_image_tag_name ON image_tags(tag_name)",
        ]

        for sql in indexes:
            cursor.execute(sql)

    def _ensure_config_db_connection(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Ensure a connection to the configuration database itself exists."""
        cursor.execute("""
            SELECT connection_string FROM database_connections
            WHERE id = ?
        """, (self.CONFIG_DB_ID,))

        result = cursor.fetchone()
        expected_conn_string = f"sqlite:///{str(self.db_path)}"

        if result is None:
            # Add connection to configuration database
            config_conn = DatabaseConnection(
                id=self.CONFIG_DB_ID,
                name=self.CONFIG_DB_NAME,
                db_type="sqlite",
                description="Application configuration database (internal use)",
                connection_string=expected_conn_string
            )

            cursor.execute("""
                INSERT INTO database_connections
                (id, name, db_type, description, connection_string, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (config_conn.id, config_conn.name, config_conn.db_type,
                  config_conn.description, config_conn.connection_string,
                  config_conn.created_at, config_conn.updated_at))

            conn.commit()
            logger.info("Added self-reference connection to Configuration Database")

        elif result[0] != expected_conn_string:
            # Update connection string if path has changed
            cursor.execute("""
                UPDATE database_connections
                SET connection_string = ?, updated_at = ?
                WHERE id = ?
            """, (expected_conn_string, datetime.now().isoformat(), self.CONFIG_DB_ID))

            conn.commit()
            logger.info("Updated Configuration Database connection path")

    def _migrate_database(self):
        """Apply database migrations for schema updates."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Migration 1: Add 'name' column to file_roots
            self._migrate_file_roots_name(cursor, conn)

            # Migration 2: Add 'database_name' column to project_databases
            self._migrate_project_databases_name(cursor, conn)

            # Migration 3: Update saved_images table structure
            self._migrate_saved_images_structure(cursor, conn)

            # Migration 4: Add 'file_path' column to scripts
            self._migrate_scripts_file_path(cursor, conn)

            # Migration 5: Add 'auto_connect' column to projects
            self._migrate_projects_auto_connect(cursor, conn)

            # Migration 6: Add 'target_database_name' column to saved_queries
            self._migrate_saved_queries_database_name(cursor, conn)

            # Migration 7: Add 'color' column to database_connections
            self._migrate_database_connections_color(cursor, conn)

            # Ensure image indexes exist
            self._ensure_image_indexes(cursor, conn)

        finally:
            conn.close()

    def _migrate_file_roots_name(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Migration 1: Add 'name' column to file_roots if it doesn't exist."""
        cursor.execute("PRAGMA table_info(file_roots)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'name' not in columns:
            logger.info("[MIGRATION] Adding 'name' column to file_roots table...")

            cursor.execute("ALTER TABLE file_roots ADD COLUMN name TEXT")

            # Initialize name from path for existing records
            cursor.execute("SELECT id, path FROM file_roots WHERE name IS NULL")
            rows = cursor.fetchall()

            for row_id, path in rows:
                folder_name = Path(path).name if path else "Unnamed"
                cursor.execute(
                    "UPDATE file_roots SET name = ? WHERE id = ?",
                    (folder_name, row_id)
                )

            conn.commit()
            logger.info(f"[OK] Migration complete: Initialized {len(rows)} file root names from paths")

    def _migrate_project_databases_name(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Migration 2: Add 'database_name' column to project_databases."""
        cursor.execute("PRAGMA table_info(project_databases)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'database_name' not in columns:
            logger.info("[MIGRATION] Adding 'database_name' column to project_databases table...")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_databases_new (
                    project_id TEXT NOT NULL,
                    database_id TEXT NOT NULL,
                    database_name TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, database_id, database_name),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (database_id) REFERENCES database_connections(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                INSERT INTO project_databases_new (project_id, database_id, database_name, created_at)
                SELECT project_id, database_id, '', created_at FROM project_databases
            """)

            cursor.execute("DROP TABLE project_databases")
            cursor.execute("ALTER TABLE project_databases_new RENAME TO project_databases")

            conn.commit()
            logger.info("[OK] Migration complete: project_databases now supports database_name")

    def _migrate_saved_images_structure(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Migration 3: Update saved_images table structure (add rootfolder_id, physical_path)."""
        cursor.execute("PRAGMA table_info(saved_images)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'rootfolder_id' not in columns:
            logger.info("[MIGRATION] Updating saved_images table structure...")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_images_new (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    filepath TEXT NOT NULL UNIQUE,
                    rootfolder_id TEXT,
                    physical_path TEXT DEFAULT '',
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (rootfolder_id) REFERENCES image_rootfolders(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                INSERT INTO saved_images_new (id, name, filepath, rootfolder_id, physical_path, description, created_at, updated_at)
                SELECT id, name, filepath, NULL, '', description, created_at, updated_at FROM saved_images
            """)

            # Migrate old categories to image_categories junction table
            cursor.execute("""
                SELECT id, category FROM saved_images WHERE category IS NOT NULL AND category != 'No category'
            """)
            old_categories = cursor.fetchall()

            for image_id, category in old_categories:
                cursor.execute("""
                    INSERT OR IGNORE INTO image_categories (image_id, category_name, created_at)
                    VALUES (?, ?, ?)
                """, (image_id, category, datetime.now().isoformat()))

            cursor.execute("DROP TABLE saved_images")
            cursor.execute("ALTER TABLE saved_images_new RENAME TO saved_images")

            # Create indexes on new columns
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_rootfolder ON saved_images(rootfolder_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_physical_path ON saved_images(physical_path)")

            conn.commit()
            logger.info(f"[OK] Migration complete: saved_images updated, {len(old_categories)} categories migrated")

    def _migrate_scripts_file_path(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Migration 4: Add 'file_path' column to scripts if it doesn't exist."""
        cursor.execute("PRAGMA table_info(scripts)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'file_path' not in columns:
            logger.info("[MIGRATION] Adding 'file_path' column to scripts table...")

            cursor.execute("ALTER TABLE scripts ADD COLUMN file_path TEXT DEFAULT ''")

            conn.commit()
            logger.info("[OK] Migration complete: scripts now supports file_path")

    def _migrate_projects_auto_connect(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Migration 5: Add 'auto_connect' column to projects if it doesn't exist."""
        cursor.execute("PRAGMA table_info(projects)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'auto_connect' not in columns:
            logger.info("[MIGRATION] Adding 'auto_connect' column to projects table...")

            cursor.execute("ALTER TABLE projects ADD COLUMN auto_connect INTEGER DEFAULT 0")

            conn.commit()
            logger.info("[OK] Migration complete: projects now supports auto_connect")

    def _migrate_saved_queries_database_name(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Migration 6: Add 'target_database_name' column to saved_queries if it doesn't exist."""
        cursor.execute("PRAGMA table_info(saved_queries)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'target_database_name' not in columns:
            logger.info("[MIGRATION] Adding 'target_database_name' column to saved_queries table...")

            cursor.execute("ALTER TABLE saved_queries ADD COLUMN target_database_name TEXT DEFAULT ''")

            # Pre-fill existing queries with connection name as fallback
            cursor.execute("""
                UPDATE saved_queries
                SET target_database_name = (
                    SELECT dc.name FROM database_connections dc
                    WHERE dc.id = saved_queries.target_database_id
                )
                WHERE target_database_name = '' OR target_database_name IS NULL
            """)

            conn.commit()
            logger.info("[OK] Migration complete: saved_queries now supports target_database_name")

    def _migrate_database_connections_color(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Migration 7: Add 'color' column to database_connections if it doesn't exist."""
        cursor.execute("PRAGMA table_info(database_connections)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'color' not in columns:
            logger.info("[MIGRATION] Adding 'color' column to database_connections table...")

            cursor.execute("ALTER TABLE database_connections ADD COLUMN color TEXT")

            conn.commit()
            logger.info("[OK] Migration complete: database_connections now supports color")

    def _ensure_image_indexes(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection):
        """Ensure image indexes exist (for fresh installs or post-migration)."""
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_rootfolder ON saved_images(rootfolder_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_physical_path ON saved_images(physical_path)")
            conn.commit()
        except Exception:
            pass  # Indexes may already exist or columns don't exist yet


# Singleton instance
_schema_manager: Optional[SchemaManager] = None


def get_schema_manager(db_path: Optional[Path] = None) -> SchemaManager:
    """
    Get the schema manager singleton.

    Args:
        db_path: Path to database (required on first call)

    Returns:
        SchemaManager instance
    """
    global _schema_manager

    if _schema_manager is None:
        if db_path is None:
            raise ValueError("db_path required for first initialization")
        _schema_manager = SchemaManager(db_path)

    return _schema_manager
