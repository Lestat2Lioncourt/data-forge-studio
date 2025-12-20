"""
Tests for virtual scrolling (DataFrameTableModel and CustomDataGridView).
"""
import pytest
import pandas as pd
import numpy as np

from dataforge_studio.ui.widgets.dataframe_model import (
    DataFrameTableModel,
    VIRTUAL_SCROLL_THRESHOLD,
)
from PySide6.QtCore import Qt


class TestDataFrameTableModel:
    """Test DataFrameTableModel functionality."""

    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'value': [10.5, 20.0, 30.75, 40.0, 50.25],
            'active': [True, False, True, True, False],
        })

    @pytest.fixture
    def model(self, qapp, sample_df):
        """Create a model with sample data."""
        model = DataFrameTableModel()
        model.set_dataframe(sample_df)
        return model

    def test_row_count(self, model):
        """Test row count."""
        assert model.rowCount() == 5

    def test_column_count(self, model):
        """Test column count."""
        assert model.columnCount() == 4

    def test_data_display_role(self, model, qapp):
        """Test data retrieval with display role."""
        from PySide6.QtCore import QModelIndex

        # First cell (id=1)
        idx = model.index(0, 0)
        assert model.data(idx, Qt.ItemDataRole.DisplayRole) == "1"

        # String cell (name=Alice)
        idx = model.index(0, 1)
        assert model.data(idx, Qt.ItemDataRole.DisplayRole) == "Alice"

        # Float cell (value=10.5)
        idx = model.index(0, 2)
        assert model.data(idx, Qt.ItemDataRole.DisplayRole) == "10.50"

    def test_header_data(self, model, qapp):
        """Test header data."""
        # Horizontal headers (column names)
        assert model.headerData(0, Qt.Orientation.Horizontal) == "id"
        assert model.headerData(1, Qt.Orientation.Horizontal) == "name"

        # Vertical headers (row numbers, 1-based)
        assert model.headerData(0, Qt.Orientation.Vertical) == "1"
        assert model.headerData(4, Qt.Orientation.Vertical) == "5"

    def test_flags(self, model, qapp):
        """Test item flags (read-only)."""
        idx = model.index(0, 0)
        flags = model.flags(idx)

        assert flags & Qt.ItemFlag.ItemIsEnabled
        assert flags & Qt.ItemFlag.ItemIsSelectable
        assert not (flags & Qt.ItemFlag.ItemIsEditable)

    def test_get_cell_value(self, model):
        """Test get_cell_value helper."""
        assert model.get_cell_value(0, 1) == "Alice"
        assert model.get_cell_value(2, 1) == "Charlie"

    def test_get_row_data(self, model):
        """Test get_row_data helper."""
        row = model.get_row_data(0)
        assert row[0] == "1"
        assert row[1] == "Alice"
        assert row[2] == "10.50"

    def test_get_columns(self, model):
        """Test get_columns helper."""
        cols = model.get_columns()
        assert cols == ["id", "name", "value", "active"]

    def test_clear(self, model, qapp):
        """Test clearing the model."""
        model.clear()
        assert model.rowCount() == 0
        assert model.columnCount() == 0


class TestDataFrameTableModelSorting:
    """Test sorting functionality."""

    @pytest.fixture
    def model(self, qapp):
        """Create a model with unsorted data."""
        df = pd.DataFrame({
            'id': [3, 1, 4, 1, 5],
            'name': ['Charlie', 'Alice', 'David', 'Bob', 'Eve'],
            'value': [30.0, 10.0, 40.0, 20.0, 50.0],
        })
        model = DataFrameTableModel()
        model.set_dataframe(df)
        return model

    def test_sort_ascending(self, model, qapp):
        """Test ascending sort."""
        model.sort(0, Qt.SortOrder.AscendingOrder)

        # IDs should now be sorted: 1, 1, 3, 4, 5
        assert model.get_cell_value(0, 0) == "1"
        assert model.get_cell_value(1, 0) == "1"
        assert model.get_cell_value(2, 0) == "3"

    def test_sort_descending(self, model, qapp):
        """Test descending sort."""
        model.sort(0, Qt.SortOrder.DescendingOrder)

        # IDs should now be sorted: 5, 4, 3, 1, 1
        assert model.get_cell_value(0, 0) == "5"
        assert model.get_cell_value(1, 0) == "4"

    def test_sort_by_string_column(self, model, qapp):
        """Test sorting by string column."""
        model.sort(1, Qt.SortOrder.AscendingOrder)

        # Names should be sorted alphabetically
        assert model.get_cell_value(0, 1) == "Alice"
        assert model.get_cell_value(1, 1) == "Bob"
        assert model.get_cell_value(2, 1) == "Charlie"

    def test_multi_column_sort(self, model, qapp):
        """Test multi-column sorting."""
        model.sort_by_columns(
            [0, 1],  # Sort by id, then name
            [Qt.SortOrder.AscendingOrder, Qt.SortOrder.AscendingOrder]
        )

        # For id=1, Alice should come before Bob
        assert model.get_cell_value(0, 0) == "1"
        assert model.get_cell_value(0, 1) == "Alice"
        assert model.get_cell_value(1, 0) == "1"
        assert model.get_cell_value(1, 1) == "Bob"


class TestDataFrameTableModelLargeDataset:
    """Test with large datasets to verify performance."""

    @pytest.fixture
    def large_df(self):
        """Create a large DataFrame (100k rows)."""
        n = 100_000
        return pd.DataFrame({
            'id': np.arange(n),
            'value': np.random.randn(n),
            'category': np.random.choice(['A', 'B', 'C'], n),
        })

    def test_large_dataset_creation(self, qapp, large_df):
        """Test creating model with large dataset."""
        model = DataFrameTableModel()
        model.set_dataframe(large_df)

        assert model.rowCount() == 100_000
        assert model.columnCount() == 3

    def test_large_dataset_data_access(self, qapp, large_df):
        """Test accessing data in large dataset."""
        model = DataFrameTableModel()
        model.set_dataframe(large_df)

        # Access first row
        assert model.get_cell_value(0, 0) == "0"

        # Access last row
        assert model.get_cell_value(99_999, 0) == "99999"

        # Access middle row
        assert model.get_cell_value(50_000, 0) == "50000"


class TestVirtualScrollThreshold:
    """Test the virtual scroll threshold constant."""

    def test_threshold_value(self):
        """Test that threshold is reasonable."""
        assert VIRTUAL_SCROLL_THRESHOLD == 50_000

    def test_small_dataset_below_threshold(self):
        """Test that small datasets are below threshold."""
        df = pd.DataFrame({'a': range(10_000)})
        assert len(df) < VIRTUAL_SCROLL_THRESHOLD

    def test_large_dataset_above_threshold(self):
        """Test that large datasets are above threshold."""
        df = pd.DataFrame({'a': range(100_000)})
        assert len(df) >= VIRTUAL_SCROLL_THRESHOLD
