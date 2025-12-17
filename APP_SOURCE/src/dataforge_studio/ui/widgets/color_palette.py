"""
Color Palette Widget - Selectable color grid for theme editor
"""

from typing import List, Optional
from PySide6.QtWidgets import (QWidget, QGridLayout, QPushButton, QHBoxLayout,
                                QVBoxLayout, QColorDialog, QSizePolicy, QApplication)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QCursor


# Default palette colors
DEFAULT_PALETTE = [
    # Dark grays (backgrounds)
    "#1e1e1e", "#252525", "#2b2b2b", "#2d2d2d", "#3d3d3d", "#4d4d4d",
    # Light grays
    "#808080", "#a0a0a0", "#b0b0b0", "#c0c0c0", "#e0e0e0", "#ffffff",
    # Accent colors
    "#0078d7", "#005a9e",
    # Semantic colors
    "#2ecc71", "#27ae60",  # Success/green
    "#f39c12", "#d68910",  # Warning/orange
    "#e74c3c", "#c0392b",  # Error/red
    "#3498db", "#2980b9",  # Info/blue
]


class ColorButton(QPushButton):
    """A button that displays a color and can be selected."""

    # Signal emitted when color is copied to clipboard
    color_copied = Signal(str)

    def __init__(self, color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._color = color
        self._selected = False
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._update_style()

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str):
        self._color = value
        self._update_style()

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        self._update_style()

    def _update_style(self):
        """Update button style based on color and selection state."""
        border = "3px solid #0078d7" if self._selected else "1px solid #505050"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: {border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #0078d7;
            }}
        """)
        self.setToolTip(f"{self._color} (clic droit pour copier)")

    def _show_context_menu(self, pos):
        """Show context menu with copy option."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        copy_action = menu.addAction(f"Copier {self._color}")
        copy_action.triggered.connect(self._copy_color)
        menu.exec(self.mapToGlobal(pos))

    def _copy_color(self):
        """Copy color hex code to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._color)
        self.color_copied.emit(self._color)


class ColorPalette(QWidget):
    """
    A grid of selectable colors for the theme editor.

    Signals:
        color_selected(str): Emitted when a color is selected (hex value)
        color_added(str): Emitted when a new color is added to palette
        color_copied(str): Emitted when a color is copied to clipboard
    """

    color_selected = Signal(str)
    color_added = Signal(str)
    color_copied = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None, colors: Optional[List[str]] = None):
        """
        Initialize color palette.

        Args:
            parent: Parent widget
            colors: List of hex colors (uses DEFAULT_PALETTE if None)
        """
        super().__init__(parent)
        self._colors = list(colors) if colors else list(DEFAULT_PALETTE)
        self._buttons: List[ColorButton] = []
        self._selected_color: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the palette grid UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Color grid
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(4)

        self._populate_grid()
        main_layout.addWidget(self.grid_widget)

        # Add color button
        add_layout = QHBoxLayout()
        add_layout.setContentsMargins(0, 5, 0, 0)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(28, 28)
        self.add_btn.setToolTip("Ajouter une couleur personnalisée")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: 1px dashed #606060;
                border-radius: 4px;
                color: #e0e0e0;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
                border-color: #0078d7;
            }
        """)
        self.add_btn.clicked.connect(self._add_custom_color)

        add_layout.addWidget(self.add_btn)
        add_layout.addStretch()
        main_layout.addLayout(add_layout)

    def _populate_grid(self):
        """Populate the color grid with buttons."""
        # Clear existing
        for btn in self._buttons:
            btn.setParent(None)
        self._buttons.clear()

        # Calculate grid dimensions (6 columns)
        cols = 6
        for i, color in enumerate(self._colors):
            row = i // cols
            col = i % cols
            btn = ColorButton(color)
            btn.clicked.connect(lambda checked, c=color: self._on_color_clicked(c))
            btn.color_copied.connect(self.color_copied.emit)
            self.grid_layout.addWidget(btn, row, col)
            self._buttons.append(btn)

    def _on_color_clicked(self, color: str):
        """Handle color button click."""
        # Deselect previous
        for btn in self._buttons:
            btn.selected = (btn.color == color)

        self._selected_color = color
        self.color_selected.emit(color)

    def _add_custom_color(self):
        """Open color dialog to add a custom color."""
        initial = QColor(self._selected_color) if self._selected_color else QColor("#808080")
        color = QColorDialog.getColor(initial, self, "Choisir une couleur")

        if color.isValid():
            hex_color = color.name()
            # Add to palette if not already present
            if hex_color not in self._colors:
                self._colors.append(hex_color)
                self._populate_grid()
                self.color_added.emit(hex_color)

            # Select the new color
            self._on_color_clicked(hex_color)

    def get_selected_color(self) -> Optional[str]:
        """Get currently selected color."""
        return self._selected_color

    def set_selected_color(self, color: str):
        """Set the selected color programmatically."""
        if color:
            # If color not in palette, add it
            if color not in self._colors:
                self._colors.append(color)
                self._populate_grid()
            self._on_color_clicked(color)

    def get_colors(self) -> List[str]:
        """Get all colors in the palette."""
        return list(self._colors)

    def set_colors(self, colors: List[str]):
        """Set the palette colors."""
        self._colors = list(colors)
        self._populate_grid()
