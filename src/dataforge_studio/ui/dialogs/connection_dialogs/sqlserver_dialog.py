"""
SQL Server Connection Dialog - Simple and Advanced modes
"""

from typing import Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QRadioButton, QButtonGroup,
                               QTabWidget, QLabel, QGroupBox)
from PySide6.QtCore import Qt

from .base_connection_dialog import BaseConnectionDialog
from .credentials_widget import CredentialsWidget
from ....database.config_db import DatabaseConnection
from ....utils.credential_manager import CredentialManager
from ....utils.connection_error_handler import format_connection_error
from ....database.sqlserver_connection import connect_sqlserver

import logging
logger = logging.getLogger(__name__)


class SQLServerConnectionDialog(BaseConnectionDialog):
    """
    SQL Server connection dialog with Simple and Advanced modes.

    Simple Mode:
    - Server name
    - Database (optional - leave empty for all databases)
    - Authentication: Windows or SQL Server
    - Username/Password (for SQL Server auth)

    Advanced Mode:
    - Direct connection string input
    - Username/Password separate
    """

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _setup_connection_fields(self):
        """Setup SQL Server-specific fields with Simple/Advanced tabs"""

        # Tab widget for Simple/Advanced modes
        self.tab_widget = QTabWidget()

        # === SIMPLE MODE TAB ===
        simple_widget = QWidget()
        simple_layout = QVBoxLayout(simple_widget)

        # Server and Database fields
        server_group = QGroupBox("Server Configuration")
        server_layout = QFormLayout(server_group)

        self.server_edit = QLineEdit()
        self.server_edit.setPlaceholderText("e.g., localhost or SERVER\\INSTANCE")
        server_layout.addRow("Server name:", self.server_edit)

        self.database_edit = QLineEdit()
        self.database_edit.setPlaceholderText("Leave empty to connect all authorized databases")
        database_help = QLabel("ℹ️ Leave empty to connect all authorized databases")
        database_help.setStyleSheet("color: gray; font-size: 10px;")
        server_layout.addRow("Database:", self.database_edit)
        server_layout.addRow("", database_help)

        simple_layout.addWidget(server_group)

        # Authentication mode
        auth_group = QGroupBox("Authentication")
        auth_layout = QVBoxLayout(auth_group)

        self.auth_button_group = QButtonGroup(self)

        self.windows_auth_radio = QRadioButton("Windows Authentication")
        self.windows_auth_radio.setChecked(True)
        self.windows_auth_radio.toggled.connect(self._on_auth_mode_changed)
        self.auth_button_group.addButton(self.windows_auth_radio)
        auth_layout.addWidget(self.windows_auth_radio)

        self.sql_auth_radio = QRadioButton("SQL Server Authentication")
        self.sql_auth_radio.toggled.connect(self._on_auth_mode_changed)
        self.auth_button_group.addButton(self.sql_auth_radio)
        auth_layout.addWidget(self.sql_auth_radio)

        simple_layout.addWidget(auth_group)

        # Credentials widget (for SQL Server authentication)
        self.simple_credentials_widget = CredentialsWidget(show_remember=True)
        self.simple_credentials_widget.set_enabled(False)  # Disabled by default (Windows auth selected)
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
        self.connection_string_edit.setPlaceholderText(
            "Example:\n"
            "Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=mydb;\n\n"
            "Or for Windows Authentication:\n"
            "Driver={ODBC Driver 17 for SQL Server};Server=localhost;Trusted_Connection=Yes;"
        )
        self.connection_string_edit.setMaximumHeight(120)
        conn_str_layout.addWidget(self.connection_string_edit)

        # Warning label
        warning_label = QLabel("⚠️ Do not include User ID or Password in the connection string")
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        conn_str_layout.addWidget(warning_label)

        advanced_layout.addWidget(conn_str_group)

        # Credentials for advanced mode
        self.advanced_credentials_widget = CredentialsWidget(show_remember=True)
        advanced_layout.addWidget(self.advanced_credentials_widget)

        advanced_layout.addStretch()

        self.tab_widget.addTab(advanced_widget, "Advanced Mode")

        # Add tab widget to main layout
        self.connection_fields_layout.addWidget(self.tab_widget)

    def _on_auth_mode_changed(self, checked: bool):
        """Handle authentication mode radio button changes"""
        # Enable/disable credentials widget based on authentication mode
        is_sql_auth = self.sql_auth_radio.isChecked()
        self.simple_credentials_widget.set_enabled(is_sql_auth)

    def _build_connection_string(self, username: str = "", password: str = "") -> str:
        """Build SQL Server connection string"""

        # Check which mode is active
        if self.tab_widget.currentIndex() == 0:
            # Simple Mode
            server = self.server_edit.text().strip()
            if not server:
                return ""

            # Start building connection string
            conn_str_parts = [
                "Driver={ODBC Driver 17 for SQL Server}",
                f"Server={server}"
            ]

            # Add database if specified
            database = self.database_edit.text().strip()
            if database:
                conn_str_parts.append(f"Database={database}")

            # Add authentication
            if self.windows_auth_radio.isChecked():
                # Windows Authentication
                conn_str_parts.append("Trusted_Connection=Yes")
            else:
                # SQL Server Authentication (credentials handled separately)
                if username and password:
                    # Only add for testing
                    conn_str_parts.append(f"UID={username}")
                    conn_str_parts.append(f"PWD={password}")

            return ";".join(conn_str_parts) + ";"

        else:
            # Advanced Mode
            conn_str = self.connection_string_edit.toPlainText().strip()

            if not conn_str:
                return ""

            # Add credentials if provided (for testing only)
            if username and password:
                # Check if connection string doesn't already have credentials
                if "UID=" not in conn_str.upper() and "USER ID=" not in conn_str.upper():
                    if not conn_str.endswith(";"):
                        conn_str += ";"
                    conn_str += f"UID={username};PWD={password};"

            return conn_str

    def _test_connection(self, connection_string: str) -> tuple[bool, str]:
        """Test SQL Server connection"""
        try:
            conn = connect_sqlserver(connection_string, timeout=5)

            # Get server version
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]

            # Get database name
            cursor.execute("SELECT DB_NAME()")
            db_name = cursor.fetchone()[0]

            conn.close()

            return (True, f"Connected to: {db_name}\n\nServer version:\n{version[:100]}...")

        except Exception as e:
            error_msg = format_connection_error(e, db_type="sqlserver", include_original=False)
            return (False, error_msg)

    def _get_db_type(self) -> str:
        """Get database type identifier"""
        return "sqlserver"

    def _get_server_name(self) -> str:
        """Get server name for error messages."""
        if self.tab_widget.currentIndex() == 0:
            return self.server_edit.text().strip()
        else:
            # Try to extract from connection string
            conn_str = self.connection_string_edit.toPlainText()
            if "Server=" in conn_str:
                import re
                match = re.search(r'Server=([^;]+)', conn_str, re.IGNORECASE)
                if match:
                    return match.group(1)
        return ""

    def _get_credentials(self) -> tuple[str, str, bool]:
        """Get credentials from current mode"""
        if self.tab_widget.currentIndex() == 0:
            # Simple Mode
            if self.windows_auth_radio.isChecked():
                # Windows auth - no credentials
                return ("", "", False)
            else:
                # SQL Server auth
                return self.simple_credentials_widget.get_credentials()
        else:
            # Advanced Mode
            return self.advanced_credentials_widget.get_credentials()

    def _load_existing_connection(self):
        """Load existing connection into fields"""
        super()._load_existing_connection()

        if not self.connection:
            return

        # Try to load credentials from keyring
        username, password = CredentialManager.get_credentials(self.connection.id)
        has_stored_credentials = bool(username)

        # Load connection string into advanced mode
        self.connection_string_edit.setPlainText(self.connection.connection_string)

        # Load credentials into advanced mode
        if has_stored_credentials:
            self.advanced_credentials_widget.set_credentials(username, password, True)

        # Try to parse simple mode fields from connection string (case-insensitive)
        conn_str = self.connection.connection_string
        conn_str_lower = conn_str.lower()

        # Parse server
        if "server=" in conn_str_lower:
            server_start = conn_str_lower.index("server=") + 7
            server_end = conn_str.find(";", server_start)
            if server_end == -1:
                server_end = len(conn_str)
            server = conn_str[server_start:server_end]
            self.server_edit.setText(server)

        # Parse database
        if "database=" in conn_str_lower:
            db_start = conn_str_lower.index("database=") + 9
            db_end = conn_str.find(";", db_start)
            if db_end == -1:
                db_end = len(conn_str)
            database = conn_str[db_start:db_end]
            self.database_edit.setText(database)

        # Parse authentication mode
        if "trusted_connection=yes" in conn_str_lower:
            self.windows_auth_radio.setChecked(True)
        else:
            self.sql_auth_radio.setChecked(True)
            if has_stored_credentials:
                self.simple_credentials_widget.set_credentials(username, password, True)
