"""
Data Viewer - Display pandas DataFrame in Qt widgets.

This module provides functions to populate Qt widgets from DataFrames,
completing the DataFrame-Pivot pattern:

    Sources → data_loader → DataFrame → data_viewer → Qt Widgets

Supported targets:
- QTableView (via DataFrameTableModel - recommended for large data)
- QTableWidget (legacy, for small datasets)
- QTreeWidget (hierarchical display)
- QComboBox (dropdown selection)
- QListWidget (simple list)

All functions handle theming automatically via the global stylesheet.
"""

import logging
from typing import Optional, List, Any, Callable, Dict, Union

import pandas as pd
from PySide6.QtWidgets import (
    QTableView, QTableWidget, QTableWidgetItem,
    QTreeWidget, QTreeWidgetItem,
    QComboBox, QListWidget, QListWidgetItem,
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QSortFilterProxyModel

from .dataframe_model import DataFrameTableModel, DataFrameSortProxyModel

logger = logging.getLogger(__name__)


# =============================================================================
# QTableView (Model-based, recommended for large datasets)
# =============================================================================

def dataframe_to_tableview(
    df: pd.DataFrame,
    table_view: QTableView,
    sortable: bool = True,
    editable: bool = False,
    auto_resize: bool = True,
    max_column_width: int = 300
) -> DataFrameTableModel:
    """
    Display a DataFrame in a QTableView using the high-performance model.

    This is the recommended method for large datasets as it uses lazy
    data access (Qt only requests visible cells).

    Args:
        df: Source DataFrame
        table_view: Target QTableView widget
        sortable: Enable column sorting (default: True)
        editable: Enable cell editing (default: False)
        auto_resize: Auto-resize columns to content (default: True)
        max_column_width: Maximum column width in pixels

    Returns:
        The DataFrameTableModel for further interaction

    Example:
        df = csv_to_dataframe("data.csv").dataframe
        model = dataframe_to_tableview(df, my_table_view)
    """
    # Create the model
    model = DataFrameTableModel(df, editable=editable)

    if sortable:
        # Wrap with sort proxy for efficient sorting
        proxy = DataFrameSortProxyModel()
        proxy.setSourceModel(model)
        table_view.setModel(proxy)
        table_view.setSortingEnabled(True)
    else:
        table_view.setModel(model)
        table_view.setSortingEnabled(False)

    # Configure view
    table_view.setAlternatingRowColors(True)
    table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table_view.verticalHeader().setDefaultSectionSize(22)

    # Auto-resize columns
    if auto_resize and len(df) > 0:
        table_view.resizeColumnsToContents()

        # Apply max width limit
        for col in range(len(df.columns)):
            if table_view.columnWidth(col) > max_column_width:
                table_view.setColumnWidth(col, max_column_width)

    logger.debug(f"Populated QTableView: {len(df)} rows, {len(df.columns)} cols")

    return model


# =============================================================================
# QTableWidget (Legacy, for small datasets or backward compatibility)
# =============================================================================

def dataframe_to_datagridview(
    df: pd.DataFrame,
    grid_widget: QTableWidget,
    editable: bool = False,
    auto_resize: bool = True,
    max_column_width: int = 300,
    batch_size: int = 1000,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> None:
    """
    Populate a QTableWidget from a DataFrame.

    This method populates cells directly, which is simpler but slower
    for large datasets. Use dataframe_to_tableview() for better performance.

    Args:
        df: Source DataFrame
        grid_widget: Target QTableWidget
        editable: Enable cell editing (default: False)
        auto_resize: Auto-resize columns to content
        max_column_width: Maximum column width in pixels
        batch_size: Process rows in batches for progress updates
        progress_callback: Optional callback(current_row, total_rows) for progress

    Example:
        df = csv_to_dataframe("data.csv").dataframe
        dataframe_to_datagridview(df, my_table_widget)
    """
    # Clear existing data
    grid_widget.clearContents()

    # Set dimensions
    num_rows = len(df)
    num_cols = len(df.columns)
    grid_widget.setColumnCount(num_cols)
    grid_widget.setRowCount(num_rows)

    # Set headers
    grid_widget.setHorizontalHeaderLabels([str(col) for col in df.columns])

    if num_rows == 0:
        return

    # Disable updates during population for better performance
    grid_widget.setUpdatesEnabled(False)

    try:
        # OPTIMIZED: Use .values (numpy array) instead of iterrows()
        # This is 10-50x faster than iterrows()
        data_array = df.values
        flags_mask = ~Qt.ItemFlag.ItemIsEditable if not editable else Qt.ItemFlag.ItemIsEnabled

        for row_idx in range(num_rows):
            row_data = data_array[row_idx]
            for col_idx in range(num_cols):
                value = row_data[col_idx]

                # Format value (optimized)
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    display_value = ""
                elif isinstance(value, float):
                    # Avoid scientific notation for reasonable numbers
                    if abs(value) >= 10000 or (abs(value) < 0.01 and value != 0):
                        display_value = f"{value:.4g}"
                    else:
                        display_value = f"{value:.2f}"
                else:
                    display_value = str(value)

                item = QTableWidgetItem(display_value)

                # Set flags
                if not editable:
                    item.setFlags(item.flags() & flags_mask)

                grid_widget.setItem(row_idx, col_idx, item)

            # Progress callback
            if progress_callback and (row_idx + 1) % batch_size == 0:
                progress_callback(row_idx + 1, num_rows)

        # Final progress
        if progress_callback:
            progress_callback(num_rows, num_rows)

    finally:
        # Re-enable updates
        grid_widget.setUpdatesEnabled(True)

    # Auto-resize (skip for very large datasets to avoid delay)
    if auto_resize and num_rows > 0 and num_rows < 10000:
        grid_widget.resizeColumnsToContents()
        for col in range(num_cols):
            if grid_widget.columnWidth(col) > max_column_width:
                grid_widget.setColumnWidth(col, max_column_width)
    elif auto_resize and num_rows >= 10000:
        # For large datasets, just set reasonable default widths
        for col in range(num_cols):
            grid_widget.setColumnWidth(col, 100)

    logger.debug(f"Populated QTableWidget: {num_rows} rows, {num_cols} cols")


# =============================================================================
# QTreeWidget (Hierarchical display)
# =============================================================================

def dataframe_to_treeview(
    df: pd.DataFrame,
    tree_widget: QTreeWidget,
    columns: Optional[List[str]] = None,
    group_by: Optional[str] = None,
    parent_item: Optional[QTreeWidgetItem] = None,
    data_column: Optional[str] = None,
    icon_callback: Optional[Callable[[pd.Series], Any]] = None
) -> None:
    """
    Populate a QTreeWidget from a DataFrame.

    Can display data as:
    - Flat list (one row per item)
    - Grouped hierarchy (if group_by is specified)

    Args:
        df: Source DataFrame
        tree_widget: Target QTreeWidget
        columns: Columns to display (default: all)
        group_by: Column to group by (creates parent nodes)
        parent_item: Parent item to add to (default: root)
        data_column: Column to store in item's UserRole data
        icon_callback: Function(row) -> QIcon for custom icons

    Examples:
        # Flat list
        dataframe_to_treeview(df, tree, columns=['name', 'type', 'size'])

        # Grouped by category
        dataframe_to_treeview(df, tree, group_by='category', columns=['name', 'size'])
    """
    # Determine columns to display
    if columns is None:
        columns = list(df.columns)

    display_columns = [c for c in columns if c in df.columns]

    # Clear if adding to root
    if parent_item is None:
        tree_widget.clear()
        tree_widget.setColumnCount(len(display_columns))
        tree_widget.setHeaderLabels(display_columns)

    # Get root
    root = parent_item if parent_item else tree_widget.invisibleRootItem()

    if group_by and group_by in df.columns:
        # Grouped mode: create parent nodes for each unique group value
        groups = df.groupby(group_by, dropna=False)

        for group_value, group_df in groups:
            # Create group node
            group_text = str(group_value) if not pd.isna(group_value) else "(Empty)"
            group_item = QTreeWidgetItem(root)
            group_item.setText(0, group_text)
            group_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'group', 'value': group_value})

            # Add children
            for _, row in group_df.iterrows():
                child_item = QTreeWidgetItem(group_item)
                _populate_tree_item(child_item, row, display_columns, data_column, icon_callback)

    else:
        # Flat mode: one item per row
        for _, row in df.iterrows():
            item = QTreeWidgetItem(root)
            _populate_tree_item(item, row, display_columns, data_column, icon_callback)

    # Resize columns
    for i in range(len(display_columns)):
        tree_widget.resizeColumnToContents(i)

    logger.debug(f"Populated QTreeWidget: {len(df)} rows")


