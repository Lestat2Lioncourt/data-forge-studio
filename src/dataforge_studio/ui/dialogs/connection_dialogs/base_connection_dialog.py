"""
Base Connection Dialog - Abstract base class for all database connection dialogs
"""

from abc import ABCMeta, abstractmethod
from typing import Optional
import uuid

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QPushButton, QDialogButtonBox,
                               QGroupBox, QMessageBox)
from PySide6.QtCore import Qt

from ....database.config_db import get_config_db, DatabaseConnection
from ....utils.credential_manager import CredentialManager
from ....utils.network_utils import check_server_reachable
from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr

import logging
logger = logging.getLogger(__name__)


# Create a combined metaclass for QDialog and ABC
class QDialogABCMeta(type(QDialog), ABCMeta):
    """Combined metaclass for QDialog and ABC"""
    pass


class BaseConnectionDialog(QDialog, metaclass=QDialogABCMeta):
    """
    Abstract base class for database connection dialogs.

    Handles:
    - Alias and description fields
    - Test connection button
    - Save/Cancel buttons
    - Credential management

    Subclasses must implement:
    - _setup_connection_fields(): Create database-specific fields
    - _build_connection_string(): Build connection string from fields
    - _test_connection(): Test the connection
    """

    def __init__(self, parent: Optional[QDialog] = None, connection: Optional[DatabaseConnection] = None):
        """
        Initialize base connection dialog.

        Args:
            parent: Parent widget
            connection: Existing connection to edit (None for new connection)
        """
        super().__init__(parent)

        self.connection = connection
        self.is_editing = connection is not None
        self.config_db = get_config_db()

        # Generate or use existing ID
        self.connection_id = connection.id if connection else str(uuid.uuid4())

        self.setWindowTitle(tr("conn_edit_title") if self.is_editing else tr("conn_new_title"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._setup_ui()
        self._load_existing_connection()

    def _setup_ui(self):
        """Setup base UI structure"""
        layout = QVBoxLayout(self)

        # Connection-specific fields (implemented by subclasses)
        self.connection_fields_layout = QVBoxLayout()
        self._setup_connection_fields()
        layout.addLayout(self.connection_fields_layout)

        # Common fields group
        common_group = QGroupBox(tr("conn_general_info"))
        common_layout = QFormLayout(common_group)

        # Alias field
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText(tr("conn_alias_placeholder"))
        common_layout.addRow(tr("conn_alias_label"), self.alias_edit)

        # Description field
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(tr("conn_description_placeholder"))
        self.description_edit.setMaximumHeight(80)
        common_layout.addRow(tr("conn_description_label"), self.description_edit)

        layout.addWidget(common_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.test_button = QPushButton("🔌 " + tr("conn_test_button"))
        self.test_button.clicked.connect(self._on_test_connection)
        button_layout.addWidget(self.test_button)

        button_layout.addStretch()

        # Standard buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

    @abstractmethod
    def _setup_connection_fields(self):
        """
        Setup database-specific connection fields.

        Must be implemented by subclasses to create their specific UI fields.
        """
        pass

    @abstractmethod
    def _build_connection_string(self, username: str = "", password: str = "") -> str:
        """
        Build connection string from UI fields.

        Args:
            username: Username (for testing only, not stored in connection string)
            password: Password (for testing only, not stored in connection string)

        Returns:
            Connection string

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def _test_connection(self, connection_string: str) -> tuple[bool, str]:
        """
        Test database connection.

        Args:
            connection_string: Complete connection string (with credentials)

        Returns:
            Tuple of (success: bool, message: str)

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def _get_db_type(self) -> str:
        """
        Get database type identifier.

        Returns:
            Database type (e.g., "sqlserver", "mysql", "postgresql")

        Must be implemented by subclasses.
        """
        pass

    def _load_existing_connection(self):
        """Load existing connection data into fields"""
        if not self.connection:
            return

        # Load common fields
        self.alias_edit.setText(self.connection.name or "")
        self.description_edit.setPlainText(self.connection.description or "")

        # Subclasses should override this to load their specific fields

    def _on_test_connection(self):
        """Handle test connection button click"""
        try:
            # Get credentials (subclasses will provide these)
            username, password, _ = self._get_credentials()

            # Build connection string with credentials
            connection_string = self._build_connection_string(username, password)

            if not connection_string:
                DialogHelper.warning(tr("conn_fill_required"), parent=self)
                return

            # First, ping the server to check if it's reachable
            reachable, vpn_message = check_server_reachable(
                connection_string,
                db_type=self._get_db_type(),
                timeout=3
            )

            if not reachable:
                DialogHelper.error("❌ " + tr("conn_server_unreachable") + f"\n\n{vpn_message}", parent=self)
                return

            # Test connection
            success, message = self._test_connection(connection_string)

            if success:
                DialogHelper.info("✅ " + tr("conn_success") + f"\n\n{message}", parent=self)
            else:
                DialogHelper.error("❌ " + tr("conn_failed") + f"\n\n{message}", parent=self)

        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            DialogHelper.error(tr("conn_test_error"), parent=self, details=str(e))

    def _on_save(self):
        """Handle save button click"""
        try:
            # Validate alias
            alias = self.alias_edit.text().strip()
            if not alias:
                DialogHelper.warning(tr("conn_enter_alias"), parent=self)
                return

            # Get credentials
            username, password, remember = self._get_credentials()

            # Build connection string WITHOUT credentials
            connection_string = self._build_connection_string()

            if not connection_string:
                DialogHelper.warning(tr("conn_fill_required"), parent=self)
                return

            # Create or update DatabaseConnection
            db_conn = DatabaseConnection(
                id=self.connection_id,
                name=alias,
                db_type=self._get_db_type(),
                connection_string=connection_string,
                description=self.description_edit.toPlainText().strip()
            )

            # Save to database
            self.config_db.save_database_connection(db_conn)

            # Save credentials if remember is checked
            if remember and username:
                CredentialManager.save_credentials(self.connection_id, username, password)
            elif not remember:
                # Delete existing credentials if unchecked
                CredentialManager.delete_credentials(self.connection_id)

            DialogHelper.info(tr("conn_saved"), parent=self)
            self.accept()

        except Exception as e:
            logger.error(f"Error saving connection: {e}")
            DialogHelper.error(tr("conn_save_error"), parent=self, details=str(e))

    @abstractmethod
    def _get_credentials(self) -> tuple[str, str, bool]:
        """
        Get credentials from UI.

        Returns:
            Tuple of (username, password, remember)

        Must be implemented by subclasses.
        """
        pass
