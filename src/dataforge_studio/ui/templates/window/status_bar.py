"""Status bar component for displaying application status."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class StatusBar(QWidget):
    """Bottom status bar for displaying messages and information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        # Enable styled background for QSS to work
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # No hardcoded styles - will be set by theme manager via apply_theme()

        self._setup_ui()

    def _setup_ui(self):
        """Setup the status bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.status_label, stretch=1)

        # Right status label (optional)
        self.right_label = QLabel("")
        self.right_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.right_label)

    def set_message(self, message: str):
        """Set the main status message."""
        self.status_label.setText(message)

    def set_right_message(self, message: str):
        """Set the right-side status message."""
        self.right_label.setText(message)

    def clear(self):
        """Clear all status messages."""
        self.status_label.setText("Ready")
        self.right_label.setText("")