def _populate_tree_item(
    item: QTreeWidgetItem,
    row: pd.Series,
    columns: List[str],
    data_column: Optional[str],
    icon_callback: Optional[Callable]
) -> None:
    """Helper to populate a single tree item from a row."""
    for col_idx, col_name in enumerate(columns):
        if col_name in row.index:
            value = row[col_name]
            display_value = "" if pd.isna(value) else str(value)
            item.setText(col_idx, display_value)

    # Store data
    if data_column and data_column in row.index:
        item.setData(0, Qt.ItemDataRole.UserRole, row[data_column])
    else:
        # Store entire row as dict
        item.setData(0, Qt.ItemDataRole.UserRole, row.to_dict())

    # Custom icon
    if icon_callback:
        try:
            icon = icon_callback(row)
            if icon:
                item.setIcon(0, icon)
        except Exception:
            pass


# =============================================================================
# QComboBox
# =============================================================================

def dataframe_to_combobox(
    df: pd.DataFrame,
    combo_box: QComboBox,
    display_column: str,
    value_column: Optional[str] = None,
    add_empty_option: bool = False,
    empty_text: str = "-- Select --",
    sort: bool = False
) -> None:
    """
    Populate a QComboBox from a DataFrame.

    Args:
        df: Source DataFrame
        combo_box: Target QComboBox
        display_column: Column for visible text
        value_column: Column for item data (default: same as display)
        add_empty_option: Add empty option at the beginning
        empty_text: Text for empty option
        sort: Sort items alphabetically

    Example:
        # Simple dropdown
        dataframe_to_combobox(df, combo, display_column='name')

        # With separate value
        dataframe_to_combobox(df, combo, display_column='name', value_column='id')
    """
    if display_column not in df.columns:
        logger.warning(f"Column '{display_column}' not found in DataFrame")
        return

    if value_column is None:
        value_column = display_column

    combo_box.clear()

    # Add empty option
    if add_empty_option:
        combo_box.addItem(empty_text, None)

    # Get data
    if sort:
        df = df.sort_values(by=display_column)

    # Populate
    for _, row in df.iterrows():
        display_text = str(row[display_column]) if not pd.isna(row[display_column]) else ""
        value = row[value_column] if value_column in row.index else None
        combo_box.addItem(display_text, value)

    logger.debug(f"Populated QComboBox: {combo_box.count()} items")


