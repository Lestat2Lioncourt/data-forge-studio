"""
PopupWindow - Base class for themed popup windows.

This template provides:
- Frameless window with custom title bar
- Full window controls (minimize, maximize, close)
- Draggable title bar
- Theme-aware colors via ThemeBridge
- Proper border styling
- Content area for subclasses

Usage:
    class MyPopup(PopupWindow):
        def __init__(self, parent=None):
            super().__init__(
                title="My Popup",
                parent=parent,
                width=800,
                height=600,
                show_minimize=True,
                show_maximize=True
            )
            self._setup_content()

        def _setup_content(self):
            layout = QVBoxLayout(self.content_widget)
            # Add your widgets...
"""

from typing import Optional
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from ..window.title_bar import TitleBar

import logging
logger = logging.getLogger(__name__)


class PopupTitleBar(TitleBar):
    """
    Title bar for popup windows.

    Extends TitleBar with optional button visibility.
    """

    def __init__(
        self,
        title: str = "Popup",
        show_minimize: bool = True,
        show_maximize: bool = True,
        parent=None
    ):
        super().__init__(title=title, show_special_button=False, parent=parent)

        # Hide buttons if not needed
        if not show_minimize:
            self.minimize_btn.hide()
        if not show_maximize:
            self.maximize_btn.hide()


class PopupWindow(QMainWindow):
    """
    Base class for themed popup windows.

    Features:
    - Frameless window with custom title bar
    - Optional minimize/maximize buttons
    - Draggable via title bar
    - Theme-aware colors
    - Visible border
    - Automatic theme updates

    Subclasses should add content to self.content_widget.
    """

    # Signal emitted when window is closed
    closed = Signal()

    def __init__(
        self,
        title: str = "Popup",
        parent: Optional[QWidget] = None,
        width: int = 600,
        height: int = 400,
        show_minimize: bool = True,
        show_maximize: bool = True,
        resizable: bool = True
    ):
        super().__init__(parent)

        self._title = title
        self._show_minimize = show_minimize
        self._show_maximize = show_maximize
        self._is_maximized = False
        self._normal_geometry = None

        # Window setup
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        if not resizable:
            self.setFixedSize(width, height)
        else:
            self.setMinimumSize(400, 300)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Title bar
        self.title_bar = PopupTitleBar(
            title=title,
            show_minimize=show_minimize,
            show_maximize=show_maximize
        )
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.maximize_clicked.connect(self._toggle_maximize)
        self._main_layout.addWidget(self.title_bar)

        # Content widget (subclasses add their content here)
        self.content_widget = QWidget()
        self._main_layout.addWidget(self.content_widget, 1)  # stretch=1 to fill space

        # Apply theme
        self._apply_theme()

        # Register for theme updates
        try:
            from ...core.theme_bridge import ThemeBridge
            theme_bridge = ThemeBridge.get_instance()
            theme_bridge.register_observer(self._on_theme_changed)
        except Exception as e:
            logger.debug(f"Could not register theme observer: {e}")

    def _apply_theme(self):
        """Apply theme colors to the window."""
        try:
            from ...core.theme_bridge import ThemeBridge
            theme_bridge = ThemeBridge.get_instance()
            colors = theme_bridge.get_theme_colors()
        except Exception:
            # Fallback colors
            colors = {
                'window_bg': '#1e1e1e',
                'border_color': '#3d3d3d',
                'main_menu_bar_bg': '#2b2b2b',
                'main_menu_bar_fg': '#ffffff',
            }

        # Get colors with fallbacks
        window_bg = colors.get('window_bg', '#1e1e1e')
        border_color = colors.get('border_color', '#3d3d3d')
        titlebar_bg = colors.get('main_menu_bar_bg', '#2b2b2b')
        titlebar_fg = colors.get('main_menu_bar_fg', '#ffffff')
        close_hover = colors.get('selector_close_btn_hover', '#e81123')

        # Apply window style
        self.setStyleSheet(f"""
            QMainWindow {{
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

        # Apply content widget background
        self.content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {window_bg};
            }}
        """)

    def _on_theme_changed(self, colors: dict):
        """Handle theme change."""
        self._apply_theme()

    def _toggle_maximize(self):
        """Toggle between maximized and normal state."""
        if self._is_maximized:
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            self._is_maximized = False
        else:
            self._normal_geometry = self.geometry()
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
            self.setGeometry(screen)
            self._is_maximized = True

    def set_title(self, title: str):
        """Update the window title."""
        self._title = title
        self.title_bar.set_title(title)

    def closeEvent(self, event):
        """Emit closed signal and cleanup."""
        # Unregister theme observer
        try:
            from ...core.theme_bridge import ThemeBridge
            theme_bridge = ThemeBridge.get_instance()
            theme_bridge.unregister_observer(self._on_theme_changed)
        except Exception:
            pass

        self.closed.emit()
        super().closeEvent(event)

    def center_on_screen(self):
        """Center the window on the primary screen."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def center_on_parent(self):
        """Center the window on its parent window."""
        parent = self.parent()
        if parent:
            parent_geo = parent.geometry()
            self.move(
                parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                parent_geo.y() + (parent_geo.height() - self.height()) // 2
            )
        else:
            self.center_on_screen()
