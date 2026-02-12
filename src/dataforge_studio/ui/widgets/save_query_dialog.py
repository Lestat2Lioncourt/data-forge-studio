"""
Save Query Dialog - Dialog for saving/editing a query to the saved queries collection
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QLabel,
    QDialogButtonBox, QGroupBox
)
from PySide6.QtCore import Qt

from ..core.i18n_bridge import tr
from ..core.theme_bridge import ThemeBridge
from ...database.config_db import get_config_db, SavedQuery


class SaveQueryDialog(QDialog):
    """
    Dialog for saving or editing a SQL query.

    Features:
    - Name field (required)
    - Description field (optional)
    - Category selection (existing or new)
    - Shows target database (read-only, set from current connection)
    - Query preview (read-only for new, editable for edit mode)
    """

    def __init__(self, parent=None, query_text: str = "",
                 database_name: str = "", database_id: str = "",
                 existing_query: SavedQuery = None):
        """
        Initialize the save query dialog.

        Args:
            parent: Parent widget
            query_text: SQL query text to save
            database_name: Name of the target database (display)
            database_id: ID of the target database connection
            existing_query: If provided, dialog opens in edit mode
        """
        super().__init__(parent)

        self._existing_query = existing_query
        self._is_edit_mode = existing_query is not None

        if self._is_edit_mode:
            self.query_text = existing_query.query_text or ""
            self.database_name = database_name
            self.database_id = existing_query.target_database_id
        else:
            self.query_text = query_text
            self.database_name = database_name
            self.database_id = database_id

        title = "Edit Query / Modifier la requête" if self._is_edit_mode else (
            tr("save_query_title") if tr("save_query_title") != "save_query_title" else "Save Query / Enregistrer la requête"
        )
        self.setWindowTitle(title)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500 if self._is_edit_mode else 400)

        # Load theme colors
        self._load_theme_colors()

        self._setup_ui()
        self._load_categories()

        # Pre-fill fields in edit mode
        if self._is_edit_mode:
            self.name_edit.setText(existing_query.name)
            self.description_edit.setText(existing_query.description or "")
            # Select category
            cat = existing_query.category or ""
            idx = self.category_combo.findText(cat)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.setCurrentText(cat)

    def _load_theme_colors(self):
        """Load colors from theme."""
        try:
            theme_bridge = ThemeBridge.get_instance()
            colors = theme_bridge.get_theme_colors()
        except Exception:
            colors = {}

        # Store theme colors with fallbacks
        self._colors = {
            'text_muted': colors.get('text_muted', '#666666'),
            'code_bg': colors.get('editor_bg', colors.get('window_bg', '#2d2d2d')),
        }

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Form section
        form_group = QGroupBox("Query Information / Informations de la requête")
        form_layout = QFormLayout(form_group)

        # Name field (required)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter query name / Entrez le nom de la requête")
        form_layout.addRow("Name / Nom *:", self.name_edit)

        # Description field (optional)
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description / Description optionnelle")
        form_layout.addRow("Description:", self.description_edit)

        # Category field (combobox, editable for new categories)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setPlaceholderText("Select or enter category / Sélectionnez ou entrez une catégorie")
        form_layout.addRow("Category / Catégorie:", self.category_combo)

        # Target database (read-only display)
        self.database_label = QLabel(self.database_name or "Not specified / Non spécifié")
        self.database_label.setStyleSheet(f"color: {self._colors['text_muted']}; font-style: italic;")
        form_layout.addRow("Database / Base de données:", self.database_label)

        layout.addWidget(form_group)

        # Query section
        query_title = "SQL Query / Requête SQL" if self._is_edit_mode else "Query Preview / Aperçu de la requête"
        preview_group = QGroupBox(query_title)
        preview_layout = QVBoxLayout(preview_group)

        self.query_preview = QTextEdit()
        self.query_preview.setPlainText(self.query_text)
        self.query_preview.setReadOnly(not self._is_edit_mode)
        if not self._is_edit_mode:
            self.query_preview.setMaximumHeight(150)
        self.query_preview.setStyleSheet(f"""
            QTextEdit {{
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
                background-color: {self._colors['code_bg']};
            }}
        """)
        preview_layout.addWidget(self.query_preview)

        layout.addWidget(preview_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        # Focus on name field
        self.name_edit.setFocus()

    def _load_categories(self):
        """Load existing categories from saved queries."""
        try:
            config_db = get_config_db()
            queries = config_db.get_all_saved_queries()

            # Extract unique categories
            categories = set()
            for q in queries:
                if q.category and q.category != "No category":
                    categories.add(q.category)

            # Add default categories if none exist
            if not categories:
                categories = {"General", "Reports", "Analysis", "Maintenance"}

            # Sort and add to combo
            self.category_combo.clear()
            self.category_combo.addItem("")  # Empty option
            for cat in sorted(categories):
                self.category_combo.addItem(cat)

        except Exception as e:
            # Add defaults on error
            self.category_combo.addItems(["", "General", "Reports", "Analysis"])

    def _on_save(self):
        """Handle save button click."""
        # Validate name
        name = self.name_edit.text().strip()
        if not name:
            from .dialog_helper import DialogHelper
            DialogHelper.warning(
                "Please enter a query name.\nVeuillez entrer un nom de requête.",
                parent=self
            )
            self.name_edit.setFocus()
            return

        # Validate database (only for new queries)
        if not self._is_edit_mode and not self.database_id:
            from .dialog_helper import DialogHelper
            DialogHelper.warning(
                "No database connection specified.\nAucune connexion de base de données spécifiée.",
                parent=self
            )
            return

        self.accept()

    def get_query_data(self) -> dict:
        """
        Get the entered query data.

        Returns:
            Dictionary with query data:
            - name: Query name
            - description: Query description
            - category: Query category
            - query_text: SQL query text
            - target_database_id: Target database connection ID
        """
        category = self.category_combo.currentText().strip()
        if not category:
            category = "No category"

        # In edit mode, get query text from the editable field
        query_text = self.query_preview.toPlainText() if self._is_edit_mode else self.query_text

        return {
            "name": self.name_edit.text().strip(),
            "description": self.description_edit.text().strip(),
            "category": category,
            "query_text": query_text,
            "target_database_id": self.database_id
        }
