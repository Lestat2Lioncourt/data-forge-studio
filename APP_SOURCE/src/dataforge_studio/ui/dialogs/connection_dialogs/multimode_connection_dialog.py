"""
MultiMode Connection Dialog - Base class for connection dialogs with Simple/Advanced modes

Factorizes the common pattern used in MySQL, PostgreSQL, and SQL Server dialogs.
"""

from abc import abstractmethod
from typing import Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QTabWidget, QLabel, QGroupBox)

from .base_connection_dialog import BaseConnectionDialog
from .credentials_widget import CredentialsWidget
from ....database.config_db import DatabaseConnection
from ....utils.credential_manager import CredentialManager

import logging
logger = logging.getLogger(__name__)


class MultiModeConnectionDialog(BaseConnectionDialog):
    """
    Base class for connection dialogs with Simple and Advanced modes.

    Provides:
    - Tab widget with Simple/Advanced tabs
    - Simple mode: Host, Port, Database fields
    - Advanced mode: Direct connection string input
    - Credentials widget for both modes

    Subclasses must implement:
    - _get_default_port() -> str
    - _get_connection_prefix() -> str (e.g., "mysql+pymysql://", "postgresql://")
    - _get_simple_mode_placeholder() -> str
    - _get_advanced_mode_placeholder() -> str
    - _test_connection(connection_string) -> tuple[bool, str]
    - _get_db_type() -> str
    """

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _setup_connection_fields(self):
        """Setup connection fields with Simple/Advanced tabs."""
        self.tab_widget = QTabWidget()

        # === SIMPLE MODE TAB ===
        simple_widget = QWidget()
        simple_layout = QVBoxLayout(simple_widget)

        # Server configuration
        server_group = QGroupBox("Server Configuration")
        server_layout = QFormLayout(server_group)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("e.g., localhost or 192.168.1.100")
        self.host_edit.setText("localhost")
        server_layout.addRow("Host:", self.host_edit)

        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText(f"Default: {self._get_default_port()}")
        self.port_edit.setText(self._get_default_port())
        server_layout.addRow("Port:", self.port_edit)

        self.database_edit = QLineEdit()
        self.database_edit.setPlaceholderText(self._get_simple_mode_placeholder())
        database_help = QLabel(f"ℹ️ {self._get_simple_mode_placeholder()}")
        database_help.setStyleSheet("color: gray; font-size: 10px;")
        server_layout.addRow("Database:", self.database_edit)
        server_layout.addRow("", database_help)

        simple_layout.addWidget(server_group)

        # Credentials
        self.simple_credentials_widget = CredentialsWidget(show_remember=True)
        simple_layout.addWidget(self.simple_credentials_widget)

        simple_layout.addStretch()

        self.tab_widget.addTab(simple_widget, "Simple Mode")

        # === ADVANCED MODE TAB ===
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)

        # Connection string input
        conn_str_group = QGroupBox("Connection String")
        conn_str_layout = QVBoxLayout(conn_str_group)

        self.connection_string_edit = QTextEdit()
        self.connection_string_edit.setPlaceholderText(self._get_advanced_mode_placeholder())
        self.connection_string_edit.setMaximumHeight(120)
        conn_str_layout.addWidget(self.connection_string_edit)

        # Warning label
        warning_label = QLabel("⚠️ Do not include username or password in the connection string")
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        conn_str_layout.addWidget(warning_label)

        advanced_layout.addWidget(conn_str_group)

        # Credentials
        self.advanced_credentials_widget = CredentialsWidget(show_remember=True)
        advanced_layout.addWidget(self.advanced_credentials_widget)

        advanced_layout.addStretch()

        self.tab_widget.addTab(advanced_widget, "Advanced Mode")

        # Add tab widget to main layout
        self.connection_fields_layout.addWidget(self.tab_widget)

    def _build_connection_string(self, username: str = "", password: str = "") -> str:
        """Build connection string from UI fields."""
        if self.tab_widget.currentIndex() == 0:
            # Simple Mode
            return self._build_simple_connection_string(username, password)
        else:
            # Advanced Mode
            return self._build_advanced_connection_string(username, password)

    def _build_simple_connection_string(self, username: str = "", password: str = "") -> str:
        """Build connection string from simple mode fields."""
        host = self.host_edit.text().strip()
        port = self.port_edit.text().strip() or self._get_default_port()

        if not host:
            return ""

        conn_str = self._get_connection_prefix()

        # Add credentials if provided (for testing only)
        if username and password:
            conn_str += f"{username}:{password}@"

        conn_str += f"{host}:{port}"

        # Add database if specified
        database = self.database_edit.text().strip()
        if database:
            conn_str += f"/{database}"

        return conn_str

    def _build_advanced_connection_string(self, username: str = "", password: str = "") -> str:
        """Build connection string from advanced mode (direct input)."""
        conn_str = self.connection_string_edit.toPlainText().strip()

        if not conn_str:
            return ""

        # Add credentials if provided (for testing only)
        if username and password:
            if "://" in conn_str and "@" not in conn_str:
                parts = conn_str.split("://")
                conn_str = f"{parts[0]}://{username}:{password}@{parts[1]}"

        return conn_str

    def _get_credentials(self) -> tuple[str, str, bool]:
        """Get credentials from current mode."""
        if self.tab_widget.currentIndex() == 0:
            return self.simple_credentials_widget.get_credentials()
        else:
            return self.advanced_credentials_widget.get_credentials()

    def _load_existing_connection(self):
        """Load existing connection into fields."""
        super()._load_existing_connection()

        if not self.connection:
            return

        # Load credentials from keyring
        username, password = CredentialManager.get_credentials(self.connection.id)
        has_stored_credentials = bool(username)

        # Load into advanced mode
        self.connection_string_edit.setPlainText(self.connection.connection_string)
        if has_stored_credentials:
            self.advanced_credentials_widget.set_credentials(username, password, True)

        # Try to parse simple mode fields from connection string
        self._parse_connection_string_to_simple_mode(
            self.connection.connection_string,
            username if has_stored_credentials else "",
            password if has_stored_credentials else "",
            has_stored_credentials
        )

    def _parse_connection_string_to_simple_mode(self, conn_str: str, username: str, password: str, has_credentials: bool):
        """
        Parse connection string and populate simple mode fields.

        Subclasses can override for custom parsing logic.
        """
        prefix = self._get_connection_prefix()

        if not conn_str.startswith(prefix):
            return

        # Remove prefix
        conn_str = conn_str[len(prefix):]

        # Skip auth part if present
        if "@" in conn_str:
            conn_str = conn_str.split("@", 1)[1]

        # Parse host:port/database
        if "/" in conn_str:
            host_port, database_opts = conn_str.split("/", 1)
            # Remove query params if present
            database = database_opts.split("?")[0] if "?" in database_opts else database_opts
            self.database_edit.setText(database)
        else:
            host_port = conn_str

        if ":" in host_port:
            host, port = host_port.split(":", 1)
            self.host_edit.setText(host)
            self.port_edit.setText(port)
        else:
            self.host_edit.setText(host_port)

        # Load credentials into simple mode
        if has_credentials:
            self.simple_credentials_widget.set_credentials(username, password, True)

    # Abstract methods that subclasses must implement

    @abstractmethod
    def _get_default_port(self) -> str:
        """Return default port for this database type."""
        pass

    @abstractmethod
    def _get_connection_prefix(self) -> str:
        """Return connection string prefix (e.g., 'mysql+pymysql://', 'postgresql://')."""
        pass

    @abstractmethod
    def _get_simple_mode_placeholder(self) -> str:
        """Return placeholder text for database field in simple mode."""
        pass

    @abstractmethod
    def _get_advanced_mode_placeholder(self) -> str:
        """Return placeholder text for advanced mode connection string."""
        pass
