"""
Unit tests for Tree Item Builders.
Tests display name generation for database connections, root folders,
queries, scripts, and jobs.
"""
import pytest
from types import SimpleNamespace

from dataforge_studio.ui.utils.tree_item_builders import (
    get_database_display_name,
    get_rootfolder_display_name,
    get_query_display_name,
    get_script_display_name,
    get_job_display_name,
)


class TestGetDatabaseDisplayName:
    """Tests for get_database_display_name()."""

    def test_returns_connection_name(self):
        """Display name is the connection name."""
        conn = SimpleNamespace(name="Production DB")
        assert get_database_display_name(conn) == "Production DB"

    def test_empty_name(self):
        """Display name handles empty string."""
        conn = SimpleNamespace(name="")
        assert get_database_display_name(conn) == ""

    def test_special_characters(self):
        """Display name preserves special characters."""
        conn = SimpleNamespace(name="Server [DEV] (192.168.1.1)")
        assert get_database_display_name(conn) == "Server [DEV] (192.168.1.1)"


class TestGetRootfolderDisplayName:
    """Tests for get_rootfolder_display_name()."""

    def test_returns_folder_name(self):
        """Display name is the folder name when set."""
        folder = SimpleNamespace(name="My Folder", path="/some/path")
        assert get_rootfolder_display_name(folder) == "My Folder"

    def test_falls_back_to_path(self):
        """Display name falls back to path when name is empty/falsy."""
        folder = SimpleNamespace(name="", path="/some/path")
        assert get_rootfolder_display_name(folder) == "/some/path"

    def test_none_name_falls_back_to_path(self):
        """Display name falls back to path when name is None."""
        folder = SimpleNamespace(name=None, path="C:\\Data")
        assert get_rootfolder_display_name(folder) == "C:\\Data"


class TestGetQueryDisplayName:
    """Tests for get_query_display_name()."""

    def test_returns_query_name(self):
        """Display name is the query name."""
        query = SimpleNamespace(name="Active Users")
        assert get_query_display_name(query) == "Active Users"

    def test_empty_name(self):
        """Display name handles empty string."""
        query = SimpleNamespace(name="")
        assert get_query_display_name(query) == ""


class TestGetScriptDisplayName:
    """Tests for get_script_display_name()."""

    def test_returns_script_name(self):
        """Display name is the script name."""
        script = SimpleNamespace(name="deploy_v2.sql")
        assert get_script_display_name(script) == "deploy_v2.sql"

    def test_empty_name(self):
        """Display name handles empty string."""
        script = SimpleNamespace(name="")
        assert get_script_display_name(script) == ""


class TestGetJobDisplayName:
    """Tests for get_job_display_name()."""

    def test_enabled_job(self):
        """Enabled job shows checkmark prefix."""
        job = SimpleNamespace(name="Nightly Backup", enabled=True)
        result = get_job_display_name(job)
        assert result == "\u2713 Nightly Backup"
        assert result.startswith("\u2713")

    def test_disabled_job(self):
        """Disabled job shows cross prefix."""
        job = SimpleNamespace(name="Nightly Backup", enabled=False)
        result = get_job_display_name(job)
        assert result == "\u2717 Nightly Backup"
        assert result.startswith("\u2717")

    def test_enabled_contains_name(self):
        """Job display name contains the job name."""
        job = SimpleNamespace(name="ETL Process", enabled=True)
        assert "ETL Process" in get_job_display_name(job)

    def test_disabled_contains_name(self):
        """Disabled job display name contains the job name."""
        job = SimpleNamespace(name="ETL Process", enabled=False)
        assert "ETL Process" in get_job_display_name(job)
