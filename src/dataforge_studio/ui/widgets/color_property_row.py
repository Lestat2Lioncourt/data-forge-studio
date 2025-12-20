"""
Color Property Row - Single row widget for editing a color property

Click on color button = copy color to clipboard
Double-click on color button = open color picker
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QLabel,
                               QColorDialog, QApplication)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor


class ColorPropertyRow(QWidget):
    """Single row for editing a color property."""

    color_changed = Signal(str, str)  # key, new_color

    def __init__(self, key: str, color: str, parent=None):
        super().__init__(parent)
        self.key = key
        self._color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(5)

        # Color button (click = copy, double-click = pick)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(20, 18)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.clicked.connect(self._copy_color_from_btn)
        self.color_btn.setToolTip("Clic = copier, Double-clic = modifier")
        layout.addWidget(self.color_btn)

        # Key label
        self.key_label = QLabel(key)
        self.key_label.setMinimumWidth(120)
        self.key_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self.key_label)

        # Hex label (clickable to copy)
        self.hex_label = QLabel(color)
        self.hex_label.setFixedWidth(60)
        self.hex_label.setStyleSheet("color: #808080; font-size: 9pt;")
        self.hex_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hex_label.mousePressEvent = self._copy_color
        layout.addWidget(self.hex_label)

        layout.addStretch()
        self._update_display()

    def set_color(self, color: str):
        self._color = color
        self._update_display()

    def _update_display(self):
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 1px solid #404040;
                border-radius: 2px;
            }}
            QPushButton:hover {{ border: 1px solid #0078d7; }}
        """)
        self.hex_label.setText(self._color)

    def _copy_color_from_btn(self):
        """Handle click on color button - use timer to detect double-click."""
        if hasattr(self, '_click_timer') and self._click_timer.isActive():
            # Double-click detected - open picker
            self._click_timer.stop()
            self._pick_color()
        else:
            # Start timer - if no second click, copy color
            self._click_timer = QTimer()
            self._click_timer.setSingleShot(True)
            self._click_timer.timeout.connect(self._do_copy_color)
            self._click_timer.start(250)  # 250ms to detect double-click

    def _do_copy_color(self):
        """Actually copy the color to clipboard."""
        QApplication.clipboard().setText(self._color)
        # Flash green feedback on the color button
        original_style = self.color_btn.styleSheet()
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 2px solid #2ecc71;
                border-radius: 2px;
            }}
        """)
        QTimer.singleShot(300, lambda: self.color_btn.setStyleSheet(original_style))

    def _pick_color(self):
        # Create dialog with system style (not themed)
        dialog = QColorDialog(QColor(self._color), self)
        dialog.setWindowTitle(f"Couleur: {self.key}")
        # Force native dialog to avoid theme issues
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, False)

        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            self._color = dialog.currentColor().name()
            self._update_display()
            self.color_changed.emit(self.key, self._color)

    def _copy_color(self, event):
        QApplication.clipboard().setText(self._color)
        self.hex_label.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 9pt;")
        QTimer.singleShot(500, lambda: self.hex_label.setStyleSheet("color: #808080; font-size: 9pt;"))
