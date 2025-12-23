"""
Configuration Database Module - SQLite database for all configuration
Migrated for PySide6 version.

Models are defined in database/models/ package.
This module provides the ConfigDatabase class as a facade for all database operations.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import asdict
import uuid
from datetime import datetime

# Import all models from the models package
from .models import (
    DatabaseConnection,
    FileConfig,
    SavedQuery,
    Project,
    Workspace,
    FileRoot,
    Script,
    Job,
    ImageRootfolder,
    SavedImage,
)
from .models.workspace_resource import WorkspaceFileRoot, WorkspaceDatabase


class ConfigDatabase:
    """SQLite database for configuration management"""

    # Configuration database internal ID
    CONFIG_DB_ID = "config-db-self-ref"
    CONFIG_DB_NAME = "Configuration Database"

    def __init__(self):
        # Store config in project root/_AppConfig/
        # Path: src/dataforge_studio/database/config_db.py -> need 4 levels up to reach project root
        project_root = Path(__file__).parent.parent.parent.parent
        self.db_path = project_root / "_AppConfig" / "configuration.db"
        self._ensure_db_folder()
        self._init_database()
        self._migrate_database()

    def _ensure_db_folder(self):
        """Ensure config folder exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_database(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Database Connections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS database_connections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                db_type TEXT NOT NULL,
                description TEXT,
                connection_string TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
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

        # Project-Database junction table (database_name allows specific database within a server)
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

        # Project-Job junction table (for workspace assignments)
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

        # Project-Script junction table (for workspace assignments)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_scripts (
                project_id TEXT NOT NULL,
                script_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (project_id, script_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE
            )
        """)

        # Scripts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                script_type TEXT NOT NULL,
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

        # Image Rootfolders table (for automatic image scanning)
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

        # Saved Images table (image library)
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

        # Image Categories junction table (many-to-many: image <-> logical categories)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_categories (
                image_id TEXT NOT NULL,
                category_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (image_id, category_name),
                FOREIGN KEY (image_id) REFERENCES saved_images(id) ON DELETE CASCADE
            )
        """)

        # Image Tags junction table (many-to-many: image <-> tags)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_tags (
                image_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (image_id, tag_name),
                FOREIGN KEY (image_id) REFERENCES saved_images(id) ON DELETE CASCADE
            )
        """)

        # User Preferences table (key-value store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_db_name ON database_connections(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_name ON file_configs(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_category ON saved_queries(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_name ON projects(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_root_path ON file_roots(path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_script_name ON scripts(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_project ON jobs(project_id)")
        # Image library indexes (created after migration adds the columns)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_category_name ON image_categories(category_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_tag_name ON image_tags(tag_name)")

        conn.commit()

        # Ensure config DB self-reference exists
        self._ensure_config_db_connection(cursor, conn)

        conn.close()

    def _ensure_config_db_connection(self, cursor, conn):
        """Ensure a connection to the configuration database itself exists"""
        cursor.execute("""
            SELECT connection_string FROM database_connections
            WHERE id = ?
        """, (self.CONFIG_DB_ID,))

        result = cursor.fetchone()
        # Use sqlite:/// format for consistency with DatabaseManager
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
            print(f"[OK] Added self-reference connection to Configuration Database")
        elif result[0] != expected_conn_string:
            # Update connection string if path has changed
            cursor.execute("""
                UPDATE database_connections
                SET connection_string = ?, updated_at = ?
                WHERE id = ?
            """, (expected_conn_string, datetime.now().isoformat(), self.CONFIG_DB_ID))

            conn.commit()
            print(f"[OK] Updated Configuration Database connection path")

    def _migrate_database(self):
        """Apply database migrations for schema updates"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Migration 1: Add 'name' column to file_roots if it doesn't exist
        cursor.execute("PRAGMA table_info(file_roots)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'name' not in columns:
            print("[MIGRATION] Adding 'name' column to file_roots table...")

            # Add the column
            cursor.execute("ALTER TABLE file_roots ADD COLUMN name TEXT")

            # Initialize name from path for existing records
            cursor.execute("SELECT id, path FROM file_roots WHERE name IS NULL")
            rows = cursor.fetchall()

            for row_id, path in rows:
                # Extract folder name from path
                folder_name = Path(path).name if path else "Unnamed"
                cursor.execute(
                    "UPDATE file_roots SET name = ? WHERE id = ?",
                    (folder_name, row_id)
                )

            conn.commit()
            print(f"[OK] Migration complete: Initialized {len(rows)} file root names from paths")

        # Migration 2: Add 'database_name' column to project_databases if it doesn't exist
        cursor.execute("PRAGMA table_info(project_databases)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'database_name' not in columns:
            print("[MIGRATION] Adding 'database_name' column to project_databases table...")

            # SQLite doesn't support adding column with PRIMARY KEY constraint
            # So we need to recreate the table
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

            # Copy existing data with empty database_name (meaning all databases)
            cursor.execute("""
                INSERT INTO project_databases_new (project_id, database_id, database_name, created_at)
                SELECT project_id, database_id, '', created_at FROM project_databases
            """)

            # Drop old table and rename new one
            cursor.execute("DROP TABLE project_databases")
            cursor.execute("ALTER TABLE project_databases_new RENAME TO project_databases")

            conn.commit()
            print("[OK] Migration complete: project_databases now supports database_name")

        # Migration 3: Update saved_images table structure (add rootfolder_id, physical_path)
        cursor.execute("PRAGMA table_info(saved_images)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'rootfolder_id' not in columns:
            print("[MIGRATION] Updating saved_images table structure...")

            # Create new table with updated schema
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

            # Copy existing data (old 'category' column becomes a logical category)
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

            # Drop old table and rename new one
            cursor.execute("DROP TABLE saved_images")
            cursor.execute("ALTER TABLE saved_images_new RENAME TO saved_images")

            # Create indexes on new columns
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_rootfolder ON saved_images(rootfolder_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_physical_path ON saved_images(physical_path)")

            conn.commit()
            print(f"[OK] Migration complete: saved_images updated, {len(old_categories)} categories migrated")

        # Ensure image indexes exist (for fresh installs or post-migration)
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_rootfolder ON saved_images(rootfolder_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_physical_path ON saved_images(physical_path)")
            conn.commit()
        except Exception:
            pass  # Indexes may already exist or columns don't exist yet

        conn.close()

    # ==================== Database Connections ====================

    def get_all_database_connections(self) -> List[DatabaseConnection]:
        """Get all database connections (including configuration.db)"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM database_connections ORDER BY name")
        rows = cursor.fetchall()

        db_conn.close()

        return [DatabaseConnection(**dict(row)) for row in rows]

    def get_business_database_connections(self) -> List[DatabaseConnection]:
        """
        Get business database connections only (excludes configuration.db).
        Use this for script/job configuration where config DB should not be proposed.
        """
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT * FROM database_connections
            WHERE id != ?
            ORDER BY name
        """, (self.CONFIG_DB_ID,))
        rows = cursor.fetchall()

        db_conn.close()

        return [DatabaseConnection(**dict(row)) for row in rows]

    def is_config_database(self, connection_id: str) -> bool:
        """Check if a database connection is the configuration database"""
        return connection_id == self.CONFIG_DB_ID

    def get_database_connection(self, conn_id: str) -> Optional[DatabaseConnection]:
        """Get a database connection by ID"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM database_connections WHERE id = ?", (conn_id,))
        row = cursor.fetchone()

        db_conn.close()

        if row:
            return DatabaseConnection(**dict(row))
        return None

    def add_database_connection(self, conn: DatabaseConnection) -> bool:
        """Add a new database connection"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT INTO database_connections
                (id, name, db_type, description, connection_string, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (conn.id, conn.name, conn.db_type, conn.description,
                  conn.connection_string, conn.created_at, conn.updated_at))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding database connection: {e}")
            return False

    def update_database_connection(self, conn: DatabaseConnection) -> bool:
        """Update an existing database connection"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            conn.updated_at = datetime.now().isoformat()

            cursor.execute("""
                UPDATE database_connections
                SET name = ?, db_type = ?, description = ?,
                    connection_string = ?, updated_at = ?
                WHERE id = ?
            """, (conn.name, conn.db_type, conn.description,
                  conn.connection_string, conn.updated_at, conn.id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating database connection: {e}")
            return False

    def delete_database_connection(self, conn_id: str) -> bool:
        """Delete a database connection"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("DELETE FROM database_connections WHERE id = ?", (conn_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error deleting database connection: {e}")
            return False

    def save_database_connection(self, conn: DatabaseConnection) -> bool:
        """
        Save a database connection (add if new, update if exists).

        Args:
            conn: DatabaseConnection object to save

        Returns:
            True if saved successfully, False otherwise
        """
        # Check if connection already exists
        existing = self.get_database_connection(conn.id)

        if existing:
            return self.update_database_connection(conn)
        else:
            return self.add_database_connection(conn)

    # ==================== Saved Queries ====================

    def get_all_saved_queries(self) -> List[SavedQuery]:
        """Get all saved queries"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM saved_queries ORDER BY category, name")
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedQuery(**dict(row)) for row in rows]

    def add_saved_query(self, query: SavedQuery) -> bool:
        """Add a new saved query"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT INTO saved_queries
                (id, name, target_database_id, query_text, category, description,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (query.id, query.name, query.target_database_id, query.query_text,
                  query.category, query.description, query.created_at, query.updated_at))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding saved query: {e}")
            return False

    def update_saved_query(self, query: SavedQuery) -> bool:
        """Update an existing saved query"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            query.updated_at = datetime.now().isoformat()

            cursor.execute("""
                UPDATE saved_queries
                SET name = ?, target_database_id = ?, query_text = ?,
                    category = ?, description = ?, updated_at = ?
                WHERE id = ?
            """, (query.name, query.target_database_id, query.query_text,
                  query.category, query.description, query.updated_at, query.id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating saved query: {e}")
            return False

    def delete_saved_query(self, query_id: str) -> bool:
        """Delete a saved query"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("DELETE FROM saved_queries WHERE id = ?", (query_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error deleting saved query: {e}")
            return False

    # ==================== Scripts ====================

    def get_all_scripts(self) -> List[Script]:
        """Get all scripts"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM scripts ORDER BY name")
        rows = cursor.fetchall()

        db_conn.close()

        return [Script(**dict(row)) for row in rows]

    def get_script(self, script_id: str) -> Optional[Script]:
        """Get script by ID"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
        row = cursor.fetchone()

        db_conn.close()

        if row:
            return Script(**dict(row))
        return None

    # ==================== Jobs ====================

    def get_all_jobs(self) -> List[Job]:
        """Get all jobs"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM jobs ORDER BY name")
        rows = cursor.fetchall()

        db_conn.close()

        return [Job(**dict(row)) for row in rows]

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()

        db_conn.close()

        if row:
            return Job(**dict(row))
        return None

    def update_job(self, job: Job) -> bool:
        """Update an existing job"""
        try:
            job.updated_at = datetime.now().isoformat()

            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                UPDATE jobs
                SET name = ?, description = ?, job_type = ?, script_id = ?, project_id = ?,
                    parent_job_id = ?, previous_job_id = ?, parameters = ?, enabled = ?,
                    updated_at = ?, last_run_at = ?
                WHERE id = ?
            """, (
                job.name, job.description, job.job_type, job.script_id, job.project_id,
                job.parent_job_id, job.previous_job_id, job.parameters, job.enabled,
                job.updated_at, job.last_run_at, job.id
            ))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating job: {e}")
            return False

    # ==================== Projects ====================

    def get_all_projects(self, sort_by_usage: bool = True) -> List[Project]:
        """Get all projects"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        if sort_by_usage:
            cursor.execute("""
                SELECT * FROM projects
                ORDER BY last_used_at DESC, name ASC
            """)
        else:
            cursor.execute("SELECT * FROM projects ORDER BY name")

        rows = cursor.fetchall()
        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()

        db_conn.close()

        if row:
            return Project(**dict(row))
        return None

    # ==================== Workspaces (alias for Projects) ====================

    # Alias methods for workspace terminology
    def get_all_workspaces(self, sort_by_usage: bool = True) -> List[Project]:
        """Get all workspaces (alias for get_all_projects)"""
        return self.get_all_projects(sort_by_usage)

    def get_workspace(self, workspace_id: str) -> Optional[Project]:
        """Get a workspace by ID (alias for get_project)"""
        return self.get_project(workspace_id)

    def add_workspace(self, workspace: Project) -> bool:
        """Add a new workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT INTO projects
                (id, name, description, is_default, created_at, updated_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (workspace.id, workspace.name, workspace.description,
                  1 if workspace.is_default else 0,
                  workspace.created_at, workspace.updated_at, workspace.last_used_at))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding workspace: {e}")
            return False

    def update_workspace(self, workspace: Project) -> bool:
        """Update an existing workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            workspace.updated_at = datetime.now().isoformat()

            cursor.execute("""
                UPDATE projects
                SET name = ?, description = ?, is_default = ?,
                    updated_at = ?, last_used_at = ?
                WHERE id = ?
            """, (workspace.name, workspace.description,
                  1 if workspace.is_default else 0,
                  workspace.updated_at, workspace.last_used_at, workspace.id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating workspace: {e}")
            return False

    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace (cascade deletes junction table entries)"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("DELETE FROM projects WHERE id = ?", (workspace_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error deleting workspace: {e}")
            return False

    def touch_workspace(self, workspace_id: str) -> bool:
        """Update last_used_at timestamp for a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                UPDATE projects
                SET last_used_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), workspace_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error touching workspace: {e}")
            return False

    # ==================== Workspace-Database Relations ====================

    def add_database_to_workspace(self, workspace_id: str, database_id: str,
                                   database_name: str = None) -> bool:
        """
        Add a database to a workspace.

        Args:
            workspace_id: Workspace ID
            database_id: Database connection (server) ID
            database_name: Specific database name (None or '' = all databases on server)
        """
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO project_databases
                (project_id, database_id, database_name, created_at)
                VALUES (?, ?, ?, ?)
            """, (workspace_id, database_id, database_name or '',
                  datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding database to workspace: {e}")
            return False

    def remove_database_from_workspace(self, workspace_id: str, database_id: str,
                                        database_name: str = None) -> bool:
        """
        Remove a database from a workspace.

        Args:
            workspace_id: Workspace ID
            database_id: Database connection (server) ID
            database_name: Specific database name (None or '' = all databases on server)
        """
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM project_databases
                WHERE project_id = ? AND database_id = ? AND database_name = ?
            """, (workspace_id, database_id, database_name or ''))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing database from workspace: {e}")
            return False

    def get_workspace_databases(self, workspace_id: str) -> List[DatabaseConnection]:
        """Get all database connections (servers) in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT DISTINCT dc.* FROM database_connections dc
            INNER JOIN project_databases pd ON dc.id = pd.database_id
            WHERE pd.project_id = ?
            ORDER BY dc.name
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [DatabaseConnection(**dict(row)) for row in rows]

    def get_workspace_databases_with_context(self, workspace_id: str) -> List[WorkspaceDatabase]:
        """
        Get all databases in a workspace WITH their database_name context.

        Returns WorkspaceDatabase objects that include:
        - The DatabaseConnection object (server config)
        - The database_name (empty string if whole server, specific name if single DB)

        This is the preferred method for WorkspaceManager to get complete information.
        """
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT dc.*, pd.database_name
            FROM database_connections dc
            INNER JOIN project_databases pd ON dc.id = pd.database_id
            WHERE pd.project_id = ?
            ORDER BY dc.name, pd.database_name
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        result = []
        for row in rows:
            row_dict = dict(row)
            database_name = row_dict.pop('database_name', '') or ''
            connection = DatabaseConnection(**row_dict)
            result.append(WorkspaceDatabase(connection=connection, database_name=database_name))

        return result

    def get_workspace_database_entries(self, workspace_id: str) -> List[Tuple[str, str, str]]:
        """
        Get all database entries in a workspace with details.

        Returns:
            List of tuples: (database_id, database_name, created_at)
            database_name = '' means all databases on that server
        """
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT database_id, database_name, created_at FROM project_databases
            WHERE project_id = ?
            ORDER BY database_id, database_name
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [(row[0], row[1], row[2]) for row in rows]

    def get_workspace_database_ids(self, workspace_id: str) -> List[str]:
        """Get all database IDs in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT DISTINCT database_id FROM project_databases
            WHERE project_id = ?
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_database_workspaces(self, database_id: str, database_name: str = None) -> List[Project]:
        """
        Get all workspaces that contain a database.

        Args:
            database_id: Database connection (server) ID
            database_name: Specific database name (None = check server-level only,
                          '' = check server-level, or provide specific name)
        """
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        if database_name is not None:
            # Check for specific database_name (or '' for server-level)
            cursor.execute("""
                SELECT p.* FROM projects p
                INNER JOIN project_databases pd ON p.id = pd.project_id
                WHERE pd.database_id = ? AND pd.database_name = ?
                ORDER BY p.name
            """, (database_id, database_name))
        else:
            # Get all workspaces that have this server (any database_name)
            cursor.execute("""
                SELECT DISTINCT p.* FROM projects p
                INNER JOIN project_databases pd ON p.id = pd.project_id
                WHERE pd.database_id = ?
                ORDER BY p.name
            """, (database_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    def is_database_in_workspace(self, workspace_id: str, database_id: str,
                                  database_name: str = None) -> bool:
        """
        Check if a database (server or specific db) is in a workspace.

        Args:
            workspace_id: Workspace ID
            database_id: Database connection (server) ID
            database_name: Specific database name (None or '' = server-level)
        """
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT 1 FROM project_databases
            WHERE project_id = ? AND database_id = ? AND database_name = ?
            LIMIT 1
        """, (workspace_id, database_id, database_name or ''))
        row = cursor.fetchone()

        db_conn.close()

        return row is not None

    # ==================== Workspace-Query Relations ====================

    def add_query_to_workspace(self, workspace_id: str, query_id: str) -> bool:
        """Add a query to a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO project_queries
                (project_id, query_id, created_at)
                VALUES (?, ?, ?)
            """, (workspace_id, query_id, datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding query to workspace: {e}")
            return False

    def remove_query_from_workspace(self, workspace_id: str, query_id: str) -> bool:
        """Remove a query from a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM project_queries
                WHERE project_id = ? AND query_id = ?
            """, (workspace_id, query_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing query from workspace: {e}")
            return False

    def get_workspace_queries(self, workspace_id: str) -> List[SavedQuery]:
        """Get all queries in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT sq.* FROM saved_queries sq
            INNER JOIN project_queries pq ON sq.id = pq.query_id
            WHERE pq.project_id = ?
            ORDER BY sq.name
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedQuery(**dict(row)) for row in rows]

    def get_workspace_query_ids(self, workspace_id: str) -> List[str]:
        """Get all query IDs in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT query_id FROM project_queries
            WHERE project_id = ?
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_query_workspaces(self, query_id: str) -> List[Project]:
        """Get all workspaces that contain a query"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT p.* FROM projects p
            INNER JOIN project_queries pq ON p.id = pq.project_id
            WHERE pq.query_id = ?
            ORDER BY p.name
        """, (query_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    # ==================== Workspace-FileRoot Relations ====================

    def add_file_root_to_workspace(self, workspace_id: str, file_root_id: str,
                                    subfolder_path: str = None) -> bool:
        """Add a file root to a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO project_file_roots
                (project_id, file_root_id, subfolder_path, created_at)
                VALUES (?, ?, ?, ?)
            """, (workspace_id, file_root_id, subfolder_path or '',
                  datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding file root to workspace: {e}")
            return False

    def remove_file_root_from_workspace(self, workspace_id: str, file_root_id: str) -> bool:
        """Remove a file root from a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM project_file_roots
                WHERE project_id = ? AND file_root_id = ?
            """, (workspace_id, file_root_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing file root from workspace: {e}")
            return False

    def get_workspace_file_roots(self, workspace_id: str) -> List[FileRoot]:
        """Get all file roots in a workspace (alias for get_project_file_roots)"""
        return self.get_project_file_roots(workspace_id)

    def get_workspace_file_roots_with_context(self, workspace_id: str) -> List[WorkspaceFileRoot]:
        """
        Get all file roots in a workspace WITH their subfolder context.

        Returns WorkspaceFileRoot objects that include:
        - The FileRoot object
        - The subfolder_path (empty string if root, relative path if subfolder)

        This is the preferred method for WorkspaceManager to get complete information.
        """
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT fr.*, pfr.subfolder_path
            FROM file_roots fr
            INNER JOIN project_file_roots pfr ON fr.id = pfr.file_root_id
            WHERE pfr.project_id = ?
            ORDER BY pfr.subfolder_path, fr.path
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        result = []
        for row in rows:
            row_dict = dict(row)
            subfolder_path = row_dict.pop('subfolder_path', '') or ''
            file_root = FileRoot(**row_dict)
            result.append(WorkspaceFileRoot(file_root=file_root, subfolder_path=subfolder_path))

        return result

    def get_workspace_file_root_ids(self, workspace_id: str) -> List[str]:
        """Get all file root IDs in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT file_root_id FROM project_file_roots
            WHERE project_id = ?
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_file_root_workspaces(self, file_root_id: str, subfolder_path: str = None) -> List[Project]:
        """Get all workspaces that contain a file root (optionally with specific subfolder)"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        if subfolder_path:
            cursor.execute("""
                SELECT p.* FROM projects p
                INNER JOIN project_file_roots pfr ON p.id = pfr.project_id
                WHERE pfr.file_root_id = ? AND pfr.subfolder_path = ?
                ORDER BY p.name
            """, (file_root_id, subfolder_path))
        else:
            cursor.execute("""
                SELECT p.* FROM projects p
                INNER JOIN project_file_roots pfr ON p.id = pfr.project_id
                WHERE pfr.file_root_id = ?
                ORDER BY p.name
            """, (file_root_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    # ==================== Workspace-Job Relations ====================

    def add_job_to_workspace(self, workspace_id: str, job_id: str) -> bool:
        """Add a job to a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO project_jobs
                (project_id, job_id, created_at)
                VALUES (?, ?, ?)
            """, (workspace_id, job_id, datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding job to workspace: {e}")
            return False

    def remove_job_from_workspace(self, workspace_id: str, job_id: str) -> bool:
        """Remove a job from a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM project_jobs
                WHERE project_id = ? AND job_id = ?
            """, (workspace_id, job_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing job from workspace: {e}")
            return False

    def get_workspace_jobs(self, workspace_id: str) -> List:
        """Get all jobs in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT j.* FROM jobs j
            INNER JOIN project_jobs pj ON j.id = pj.job_id
            WHERE pj.project_id = ?
            ORDER BY j.name
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Job(**dict(row)) for row in rows]

    def get_workspace_job_ids(self, workspace_id: str) -> List[str]:
        """Get all job IDs in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT job_id FROM project_jobs
            WHERE project_id = ?
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_job_workspaces(self, job_id: str) -> List[Project]:
        """Get all workspaces that contain a job"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT p.* FROM projects p
            INNER JOIN project_jobs pj ON p.id = pj.project_id
            WHERE pj.job_id = ?
            ORDER BY p.name
        """, (job_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    # ==================== Workspace-Script Relations ====================

    def add_script_to_workspace(self, workspace_id: str, script_id: str) -> bool:
        """Add a script to a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO project_scripts
                (project_id, script_id, created_at)
                VALUES (?, ?, ?)
            """, (workspace_id, script_id, datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding script to workspace: {e}")
            return False

    def remove_script_from_workspace(self, workspace_id: str, script_id: str) -> bool:
        """Remove a script from a workspace"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM project_scripts
                WHERE project_id = ? AND script_id = ?
            """, (workspace_id, script_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing script from workspace: {e}")
            return False

    def get_workspace_scripts(self, workspace_id: str) -> List[Script]:
        """Get all scripts in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT s.* FROM scripts s
            INNER JOIN project_scripts ps ON s.id = ps.script_id
            WHERE ps.project_id = ?
            ORDER BY s.script_type, s.name
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Script(**dict(row)) for row in rows]

    def get_workspace_script_ids(self, workspace_id: str) -> List[str]:
        """Get all script IDs in a workspace"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT script_id FROM project_scripts
            WHERE project_id = ?
        """, (workspace_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_script_workspaces(self, script_id: str) -> List[Project]:
        """Get all workspaces that contain a script"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT p.* FROM projects p
            INNER JOIN project_scripts ps ON p.id = ps.project_id
            WHERE ps.script_id = ?
            ORDER BY p.name
        """, (script_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    # ==================== File Roots ====================

    def get_all_file_roots(self) -> List[FileRoot]:
        """Get all file roots"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM file_roots ORDER BY path")
        rows = cursor.fetchall()

        db_conn.close()

        return [FileRoot(**dict(row)) for row in rows]

    def get_project_file_roots(self, project_id: str) -> List[FileRoot]:
        """Get all file roots associated with a project"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT fr.* FROM file_roots fr
            INNER JOIN project_file_roots pfr ON fr.id = pfr.file_root_id
            WHERE pfr.project_id = ?
            ORDER BY fr.path
        """, (project_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [FileRoot(**dict(row)) for row in rows]

    def _save_file_root(self, file_root: FileRoot):
        """Save or update a file root"""
        from datetime import datetime

        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        # Set timestamps if not provided
        now = datetime.now().isoformat()
        created_at = file_root.created_at or now
        updated_at = now

        cursor.execute("""
            INSERT OR REPLACE INTO file_roots (id, path, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (file_root.id, file_root.path, file_root.name or '', file_root.description or '', created_at, updated_at))

        db_conn.commit()
        db_conn.close()

    def _delete_file_root(self, file_root_id: str):
        """Delete a file root"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("DELETE FROM file_roots WHERE id = ?", (file_root_id,))

        db_conn.commit()
        db_conn.close()

    # ==================== User Preferences ====================

    def get_preference(self, key: str, default: str = None) -> Optional[str]:
        """Get a user preference value by key"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        row = cursor.fetchone()

        db_conn.close()

        if row:
            return row[0]
        return default

    def set_preference(self, key: str, value: str) -> bool:
        """Set a user preference value (insert or update)"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
            """, (key, value, datetime.now().isoformat(), value, datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error setting preference: {e}")
            return False

    def get_all_preferences(self) -> dict:
        """Get all user preferences as a dictionary"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT key, value FROM user_preferences")
        rows = cursor.fetchall()

        db_conn.close()

        return {row[0]: row[1] for row in rows}

    # ==================== Image Rootfolders ====================

    def get_all_image_rootfolders(self) -> List[ImageRootfolder]:
        """Get all image rootfolders"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM image_rootfolders ORDER BY name")
        rows = cursor.fetchall()

        db_conn.close()

        return [ImageRootfolder(**dict(row)) for row in rows]

    def get_image_rootfolder(self, rootfolder_id: str) -> Optional[ImageRootfolder]:
        """Get an image rootfolder by ID"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM image_rootfolders WHERE id = ?", (rootfolder_id,))
        row = cursor.fetchone()

        db_conn.close()

        return ImageRootfolder(**dict(row)) if row else None

    def add_image_rootfolder(self, rootfolder: ImageRootfolder) -> bool:
        """Add a new image rootfolder"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT INTO image_rootfolders
                (id, path, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (rootfolder.id, rootfolder.path, rootfolder.name,
                  rootfolder.description, rootfolder.created_at, rootfolder.updated_at))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding image rootfolder: {e}")
            return False

    def update_image_rootfolder(self, rootfolder: ImageRootfolder) -> bool:
        """Update an existing image rootfolder"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            rootfolder.updated_at = datetime.now().isoformat()

            cursor.execute("""
                UPDATE image_rootfolders
                SET path = ?, name = ?, description = ?, updated_at = ?
                WHERE id = ?
            """, (rootfolder.path, rootfolder.name, rootfolder.description,
                  rootfolder.updated_at, rootfolder.id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating image rootfolder: {e}")
            return False

    def delete_image_rootfolder(self, rootfolder_id: str) -> bool:
        """Delete an image rootfolder (cascade deletes associated images)"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("DELETE FROM image_rootfolders WHERE id = ?", (rootfolder_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error deleting image rootfolder: {e}")
            return False

    # ==================== Saved Images ====================

    def get_all_saved_images(self) -> List[SavedImage]:
        """Get all saved images"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM saved_images ORDER BY physical_path, name")
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedImage(**dict(row)) for row in rows]

    def get_images_by_rootfolder(self, rootfolder_id: str) -> List[SavedImage]:
        """Get all images in a rootfolder"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT * FROM saved_images
            WHERE rootfolder_id = ?
            ORDER BY physical_path, name
        """, (rootfolder_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedImage(**dict(row)) for row in rows]

    def get_images_by_physical_path(self, rootfolder_id: str, physical_path: str) -> List[SavedImage]:
        """Get all images in a specific physical path within a rootfolder"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT * FROM saved_images
            WHERE rootfolder_id = ? AND physical_path = ?
            ORDER BY name
        """, (rootfolder_id, physical_path))
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedImage(**dict(row)) for row in rows]

    def get_saved_image(self, image_id: str) -> Optional[SavedImage]:
        """Get a saved image by ID"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM saved_images WHERE id = ?", (image_id,))
        row = cursor.fetchone()

        db_conn.close()

        return SavedImage(**dict(row)) if row else None

    def get_saved_image_by_filepath(self, filepath: str) -> Optional[SavedImage]:
        """Get a saved image by filepath"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM saved_images WHERE filepath = ?", (filepath,))
        row = cursor.fetchone()

        db_conn.close()

        return SavedImage(**dict(row)) if row else None

    def add_saved_image(self, name: str, filepath: str, rootfolder_id: str = None,
                        physical_path: str = "", description: str = "") -> Optional[str]:
        """
        Add a new saved image.

        Args:
            name: Display name for the image
            filepath: Absolute path to the image file
            rootfolder_id: Optional FK to image_rootfolders
            physical_path: Relative path within rootfolder (e.g., "Screenshots/2024")
            description: Optional description

        Returns:
            Image ID if successful, None otherwise
        """
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            image = SavedImage(
                id=str(uuid.uuid4()),
                name=name,
                filepath=filepath,
                rootfolder_id=rootfolder_id,
                physical_path=physical_path,
                description=description
            )

            cursor.execute("""
                INSERT INTO saved_images
                (id, name, filepath, rootfolder_id, physical_path, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (image.id, image.name, image.filepath, image.rootfolder_id,
                  image.physical_path, image.description, image.created_at, image.updated_at))

            db_conn.commit()
            db_conn.close()
            return image.id
        except Exception as e:
            print(f"Error adding saved image: {e}")
            return None

    def update_saved_image(self, image: SavedImage) -> bool:
        """Update an existing saved image"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            image.updated_at = datetime.now().isoformat()

            cursor.execute("""
                UPDATE saved_images
                SET name = ?, filepath = ?, rootfolder_id = ?, physical_path = ?,
                    description = ?, updated_at = ?
                WHERE id = ?
            """, (image.name, image.filepath, image.rootfolder_id, image.physical_path,
                  image.description, image.updated_at, image.id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating saved image: {e}")
            return False

    def delete_saved_image(self, image_id: str) -> bool:
        """Delete a saved image (cascade deletes categories and tags)"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("DELETE FROM saved_images WHERE id = ?", (image_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error deleting saved image: {e}")
            return False

    def delete_images_by_rootfolder(self, rootfolder_id: str) -> int:
        """Delete all images in a rootfolder. Returns count of deleted images."""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM saved_images WHERE rootfolder_id = ?", (rootfolder_id,))
            count = cursor.fetchone()[0]

            cursor.execute("DELETE FROM saved_images WHERE rootfolder_id = ?", (rootfolder_id,))

            db_conn.commit()
            db_conn.close()
            return count
        except Exception as e:
            print(f"Error deleting images by rootfolder: {e}")
            return 0

    # ==================== Image Categories ====================

    def get_image_categories(self, image_id: str) -> List[str]:
        """Get all logical categories for an image"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT category_name FROM image_categories
            WHERE image_id = ?
            ORDER BY category_name
        """, (image_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_all_image_category_names(self) -> List[str]:
        """Get all unique logical category names across all images"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT DISTINCT category_name FROM image_categories
            ORDER BY category_name
        """)
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_images_by_category(self, category_name: str) -> List[SavedImage]:
        """Get all images in a logical category"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT si.* FROM saved_images si
            INNER JOIN image_categories ic ON si.id = ic.image_id
            WHERE ic.category_name = ?
            ORDER BY si.name
        """, (category_name,))
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedImage(**dict(row)) for row in rows]

    def add_image_category(self, image_id: str, category_name: str) -> bool:
        """Add a logical category to an image"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO image_categories (image_id, category_name, created_at)
                VALUES (?, ?, ?)
            """, (image_id, category_name, datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding image category: {e}")
            return False

    def remove_image_category(self, image_id: str, category_name: str) -> bool:
        """Remove a logical category from an image"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM image_categories
                WHERE image_id = ? AND category_name = ?
            """, (image_id, category_name))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing image category: {e}")
            return False

    def set_image_categories(self, image_id: str, category_names: List[str]) -> bool:
        """Set all logical categories for an image (replaces existing)"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            # Remove existing categories
            cursor.execute("DELETE FROM image_categories WHERE image_id = ?", (image_id,))

            # Add new categories
            now = datetime.now().isoformat()
            for cat_name in category_names:
                if cat_name.strip():
                    cursor.execute("""
                        INSERT INTO image_categories (image_id, category_name, created_at)
                        VALUES (?, ?, ?)
                    """, (image_id, cat_name.strip(), now))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error setting image categories: {e}")
            return False

    # ==================== Image Tags ====================

    def get_image_tags(self, image_id: str) -> List[str]:
        """Get all tags for an image"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT tag_name FROM image_tags
            WHERE image_id = ?
            ORDER BY tag_name
        """, (image_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_all_image_tag_names(self) -> List[str]:
        """Get all unique tag names across all images"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT DISTINCT tag_name FROM image_tags
            ORDER BY tag_name
        """)
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    def get_images_by_tag(self, tag_name: str) -> List[SavedImage]:
        """Get all images with a specific tag"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT si.* FROM saved_images si
            INNER JOIN image_tags it ON si.id = it.image_id
            WHERE it.tag_name = ?
            ORDER BY si.name
        """, (tag_name,))
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedImage(**dict(row)) for row in rows]

    def add_image_tag(self, image_id: str, tag_name: str) -> bool:
        """Add a tag to an image"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO image_tags (image_id, tag_name, created_at)
                VALUES (?, ?, ?)
            """, (image_id, tag_name.strip().lower(), datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding image tag: {e}")
            return False

    def remove_image_tag(self, image_id: str, tag_name: str) -> bool:
        """Remove a tag from an image"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM image_tags
                WHERE image_id = ? AND tag_name = ?
            """, (image_id, tag_name))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing image tag: {e}")
            return False

    def set_image_tags(self, image_id: str, tag_names: List[str]) -> bool:
        """Set all tags for an image (replaces existing)"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            # Remove existing tags
            cursor.execute("DELETE FROM image_tags WHERE image_id = ?", (image_id,))

            # Add new tags (normalized to lowercase)
            now = datetime.now().isoformat()
            for tag in tag_names:
                tag_clean = tag.strip().lower()
                if tag_clean:
                    cursor.execute("""
                        INSERT INTO image_tags (image_id, tag_name, created_at)
                        VALUES (?, ?, ?)
                    """, (image_id, tag_clean, now))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error setting image tags: {e}")
            return False

    # ==================== Image Search ====================

    def search_images(self, query: str, search_name: bool = True,
                      search_categories: bool = True, search_tags: bool = True) -> List[SavedImage]:
        """
        Search images by name, categories, and/or tags.

        Args:
            query: Search query string
            search_name: Include filename in search
            search_categories: Include logical categories in search
            search_tags: Include tags in search

        Returns:
            List of matching SavedImage objects (deduplicated)
        """
        if not query.strip():
            return []

        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        query_pattern = f"%{query.strip()}%"
        image_ids = set()

        # Search in name
        if search_name:
            cursor.execute("""
                SELECT id FROM saved_images
                WHERE name LIKE ? OR filepath LIKE ?
            """, (query_pattern, query_pattern))
            for row in cursor.fetchall():
                image_ids.add(row[0])

        # Search in categories
        if search_categories:
            cursor.execute("""
                SELECT DISTINCT image_id FROM image_categories
                WHERE category_name LIKE ?
            """, (query_pattern,))
            for row in cursor.fetchall():
                image_ids.add(row[0])

        # Search in tags
        if search_tags:
            cursor.execute("""
                SELECT DISTINCT image_id FROM image_tags
                WHERE tag_name LIKE ?
            """, (query_pattern.lower(),))
            for row in cursor.fetchall():
                image_ids.add(row[0])

        # Fetch full image objects
        if not image_ids:
            db_conn.close()
            return []

        placeholders = ",".join("?" * len(image_ids))
        cursor.execute(f"""
            SELECT * FROM saved_images
            WHERE id IN ({placeholders})
            ORDER BY name
        """, list(image_ids))
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedImage(**dict(row)) for row in rows]

    def get_image_physical_paths(self, rootfolder_id: str) -> List[str]:
        """Get all unique physical paths within a rootfolder"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT DISTINCT physical_path FROM saved_images
            WHERE rootfolder_id = ?
            ORDER BY physical_path
        """, (rootfolder_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]


# Global configuration database instance
def get_config_db() -> ConfigDatabase:
    """Get the global configuration database instance"""
    global _config_db_instance
    if '_config_db_instance' not in globals():
        _config_db_instance = ConfigDatabase()
    return _config_db_instance
