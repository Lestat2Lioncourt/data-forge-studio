"""
Microsoft Access Connection Dialog
"""

from typing import Optional
import pyodbc

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLineEdit

from .file_based_connection_dialog import FileBasedConnectionDialog
from .credentials_widget import CredentialsWidget
from ....database.config_db import DatabaseConnection
from ....utils.credential_manager import CredentialManager
from ....utils.connection_error_handler import format_connection_error

import logging
logger = logging.getLogger(__name__)


class AccessConnectionDialog(FileBasedConnectionDialog):
    """
    Microsoft Access connection dialog.

    Features:
    - File selector for .accdb/.mdb files
    - Create new database option
    - Optional password protection
    """

    def __init__(self, parent: Optional[QWidget] = None, connection: Optional[DatabaseConnection] = None):
        super().__init__(parent, connection)

    def _get_file_extension(self) -> str:
        """Get Access file extension (default for new databases)"""
        return ".accdb"

    def _get_file_filter(self) -> str:
        """Get file filter supporting both .mdb and .accdb"""
        return "Access Files (*.accdb *.mdb);;Access 2007+ (*.accdb);;Access 97-2003 (*.mdb);;All Files (*.*)"

    def _get_db_type(self) -> str:
        """Get database type identifier"""
        return "access"

    def _supports_password(self) -> bool:
        """Access supports password protection"""
        return True

    def _setup_password_field(self):
        """Setup password field for Access"""
        password_group = QGroupBox("Database Password (Optional)")
        password_layout = QVBoxLayout(password_group)

        # Use CredentialsWidget but hide username (Access only needs password)
        self.credentials_widget = CredentialsWidget(show_remember=True)
        self.credentials_widget.username_edit.hide()
        self.credentials_widget.findChild(QWidget, "Username:").hide() if hasattr(self.credentials_widget, "Username:") else None

        password_layout.addWidget(self.credentials_widget)

        self.connection_fields_layout.addWidget(password_group)

    def _create_database_file(self, file_path: str):
        """Create a new Access database file"""
        from ...widgets.dialog_helper import DialogHelper
        from PySide6.QtWidgets import QInputDialog

        try:
            # Ask if user wants to protect with password
            protect = DialogHelper.confirm(
                "Do you want to protect this database with a password?\n\n"
                "If yes, you will need to enter this password every time you connect.",
                parent=self
            )

            password = ""
            if protect:
                # Ask for password
                password, ok = QInputDialog.getText(
                    self,
                    "Database Password",
                    "Enter password for the new database:",
                    QLineEdit.EchoMode.Password
                )

                if not ok or not password:
                    # User cancelled password entry
                    DialogHelper.info("Database creation cancelled.", parent=self)
                    return

                # Confirm password
                password_confirm, ok = QInputDialog.getText(
                    self,
                    "Confirm Password",
                    "Confirm password:",
                    QLineEdit.EchoMode.Password
                )

                if not ok or password != password_confirm:
                    DialogHelper.warning("Passwords do not match. Database creation cancelled.", parent=self)
                    return

            # Create new Access database using ADOX (requires pywin32)
            import win32com.client

            catalog = win32com.client.Dispatch("ADOX.Catalog")

            # Build connection string
            conn_str = f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={file_path}"

            # Add password if provided
            if password:
                conn_str += f";Jet OLEDB:Database Password={password}"

            catalog.Create(conn_str)
            catalog = None

            # If password was set, store it in the credentials widget for later use
            if password and hasattr(self, 'credentials_widget'):
                self.credentials_widget.set_credentials("", password, True)

        except ImportError:
            # Fallback: Create connection string and let user know they need to create it manually
            DialogHelper.warning(
                "Cannot create Access database automatically.\n\n"
                "Please create the database manually using Microsoft Access,\n"
                "then select the file using the Browse button.",
                parent=self
            )
        except Exception as e:
            raise Exception(f"Failed to create Access database: {e}")

    def _build_file_connection_string(self, file_path: str, password: str = "") -> str:
        """Build Access connection string"""
        conn_str = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};Dbq={file_path};"

        # Add password if provided (only for testing)
        if password:
            conn_str += f"Pwd={password};"

        return conn_str

    def _test_connection(self, connection_string: str) -> tuple[bool, str]:
        """Test Access connection"""
        try:
            # Try to connect
            from ....constants import CONNECTION_TIMEOUT_S
            conn = pyodbc.connect(connection_string, timeout=CONNECTION_TIMEOUT_S)
            cursor = conn.cursor()

            # Get table count
            tables = cursor.tables(tableType='TABLE')
            table_count = len(list(tables))

            conn.close()

            return (True, f"Microsoft Access Database\nTables: {table_count}")

        except Exception as e:
            error_msg = format_connection_error(e, db_type="access", include_original=False)
            return (False, error_msg)

    def _extract_file_path(self, connection_string: str) -> str:
        """Extract file path from Access connection string"""
        if "Dbq=" in connection_string:
            start = connection_string.index("Dbq=") + 4
            end = connection_string.index(";", start) if ";" in connection_string[start:] else len(connection_string)
            return connection_string[start:end]
        return ""

    def _get_credentials(self) -> tuple[str, str, bool]:
        """Get password from credentials widget"""
        if hasattr(self, 'credentials_widget'):
            _, password, remember = self.credentials_widget.get_credentials()
            return ("", password, remember)  # Access only uses password, not username
        return ("", "", False)

    def _load_existing_connection(self):
        """Load existing connection into fields"""
        super()._load_existing_connection()

        if not self.connection:
            return

        # Try to load password from keyring
        _, password = CredentialManager.get_credentials(self.connection.id)
        if password and hasattr(self, 'credentials_widget'):
            self.credentials_widget.set_credentials("", password, True)
