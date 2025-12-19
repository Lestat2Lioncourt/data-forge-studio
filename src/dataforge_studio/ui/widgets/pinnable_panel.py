"""
Pinnable Panel - SSMS-style auto-hide panel with pin/unpin functionality

Usage:
    panel = PinnablePanel(title="Explorer", icon="folder.png")
    panel.set_content(my_tree_widget)
    splitter.addWidget(panel)

Behavior:
    - Pinned (default): Panel is always visible, normal docked behavior
    - Unpinned: Panel collapses to a thin tab, slides out on hover/click
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QSizePolicy, QSplitter, QApplication
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QEvent, QSize
)
from PySide6.QtGui import QCursor, QEnterEvent

from ..core.theme_bridge import ThemeBridge
from ...utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


class PinnablePanelHeader(QFrame):
    """Header bar with title and pin button."""

    pin_toggled = Signal(bool)  # True = pinned, False = unpinned

    def __init__(self, title: str, icon_name: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._title = title
        self._icon_name = icon_name
        self._is_pinned = True

        self._setup_ui()
        self._apply_style()

        theme_bridge = ThemeBridge.get_instance()
        theme_bridge.register_observer(self._on_theme_changed)

    def _setup_ui(self):
        """Setup header UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(4)

        # Icon
        if self._icon_name:
            icon = get_icon(self._icon_name, size=16)
            if icon and not icon.isNull():
                icon_label = QLabel()
                icon_label.setPixmap(icon.pixmap(16, 16))
                layout.addWidget(icon_label)

        # Title
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(self._title_label)

        layout.addStretch()

        # Pin button with icon
        self._pin_btn = QPushButton()
        self._pin_btn.setFixedSize(20, 20)
        self._pin_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._pin_btn.clicked.connect(self._toggle_pin)
        self._update_pin_icon()
        layout.addWidget(self._pin_btn)

        self.setFixedHeight(24)

    def _toggle_pin(self):
        """Toggle pin state."""
        self._is_pinned = not self._is_pinned
        self._update_pin_icon()
        self.pin_toggled.emit(self._is_pinned)

    def _update_pin_icon(self):
        """Update pin button icon based on state."""
        from PySide6.QtGui import QTransform, QPixmap

        pin_icon = get_icon("pin", size=16)
        if pin_icon and not pin_icon.isNull():
            if self._is_pinned:
                # Normal icon when pinned
                self._pin_btn.setIcon(pin_icon)
            else:
                # Rotate icon 45° when unpinned to indicate auto-hide mode
                pixmap = pin_icon.pixmap(16, 16)
                transform = QTransform().rotate(45)
                rotated_pixmap = pixmap.transformed(transform)
                from PySide6.QtGui import QIcon
                self._pin_btn.setIcon(QIcon(rotated_pixmap))
            self._pin_btn.setIconSize(QSize(16, 16))

        if self._is_pinned:
            self._pin_btn.setToolTip("Désépingler (auto-masquer)")
        else:
            self._pin_btn.setToolTip("Épingler (toujours visible)")

    def _apply_style(self):
        """Apply themed style."""
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()

        bg = colors.get("sectionheader_bg", "#3c3c3c")
        fg = colors.get("sectionheader_fg", "#ffffff")
        border = colors.get("border_color", "#3d3d3d")
        hover_bg = colors.get("sectionheader_hover_bg", "#4a4a4a")
        selected_bg = colors.get("selected_bg", "#0078d7")

        self.setStyleSheet(f"""
            PinnablePanelHeader {{
                background-color: {bg};
                border-bottom: 1px solid {border};
            }}
            QLabel {{
                color: {fg};
                background: transparent;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
        """)

    def _on_theme_changed(self, colors: dict):
        self._apply_style()

    def is_pinned(self) -> bool:
        return self._is_pinned

    def set_pinned(self, pinned: bool):
        if self._is_pinned != pinned:
            self._is_pinned = pinned
            self._update_pin_icon()


