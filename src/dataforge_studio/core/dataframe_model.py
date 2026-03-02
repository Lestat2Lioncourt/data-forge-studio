"""
DataFrame Table Model - High-performance Qt model for pandas DataFrame.

This module provides QAbstractTableModel implementations that wrap pandas
DataFrames for efficient display in Qt views (QTableView, QTreeView).

Key features:
- Lazy data access (Qt only requests visible cells)
- Efficient sorting without data copying
- Type-aware formatting and alignment
- Support for alternating row colors
- Column type information for rendering hints
"""

import logging
from typing import Any, Optional, List

import pandas as pd
from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
)
from PySide6.QtGui import QColor, QBrush

logger = logging.getLogger(__name__)


class DataFrameTableModel(QAbstractTableModel):
    """
    High-performance Qt table model backed by a pandas DataFrame.

    This model provides efficient data access for Qt views by:
    - Only fetching data when requested by the view (lazy evaluation)
    - Caching formatted strings for repeated access
    - Supporting native sorting via sort proxy model
    - Providing type-aware alignment and formatting

    Usage:
        df = pd.read_csv("data.csv")
        model = DataFrameTableModel(df)
        table_view.setModel(model)

    For sorting, use with QSortFilterProxyModel:
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        table_view.setModel(proxy)
        table_view.setSortingEnabled(True)
    """

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        parent=None,
        editable: bool = False,
        show_row_numbers: bool = True
    ):
        """
        Initialize the model with a DataFrame.

        Args:
            df: Source DataFrame (can be None, set later with setDataFrame)
            parent: Parent QObject
            editable: Whether cells can be edited
            show_row_numbers: Whether to show row numbers in vertical header
        """
        super().__init__(parent)
        self._df: pd.DataFrame = df if df is not None else pd.DataFrame()
        self._editable = editable
        self._show_row_numbers = show_row_numbers

        # Column types cache for alignment/formatting
        self._column_types: List[str] = []
        self._update_column_types()

    def setDataFrame(self, df: pd.DataFrame):
        """
        Replace the underlying DataFrame.

        Args:
            df: New DataFrame to display
        """
        self.beginResetModel()
        self._df = df if df is not None else pd.DataFrame()
        self._update_column_types()
        self.endResetModel()

    def getDataFrame(self) -> pd.DataFrame:
        """Return the underlying DataFrame."""
        return self._df

    def _update_column_types(self):
        """Update cached column type information."""
        self._column_types = []
        for col in self._df.columns:
            dtype = self._df[col].dtype
            if pd.api.types.is_integer_dtype(dtype):
                self._column_types.append('int')
            elif pd.api.types.is_float_dtype(dtype):
                self._column_types.append('float')
            elif pd.api.types.is_bool_dtype(dtype):
                self._column_types.append('bool')
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                self._column_types.append('datetime')
            else:
                self._column_types.append('str')

    # ==================== Required QAbstractTableModel methods ====================

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows in the DataFrame."""
        if parent.isValid():
            return 0
        return len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns in the DataFrame."""
        if parent.isValid():
            return 0
        return len(self._df.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """
        Return data for the given index and role.

        Supported roles:
        - DisplayRole: Formatted string value
        - EditRole: Raw value for editing
        - TextAlignmentRole: Alignment based on data type
        - ToolTipRole: Full value for truncated cells
        """
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= len(self._df) or col >= len(self._df.columns):
            return None

        value = self._df.iloc[row, col]

        if role == Qt.ItemDataRole.DisplayRole:
            return self._format_value(value, col)

        elif role == Qt.ItemDataRole.EditRole:
            return value

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return self._get_alignment(col)

        elif role == Qt.ItemDataRole.ToolTipRole:
            # Show full value in tooltip for potentially truncated text
            str_value = str(value) if not pd.isna(value) else ""
            if len(str_value) > 50:
                return str_value
            return None

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """Return header data for rows and columns."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section < len(self._df.columns):
                    return str(self._df.columns[section])
            else:
                # Vertical header: row numbers (1-based for user display)
                if self._show_row_numbers:
                    return str(section + 1)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return item flags (selectable, editable, etc.)."""
        default_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        if self._editable:
            default_flags |= Qt.ItemFlag.ItemIsEditable

        return default_flags

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        """
        Set data at the given index (if editable).

        Args:
            index: Cell index
            value: New value
            role: Data role (must be EditRole)

        Returns:
            True if value was set successfully
        """
        if not self._editable or not index.isValid():
            return False

        if role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()

        try:
            # Try to preserve the original type
            col_name = self._df.columns[col]
            original_dtype = self._df[col_name].dtype

            # Convert value to appropriate type
            if pd.api.types.is_integer_dtype(original_dtype):
                value = int(value) if value != '' else None
            elif pd.api.types.is_float_dtype(original_dtype):
                value = float(value) if value != '' else None
            elif pd.api.types.is_bool_dtype(original_dtype):
                value = str(value).lower() in ('true', '1', 'yes', 'oui')

            self._df.iloc[row, col] = value
            self.dataChanged.emit(index, index, [role])
            return True

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to set value at ({row}, {col}): {e}")
            return False

    # ==================== Helper methods ====================

    def _format_value(self, value: Any, col_index: int) -> str:
        """
        Format a value for display based on its type.

        Args:
            value: Raw value
            col_index: Column index for type lookup

        Returns:
            Formatted string
        """
        if pd.isna(value):
            return ""

        if col_index < len(self._column_types):
            col_type = self._column_types[col_index]

            if col_type == 'float':
                # Format floats with reasonable precision
                if abs(value) < 0.01 or abs(value) >= 10000:
                    return f"{value:.4g}"
                return f"{value:.2f}"

            elif col_type == 'int':
                return str(int(value))

            elif col_type == 'bool':
                return "True" if value else "False"

            elif col_type == 'datetime':
                try:
                    return value.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError, AttributeError):
                    return str(value)

        return str(value)

    def _get_alignment(self, col_index: int) -> Qt.AlignmentFlag:
        """
        Get text alignment based on column type.

        Numbers are right-aligned, text is left-aligned.
        """
        if col_index < len(self._column_types):
            col_type = self._column_types[col_index]
            if col_type in ('int', 'float'):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    # ==================== Convenience methods ====================

    def getColumnNames(self) -> List[str]:
        """Return list of column names."""
        return list(self._df.columns)

    def getColumnType(self, col_index: int) -> str:
        """Return type string for a column ('int', 'float', 'str', etc.)."""
        if col_index < len(self._column_types):
            return self._column_types[col_index]
        return 'str'

    def getRowData(self, row: int) -> List[Any]:
        """Return all values for a row as a list."""
        if row < len(self._df):
            return list(self._df.iloc[row])
        return []

    def getCellValue(self, row: int, col: int) -> Any:
        """Return raw value at the given position."""
        if row < len(self._df) and col < len(self._df.columns):
            return self._df.iloc[row, col]
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """
        Sort the DataFrame by the given column.

        Note: For better performance with large datasets, use QSortFilterProxyModel
        instead of this method.
        """
        if column >= len(self._df.columns):
            return

        self.layoutAboutToBeChanged.emit()

        col_name = self._df.columns[column]
        ascending = (order == Qt.SortOrder.AscendingOrder)

        try:
            self._df = self._df.sort_values(
                by=col_name,
                ascending=ascending,
                na_position='last'
            ).reset_index(drop=True)
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Sort failed: {e}")

        self.layoutChanged.emit()


class DataFrameSortProxyModel(QSortFilterProxyModel):
    """
    Proxy model for sorting and filtering DataFrameTableModel.

    Provides type-aware sorting that handles:
    - Numeric sorting for int/float columns
    - Case-insensitive string sorting
    - Proper handling of null/NaN values
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """
        Compare two items for sorting with type awareness.
        """
        source_model = self.sourceModel()
        if not isinstance(source_model, DataFrameTableModel):
            return super().lessThan(left, right)

        left_value = source_model.getCellValue(left.row(), left.column())
        right_value = source_model.getCellValue(right.row(), right.column())

        # Handle None/NaN: always sort to end
        left_is_null = pd.isna(left_value)
        right_is_null = pd.isna(right_value)

        if left_is_null and right_is_null:
            return False
        if left_is_null:
            return False  # Null goes to end
        if right_is_null:
            return True  # Non-null before null

        # Type-aware comparison
        col_type = source_model.getColumnType(left.column())

        try:
            if col_type in ('int', 'float'):
                return float(left_value) < float(right_value)
            else:
                return str(left_value).lower() < str(right_value).lower()
        except (ValueError, TypeError):
            return str(left_value).lower() < str(right_value).lower()
