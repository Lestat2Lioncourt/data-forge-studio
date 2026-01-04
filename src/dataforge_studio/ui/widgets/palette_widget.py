"""
Palette Widget - Shows palette colors for quick reuse (pipette workflow).

Click on a color to load it (cursor becomes brush), then click on a theme property to apply it.
Click again on the same color or press Escape to cancel.
"""

from typing import Dict, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal


# Palette source keys to display
PALETTE_KEYS = [
    ("background", "Fond"),
    ("surface", "Surface"),
    ("border", "Bordure"),
    ("accent", "Accent"),
    ("text", "Texte"),
    ("text_secondary", "Texte 2"),
    ("icon", "Icône"),
    ("info", "Info"),
    ("warning", "Alerte"),
    ("error", "Erreur"),
    ("important", "Important"),
]


class PaletteWidget(QWidget):
    """Shows palette source colors for quick reuse via pipette workflow."""

    color_selected = Signal(str)  # Emitted when a color is loaded
    color_cleared = Signal()  # Emitted when selection is cleared

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors: Dict[str, str] = {}
        self._loaded_color: Optional[str] = None
        self._color_buttons: Dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(6)

        self.title = QLabel("Palette source")
        self.title.setStyleSheet("font-weight: bold; font-size: 10pt;")
        layout.addWidget(self.title)

        self.subtitle = QLabel("Cliquer pour charger une couleur")
        self.subtitle.setStyleSheet("font-size: 8pt; color: #808080;")
        layout.addWidget(self.subtitle)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(4)

        # Create color buttons for each palette key
        for i, (key, label) in enumerate(PALETTE_KEYS):
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setToolTip(f"{label} - Cliquer pour charger")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._on_color_clicked(k))
            self._color_buttons[key] = btn

            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 9pt;")

            self.grid_layout.addWidget(btn, i, 0)
            self.grid_layout.addWidget(lbl, i, 1)

        layout.addWidget(self.grid_widget)
        layout.addStretch()

    @property
    def loaded_color(self) -> Optional[str]:
        """Get the currently loaded color, or None if no color is loaded."""
        return self._loaded_color

    def clear_loaded_color(self):
        """Clear the loaded color."""
        if self._loaded_color:
            self._loaded_color = None
            self._update_button_styles()
            self.subtitle.setText("Cliquer pour charger une couleur")
            self.subtitle.setStyleSheet("font-size: 8pt; color: #808080;")
            self.color_cleared.emit()

    def update_colors(self, colors_dict: Dict[str, str]):
        """Update palette with colors from theme data."""
        self._colors = {}

        for key, label in PALETTE_KEYS:
            color = colors_dict.get(key, "#808080")
            self._colors[key] = color

        self._update_button_styles()

    def _on_color_clicked(self, key: str):
        """Handle click on a palette color."""
        color = self._colors.get(key, "#808080")

        if self._loaded_color == color:
            # Clicking same color again clears the selection
            self.clear_loaded_color()
        else:
            # Load the new color
            self._loaded_color = color
            self._update_button_styles()
            self.subtitle.setText(f"Chargé: {color}")
            self.subtitle.setStyleSheet("font-size: 8pt; color: #2ecc71; font-weight: bold;")
            self.color_selected.emit(color)

    def _update_button_styles(self):
        """Update button styles to show which color is loaded."""
        for key, btn in self._color_buttons.items():
            color = self._colors.get(key, "#808080")

            if color == self._loaded_color:
                # Selected color - highlight with thick border
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        border: 3px solid #2ecc71;
                        border-radius: 3px;
                    }}
                """)
                btn.setToolTip(f"{color} - CHARGÉ (cliquer pour annuler)")
            else:
                # Normal color
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        border: 1px solid #505050;
                        border-radius: 3px;
                    }}
                    QPushButton:hover {{ border: 2px solid #0078d7; }}
                """)
                btn.setToolTip(f"{color} - Cliquer pour charger")

    def keyPressEvent(self, event):
        """Handle Escape key to clear loaded color."""
        if event.key() == Qt.Key.Key_Escape:
            self.clear_loaded_color()
        else:
            super().keyPressEvent(event)
