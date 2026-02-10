"""
Edit Dialogs - Dialogs for editing database connections, root folders, etc.
"""

from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QPushButton, QLabel,
                               QFileDialog, QDialogButtonBox)
from PySide6.QtCore import Qt

from ..core.i18n_bridge import tr


class EditRootFolderDialog(QDialog):
    """Dialog for editing RootFolder name and description"""

    def __init__(self, parent=None, name: str = "", description: str = "", path: str = ""):
        super().__init__(parent)

        self.setWindowTitle(tr("edit_rootfolder_title") if name else tr("add_rootfolder_title"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        self.name = name
        self.description = description
        self.path = path

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # Path field (read-only or with browse button for new)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(self.path)
        self.path_edit.setReadOnly(bool(self.path))  # Read-only if editing existing
        path_layout.addWidget(self.path_edit)

        if not self.path:
            # Add browse button for new root folder
            browse_btn = QPushButton(tr("browse"))
            browse_btn.clicked.connect(self._browse_folder)
            path_layout.addWidget(browse_btn)

        form_layout.addRow(tr("path") + ":", path_layout)

        # Name field
        self.name_edit = QLineEdit(self.name)
        self.name_edit.setPlaceholderText(tr("enter_name"))
        form_layout.addRow(tr("name") + ":", self.name_edit)

        # Description field
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(self.description)
        self.description_edit.setPlaceholderText(tr("enter_description"))
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow(tr("description") + ":", self.description_edit)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _browse_folder(self):
        """Browse for folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            tr("select_folder"),
            str(Path.home())
        )

        if folder:
            self.path_edit.setText(folder)
            # Auto-fill name with folder name if name is empty
            if not self.name_edit.text():
                self.name_edit.setText(Path(folder).name)

    def get_values(self) -> tuple:
        """Return (name, description, path)"""
        return (
            self.name_edit.text().strip(),
            self.description_edit.toPlainText().strip(),
            self.path_edit.text().strip()
        )


class EditDatabaseConnectionDialog(QDialog):
    """Dialog for editing DatabaseConnection name and description"""

    def __init__(self, parent=None, name: str = "", description: str = ""):
        super().__init__(parent)

        self.setWindowTitle(tr("edit_database_connection_title"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(250)

        self.name = name
        self.description = description

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # Name field
        self.name_edit = QLineEdit(self.name)
        self.name_edit.setPlaceholderText(tr("enter_name"))
        form_layout.addRow(tr("name") + ":", self.name_edit)

        # Description field
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(self.description)
        self.description_edit.setPlaceholderText(tr("enter_description"))
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow(tr("description") + ":", self.description_edit)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self) -> tuple:
        """Return (name, description)"""
        return (
            self.name_edit.text().strip(),
            self.description_edit.toPlainText().strip()
        )


class EditWorkspaceDialog(QDialog):
    """Dialog for creating/editing Workspace name and description"""

    def __init__(self, parent=None, name: str = "", description: str = "",
                 auto_connect: bool = False, is_new: bool = True):
        super().__init__(parent)

        title = tr("new_workspace") if is_new else tr("edit_workspace")
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setMinimumHeight(280)

        self.name = name
        self.description = description
        self.auto_connect = auto_connect

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # Name field
        self.name_edit = QLineEdit(self.name)
        self.name_edit.setPlaceholderText(tr("enter_name"))
        form_layout.addRow(tr("name") + ":", self.name_edit)

        # Description field
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(self.description)
        self.description_edit.setPlaceholderText(tr("enter_description"))
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow(tr("description") + ":", self.description_edit)

        layout.addLayout(form_layout)

        # Auto-connect checkbox
        from PySide6.QtWidgets import QCheckBox
        self.auto_connect_checkbox = QCheckBox(
            "Connexion automatique au démarrage (bases de données et FTP)")
        self.auto_connect_checkbox.setChecked(self.auto_connect)
        self.auto_connect_checkbox.setToolTip(
            "Si activé, toutes les connexions de ce workspace seront "
            "établies automatiquement au lancement de l'application.")
        layout.addWidget(self.auto_connect_checkbox)

        layout.addSpacing(10)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self) -> tuple:
        """Return (name, description, auto_connect)"""
        return (
            self.name_edit.text().strip(),
            self.description_edit.toPlainText().strip(),
            self.auto_connect_checkbox.isChecked()
        )
