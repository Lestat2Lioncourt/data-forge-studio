"""
FileViewerWidget - Viewer for file content.

Part of the ObjectViewerWidget system for unified object display.

Features:
- Details panel showing file metadata (name, type, size, encoding, etc.)
- Content viewer supporting CSV, JSON, Excel, text, and log files
- View mode switching for JSON (table/raw)
- Large dataset warnings
- Log file syntax highlighting
"""

from pathlib import Path
from typing import Optional, Callable
import re
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStackedWidget, QTextEdit, QComboBox, QMessageBox, QApplication
)
from PySide6.QtGui import QColor, QTextCharFormat, QFont, QCursor
from PySide6.QtCore import Signal, Qt

from .form_builder import FormBuilder
from .custom_datagridview import CustomDataGridView
from .dialog_helper import DialogHelper
from ...utils.file_reader import read_file_content

# DataFrame-Pivot pattern: centralized loading functions
from ...core.data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    excel_to_dataframe,
    DataLoadResult,
    LoadWarningLevel,
    LARGE_DATASET_THRESHOLD
)

logger = logging.getLogger(__name__)


class FileViewerWidget(QWidget):
    """
    Unified file viewer widget.

    Provides:
    - Details panel (top): File metadata
    - Content viewer (bottom): File content display

    Signals:
        file_loaded: Emitted when a file is successfully loaded
    """

    file_loaded = Signal(Path)  # Emitted when file is loaded

    def __init__(self, parent: Optional[QWidget] = None, show_details: bool = True):
        """
        Initialize file viewer.

        Args:
            parent: Parent widget
            show_details: Whether to show the details panel
        """
        super().__init__(parent)

        self.current_file_path: Optional[Path] = None
        self._current_json_content: Optional[str] = None
        self._show_details = show_details

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Details panel (top)
        if self._show_details:
            self.details_form_builder = FormBuilder(title="Details") \
                .add_field("Name:", "name") \
                .add_field("Type:", "type") \
                .add_field("Size:", "size") \
                .add_field("Modified:", "modified") \
                .add_field("Path:", "path") \
                .add_field("Encoding:", "encoding") \
                .add_field("Separator:", "separator") \
                .add_field("Delimiter:", "delimiter")

            details_widget = self.details_form_builder.build()
            layout.addWidget(details_widget, stretch=1)
        else:
            self.details_form_builder = None

        # Content header with view mode toggle
        content_header = QHBoxLayout()
        content_label = QLabel("Content")
        content_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        content_header.addWidget(content_label)

        # View mode toggle (for JSON files)
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItem("Table View", "table")
        self.view_mode_combo.addItem("Raw JSON", "raw")
        self.view_mode_combo.setVisible(False)
        self.view_mode_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        content_header.addWidget(self.view_mode_combo)
        content_header.addStretch()

        layout.addLayout(content_header)

        # Content stack
        self.content_stack = QStackedWidget()

        # Page 0: Grid view (for CSV, JSON table, Excel)
        self.content_viewer = CustomDataGridView()
        self.content_stack.addWidget(self.content_viewer)

        # Page 1: Text view (for raw JSON, text, log files)
        self.text_viewer = QTextEdit()
        self.text_viewer.setReadOnly(True)
        self.content_stack.addWidget(self.text_viewer)

        layout.addWidget(self.content_stack, stretch=4)

    def load_file(self, file_path: Path):
        """
        Load and display a file.

        Args:
            file_path: Path to the file to display
        """
        # Show wait cursor
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        try:
            self.current_file_path = file_path
            extension = file_path.suffix.lower()

            # Show file details
            self._show_file_details(file_path)

            # Read file content
            content = read_file_content(file_path)

            if content is None:
                DialogHelper.warning(f"Cannot read file: {file_path.name}")
                return

            # Display based on type
            if extension == '.csv':
                self.view_mode_combo.setVisible(False)
                self._display_csv(file_path)
            elif extension == '.json':
                self.view_mode_combo.setVisible(True)
                self.view_mode_combo.setCurrentIndex(0)
                self._current_json_content = content
                self._display_json(content)
            elif extension in ['.xlsx', '.xls']:
                self.view_mode_combo.setVisible(False)
                self._display_excel(file_path)
            elif extension == '.log':
                self.view_mode_combo.setVisible(False)
                self._display_log_file(file_path)
            elif extension in ['.txt', '.py', '.sql', '.md', '.ini', '.cfg', '.xml', '.html', '.css', '.js']:
                self.view_mode_combo.setVisible(False)
                self._display_text_file(content)
            else:
                self.view_mode_combo.setVisible(False)
                self._display_text_file(content)

            self.file_loaded.emit(file_path)

        except (OSError, UnicodeDecodeError) as e:
            logger.error(f"Error loading file: {e}")
            DialogHelper.error("Error loading file", details=str(e))

        finally:
            # Restore cursor
            QApplication.restoreOverrideCursor()

    def _show_file_details(self, file_path: Path):
        """Show file details in the details panel."""
        if not self.details_form_builder:
            return

        try:
            stat = file_path.stat()

            # Format size
            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.2f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
            else:
                size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

            # Format modified date
            from datetime import datetime
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            # File type
            file_type = file_path.suffix.upper()[1:] if file_path.suffix else "File"

            # Update details form
            self.details_form_builder.set_value("name", file_path.name)
            self.details_form_builder.set_value("type", file_type)
            self.details_form_builder.set_value("size", size_str)
            self.details_form_builder.set_value("modified", modified)
            self.details_form_builder.set_value("path", str(file_path))

            # Clear CSV-specific fields (will be set by _display_csv)
            self.details_form_builder.set_value("encoding", "-")
            self.details_form_builder.set_value("separator", "-")
            self.details_form_builder.set_value("delimiter", "-")

        except (OSError, UnicodeDecodeError) as e:
            logger.error(f"Error showing file details: {e}")

    def show_folder_details(self, name: str, path: str, modified: str = "-"):
        """
        Show folder/rootfolder details.

        Args:
            name: Folder name
            path: Folder path
            modified: Last modified date string
        """
        if not self.details_form_builder:
            return

        self.details_form_builder.set_value("name", name)
        self.details_form_builder.set_value("type", "Folder")
        self.details_form_builder.set_value("size", "-")
        self.details_form_builder.set_value("modified", modified)
        self.details_form_builder.set_value("path", path)
        self.details_form_builder.set_value("encoding", "-")
        self.details_form_builder.set_value("separator", "-")
        self.details_form_builder.set_value("delimiter", "-")

        # Clear content
        self.clear_content()

    def clear(self):
        """Clear both details and content."""
        if self.details_form_builder:
            self.details_form_builder.clear()
        self.clear_content()

    def clear_content(self):
        """Clear only the content viewer."""
        self.content_viewer.clear()
        self.text_viewer.clear()
        self._current_json_content = None
        self.view_mode_combo.setVisible(False)

    # ==================== Content Display Methods ====================

    def _display_csv(self, file_path: Path):
        """Display CSV content in grid using DataFrame-Pivot pattern."""
        result = csv_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                DialogHelper.error("Error loading CSV", details=str(result.error))
            return

        if result.warning_level == LoadWarningLevel.WARNING and result.warning_message:
            logger.warning(result.warning_message)

        df = result.dataframe
        if df is not None and not df.empty:
            # Update details with CSV-specific info
            encoding = result.source_info.get('encoding', 'unknown')
            separator = result.source_info.get('separator', ',')
            delimiter = result.source_info.get('quotechar', '"')
            sep_display = {',': 'comma', ';': 'semicolon', '\t': 'tab', '|': 'pipe'}.get(separator, separator)
            delim_display = {'"': 'double quote', "'": 'single quote'}.get(delimiter, delimiter)

            if self.details_form_builder:
                self.details_form_builder.set_value("encoding", encoding)
                self.details_form_builder.set_value("separator", sep_display)
                self.details_form_builder.set_value("delimiter", delim_display)

            logger.info(f"CSV loaded: {result.row_count} rows, encoding={encoding}, separator={sep_display}")

            self.content_viewer.set_dataframe(df)
            self.content_stack.setCurrentWidget(self.content_viewer)
        else:
            self.content_viewer.clear()

    def _on_view_mode_changed(self, index: int):
        """Handle view mode change for JSON files."""
        if self._current_json_content is None:
            return

        view_mode = self.view_mode_combo.currentData()

        if view_mode == "table":
            self.content_stack.setCurrentWidget(self.content_viewer)
            self._display_json_table(self._current_json_content)
        elif view_mode == "raw":
            self.content_stack.setCurrentWidget(self.text_viewer)
            self._display_json_raw(self._current_json_content)

    def _display_json(self, content: str):
        """Display JSON content (default to table view)."""
        view_mode = self.view_mode_combo.currentData()

        if view_mode == "raw":
            self.content_stack.setCurrentWidget(self.text_viewer)
            self._display_json_raw(content)
        else:
            self.content_stack.setCurrentWidget(self.content_viewer)
            self._display_json_table(content)

    def _display_json_table(self, content: str):
        """Display JSON content as table in grid."""
        result = json_to_dataframe(
            self.current_file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                self._display_json_table_legacy(content)
            return

        if result.warning_level == LoadWarningLevel.WARNING and result.warning_message:
            logger.warning(result.warning_message)

        df = result.dataframe
        if df is not None and not df.empty:
            logger.info(f"JSON loaded: {result.row_count} rows, {result.column_count} cols")
            self.content_viewer.set_dataframe(df)
        else:
            self._display_json_table_legacy(content)

    def _display_json_table_legacy(self, content: str):
        """Fallback for complex JSON structures."""
        import json

        try:
            data = json.loads(content)

            headers = ["Key", "Value"]
            rows = []

            def flatten_json(obj, prefix=''):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        full_key = f"{prefix}.{key}" if prefix else key
                        if isinstance(value, (dict, list)):
                            flatten_json(value, full_key)
                        else:
                            rows.append([full_key, str(value)])
                elif isinstance(obj, list):
                    for i, value in enumerate(obj):
                        full_key = f"{prefix}[{i}]"
                        if isinstance(value, (dict, list)):
                            flatten_json(value, full_key)
                        else:
                            rows.append([full_key, str(value)])

            flatten_json(data)

            self.content_viewer.set_columns(headers)
            self.content_viewer.set_data(rows)

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error displaying JSON (legacy): {e}")
            DialogHelper.error("Error displaying JSON", details=str(e))

    def _display_json_raw(self, content: str):
        """Display JSON content as formatted raw text."""
        import json

        try:
            data = json.loads(content)
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            self.text_viewer.setPlainText(formatted_json)

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error displaying raw JSON: {e}")
            DialogHelper.error("Error displaying raw JSON", details=str(e))

    def _display_excel(self, file_path: Path):
        """Display Excel content in grid."""
        result = excel_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                DialogHelper.error("Error loading Excel", details=str(result.error))
            return

        if result.warning_level == LoadWarningLevel.WARNING and result.warning_message:
            logger.warning(result.warning_message)

        df = result.dataframe
        if df is not None and not df.empty:
            sheets = result.source_info.get('available_sheets', [])
            current_sheet = result.source_info.get('sheet', 0)
            logger.info(f"Excel loaded: {result.row_count} rows, sheet={current_sheet}, available={sheets}")

            self.content_viewer.set_dataframe(df)
            self.content_stack.setCurrentWidget(self.content_viewer)
        else:
            self.content_viewer.clear()

    def _display_text_file(self, content: str):
        """Display text file content in text viewer."""
        self._apply_text_viewer_theme()
        self.text_viewer.setFont(QFont("Consolas", 10))
        self.text_viewer.setPlainText(content)
        self.content_stack.setCurrentWidget(self.text_viewer)

    def _display_log_file(self, file_path: Path):
        """Display log file with themed coloring based on log levels."""
        content = read_file_content(file_path)
        if content is None:
            self.text_viewer.setPlainText("(Cannot read file)")
            self.content_stack.setCurrentWidget(self.text_viewer)
            return

        lines = content.splitlines(keepends=True)

        log_colors = self._get_log_colors()
        self._apply_text_viewer_theme()

        self.text_viewer.clear()
        self.text_viewer.setFont(QFont("Consolas", 10))

        level_pattern = re.compile(
            r'\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|SUCCESS|FATAL)\b',
            re.IGNORECASE
        )

        cursor = self.text_viewer.textCursor()
        for line in lines:
            match = level_pattern.search(line)
            if match:
                level = match.group(1).upper()
                if level == "WARN":
                    level = "WARNING"
                elif level == "FATAL":
                    level = "CRITICAL"
                color = log_colors.get(level, log_colors.get("INFO"))
            else:
                color = log_colors.get("INFO")

            fmt = QTextCharFormat()
            fmt.setForeground(color)

            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(line, fmt)

        self.content_stack.setCurrentWidget(self.text_viewer)

    def _apply_text_viewer_theme(self):
        """Apply theme colors to the text viewer."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            theme_colors = theme.get_theme_colors()

            log_bg = theme_colors.get("log_bg", theme_colors.get("editor_bg", "#1e1e1e"))
            log_fg = theme_colors.get("log_fg", theme_colors.get("editor_fg", "#d4d4d4"))

            self.text_viewer.setStyleSheet(f"""
                QTextEdit {{
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 10pt;
                    background-color: {log_bg};
                    color: {log_fg};
                }}
            """)
        except Exception as e:
            logger.error(f"Error applying text viewer theme: {e}")
            self.text_viewer.setStyleSheet("""
                QTextEdit {
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 10pt;
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
            """)

    def _get_log_colors(self) -> dict:
        """Get themed colors for log levels."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            theme_colors = theme.get_theme_colors()

            return {
                "DEBUG": QColor(theme_colors.get("log_debug_fg", "#888888")),
                "INFO": QColor(theme_colors.get("log_info_fg", "#ffffff")),
                "WARNING": QColor(theme_colors.get("log_warning_fg", "#ffa500")),
                "ERROR": QColor(theme_colors.get("log_error_fg", "#ff4444")),
                "CRITICAL": QColor(theme_colors.get("log_error_fg", "#ff4444")),
                "SUCCESS": QColor(theme_colors.get("log_success_fg", "#4ade80")),
            }
        except Exception as e:
            logger.error(f"Error loading log colors from theme: {e}")
            return {
                "DEBUG": QColor("#888888"),
                "INFO": QColor("#ffffff"),
                "WARNING": QColor("#ffa500"),
                "ERROR": QColor("#ff4444"),
                "CRITICAL": QColor("#ff4444"),
                "SUCCESS": QColor("#4ade80"),
            }

    def _handle_large_dataset_warning(self, row_count: int) -> bool:
        """Handle warning for large datasets."""
        row_count_fmt = f"{row_count:,}"
        threshold_fmt = f"{LARGE_DATASET_THRESHOLD:,}"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Large Dataset Warning")
        msg.setText(f"This file contains {row_count_fmt} rows.")
        msg.setInformativeText(
            f"Loading more than {threshold_fmt} rows may:\n"
            f"- Be slow to load\n"
            f"- Consume significant memory\n"
            f"- Slow down the interface\n\n"
            f"Do you want to continue?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        result = msg.exec()
        return result == QMessageBox.StandardButton.Yes
