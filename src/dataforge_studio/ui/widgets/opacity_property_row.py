"""
Opacity Property Row - Widget for editing opacity/transparency values (0-100)
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QSpinBox
from PySide6.QtCore import Qt, Signal


class OpacityPropertyRow(QWidget):
    """Row widget for editing an opacity value (0-100)."""

    value_changed = Signal(str, int)  # key, new_value

    def __init__(self, key: str, value: int, label: str = None, parent=None):
        super().__init__(parent)
        self.key = key
        self._value = max(0, min(100, value))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(10)

        # Label
        self.label = QLabel(label or key)
        self.label.setMinimumWidth(120)
        self.label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self.label)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(self._value)
        self.slider.setMinimumWidth(100)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider, stretch=1)

        # Spinbox
        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, 100)
        self.spinbox.setValue(self._value)
        self.spinbox.setSuffix(" %")
        self.spinbox.setFixedWidth(60)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)
        layout.addWidget(self.spinbox)

    def set_value(self, value: int):
        """Set the opacity value."""
        self._value = max(0, min(100, value))
        self.slider.blockSignals(True)
        self.spinbox.blockSignals(True)
        self.slider.setValue(self._value)
        self.spinbox.setValue(self._value)
        self.slider.blockSignals(False)
        self.spinbox.blockSignals(False)

    def _on_slider_changed(self, value: int):
        """Handle slider change."""
        self._value = value
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(value)
        self.spinbox.blockSignals(False)
        self.value_changed.emit(self.key, value)

    def _on_spinbox_changed(self, value: int):
        """Handle spinbox change."""
        self._value = value
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.value_changed.emit(self.key, value)
