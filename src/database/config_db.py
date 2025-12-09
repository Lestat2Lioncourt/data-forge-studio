"""
Configuration Database Module - SQLite database for all configuration
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from ..utils.config import Config
from ..utils.logger import logger
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
    category: str = "No category"  # Optional, defaults to "No category"
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
    """Project configuration for organizing databases, queries, and files"""
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


@dataclass
class FileRoot:
    """File root directory configuration"""
    id: str
    path: str
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


class ConfigDatabase:
    """SQLite database for configuration management"""

    def __init__(self):
        # Store config in project root folder
        # Go up from src/database/ to project root
        project_root = Path(__file__).parent.parent.parent
        self.db_path = project_root / "_AppConfig" / "configuration.db"
        self._ensure_db_folder()
        self._init_database()

    def _ensure_db_folder(self):
        """Ensure config folder exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraints
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
                project TEXT NOT NULL,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                target_database_id TEXT NOT NULL,
                query_text TEXT NOT NULL,
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
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Project-Database junction table (many-to-many)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_databases (
                project_id TEXT NOT NULL,
                database_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (project_id, database_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (database_id) REFERENCES database_connections(id) ON DELETE CASCADE
            )
        """)

        # Project-Query junction table (many-to-many)
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

        # Project-FileRoot junction table (many-to-many)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_file_roots (
                project_id TEXT NOT NULL,
                file_root_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (project_id, file_root_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (file_root_id) REFERENCES file_roots(id) ON DELETE CASCADE
            )
        """)

        # Project-Jobs junction table (many-to-many) - for future use
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_jobs (
                project_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (project_id, job_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_db_name ON database_connections(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_name ON file_configs(name)")
        # Note: idx_query_project removed - project column no longer exists after migration
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_category ON saved_queries(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_name ON projects(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_last_used ON projects(last_used_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_root_path ON file_roots(path)")

        conn.commit()

        # Migration: Add is_default column to projects table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE projects ADD COLUMN is_default INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # Migration: Migrate saved_queries to remove project column and make category optional
        self._migrate_saved_queries_schema(cursor, conn)

        # Fix any saved queries that still reference the 'project' column
        # This runs every time to catch queries added/modified after migration
        self._fix_queries_referencing_project_column(cursor, conn)

        # Add self-reference connection if not exists
        self._ensure_config_db_connection(cursor, conn)

        conn.close()

    def _migrate_saved_queries_schema(self, cursor, conn):
        """
        Migrate saved_queries table to remove project column and make category optional
        Also migrate existing project associations to project_queries junction table
        """
        # Check if migration is needed by checking if 'project' column exists
        cursor.execute("PRAGMA table_info(saved_queries)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'project' not in columns:
            # Migration already done
            return

        logger.info("Migrating saved_queries schema: removing project column, making category optional")

        # Step 1: Migrate project associations to project_queries table
        cursor.execute("""
            SELECT id, project, target_database_id
            FROM saved_queries
            WHERE project IS NOT NULL AND project != ''
        """)
        queries_with_projects = cursor.fetchall()

        for query_id, project_name, db_id in queries_with_projects:
            # Find or create project
            cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
            project_row = cursor.fetchone()

            if project_row:
                project_id = project_row[0]
                # Add to project_queries if not already there
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO project_queries (project_id, query_id, created_at)
                        VALUES (?, ?, ?)
                    """, (project_id, query_id, datetime.now().isoformat()))
                except Exception as e:
                    logger.warning(f"Could not migrate query {query_id} to project {project_name}: {e}")

        conn.commit()
        logger.info(f"Migrated {len(queries_with_projects)} query-project associations")

        # Step 2: Create new table without project column and with optional category
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_queries_new (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target_database_id TEXT NOT NULL,
                query_text TEXT NOT NULL,
                category TEXT DEFAULT 'No category',
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (target_database_id) REFERENCES database_connections(id)
            )
        """)

        # Step 3: Copy data to new table, handling NULL or empty categories
        cursor.execute("""
            INSERT INTO saved_queries_new (
                id, name, target_database_id, query_text,
                category, description, created_at, updated_at
            )
            SELECT
                id, name, target_database_id, query_text,
                CASE
                    WHEN category IS NULL OR category = '' THEN 'No category'
                    ELSE category
                END,
                description, created_at, updated_at
            FROM saved_queries
        """)

        # Step 4: Drop old table
        cursor.execute("DROP TABLE saved_queries")

        # Step 5: Rename new table
        cursor.execute("ALTER TABLE saved_queries_new RENAME TO saved_queries")

        # Step 6: Recreate indexes (drop the project index)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_category ON saved_queries(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_database ON saved_queries(target_database_id)")

        conn.commit()
        logger.important("Successfully migrated saved_queries schema")

    def _fix_queries_referencing_project_column(self, cursor, conn):
        """Fix saved queries that still reference the removed 'project' column"""
        try:
            # Get all queries that might reference 'project' column
            cursor.execute("""
                SELECT id, name, query_text
                FROM saved_queries
                WHERE LOWER(query_text) LIKE '%project%'
            """)
            queries_to_fix = cursor.fetchall()

            if not queries_to_fix:
                return

            logger.info(f"Found {len(queries_to_fix)} queries referencing 'project' column")

            for query_id, name, query_text in queries_to_fix:
                original_query = query_text
                updated = False

                # Common patterns to fix
                # Pattern 1: "SELECT project, ..." -> "SELECT category, ..."
                if "SELECT project," in query_text or "SELECT project " in query_text:
                    query_text = query_text.replace("SELECT project,", "SELECT category,")
                    query_text = query_text.replace("SELECT project ", "SELECT category ")
                    updated = True

                # Pattern 2: "GROUP BY project" -> "GROUP BY category"
                if "GROUP BY project" in query_text:
                    query_text = query_text.replace("GROUP BY project", "GROUP BY category")
                    updated = True

                # Pattern 3: "WHERE project =" -> Remove the WHERE clause or comment it
                if "WHERE project" in query_text:
                    # This is trickier, we'll just comment it out
                    query_text = query_text.replace("WHERE project", "-- WHERE project (removed - column no longer exists)")
                    updated = True

                if updated:
                    # Update the query
                    cursor.execute("""
                        UPDATE saved_queries
                        SET query_text = ?,
                            updated_at = ?
                        WHERE id = ?
                    """, (query_text, datetime.now().isoformat(), query_id))

                    logger.info(f"Fixed query '{name}':")
                    logger.info(f"  Before: {original_query}")
                    logger.info(f"  After:  {query_text}")

            conn.commit()
            logger.important(f"Fixed {len([q for q in queries_to_fix])} queries referencing 'project' column")

        except Exception as e:
            logger.error(f"Error fixing queries referencing project column: {e}")

    def _ensure_config_db_connection(self, cursor, conn):
        """Ensure a connection to the configuration database itself exists"""
        # Check if configuration DB connection already exists
        cursor.execute("""
            SELECT connection_string FROM database_connections
            WHERE name = 'Configuration Database'
        """)

        result = cursor.fetchone()
        expected_conn_string = f"DRIVER={{SQLite3 ODBC Driver}};Database={str(self.db_path)}"

        if result is None:
            # Add connection to configuration database
            config_conn = DatabaseConnection(
                id="config-db-self-ref",
                name="Configuration Database",
                db_type="sqlite",
                description="Application configuration database (self-reference)",
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
                WHERE name = 'Configuration Database'
            """, (expected_conn_string, datetime.now().isoformat()))

            conn.commit()
            print(f"[OK] Updated Configuration Database connection path to: {self.db_path}")

    # ==================== Database Connections ====================

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

    def get_all_database_connections(self) -> List[DatabaseConnection]:
        """Get all database connections"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM database_connections ORDER BY name")
        rows = cursor.fetchall()

        db_conn.close()

        return [DatabaseConnection(**dict(row)) for row in rows]

    # ==================== File Configurations ====================

    def add_file_config(self, file_config: FileConfig) -> bool:
        """Add a new file configuration"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT INTO file_configs
                (id, name, location, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_config.id, file_config.name, file_config.location,
                  file_config.description, file_config.created_at, file_config.updated_at))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding file config: {e}")
            return False

    def update_file_config(self, file_config: FileConfig) -> bool:
        """Update an existing file configuration"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            file_config.updated_at = datetime.now().isoformat()

            cursor.execute("""
                UPDATE file_configs
                SET name = ?, location = ?, description = ?, updated_at = ?
                WHERE id = ?
            """, (file_config.name, file_config.location, file_config.description,
                  file_config.updated_at, file_config.id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating file config: {e}")
            return False

    def delete_file_config(self, file_id: str) -> bool:
        """Delete a file configuration"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("DELETE FROM file_configs WHERE id = ?", (file_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error deleting file config: {e}")
            return False

    def get_all_file_configs(self) -> List[FileConfig]:
        """Get all file configurations"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM file_configs ORDER BY name")
        rows = cursor.fetchall()

        db_conn.close()

        return [FileConfig(**dict(row)) for row in rows]

    # ==================== Saved Queries ====================

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

    def get_saved_queries_by_category(self, category: str) -> List[SavedQuery]:
        """Get all saved queries for a category"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT * FROM saved_queries
            WHERE category = ?
            ORDER BY name
        """, (category,))
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedQuery(**dict(row)) for row in rows]

    def get_all_saved_queries(self) -> List[SavedQuery]:
        """Get all saved queries"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM saved_queries ORDER BY category, name")
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedQuery(**dict(row)) for row in rows]

    def get_categories(self) -> List[str]:
        """Get all distinct categories"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT DISTINCT category
            FROM saved_queries
            ORDER BY category
        """)
        rows = cursor.fetchall()

        db_conn.close()

        return [row[0] for row in rows]

    # ==================== Projects ====================

    def add_project(self, project: Project) -> bool:
        """Add a new project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            # If this is the default project, unset all other defaults
            if project.is_default:
                cursor.execute("UPDATE projects SET is_default = 0")

            cursor.execute("""
                INSERT INTO projects
                (id, name, description, is_default, created_at, updated_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project.id, project.name, project.description, int(project.is_default),
                  project.created_at, project.updated_at, project.last_used_at))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding project: {e}")
            return False

    def update_project(self, project: Project) -> bool:
        """Update an existing project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            project.updated_at = datetime.now().isoformat()

            # If this is the default project, unset all other defaults
            if project.is_default:
                cursor.execute("UPDATE projects SET is_default = 0 WHERE id != ?", (project.id,))

            cursor.execute("""
                UPDATE projects
                SET name = ?, description = ?, is_default = ?, updated_at = ?, last_used_at = ?
                WHERE id = ?
            """, (project.name, project.description, int(project.is_default), project.updated_at,
                  project.last_used_at, project.id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating project: {e}")
            return False

    def delete_project(self, project_id: str) -> bool:
        """Delete a project (cascades to all associations)"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False

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

    def get_all_projects(self, sort_by_usage: bool = True) -> List[Project]:
        """Get all projects, optionally sorted by last usage"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        if sort_by_usage:
            cursor.execute("""
                SELECT * FROM projects
                ORDER BY last_used_at DESC NULLS LAST, name ASC
            """)
        else:
            cursor.execute("SELECT * FROM projects ORDER BY name")

        rows = cursor.fetchall()
        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    def update_project_last_used(self, project_id: str) -> bool:
        """Update the last_used_at timestamp for a project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute("""
                UPDATE projects
                SET last_used_at = ?
                WHERE id = ?
            """, (now, project_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating project last used: {e}")
            return False

    def set_default_project(self, project_id: str) -> bool:
        """Set a project as the default project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            # Unset all defaults
            cursor.execute("UPDATE projects SET is_default = 0")

            # Set the specified project as default
            cursor.execute("UPDATE projects SET is_default = 1 WHERE id = ?", (project_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error setting default project: {e}")
            return False

    def get_default_project(self) -> Optional[Project]:
        """Get the default project"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM projects WHERE is_default = 1 LIMIT 1")
        row = cursor.fetchone()

        db_conn.close()

        if row:
            return Project(**dict(row))
        return None

    # ==================== File Roots ====================

    def add_file_root(self, file_root: FileRoot) -> bool:
        """Add a new file root"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT INTO file_roots
                (id, path, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (file_root.id, file_root.path, file_root.description,
                  file_root.created_at, file_root.updated_at))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding file root: {e}")
            return False

    def update_file_root(self, file_root: FileRoot) -> bool:
        """Update an existing file root"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            file_root.updated_at = datetime.now().isoformat()

            cursor.execute("""
                UPDATE file_roots
                SET path = ?, description = ?, updated_at = ?
                WHERE id = ?
            """, (file_root.path, file_root.description,
                  file_root.updated_at, file_root.id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error updating file root: {e}")
            return False

    def delete_file_root(self, file_root_id: str) -> bool:
        """Delete a file root"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("DELETE FROM file_roots WHERE id = ?", (file_root_id,))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error deleting file root: {e}")
            return False

    def get_all_file_roots(self) -> List[FileRoot]:
        """Get all file roots"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("SELECT * FROM file_roots ORDER BY path")
        rows = cursor.fetchall()

        db_conn.close()

        return [FileRoot(**dict(row)) for row in rows]

    # ==================== Project Associations ====================

    def add_project_database(self, project_id: str, database_id: str) -> bool:
        """Associate a database with a project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO project_databases
                (project_id, database_id, created_at)
                VALUES (?, ?, ?)
            """, (project_id, database_id, datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding project-database association: {e}")
            return False

    def remove_project_database(self, project_id: str, database_id: str) -> bool:
        """Remove database association from a project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM project_databases
                WHERE project_id = ? AND database_id = ?
            """, (project_id, database_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing project-database association: {e}")
            return False

    def get_project_databases(self, project_id: str) -> List[DatabaseConnection]:
        """Get all databases associated with a project"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT dc.* FROM database_connections dc
            INNER JOIN project_databases pd ON dc.id = pd.database_id
            WHERE pd.project_id = ?
            ORDER BY dc.name
        """, (project_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [DatabaseConnection(**dict(row)) for row in rows]

    def get_database_projects(self, database_id: str) -> List[Project]:
        """Get all projects associated with a database"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT p.* FROM projects p
            INNER JOIN project_databases pd ON p.id = pd.project_id
            WHERE pd.database_id = ?
            ORDER BY p.name
        """, (database_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    def add_project_query(self, project_id: str, query_id: str) -> bool:
        """Associate a query with a project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO project_queries
                (project_id, query_id, created_at)
                VALUES (?, ?, ?)
            """, (project_id, query_id, datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding project-query association: {e}")
            return False

    def remove_project_query(self, project_id: str, query_id: str) -> bool:
        """Remove query association from a project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM project_queries
                WHERE project_id = ? AND query_id = ?
            """, (project_id, query_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing project-query association: {e}")
            return False

    def get_project_saved_queries(self, project_id: str) -> List[SavedQuery]:
        """Get all saved queries associated with a project"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT sq.* FROM saved_queries sq
            INNER JOIN project_queries pq ON sq.id = pq.query_id
            WHERE pq.project_id = ?
            ORDER BY sq.category, sq.name
        """, (project_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [SavedQuery(**dict(row)) for row in rows]

    def get_query_projects(self, query_id: str) -> List[Project]:
        """Get all projects associated with a query"""
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

    def add_project_file_root(self, project_id: str, file_root_id: str) -> bool:
        """Associate a file root with a project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO project_file_roots
                (project_id, file_root_id, created_at)
                VALUES (?, ?, ?)
            """, (project_id, file_root_id, datetime.now().isoformat()))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error adding project-file_root association: {e}")
            return False

    def remove_project_file_root(self, project_id: str, file_root_id: str) -> bool:
        """Remove file root association from a project"""
        try:
            db_conn = self._get_connection()
            cursor = db_conn.cursor()

            cursor.execute("""
                DELETE FROM project_file_roots
                WHERE project_id = ? AND file_root_id = ?
            """, (project_id, file_root_id))

            db_conn.commit()
            db_conn.close()
            return True
        except Exception as e:
            print(f"Error removing project-file_root association: {e}")
            return False

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

    def get_file_root_projects(self, file_root_id: str) -> List[Project]:
        """Get all projects associated with a file root"""
        db_conn = self._get_connection()
        cursor = db_conn.cursor()

        cursor.execute("""
            SELECT p.* FROM projects p
            INNER JOIN project_file_roots pfr ON p.id = pfr.project_id
            WHERE pfr.file_root_id = ?
            ORDER BY p.name
        """, (file_root_id,))
        rows = cursor.fetchall()

        db_conn.close()

        return [Project(**dict(row)) for row in rows]

    # ==================== Migration from JSON ====================

    def migrate_from_json(self, json_file_path: Path) -> bool:
        """Migrate connections from old JSON format"""
        try:
            import json

            if not json_file_path.exists():
                return False

            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for conn_data in data:
                conn = DatabaseConnection(
                    id=conn_data.get('id', str(uuid.uuid4())),
                    name=conn_data['name'],
                    db_type=conn_data['db_type'],
                    description=conn_data['description'],
                    connection_string=conn_data['connection_string']
                )
                self.add_database_connection(conn)

            print(f"Migrated {len(data)} connections from JSON")
            return True

        except Exception as e:
            print(f"Error migrating from JSON: {e}")
            return False


# Global configuration database instance
config_db = ConfigDatabase()
