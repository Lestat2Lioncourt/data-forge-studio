"""
Data Lake Frame - Data Lake operations view
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from ..core.i18n_bridge import tr


class DataLakeFrame(QWidget):
    """Data Lake operations frame."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # Simple label for now - will be enhanced in Phase 2
        label = QLabel(tr("menu_data_lake"))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; padding: 40px;")

        layout.addWidget(label)

        # Add info text
        info_label = QLabel("Data Lake operations will be available here.\n\nPhase 2 will add:\n• Toolbar with buttons\n• Log panel\n• Data import/export")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 20px; opacity: 0.7;")

        layout.addWidget(info_label)
