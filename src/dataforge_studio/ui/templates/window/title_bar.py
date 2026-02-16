"""Custom title bar with window controls and drag functionality."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QFont, QMouseEvent, QIcon

from .resources import get_icon_path


class TitleBar(QWidget):
    """Custom title bar with app icon/name and window control buttons."""

    # Signals for window controls
    close_clicked = Signal()
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    special_clicked = Signal()  # Toggle right panel split

    def __init__(self, title: str = "Application", show_special_button: bool = False, parent=None):
        super().__init__(parent)
        self.title = title
        self._show_special_button = show_special_button
        self._drag_position = QPoint()
        self._is_dragging = False
        self._click_x_ratio = 0.5

        self.setFixedHeight(40)
        # Enable styled background for QSS to work
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # No hardcoded styles - will be set by theme manager via apply_theme()

        self._setup_ui()

    def _setup_ui(self):
        """Setup the title bar UI components."""
        # Button spacing constant
        BUTTON_SPACING = 0  # Spacing between buttons and right margin

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, BUTTON_SPACING, 0)  # Left margin before icon
        layout.setSpacing(0)  # No extra spacing, controlled by widget sizes

        # App icon (if available) - 40x40 to match title bar height
        from pathlib import Path
        from PySide6.QtGui import QPixmap
        icon_path = Path(__file__).parent.parent.parent / "assets" / "images" / "DataForge-Studio-logo.png"
        if icon_path.exists():
            self.icon_label = QLabel()
            self.icon_label.setObjectName("AppLogoLabel")
            self.icon_label.setStyleSheet("#AppLogoLabel { padding: 0; margin: 0; border: none; background: transparent; }")
            icon_pixmap = QPixmap(str(icon_path))
            if not icon_pixmap.isNull():
                # Scale to fit 32x32
                scaled_icon = icon_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.icon_label.setPixmap(scaled_icon)
                self.icon_label.setFixedSize(32, 32)
                self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.icon_label.setScaledContents(False)
                layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # App title image (or fallback to text)
        title_image_path = Path(__file__).parent.parent.parent / "assets" / "images" / "DataForge-Studio-title.png"
        self.title_label = QLabel()
        if title_image_path.exists():
            title_pixmap = QPixmap(str(title_image_path))
            if not title_pixmap.isNull():
                title_h = 22  # Fit within 40px title bar
                scaled_title = title_pixmap.scaledToHeight(title_h, Qt.TransformationMode.SmoothTransformation)
                self.title_label.setPixmap(scaled_title)
                self.title_label.setFixedSize(scaled_title.width() + 19, scaled_title.height())
                self.title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                self.title_label.setStyleSheet("background: transparent;")
            else:
                self.title_label.setText(self.title)
        else:
            self.title_label.setText(self.title)
            font = QFont()
            font.setPointSize(10)
            self.title_label.setFont(font)
        layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Spacer
        layout.addStretch()

        # Button size constants
        BUTTON_WIDTH = 32  # Compact width
        BUTTON_HEIGHT = 40

        # Special button (optional - toggle split)
        if self._show_special_button:
            self.special_btn = QPushButton("⚡")
            self.special_btn.setObjectName("specialButton")
            self.special_btn.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
            self.special_btn.clicked.connect(self.special_clicked.emit)
            self.special_btn.setToolTip("Toggle panel split")
            self._set_button_icon(self.special_btn, "btn_special.png", "⚡")
            layout.addWidget(self.special_btn)

        # Minimize button
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.minimize_btn.clicked.connect(self.minimize_clicked.emit)
        self._set_button_icon(self.minimize_btn, "btn_minimize.png", "−")
        layout.addWidget(self.minimize_btn)

        # Maximize/Restore button
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.maximize_btn.clicked.connect(self.maximize_clicked.emit)
        self._set_button_icon(self.maximize_btn, "btn_zoom.png", "□")
        layout.addWidget(self.maximize_btn)

        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.close_btn.clicked.connect(self.close_clicked.emit)
        self._set_button_icon(self.close_btn, "btn_close.png", "✕")
        layout.addWidget(self.close_btn)

    def _set_button_icon(self, button: QPushButton, icon_name: str, fallback_text: str):
        """
        Set icon for a button if available, otherwise use fallback text.

        Args:
            button: The button to set icon/text for
            icon_name: Name of the icon file in the icons directory
            fallback_text: Text to use if icon is not available
        """
        icon_path = get_icon_path(icon_name)
        if icon_path:
            button.setIcon(QIcon(icon_path))
            button.setIconSize(QSize(24, 24))  # Larger icons to fill compact buttons
            button.setText("")  # Remove text when icon is present
        else:
            button.setText(fallback_text)

    def set_title(self, title: str):
        """Update the title text."""
        self.title = title
        self.title_label.setText(title)

    def update_maximize_button(self, is_maximized: bool):
        """Update maximize button icon based on window state."""
        # Use btn_zoom.png for both states (can add btn_restore.png later if needed)
        if is_maximized:
            self._set_button_icon(self.maximize_btn, "btn_zoom.png", "❐")
        else:
            self._set_button_icon(self.maximize_btn, "btn_zoom.png", "□")

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            # Store click position relative to title bar (as percentage for restore calculation)
            self._click_x_ratio = event.position().x() / self.width() if self.width() > 0 else 0.5
            self._drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            window = self.window()

            # Check if window is maximized (using custom _is_maximized flag)
            is_maximized = getattr(window, '_is_maximized', False) or window.isMaximized()

            if is_maximized:
                # Get the normal geometry before restoring
                # ResizeWrapper uses _resize_start_geometry, TemplateWindow uses _normal_geometry
                normal_geometry = getattr(window, '_resize_start_geometry', None) or \
                                  getattr(window, '_normal_geometry', None)
                if normal_geometry and normal_geometry.isValid():
                    normal_width = normal_geometry.width()
                else:
                    normal_width = 1200  # Default width

                # Restore window using toggle_maximize if available
                if hasattr(window, 'toggle_maximize'):
                    window.toggle_maximize()
                else:
                    window.showNormal()

                # Calculate new position: cursor should stay at same relative X position
                cursor_pos = event.globalPosition().toPoint()
                new_x = cursor_pos.x() - int(normal_width * self._click_x_ratio)
                new_y = cursor_pos.y() - 20  # Offset for title bar height

                window.move(new_x, new_y)

                # Update drag position for continued dragging
                self._drag_position = cursor_pos - window.frameGeometry().topLeft()
            else:
                window.move(event.globalPosition().toPoint() - self._drag_position)

            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop dragging."""
        self._is_dragging = False
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to maximize/restore window."""
        if event.button() == Qt.LeftButton:
            self.maximize_clicked.emit()
            event.accept()
