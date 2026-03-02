"""
File Content Handler - Handles file viewing for ResourcesManager

Manages CSV, Excel, JSON, and text file display in the content panel.
"""

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QTextEdit, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QFont
import re

from ...widgets.custom_datagridview import CustomDataGridView
from ...widgets.form_builder import FormBuilder
from ....core.data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    excel_to_dataframe,
    LARGE_DATASET_THRESHOLD
)

import logging
logger = logging.getLogger(__name__)


class FileContentHandler:
    """
    Handles file content display in ResourcesManager.

    Manages:
    - File viewer stack (grid for data, text for code/config)
    - Encoding detection
    - Large dataset warnings
    - Details panel updates for files
    """

    def __init__(self, parent: QWidget, form_builder: FormBuilder):
        """
        Initialize file content handler.

        Args:
            parent: Parent widget (ResourcesManager)
            form_builder: FormBuilder for details panel updates
        """
        self._parent = parent
        self._form_builder = form_builder

        # Detected file properties
        self._detected_encoding: Optional[str] = None
        self._detected_separator: Optional[str] = None
        self._detected_delimiter: Optional[str] = None

        # Create viewer widgets
        self._setup_viewers()

    def _setup_viewers(self):
        """Create file viewer widgets."""
        # Create file viewer stack (grid for data files, text for others)
        self.file_viewer_stack = QStackedWidget()

        # Grid viewer for CSV, Excel, etc.
        self.file_grid_viewer = CustomDataGridView()
        self.file_viewer_stack.addWidget(self.file_grid_viewer)

        # Text viewer for text files, JSON, etc.
        self.file_text_viewer = QTextEdit()
        self.file_text_viewer.setReadOnly(True)
        self.file_text_viewer.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10pt;
            }
        """)
        self.file_viewer_stack.addWidget(self.file_text_viewer)

        # Welcome/placeholder widget
        file_welcome = QWidget()
        file_welcome_layout = QVBoxLayout(file_welcome)
        file_welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label = QLabel("Double-cliquez sur un fichier pour afficher son contenu")
        welcome_label.setStyleSheet("color: gray; font-size: 11pt;")
        file_welcome_layout.addWidget(welcome_label)
        self.file_viewer_stack.addWidget(file_welcome)

        # Start with welcome widget
        self.file_viewer_stack.setCurrentIndex(2)

    def get_widget(self) -> QStackedWidget:
        """Get the file viewer stack widget to add to content stack."""
        return self.file_viewer_stack

    def load_file(self, file_path: Path) -> bool:
        """
        Load and display file content.

        Args:
            file_path: Path to the file to load

        Returns:
            True if file was loaded successfully
        """
        if not file_path.exists() or not file_path.is_file():
            return False

        ext = file_path.suffix.lower()

        try:
            # CSV files
            if ext == ".csv":
                self._load_csv_file(file_path)

            # Excel files
            elif ext in (".xlsx", ".xls"):
                self._load_excel_file(file_path)

            # JSON files
            elif ext == ".json":
                self._load_json_file(file_path)

            # Log files (with themed coloring)
            elif ext == ".log":
                self._load_log_file(file_path)

            # Text files (py, sql, txt, md, etc.)
            elif ext in (".txt", ".py", ".sql", ".md", ".ini",
                        ".cfg", ".xml", ".html", ".css", ".js"):
                self._load_text_file(file_path)

            else:
                # Unknown type - try as text
                self._load_text_file(file_path)

            return True

        except (OSError, UnicodeDecodeError) as e:
            logger.error(f"Error loading file {file_path}: {e}")
            self.file_text_viewer.setPlainText(f"Erreur lors du chargement: {str(e)}")
            self.file_viewer_stack.setCurrentIndex(1)  # Text viewer
            return False

    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding by trying multiple encodings.

        Returns the encoding name that successfully reads the file.
        """
        # Try common encodings in order of likelihood
        encodings_to_try = [
            'utf-8-sig',  # UTF-8 with BOM (common in Windows)
            'utf-8',      # Standard UTF-8
            'cp1252',     # Windows Western European
            'iso-8859-1', # Latin-1
            'cp850',      # DOS Western European
            'utf-16',     # UTF-16 with BOM
        ]

        # Read raw bytes to check for BOM
        with open(file_path, 'rb') as f:
            raw = f.read(4096)

        # Check for BOM markers
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        elif raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            return 'utf-16'

        # Try each encoding
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()  # Try to read entire file
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue

        # Fallback to latin-1 (never fails)
        return 'iso-8859-1'

    def _load_csv_file(self, file_path: Path):
        """Load CSV file into grid viewer using DataFrame-Pivot pattern."""
        result = csv_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                self.file_text_viewer.setPlainText(f"Erreur: {str(result.error)}")
                self.file_viewer_stack.setCurrentIndex(1)
            return

        # Store detected values for display
        self._detected_encoding = result.source_info.get('encoding')
        self._detected_separator = result.source_info.get('separator')
        self._detected_delimiter = '"'  # pandas default

        df = result.dataframe
        if df is not None and not df.empty:
            self.file_grid_viewer.set_dataframe(df)
            self.file_viewer_stack.setCurrentIndex(0)  # Grid viewer
            self._update_file_details(file_path)
            logger.info(f"CSV loaded: {result.row_count} rows, encoding={self._detected_encoding}")
        else:
            self.file_text_viewer.setPlainText("(Fichier CSV vide)")
            self.file_viewer_stack.setCurrentIndex(1)

    def _load_excel_file(self, file_path: Path):
        """Load Excel file into grid viewer using DataFrame-Pivot pattern."""
        result = excel_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                error_msg = str(result.error)
                if "openpyxl" in error_msg.lower() or "xlrd" in error_msg.lower():
                    self.file_text_viewer.setPlainText(
                        "Module openpyxl non installé.\n"
                        "Installez-le avec: pip install openpyxl"
                    )
                else:
                    self.file_text_viewer.setPlainText(f"Erreur: {error_msg}")
                self.file_viewer_stack.setCurrentIndex(1)
            return

        # Store info for display
        self._detected_encoding = "Excel Binary"
        self._detected_separator = None
        self._detected_delimiter = None

        df = result.dataframe
        if df is not None and not df.empty:
            self.file_grid_viewer.set_dataframe(df)
            self.file_viewer_stack.setCurrentIndex(0)
            sheets = result.source_info.get('available_sheets', [])
            logger.info(f"Excel loaded: {result.row_count} rows, sheets={sheets}")
        else:
            self.file_text_viewer.setPlainText("(Fichier Excel vide)")
            self.file_viewer_stack.setCurrentIndex(1)

    def _load_json_file(self, file_path: Path):
        """Load JSON file - try as table first, fallback to formatted text."""
        import json

        # First, try loading as tabular data
        result = json_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        # Store encoding info
        self._detected_encoding = result.source_info.get('encoding', 'utf-8')
        self._detected_separator = None
        self._detected_delimiter = None

        # If successfully loaded as table with multiple rows, show in grid
        if result.success and result.dataframe is not None and len(result.dataframe) > 1:
            df = result.dataframe
            self.file_grid_viewer.set_dataframe(df)
            self.file_viewer_stack.setCurrentIndex(0)  # Grid viewer
            self._update_file_details(file_path)
            logger.info(f"JSON loaded as table: {result.row_count} rows")
            return

        # Fallback: display as formatted JSON text
        encoding = self._detect_encoding(file_path)
        self._detected_encoding = encoding

        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        try:
            data = json.loads(content)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.file_text_viewer.setPlainText(formatted)
        except json.JSONDecodeError:
            self.file_text_viewer.setPlainText(content)

        self.file_viewer_stack.setCurrentIndex(1)  # Text viewer
        self._update_file_details(file_path)

    def _load_text_file(self, file_path: Path):
        """Load text file into text viewer with proper encoding detection."""
        encoding = self._detect_encoding(file_path)
        self._detected_encoding = encoding
        self._detected_separator = None
        self._detected_delimiter = None

        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        self.file_text_viewer.setPlainText(content)
        self.file_viewer_stack.setCurrentIndex(1)  # Text viewer
        self._update_file_details(file_path)

    def _load_log_file(self, file_path: Path):
        """Load log file with themed coloring based on log levels."""
        encoding = self._detect_encoding(file_path)
        self._detected_encoding = encoding
        self._detected_separator = None
        self._detected_delimiter = None

        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()

        # Get theme colors for log levels
        log_colors = self._get_log_colors()

        # Clear and prepare text viewer
        self.file_text_viewer.clear()
        self.file_text_viewer.setFont(QFont("Consolas", 10))

        # Pattern to detect log level in a line
        # Matches: [INFO], [WARNING], INFO:, WARNING -, etc.
        level_pattern = re.compile(
            r'\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|SUCCESS|FATAL)\b',
            re.IGNORECASE
        )

        # Process each line with appropriate color
        cursor = self.file_text_viewer.textCursor()
        for line in lines:
            # Detect log level
            match = level_pattern.search(line)
            if match:
                level = match.group(1).upper()
                # Normalize WARN -> WARNING, FATAL -> CRITICAL
                if level == "WARN":
                    level = "WARNING"
                elif level == "FATAL":
                    level = "CRITICAL"
                color = log_colors.get(level, log_colors.get("INFO"))
            else:
                # Default color for lines without level
                color = log_colors.get("INFO")

            # Create format with color
            fmt = QTextCharFormat()
            fmt.setForeground(color)

            # Insert line with color
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(line, fmt)

        self.file_viewer_stack.setCurrentIndex(1)  # Text viewer
        self._update_file_details(file_path)

    def _get_log_colors(self) -> dict:
        """Get themed colors for log levels."""
        try:
            from ...core.theme_bridge import ThemeBridge
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
        except Exception:
            # Fallback colors
            return {
                "DEBUG": QColor("#888888"),
                "INFO": QColor("#ffffff"),
                "WARNING": QColor("#ffa500"),
                "ERROR": QColor("#ff4444"),
                "CRITICAL": QColor("#ff4444"),
                "SUCCESS": QColor("#4ade80"),
            }

    def _update_file_details(self, file_path: Path):
        """Update the details panel with file info including encoding."""
        try:
            stat = file_path.stat()

            # Format size
            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.2f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

            file_type = file_path.suffix.upper()[1:] if file_path.suffix else "File"

            # Format modified date
            from datetime import datetime
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

            # Update details form
            self._form_builder.set_value("name", file_path.name)
            self._form_builder.set_value("resource_type", f"{file_type} ({size_str})")
            self._form_builder.set_value("description", f"Modified: {modified}")
            self._form_builder.set_value("path", str(file_path))

            # Show encoding
            encoding_display = self._detected_encoding.upper() if self._detected_encoding else "-"
            self._form_builder.set_value("encoding", encoding_display)

            # Show separator (with friendly names)
            separator_names = {
                ',': 'Comma (,)',
                ';': 'Semicolon (;)',
                '\t': 'Tab (\\t)',
                '|': 'Pipe (|)',
                ' ': 'Space',
            }
            if self._detected_separator:
                sep_display = separator_names.get(
                    self._detected_separator, f"'{self._detected_separator}'"
                )
            else:
                sep_display = "-"
            self._form_builder.set_value("separator", sep_display)

            # Show delimiter (quote character)
            delimiter_names = {
                '"': 'Double quote (")',
                "'": "Single quote (')",
            }
            if self._detected_delimiter:
                delim_display = delimiter_names.get(
                    self._detected_delimiter, f"'{self._detected_delimiter}'"
                )
            else:
                delim_display = "-"
            self._form_builder.set_value("delimiter", delim_display)

        except Exception as e:
            logger.error(f"Error updating file details: {e}")

    def _handle_large_dataset_warning(self, row_count: int) -> bool:
        """
        Handle warning for large datasets (> 100k rows).

        Args:
            row_count: Number of rows detected

        Returns:
            True to proceed with loading, False to cancel
        """
        # Format numbers with thousands separator
        row_count_fmt = f"{row_count:,}"
        threshold_fmt = f"{LARGE_DATASET_THRESHOLD:,}"

        msg = QMessageBox(self._parent)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Large Dataset Warning")
        msg.setText(f"This file contains {row_count_fmt} rows.")
        msg.setInformativeText(
            f"Loading more than {threshold_fmt} rows may:\n"
            f"• Be slow to load\n"
            f"• Consume significant memory\n"
            f"• Slow down the interface\n\n"
            f"Do you want to continue?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        result = msg.exec()
        return result == QMessageBox.StandardButton.Yes

    def update_details_for_item(self, item_data: dict):
        """
        Update details panel for a file/folder item.

        Args:
            item_data: Tree item data dictionary
        """
        item_type = item_data.get("type", "")
        path_str = item_data.get("path", "")
        obj = item_data.get("obj")

        if item_type == "rootfolder" and obj:
            # Root folder from database
            name = getattr(obj, "name", "") or Path(path_str).name
            self._form_builder.set_value("name", name)
            self._form_builder.set_value("resource_type", "Root Folder")
            self._form_builder.set_value("description", getattr(obj, "description", "") or "")
            self._form_builder.set_value("path", getattr(obj, "path", path_str))
            self._form_builder.set_value("encoding", "-")
            self._form_builder.set_value("separator", "-")
            self._form_builder.set_value("delimiter", "-")

        elif path_str:
            # File or folder from filesystem
            file_path = Path(path_str)
            if file_path.exists():
                try:
                    stat = file_path.stat()

                    # Format size
                    if file_path.is_file():
                        size_bytes = stat.st_size
                        if size_bytes < 1024:
                            size_str = f"{size_bytes} B"
                        elif size_bytes < 1024 * 1024:
                            size_str = f"{size_bytes / 1024:.2f} KB"
                        else:
                            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
                        file_type = file_path.suffix.upper()[1:] if file_path.suffix else "File"
                    else:
                        size_str = "-"
                        file_type = "Folder"

                    # Format modified date
                    from datetime import datetime
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                    self._form_builder.set_value("name", file_path.name)
                    self._form_builder.set_value("resource_type", f"{file_type} ({size_str})")
                    self._form_builder.set_value("description", f"Modified: {modified}")
                    self._form_builder.set_value("path", str(file_path))
                    self._form_builder.set_value("encoding", "-")
                    self._form_builder.set_value("separator", "-")
                    self._form_builder.set_value("delimiter", "-")
                except (OSError, UnicodeDecodeError) as e:
                    logger.error(f"Error getting file info: {e}")
