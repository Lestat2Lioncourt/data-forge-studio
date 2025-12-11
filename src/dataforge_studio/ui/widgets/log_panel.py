"""
Log Panel - Reusable log panel with filtering
Provides colored log output with optional level filtering
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QCheckBox
from PySide6.QtGui import QTextCursor, QColor
from PySide6.QtCore import Qt


class LogPanel(QWidget):
    """
    Reusable log panel with filtering.

    Provides a text area for displaying log messages with optional
    filtering by log level (INFO, WARNING, ERROR, SUCCESS).

    Features:
    - Colored messages based on level
    - Optional checkboxes to filter log levels
    - Auto-scroll to bottom on new messages
    """

    # Color mapping for different log levels
    COLORS = {
        "INFO": QColor("#ffffff"),      # White
        "WARNING": QColor("#ffa500"),   # Orange
        "ERROR": QColor("#ff4444"),     # Red
        "SUCCESS": QColor("#00ff00"),   # Green
        "DEBUG": QColor("#888888")      # Gray
    }

    def __init__(self, parent: Optional[QWidget] = None, with_filters: bool = True):
        """
        Initialize log panel.

        Args:
            parent: Parent widget (optional)
            with_filters: Whether to show filter checkboxes (default: True)
        """
        super().__init__(parent)
        self.with_filters = with_filters
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Filters (optional)
        if self.with_filters:
            filter_layout = QHBoxLayout()

            self.info_cb = QCheckBox("INFO")
            self.info_cb.setChecked(True)

            self.warning_cb = QCheckBox("WARNING")
            self.warning_cb.setChecked(True)

            self.error_cb = QCheckBox("ERROR")
            self.error_cb.setChecked(True)

            self.success_cb = QCheckBox("SUCCESS")
            self.success_cb.setChecked(True)

            filter_layout.addWidget(self.info_cb)
            filter_layout.addWidget(self.warning_cb)
            filter_layout.addWidget(self.error_cb)
            filter_layout.addWidget(self.success_cb)
            filter_layout.addStretch()

            layout.addLayout(filter_layout)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.log_text)

    def add_message(self, message: str, level: str = "INFO"):
        """
        Add a log message with color based on level.

        Args:
            message: Message text to log
            level: Log level ("INFO", "WARNING", "ERROR", "SUCCESS", "DEBUG")
        """
        # Check if level is filtered
        if self.with_filters:
            if level == "INFO" and not self.info_cb.isChecked():
                return
            if level == "WARNING" and not self.warning_cb.isChecked():
                return
            if level == "ERROR" and not self.error_cb.isChecked():
                return
            if level == "SUCCESS" and not self.success_cb.isChecked():
                return

        # Get color for this level
        color = self.COLORS.get(level.upper(), QColor("white"))

        # Add message with color
        self.log_text.setTextColor(color)
        self.log_text.append(f"[{level}] {message}")

        # Scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def add_info(self, message: str):
        """
        Add INFO level message.

        Args:
            message: Message text
        """
        self.add_message(message, "INFO")

    def add_warning(self, message: str):
        """
        Add WARNING level message.

        Args:
            message: Message text
        """
        self.add_message(message, "WARNING")

    def add_error(self, message: str):
        """
        Add ERROR level message.

        Args:
            message: Message text
        """
        self.add_message(message, "ERROR")

    def add_success(self, message: str):
        """
        Add SUCCESS level message.

        Args:
            message: Message text
        """
        self.add_message(message, "SUCCESS")

    def add_debug(self, message: str):
        """
        Add DEBUG level message.

        Args:
            message: Message text
        """
        self.add_message(message, "DEBUG")

    def clear(self):
        """Clear all log messages."""
        self.log_text.clear()

    def get_text(self) -> str:
        """
        Get all log text.

        Returns:
            Complete log text
        """
        return self.log_text.toPlainText()

    def save_to_file(self, file_path: str):
        """
        Save log content to file.

        Args:
            file_path: Path to save file
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.get_text())
        except Exception as e:
            print(f"Error saving log to file: {e}")

    def apply_theme_style(self, stylesheet: str):
        """
        Apply QSS stylesheet to the log text area.

        Args:
            stylesheet: QSS stylesheet string
        """
        self.log_text.setStyleSheet(stylesheet)
