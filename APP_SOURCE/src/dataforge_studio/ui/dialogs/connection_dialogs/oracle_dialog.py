"""
Oracle Connection Dialog - Simple and Advanced modes
"""

from typing import Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QTabWidget, QLabel, QGroupBox)

from .base_connection_dialog import BaseConnectionDialog
from .credentials_widget import CredentialsWidget
from ....database.config_db import DatabaseConnection
from ....utils.credential_manager import CredentialManager

import logging
logger = logging.getLogger(__name__)


class OracleConnectionDialog(BaseConnectionDialog):
    """Oracle connection dialog with Simple and Advanced modes."""

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _setup_connection_fields(self):
        """Setup Oracle-specific fields"""
        self.tab_widget = QTabWidget()

        # Simple Mode
        simple_widget = QWidget()
        simple_layout = QVBoxLayout(simple_widget)

        server_group = QGroupBox("Server Configuration")
        server_layout = QFormLayout(server_group)

        self.host_edit = QLineEdit("localhost")
        server_layout.addRow("Host:", self.host_edit)

        self.port_edit = QLineEdit("1521")
        server_layout.addRow("Port:", self.port_edit)

        self.service_name_edit = QLineEdit()
        self.service_name_edit.setPlaceholderText("e.g., ORCL, XE")
        server_layout.addRow("Service Name:", self.service_name_edit)

        simple_layout.addWidget(server_group)

        self.simple_credentials_widget = CredentialsWidget(show_remember=True)
        simple_layout.addWidget(self.simple_credentials_widget)
        simple_layout.addStretch()

        self.tab_widget.addTab(simple_widget, "Simple Mode")

        # Advanced Mode
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)

        conn_str_group = QGroupBox("Connection String (TNS)")
        conn_str_layout = QVBoxLayout(conn_str_group)

        self.connection_string_edit = QTextEdit()
        self.connection_string_edit.setPlaceholderText(
            "Example TNS:\n"
            "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1521))"
            "(CONNECT_DATA=(SERVICE_NAME=ORCL)))\n\n"
            "Or Easy Connect:\n"
            "localhost:1521/ORCL"
        )
        self.connection_string_edit.setMaximumHeight(120)
        conn_str_layout.addWidget(self.connection_string_edit)

        warning_label = QLabel("⚠️ Do not include username or password in the connection string")
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        conn_str_layout.addWidget(warning_label)

        advanced_layout.addWidget(conn_str_group)

        self.advanced_credentials_widget = CredentialsWidget(show_remember=True)
        advanced_layout.addWidget(self.advanced_credentials_widget)
        advanced_layout.addStretch()

        self.tab_widget.addTab(advanced_widget, "Advanced Mode")

        self.connection_fields_layout.addWidget(self.tab_widget)

    def _build_connection_string(self, username: str = "", password: str = "") -> str:
        """Build Oracle connection string"""
        if self.tab_widget.currentIndex() == 0:
            # Simple Mode - Easy Connect format
            host = self.host_edit.text().strip()
            port = self.port_edit.text().strip() or "1521"
            service_name = self.service_name_edit.text().strip()

            if not host or not service_name:
                return ""

            # Oracle connection string for cx_Oracle (Easy Connect)
            conn_str = f"{host}:{port}/{service_name}"

            return conn_str
        else:
            # Advanced Mode - TNS or Easy Connect
            return self.connection_string_edit.toPlainText().strip()

    def _test_connection(self, connection_string: str) -> tuple[bool, str]:
        """Test Oracle connection"""
        try:
            import cx_Oracle

            # Get credentials for testing
            username, password, _ = self._get_credentials()

            if not username or not password:
                return (False, "Username and password required for Oracle connection")

            # Connect
            conn = cx_Oracle.connect(
                user=username,
                password=password,
                dsn=connection_string
            )

            cursor = conn.cursor()

            # Get Oracle version
            cursor.execute("SELECT * FROM v$version WHERE banner LIKE 'Oracle%'")
            version = cursor.fetchone()[0]

            # Get current user
            cursor.execute("SELECT USER FROM dual")
            current_user = cursor.fetchone()[0]

            conn.close()

            return (True, f"{version}\n\nConnected as: {current_user}")

        except ImportError:
            return (False, "cx_Oracle library not installed. Please install it:\npip install cx_Oracle")
        except Exception as e:
            return (False, str(e))

    def _get_db_type(self) -> str:
        return "oracle"

    def _get_credentials(self) -> tuple[str, str, bool]:
        if self.tab_widget.currentIndex() == 0:
            return self.simple_credentials_widget.get_credentials()
        else:
            return self.advanced_credentials_widget.get_credentials()

    def _load_existing_connection(self):
        super()._load_existing_connection()
        if not self.connection:
            return

        username, password = CredentialManager.get_credentials(self.connection.id)
        self.connection_string_edit.setPlainText(self.connection.connection_string)

        if username:
            self.advanced_credentials_widget.set_credentials(username, password, True)
            self.simple_credentials_widget.set_credentials(username, password, True)

        # Try to parse simple mode from Easy Connect format
        conn_str = self.connection.connection_string
        if ":" in conn_str and "/" in conn_str and "(" not in conn_str:
            # Easy Connect format: host:port/service
            host_port, service = conn_str.split("/", 1)
            if ":" in host_port:
                host, port = host_port.split(":", 1)
                self.host_edit.setText(host)
                self.port_edit.setText(port)
            else:
                self.host_edit.setText(host_port)
            self.service_name_edit.setText(service)
