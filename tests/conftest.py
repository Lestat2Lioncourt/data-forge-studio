"""
Pytest configuration and fixtures for DataForge Studio tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path

# Qt Application fixture for tests that need QWidget
_qt_app = None


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for tests that need Qt widgets."""
    global _qt_app
    from PySide6.QtWidgets import QApplication
    if _qt_app is None:
        _qt_app = QApplication.instance() or QApplication([])
    yield _qt_app


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
