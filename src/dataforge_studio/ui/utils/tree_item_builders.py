"""
Tree Item Builders - Centralized display logic for resource tree items.

Provides consistent icon and display name generation for all resource types.
All consumers (ResourcesManager, WorkspaceManager, specialized managers)
should use these functions instead of building display logic inline.
"""

from typing import Optional
from PySide6.QtGui import QIcon

from ...utils.image_loader import (
    get_icon, get_database_icon_with_dot, get_auto_color
)

import logging
logger = logging.getLogger(__name__)


def get_database_display_icon(db_connection, index: int = 0) -> Optional[QIcon]:
    """Get display icon for a database connection (DB type logo + color dot)."""
    color = db_connection.color or get_auto_color(index)
    return get_database_icon_with_dot(db_connection.db_type, color)


def get_database_display_name(db_connection) -> str:
    """Get display name for a database connection."""
    return db_connection.name


def get_rootfolder_display_icon() -> Optional[QIcon]:
    """Get display icon for a root folder."""
    return get_icon("RootFolders", size=16)


def get_rootfolder_display_name(root_folder) -> str:
    """Get display name for a root folder."""
    return root_folder.name or root_folder.path


def get_query_display_icon() -> Optional[QIcon]:
    """Get display icon for a saved query."""
    return get_icon("query", size=16)


def get_query_display_name(query) -> str:
    """Get display name for a saved query."""
    return query.name


def get_script_display_icon() -> Optional[QIcon]:
    """Get display icon for a script."""
    return get_icon("script", size=16)


def get_script_display_name(script) -> str:
    """Get display name for a script."""
    return script.name


def get_job_display_icon() -> Optional[QIcon]:
    """Get display icon for a job."""
    return get_icon("jobs", size=16)


def get_job_display_name(job) -> str:
    """Get display name for a job (includes enabled status indicator)."""
    status = "\u2713" if job.enabled else "\u2717"
    return f"{status} {job.name}"


def get_category_display_icon() -> Optional[QIcon]:
    """Get display icon for a category/folder grouping."""
    return get_icon("folder", size=16)
