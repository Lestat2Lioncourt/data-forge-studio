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
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QCursor

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
        self._resize_edge = None  # Edge being dragged for resize
        self._resize_start_pos = None
        self._resize_start_geo = None
        self._resize_margin = 6  # Pixels from edge to trigger resize

        # Window setup
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        if not resizable:
            self.setFixedSize(width, height)
        else:
            self.setMinimumSize(400, 300)
            self.setMouseTracking(True)

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

    def _get_resize_edge(self, pos: QPoint) -> Optional[str]:
        """Determine which edge the mouse is near for resizing."""
        rect = self.rect()
        m = self._resize_margin
        edges = []
        if pos.y() <= m:
            edges.append("top")
        if pos.y() >= rect.height() - m:
            edges.append("bottom")
        if pos.x() <= m:
            edges.append("left")
        if pos.x() >= rect.width() - m:
            edges.append("right")
        return "-".join(edges) if edges else None

    def _update_cursor_for_edge(self, edge: Optional[str]):
        """Set the appropriate resize cursor for the given edge."""
        cursor_map = {
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "top-left": Qt.CursorShape.SizeFDiagCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
            "top-right": Qt.CursorShape.SizeBDiagCursor,
            "bottom-left": Qt.CursorShape.SizeBDiagCursor,
        }
        if edge and edge in cursor_map:
            self.setCursor(cursor_map[edge])
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        """Start resize if clicking on an edge."""
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle resize dragging or update cursor."""
        if self._resize_edge and self._resize_start_pos:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geo = QRect(self._resize_start_geo)
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()

            if "right" in self._resize_edge:
                geo.setWidth(max(min_w, self._resize_start_geo.width() + delta.x()))
            if "bottom" in self._resize_edge:
                geo.setHeight(max(min_h, self._resize_start_geo.height() + delta.y()))
            if "left" in self._resize_edge:
                new_w = self._resize_start_geo.width() - delta.x()
                if new_w >= min_w:
                    geo.setLeft(self._resize_start_geo.left() + delta.x())
            if "top" in self._resize_edge:
                new_h = self._resize_start_geo.height() - delta.y()
                if new_h >= min_h:
                    geo.setTop(self._resize_start_geo.top() + delta.y())

            self.setGeometry(geo)
            return

        # Update cursor shape when hovering near edges
        edge = self._get_resize_edge(event.pos())
        self._update_cursor_for_edge(edge)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """End resize."""
        if self._resize_edge:
            self._resize_edge = None
            self._resize_start_pos = None
            self._resize_start_geo = None
            self._update_cursor_for_edge(self._get_resize_edge(event.pos()))
            return
        super().mouseReleaseEvent(event)

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
