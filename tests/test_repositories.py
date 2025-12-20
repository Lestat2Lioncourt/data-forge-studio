"""
Unit tests for the repository pattern implementation.
Tests the new modular database access layer.
"""
import pytest
import tempfile
from pathlib import Path

from dataforge_studio.database.connection_pool import ConnectionPool
from dataforge_studio.database.schema_manager import SchemaManager
from dataforge_studio.database.repositories import (
    DatabaseConnectionRepository,
    SavedQueryRepository,
    ProjectRepository,
    FileRootRepository,
    ScriptRepository,
    JobRepository,
    UserPreferencesRepository,
)
from dataforge_studio.database.models import (
    DatabaseConnection,
    SavedQuery,
    Project,
    FileRoot,
    Script,
    Job,
)


class TestConnectionPool:
    """Test ConnectionPool functionality."""

    @pytest.fixture
    def pool(self, tmp_path):
        """Create a connection pool with temporary database."""
        db_path = tmp_path / "test.db"
        pool = ConnectionPool(db_path, max_connections=3)
        # Initialize schema
        schema = SchemaManager(db_path)
        schema.initialize()
        yield pool
        pool.close_all()

    def test_get_connection(self, pool):
        """Test getting a connection from the pool."""
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_connection_reuse(self, pool):
        """Test that connections are reused."""
        # Get and return a connection
        with pool.get_connection() as conn1:
            id1 = id(conn1)

        # Get another connection - should be the same one
        with pool.get_connection() as conn2:
            id2 = id(conn2)

        assert id1 == id2

    def test_transaction_commit(self, pool):
        """Test transaction with commit."""
        with pool.transaction() as conn:
            conn.execute("""
                INSERT INTO user_preferences (key, value, updated_at)
                VALUES ('test_key', 'test_value', datetime('now'))
            """)

        # Verify data was committed
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = 'test_key'")
            result = cursor.fetchone()
            assert result[0] == 'test_value'

    def test_transaction_rollback(self, pool):
        """Test transaction rollback on exception."""
        try:
            with pool.transaction() as conn:
                conn.execute("""
                    INSERT INTO user_preferences (key, value, updated_at)
                    VALUES ('rollback_key', 'value', datetime('now'))
                """)
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify data was not committed
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = 'rollback_key'")
            result = cursor.fetchone()
            assert result is None


class TestDatabaseConnectionRepository:
    """Test DatabaseConnectionRepository."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Create repository with test database."""
        db_path = tmp_path / "test.db"
        pool = ConnectionPool(db_path)
        schema = SchemaManager(db_path)
        schema.initialize()
        return DatabaseConnectionRepository(pool)

    def test_add_and_get(self, repo):
        """Test adding and retrieving a connection."""
        conn = DatabaseConnection(
            id="test-conn-1",
            name="Test Connection",
            db_type="sqlserver",
            connection_string="Server=test;Database=db",
            description="Test description"
        )

        result = repo.add(conn)
        assert result is True

        retrieved = repo.get_by_id("test-conn-1")
        assert retrieved is not None
        assert retrieved.name == "Test Connection"
        assert retrieved.db_type == "sqlserver"

    def test_update(self, repo):
        """Test updating a connection."""
        conn = DatabaseConnection(
            id="test-conn-2",
            name="Original Name",
            db_type="sqlite",
            connection_string="test.db",
            description="Test"
        )
        repo.add(conn)

        conn.name = "Updated Name"
        result = repo.update(conn)
        assert result is True

        retrieved = repo.get_by_id("test-conn-2")
        assert retrieved.name == "Updated Name"

    def test_delete(self, repo):
        """Test deleting a connection."""
        conn = DatabaseConnection(
            id="test-conn-3",
            name="To Delete",
            db_type="sqlite",
            connection_string="test.db",
            description="To be deleted"
        )
        repo.add(conn)

        result = repo.delete("test-conn-3")
        assert result is True

        retrieved = repo.get_by_id("test-conn-3")
        assert retrieved is None

    def test_get_business_connections(self, repo):
        """Test getting business connections (excluding config db)."""
        # Add a business connection
        conn = DatabaseConnection(
            id="business-conn",
            name="Business DB",
            db_type="sqlserver",
            connection_string="Server=prod",
            description="Production database"
        )
        repo.add(conn)

        connections = repo.get_business_connections()
        # Should not include config-db-self-ref
        config_ids = [c.id for c in connections]
        assert DatabaseConnectionRepository.CONFIG_DB_ID not in config_ids
        assert "business-conn" in config_ids


