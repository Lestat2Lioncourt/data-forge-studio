"""
Help Button Widget - Contextual help button for toolbars.
"""

from typing import Optional, Callable
from PySide6.QtWidgets import QPushButton, QWidget
from PySide6.QtCore import Qt, Signal

from ..core.i18n_bridge import tr
from ...utils.image_loader import get_icon


class HelpButton(QPushButton):
    """
    Small help button [?] for contextual help.

    Can be added to toolbars to provide quick access to relevant documentation.
    """

    # Signal emitted when help is requested
    help_requested = Signal(str)  # topic name

    def __init__(
        self,
        topic: str = "general",
        parent: Optional[QWidget] = None,
        on_click: Optional[Callable] = None
    ):
        """
        Initialize the help button.

        Args:
            topic: Help topic identifier (e.g., "database", "queries")
            parent: Parent widget
            on_click: Optional callback when clicked
        """
        super().__init__(parent)
        self._topic = topic
        self._on_click = on_click

        self._setup_ui()

    def _setup_ui(self):
        """Setup button UI."""
        # Try to use an icon, fallback to text
        icon = get_icon("help.png", size=16) or get_icon("info.png", size=16)
        if icon:
            self.setIcon(icon)
        else:
            self.setText("?")

        self.setToolTip(tr("help_btn_tooltip"))
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Style
        self.setStyleSheet("""
            QPushButton {
                border: 1px solid #555;
                border-radius: 12px;
                background-color: transparent;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #4a9eff;
            }
            QPushButton:pressed {
                background-color: #4a9eff;
            }
        """)

        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        """Handle button click."""
        if self._on_click:
            self._on_click(self._topic)
        self.help_requested.emit(self._topic)

    def set_topic(self, topic: str):
        """Set the help topic."""
        self._topic = topic
