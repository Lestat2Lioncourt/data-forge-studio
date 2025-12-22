"""
Credentials Widget - Reusable component for username/password input with secure storage option
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox
from PySide6.QtCore import Signal


class CredentialsWidget(QWidget):
    """
    Reusable widget for database credentials input.

    Includes:
    - Username field
    - Password field (masked)
    - "Remember password" checkbox with security info
    """

    # Signal emitted when credentials change
    credentials_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None, show_remember: bool = True):
        """
        Initialize credentials widget.

        Args:
            parent: Parent widget
            show_remember: Whether to show "Remember password" checkbox
        """
        super().__init__(parent)

        self.show_remember = show_remember
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Form layout for username and password
        form_layout = QFormLayout()

        # Username field
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter username")
        self.username_edit.textChanged.connect(lambda _: self.credentials_changed.emit())
        form_layout.addRow("Username:", self.username_edit)

        # Password field
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter password")
        self.password_edit.textChanged.connect(lambda _: self.credentials_changed.emit())
        form_layout.addRow("Password:", self.password_edit)

        layout.addLayout(form_layout)

        # Remember password checkbox (if enabled)
        if self.show_remember:
            self.remember_checkbox = QCheckBox(
                "Remember password (stored securely in your system's credential manager)"
            )
            self.remember_checkbox.setChecked(False)
            layout.addWidget(self.remember_checkbox)
        else:
            self.remember_checkbox = None

    def get_credentials(self) -> tuple[str, str, bool]:
        """
        Get credentials and remember choice.

        Returns:
            Tuple of (username, password, remember)
        """
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        remember = self.remember_checkbox.isChecked() if self.remember_checkbox else False

        return (username, password, remember)

    def set_credentials(self, username: str = "", password: str = "", remember: bool = False):
        """
        Set credentials values.

        Args:
            username: Username to display
            password: Password to display
            remember: Whether to check "Remember" checkbox
        """
        self.username_edit.setText(username)
        self.password_edit.setText(password)

        if self.remember_checkbox:
            self.remember_checkbox.setChecked(remember)

    def clear(self):
        """Clear all fields"""
        self.username_edit.clear()
        self.password_edit.clear()

        if self.remember_checkbox:
            self.remember_checkbox.setChecked(False)

    def set_enabled(self, enabled: bool):
        """Enable or disable all fields"""
        self.username_edit.setEnabled(enabled)
        self.password_edit.setEnabled(enabled)

        if self.remember_checkbox:
            self.remember_checkbox.setEnabled(enabled)

    def is_empty(self) -> bool:
        """Check if username and password are empty"""
        return not self.username_edit.text().strip() and not self.password_edit.text()
