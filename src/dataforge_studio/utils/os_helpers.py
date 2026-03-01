"""
OS helpers — cross-platform file/folder operations.
"""

import logging
import os
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def reveal_in_explorer(file_path: Path) -> None:
    """Open the system file explorer and select/highlight the given file."""
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", str(file_path)])
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", str(file_path)])
        else:
            subprocess.run(["xdg-open", str(file_path.parent)])
    except Exception as e:
        logger.error(f"Error opening file location: {e}")


def open_in_explorer(path: Path) -> None:
    """Open a folder (or file with default app) in the system explorer."""
    try:
        if platform.system() == "Windows":
            subprocess.run(["explorer", str(path)])
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])
    except Exception as e:
        logger.error(f"Error opening location: {e}")


def open_file_with_default_app(file_path: Path) -> None:
    """Open a file with the system's default application."""
    try:
        if platform.system() == "Windows":
            os.startfile(str(file_path))
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(file_path)])
        else:
            subprocess.run(["xdg-open", str(file_path)])
    except Exception as e:
        logger.error(f"Error opening file: {e}")
