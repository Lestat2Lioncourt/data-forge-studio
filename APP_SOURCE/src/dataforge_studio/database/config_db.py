"""
Configuration Database Module - SQLite database for all configuration
Migrated for PySide6 version v0.50
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid
from datetime import datetime


@dataclass
class DatabaseConnection:
    """Database connection configuration"""
    id: str
    name: str
    db_type: str
    description: str
    connection_string: str
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


@dataclass
class FileConfig:
    """File configuration"""
    id: str
    name: str
    location: str
    description: str
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


@dataclass
class SavedQuery:
    """Saved query configuration"""
    id: str
    name: str
    target_database_id: str
    query_text: str
    category: str = "No category"
    description: str = ""
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        if not self.category:
            self.category = "No category"


@dataclass
class Project:
    """Project/Workspace configuration for organizing databases, queries, and files"""
    id: str
    name: str
    description: str
    is_default: bool = False
    created_at: str = None
    updated_at: str = None
    last_used_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


# Alias for Workspace (same as Project for backward compatibility)
Workspace = Project


@dataclass
class FileRoot:
    """File root directory configuration"""
    id: str
    path: str
    name: str = None  # Display name for the root folder
    description: str = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            # Default name from path if not provided
            self.name = Path(self.path).name if self.path else "Unnamed"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


@dataclass
class Script:
    """Script definition (generic, reusable)"""
    id: str
    name: str
    description: str
    script_type: str
    parameters_schema: str
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


@dataclass
class Job:
    """
    Job = Can be either:
    1. Atomic job: Script instance with configured parameters
    2. Workflow job: Container of other jobs
    """
    id: str
    name: str
    description: str
    job_type: str
    script_id: str = None
    project_id: str = None
    parent_job_id: str = None
    previous_job_id: str = None
    parameters: str = None
    enabled: bool = True
    created_at: str = None
    updated_at: str = None
    last_run_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


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


# Global configuration database instance
def get_config_db() -> ConfigDatabase:
    """Get the global configuration database instance"""
    global _config_db_instance
    if '_config_db_instance' not in globals():
        _config_db_instance = ConfigDatabase()
    return _config_db_instance
