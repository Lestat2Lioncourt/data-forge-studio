"""
Collapsible Section Widget
A container widget with a clickable header that expands/collapses its content.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from ..core.theme_bridge import ThemeBridge
from ...utils.image_loader import get_icon


class CollapsibleSection(QWidget):
    """
    A collapsible section with a header and content area.

    The header is clickable and shows an expand/collapse arrow.
    The content area can contain any widget (typically a tree view).
    """

    # Signal emitted when section is expanded/collapsed
    toggled = Signal(bool)  # True = expanded, False = collapsed

    def __init__(self, title: str, icon_name: str = None, parent: QWidget = None):
        """
        Initialize collapsible section.

        Args:
            title: Section title displayed in header
            icon_name: Optional icon name for the section
            parent: Parent widget
        """
        super().__init__(parent)
        self._title = title
        self._icon_name = icon_name
        self._is_expanded = True
        self._content_widget = None

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header frame (clickable)
        self._header = QFrame()
        self._header.setObjectName("collapsible_header")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setFixedHeight(28)
        self._header.mousePressEvent = self._on_header_click

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(6)

        # Arrow indicator
        self._arrow_label = QLabel()
        self._arrow_label.setFixedSize(16, 16)
        self._update_arrow()
        header_layout.addWidget(self._arrow_label)

        # Icon (optional)
        if self._icon_name:
            self._icon_label = QLabel()
            self._icon_label.setFixedSize(16, 16)
            icon = get_icon(self._icon_name)
            if icon:
                self._icon_label.setPixmap(icon.pixmap(16, 16))
            header_layout.addWidget(self._icon_label)

        # Title
        self._title_label = QLabel(self._title)
        self._title_label.setObjectName("collapsible_title")
        font = self._title_label.font()
        font.setBold(True)
        self._title_label.setFont(font)
        header_layout.addWidget(self._title_label)

        # Count label (will be updated when content is set)
        self._count_label = QLabel("")
        self._count_label.setObjectName("collapsible_count")
        header_layout.addWidget(self._count_label)

        header_layout.addStretch()

        layout.addWidget(self._header)

        # Content container
        self._content_container = QWidget()
        self._content_container.setObjectName("collapsible_content")
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        layout.addWidget(self._content_container)

    def _on_header_click(self, event):
        """Handle header click to toggle expand/collapse."""
        self.toggle()

    def toggle(self):
        """Toggle the expanded/collapsed state."""
        self._is_expanded = not self._is_expanded
        self._content_container.setVisible(self._is_expanded)
        self._update_arrow()
        self.toggled.emit(self._is_expanded)

    def expand(self):
        """Expand the section."""
        if not self._is_expanded:
            self.toggle()

    def collapse(self):
        """Collapse the section."""
        if self._is_expanded:
            self.toggle()

    def is_expanded(self) -> bool:
        """Return whether the section is expanded."""
        return self._is_expanded

    def _update_arrow(self):
        """Update the arrow indicator based on expanded state."""
        # Use unicode arrows for simplicity
        arrow = "▼" if self._is_expanded else "►"
        self._arrow_label.setText(arrow)

    def set_content(self, widget: QWidget):
        """
        Set the content widget for this section.

        Args:
            widget: Widget to display in the content area
        """
        # Remove old content if any
        if self._content_widget:
            self._content_layout.removeWidget(self._content_widget)

        self._content_widget = widget
        self._content_layout.addWidget(widget)

    def set_count(self, count: int):
        """
        Set the item count displayed in the header.

        Args:
            count: Number of items
        """
        self._count_label.setText(f"({count})")

    def set_title(self, title: str):
        """
        Set the section title.

        Args:
            title: New title
        """
        self._title = title
        self._title_label.setText(title)

    def _apply_theme(self):
        """Apply theme colors to the section."""
        colors = ThemeBridge.get_instance().get_theme_colors()

        header_bg = colors.get("panel_bg", "#2d2d2d")
        header_hover = colors.get("item_hover_bg", "#3d3d3d")
        text_color = colors.get("text_color", "#ffffff")
        secondary_text = colors.get("secondary_text", "#888888")
        border_color = colors.get("border_color", "#3d3d3d")

        self._header.setStyleSheet(f"""
            QFrame#collapsible_header {{
                background-color: {header_bg};
                border: 1px solid {border_color};
                border-radius: 3px;
            }}
            QFrame#collapsible_header:hover {{
                background-color: {header_hover};
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
                border: none;
            }}
            QLabel#collapsible_count {{
                color: {secondary_text};
            }}
        """)

        self._content_container.setStyleSheet(f"""
            QWidget#collapsible_content {{
                border-left: 1px solid {border_color};
                margin-left: 8px;
            }}
        """)
