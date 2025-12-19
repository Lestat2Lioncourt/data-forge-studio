"""
Image Fullscreen Dialog - Detached window for viewing images in fullscreen
"""

from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QKeyEvent

from ...database.config_db import SavedImage


class ImageFullscreenDialog(QDialog):
    """
    Fullscreen dialog for viewing images.

    Features:
    - Large image preview
    - Navigation with arrow keys (←/→)
    - Escape key to close
    - Navigation buttons
    """

    image_changed = Signal(object)  # SavedImage

    def __init__(self, parent=None, image: Optional[SavedImage] = None,
                 image_list: Optional[List[SavedImage]] = None):
        """
        Initialize the fullscreen dialog.

        Args:
            parent: Parent widget
            image: Current image to display
            image_list: List of images for navigation
        """
        super().__init__(parent)

        self.current_image = image
        self.image_list = image_list or ([image] if image else [])
        self.current_index = 0

        # Find current image index in list
        if image and self.image_list:
            for i, img in enumerate(self.image_list):
                if img.id == image.id:
                    self.current_index = i
                    break

        self.setWindowTitle("Image Viewer")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(800, 600)

        self._setup_ui()

        if image:
            self._display_image(image)

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Top toolbar
        toolbar = QHBoxLayout()

        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self._go_previous)
        toolbar.addWidget(self.prev_btn)

        self.counter_label = QLabel()
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.counter_label, stretch=1)

        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._go_next)
        toolbar.addWidget(self.next_btn)

        layout.addLayout(toolbar)

        # Image name
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(self.name_label)

        # Image preview area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background-color: #1a1a1a; border: none; }")

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("QLabel { background-color: #1a1a1a; }")
        scroll_area.setWidget(self.preview_label)

        layout.addWidget(scroll_area, stretch=1)

        # Bottom bar with info
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(self.info_label)

        # Help text
        help_label = QLabel("← → : Navigate  |  Esc : Close  |  F11 : Toggle Fullscreen")
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(help_label)

        self._update_navigation_buttons()

    def _display_image(self, image: SavedImage):
        """Display an image."""
        self.current_image = image

        filepath = Path(image.filepath)
        self.name_label.setText(image.name)

        if not filepath.exists():
            self.preview_label.setText(f"File not found:\n{image.filepath}")
            self.preview_label.setStyleSheet("QLabel { color: red; background-color: #1a1a1a; }")
            self.info_label.setText("")
            return

        pixmap = QPixmap(str(filepath))
        if pixmap.isNull():
            self.preview_label.setText("Cannot load image")
            self.preview_label.setStyleSheet("QLabel { color: red; background-color: #1a1a1a; }")
            self.info_label.setText("")
            return

        # Scale to fit the available space
        available_size = self.preview_label.parent().size()
        scaled = pixmap.scaled(
            available_size.width() - 20,
            available_size.height() - 20,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setStyleSheet("QLabel { background-color: #1a1a1a; }")

        # Update info
        size_bytes = filepath.stat().st_size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

        self.info_label.setText(
            f"{pixmap.width()} x {pixmap.height()} px  |  {size_str}  |  {filepath.suffix.upper()}"
        )

        self._update_navigation_buttons()
        self.image_changed.emit(image)

    def _update_navigation_buttons(self):
        """Update navigation button states."""
        count = len(self.image_list)
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < count - 1)

        if count > 0:
            self.counter_label.setText(f"{self.current_index + 1} / {count}")
        else:
            self.counter_label.setText("")

    def _go_previous(self):
        """Go to previous image."""
        if self.current_index > 0:
            self.current_index -= 1
            self._display_image(self.image_list[self.current_index])

    def _go_next(self):
        """Go to next image."""
        if self.current_index < len(self.image_list) - 1:
            self.current_index += 1
            self._display_image(self.image_list[self.current_index])

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Left:
            self._go_previous()
        elif event.key() == Qt.Key.Key_Right:
            self._go_next()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Handle resize to rescale image."""
        super().resizeEvent(event)
        if self.current_image:
            # Redisplay to rescale
            self._display_image(self.current_image)

    def showFullScreen(self):
        """Show in fullscreen mode."""
        super().showFullScreen()

    def showMaximized(self):
        """Show maximized."""
        super().showMaximized()
        if self.current_image:
            self._display_image(self.current_image)
