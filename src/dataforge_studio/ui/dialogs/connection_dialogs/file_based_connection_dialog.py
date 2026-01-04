"""
File-Based Connection Dialog - Base class for SQLite and Access databases
"""

from abc import abstractmethod
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QPushButton, QFileDialog, QGroupBox,
                               QLabel)
from PySide6.QtCore import Qt

from .base_connection_dialog import BaseConnectionDialog
from ....database.config_db import DatabaseConnection

import logging
logger = logging.getLogger(__name__)


class FileBasedConnectionDialog(BaseConnectionDialog):
    """
    Base class for file-based database connection dialogs (SQLite, Access).

    Features:
    - File selector with browse button
    - Create New Database button
    - Optional password field (for Access)
    """

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _setup_connection_fields(self):
        """Setup file-based connection fields"""

        # File selection group
        file_group = QGroupBox("Database File")
        file_layout = QVBoxLayout(file_group)

        # File path with browse button
        path_layout = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText(f"Select or create a {self._get_file_extension()} file")
        self.file_path_edit.setReadOnly(True)
        path_layout.addWidget(self.file_path_edit)

        browse_btn = QPushButton("📁 Browse")
        browse_btn.clicked.connect(self._browse_file)
        path_layout.addWidget(browse_btn)

        file_layout.addLayout(path_layout)

        # Create new database button
        create_btn = QPushButton(f"+ Create New {self._get_db_type().upper()} Database")
        create_btn.clicked.connect(self._create_new_database)
        file_layout.addWidget(create_btn)

        self.connection_fields_layout.addWidget(file_group)

        # Optional password field (for Access)
        if self._supports_password():
            self._setup_password_field()

    def _browse_file(self):
        """Open file browser to select database file"""
        file_filter = self._get_file_filter()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {self._get_db_type().upper()} Database",
            str(Path.home()),
            file_filter
        )

        if file_path:
            self.file_path_edit.setText(file_path)

    def _create_new_database(self):
        """Create a new database file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Create New {self._get_db_type().upper()} Database",
            str(Path.home()),
            f"{self._get_db_type().upper()} Files (*{self._get_file_extension()})"
        )

        if file_path:
            # Ensure correct extension
            if not file_path.endswith(self._get_file_extension()):
                file_path += self._get_file_extension()

            try:
                # Create the database file
                self._create_database_file(file_path)
                self.file_path_edit.setText(file_path)

                from ...widgets.dialog_helper import DialogHelper
                DialogHelper.info(f"Database created successfully!\n\n{file_path}", parent=self)

            except Exception as e:
                logger.error(f"Error creating database: {e}")
                from ...widgets.dialog_helper import DialogHelper
                DialogHelper.error("Error creating database", parent=self, details=str(e))

    @abstractmethod
    def _get_file_extension(self) -> str:
        """
        Get file extension for this database type.

        Returns:
            File extension (e.g., ".db", ".accdb")
        """
        pass

    def _get_file_filter(self) -> str:
        """
        Get file filter for file dialogs.
        Can be overridden to support multiple extensions.

        Returns:
            File filter string (e.g., "DB Files (*.db);;All Files (*.*)")
        """
        ext = self._get_file_extension()
        db_type = self._get_db_type().upper()
        return f"{db_type} Files (*{ext});;All Files (*.*)"

    @abstractmethod
    def _create_database_file(self, file_path: str):
        """
        Create a new database file.

        Args:
            file_path: Path where to create the database file
        """
        pass

    def _supports_password(self) -> bool:
        """
        Whether this database type supports password protection.

        Returns:
            True if password is supported (Access), False otherwise (SQLite)
        """
        return False

    def _setup_password_field(self):
        """Setup optional password field (for Access)"""
        # Override in subclass if needed
        pass

    def _build_connection_string(self, username: str = "", password: str = "") -> str:
        """Build file-based connection string"""
        file_path = self.file_path_edit.text().strip()

        if not file_path:
            return ""

        # Subclasses will implement the specific connection string format
        return self._build_file_connection_string(file_path, password)

    @abstractmethod
    def _build_file_connection_string(self, file_path: str, password: str = "") -> str:
        """
        Build connection string for file-based database.

        Args:
            file_path: Path to database file
            password: Optional password

        Returns:
            Connection string
        """
        pass

    def _get_credentials(self) -> tuple[str, str, bool]:
        """Get credentials (file-based databases typically don't need username)"""
        # Override in subclass if password is supported
        return ("", "", False)

    def _load_existing_connection(self):
        """Load existing connection into fields"""
        super()._load_existing_connection()

        if not self.connection:
            return

        # Extract file path from connection string
        file_path = self._extract_file_path(self.connection.connection_string)
        if file_path:
            self.file_path_edit.setText(file_path)

    @abstractmethod
    def _extract_file_path(self, connection_string: str) -> str:
        """
        Extract file path from connection string.

        Args:
            connection_string: Connection string

        Returns:
            File path
        """
        pass
