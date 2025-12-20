"""
Image Content Handler - Handles image preview and management for ResourcesManager

Manages image preview, navigation, editing, and library operations.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QPixmap

from ...widgets.form_builder import FormBuilder
from ...widgets.dialog_helper import DialogHelper
from ....database.config_db import get_config_db

import logging
logger = logging.getLogger(__name__)


class ImageContentHandler(QObject):
    """
    Handles image content display and management in ResourcesManager.

    Manages:
    - Image preview with scroll area
    - Keyboard navigation between images
    - Edit/delete/copy operations
    - Details panel updates for images
    """

    # Signal to refresh the images tree section
    images_refreshed = Signal()

    def __init__(self, parent: QWidget, form_builder: FormBuilder):
        """
        Initialize image content handler.

        Args:
            parent: Parent widget (ResourcesManager)
            form_builder: FormBuilder for details panel updates
        """
        super().__init__(parent)
        self._parent = parent
        self._form_builder = form_builder

        # Current image context
        self._current_image_obj = None
        self._image_nav_list: List = []
        self._image_nav_index: int = 0

        # Tree items reference (for navigation sync)
        self._tree_items: Dict[str, Any] = {}

        # Create viewer widget
        self._setup_viewer()

    def _setup_viewer(self):
        """Create image viewer widget."""
        self.image_widget = QWidget()
        image_layout = QVBoxLayout(self.image_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar for image actions
        image_toolbar = QHBoxLayout()

        self.image_open_btn = QPushButton("📂 Open in Explorer")
        self.image_open_btn.clicked.connect(self._open_image_location)
        image_toolbar.addWidget(self.image_open_btn)

        self.image_copy_btn = QPushButton("📋 Copy to Clipboard")
        self.image_copy_btn.clicked.connect(self._copy_image_to_clipboard)
        image_toolbar.addWidget(self.image_copy_btn)

        self.image_edit_btn = QPushButton("✏️ Edit")
        self.image_edit_btn.clicked.connect(self._edit_current_image)
        image_toolbar.addWidget(self.image_edit_btn)

        image_toolbar.addStretch()
        image_layout.addLayout(image_toolbar)

        # Scrollable image preview area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background-color: #2d2d2d; }")

        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview_label.setStyleSheet("QLabel { background-color: #2d2d2d; }")
        scroll_area.setWidget(self.image_preview_label)

        image_layout.addWidget(scroll_area)

    def get_widget(self) -> QWidget:
        """Get the image viewer widget to add to content stack."""
        return self.image_widget

    def set_tree_items(self, tree_items: Dict[str, Any]):
        """Set reference to tree items for navigation sync."""
        self._tree_items = tree_items

    @property
    def current_image(self):
        """Get the current image object."""
        return self._current_image_obj

    def load_image(self, image_obj) -> bool:
        """
        Load and display an image preview.

        Args:
            image_obj: SavedImage object from database

        Returns:
            True if image was loaded successfully
        """
        self._current_image_obj = image_obj

        # Get image categories and tags from database
        config_db = get_config_db()
        categories = config_db.get_image_categories(image_obj.id)
        tags = config_db.get_image_tags(image_obj.id)

        categories_str = ", ".join(categories) if categories else "-"
        tags_str = ", ".join(tags) if tags else "-"

        # Update details panel
        self._form_builder.set_value("name", image_obj.name)
        self._form_builder.set_value("resource_type", "Image")
        self._form_builder.set_value("description", image_obj.description or "-")
        self._form_builder.set_value("path", image_obj.filepath)
        self._form_builder.set_value("encoding", f"Categories: {categories_str}")
        self._form_builder.set_value("separator", f"Tags: {tags_str}")
        self._form_builder.set_value("delimiter", "-")

        # Load image
        filepath = Path(image_obj.filepath)
        if filepath.exists():
            pixmap = QPixmap(str(filepath))
            if not pixmap.isNull():
                # Scale to fit while maintaining aspect ratio
                scaled = pixmap.scaled(
                    800, 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview_label.setPixmap(scaled)
                logger.info(f"Loaded image preview: {image_obj.name}")
                return True
            else:
                self.image_preview_label.setText(
                    "Cannot load image / Impossible de charger l'image"
                )
                return False
        else:
            self.image_preview_label.setText(
                f"File not found: {filepath}\nFichier introuvable: {filepath}"
            )
            return False

    def build_navigation_list(self, current_image, tree_view):
        """
        Build the list of images for arrow navigation.

        Args:
            current_image: Current image object
            tree_view: Tree view widget to get siblings from
        """
        # Get the current tree item
        current_item = tree_view.tree.currentItem()
        if not current_item:
            self._image_nav_list = [current_image]
            self._image_nav_index = 0
            return

        # Get parent item (category)
        parent_item = current_item.parent()
        if not parent_item:
            self._image_nav_list = [current_image]
            self._image_nav_index = 0
            return

        # Collect all images from this category
        self._image_nav_list = []
        self._image_nav_index = 0

        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole) or {}
            if data.get("type") == "image":
                img_obj = data.get("obj")
                if img_obj:
                    self._image_nav_list.append(img_obj)
                    if img_obj.id == current_image.id:
                        self._image_nav_index = len(self._image_nav_list) - 1

    def navigate(self, direction: int, tree_view=None) -> bool:
        """
        Navigate to previous (-1) or next (+1) image.

        Args:
            direction: -1 for previous, +1 for next
            tree_view: Optional tree view to sync selection

        Returns:
            True if navigation occurred
        """
        if not self._image_nav_list:
            return False

        new_index = self._image_nav_index + direction
        if 0 <= new_index < len(self._image_nav_list):
            self._image_nav_index = new_index
            image_obj = self._image_nav_list[new_index]
            self.load_image(image_obj)

            # Update tree selection
            if tree_view:
                item_key = f"img_{image_obj.id}"
                if item_key in self._tree_items:
                    tree_view.tree.setCurrentItem(self._tree_items.get(item_key))

            return True
        return False

    def has_navigation_list(self) -> bool:
        """Check if navigation list is available."""
        return bool(self._current_image_obj and self._image_nav_list)

    def _open_image_location(self):
        """Open the image file location in explorer."""
        import subprocess
        import platform

        if not self._current_image_obj:
            return

        filepath = Path(self._current_image_obj.filepath)
        if filepath.exists():
            if platform.system() == "Windows":
                subprocess.run(["explorer", "/select,", str(filepath)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", "-R", str(filepath)])
            else:  # Linux
                subprocess.run(["xdg-open", str(filepath.parent)])

    def _copy_image_to_clipboard(self):
        """Copy the current image to clipboard."""
        from PySide6.QtWidgets import QApplication

        if not self._current_image_obj:
            return

        filepath = Path(self._current_image_obj.filepath)
        if filepath.exists():
            pixmap = QPixmap(str(filepath))
            if not pixmap.isNull():
                QApplication.clipboard().setPixmap(pixmap)
                DialogHelper.info(
                    "Image copied to clipboard.\nImage copiée dans le presse-papier.",
                    parent=self._parent
                )

    def _edit_current_image(self):
        """Edit the current image metadata."""
        if not self._current_image_obj:
            return
        self.edit_image(self._current_image_obj)

    def add_image(self, default_category: str = ""):
        """
        Add a new image to the library.

        Args:
            default_category: Default category to pre-select
        """
        from PySide6.QtWidgets import QDialog
        from ...widgets.save_image_dialog import SaveImageDialog

        dialog = SaveImageDialog(
            parent=self._parent,
            default_category=default_category
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_image_data()

            try:
                config_db = get_config_db()
                image_id = config_db.add_saved_image(
                    name=data["name"],
                    filepath=data["filepath"],
                    category=data["category"],
                    description=data["description"]
                )

                if image_id:
                    DialogHelper.info(
                        f"Image '{data['name']}' added successfully.\n"
                        f"Image '{data['name']}' ajoutée avec succès.",
                        parent=self._parent
                    )
                    self.images_refreshed.emit()
                    logger.info(f"Added new image: {data['name']}")
                else:
                    DialogHelper.error(
                        "Failed to add image.\nÉchec de l'ajout de l'image.",
                        parent=self._parent
                    )

            except Exception as e:
                logger.error(f"Error adding image: {e}")
                DialogHelper.error(f"Error: {e}", parent=self._parent)

    def edit_image(self, image_obj):
        """
        Edit an image's metadata.

        Args:
            image_obj: SavedImage object to edit
        """
        from PySide6.QtWidgets import QDialog
        from ...widgets.save_image_dialog import SaveImageDialog

        # Store current image for preview panel context
        self._current_image_obj = image_obj

        dialog = SaveImageDialog(
            parent=self._parent,
            image=image_obj,
            edit_mode=True
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_image_data()

            # Update image object
            image_obj.name = data["name"]
            image_obj.category = data["category"]
            image_obj.description = data["description"]
            image_obj.filepath = data["filepath"]

            try:
                config_db = get_config_db()
                if config_db.update_saved_image(image_obj):
                    DialogHelper.info(
                        f"Image '{data['name']}' updated.\n"
                        f"Image '{data['name']}' mise à jour.",
                        parent=self._parent
                    )
                    self.images_refreshed.emit()
                    # Reload preview if currently viewing this image
                    if self._current_image_obj and self._current_image_obj.id == image_obj.id:
                        self.load_image(image_obj)
                    logger.info(f"Updated image: {data['name']}")
                else:
                    DialogHelper.error(
                        "Failed to update image.\nÉchec de la mise à jour.",
                        parent=self._parent
                    )

            except Exception as e:
                logger.error(f"Error updating image: {e}")
                DialogHelper.error(f"Error: {e}", parent=self._parent)

    def delete_image(self, image_obj) -> bool:
        """
        Delete an image from the library.

        Args:
            image_obj: SavedImage object to delete

        Returns:
            True if deleted successfully
        """
        if not DialogHelper.confirm(
            f"Delete image '{image_obj.name}'?\n"
            f"Supprimer l'image '{image_obj.name}' ?\n\n"
            f"(The file will not be deleted from disk)\n"
            f"(Le fichier ne sera pas supprimé du disque)",
            parent=self._parent
        ):
            return False

        try:
            config_db = get_config_db()
            if config_db.delete_saved_image(image_obj.id):
                DialogHelper.info(
                    f"Image '{image_obj.name}' removed from library.\n"
                    f"Image '{image_obj.name}' retirée de la bibliothèque.",
                    parent=self._parent
                )
                self.images_refreshed.emit()

                # Clear preview if this was the displayed image
                if self._current_image_obj and self._current_image_obj.id == image_obj.id:
                    self._current_image_obj = None
                    self.image_preview_label.clear()

                logger.info(f"Deleted image: {image_obj.name}")
                return True
            else:
                DialogHelper.error(
                    "Failed to delete image.\nÉchec de la suppression.",
                    parent=self._parent
                )
                return False

        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            DialogHelper.error(f"Error: {e}", parent=self._parent)
            return False

    def clear_current(self):
        """Clear the current image display."""
        self._current_image_obj = None
        self.image_preview_label.clear()
