"""
Toolbar Builder - Fluent API for building toolbars
Eliminates repetitive toolbar creation code
"""

from typing import Callable, Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from pathlib import Path


class ToolbarBuilder:
    """
    Fluent API for building toolbars with buttons.

    Provides a chainable interface for creating consistent toolbars
    across the application. Eliminates the ~150 lines of repetitive
    toolbar creation code from the original codebase.

    Example:
        toolbar = ToolbarBuilder(parent) \\
            .add_button("Refresh", callback, icon="refresh.png") \\
            .add_button("Add", callback) \\
            .add_separator() \\
            .add_button("Delete", callback) \\
            .add_stretch() \\
            .add_button("Settings", callback, side="right") \\
            .build()
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize toolbar builder.

        Args:
            parent: Parent widget (optional)
        """
        self.toolbar = QWidget(parent)
        self.layout = QHBoxLayout(self.toolbar)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(2)

    def add_button(self, text: str, callback: Callable,
                  icon: Optional[str] = None,
                  tooltip: Optional[str] = None,
                  side: str = "left") -> 'ToolbarBuilder':
        """
        Add a button to the toolbar.

        Args:
            text: Button text
            callback: Function to call when clicked
            icon: Optional icon filename (in icons/ directory)
            tooltip: Optional tooltip text
            side: "left" or "right" (default: "left")

        Returns:
            self for chaining
        """
        btn = QPushButton(text)
        btn.clicked.connect(callback)

        if icon:
            icon_path = self._get_icon_path(icon)
            if icon_path and icon_path.exists():
                btn.setIcon(QIcon(str(icon_path)))

        if tooltip:
            btn.setToolTip(tooltip)

        if side == "left":
            self.layout.addWidget(btn)
        else:
            self.layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignRight)

        return self

    def add_separator(self) -> 'ToolbarBuilder':
        """
        Add a vertical separator line.

        Returns:
            self for chaining
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(separator)
        return self

    def add_stretch(self) -> 'ToolbarBuilder':
        """
        Add stretchy space (pushes subsequent items to the right).

        Returns:
            self for chaining
        """
        self.layout.addStretch()
        return self

    def add_widget(self, widget: QWidget, alignment: Optional[Qt.AlignmentFlag] = None) -> 'ToolbarBuilder':
        """
        Add a custom widget to the toolbar.

        Args:
            widget: Widget to add
            alignment: Optional alignment

        Returns:
            self for chaining
        """
        if alignment:
            self.layout.addWidget(widget, 0, alignment)
        else:
            self.layout.addWidget(widget)
        return self

    def add_label(self, text: str, bold: bool = False) -> 'ToolbarBuilder':
        """
        Add a text label to the toolbar.

        Args:
            text: Label text
            bold: Whether to make text bold

        Returns:
            self for chaining
        """
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: bold;")
        self.layout.addWidget(label)
        return self

    def add_spacer(self, width: int = 10) -> 'ToolbarBuilder':
        """
        Add a fixed-width spacer.

        Args:
            width: Spacer width in pixels

        Returns:
            self for chaining
        """
        spacer = QWidget()
        spacer.setFixedWidth(width)
        self.layout.addWidget(spacer)
        return self

    def build(self) -> QWidget:
        """
        Return the built toolbar widget.

        Returns:
            QWidget containing the toolbar
        """
        return self.toolbar

    def _get_icon_path(self, icon_name: str) -> Optional[Path]:
        """
        Get path to icon file.

        Searches in multiple locations:
        1. window_template/icons/
        2. ui/icons/ (if created later)

        Args:
            icon_name: Icon filename

        Returns:
            Path to icon or None if not found
        """
        # Try window_template icons first
        try:
            from ..window_template import get_icon_path
            path = get_icon_path(icon_name)
            if path:
                return Path(path)
        except:
            pass

        # Try ui/icons/
        ui_icons = Path(__file__).parent.parent / "icons" / icon_name
        if ui_icons.exists():
            return ui_icons

        return None
