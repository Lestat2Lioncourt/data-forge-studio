"""
Unit tests for ConfigDatabase module
"""
import pytest
import sqlite3
from pathlib import Path
from src.database.config_db import (
    ConfigDatabase, DatabaseConnection, SavedQuery,
    FileConfig, Project, FileRoot
)
from datetime import datetime


class TestDatabaseConnection:
    """Test DatabaseConnection dataclass"""

    def test_initialization_with_id(self):
        """Test creating DatabaseConnection with ID"""
        conn = DatabaseConnection(
            id="test-id",
            name="Test DB",
            db_type="sqlserver",
            description="Test database",
            connection_string="test_connection"
        )
        assert conn.id == "test-id"
        assert conn.name == "Test DB"
        assert conn.created_at is not None
        assert conn.updated_at is not None

    def test_initialization_auto_id(self):
        """Test creating DatabaseConnection with auto-generated ID"""
        conn = DatabaseConnection(
            id="",
            name="Test DB",
            db_type="sqlserver",
            description="Test database",
            connection_string="test_connection"
        )
        assert conn.id != ""
        assert len(conn.id) > 0

    def test_timestamps_auto_generated(self):
        """Test that timestamps are auto-generated"""
        conn = DatabaseConnection(
            id="test-id",
            name="Test DB",
            db_type="sqlserver",
            description="Test database",
            connection_string="test_connection"
        )
        # Parse timestamp to verify it's valid
        created = datetime.fromisoformat(conn.created_at)
        updated = datetime.fromisoformat(conn.updated_at)
        assert created is not None
        assert updated is not None


class TestSavedQuery:
    """Test SavedQuery dataclass"""

    def test_initialization(self):
        """Test creating SavedQuery"""
        query = SavedQuery(
            id="",
            project="Project A",
            category="Analysis",
            name="Sales Report",
            description="Monthly sales report",
            target_database_id="db-123",
            query_text="SELECT * FROM sales"
        )
        assert query.id != ""
        assert query.project == "Project A"
        assert query.category == "Analysis"
        assert query.name == "Sales Report"
        assert query.created_at is not None


class TestFileConfig:
    """Test FileConfig dataclass"""

    def test_initialization(self):
        """Test creating FileConfig"""
        file_cfg = FileConfig(
            id="",
            name="Config File",
            location="/path/to/file",
            description="Test config file"
        )
        assert file_cfg.id != ""
        assert file_cfg.name == "Config File"
        assert file_cfg.location == "/path/to/file"


class TestProject:
    """Test Project dataclass"""

    def test_initialization(self):
        """Test creating Project"""
        project = Project(
            id="",
            name="Analytics Project",
            description="Data analytics project"
        )
        assert project.id != ""
        assert project.name == "Analytics Project"
        assert project.created_at is not None
        assert project.updated_at is not None


class TestFileRoot:
    """Test FileRoot dataclass"""

    def test_initialization(self):
        """Test creating FileRoot"""
        root = FileRoot(
            id="",
            path="/data/root",
            description="Main data root"
        )
        assert root.id != ""
        assert root.path == "/data/root"
        assert root.description == "Main data root"


