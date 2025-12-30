"""
Distribution Analysis Dialog - Shows statistical analysis of dataset columns
"""

from typing import List, Dict, Any
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QLabel, QTabWidget, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from .custom_datagridview import CustomDataGridView
from ..templates.window.title_bar import TitleBar
from ..core.theme_bridge import ThemeBridge
import logging

logger = logging.getLogger(__name__)


class DistributionAnalysisDialog(QDialog):
    """Dialog showing distribution analysis for dataset columns"""

    def __init__(self, data: List[List[Any]], columns: List[str], db_name: str = None, table_name: str = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.columns = columns
        self.db_name = db_name
        self.table_name = table_name

        # Set frameless window
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(900, 600)

        # Allow window to be deleted when closed (for multiple instances)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Apply theme colors
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()
        window_bg = colors.get('window_bg', '#1e1e1e')
        border_color = colors.get('border_color', '#3d3d3d')

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {window_bg};
                border: 1px solid {border_color};
            }}
        """)

        self._setup_ui()
        self._analyze_data()

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Custom title bar
        if self.db_name and self.table_name:
            title = f"Distribution {self.db_name}.{self.table_name}"
        else:
            title = "Distribution Analysis"
        self.title_bar = TitleBar(title)
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.maximize_clicked.connect(self._toggle_maximize)
        layout.addWidget(self.title_bar)

        # Apply theme to title bar
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()
        title_bar_bg = colors.get('main_menu_bar_bg', '#2b2b2b')
        title_bar_fg = colors.get('main_menu_bar_fg', '#ffffff')
        self.title_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {title_bar_bg};
                color: {title_bar_fg};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {title_bar_fg};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QPushButton#closeButton:hover {{
                background-color: #e81123;
            }}
        """)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Info label
        info_label = QLabel(f"Dataset: {len(self.data)} rows × {len(self.columns)} columns")
        content_layout.addWidget(info_label)

        # Tab widget for different views
        self.tabs = QTabWidget()
        content_layout.addWidget(self.tabs)

        # Statistics tab - using CustomDataGridView
        self.stats_grid = CustomDataGridView()
        self.tabs.addTab(self.stats_grid, "📈 Statistics")

        # Value distribution tab - using CustomDataGridView
        self.value_dist_grid = CustomDataGridView()
        self.tabs.addTab(self.value_dist_grid, "📊 Value Distribution")

        # Apply smaller font size to grids
        smaller_font = QFont()
        smaller_font.setPointSize(9)  # Reduced from default (usually 10-11)
        self.stats_grid.table.setFont(smaller_font)
        self.value_dist_grid.table.setFont(smaller_font)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        content_layout.addWidget(close_btn)

        # Add content widget to main layout
        layout.addWidget(content_widget)

    def _toggle_maximize(self):
        """Toggle between maximized and normal state"""
        if self.isMaximized():
            self.showNormal()
            self.title_bar.update_maximize_button(False)
        else:
            self.showMaximized()
            self.title_bar.update_maximize_button(True)

    def _analyze_data(self):
        """Analyze data and populate tables"""
        if not self.data:
            return

        # Transpose data to work column by column
        column_data = {}
        for col_idx, col_name in enumerate(self.columns):
            column_data[col_name] = [row[col_idx] if col_idx < len(row) else None
                                     for row in self.data]

        # Populate statistics table
        self._populate_statistics(column_data)

        # Populate value distribution table
        self._populate_value_distribution(column_data)

    def _populate_statistics(self, column_data: Dict[str, List[Any]]):
        """Populate statistics table with column analysis (transposed: columns as rows)"""
        stats_columns = [
            "Column Name",
            "Format",
            "Total Values",
            "Non-Null",
            "Null",
            "Unique",
            "Data Type",
            "lMin",
            "lMax",
            "Min",
            "Max",
            "Mean",
            "Median",
            "Std Dev"
        ]

        # Build data rows - one row per data column
        stats_data = []

        for col_name in self.columns:
            values = column_data[col_name]
            row_data = []

            # Column name
            row_data.append(col_name)

            # Non-null values (needed early for format detection)
            non_null = [v for v in values if v is not None and str(v).strip() != '']

            # Data type detection (needed for format)
            data_type = self._detect_data_type(non_null)

            # Format detection
            format_type = self._detect_format(non_null, data_type)
            row_data.append(format_type)

            # Total values
            row_data.append(str(len(values)))

            # Non-null values
            row_data.append(str(len(non_null)))

            # Null values
            null_count = len(values) - len(non_null)
            row_data.append(str(null_count))

            # Unique values
            unique = len(set(str(v) for v in non_null))
            row_data.append(str(unique))

            # Data type
            row_data.append(data_type)

            # Text length statistics (for all types)
            if non_null:
                text_lengths = [len(str(v)) for v in non_null]
                row_data.append(str(min(text_lengths)))  # lMin
                row_data.append(str(max(text_lengths)))  # lMax
            else:
                row_data.extend(["N/A", "N/A"])

            # Numeric statistics (if applicable)
            if data_type == "Numeric":
                try:
                    numeric_values = [float(v) for v in non_null if v is not None]

                    if numeric_values:
                        # Min
                        row_data.append(f"{min(numeric_values):.2f}")
                        # Max
                        row_data.append(f"{max(numeric_values):.2f}")
                        # Mean
                        mean = sum(numeric_values) / len(numeric_values)
                        row_data.append(f"{mean:.2f}")
                        # Median
                        sorted_values = sorted(numeric_values)
                        mid = len(sorted_values) // 2
                        median = sorted_values[mid] if len(sorted_values) % 2 == 1 else \
                                (sorted_values[mid - 1] + sorted_values[mid]) / 2
                        row_data.append(f"{median:.2f}")
                        # Standard Deviation (Écart type)
                        variance = sum((x - mean) ** 2 for x in numeric_values) / len(numeric_values)
                        std_dev = variance ** 0.5
                        row_data.append(f"{std_dev:.2f}")
                    else:
                        row_data.extend(["N/A", "N/A", "N/A", "N/A", "N/A"])
                except (ValueError, TypeError, ZeroDivisionError):
                    row_data.extend(["N/A", "N/A", "N/A", "N/A", "N/A"])
            else:
                # For non-numeric, show first and last values
                if non_null:
                    row_data.append(str(non_null[0])[:50])
                    row_data.append(str(non_null[-1])[:50])
                else:
                    row_data.extend(["N/A", "N/A"])
                row_data.extend(["N/A", "N/A"])

                # Standard Deviation for text (based on text length)
                if non_null:
                    mean_length = sum(text_lengths) / len(text_lengths)
                    variance_length = sum((x - mean_length) ** 2 for x in text_lengths) / len(text_lengths)
                    std_dev_length = variance_length ** 0.5
                    row_data.append(f"{std_dev_length:.2f}")
                else:
                    row_data.append("N/A")

            stats_data.append(row_data)

        # Use CustomDataGridView methods
        self.stats_grid.set_columns(stats_columns)
        self.stats_grid.set_data(stats_data)

    def _populate_value_distribution(self, column_data: Dict[str, List[Any]]):
        """Populate value distribution table showing top values per column (transposed)"""
        max_top_values = 10  # Show top 10 values per column

        # Headers: Column Name + Top 1, Top 2, ... Top 10
        headers = ["Column Name"]
        for i in range(1, max_top_values + 1):
            headers.append(f"Top {i}")

        # Build data rows - one row per data column
        dist_data = []

        for col_name in self.columns:
            values = column_data[col_name]
            non_null = [v for v in values if v is not None and str(v).strip() != '']

            row_data = []

            # Column name
            row_data.append(col_name)

            # Count value frequencies
            from collections import Counter
            value_counts = Counter(str(v) for v in non_null)

            # Get top values
            top_values = value_counts.most_common(max_top_values)

            # Fill top values as "value (count)"
            for value, count in top_values:
                display = f"{value[:50]} ({count})"  # Limit display length
                row_data.append(display)

            # Fill remaining cells with empty if less than max_top_values
            while len(row_data) < len(headers):
                row_data.append("")

            dist_data.append(row_data)

        # Use CustomDataGridView methods
        self.value_dist_grid.set_columns(headers)
        self.value_dist_grid.set_data(dist_data)

    def _detect_data_type(self, values: List[Any]) -> str:
        """Detect the data type of a column"""
        if not values:
            return "Unknown"

        # Try to detect numeric
        numeric_count = 0
        for v in values[:min(100, len(values))]:  # Sample first 100 values
            try:
                float(v)
                numeric_count += 1
            except (ValueError, TypeError):
                pass

        if numeric_count > len(values[:min(100, len(values))]) * 0.8:  # 80% threshold
            return "Numeric"

        # Check for dates (basic check)
        date_indicators = ['/', '-', ':']
        date_count = 0
        for v in values[:min(100, len(values))]:
            str_v = str(v)
            if any(ind in str_v for ind in date_indicators) and len(str_v) > 8:
                date_count += 1

        if date_count > len(values[:min(100, len(values))]) * 0.8:
            return "Date/Time"

        return "Text"

    def _detect_format(self, values: List[Any], data_type: str) -> str:
        """
        Detect the precise format of a column.

        Args:
            values: List of non-null values
            data_type: Detected data type (Numeric, Date/Time, Text)

        Returns:
            Format string (Integer, Decimal, Date, DateTime, Text, etc.)
        """
        if not values:
            return "Unknown"

        if data_type == "Numeric":
            # Check if all numeric values are integers
            integer_count = 0
            for v in values[:min(100, len(values))]:
                try:
                    float_val = float(v)
                    if float_val.is_integer():
                        integer_count += 1
                except (ValueError, TypeError):
                    pass

            if integer_count > len(values[:min(100, len(values))]) * 0.9:  # 90% threshold
                return "Integer"
            else:
                return "Decimal"

        elif data_type == "Date/Time":
            # Check if values contain time component (has ':')
            has_time = any(':' in str(v) for v in values[:min(20, len(values))])
            return "DateTime" if has_time else "Date"

        else:  # Text
            # Check average length to classify
            avg_length = sum(len(str(v)) for v in values[:min(100, len(values))]) / min(100, len(values))
            if avg_length < 10:
                return "Short Text"
            elif avg_length < 50:
                return "Text"
            else:
                return "Long Text"
