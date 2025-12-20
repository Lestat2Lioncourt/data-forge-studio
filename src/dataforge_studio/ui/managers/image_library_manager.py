"""
Image Library Manager - Dedicated manager for the image library

Features:
- Tree view with physical folders (from rootfolders) and logical categories
- Image preview with details panel
- Search by name, category, and tags
- Context menus for managing images, categories, and tags
"""

import logging
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QStackedWidget,
    QLabel, QPushButton, QLineEdit, QCheckBox,
    QScrollArea, QGroupBox, QFormLayout, QFrame,
    QMenu, QApplication, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QAction, QIcon

from ..core.i18n_bridge import tr
from ..widgets.dialog_helper import DialogHelper
from ..widgets.scan_progress_dialog import ScanProgressDialog
from ..widgets.image_fullscreen_dialog import ImageFullscreenDialog
from ...database.config_db import (
    get_config_db, ImageRootfolder, SavedImage
)
from ...utils.image_scanner import ImageScanner, create_rootfolder_and_scan

logger = logging.getLogger(__name__)

# Supported image extensions for display
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg"}


class ImageLibraryManager(QWidget):
    """
    Widget for managing the image library.

    Structure:
    - Left: Tree view
        - Dossiers (physical folders from rootfolders)
        - Catégories (logical categories)
        - Recherche (search interface)
    - Right: Content area
        - Image preview
        - Details panel (categories, tags)
    """

    # Signals
    image_selected = Signal(object)  # SavedImage

    def __init__(self, parent=None):
        super().__init__(parent)

        self.config_db = get_config_db()
        self._current_image: Optional[SavedImage] = None
        self._tree_items: Dict[str, QTreeWidgetItem] = {}

        self._setup_ui()
        self._setup_connections()
        self.refresh()

    def _setup_ui(self):
        """Setup the main UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Main splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        # Left panel: Tree + Search
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # Search section
        self._setup_search_section(left_layout)

        # Action buttons
        action_layout = QHBoxLayout()
        self.add_folder_btn = QPushButton("➕ " + tr("image_add_image_folder"))
        self.add_folder_btn.clicked.connect(self._add_rootfolder)
        action_layout.addWidget(self.add_folder_btn)
        action_layout.addStretch()
        left_layout.addLayout(action_layout)

        # Tree view
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.setExpandsOnDoubleClick(False)
        left_layout.addWidget(self.tree)

        self.splitter.addWidget(left_panel)

        # Right panel: Preview + Details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Content stack
        self.content_stack = QStackedWidget()
        right_layout.addWidget(self.content_stack)

        # Page 0: Welcome / empty state
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_label = QLabel(tr("image_select_preview"))
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("color: gray; font-size: 14px;")
        welcome_layout.addWidget(welcome_label)
        self.content_stack.addWidget(welcome_widget)

        # Page 1: Image preview
        self._setup_preview_page()

        self.splitter.addWidget(right_panel)

        # Set initial splitter sizes
        self.splitter.setSizes([300, 500])

    def _setup_search_section(self, parent_layout: QVBoxLayout):
        """Setup the search section."""
        search_group = QGroupBox(tr("image_search"))
        search_layout = QVBoxLayout(search_group)

        # Search input
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("image_search_placeholder"))
        self.search_input.setClearButtonEnabled(True)
        search_row.addWidget(self.search_input)

        self.search_btn = QPushButton("🔍")
        self.search_btn.setFixedWidth(30)
        search_row.addWidget(self.search_btn)
        search_layout.addLayout(search_row)

        # Search filters
        filters_layout = QHBoxLayout()
        self.search_name_cb = QCheckBox(tr("image_name"))
        self.search_name_cb.setChecked(True)
        filters_layout.addWidget(self.search_name_cb)

        self.search_category_cb = QCheckBox(tr("image_categories"))
        self.search_category_cb.setChecked(True)
        filters_layout.addWidget(self.search_category_cb)

        self.search_tag_cb = QCheckBox(tr("image_tags"))
        self.search_tag_cb.setChecked(True)
        filters_layout.addWidget(self.search_tag_cb)

        filters_layout.addStretch()
        search_layout.addLayout(filters_layout)

        parent_layout.addWidget(search_group)

    def _setup_preview_page(self):
        """Setup the image preview page."""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Toolbar
        toolbar = QHBoxLayout()

        self.open_btn = QPushButton("📂 " + tr("image_open_explorer"))
        self.open_btn.clicked.connect(self._open_image_location)
        toolbar.addWidget(self.open_btn)

        self.copy_btn = QPushButton("📋 " + tr("image_copy_clipboard"))
        self.copy_btn.clicked.connect(self._copy_image_to_clipboard)
        toolbar.addWidget(self.copy_btn)

        toolbar.addStretch()

        self.edit_btn = QPushButton("✏️ " + tr("image_edit"))
        self.edit_btn.clicked.connect(self._edit_current_image)
        toolbar.addWidget(self.edit_btn)

        self.fullscreen_btn = QPushButton("🔲 " + tr("image_fullscreen"))
        self.fullscreen_btn.clicked.connect(self._open_fullscreen)
        toolbar.addWidget(self.fullscreen_btn)

        preview_layout.addLayout(toolbar)

        # Image preview area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background-color: #2d2d2d; }")

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("QLabel { background-color: #2d2d2d; }")
        scroll_area.setWidget(self.preview_label)

        preview_layout.addWidget(scroll_area, stretch=1)

        # Details section
        details_group = QGroupBox(tr("image_details"))
        details_layout = QFormLayout(details_group)

        self.detail_name = QLabel()
        details_layout.addRow(tr("image_name") + ":", self.detail_name)

        self.detail_path = QLabel()
        self.detail_path.setWordWrap(True)
        self.detail_path.setStyleSheet("color: gray; font-size: 10px;")
        details_layout.addRow(tr("image_path") + ":", self.detail_path)

        self.detail_physical = QLabel()
        details_layout.addRow(tr("image_folder") + ":", self.detail_physical)

        # Technical metadata
        self.detail_dimensions = QLabel()
        details_layout.addRow(tr("image_dimensions") + ":", self.detail_dimensions)

        self.detail_filesize = QLabel()
        details_layout.addRow(tr("image_filesize") + ":", self.detail_filesize)

        self.detail_format = QLabel()
        details_layout.addRow(tr("image_format") + ":", self.detail_format)

        self.detail_modified = QLabel()
        details_layout.addRow(tr("image_modified") + ":", self.detail_modified)

        # Categories section
        cat_widget = QWidget()
        cat_layout = QHBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_categories = QLabel()
        self.detail_categories.setWordWrap(True)
        cat_layout.addWidget(self.detail_categories)
        self.edit_categories_btn = QPushButton("+")
        self.edit_categories_btn.setFixedWidth(25)
        self.edit_categories_btn.setToolTip(tr("image_manage_categories"))
        self.edit_categories_btn.clicked.connect(self._manage_categories)
        cat_layout.addWidget(self.edit_categories_btn)
        details_layout.addRow(tr("image_categories") + ":", cat_widget)

        # Tags section
        tag_widget = QWidget()
        tag_layout = QHBoxLayout(tag_widget)
        tag_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_tags = QLabel()
        self.detail_tags.setWordWrap(True)
        tag_layout.addWidget(self.detail_tags)
        self.edit_tags_btn = QPushButton("+")
        self.edit_tags_btn.setFixedWidth(25)
        self.edit_tags_btn.setToolTip(tr("image_manage_tags"))
        self.edit_tags_btn.clicked.connect(self._manage_tags)
        tag_layout.addWidget(self.edit_tags_btn)
        details_layout.addRow(tr("image_tags") + ":", tag_widget)

        preview_layout.addWidget(details_group)

        self.content_stack.addWidget(preview_widget)

    def _setup_connections(self):
        """Setup signal connections."""
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

        self.search_input.returnPressed.connect(self._perform_search)
        self.search_btn.clicked.connect(self._perform_search)

    # ==================== Tree Loading ====================

    def refresh(self):
        """Refresh the entire tree."""
        self.tree.clear()
        self._tree_items.clear()

        self._load_folders_section()
        self._load_categories_section()

    def _load_folders_section(self):
        """Load the Dossiers (physical folders) section."""
        folders_item = QTreeWidgetItem(self.tree, ["📂 " + tr("image_folders")])
        folders_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "folders_root"
        })
        folders_item.setExpanded(True)
        self._tree_items["folders_root"] = folders_item

        # Load rootfolders
        rootfolders = self.config_db.get_all_image_rootfolders()
        for rf in rootfolders:
            self._add_rootfolder_to_tree(rf, folders_item)

        # Add "Add folder" item
        add_item = QTreeWidgetItem(folders_item, ["➕ " + tr("image_add_folder_hint")])
        add_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "add_rootfolder"
        })
        add_item.setForeground(0, Qt.GlobalColor.gray)

    def _add_rootfolder_to_tree(self, rootfolder: ImageRootfolder, parent_item: QTreeWidgetItem):
        """Add a rootfolder and its physical structure to the tree."""
        rf_item = QTreeWidgetItem(parent_item, [f"📁 {rootfolder.name}"])
        rf_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "image_rootfolder",
            "obj": rootfolder
        })
        self._tree_items[f"rf_{rootfolder.id}"] = rf_item

        # Get physical paths and build tree structure
        physical_paths = self.config_db.get_image_physical_paths(rootfolder.id)

        # Build hierarchical structure
        path_items = {}
        for path in physical_paths:
            if not path:  # Images at root level
                continue

            parts = path.split("/")
            current_parent = rf_item
            current_path = ""

            for part in parts:
                current_path = f"{current_path}/{part}" if current_path else part
                item_key = f"rf_{rootfolder.id}_{current_path}"

                if item_key not in path_items:
                    folder_item = QTreeWidgetItem(current_parent, [f"📁 {part}"])
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "physical_folder",
                        "rootfolder": rootfolder,
                        "physical_path": current_path
                    })
                    path_items[item_key] = folder_item
                    self._tree_items[item_key] = folder_item

                current_parent = path_items[item_key]

        # Add images at each level
        self._add_images_to_folder(rootfolder.id, "", rf_item)
        for path in physical_paths:
            if path:
                item_key = f"rf_{rootfolder.id}_{path}"
                if item_key in path_items:
                    self._add_images_to_folder(rootfolder.id, path, path_items[item_key])

    def _add_images_to_folder(self, rootfolder_id: str, physical_path: str, parent_item: QTreeWidgetItem):
        """Add images to a folder item."""
        images = self.config_db.get_images_by_physical_path(rootfolder_id, physical_path)
        for img in images:
            self._add_image_to_tree(img, parent_item)

    def _add_image_to_tree(self, image: SavedImage, parent_item: QTreeWidgetItem):
        """Add an image item to the tree."""
        # Check if image has categories or tags
        categories = self.config_db.get_image_categories(image.id)
        tags = self.config_db.get_image_tags(image.id)

        # Icon based on having categories/tags
        icon = "🖼️"
        if categories or tags:
            icon = "🖼️⭐"  # Star indicates it has metadata

        img_item = QTreeWidgetItem(parent_item, [f"{icon} {image.name}"])
        img_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "image",
            "obj": image
        })
        self._tree_items[f"img_{image.id}"] = img_item

    def _load_categories_section(self):
        """Load the Catégories (logical categories) section."""
        cat_item = QTreeWidgetItem(self.tree, ["🏷️ " + tr("image_categories")])
        cat_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "categories_root"
        })
        cat_item.setExpanded(True)
        self._tree_items["categories_root"] = cat_item

        # Load logical categories
        category_names = self.config_db.get_all_image_category_names()
        for cat_name in category_names:
            images = self.config_db.get_images_by_category(cat_name)
            count = len(images)

            cat_folder = QTreeWidgetItem(cat_item, [f"📁 {cat_name} ({count})"])
            cat_folder.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "logical_category",
                "name": cat_name
            })
            self._tree_items[f"cat_{cat_name}"] = cat_folder

            # Add images in this category
            for img in images:
                self._add_image_to_tree(img, cat_folder)

        # Add "Create category" item
        add_item = QTreeWidgetItem(cat_item, ["➕ " + tr("image_create_category")])
        add_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "add_category"
        })
        add_item.setForeground(0, Qt.GlobalColor.gray)

    # ==================== Tree Interactions ====================

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click."""
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        item_type = data.get("type", "")

        if item_type == "image":
            image = data.get("obj")
            if image:
                self._show_image_preview(image)

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item double-click."""
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        item_type = data.get("type", "")

        if item_type == "add_rootfolder":
            self._add_rootfolder()
        elif item_type == "add_category":
            self._create_category()
        elif item_type in ("image_rootfolder", "physical_folder", "logical_category",
                           "folders_root", "categories_root"):
            # Toggle expansion
            item.setExpanded(not item.isExpanded())
        elif item_type == "image":
            # Open image with default viewer
            image = data.get("obj")
            if image:
                self._open_image_external(image)

    def _on_context_menu(self, position):
        """Handle context menu request."""
        item = self.tree.itemAt(position)

        menu = QMenu(self)

        # If no item selected, show general menu
        if not item:
            menu.addAction("➕ " + tr("image_add_folder_hint"), self._add_rootfolder)
            menu.addSeparator()
            menu.addAction("🔄 " + tr("btn_refresh"), self.refresh)
            menu.exec(self.tree.viewport().mapToGlobal(position))
            return

        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        item_type = data.get("type", "")

        if item_type == "folders_root":
            menu.addAction("➕ " + tr("image_add_folder_hint"), self._add_rootfolder)
            menu.addSeparator()
            menu.addAction("🔄 " + tr("btn_refresh"), self.refresh)

        elif item_type == "image_rootfolder":
            rootfolder = data.get("obj")
            if rootfolder:
                menu.addAction("🔄 " + tr("image_rescan_folder"), lambda: self._rescan_rootfolder(rootfolder))
                menu.addSeparator()
                menu.addAction("📂 " + tr("image_open_explorer"), lambda: self._open_folder_in_explorer(rootfolder.path))
                menu.addSeparator()
                menu.addAction("🗑️ " + tr("image_remove_folder"), lambda: self._remove_rootfolder(rootfolder))

        elif item_type == "physical_folder":
            rootfolder = data.get("rootfolder")
            path = data.get("physical_path", "")
            if rootfolder:
                full_path = Path(rootfolder.path) / path
                menu.addAction("📂 " + tr("image_open_explorer"), lambda: self._open_folder_in_explorer(str(full_path)))

        elif item_type == "categories_root":
            menu.addAction("➕ " + tr("image_create_category"), self._create_category)
            menu.addSeparator()
            menu.addAction("🔄 " + tr("btn_refresh"), self.refresh)

        elif item_type == "logical_category":
            cat_name = data.get("name", "")
            menu.addAction("✏️ " + tr("image_rename_category"), lambda: self._rename_category(cat_name))
            menu.addAction("🗑️ " + tr("image_delete_category"), lambda: self._delete_category(cat_name))

        elif item_type == "image":
            image = data.get("obj")
            if image:
                menu.addAction("🔲 " + tr("image_view_fullscreen"), self._open_fullscreen)
                menu.addSeparator()
                menu.addAction("📂 " + tr("image_open_explorer"), self._open_image_location)
                menu.addAction("📋 " + tr("image_copy_clipboard"), self._copy_image_to_clipboard)
                menu.addSeparator()
                menu.addAction("🏷️ " + tr("image_manage_categories") + "...", self._manage_categories)
                menu.addAction("🔖 " + tr("image_manage_tags") + "...", self._manage_tags)
                menu.addSeparator()
                menu.addAction("✏️ " + tr("image_edit_details"), self._edit_current_image)
                menu.addAction("🗑️ " + tr("image_remove_library"), lambda: self._remove_image(image))

        if menu.actions():
            menu.exec(self.tree.viewport().mapToGlobal(position))

    # ==================== Image Preview ====================

    def _show_image_preview(self, image: SavedImage):
        """Show image in the preview panel."""
        import os
        from datetime import datetime

        self._current_image = image
        self.content_stack.setCurrentIndex(1)

        filepath = Path(image.filepath)
        dimensions_str = "-"
        filesize_str = "-"
        format_str = "-"
        modified_str = "-"

        # Load image and get metadata
        if not filepath.exists():
            self.preview_label.setText(tr("image_file_not_found") + f":\n{image.filepath}")
            self.preview_label.setStyleSheet("QLabel { color: red; background-color: #2d2d2d; }")
        else:
            pixmap = QPixmap(str(filepath))
            if pixmap.isNull():
                self.preview_label.setText(tr("image_cannot_load"))
            else:
                # Scale to fit
                scaled = pixmap.scaled(
                    600, 400,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)
                self.preview_label.setStyleSheet("QLabel { background-color: #2d2d2d; }")

                # Image dimensions
                dimensions_str = f"{pixmap.width()} x {pixmap.height()} px"

            # File size
            try:
                size_bytes = filepath.stat().st_size
                if size_bytes < 1024:
                    filesize_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    filesize_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    filesize_str = f"{size_bytes / (1024 * 1024):.2f} MB"
            except Exception:
                filesize_str = "-"

            # Format/encoding
            suffix = filepath.suffix.lower()
            format_map = {
                ".png": "PNG (Portable Network Graphics)",
                ".jpg": "JPEG (Joint Photographic Experts Group)",
                ".jpeg": "JPEG (Joint Photographic Experts Group)",
                ".gif": "GIF (Graphics Interchange Format)",
                ".bmp": "BMP (Bitmap)",
                ".webp": "WebP",
                ".svg": "SVG (Scalable Vector Graphics)",
                ".ico": "ICO (Icon)",
                ".tiff": "TIFF (Tagged Image File Format)",
                ".tif": "TIFF (Tagged Image File Format)",
            }
            format_str = format_map.get(suffix, suffix.upper())

            # Modification date
            try:
                mtime = filepath.stat().st_mtime
                modified_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                modified_str = "-"

        # Update basic details
        self.detail_name.setText(image.name)
        self.detail_path.setText(image.filepath)
        self.detail_physical.setText(image.physical_path or "(root)")

        # Update technical metadata
        self.detail_dimensions.setText(dimensions_str)
        self.detail_filesize.setText(filesize_str)
        self.detail_format.setText(format_str)
        self.detail_modified.setText(modified_str)

        # Load categories and tags
        categories = self.config_db.get_image_categories(image.id)
        tags = self.config_db.get_image_tags(image.id)

        self.detail_categories.setText(", ".join(categories) if categories else tr("categories_none"))
        self.detail_tags.setText(", ".join(tags) if tags else tr("categories_none"))

        self.image_selected.emit(image)

    # ==================== Actions ====================

    def _add_rootfolder(self):
        """Add a new image rootfolder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            tr("image_select_folder_title"),
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder:
            return

        # Check if already exists
        existing = self.config_db.get_all_image_rootfolders()
        for rf in existing:
            if rf.path == folder:
                DialogHelper.warning(
                    tr("image_folder_exists") + f"\n{folder}",
                    parent=self
                )
                return

        # Get name
        name, ok = QInputDialog.getText(
            self,
            tr("image_folder_name_title"),
            tr("image_folder_name_prompt"),
            text=Path(folder).name
        )

        if not ok or not name.strip():
            return

        # Create rootfolder and scan
        dialog = ScanProgressDialog(
            self,
            title=tr("image_scanning"),
            description=tr("image_scanning_folder") + f" {folder}"
        )

        def scan_with_rootfolder(progress_callback=None):
            rootfolder = create_rootfolder_and_scan(
                folder, name.strip(), "",
                progress_callback
            )
            if rootfolder:
                return {"success": True, "rootfolder": rootfolder}
            return {"success": False}

        dialog.set_scan_function(scan_with_rootfolder)
        result = dialog.exec_scan()

        if result and result.get("success"):
            self.refresh()
            DialogHelper.info(
                tr("image_folder_added") + "\n" +
                tr("image_found_count", count=result.get('total_found', 0)),
                parent=self
            )
        else:
            DialogHelper.error(tr("image_add_failed"), parent=self)

    def _rescan_rootfolder(self, rootfolder: ImageRootfolder):
        """Rescan a rootfolder for new/removed images."""
        dialog = ScanProgressDialog(
            self,
            title=tr("image_rescanning"),
            description=f"{tr('image_rescanning')}: {rootfolder.name}"
        )

        scanner = ImageScanner(rootfolder)
        dialog.set_scan_function(scanner.rescan, remove_missing=True)
        result = dialog.exec_scan()

        if result:
            self.refresh()
            DialogHelper.info(
                tr("image_rescan_complete") + "\n" +
                tr("image_rescan_added", count=result.get('added', 0)) + "\n" +
                tr("image_rescan_removed", count=result.get('removed', 0)),
                parent=self
            )

    def _remove_rootfolder(self, rootfolder: ImageRootfolder):
        """Remove a rootfolder from the library."""
        images = self.config_db.get_images_by_rootfolder(rootfolder.id)
        count = len(images)

        if not DialogHelper.confirm(
            tr("image_confirm_remove_folder", name=rootfolder.name) + "\n\n" +
            tr("image_remove_count", count=count) + "\n" +
            tr("image_files_not_deleted"),
            parent=self
        ):
            return

        self.config_db.delete_image_rootfolder(rootfolder.id)
        self.refresh()

    def _create_category(self):
        """Create a new logical category."""
        name, ok = QInputDialog.getText(
            self,
            tr("image_new_category_title"),
            tr("image_new_category_prompt")
        )

        if ok and name.strip():
            # Category will be created when first image is added to it
            DialogHelper.info(
                tr("image_category_hint", name=name.strip()),
                parent=self
            )

    def _rename_category(self, old_name: str):
        """Rename a logical category."""
        new_name, ok = QInputDialog.getText(
            self,
            tr("image_rename_category_title"),
            tr("image_rename_category_prompt"),
            text=old_name
        )

        if ok and new_name.strip() and new_name.strip() != old_name:
            # Get all images in this category and update them
            images = self.config_db.get_images_by_category(old_name)
            for img in images:
                self.config_db.remove_image_category(img.id, old_name)
                self.config_db.add_image_category(img.id, new_name.strip())

            self.refresh()

    def _delete_category(self, cat_name: str):
        """Delete a logical category."""
        images = self.config_db.get_images_by_category(cat_name)
        count = len(images)

        if not DialogHelper.confirm(
            tr("image_confirm_delete_category", name=cat_name) + "\n\n" +
            tr("image_delete_category_hint", count=count) + "\n" +
            tr("image_files_not_deleted"),
            parent=self
        ):
            return

        for img in images:
            self.config_db.remove_image_category(img.id, cat_name)

        self.refresh()

    def _open_image_location(self):
        """Open the current image's location in file explorer."""
        if not self._current_image:
            return

        path = Path(self._current_image.filepath)
        if not path.exists():
            DialogHelper.warning(tr("image_file_not_found") + ".", parent=self)
            return

        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", str(path)])
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", str(path)])
        else:
            subprocess.run(["xdg-open", str(path.parent)])

    def _open_folder_in_explorer(self, folder_path: str):
        """Open a folder in file explorer."""
        path = Path(folder_path)
        if not path.exists():
            DialogHelper.warning(tr("image_folder_not_found") + ".", parent=self)
            return

        if platform.system() == "Windows":
            subprocess.run(["explorer", str(path)])
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])

    def _open_image_external(self, image: SavedImage):
        """Open image with system default viewer."""
        path = Path(image.filepath)
        if not path.exists():
            DialogHelper.warning(tr("image_file_not_found") + ".", parent=self)
            return

        if platform.system() == "Windows":
            subprocess.run(["start", "", str(path)], shell=True)
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])

    def _copy_image_to_clipboard(self):
        """Copy the current image to clipboard."""
        if not self._current_image:
            return

        path = Path(self._current_image.filepath)
        if not path.exists():
            DialogHelper.warning(tr("image_file_not_found") + ".", parent=self)
            return

        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            QApplication.clipboard().setPixmap(pixmap)
            DialogHelper.info(tr("image_copied_clipboard"), parent=self)

    def _open_fullscreen(self):
        """Open current image in fullscreen dialog."""
        if not self._current_image:
            return

        # Build image list for navigation
        image_list = self._build_image_list()

        dialog = ImageFullscreenDialog(
            parent=self,
            image=self._current_image,
            image_list=image_list
        )
        dialog.showMaximized()
        dialog.exec()

    def _build_image_list(self) -> List[SavedImage]:
        """Build a list of images for navigation based on current context."""
        # Get currently selected item to determine context
        current_item = self.tree.currentItem()
        if not current_item:
            return [self._current_image] if self._current_image else []

        # Find parent to determine context (folder, category, or search results)
        parent = current_item.parent()
        if not parent:
            return [self._current_image] if self._current_image else []

        # Collect all image children from the parent
        images = []
        for i in range(parent.childCount()):
            child = parent.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole) or {}
            if data.get("type") == "image":
                img = data.get("obj")
                if img:
                    images.append(img)

        return images if images else ([self._current_image] if self._current_image else [])

    def _edit_current_image(self):
        """Edit the current image's details."""
        if not self._current_image:
            return

        # For now, just allow editing name and description
        name, ok = QInputDialog.getText(
            self,
            tr("image_edit_title"),
            tr("image_edit_name_prompt"),
            text=self._current_image.name
        )

        if ok and name.strip():
            self._current_image.name = name.strip()
            self.config_db.update_saved_image(self._current_image)
            self.refresh()
            self._show_image_preview(self._current_image)

    def _remove_image(self, image: SavedImage):
        """Remove an image from the library."""
        if not DialogHelper.confirm(
            tr("image_confirm_remove", name=image.name) + "\n\n" +
            tr("image_files_not_deleted"),
            parent=self
        ):
            return

        self.config_db.delete_saved_image(image.id)
        self._current_image = None
        self.content_stack.setCurrentIndex(0)
        self.refresh()

    def _manage_categories(self):
        """Manage categories for the current image."""
        if not self._current_image:
            return

        current_categories = self.config_db.get_image_categories(self._current_image.id)
        all_categories = self.config_db.get_all_image_category_names()

        # Simple dialog for now - comma-separated input
        current_text = ", ".join(current_categories)
        hint = tr("image_available_hint", list=', '.join(all_categories)) if all_categories else ""

        text, ok = QInputDialog.getText(
            self,
            tr("image_manage_categories_title"),
            tr("image_manage_categories_prompt") + f"\n{hint}",
            text=current_text
        )

        if ok:
            new_categories = [c.strip() for c in text.split(",") if c.strip()]
            self.config_db.set_image_categories(self._current_image.id, new_categories)
            self.refresh()
            self._show_image_preview(self._current_image)

    def _manage_tags(self):
        """Manage tags for the current image."""
        if not self._current_image:
            return

        current_tags = self.config_db.get_image_tags(self._current_image.id)
        all_tags = self.config_db.get_all_image_tag_names()

        # Simple dialog for now - comma-separated input
        current_text = ", ".join(current_tags)
        hint = tr("image_existing_tags_hint", list=', '.join(all_tags)) if all_tags else ""

        text, ok = QInputDialog.getText(
            self,
            tr("image_manage_tags_title"),
            tr("image_manage_tags_prompt") + f"\n{hint}",
            text=current_text
        )

        if ok:
            new_tags = [t.strip() for t in text.split(",") if t.strip()]
            self.config_db.set_image_tags(self._current_image.id, new_tags)
            self.refresh()
            self._show_image_preview(self._current_image)

    # ==================== Search ====================

    def _perform_search(self):
        """Perform image search."""
        query = self.search_input.text().strip()
        if not query:
            self.refresh()
            return

        # Search with selected filters
        results = self.config_db.search_images(
            query,
            search_name=self.search_name_cb.isChecked(),
            search_categories=self.search_category_cb.isChecked(),
            search_tags=self.search_tag_cb.isChecked()
        )

        # Display results
        self.tree.clear()
        self._tree_items.clear()

        results_item = QTreeWidgetItem(self.tree, ["🔍 " + tr("image_search_results", count=len(results))])
        results_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "search_results"})
        results_item.setExpanded(True)

        for img in results:
            self._add_image_to_tree(img, results_item)

        # Add "Clear search" item
        clear_item = QTreeWidgetItem(results_item, ["✕ " + tr("image_clear_search")])
        clear_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "clear_search"})
        clear_item.setForeground(0, Qt.GlobalColor.gray)
