"""
Palette Widget - Shows unique colors used in theme for quick reuse

Displays a grid of color swatches that can be clicked to copy the color.
"""

from typing import Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal


class PaletteWidget(QWidget):
    """Shows unique colors used in theme for quick reuse."""

    color_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("Palette (couleurs utilisees)")
        title.setStyleSheet("font-weight: bold; font-size: 9pt; color: #808080;")
        layout.addWidget(title)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(3)
        layout.addWidget(self.grid_widget)
        layout.addStretch()

    def update_colors(self, colors_dict: Dict[str, str]):
        """Update palette with unique colors from theme."""
        # Clear grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get unique colors
        unique_colors = sorted(set(v for v in colors_dict.values() if isinstance(v, str) and v.startswith('#')))
        self._colors = unique_colors

        # Create color buttons (6 per row)
        cols = 6
        for i, color in enumerate(unique_colors):
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: 1px solid #404040;
                    border-radius: 2px;
                }}
                QPushButton:hover {{ border: 2px solid #0078d7; }}
            """)
            btn.setToolTip(color)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=color: self.color_selected.emit(c))
            self.grid_layout.addWidget(btn, i // cols, i % cols)
