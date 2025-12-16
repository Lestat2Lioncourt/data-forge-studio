"""
Custom Data Grid View - Table widget with sorting, export, and clipboard features
Replaces the 893-line TKinter version with a more compact PySide6 implementation
"""

from typing import List, Optional, Any, Tuple
from PySide6.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView,
                               QFileDialog, QApplication, QDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
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
        self.active_sorts: List[Tuple[int, Qt.SortOrder]] = []  # List of (column_index, sort_order) for multi-column sort
        self.is_fullscreen = False
        self.fullscreen_dialog = None
        self.fullscreen_table = None
        self.data = []  # Store data for fullscreen display
        self.columns = []  # Store column names
        self.db_name = None  # Database name for context
        self.table_name = None  # Table/view name for context
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

            self.fullscreen_btn = QPushButton("⛶ Fullscreen")
            self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
            toolbar_layout.addWidget(self.fullscreen_btn)

            self.distribution_btn = QPushButton("📊 Distribution Analysis")
            self.distribution_btn.clicked.connect(self._show_distribution_analysis)
            toolbar_layout.addWidget(self.distribution_btn)

            layout.addLayout(toolbar_layout)

        # Table widget
        self.table = QTableWidget()
        self.table.setSortingEnabled(False)  # We'll handle sorting manually for multi-column support
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setToolTip("Click to sort (▲▼), Ctrl+Click to add column to multi-sort (with numbers)")
        self.table.verticalHeader().setVisible(True)  # Show row numbers

        # Compact row height - can be manually resized if needed for multi-line content
        self.table.verticalHeader().setDefaultSectionSize(16)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        layout.addWidget(self.table)

        # Connect signals
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

    def set_columns(self, columns: List[str]):
        """
        Set column headers.

        Args:
            columns: List of column names
        """
        self.columns = columns  # Store for fullscreen
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

    def set_data(self, data: List[List[Any]]):
        """
        Set grid data.

        Args:
            data: 2D list of data [[row1_col1, row1_col2, ...], [row2_col1, ...], ...]
        """
        self.data = data  # Store for fullscreen
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

        # Auto-resize columns
        self.autosize_columns()

    def clear(self):
        """Clear all data from the grid."""
        self.table.clearContents()
        self.table.setRowCount(0)

    def autosize_columns(self, max_width: int = 300):
        """
        Auto-resize all columns to fit content.

        Args:
            max_width: Maximum width for any column (default: 300)
        """
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount()):
            if self.table.columnWidth(col) > max_width:
                self.table.setColumnWidth(col, max_width)

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

    def _on_header_clicked(self, column: int):
        """
        Handle header click for sorting.
        Ctrl+Click: Add to multi-column sort
        Regular Click: Single column sort
        """
        from PySide6.QtWidgets import QApplication

        # Check if Ctrl is pressed
        modifiers = QApplication.keyboardModifiers()
        ctrl_pressed = modifiers & Qt.KeyboardModifier.ControlModifier

        if ctrl_pressed:
            # Multi-column sort: add or toggle this column
            existing_sort = None
            for i, (col, order) in enumerate(self.active_sorts):
                if col == column:
                    existing_sort = i
                    break

            if existing_sort is not None:
                # Toggle sort order for this column
                old_col, old_order = self.active_sorts[existing_sort]
                new_order = Qt.SortOrder.DescendingOrder if old_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
                self.active_sorts[existing_sort] = (column, new_order)
            else:
                # Add new column to sort list
                self.active_sorts.append((column, Qt.SortOrder.AscendingOrder))
        else:
            # Single column sort: replace all sorts
            existing_sort = None
            if len(self.active_sorts) == 1 and self.active_sorts[0][0] == column:
                # Toggle sort order
                old_order = self.active_sorts[0][1]
                new_order = Qt.SortOrder.DescendingOrder if old_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
                self.active_sorts = [(column, new_order)]
            else:
                # New single column sort
                self.active_sorts = [(column, Qt.SortOrder.AscendingOrder)]

        # Apply the sort
        self._apply_multi_column_sort()

    def _apply_multi_column_sort(self):
        """Apply multi-column sorting to the table."""
        if not self.active_sorts:
            return

        # Get current data from table
        current_data = []
        for row in range(self.table.rowCount()):
            row_data = [self.get_cell_value(row, col) for col in range(self.table.columnCount())]
            current_data.append(row_data)

        if not current_data:
            return

        # Custom comparison class for handling mixed ascending/descending
        class SortableValue:
            def __init__(self, value, descending=False):
                self.value = value
                self.descending = descending

                # Try to convert to number
                try:
                    self.numeric = float(value) if value else 0
                    self.is_numeric = True
                except (ValueError, TypeError):
                    self.numeric = 0
                    self.is_numeric = False
                    self.str_value = str(value).lower()

            def __lt__(self, other):
                # Compare based on type
                if self.is_numeric and other.is_numeric:
                    # Both numeric
                    my_val = self.numeric
                    other_val = other.numeric
                elif not self.is_numeric and not other.is_numeric:
                    # Both strings
                    my_val = self.str_value
                    other_val = other.str_value
                else:
                    # Mixed types: numeric < string
                    if self.is_numeric:
                        result = True  # numeric comes before string
                    else:
                        result = False  # string comes after numeric
                    return (not result) if self.descending else result

                # Apply sort order
                if self.descending:
                    return my_val > other_val
                else:
                    return my_val < other_val

            def __eq__(self, other):
                if self.is_numeric and other.is_numeric:
                    return self.numeric == other.numeric
                elif not self.is_numeric and not other.is_numeric:
                    return self.str_value == other.str_value
                else:
                    # Mixed types: never equal
                    return False

            def __le__(self, other):
                return self.__lt__(other) or self.__eq__(other)

            def __gt__(self, other):
                return not self.__le__(other)

            def __ge__(self, other):
                return not self.__lt__(other)

        # Sort using multiple columns
        def multi_key(row_data):
            """Generate sort key for multi-column sorting."""
            keys = []
            for col, order in self.active_sorts:
                if col < len(row_data):
                    value = row_data[col]
                    is_desc = (order == Qt.SortOrder.DescendingOrder)
                    keys.append(SortableValue(value, is_desc))
                else:
                    keys.append(SortableValue("", False))
            return tuple(keys)

        # Sort data
        try:
            sorted_data = sorted(current_data, key=multi_key)
        except Exception as e:
            # Fallback: simple sort on first column
            col, order = self.active_sorts[0]
            sorted_data = sorted(current_data,
                               key=lambda x: str(x[col]).lower() if col < len(x) else "",
                               reverse=(order == Qt.SortOrder.DescendingOrder))

        # Update table with sorted data
        self.table.setSortingEnabled(False)
        for row_idx, row_data in enumerate(sorted_data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

        # Update headers to show all sort indicators with numbers
        self._update_sort_indicators()

    def _update_sort_indicators(self):
        """Update column headers to show sort indicators with numbers and arrows."""
        # First, restore all headers to their original text (remove previous indicators)
        for col_idx in range(self.table.columnCount()):
            original_text = self.columns[col_idx] if col_idx < len(self.columns) else f"Column {col_idx}"
            self.table.horizontalHeaderItem(col_idx).setText(original_text)

        # Add sort indicators for all sorted columns
        for sort_index, (col, order) in enumerate(self.active_sorts, start=1):
            if col < self.table.columnCount():
                header_item = self.table.horizontalHeaderItem(col)
                if header_item:
                    original_text = self.columns[col] if col < len(self.columns) else f"Column {col}"
                    # Triangle: ▲ for ascending, ▼ for descending
                    arrow = "▲" if order == Qt.SortOrder.AscendingOrder else "▼"
                    # Show number only if multiple sorts
                    if len(self.active_sorts) > 1:
                        header_item.setText(f"{original_text} {arrow}{sort_index}")
                    else:
                        header_item.setText(f"{original_text} {arrow}")

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

    def _toggle_fullscreen(self):
        """Toggle fullscreen view of the grid."""
        if self.is_fullscreen:
            # Close fullscreen
            if self.fullscreen_dialog:
                self.fullscreen_dialog.close()
                self.fullscreen_dialog = None
            self.is_fullscreen = False
        else:
            # Open fullscreen
            self._open_fullscreen()
            self.is_fullscreen = True

    def _open_fullscreen(self):
        """Open fullscreen dialog with grid data."""
        # Create fullscreen dialog
        self.fullscreen_dialog = QDialog(self)
        self.fullscreen_dialog.setWindowTitle("Fullscreen View - Press ESC to exit, Ctrl+Click for multi-column sort")
        self.fullscreen_dialog.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)

        # Layout
        layout = QVBoxLayout(self.fullscreen_dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create table for fullscreen
        self.fullscreen_table = QTableWidget()
        self.fullscreen_table.setSortingEnabled(False)  # We handle sorting manually
        self.fullscreen_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fullscreen_table.setAlternatingRowColors(True)
        self.fullscreen_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.fullscreen_table.verticalHeader().setVisible(True)

        # Copy columns
        if self.columns:
            self.fullscreen_table.setColumnCount(len(self.columns))
            self.fullscreen_table.setHorizontalHeaderLabels(self.columns)

        # Copy data
        if self.data:
            self.fullscreen_table.setRowCount(len(self.data))

            for row_idx, row_data in enumerate(self.data):
                for col_idx, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.fullscreen_table.setItem(row_idx, col_idx, item)

            # Auto-resize columns in fullscreen
            self.fullscreen_table.resizeColumnsToContents()
            for col in range(self.fullscreen_table.columnCount()):
                if self.fullscreen_table.columnWidth(col) > 300:
                    self.fullscreen_table.setColumnWidth(col, 300)

        # Connect header click for multi-column sort (same as main table)
        self.fullscreen_table.horizontalHeader().sectionClicked.connect(self._on_fullscreen_header_clicked)

        layout.addWidget(self.fullscreen_table)

        # Apply existing sorts to fullscreen table
        if self.active_sorts:
            self._apply_fullscreen_sort()

        # Install event filter for ESC key
        self.fullscreen_dialog.installEventFilter(self)

        # Show dialog in fullscreen AFTER layout is set
        self.fullscreen_dialog.showFullScreen()
        self.fullscreen_dialog.exec()

        # When dialog closes, apply sorts back to main table
        if self.active_sorts:
            self._apply_multi_column_sort()

        # Reset state when dialog closes
        self.is_fullscreen = False
        self.fullscreen_table = None
        self.fullscreen_dialog = None

    def _on_fullscreen_header_clicked(self, column: int):
        """
        Handle header click for sorting in fullscreen mode.
        Ctrl+Click: Add to multi-column sort
        Regular Click: Single column sort
        """
        from PySide6.QtWidgets import QApplication

        # Check if Ctrl is pressed
        modifiers = QApplication.keyboardModifiers()
        ctrl_pressed = modifiers & Qt.KeyboardModifier.ControlModifier

        if ctrl_pressed:
            # Multi-column sort: add or toggle this column
            existing_sort = None
            for i, (col, order) in enumerate(self.active_sorts):
                if col == column:
                    existing_sort = i
                    break

            if existing_sort is not None:
                # Toggle sort order for this column
                old_col, old_order = self.active_sorts[existing_sort]
                new_order = Qt.SortOrder.DescendingOrder if old_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
                self.active_sorts[existing_sort] = (column, new_order)
            else:
                # Add new column to sort list
                self.active_sorts.append((column, Qt.SortOrder.AscendingOrder))
        else:
            # Single column sort: replace all sorts
            existing_sort = None
            if len(self.active_sorts) == 1 and self.active_sorts[0][0] == column:
                # Toggle sort order
                old_order = self.active_sorts[0][1]
                new_order = Qt.SortOrder.DescendingOrder if old_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
                self.active_sorts = [(column, new_order)]
            else:
                # New single column sort
                self.active_sorts = [(column, Qt.SortOrder.AscendingOrder)]

        # Apply the sort to fullscreen table
        self._apply_fullscreen_sort()

    def _apply_fullscreen_sort(self):
        """Apply multi-column sorting to the fullscreen table."""
        if not self.active_sorts or not self.fullscreen_table:
            return

        # Get current data from fullscreen table
        current_data = []
        for row in range(self.fullscreen_table.rowCount()):
            row_data = []
            for col in range(self.fullscreen_table.columnCount()):
                item = self.fullscreen_table.item(row, col)
                row_data.append(item.text() if item else "")
            current_data.append(row_data)

        if not current_data:
            return

        # Use the same SortableValue class as main table
        class SortableValue:
            def __init__(self, value, descending=False):
                self.value = value
                self.descending = descending

                # Try to convert to number
                try:
                    self.numeric = float(value) if value else 0
                    self.is_numeric = True
                except (ValueError, TypeError):
                    self.numeric = 0
                    self.is_numeric = False
                    self.str_value = str(value).lower()

            def __lt__(self, other):
                # Compare based on type
                if self.is_numeric and other.is_numeric:
                    my_val = self.numeric
                    other_val = other.numeric
                elif not self.is_numeric and not other.is_numeric:
                    my_val = self.str_value
                    other_val = other.str_value
                else:
                    # Mixed types: numeric < string
                    if self.is_numeric:
                        result = True
                    else:
                        result = False
                    return (not result) if self.descending else result

                # Apply sort order
                if self.descending:
                    return my_val > other_val
                else:
                    return my_val < other_val

            def __eq__(self, other):
                if self.is_numeric and other.is_numeric:
                    return self.numeric == other.numeric
                elif not self.is_numeric and not other.is_numeric:
                    return self.str_value == other.str_value
                else:
                    return False

            def __le__(self, other):
                return self.__lt__(other) or self.__eq__(other)

            def __gt__(self, other):
                return not self.__le__(other)

            def __ge__(self, other):
                return not self.__lt__(other)

        # Sort using multiple columns
        def multi_key(row_data):
            """Generate sort key for multi-column sorting."""
            keys = []
            for col, order in self.active_sorts:
                if col < len(row_data):
                    value = row_data[col]
                    is_desc = (order == Qt.SortOrder.DescendingOrder)
                    keys.append(SortableValue(value, is_desc))
                else:
                    keys.append(SortableValue("", False))
            return tuple(keys)

        # Sort data
        try:
            sorted_data = sorted(current_data, key=multi_key)
        except Exception as e:
            # Fallback: simple sort on first column
            col, order = self.active_sorts[0]
            sorted_data = sorted(current_data,
                               key=lambda x: str(x[col]).lower() if col < len(x) else "",
                               reverse=(order == Qt.SortOrder.DescendingOrder))

        # Update fullscreen table with sorted data
        for row_idx, row_data in enumerate(sorted_data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.fullscreen_table.setItem(row_idx, col_idx, item)

        # Update headers with sort indicators
        self._update_fullscreen_sort_indicators()

    def _update_fullscreen_sort_indicators(self):
        """Update column headers in fullscreen to show sort indicators with numbers and arrows."""
        if not self.fullscreen_table:
            return

        # First, restore all headers to their original text
        for col_idx in range(self.fullscreen_table.columnCount()):
            original_text = self.columns[col_idx] if col_idx < len(self.columns) else f"Column {col_idx}"
            self.fullscreen_table.horizontalHeaderItem(col_idx).setText(original_text)

        # Add sort indicators for all sorted columns
        for sort_index, (col, order) in enumerate(self.active_sorts, start=1):
            if col < self.fullscreen_table.columnCount():
                header_item = self.fullscreen_table.horizontalHeaderItem(col)
                if header_item:
                    original_text = self.columns[col] if col < len(self.columns) else f"Column {col}"
                    arrow = "▲" if order == Qt.SortOrder.AscendingOrder else "▼"
                    if len(self.active_sorts) > 1:
                        header_item.setText(f"{original_text} {arrow}{sort_index}")
                    else:
                        header_item.setText(f"{original_text} {arrow}")

    def set_context(self, db_name: str = None, table_name: str = None):
        """
        Set the database context for this grid.

        Args:
            db_name: Database name
            table_name: Table, view or query name
        """
        self.db_name = db_name
        self.table_name = table_name

    def _show_distribution_analysis(self):
        """Show distribution analysis dialog for current grid data"""
        if not self.data or not self.columns:
            from ..widgets.dialog_helper import DialogHelper
            DialogHelper.info("No data available for analysis", parent=self)
            return

        # Import here to avoid circular import
        from ..widgets.distribution_analysis_dialog import DistributionAnalysisDialog

        # Show distribution analysis dialog (non-modal to allow multiple windows)
        dialog = DistributionAnalysisDialog(
            self.data, self.columns,
            db_name=self.db_name,
            table_name=self.table_name,
            parent=self
        )
        dialog.show()

    def eventFilter(self, obj, event):
        """Filter events to handle ESC key in fullscreen."""
        if obj == self.fullscreen_dialog and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.fullscreen_dialog.close()
                return True
        return super().eventFilter(obj, event)
