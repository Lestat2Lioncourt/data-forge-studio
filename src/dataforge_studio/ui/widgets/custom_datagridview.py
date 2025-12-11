"""
Custom Data Grid View - Table widget with sorting, export, and clipboard features
Replaces the 893-line TKinter version with a more compact PySide6 implementation
"""

from typing import List, Optional, Any
from PySide6.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView,
                               QFileDialog, QApplication)
from PySide6.QtCore import Qt, Signal
import csv


class CustomDataGridView(QWidget):
    """
    Custom data grid with sorting, export, and clipboard features.

    Provides a simplified version of the original 893-line TKinter implementation,
    leveraging native QTableWidget capabilities for sorting and selection.

    Signals:
        selection_changed(list): Emitted when selection changes
    """

    # Signals
    selection_changed = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None, show_toolbar: bool = True):
        """
        Initialize custom data grid.

        Args:
            parent: Parent widget (optional)
            show_toolbar: Whether to show the toolbar with export/copy buttons
        """
        super().__init__(parent)
        self.show_toolbar = show_toolbar
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar (optional)
        if self.show_toolbar:
            toolbar_layout = QHBoxLayout()

            self.export_csv_btn = QPushButton("Export CSV")
            self.export_csv_btn.clicked.connect(self._export_csv)
            toolbar_layout.addWidget(self.export_csv_btn)

            self.copy_btn = QPushButton("Copy")
            self.copy_btn.clicked.connect(self._copy_to_clipboard)
            toolbar_layout.addWidget(self.copy_btn)

            toolbar_layout.addStretch()

            layout.addLayout(toolbar_layout)

        # Table widget
        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setVisible(True)  # Show row numbers

        layout.addWidget(self.table)

        # Connect signals
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def set_columns(self, columns: List[str]):
        """
        Set column headers.

        Args:
            columns: List of column names
        """
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

    def set_data(self, data: List[List[Any]]):
        """
        Set grid data.

        Args:
            data: 2D list of data [[row1_col1, row1_col2, ...], [row2_col1, ...], ...]
        """
        self.table.setRowCount(len(data))

        # Temporarily disable sorting while populating
        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
                self.table.setItem(row_idx, col_idx, item)

        # Re-enable sorting
        self.table.setSortingEnabled(sorting_enabled)

        # Auto-resize columns to content (limit to reasonable width)
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount()):
            if self.table.columnWidth(col) > 300:
                self.table.setColumnWidth(col, 300)

    def clear(self):
        """Clear all data from the grid."""
        self.table.clearContents()
        self.table.setRowCount(0)

    def get_row_count(self) -> int:
        """Get number of rows."""
        return self.table.rowCount()

    def get_column_count(self) -> int:
        """Get number of columns."""
        return self.table.columnCount()

    def get_cell_value(self, row: int, col: int) -> str:
        """
        Get value from a specific cell.

        Args:
            row: Row index
            col: Column index

        Returns:
            Cell value as string
        """
        item = self.table.item(row, col)
        return item.text() if item else ""

    def get_row_data(self, row: int) -> List[str]:
        """
        Get all data from a specific row.

        Args:
            row: Row index

        Returns:
            List of cell values
        """
        return [self.get_cell_value(row, col) for col in range(self.table.columnCount())]

    def _on_selection_changed(self):
        """Handle selection changes."""
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        self.selection_changed.emit(selected_rows)

    def _export_csv(self):
        """Export data to CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "", "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write headers
                headers = [self.table.horizontalHeaderItem(i).text()
                          for i in range(self.table.columnCount())]
                writer.writerow(headers)

                # Write data
                for row in range(self.table.rowCount()):
                    row_data = self.get_row_data(row)
                    writer.writerow(row_data)

            from ..widgets.dialog_helper import DialogHelper
            DialogHelper.info(f"Data exported successfully to:\n{file_path}", "Export Complete", self)

        except Exception as e:
            from ..widgets.dialog_helper import DialogHelper
            DialogHelper.error("Export failed", "Export Error", self, details=str(e))

    def _copy_to_clipboard(self):
        """Copy selected rows to clipboard (tab-separated)."""
        selection = self.table.selectedIndexes()
        if not selection:
            return

        # Get unique rows and columns from selection
        rows = sorted(set(index.row() for index in selection))
        cols = sorted(set(index.column() for index in selection))

        # Build tab-separated text
        text_rows = []
        for row in rows:
            row_text = '\t'.join(
                self.get_cell_value(row, col) for col in cols
            )
            text_rows.append(row_text)

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(text_rows))

    def apply_theme_style(self, stylesheet: str):
        """
        Apply QSS stylesheet to the table.

        Args:
            stylesheet: QSS stylesheet string
        """
        self.table.setStyleSheet(stylesheet)

    def resize_columns_to_contents(self):
        """Resize all columns to fit their contents."""
        self.table.resizeColumnsToContents()

    def set_column_width(self, column: int, width: int):
        """
        Set width of a specific column.

        Args:
            column: Column index
            width: Width in pixels
        """
        self.table.setColumnWidth(column, width)
