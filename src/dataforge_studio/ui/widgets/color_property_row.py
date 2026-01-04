"""
Color Property Row - Single row widget for editing a color property

Normal mode:
- Click on color button = copy color to clipboard
- Double-click on color button = open color picker

Paste mode (when a palette color is loaded):
- Click on color button = paste the loaded color
- Double-click on color button = open color picker
"""

from typing import Optional
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QLabel,
                               QColorDialog, QApplication)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QCursor, QPixmap, QPainter


class ColorPropertyRow(QWidget):
    """Single row for editing a color property."""

    color_changed = Signal(str, str)  # key, new_color
    color_pasted = Signal(str, str)  # key, pasted_color - emitted when paste mode color is applied
    color_clicked = Signal(str, str)  # key, color - emitted on single click (for copy/paste workflow)

    def __init__(self, key: str, color: str, source: str = None, parent=None):
        super().__init__(parent)
        self.key = key
        self._color = color
        self._source = source  # Disposition vector (e.g., "background", "blend(surface, accent, 0.5)")
        self._paste_color: Optional[str] = None  # Color to paste when in paste mode

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(5)

        # Color button (click = copy/paste, double-click = pick)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(20, 18)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.clicked.connect(self._on_color_btn_clicked)
        self.color_btn.setToolTip("Clic = copier, Double-clic = modifier")
        layout.addWidget(self.color_btn)

        # Key label
        self.key_label = QLabel(key)
        self.key_label.setMinimumWidth(150)
        self.key_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self.key_label)

        # Hex label (clickable to copy)
        self.hex_label = QLabel(color)
        self.hex_label.setFixedWidth(60)
        self.hex_label.setStyleSheet("color: #808080; font-size: 9pt;")
        self.hex_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hex_label.mousePressEvent = self._copy_color
        layout.addWidget(self.hex_label)

        # Source label (shows disposition vector)
        if source:
            self.source_label = QLabel(f"← {source}")
            self.source_label.setStyleSheet("color: #6080a0; font-size: 8pt; font-style: italic;")
            self.source_label.setToolTip(f"Source: {source}")
            layout.addWidget(self.source_label)
        else:
            self.source_label = None

        layout.addStretch()

        # Create brush cursor for paste mode
        self._brush_cursor = self._create_brush_cursor()
        self._normal_cursor = Qt.CursorShape.PointingHandCursor

        self._update_display()

    def _create_brush_cursor(self) -> QCursor:
        """Create a brush/paint cursor for paste mode."""
        size = 20
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw a paint bucket icon
        painter.setPen(QColor("#333333"))
        painter.setBrush(QColor("#FFD700"))  # Gold

        # Bucket body
        painter.drawRect(4, 8, 10, 10)
        # Bucket top/handle
        painter.drawArc(2, 2, 14, 12, 0, 180 * 16)

        painter.end()

        return QCursor(pixmap, 2, 2)

    def set_color(self, color: str):
        """Set the color value."""
        self._color = color
        self._update_display()

    def set_paste_mode(self, color: str):
        """
        Enable paste mode with the given color.
        In paste mode, clicking applies this color instead of copying.
        """
        self._paste_color = color
        self.color_btn.setCursor(self._brush_cursor)
        self.color_btn.setToolTip(f"Clic = appliquer {color}, Double-clic = modifier")
        # Update border to show paste mode is active
        self._update_display()

    def clear_paste_mode(self):
        """Disable paste mode."""
        self._paste_color = None
        self.color_btn.setCursor(self._normal_cursor)
        self.color_btn.setToolTip("Clic = copier, Double-clic = modifier")
        self._update_display()

    @property
    def is_paste_mode(self) -> bool:
        """Check if paste mode is active."""
        return self._paste_color is not None

    def _update_display(self):
        """Update the visual display."""
        border_color = "#404040"
        hover_border = "#0078d7"

        if self._paste_color:
            # In paste mode - show different border style
            border_color = "#2ecc71"
            hover_border = "#27ae60"

        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 1px solid {border_color};
                border-radius: 2px;
            }}
            QPushButton:hover {{ border: 2px solid {hover_border}; }}
        """)
        self.hex_label.setText(self._color)

    def _on_color_btn_clicked(self):
        """Handle click on color button."""
        if hasattr(self, '_click_timer') and self._click_timer.isActive():
            # Double-click detected - open picker
            self._click_timer.stop()
            self._pick_color()
        else:
            # Start timer - if no second click, do action
            self._click_timer = QTimer()
            self._click_timer.setSingleShot(True)
            if self._paste_color:
                self._click_timer.timeout.connect(self._do_paste_color)
            else:
                self._click_timer.timeout.connect(self._do_copy_color)
            self._click_timer.start(250)  # 250ms to detect double-click

    def _do_paste_color(self):
        """Apply the paste color."""
        if self._paste_color:
            old_color = self._color
            self._color = self._paste_color
            self._update_display()

            # Flash feedback
            self.color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._color};
                    border: 2px solid #27ae60;
                    border-radius: 2px;
                }}
            """)
            QTimer.singleShot(300, self._update_display)

            # Emit signals
            self.color_changed.emit(self.key, self._color)
            self.color_pasted.emit(self.key, self._color)

    def _do_copy_color(self):
        """Copy the color to clipboard and emit clicked signal."""
        QApplication.clipboard().setText(self._color)
        # Emit clicked signal for copy/paste workflow
        self.color_clicked.emit(self.key, self._color)
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
        """Open color picker dialog."""
        # Clear paste mode when opening picker
        was_paste_mode = self._paste_color
        self.clear_paste_mode()

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
        """Copy color when clicking hex label."""
        QApplication.clipboard().setText(self._color)
        self.hex_label.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 9pt;")
        QTimer.singleShot(500, lambda: self.hex_label.setStyleSheet("color: #808080; font-size: 9pt;"))
