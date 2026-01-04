"""
Toolbar Builder - Fluent API for building toolbars
Eliminates repetitive toolbar creation code
"""

from typing import Callable, Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame, QLabel, QSizePolicy
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
        self.toolbar.setObjectName("ToolbarWidget")  # For QSS targeting
        self.layout = QHBoxLayout(self.toolbar)
        # Minimal margins for compact ribbon-like appearance
        self.layout.setContentsMargins(5, 2, 5, 2)
        self.layout.setSpacing(3)

        # Fix toolbar height
        self.toolbar.setMaximumHeight(40)
        self.toolbar.setMinimumHeight(32)

        # Track if stretch was manually added
        self._has_stretch = False

    def add_button(self, text: str, callback: Callable,
                  icon: Optional[str] = None,
                  tooltip: Optional[str] = None,
                  side: str = "left",
                  return_button: bool = False):
        """
        Add a button to the toolbar.

        Args:
            text: Button text
            callback: Function to call when clicked
            icon: Optional icon filename (in icons/ directory)
            tooltip: Optional tooltip text
            side: "left" or "right" (default: "left")
            return_button: If True, returns the QPushButton instead of self

        Returns:
            self for chaining, or QPushButton if return_button=True
        """
        btn = QPushButton(text)
        btn.clicked.connect(callback)

        # Set compact size policy and fixed height for ribbon-like appearance
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setMaximumHeight(28)
        btn.setMinimumHeight(24)

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

        self._last_button = btn
        return btn if return_button else self

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
        self._has_stretch = True
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
        Automatically adds a stretch at the end if not manually added.

        Returns:
            QWidget containing the toolbar
        """
        # Add stretch at the end if not manually added
        # This prevents buttons from stretching to fill width
        if not self._has_stretch:
            self.layout.addStretch()

        return self.toolbar

    def _get_icon_path(self, icon_name: str) -> Optional[Path]:
        """
        Get path to icon file with theme-aware recoloring.

        Uses the theme's icon_color to recolor base icons.
        Falls back to templates/window/icons/ or ui/icons/ if not found.

        Args:
            icon_name: Icon filename

        Returns:
            Path to icon or None if not found
        """
        # Try themed icon first (from assets/icons/base/, recolored)
        # Use toolbar button text color for icon (same color as text)
        try:
            from ..core.theme_bridge import ThemeBridge
            from ..core.theme_image_generator import get_themed_icon_path

            theme_bridge = ThemeBridge.get_instance()
            theme_colors = theme_bridge.get_theme_colors(theme_bridge.current_theme)
            # Use toolbar button fg color for icons (matches text color)
            icon_color = theme_colors.get('toolbarbtn_fg', theme_colors.get('toolbar_button_fg', theme_colors.get('text_primary', '#e0e0e0')))
            is_dark = theme_colors.get('is_dark', True)

            themed_path = get_themed_icon_path(icon_name, is_dark, icon_color)
            if themed_path:
                return Path(themed_path)
        except Exception:
            pass

        # Try templates/window icons
        try:
            from ..templates.window import get_icon_path
            path = get_icon_path(icon_name)
            if path:
                return Path(path)
        except (ImportError, AttributeError):
            pass

        # Try ui/icons/
        ui_icons = Path(__file__).parent.parent / "icons" / icon_name
        if ui_icons.exists():
            return ui_icons

        return None
