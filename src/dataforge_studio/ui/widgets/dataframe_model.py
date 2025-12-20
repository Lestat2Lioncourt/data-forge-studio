"""
DataFrame Table Model for Virtual Scrolling.

Provides a QAbstractTableModel wrapper around pandas DataFrame for efficient
display of large datasets. Only visible cells are rendered, enabling smooth
scrolling through millions of rows.
"""
from typing import Any, Optional, List, TYPE_CHECKING
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor

if TYPE_CHECKING:
    import pandas as pd


# Threshold for switching to virtual scrolling mode
VIRTUAL_SCROLL_THRESHOLD = 50_000


class DataFrameTableModel(QAbstractTableModel):
    """
    QAbstractTableModel implementation for pandas DataFrame.

    This model provides data on-demand, making it memory-efficient for
    large datasets. Only visible cells are rendered by the view.

    Features:
    - Memory efficient: doesn't create QTableWidgetItem for each cell
    - Fast: direct access to numpy array data
    - Sortable: integrated with QSortFilterProxyModel
    - Read-only: cells are not editable
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dataframe: Optional["pd.DataFrame"] = None
        self._columns: List[str] = []
        self._row_count: int = 0
        self._col_count: int = 0

    def set_dataframe(self, df: "pd.DataFrame") -> None:
        """
        Set the DataFrame to display.

        Args:
            df: pandas DataFrame
        """
        self.beginResetModel()
        self._dataframe = df
        self._columns = [str(col) for col in df.columns]
        self._row_count = len(df)
        self._col_count = len(df.columns)
        self.endResetModel()

    def clear(self) -> None:
        """Clear the model data."""
        self.beginResetModel()
        self._dataframe = None
        self._columns = []
        self._row_count = 0
        self._col_count = 0
        self.endResetModel()

    @property
    def dataframe(self) -> Optional["pd.DataFrame"]:
        """Get the underlying DataFrame."""
        return self._dataframe

    # -------------------------------------------------------------------------
    # QAbstractTableModel interface
    # -------------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows."""
        if parent.isValid():
            return 0
        return self._row_count

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return self._col_count

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """
        Return data for the given index and role.

        This is the core method called by the view for each visible cell.
        It must be fast as it's called frequently during scrolling.
        """
        if not index.isValid() or self._dataframe is None:
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= self._row_count:
            return None
        if col < 0 or col >= self._col_count:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            # Get value directly from numpy array (fast)
            value = self._dataframe.iat[row, col]
            return self._format_value(value)

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # Right-align numbers, left-align text
            value = self._dataframe.iat[row, col]
            if isinstance(value, (int, float)) and not self._is_nan(value):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ToolTipRole:
            # Show full value in tooltip for truncated cells
            value = self._dataframe.iat[row, col]
            if value is not None and not self._is_nan(value):
                return str(value)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data."""
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._columns):
                return self._columns[section]
        else:
            # Row numbers (1-based for user display)
            return str(section + 1)

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return item flags (read-only)."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # -------------------------------------------------------------------------
    # Sorting support
    # -------------------------------------------------------------------------

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """
        Sort the model by the given column.

        Note: For multi-column sort, use sort_by_columns() instead.
        """
        if self._dataframe is None or column < 0 or column >= self._col_count:
            return

        self.layoutAboutToBeChanged.emit()

        try:
            col_name = self._dataframe.columns[column]
            ascending = (order == Qt.SortOrder.AscendingOrder)

            self._dataframe = self._dataframe.sort_values(
                by=col_name,
                ascending=ascending,
                na_position='last'
            ).reset_index(drop=True)

        except TypeError:
            # Mixed types: convert to string
            col_name = self._dataframe.columns[column]
            self._dataframe[col_name] = self._dataframe[col_name].astype(str)
            self._dataframe = self._dataframe.sort_values(
                by=col_name,
                ascending=(order == Qt.SortOrder.AscendingOrder),
                na_position='last'
            ).reset_index(drop=True)

        self.layoutChanged.emit()

    def sort_by_columns(self, columns: List[int], orders: List[Qt.SortOrder]) -> None:
        """
        Sort by multiple columns.

        Args:
            columns: List of column indices
            orders: List of sort orders (same length as columns)
        """
        if self._dataframe is None or not columns:
            return

        self.layoutAboutToBeChanged.emit()

        try:
            col_names = [self._dataframe.columns[c] for c in columns if 0 <= c < self._col_count]
            ascending = [o == Qt.SortOrder.AscendingOrder for o in orders[:len(col_names)]]

            if col_names:
                self._dataframe = self._dataframe.sort_values(
                    by=col_names,
                    ascending=ascending,
                    na_position='last'
                ).reset_index(drop=True)

        except TypeError:
            # Mixed types: convert to string
            for col_name in col_names:
                self._dataframe[col_name] = self._dataframe[col_name].astype(str)
            self._dataframe = self._dataframe.sort_values(
                by=col_names,
                ascending=ascending,
                na_position='last'
            ).reset_index(drop=True)

        self.layoutChanged.emit()

    # -------------------------------------------------------------------------
    # Data access helpers
    # -------------------------------------------------------------------------

    def get_row_data(self, row: int) -> List[str]:
        """Get all values from a row as strings."""
        if self._dataframe is None or row < 0 or row >= self._row_count:
            return []
        return [self._format_value(v) for v in self._dataframe.iloc[row]]

    def get_cell_value(self, row: int, col: int) -> str:
        """Get a single cell value as string."""
        if self._dataframe is None:
            return ""
        if row < 0 or row >= self._row_count:
            return ""
        if col < 0 or col >= self._col_count:
            return ""
        return self._format_value(self._dataframe.iat[row, col])

    def get_all_data(self) -> List[List[Any]]:
        """Get all data as list of lists (for export)."""
        if self._dataframe is None:
            return []
        return self._dataframe.values.tolist()

    def get_columns(self) -> List[str]:
        """Get column names."""
        return self._columns.copy()

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        import pandas as pd

        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        elif isinstance(value, float):
            if abs(value) >= 10000 or (abs(value) < 0.01 and value != 0):
                return f"{value:.4g}"
            else:
                return f"{value:.2f}"
        else:
            return str(value)

    def _is_nan(self, value: Any) -> bool:
        """Check if value is NaN."""
        import pandas as pd
        return isinstance(value, float) and pd.isna(value)


class SortableDataFrameModel(QSortFilterProxyModel):
    """
    Proxy model that adds sorting capability to DataFrameTableModel.

    Uses the underlying DataFrame's sort for efficiency rather than
    Qt's row-by-row comparison.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sort_columns: List[int] = []
        self._sort_orders: List[Qt.SortOrder] = []

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Sort by a single column."""
        source = self.sourceModel()
        if isinstance(source, DataFrameTableModel):
            source.sort(column, order)
            self._sort_columns = [column]
            self._sort_orders = [order]
        else:
            super().sort(column, order)

    def sort_by_columns(self, columns: List[int], orders: List[Qt.SortOrder]) -> None:
        """Sort by multiple columns."""
        source = self.sourceModel()
        if isinstance(source, DataFrameTableModel):
            source.sort_by_columns(columns, orders)
            self._sort_columns = columns
            self._sort_orders = orders

    @property
    def active_sorts(self) -> List[tuple]:
        """Get current sort configuration as list of (column, order) tuples."""
        return list(zip(self._sort_columns, self._sort_orders))
