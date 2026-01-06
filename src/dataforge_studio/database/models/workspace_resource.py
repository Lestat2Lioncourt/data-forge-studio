"""
Workspace Resource models - Resources attached to workspaces with their context.

These models wrap base resources (FileRoot, DatabaseConnection, FTPRoot) with workspace-specific
information like subfolder_path or database_name.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .file_root import FileRoot
from .ftp_root import FTPRoot
from .database_connection import DatabaseConnection


@dataclass
class WorkspaceFileRoot:
    """
    A FileRoot attached to a workspace, potentially with a subfolder path.

    When a subfolder is attached (not the root), subfolder_path contains
    the relative path from the FileRoot's root to the attached folder.
    """
    file_root: FileRoot
    subfolder_path: str = ""  # Empty string means root folder

    @property
    def display_name(self) -> str:
        """Name to display in the tree (subfolder name or root name)."""
        if self.subfolder_path:
            return Path(self.subfolder_path).name
        return self.file_root.name or Path(self.file_root.path).name

    @property
    def full_path(self) -> str:
        """Full filesystem path to the attached folder."""
        if self.subfolder_path:
            return str(Path(self.file_root.path) / self.subfolder_path)
        return self.file_root.path

    @property
    def is_subfolder(self) -> bool:
        """True if this is a subfolder attachment, not the root."""
        return bool(self.subfolder_path)


@dataclass
class WorkspaceDatabase:
    """
    A Database attached to a workspace, potentially a specific database on a server.

    When a specific database is attached (not the whole server), database_name
    contains the name of that database.
    """
    connection: DatabaseConnection
    database_name: str = ""  # Empty string means whole server

    @property
    def display_name(self) -> str:
        """Name to display in the tree (database name or server name)."""
        if self.database_name:
            return self.database_name
        return self.connection.name

    @property
    def is_specific_database(self) -> bool:
        """True if this is a specific database, not the whole server."""
        return bool(self.database_name)


@dataclass
class WorkspaceFTPRoot:
    """
    An FTPRoot attached to a workspace, potentially with a remote subfolder path.

    When a subfolder is attached (not the root), subfolder_path contains
    the relative path from the FTPRoot's initial_path to the attached folder.
    """
    ftp_root: FTPRoot
    subfolder_path: str = ""  # Empty string means initial_path

    @property
    def display_name(self) -> str:
        """Name to display in the tree (subfolder name or root name)."""
        if self.subfolder_path:
            # Get last component of remote path
            parts = self.subfolder_path.rstrip("/").split("/")
            return parts[-1] if parts else self.ftp_root.name
        return self.ftp_root.name

    @property
    def full_remote_path(self) -> str:
        """Full remote path to the attached folder."""
        base_path = self.ftp_root.initial_path.rstrip("/")
        if self.subfolder_path:
            return f"{base_path}/{self.subfolder_path.lstrip('/')}"
        return base_path or "/"

    @property
    def is_subfolder(self) -> bool:
        """True if this is a subfolder attachment, not the root."""
        return bool(self.subfolder_path)