class TestConfigDatabase:
    """Test ConfigDatabase class"""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary ConfigDatabase for testing"""
        # Monkey-patch the __init__ to use temp path
        original_init = ConfigDatabase.__init__

        def temp_init(self):
            self.db_path = tmp_path / "test_config.db"
            self._ensure_db_folder()
            self._init_database()

        ConfigDatabase.__init__ = temp_init
        db = ConfigDatabase()
        ConfigDatabase.__init__ = original_init
        return db

    def test_database_initialization(self, temp_db):
        """Test database is properly initialized"""
        assert temp_db.db_path.exists()

        # Check tables exist
        conn = temp_db._get_connection()
        cursor = conn.cursor()

        tables = [
            "database_connections",
            "file_configs",
            "saved_queries",
            "projects",
            "file_roots"
        ]

        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            result = cursor.fetchone()
            assert result is not None, f"Table {table} should exist"

        conn.close()

    def test_add_database_connection(self, temp_db):
        """Test adding database connection"""
        conn = DatabaseConnection(
            id="",
            name="Test SQL Server",
            db_type="sqlserver",
            description="Test database connection",
            connection_string="DRIVER={SQL Server};SERVER=localhost;DATABASE=test"
        )

        result = temp_db.add_database_connection(conn)
        assert result is True

        # Verify it was added
        connections = temp_db.get_all_database_connections()
        # Should have at least 2 (self-reference + our test connection)
        assert len(connections) >= 2

        # Find our connection
        test_conn = next((c for c in connections if c.name == "Test SQL Server"), None)
        assert test_conn is not None
        assert test_conn.db_type == "sqlserver"

    def test_get_database_connection_by_id(self, temp_db):
        """Test retrieving database connection by ID"""
        conn = DatabaseConnection(
            id="test-conn-123",
            name="Test DB",
            db_type="sqlite",
            description="Test connection",
            connection_string="test"
        )

        temp_db.add_database_connection(conn)

        retrieved = temp_db.get_database_connection("test-conn-123")
        assert retrieved is not None
        assert retrieved.id == "test-conn-123"
        assert retrieved.name == "Test DB"

    def test_update_database_connection(self, temp_db):
        """Test updating database connection"""
        # Add connection
        conn = DatabaseConnection(
            id="update-test",
            name="Original Name",
            db_type="sqlserver",
            description="Original description",
            connection_string="original"
        )
        temp_db.add_database_connection(conn)

        # Update connection
        conn.name = "Updated Name"
        conn.description = "Updated description"
        result = temp_db.update_database_connection(conn)
        assert result is True

        # Verify update
        retrieved = temp_db.get_database_connection("update-test")
        assert retrieved.name == "Updated Name"
        assert retrieved.description == "Updated description"

    def test_delete_database_connection(self, temp_db):
        """Test deleting database connection"""
        conn = DatabaseConnection(
            id="delete-test",
            name="To Delete",
            db_type="sqlite",
            description="Will be deleted",
            connection_string="test"
        )
        temp_db.add_database_connection(conn)

        # Delete
        result = temp_db.delete_database_connection("delete-test")
        assert result is True

        # Verify deletion
        retrieved = temp_db.get_database_connection("delete-test")
        assert retrieved is None

    def test_add_saved_query(self, temp_db):
        """Test adding saved query"""
        query = SavedQuery(
            id="",
            project="Analytics",
            category="Sales",
            name="Monthly Report",
            description="Monthly sales report",
            target_database_id="config-db-self-ref",
            query_text="SELECT * FROM sales WHERE month = CURRENT_MONTH"
        )

        result = temp_db.add_saved_query(query)
        assert result is True

        # Verify
        queries = temp_db.get_all_saved_queries()
        assert len(queries) > 0

        monthly_query = next((q for q in queries if q.name == "Monthly Report"), None)
        assert monthly_query is not None
        assert monthly_query.category == "Sales"

    def test_get_saved_queries_by_project(self, temp_db):
        """Test getting saved queries filtered by project"""
        # Use config-db-self-ref which exists from initialization
        query1 = SavedQuery(
            id="", project="ProjectA", category="Cat1", name="Query1",
            description="", target_database_id="config-db-self-ref", query_text="SELECT 1"
        )
        query2 = SavedQuery(
            id="", project="ProjectB", category="Cat1", name="Query2",
            description="", target_database_id="config-db-self-ref", query_text="SELECT 2"
        )
        query3 = SavedQuery(
            id="", project="ProjectA", category="Cat2", name="Query3",
            description="", target_database_id="config-db-self-ref", query_text="SELECT 3"
        )

        temp_db.add_saved_query(query1)
        temp_db.add_saved_query(query2)
        temp_db.add_saved_query(query3)

        project_a_queries = [q for q in temp_db.get_all_saved_queries() if q.project == "ProjectA"]
        assert len(project_a_queries) == 2

    def test_delete_saved_query(self, temp_db):
        """Test deleting saved query"""
        query = SavedQuery(
            id="delete-query-test",
            project="Test",
            category="Test",
            name="To Delete",
            description="",
            target_database_id="config-db-self-ref",
            query_text="SELECT 1"
        )
        temp_db.add_saved_query(query)

        # Delete
        result = temp_db.delete_saved_query("delete-query-test")
        assert result is True

        # Verify
        all_queries = temp_db.get_all_saved_queries()
        deleted_query = next((q for q in all_queries if q.id == "delete-query-test"), None)
        assert deleted_query is None

    def test_get_all_database_connections(self, temp_db):
        """Test getting all database connections"""
        connections = temp_db.get_all_database_connections()

        # Should have at least the self-reference connection
        assert len(connections) >= 1

        # Verify self-reference exists
        config_db_conn = next((c for c in connections if c.name == "Configuration Database"), None)
        assert config_db_conn is not None

    def test_get_nonexistent_connection(self, temp_db):
        """Test retrieving non-existent connection returns None"""
        conn = temp_db.get_database_connection("nonexistent-id")
        assert conn is None

    def test_add_file_config(self, temp_db):
        """Test adding file configuration"""
        file_cfg = FileConfig(
            id="",
            name="Data File",
            location="/path/to/data.csv",
            description="Test data file"
        )

        result = temp_db.add_file_config(file_cfg)
        assert result is True

    def test_add_project(self, temp_db):
        """Test adding project"""
        project = Project(
            id="",
            name="Analytics Project",
            description="Data analytics and reporting"
        )

        result = temp_db.add_project(project)
        assert result is True

        # Verify
        projects = temp_db.get_all_projects()
        assert len(projects) > 0

        analytics_project = next((p for p in projects if p.name == "Analytics Project"), None)
        assert analytics_project is not None

    def test_add_file_root(self, temp_db):
        """Test adding file root"""
        root = FileRoot(
            id="",
            path="/data/root/folder",
            description="Main data root directory"
        )

        result = temp_db.add_file_root(root)
        assert result is True

    def test_database_connection_handles_duplicates(self, temp_db):
        """Test that adding duplicate connection is handled"""
        conn = DatabaseConnection(
            id="dup-test",
            name="Duplicate Test",
            db_type="sqlite",
            description="Test",
            connection_string="test"
        )

        # Add first time - should succeed
        result1 = temp_db.add_database_connection(conn)
        assert result1 is True

        # Add again with same ID - should fail or be ignored
        result2 = temp_db.add_database_connection(conn)
        # Behavior depends on implementation - just verify it doesn't crash
        assert isinstance(result2, bool)
