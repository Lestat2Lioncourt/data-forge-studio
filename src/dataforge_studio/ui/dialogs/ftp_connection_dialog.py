"""
FTP Connection Dialog - Dialog for creating/editing FTP/FTPS/SFTP connections.

Supports:
- FTP (standard, unencrypted)
- FTPS (FTP over SSL/TLS)
- SFTP (SSH File Transfer Protocol)
"""

from typing import Optional
import uuid

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QDialogButtonBox,
    QGroupBox, QComboBox, QSpinBox, QCheckBox, QLabel
)
from PySide6.QtCore import Qt, QThread, Signal

from ...database.config_db import get_config_db
from ...database.models import FTPRoot, FTPProtocol
from ...utils.credential_manager import CredentialManager
from ...utils.ftp_client import FTPClientFactory, BaseFTPClient
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from .connection_dialogs.credentials_widget import CredentialsWidget

import logging
logger = logging.getLogger(__name__)


class FTPTestWorker(QThread):
    """Background worker for testing FTP connection."""

    success = Signal(str)  # Success message
    error = Signal(str)    # Error message

    def __init__(self, protocol: str, host: str, port: int,
                 username: str, password: str, passive_mode: bool):
        super().__init__()
        self.protocol = protocol
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.passive_mode = passive_mode

    def run(self):
        try:
            client = FTPClientFactory.create(
                self.protocol,
                passive_mode=self.passive_mode,
                timeout=15
            )

            if client.connect(self.host, self.port, self.username, self.password):
                # Try to list root directory to verify access
                try:
                    files = client.list_directory("/")
                    client.disconnect()
                    self.success.emit(
                        f"Connexion reussie!\n"
                        f"Protocole: {self.protocol.upper()}\n"
                        f"Serveur: {self.host}:{self.port}\n"
                        f"Fichiers/dossiers trouves: {len(files)}"
                    )
                except Exception as e:
                    client.disconnect()
                    self.success.emit(
                        f"Connexion reussie!\n"
                        f"Protocole: {self.protocol.upper()}\n"
                        f"Note: Impossible de lister le repertoire racine"
                    )
            else:
                self.error.emit("Echec de la connexion - verifiez vos identifiants")

        except Exception as e:
            self.error.emit(f"Erreur de connexion:\n{str(e)}")


