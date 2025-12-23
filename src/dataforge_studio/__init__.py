"""
DataForge Studio - Multi-database management tool
PySide6 Edition
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("data-forge-studio")
except PackageNotFoundError:
    # Package not installed, fallback to reading pyproject.toml directly
    __version__ = "0.5.7"  # Fallback version

__author__ = "Lestat2Lioncourt"

from .main import main

__all__ = ["main", "__version__"]