class PinnablePanel(QWidget):
    """
    A panel that can be pinned (always visible) or unpinned (auto-hide).

    When unpinned, the panel collapses to a thin tab.
    Hovering or clicking the tab expands the panel as an overlay.
    """

    pinned_changed = Signal(bool)
    expanded_changed = Signal(bool)

    # Collapsed width (just the tab)
    COLLAPSED_WIDTH = 24

    def __init__(self, title: str = "Panel", icon_name: Optional[str] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._title = title
        self._icon_name = icon_name
        self._is_pinned = True
        self._is_expanded = True
        self._content_widget: Optional[QWidget] = None
        self._normal_width = 250

        # Timer for auto-hide
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._do_collapse)
        self._hide_delay = 400  # ms

        self._setup_ui()
        self._apply_style()

        theme_bridge = ThemeBridge.get_instance()
        theme_bridge.register_observer(self._on_theme_changed)

    def _setup_ui(self):
        """Setup the panel UI."""
        # Main layout - no margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = PinnablePanelHeader(self._title, self._icon_name, self)
        self._header.pin_toggled.connect(self._on_pin_toggled)
        layout.addWidget(self._header)

        # Content container
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        layout.addWidget(self._content_container, stretch=1)

        # Tab indicator (shown when collapsed) - shows >> to indicate expandable
        self._tab_label = QLabel("»")  # Right-pointing double angle quotation mark
        self._tab_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tab_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._tab_label.setFixedWidth(self.COLLAPSED_WIDTH)
        self._tab_label.setToolTip(self._title)  # Show title on hover
        self._tab_label.hide()
        layout.addWidget(self._tab_label, stretch=1)

        self.setMouseTracking(True)

    def _apply_style(self):
        """Apply themed style."""
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()

        bg = colors.get("panel_bg", "#252525")
        border = colors.get("border_color", "#3d3d3d")
        fg = colors.get("foreground", "#ffffff")
        hover_bg = colors.get("selected_bg", "#0078d7")

        self.setStyleSheet(f"""
            PinnablePanel {{
                background-color: {bg};
            }}
        """)

        self._content_container.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
            }}
        """)

        # Use tree text color for better visibility
        tree_fg = colors.get("tree_line1_fg", "#E6E6E6")

        self._tab_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {tree_fg};
                border: 1px solid {border};
                border-left: none;
                font-size: 16px;
                font-weight: bold;
                padding: 4px;
            }}
            QLabel:hover {{
                background-color: {hover_bg};
                color: white;
            }}
        """)

    def _on_theme_changed(self, colors: dict):
        self._apply_style()

    def set_content(self, widget: QWidget):
        """Set the content widget."""
        if self._content_widget:
            self._content_layout.removeWidget(self._content_widget)
            self._content_widget.setParent(None)

        self._content_widget = widget
        self._content_layout.addWidget(widget)

    def set_normal_width(self, width: int):
        """Set the normal expanded width."""
        self._normal_width = width
        if self._is_pinned or self._is_expanded:
            # Update splitter size if inside a splitter
            splitter = self._find_parent_splitter()
            if splitter:
                idx = self._get_splitter_index(splitter)
                if idx >= 0:
                    sizes = splitter.sizes()
                    sizes[idx] = width
                    splitter.setSizes(sizes)

    def _on_pin_toggled(self, is_pinned: bool):
        """Handle pin button toggle."""
        self._is_pinned = is_pinned

        if is_pinned:
            # Pinned: expand and stay visible
            self._expand()
            self._hide_timer.stop()
            # Disconnect splitter signal if connected
            self._disconnect_splitter_signals()
        else:
            # Unpinned: capture current width and setup splitter monitoring
            self._capture_current_width()
            self._connect_splitter_signals()
            # Will collapse when mouse leaves

        self.pinned_changed.emit(is_pinned)

    def _capture_current_width(self):
        """Capture current width from splitter before switching to auto-hide."""
        splitter = self._find_parent_splitter()
        if splitter:
            idx = self._get_splitter_index(splitter)
            if idx >= 0:
                current_width = splitter.sizes()[idx]
                if current_width > self.COLLAPSED_WIDTH:
                    self._normal_width = current_width

    def _connect_splitter_signals(self):
        """Connect to splitter signals to detect resizing."""
        splitter = self._find_parent_splitter()
        if splitter and not hasattr(self, '_splitter_connected'):
            splitter.splitterMoved.connect(self._on_splitter_moved)
            self._splitter_connected = True

    def _disconnect_splitter_signals(self):
        """Disconnect from splitter signals."""
        if hasattr(self, '_splitter_connected') and self._splitter_connected:
            splitter = self._find_parent_splitter()
            if splitter:
                try:
                    splitter.splitterMoved.disconnect(self._on_splitter_moved)
                except RuntimeError:
                    pass
            self._splitter_connected = False

    def _on_splitter_moved(self, pos: int, index: int):
        """Handle splitter resize - pause auto-collapse and update normal width."""
        # Stop any pending collapse
        self._hide_timer.stop()

        # Update normal width if we're expanded
        if self._is_expanded:
            splitter = self._find_parent_splitter()
            if splitter:
                idx = self._get_splitter_index(splitter)
                if idx >= 0:
                    new_width = splitter.sizes()[idx]
                    if new_width > self.COLLAPSED_WIDTH:
                        self._normal_width = new_width

    def _find_parent_splitter(self) -> Optional[QSplitter]:
        """Find the parent QSplitter if any."""
        parent = self.parent()
        while parent:
            if isinstance(parent, QSplitter):
                return parent
            parent = parent.parent()
        return None

    def _get_splitter_index(self, splitter: QSplitter) -> int:
        """Get the index of this widget in the splitter."""
        for i in range(splitter.count()):
            if splitter.widget(i) == self:
                return i
        return -1

    def _expand(self):
        """Expand the panel."""
        if self._is_expanded:
            return

        self._is_expanded = True
        self._header.show()
        self._content_container.show()
        self._tab_label.hide()

        # Reset size constraints
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX

        # Update splitter sizes
        splitter = self._find_parent_splitter()
        if splitter:
            idx = self._get_splitter_index(splitter)
            if idx >= 0:
                sizes = splitter.sizes()
                sizes[idx] = self._normal_width
                splitter.setSizes(sizes)

        self.expanded_changed.emit(True)

    def _do_collapse(self):
        """Collapse the panel to tab."""
        if self._is_pinned or not self._is_expanded:
            return

        # Check if mouse is still over the panel
        if self.underMouse():
            return

        # Check if mouse button is pressed (user might be resizing)
        if QApplication.mouseButtons() != Qt.MouseButton.NoButton:
            # Reschedule collapse check
            self._hide_timer.start(self._hide_delay)
            return

        # Check if mouse is near the splitter handle (grace zone for resizing)
        cursor_pos = QCursor.pos()
        panel_rect = self.rect()
        global_pos = self.mapToGlobal(panel_rect.topLeft())
        right_edge = global_pos.x() + panel_rect.width()
        grace_zone = 15

        if cursor_pos.x() >= right_edge - 5 and cursor_pos.x() <= right_edge + grace_zone:
            # Mouse is near splitter, don't collapse yet
            self._hide_timer.start(self._hide_delay)
            return

        self._is_expanded = False
        self._header.hide()
        self._content_container.hide()
        self._tab_label.show()

        # Set size constraints for collapsed state
        self.setMinimumWidth(self.COLLAPSED_WIDTH)
        self.setMaximumWidth(self.COLLAPSED_WIDTH)

        # Update splitter sizes
        splitter = self._find_parent_splitter()
        if splitter:
            idx = self._get_splitter_index(splitter)
            if idx >= 0:
                sizes = splitter.sizes()
                sizes[idx] = self.COLLAPSED_WIDTH
                splitter.setSizes(sizes)

        self.expanded_changed.emit(False)

    def enterEvent(self, event: QEnterEvent):
        """Mouse entered - stop hide timer and expand if collapsed."""
        self._hide_timer.stop()
        if not self._is_pinned and not self._is_expanded:
            self._expand()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        """Mouse left - start hide timer if unpinned."""
        if not self._is_pinned and self._is_expanded:
            # Check if mouse is near the splitter handle (grace zone)
            # This prevents collapse when trying to resize
            cursor_pos = QCursor.pos()
            panel_rect = self.rect()
            global_rect = self.mapToGlobal(panel_rect.topLeft())

            # Grace zone: 10 pixels beyond the right edge (where splitter handle is)
            grace_zone = 10
            right_edge = global_rect.x() + panel_rect.width()

            if cursor_pos.x() >= right_edge - 5 and cursor_pos.x() <= right_edge + grace_zone:
                # Mouse is near splitter handle, use longer delay
                self._hide_timer.start(self._hide_delay * 3)
            else:
                self._hide_timer.start(self._hide_delay)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle click on collapsed tab."""
        if not self._is_expanded and event.button() == Qt.MouseButton.LeftButton:
            self._expand()
        super().mousePressEvent(event)

    # Public API

    def is_pinned(self) -> bool:
        return self._is_pinned

    def set_pinned(self, pinned: bool):
        if self._is_pinned != pinned:
            self._header.set_pinned(pinned)
            self._on_pin_toggled(pinned)

    def is_expanded(self) -> bool:
        return self._is_expanded

    def expand(self):
        self._expand()

    def collapse(self):
        if not self._is_pinned:
            self._do_collapse()

    def sizeHint(self) -> QSize:
        if self._is_expanded:
            return QSize(self._normal_width, 400)
        else:
            return QSize(self.COLLAPSED_WIDTH, 400)

    def minimumSizeHint(self) -> QSize:
        if self._is_expanded:
            return QSize(self._normal_width, 100)
        else:
            return QSize(self.COLLAPSED_WIDTH, 100)
