"""
SelectorDialog - Base dialog class with custom title bar for selection interfaces.

This dialog provides:
- Frameless window with custom title bar (close button only)
- Draggable title bar
- Visible border
- Theme-aware colors
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QFont, QMouseEvent, QIcon


class SelectorTitleBar(QWidget):
    """
    Simplified title bar for selector dialogs.

    Only contains:
    - Title text
    - Close button (with red hover effect)

    No minimize/maximize buttons.
    """

    close_clicked = Signal()

    def __init__(self, title: str = "Select", parent=None):
        super().__init__(parent)
        self.title = title
        self._drag_position = QPoint()
        self._is_dragging = False

        self.setFixedHeight(32)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the title bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(5)

        # Title label
        self.title_label = QLabel(self.title)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)

        # Spacer
        layout.addStretch()

        # Close button — use same icon as main TitleBar for consistency
        BUTTON_SIZE = 32
        self.close_btn = QPushButton("\u2715")  # Unicode X fallback
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        self.close_btn.clicked.connect(self.close_clicked.emit)
        self.close_btn.setToolTip("Close")

        # Load btn_close.png from the window template icons
        from ..window.resources import get_icon_path
        icon_path = get_icon_path("btn_close.png")
        if icon_path:
            self.close_btn.setIcon(QIcon(icon_path))
            self.close_btn.setIconSize(QSize(24, 24))
            self.close_btn.setText("")

        layout.addWidget(self.close_btn)

    def set_title(self, title: str):
        """Update the title text."""
        self.title = title
        self.title_label.setText(title)

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


class SelectorDialog(QDialog):
    """
    Base dialog class with custom title bar for selection interfaces.

    Features:
    - FramelessWindowHint (no native window decoration)
    - Simplified title bar with close button only
    - Draggable via title bar
    - Visible border
    - Theme-aware colors

    Usage:
        class MySelectorDialog(SelectorDialog):
            def __init__(self, parent=None):
                super().__init__(title="Select Item", parent=parent)
                # Add your content to self.content_widget
                self._setup_content()

            def _setup_content(self):
                layout = QVBoxLayout(self.content_widget)
                # Add your widgets...
    """

    def __init__(self, title: str = "Select", parent=None, width: int = 500, height: int = 400):
        super().__init__(parent)

        self._title = title

        # Set frameless window
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(width, height)

        # Allow window to be deleted when closed
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Title bar
        self.title_bar = SelectorTitleBar(title)
        self.title_bar.close_clicked.connect(self.close)
        self._main_layout.addWidget(self.title_bar)

        # Content widget (subclasses add their content here)
        self.content_widget = QWidget()
        self._main_layout.addWidget(self.content_widget)

        # Apply theme
        self._apply_theme()

    def _apply_theme(self):
        """Apply theme colors to the dialog."""
        # Try to get colors from ThemeBridge
        try:
            from ...core.theme_bridge import ThemeBridge
            theme_bridge = ThemeBridge.get_instance()
            colors = theme_bridge.get_theme_colors()
        except Exception:
            # Fallback colors
            colors = {
                'window_bg': '#1e1e1e',
                'border_color': '#3d3d3d',
                'selector_titlebar_bg': '#2b2b2b',
                'selector_titlebar_fg': '#ffffff',
                'selector_close_btn_hover': '#e81123',
            }

        # Get colors with fallbacks
        window_bg = colors.get('window_bg', '#1e1e1e')
        border_color = colors.get('selector_border_color', colors.get('border_color', '#3d3d3d'))
        titlebar_bg = colors.get('selector_titlebar_bg', colors.get('main_menu_bar_bg', '#2b2b2b'))
        titlebar_fg = colors.get('selector_titlebar_fg', colors.get('main_menu_bar_fg', '#ffffff'))
        close_hover = colors.get('selector_close_btn_hover', '#e81123')

        # Apply dialog style (border)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {window_bg};
                border: 1px solid {border_color};
            }}
        """)

        # Apply title bar style
        self.title_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {titlebar_bg};
                color: {titlebar_fg};
            }}
            QLabel {{
                color: {titlebar_fg};
                background-color: transparent;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {titlebar_fg};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QPushButton#closeButton:hover {{
                background-color: {close_hover};
                color: white;
            }}
        """)

    def set_title(self, title: str):
        """Update the dialog title."""
        self._title = title
        self.title_bar.set_title(title)
