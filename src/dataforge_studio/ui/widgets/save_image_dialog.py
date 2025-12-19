"""
Save Image Dialog - Dialog for adding/editing an image in the image library
"""

from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QLabel,
    QDialogButtonBox, QGroupBox, QFileDialog, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, SavedImage


class SaveImageDialog(QDialog):
    """
    Dialog for adding or editing an image in the image library.

    Features:
    - Name field (required)
    - Description field (optional)
    - Category selection (existing or new)
    - File path with browse button
    - Image preview
    """

    # Supported image extensions
    IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg")

    def __init__(self, parent=None, image: Optional[SavedImage] = None,
                 edit_mode: bool = False, default_category: str = ""):
        """
        Initialize the save image dialog.

        Args:
            parent: Parent widget
            image: Existing SavedImage object (for edit mode)
            edit_mode: True if editing an existing image
            default_category: Default category to pre-select
        """
        super().__init__(parent)

        self.image = image
        self.edit_mode = edit_mode
        self.default_category = default_category

        title = "Edit Image / Modifier l'image" if edit_mode else "Add Image / Ajouter une image"
        self.setWindowTitle(title)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._setup_ui()
        self._load_categories()

        # Populate fields if editing
        if edit_mode and image:
            self._populate_from_image(image)
        elif default_category:
            # Set default category for new image
            index = self.category_combo.findText(default_category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.setCurrentText(default_category)

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Form section
        form_group = QGroupBox("Image Information / Informations de l'image")
        form_layout = QFormLayout(form_group)

        # Name field (required)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter image name / Entrez le nom de l'image")
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

        # File path field with browse button
        filepath_layout = QHBoxLayout()
        self.filepath_edit = QLineEdit()
        self.filepath_edit.setPlaceholderText("Select image file / Sélectionnez un fichier image")
        self.filepath_edit.textChanged.connect(self._on_filepath_changed)
        filepath_layout.addWidget(self.filepath_edit)

        self.browse_btn = QPushButton("Browse... / Parcourir...")
        self.browse_btn.clicked.connect(self._browse_file)
        filepath_layout.addWidget(self.browse_btn)

        form_layout.addRow("File / Fichier *:", filepath_layout)

        layout.addWidget(form_group)

        # Image preview section
        preview_group = QGroupBox("Preview / Aperçu")
        preview_layout = QVBoxLayout(preview_group)

        # Scrollable preview area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        scroll_area.setStyleSheet("QScrollArea { background-color: #2d2d2d; }")

        self.preview_label = QLabel("No image selected / Aucune image sélectionnée")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("QLabel { color: #888; background-color: #2d2d2d; }")
        scroll_area.setWidget(self.preview_label)

        preview_layout.addWidget(scroll_area)
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
        """Load existing categories from saved images."""
        try:
            config_db = get_config_db()
            images = config_db.get_all_saved_images()

            # Extract unique categories
            categories = set()
            for img in images:
                if img.category and img.category != "No category":
                    categories.add(img.category)

            # Add default categories if none exist
            if not categories:
                categories = {"Screenshots", "Diagrams", "Photos", "Icons"}

            # Sort and add to combo
            self.category_combo.clear()
            self.category_combo.addItem("")  # Empty option
            for cat in sorted(categories):
                self.category_combo.addItem(cat)

        except Exception:
            # Add defaults on error
            self.category_combo.addItems(["", "Screenshots", "Diagrams", "Photos"])

    def _populate_from_image(self, image: SavedImage):
        """Populate form fields from an existing image."""
        self.name_edit.setText(image.name)
        self.description_edit.setText(image.description or "")
        self.filepath_edit.setText(image.filepath)

        # Set category
        if image.category:
            index = self.category_combo.findText(image.category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.setCurrentText(image.category)

    def _browse_file(self):
        """Open file browser to select an image."""
        # Build filter string
        extensions = " ".join(f"*{ext}" for ext in self.IMAGE_EXTENSIONS)
        filter_str = f"Images ({extensions});;All Files (*.*)"

        # Start from current filepath directory if set
        start_dir = ""
        current = self.filepath_edit.text().strip()
        if current:
            path = Path(current)
            if path.parent.exists():
                start_dir = str(path.parent)

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image / Sélectionner une image",
            start_dir,
            filter_str
        )

        if filepath:
            self.filepath_edit.setText(filepath)

            # Auto-fill name from filename if empty
            if not self.name_edit.text().strip():
                name = Path(filepath).stem
                self.name_edit.setText(name)

    def _on_filepath_changed(self, filepath: str):
        """Update preview when filepath changes."""
        self._update_preview(filepath)

    def _update_preview(self, filepath: str):
        """Update the image preview."""
        if not filepath:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("No image selected / Aucune image sélectionnée")
            return

        path = Path(filepath)
        if not path.exists():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"File not found / Fichier introuvable:\n{filepath}")
            self.preview_label.setStyleSheet("QLabel { color: #ff6666; background-color: #2d2d2d; }")
            return

        # Check if it's a valid image extension
        if path.suffix.lower() not in self.IMAGE_EXTENSIONS:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"Unsupported format / Format non supporté:\n{path.suffix}")
            self.preview_label.setStyleSheet("QLabel { color: #ff6666; background-color: #2d2d2d; }")
            return

        # Load and display image
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            self.preview_label.setText("Cannot load image / Impossible de charger l'image")
            self.preview_label.setStyleSheet("QLabel { color: #ff6666; background-color: #2d2d2d; }")
            return

        # Scale to fit preview area while maintaining aspect ratio
        scaled = pixmap.scaled(
            500, 300,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setStyleSheet("QLabel { background-color: #2d2d2d; }")

        # Show image dimensions
        self.preview_label.setToolTip(f"{pixmap.width()} x {pixmap.height()} pixels")

    def _on_save(self):
        """Handle save button click."""
        from .dialog_helper import DialogHelper

        # Validate name
        name = self.name_edit.text().strip()
        if not name:
            DialogHelper.warning(
                "Please enter an image name.\nVeuillez entrer un nom d'image.",
                parent=self
            )
            self.name_edit.setFocus()
            return

        # Validate filepath
        filepath = self.filepath_edit.text().strip()
        if not filepath:
            DialogHelper.warning(
                "Please select an image file.\nVeuillez sélectionner un fichier image.",
                parent=self
            )
            self.browse_btn.setFocus()
            return

        # Check if file exists
        if not Path(filepath).exists():
            DialogHelper.warning(
                f"File not found:\n{filepath}\n\nFichier introuvable:\n{filepath}",
                parent=self
            )
            self.filepath_edit.setFocus()
            return

        self.accept()

    def get_image_data(self) -> dict:
        """
        Get the entered image data.

        Returns:
            Dictionary with image data:
            - name: Image name
            - description: Image description
            - category: Image category
            - filepath: Path to image file
        """
        category = self.category_combo.currentText().strip()
        if not category:
            category = "No category"

        return {
            "name": self.name_edit.text().strip(),
            "description": self.description_edit.text().strip(),
            "category": category,
            "filepath": self.filepath_edit.text().strip()
        }
