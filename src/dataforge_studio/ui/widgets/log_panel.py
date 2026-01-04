"""
Log Panel - Reusable log panel with filtering
Provides colored log output with optional level filtering
"""

import logging
from typing import Optional, Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QCheckBox
from PySide6.QtGui import QTextCursor, QColor
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class LogPanel(QWidget):
    """
    Reusable log panel with filtering.

    Provides a text area for displaying log messages with optional
    filtering by log level (INFO, WARNING, ERROR, IMPORTANT).

    Features:
    - Colored messages based on level (from theme)
    - Optional checkboxes to filter log levels
    - Auto-scroll to bottom on new messages
    - Theme-aware (updates colors when theme changes)
    """

    def __init__(self, parent: Optional[QWidget] = None, with_filters: bool = True):
        """
        Initialize log panel.

        Args:
            parent: Parent widget (optional)
            with_filters: Whether to show filter checkboxes (default: True)
        """
        super().__init__(parent)
        self.with_filters = with_filters

        # Color mapping - will be loaded from theme
        self.colors: Dict[str, QColor] = {}

        self._setup_ui()
        self._load_theme_colors()
        self._register_theme_observer()

    def _load_theme_colors(self):
        """Load colors from current theme."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            theme_colors = theme.get_theme_colors()

            # Map log levels to theme colors
            self.colors = {
                "INFO": QColor(theme_colors.get("log_info", "#3498db")),
                "WARNING": QColor(theme_colors.get("log_warning", "#f39c12")),
                "ERROR": QColor(theme_colors.get("log_error", "#e74c3c")),
                "IMPORTANT": QColor(theme_colors.get("log_important", "#9b59b6")),
                "DEBUG": QColor(theme_colors.get("log_debug", "#808080"))
            }

            # Apply background from log_bg theme color
            log_bg = theme_colors.get("log_bg", "#2d2d2d")
            log_fg = theme_colors.get("normal_fg", "#ffffff")
            self.log_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {log_bg};
                    color: {log_fg};
                    border: none;
                    font-family: Consolas;
                    font-size: 9pt;
                }}
            """)

        except Exception as e:
            # Fallback to default colors if theme not available
            self.colors = {
                "INFO": QColor("#3498db"),
                "WARNING": QColor("#f39c12"),
                "ERROR": QColor("#e74c3c"),
                "IMPORTANT": QColor("#9b59b6"),
                "DEBUG": QColor("#808080")
            }

    def _register_theme_observer(self):
        """Register as observer for theme changes."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            theme.register_observer(self._on_theme_changed)
        except Exception:
            pass

    def _on_theme_changed(self, theme_colors: Dict[str, str]):
        """
        Called when theme changes.

        Args:
            theme_colors: New theme colors dict
        """
        # Reload colors
        self._load_theme_colors()

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

            self.important_cb = QCheckBox("IMPORTANT")
            self.important_cb.setChecked(True)

            filter_layout.addWidget(self.info_cb)
            filter_layout.addWidget(self.warning_cb)
            filter_layout.addWidget(self.error_cb)
            filter_layout.addWidget(self.important_cb)
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
            level: Log level ("INFO", "WARNING", "ERROR", "IMPORTANT", "DEBUG")
        """
        # Check if level is filtered
        if self.with_filters:
            if level == "INFO" and not self.info_cb.isChecked():
                return
            if level == "WARNING" and not self.warning_cb.isChecked():
                return
            if level == "ERROR" and not self.error_cb.isChecked():
                return
            if level == "IMPORTANT" and not self.important_cb.isChecked():
                return

        # Get color for this level
        color = self.colors.get(level.upper(), QColor("white"))

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

    def add_important(self, message: str):
        """
        Add IMPORTANT level message.

        Args:
            message: Message text
        """
        self.add_message(message, "IMPORTANT")

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
            logger.error(f"Error saving log to file: {e}")

    def apply_theme_style(self, stylesheet: str):
        """
        Apply QSS stylesheet to the log text area.

        Args:
            stylesheet: QSS stylesheet string
        """
        self.log_text.setStyleSheet(stylesheet)
