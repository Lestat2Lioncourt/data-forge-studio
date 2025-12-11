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

        self.setFixedHeight(40)
        self.setStyleSheet("""
            TitleBar {
                background-color: #2b2b2b;
                border-bottom: 1px solid #3d3d3d;
            }
            QLabel {
                color: #ffffff;
                padding-left: 10px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-size: 16px;
                padding: 0px;
                margin: 0px;
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the title bar UI components."""
        # Button spacing constant
        BUTTON_SPACING = 0  # Spacing between buttons and right margin

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, BUTTON_SPACING, 0)  # Right margin
        layout.setSpacing(BUTTON_SPACING)  # Spacing between buttons

        # App title label
        self.title_label = QLabel(self.title)
        font = QFont()
        font.setPointSize(10)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)

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
            self._drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_position)
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
