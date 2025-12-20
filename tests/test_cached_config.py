"""
Unit tests for CachedConfigDB.
Tests caching behavior, invalidation, and thread safety.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from dataforge_studio.database.cached_config import (
    CachedConfigDB,
    get_cached_config_db,
    invalidate_config_cache,
)
from dataforge_studio.database.models import (
    DatabaseConnection,
    SavedQuery,
    Project,
    FileRoot,
)


class TestCachedConfigDB:
    """Test CachedConfigDB caching behavior."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock ConfigDatabase."""
        mock = Mock()
        # Setup return values for common methods
        mock.get_all_database_connections.return_value = [
            DatabaseConnection(
                id="db1", name="Test DB", db_type="sqlite",
                connection_string="test.db", description="Test"
            )
        ]
        mock.get_all_saved_queries.return_value = []
        mock.get_all_projects.return_value = []
        mock.get_all_workspaces.return_value = []
        mock.get_all_file_roots.return_value = []
        mock.get_all_scripts.return_value = []
        mock.get_all_jobs.return_value = []
        mock.get_workspace_databases.return_value = []
        mock.get_workspace_queries.return_value = []
        return mock

    @pytest.fixture
    def cached_db(self, mock_db):
        """Create CachedConfigDB with mock."""
        return CachedConfigDB(config_db=mock_db, ttl=10, maxsize=50)

    def test_caches_database_connections(self, cached_db, mock_db):
        """Test that database connections are cached."""
        # First call - should hit the database
        result1 = cached_db.get_all_database_connections()
        assert len(result1) == 1
        assert mock_db.get_all_database_connections.call_count == 1

        # Second call - should use cache
        result2 = cached_db.get_all_database_connections()
        assert len(result2) == 1
        assert mock_db.get_all_database_connections.call_count == 1  # Still 1

    def test_caches_workspace_databases(self, cached_db, mock_db):
        """Test that workspace databases are cached per workspace."""
        # Call for workspace "ws1"
        cached_db.get_workspace_databases("ws1")
        cached_db.get_workspace_databases("ws1")
        assert mock_db.get_workspace_databases.call_count == 1

        # Call for different workspace "ws2" - should call again
        cached_db.get_workspace_databases("ws2")
        assert mock_db.get_workspace_databases.call_count == 2

        # Call for "ws1" again - should use cache
        cached_db.get_workspace_databases("ws1")
        assert mock_db.get_workspace_databases.call_count == 2

    def test_invalidates_on_add(self, cached_db, mock_db):
        """Test that cache is invalidated when adding."""
        mock_db.add_database_connection.return_value = True

        # Prime the cache
        cached_db.get_all_database_connections()
        assert mock_db.get_all_database_connections.call_count == 1

        # Add a connection
        conn = DatabaseConnection(
            id="new", name="New DB", db_type="sqlite",
            connection_string="new.db", description="New"
        )
        cached_db.add_database_connection(conn)

        # Cache should be invalidated - next call hits DB
        cached_db.get_all_database_connections()
        assert mock_db.get_all_database_connections.call_count == 2

    def test_invalidates_on_update(self, cached_db, mock_db):
        """Test that cache is invalidated when updating."""
        mock_db.update_database_connection.return_value = True

        # Prime the cache
        cached_db.get_all_database_connections()
        assert mock_db.get_all_database_connections.call_count == 1

        # Update a connection
        conn = DatabaseConnection(
            id="db1", name="Updated DB", db_type="sqlite",
            connection_string="test.db", description="Updated"
        )
        cached_db.update_database_connection(conn)

        # Cache should be invalidated
        cached_db.get_all_database_connections()
        assert mock_db.get_all_database_connections.call_count == 2

    def test_invalidates_on_delete(self, cached_db, mock_db):
        """Test that cache is invalidated when deleting."""
        mock_db.delete_database_connection.return_value = True

        # Prime the cache
        cached_db.get_all_database_connections()
        assert mock_db.get_all_database_connections.call_count == 1

        # Delete a connection
        cached_db.delete_database_connection("db1")

        # Cache should be invalidated
        cached_db.get_all_database_connections()
        assert mock_db.get_all_database_connections.call_count == 2

    def test_invalidate_all(self, cached_db, mock_db):
        """Test invalidating entire cache."""
        # Prime multiple caches
        cached_db.get_all_database_connections()
        cached_db.get_all_saved_queries()
        cached_db.get_all_projects()

        # Invalidate all
        cached_db.invalidate_all()

        # All should be refetched
        cached_db.get_all_database_connections()
        cached_db.get_all_saved_queries()
        cached_db.get_all_projects()

        assert mock_db.get_all_database_connections.call_count == 2
        assert mock_db.get_all_saved_queries.call_count == 2
        assert mock_db.get_all_projects.call_count == 2

    def test_invalidate_with_prefix(self, cached_db, mock_db):
        """Test invalidating cache by prefix."""
        # Prime caches
        cached_db.get_all_database_connections()
        cached_db.get_all_saved_queries()

        # Invalidate only database-related
        cached_db.invalidate("get_all_database")

        # Only database should be refetched
        cached_db.get_all_database_connections()
        cached_db.get_all_saved_queries()

        assert mock_db.get_all_database_connections.call_count == 2
        assert mock_db.get_all_saved_queries.call_count == 1  # Still cached

    def test_cache_info(self, cached_db, mock_db):
        """Test cache info property."""
        cached_db.get_all_database_connections()
        cached_db.get_all_saved_queries()

        info = cached_db.cache_info
        assert info["size"] == 2
        assert info["maxsize"] == 50
        assert info["ttl"] == 10
        assert len(info["keys"]) == 2

    def test_passthrough_unknown_methods(self, cached_db, mock_db):
        """Test that unknown methods are passed to underlying DB."""
        mock_db.some_other_method.return_value = "result"

        result = cached_db.some_other_method("arg1", "arg2")

        assert result == "result"
        mock_db.some_other_method.assert_called_once_with("arg1", "arg2")

    def test_no_invalidation_on_failed_add(self, cached_db, mock_db):
        """Test that cache is not invalidated when add fails."""
        mock_db.add_database_connection.return_value = False

        # Prime the cache
        cached_db.get_all_database_connections()

        # Attempt to add (fails)
        conn = DatabaseConnection(
            id="new", name="New DB", db_type="sqlite",
            connection_string="new.db", description="New"
        )
        cached_db.add_database_connection(conn)

        # Cache should NOT be invalidated
        cached_db.get_all_database_connections()
        assert mock_db.get_all_database_connections.call_count == 1  # Still 1