# =============================================================================
# QListWidget
# =============================================================================

def dataframe_to_listwidget(
    df: pd.DataFrame,
    list_widget: QListWidget,
    display_column: str,
    data_column: Optional[str] = None,
    icon_callback: Optional[Callable[[pd.Series], Any]] = None,
    checkable: bool = False
) -> None:
    """
    Populate a QListWidget from a DataFrame.

    Args:
        df: Source DataFrame
        list_widget: Target QListWidget
        display_column: Column for visible text
        data_column: Column for item data (default: store entire row)
        icon_callback: Function(row) -> QIcon for custom icons
        checkable: Make items checkable

    Example:
        dataframe_to_listwidget(df, my_list, display_column='name')
    """
    if display_column not in df.columns:
        logger.warning(f"Column '{display_column}' not found in DataFrame")
        return

    list_widget.clear()

    for _, row in df.iterrows():
        display_text = str(row[display_column]) if not pd.isna(row[display_column]) else ""
        item = QListWidgetItem(display_text)

        # Store data
        if data_column and data_column in row.index:
            item.setData(Qt.ItemDataRole.UserRole, row[data_column])
        else:
            item.setData(Qt.ItemDataRole.UserRole, row.to_dict())

        # Icon
        if icon_callback:
            try:
                icon = icon_callback(row)
                if icon:
                    item.setIcon(icon)
            except Exception:
                pass

        # Checkable
        if checkable:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)

        list_widget.addItem(item)

    logger.debug(f"Populated QListWidget: {list_widget.count()} items")


# =============================================================================
# Extraction (Widget → DataFrame)
# =============================================================================

def tablewidget_to_dataframe(table_widget: QTableWidget) -> pd.DataFrame:
    """
    Extract data from a QTableWidget back to a DataFrame.

    Args:
        table_widget: Source QTableWidget

    Returns:
        DataFrame with the table's content
    """
    # Get headers
    columns = []
    for col in range(table_widget.columnCount()):
        header_item = table_widget.horizontalHeaderItem(col)
        columns.append(header_item.text() if header_item else f"Column_{col}")

    # Get data
    data = []
    for row in range(table_widget.rowCount()):
        row_data = []
        for col in range(table_widget.columnCount()):
            item = table_widget.item(row, col)
            row_data.append(item.text() if item else "")
        data.append(row_data)

    return pd.DataFrame(data, columns=columns)


def treewidget_to_dataframe(
    tree_widget: QTreeWidget,
    include_children: bool = True
) -> pd.DataFrame:
    """
    Extract data from a QTreeWidget back to a DataFrame.

    Args:
        tree_widget: Source QTreeWidget
        include_children: Include nested children (flattened)

    Returns:
        DataFrame with the tree's content
    """
    # Get headers
    columns = []
    for col in range(tree_widget.columnCount()):
        header_item = tree_widget.headerItem()
        if header_item:
            columns.append(header_item.text(col))
        else:
            columns.append(f"Column_{col}")

    # Collect items
    data = []

    def collect_items(parent_item, level=0):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            row_data = [child.text(col) for col in range(tree_widget.columnCount())]
            data.append(row_data)

            if include_children:
                collect_items(child, level + 1)

    collect_items(tree_widget.invisibleRootItem())

    return pd.DataFrame(data, columns=columns)
