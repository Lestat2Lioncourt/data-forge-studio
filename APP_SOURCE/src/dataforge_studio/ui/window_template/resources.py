"""Resource management for loading embedded icons and assets."""

from pathlib import Path
from typing import Optional


def get_icon_path(icon_name: str) -> Optional[str]:
    """
    Get the absolute path to an embedded icon.

    Args:
        icon_name: Name of the icon file (e.g., "close.png")

    Returns:
        Absolute path to the icon file, or None if not found
    """
    icons_dir = Path(__file__).parent / "icons"
    icon_path = icons_dir / icon_name

    if icon_path.exists():
        return str(icon_path)

    return None


def get_resource_path(resource_name: str, subdir: str = "") -> Optional[str]:
    """
    Get the absolute path to an embedded resource.

    Args:
        resource_name: Name of the resource file
        subdir: Optional subdirectory within the package

    Returns:
        Absolute path to the resource file, or None if not found
    """
    package_dir = Path(__file__).parent

    if subdir:
        resource_path = package_dir / subdir / resource_name
    else:
        resource_path = package_dir / resource_name

    if resource_path.exists():
        return str(resource_path)

    return None
