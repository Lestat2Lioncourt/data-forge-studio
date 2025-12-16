"""
MongoDB Connection Dialog - Simple and Advanced modes
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


class MongoDBConnectionDialog(BaseConnectionDialog):
    """MongoDB connection dialog with Simple and Advanced modes."""

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _setup_connection_fields(self):
        """Setup MongoDB-specific fields"""
        self.tab_widget = QTabWidget()

        # Simple Mode
        simple_widget = QWidget()
        simple_layout = QVBoxLayout(simple_widget)

        server_group = QGroupBox("Server Configuration")
        server_layout = QFormLayout(server_group)

        self.host_edit = QLineEdit("localhost")
        server_layout.addRow("Host:", self.host_edit)

        self.port_edit = QLineEdit("27017")
        server_layout.addRow("Port:", self.port_edit)

        self.database_edit = QLineEdit()
        self.database_edit.setPlaceholderText("Leave empty to connect all authorized databases")
        server_layout.addRow("Database:", self.database_edit)

        self.auth_database_edit = QLineEdit("admin")
        server_layout.addRow("Auth Database:", self.auth_database_edit)

        simple_layout.addWidget(server_group)

        self.simple_credentials_widget = CredentialsWidget(show_remember=True)
        simple_layout.addWidget(self.simple_credentials_widget)
        simple_layout.addStretch()

        self.tab_widget.addTab(simple_widget, "Simple Mode")

        # Advanced Mode
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)

        conn_str_group = QGroupBox("MongoDB URI")
        conn_str_layout = QVBoxLayout(conn_str_group)

        self.connection_string_edit = QTextEdit()
        self.connection_string_edit.setPlaceholderText(
            "Example:\n"
            "mongodb://localhost:27017/mydb\n\n"
            "Or with options:\n"
            "mongodb://localhost:27017/mydb?authSource=admin"
        )
        self.connection_string_edit.setMaximumHeight(120)
        conn_str_layout.addWidget(self.connection_string_edit)

        warning_label = QLabel("⚠️ Do not include username or password in the URI")
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        conn_str_layout.addWidget(warning_label)

        advanced_layout.addWidget(conn_str_group)

        self.advanced_credentials_widget = CredentialsWidget(show_remember=True)
        advanced_layout.addWidget(self.advanced_credentials_widget)
        advanced_layout.addStretch()

        self.tab_widget.addTab(advanced_widget, "Advanced Mode")

        self.connection_fields_layout.addWidget(self.tab_widget)

    def _build_connection_string(self, username: str = "", password: str = "") -> str:
        """Build MongoDB connection string"""
        if self.tab_widget.currentIndex() == 0:
            # Simple Mode
            host = self.host_edit.text().strip()
            port = self.port_edit.text().strip() or "27017"
            database = self.database_edit.text().strip()
            auth_db = self.auth_database_edit.text().strip() or "admin"

            if not host:
                return ""

            conn_str = f"mongodb://"

            if username and password:
                conn_str += f"{username}:{password}@"

            conn_str += f"{host}:{port}"

            if database:
                conn_str += f"/{database}"

            conn_str += f"?authSource={auth_db}"

            return conn_str
        else:
            # Advanced Mode
            conn_str = self.connection_string_edit.toPlainText().strip()

            if not conn_str or not username or not password:
                return conn_str

            if "://" in conn_str and "@" not in conn_str:
                parts = conn_str.split("://")
                conn_str = f"{parts[0]}://{username}:{password}@{parts[1]}"

            return conn_str

    def _test_connection(self, connection_string: str) -> tuple[bool, str]:
        """Test MongoDB connection"""
        try:
            from pymongo import MongoClient

            client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            # Force connection
            server_info = client.server_info()

            version = server_info.get('version', 'Unknown')
            databases = client.list_database_names()

            client.close()

            return (True, f"MongoDB version: {version}\nDatabases: {len(databases)}")

        except ImportError:
            return (False, "pymongo library not installed. Please install it:\npip install pymongo")
        except Exception as e:
            return (False, str(e))

    def _get_db_type(self) -> str:
        return "mongodb"

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