class FTPConnectionDialog(QDialog):
    """
    Dialog for creating or editing FTP/FTPS/SFTP connections.

    Features:
    - Protocol selection (FTP, FTPS, SFTP)
    - Server configuration (host, port, initial path)
    - Passive mode option (FTP/FTPS only)
    - Credentials with secure storage option
    - Connection testing
    """

    def __init__(self, parent: Optional[QDialog] = None,
                 ftp_root: Optional[FTPRoot] = None):
        """
        Initialize FTP connection dialog.

        Args:
            parent: Parent widget
            ftp_root: Existing FTPRoot to edit (None for new connection)
        """
        super().__init__(parent)

        self.ftp_root = ftp_root
        self.is_editing = ftp_root is not None
        self.config_db = get_config_db()
        self._test_worker: Optional[FTPTestWorker] = None

        # Generate or use existing ID
        self.ftp_root_id = ftp_root.id if ftp_root else str(uuid.uuid4())

        title = "Modifier la connexion FTP" if self.is_editing else "Nouvelle connexion FTP"
        self.setWindowTitle(title)
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)

        self._setup_ui()
        self._load_existing_connection()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)

        # Protocol selection
        protocol_group = QGroupBox("Protocole")
        protocol_layout = QHBoxLayout(protocol_group)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItem("FTP (non securise)", "ftp")
        self.protocol_combo.addItem("FTPS (FTP over SSL/TLS)", "ftps")
        self.protocol_combo.addItem("SFTP (SSH File Transfer)", "sftp")
        self.protocol_combo.currentIndexChanged.connect(self._on_protocol_changed)
        protocol_layout.addWidget(self.protocol_combo)
        protocol_layout.addStretch()

        # Protocol availability warning
        self.sftp_warning = QLabel("")
        self.sftp_warning.setStyleSheet("color: #ff9800;")
        protocol_layout.addWidget(self.sftp_warning)

        layout.addWidget(protocol_group)

        # Server configuration
        server_group = QGroupBox("Configuration du serveur")
        server_layout = QFormLayout(server_group)

        # Host
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("ex: ftp.example.com ou 192.168.1.100")
        server_layout.addRow("Hote:", self.host_edit)

        # Port
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(21)
        server_layout.addRow("Port:", self.port_spin)

        # Initial path
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("/")
        self.path_edit.setText("/")
        server_layout.addRow("Chemin initial:", self.path_edit)

        # Passive mode (FTP/FTPS only)
        self.passive_checkbox = QCheckBox("Mode passif (recommande pour les pare-feux)")
        self.passive_checkbox.setChecked(True)
        server_layout.addRow("", self.passive_checkbox)

        layout.addWidget(server_group)

        # Credentials
        credentials_group = QGroupBox("Identifiants")
        credentials_layout = QVBoxLayout(credentials_group)

        self.credentials_widget = CredentialsWidget(show_remember=True)
        credentials_layout.addWidget(self.credentials_widget)

        layout.addWidget(credentials_group)

        # General info
        general_group = QGroupBox("Informations generales")
        general_layout = QFormLayout(general_group)

        # Alias
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("Nom d'affichage pour cette connexion")
        general_layout.addRow("Alias:", self.alias_edit)

        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Description optionnelle...")
        self.description_edit.setMaximumHeight(60)
        general_layout.addRow("Description:", self.description_edit)

        layout.addWidget(general_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.test_button = QPushButton("Tester la connexion")
        self.test_button.clicked.connect(self._on_test_connection)
        button_layout.addWidget(self.test_button)

        button_layout.addStretch()

        # Standard buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

        # Check SFTP availability
        self._check_sftp_availability()

    def _check_sftp_availability(self):
        """Check if SFTP is available and update UI."""
        if not FTPClientFactory.is_protocol_available("sftp"):
            self.sftp_warning.setText("(SFTP non disponible - paramiko requis)")

    def _on_protocol_changed(self, index: int):
        """Handle protocol selection change."""
        protocol = self.protocol_combo.currentData()

        # Update default port
        if protocol == "sftp":
            self.port_spin.setValue(22)
            self.passive_checkbox.setEnabled(False)
            self.passive_checkbox.setChecked(False)
        else:
            if self.port_spin.value() == 22:
                self.port_spin.setValue(21)
            self.passive_checkbox.setEnabled(True)
            self.passive_checkbox.setChecked(True)

    def _load_existing_connection(self):
        """Load existing FTP root data into form."""
        if not self.ftp_root:
            return

        # Set protocol
        for i in range(self.protocol_combo.count()):
            if self.protocol_combo.itemData(i) == self.ftp_root.protocol:
                self.protocol_combo.setCurrentIndex(i)
                break

        # Set server info
        self.host_edit.setText(self.ftp_root.host)
        self.port_spin.setValue(self.ftp_root.port)
        self.path_edit.setText(self.ftp_root.initial_path)
        self.passive_checkbox.setChecked(self.ftp_root.passive_mode)

        # Set general info
        self.alias_edit.setText(self.ftp_root.name)
        self.description_edit.setPlainText(self.ftp_root.description or "")

        # Load credentials from keyring
        username, password = CredentialManager.get_credentials(self.ftp_root_id)
        if username:
            self.credentials_widget.set_credentials(username, password, True)

    def _on_test_connection(self):
        """Test the FTP connection."""
        # Validate required fields
        if not self.host_edit.text().strip():
            DialogHelper.warning("Veuillez entrer l'adresse du serveur.", parent=self)
            self.host_edit.setFocus()
            return

        username, password, _ = self.credentials_widget.get_credentials()
        if not username:
            DialogHelper.warning("Veuillez entrer un nom d'utilisateur.", parent=self)
            return

        # Check SFTP availability
        protocol = self.protocol_combo.currentData()
        if protocol == "sftp" and not FTPClientFactory.is_protocol_available("sftp"):
            DialogHelper.warning(
                "SFTP n'est pas disponible.\n"
                "Installez paramiko: pip install paramiko",
                parent=self
            )
            return

        # Disable button during test
        self.test_button.setEnabled(False)
        self.test_button.setText("Test en cours...")

        # Start test in background
        self._test_worker = FTPTestWorker(
            protocol=protocol,
            host=self.host_edit.text().strip(),
            port=self.port_spin.value(),
            username=username,
            password=password,
            passive_mode=self.passive_checkbox.isChecked()
        )
        self._test_worker.success.connect(self._on_test_success)
        self._test_worker.error.connect(self._on_test_error)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.start()

    def _on_test_success(self, message: str):
        """Handle successful connection test."""
        DialogHelper.info(message, parent=self)

    def _on_test_error(self, message: str):
        """Handle failed connection test."""
        DialogHelper.warning(message, parent=self)

    def _on_test_finished(self):
        """Reset test button after test completes."""
        self.test_button.setEnabled(True)
        self.test_button.setText("Tester la connexion")
        self._test_worker = None

    def _on_save(self):
        """Save the FTP connection."""
        # Validate required fields
        if not self.host_edit.text().strip():
            DialogHelper.warning("Veuillez entrer l'adresse du serveur.", parent=self)
            self.host_edit.setFocus()
            return

        username, password, remember = self.credentials_widget.get_credentials()

        # Generate alias if not provided
        alias = self.alias_edit.text().strip()
        if not alias:
            protocol = self.protocol_combo.currentData()
            alias = f"{protocol.upper()}://{self.host_edit.text().strip()}"

        # Create or update FTPRoot
        protocol = self.protocol_combo.currentData()
        initial_path = self.path_edit.text().strip() or "/"

        ftp_root = FTPRoot(
            id=self.ftp_root_id,
            name=alias,
            protocol=protocol,
            host=self.host_edit.text().strip(),
            port=self.port_spin.value(),
            initial_path=initial_path,
            passive_mode=self.passive_checkbox.isChecked(),
            description=self.description_edit.toPlainText().strip() or None
        )

        # Save to database
        if self.config_db.save_ftp_root(ftp_root):
            # Handle credentials
            if remember and username:
                CredentialManager.save_credentials(self.ftp_root_id, username, password)
            elif not remember:
                CredentialManager.delete_credentials(self.ftp_root_id)

            self.ftp_root = ftp_root
            self.accept()
        else:
            DialogHelper.warning(
                "Erreur lors de l'enregistrement de la connexion.",
                parent=self
            )

    def get_ftp_root(self) -> Optional[FTPRoot]:
        """Get the created/edited FTPRoot."""
        return self.ftp_root