class TestCachedConfigDBQueries:
    """Test caching for saved queries."""

    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.get_all_saved_queries.return_value = [
            SavedQuery(
                id="q1", name="Query 1", query_text="SELECT 1",
                target_database_id="db1", category="Test"
            )
        ]
        mock.get_workspace_queries.return_value = []
        mock.add_saved_query.return_value = True
        mock.update_saved_query.return_value = True
        mock.delete_saved_query.return_value = True
        return mock

    @pytest.fixture
    def cached_db(self, mock_db):
        return CachedConfigDB(config_db=mock_db, ttl=10)

    def test_caches_queries(self, cached_db, mock_db):
        """Test query caching."""
        cached_db.get_all_saved_queries()
        cached_db.get_all_saved_queries()
        assert mock_db.get_all_saved_queries.call_count == 1

    def test_invalidates_on_query_add(self, cached_db, mock_db):
        """Test cache invalidation on query add."""
        cached_db.get_all_saved_queries()

        query = SavedQuery(
            id="q2", name="Query 2", query_text="SELECT 2",
            target_database_id="db1", category="Test"
        )
        cached_db.add_saved_query(query)

        cached_db.get_all_saved_queries()
        assert mock_db.get_all_saved_queries.call_count == 2


class TestCachedConfigDBProjects:
    """Test caching for projects/workspaces."""

    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.get_all_projects.return_value = [
            Project(id="p1", name="Project 1", description="Test")
        ]
        mock.get_all_workspaces.return_value = []
        mock.add_project.return_value = True
        return mock

    @pytest.fixture
    def cached_db(self, mock_db):
        return CachedConfigDB(config_db=mock_db, ttl=10)

    def test_caches_projects(self, cached_db, mock_db):
        """Test project caching."""
        cached_db.get_all_projects()
        cached_db.get_all_projects()
        assert mock_db.get_all_projects.call_count == 1

    def test_different_sort_creates_different_cache(self, cached_db, mock_db):
        """Test that different sort options use different cache entries."""
        cached_db.get_all_projects(sort_by_usage=True)
        cached_db.get_all_projects(sort_by_usage=False)
        assert mock_db.get_all_projects.call_count == 2


class TestSingletonCachedConfigDB:
    """Test singleton behavior."""

    def test_singleton_returns_same_instance(self):
        """Test that get_cached_config_db returns singleton."""
        db1 = get_cached_config_db()
        db2 = get_cached_config_db()
        assert db1 is db2

    def test_invalidate_config_cache_function(self):
        """Test convenience invalidation function."""
        # Should not raise even if singleton not initialized
        invalidate_config_cache("test_prefix")
        invalidate_config_cache()  # Clear all
