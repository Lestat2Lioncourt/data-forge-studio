"""
Pytest configuration and fixtures for DataForge Studio tests.
"""
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
import tempfile
import shutil


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test_config.db"
    yield db_path
    # Cleanup is automatic with tmp_path


@pytest.fixture
def temp_app_config(tmp_path):
    """Create a temporary _AppConfig directory for testing."""
    config_dir = tmp_path / "_AppConfig"
    config_dir.mkdir(exist_ok=True)
    yield config_dir


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the test data directory."""
    return Path(__file__).parent / "test_data"