class TestSavedQueryRepository:
    """Test SavedQueryRepository."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Create repository with test database."""
        db_path = tmp_path / "test.db"
        pool = ConnectionPool(db_path)
        schema = SchemaManager(db_path)
        schema.initialize()

        # Add a database connection for FK
        conn_repo = DatabaseConnectionRepository(pool)
        conn = DatabaseConnection(
            id="test-db",
            name="Test DB",
            db_type="sqlite",
            connection_string="test.db",
            description="Test database"
        )
        conn_repo.add(conn)

        return SavedQueryRepository(pool)

    def test_add_and_get_query(self, repo):
        """Test adding and retrieving a query."""
        query = SavedQuery(
            id="query-1",
            name="Test Query",
            target_database_id="test-db",
            query_text="SELECT * FROM test",
            category="Reports",
            description="A test query"
        )

        result = repo.add(query)
        assert result is True

        retrieved = repo.get_by_id("query-1")
        assert retrieved is not None
        assert retrieved.name == "Test Query"
        assert retrieved.category == "Reports"

    def test_get_queries_by_category(self, repo):
        """Test getting queries by category."""
        query1 = SavedQuery(
            id="q1",
            name="Query 1",
            target_database_id="test-db",
            query_text="SELECT 1",
            category="Reports"
        )
        query2 = SavedQuery(
            id="q2",
            name="Query 2",
            target_database_id="test-db",
            query_text="SELECT 2",
            category="Admin"
        )
        repo.add(query1)
        repo.add(query2)

        reports = repo.get_queries_by_category("Reports")
        assert len(reports) == 1
        assert reports[0].id == "q1"


class TestProjectRepository:
    """Test ProjectRepository."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Create repository with test database."""
        db_path = tmp_path / "test.db"
        pool = ConnectionPool(db_path)
        schema = SchemaManager(db_path)
        schema.initialize()
        return ProjectRepository(pool)

    def test_add_and_get_project(self, repo):
        """Test adding and retrieving a project."""
        project = Project(
            id="proj-1",
            name="Test Project",
            description="A test project",
            is_default=False
        )

        result = repo.add(project)
        assert result is True

        retrieved = repo.get_by_id("proj-1")
        assert retrieved is not None
        assert retrieved.name == "Test Project"

    def test_touch_workspace(self, repo):
        """Test updating last_used_at timestamp."""
        project = Project(
            id="proj-2",
            name="Workspace",
            description="Test workspace",
            is_default=False
        )
        repo.add(project)

        original = repo.get_by_id("proj-2")
        original_time = original.last_used_at

        result = repo.touch("proj-2")
        assert result is True

        updated = repo.get_by_id("proj-2")
        # last_used_at should be updated
        assert updated.last_used_at != original_time


class TestUserPreferencesRepository:
    """Test UserPreferencesRepository."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Create repository with test database."""
        db_path = tmp_path / "test.db"
        pool = ConnectionPool(db_path)
        schema = SchemaManager(db_path)
        schema.initialize()
        return UserPreferencesRepository(pool)

    def test_set_and_get(self, repo):
        """Test setting and getting a preference."""
        result = repo.set("theme", "dark")
        assert result is True

        value = repo.get("theme")
        assert value == "dark"

    def test_get_with_default(self, repo):
        """Test getting a non-existent preference with default."""
        value = repo.get("nonexistent", "default_value")
        assert value == "default_value"

    def test_get_all(self, repo):
        """Test getting all preferences."""
        repo.set("key1", "value1")
        repo.set("key2", "value2")

        prefs = repo.get_all()
        assert "key1" in prefs
        assert "key2" in prefs
        assert prefs["key1"] == "value1"

    def test_delete(self, repo):
        """Test deleting a preference."""
        repo.set("to_delete", "value")

        result = repo.delete("to_delete")
        assert result is True

        value = repo.get("to_delete")
        assert value is None
