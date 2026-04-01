"""
Unit tests for Data Loader.
Tests csv_to_dataframe(), json_to_dataframe(), merge_folder_files(),
DataLoadResult, and MERGEABLE_EXTENSIONS.
"""
import json
import pytest
from pathlib import Path

import pandas as pd

from dataforge_studio.core.data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    merge_folder_files,
    dataframe_from_records,
    dataframe_to_records,
    DataLoadResult,
    LoadWarningLevel,
    MERGEABLE_EXTENSIONS,
    LARGE_DATASET_THRESHOLD,
)


class TestDataLoadResult:
    """Tests for the DataLoadResult dataclass."""

    def test_success_with_dataframe(self):
        """success is True when dataframe is present and no error."""
        result = DataLoadResult(dataframe=pd.DataFrame({"a": [1]}))
        assert result.success is True

    def test_failure_with_error(self):
        """success is False when error is set."""
        result = DataLoadResult(error=ValueError("fail"))
        assert result.success is False

    def test_failure_no_dataframe(self):
        """success is False when dataframe is None."""
        result = DataLoadResult()
        assert result.success is False

    def test_is_large_dataset(self):
        """is_large_dataset reflects the threshold."""
        result = DataLoadResult(row_count=LARGE_DATASET_THRESHOLD + 1)
        assert result.is_large_dataset is True

    def test_is_not_large_dataset(self):
        """is_large_dataset is False below threshold."""
        result = DataLoadResult(row_count=100)
        assert result.is_large_dataset is False

    def test_default_values(self):
        """Default values are sensible."""
        result = DataLoadResult()
        assert result.row_count == 0
        assert result.column_count == 0
        assert result.warning_level == LoadWarningLevel.NONE
        assert result.warning_message == ""
        assert result.is_truncated is False
        assert result.source_info == {}
        assert result.error is None


class TestMergeableExtensions:
    """Tests for MERGEABLE_EXTENSIONS constant."""

    def test_csv_supported(self):
        assert '.csv' in MERGEABLE_EXTENSIONS

    def test_xlsx_supported(self):
        assert '.xlsx' in MERGEABLE_EXTENSIONS

    def test_xls_supported(self):
        assert '.xls' in MERGEABLE_EXTENSIONS

    def test_json_supported(self):
        assert '.json' in MERGEABLE_EXTENSIONS

    def test_txt_not_supported(self):
        assert '.txt' not in MERGEABLE_EXTENSIONS


class TestCsvToDataframe:
    """Tests for csv_to_dataframe()."""

    def test_basic_csv(self, tmp_path):
        """Load a basic CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b,c\n1,2,3\n4,5,6\n", encoding="utf-8")

        result = csv_to_dataframe(csv_file)
        assert result.success is True
        assert result.row_count == 2
        assert result.column_count == 3
        assert list(result.dataframe.columns) == ["a", "b", "c"]

    def test_semicolon_separator(self, tmp_path):
        """Load a CSV with semicolon separator."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a;b;c\n1;2;3\n4;5;6\n", encoding="utf-8")

        result = csv_to_dataframe(csv_file)
        assert result.success is True
        assert result.column_count == 3

    def test_explicit_separator(self, tmp_path):
        """Load a CSV with explicit separator parameter."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a|b|c\n1|2|3\n", encoding="utf-8")

        result = csv_to_dataframe(csv_file, separator="|")
        assert result.success is True
        assert result.column_count == 3

    def test_explicit_encoding(self, tmp_path):
        """Load a CSV with explicit encoding."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name\nCafe\n", encoding="utf-8")

        result = csv_to_dataframe(csv_file, encoding="utf-8")
        assert result.success is True
        assert result.row_count == 1

    def test_nrows_limit(self, tmp_path):
        """Load a CSV with nrows limit."""
        csv_file = tmp_path / "test.csv"
        lines = ["x\n"] + [f"{i}\n" for i in range(100)]
        csv_file.write_text("".join(lines), encoding="utf-8")

        result = csv_to_dataframe(csv_file, nrows=10)
        assert result.success is True
        assert result.row_count == 10
        assert result.is_truncated is True

    def test_nonexistent_file(self, tmp_path):
        """csv_to_dataframe() returns error for missing file."""
        result = csv_to_dataframe(tmp_path / "missing.csv")
        assert result.success is False
        assert result.error is not None
        assert result.warning_level == LoadWarningLevel.ERROR

    def test_source_info_populated(self, tmp_path):
        """csv_to_dataframe() populates source_info."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n", encoding="utf-8")

        result = csv_to_dataframe(csv_file)
        assert 'encoding' in result.source_info
        assert 'separator' in result.source_info

    def test_utf8_bom(self, tmp_path):
        """Load a CSV with UTF-8 BOM encoding."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_bytes(b'\xef\xbb\xbfa,b\n1,2\n')

        result = csv_to_dataframe(csv_file)
        assert result.success is True
        assert result.source_info['encoding'] == 'utf-8-sig'


class TestJsonToDataframe:
    """Tests for json_to_dataframe()."""

    def test_array_of_objects(self, tmp_path):
        """Load a JSON array of objects."""
        json_file = tmp_path / "test.json"
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = json_to_dataframe(json_file)
        assert result.success is True
        assert result.row_count == 2
        assert result.column_count == 2

    def test_column_oriented(self, tmp_path):
        """Load a column-oriented JSON object."""
        json_file = tmp_path / "test.json"
        data = {"a": [1, 2, 3], "b": [4, 5, 6]}
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = json_to_dataframe(json_file)
        assert result.success is True
        assert result.row_count == 3
        assert result.column_count == 2

    def test_row_keyed_object(self, tmp_path):
        """Load a row-keyed JSON object (dict of dicts)."""
        json_file = tmp_path / "test.json"
        data = {
            "row1": {"name": "Alice", "age": 30},
            "row2": {"name": "Bob", "age": 25}
        }
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = json_to_dataframe(json_file)
        assert result.success is True
        assert result.row_count == 2
        assert "_id" in result.dataframe.columns

    def test_single_flat_object(self, tmp_path):
        """Load a single flat JSON object."""
        json_file = tmp_path / "test.json"
        data = {"name": "Alice", "age": 30}
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = json_to_dataframe(json_file)
        assert result.success is True
        assert result.row_count == 1

    def test_nrows_limit(self, tmp_path):
        """json_to_dataframe() respects nrows limit."""
        json_file = tmp_path / "test.json"
        data = [{"x": i} for i in range(100)]
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = json_to_dataframe(json_file, nrows=10)
        assert result.success is True
        assert result.row_count == 10
        assert result.is_truncated is True

    def test_invalid_json(self, tmp_path):
        """json_to_dataframe() returns error for invalid JSON."""
        json_file = tmp_path / "test.json"
        json_file.write_text("not valid json {{{", encoding="utf-8")

        result = json_to_dataframe(json_file)
        assert result.success is False
        assert result.error is not None

    def test_nonexistent_file(self, tmp_path):
        """json_to_dataframe() returns error for missing file."""
        result = json_to_dataframe(tmp_path / "missing.json")
        assert result.success is False

    def test_empty_array(self, tmp_path):
        """json_to_dataframe() handles empty array."""
        json_file = tmp_path / "test.json"
        json_file.write_text("[]", encoding="utf-8")

        result = json_to_dataframe(json_file)
        assert result.success is True
        assert result.row_count == 0


class TestMergeFolderFiles:
    """Tests for merge_folder_files()."""

    def test_merge_csv_files(self, tmp_path):
        """Merge multiple CSV files from a folder."""
        (tmp_path / "a.csv").write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
        (tmp_path / "b.csv").write_text("x,y\n5,6\n", encoding="utf-8")

        result = merge_folder_files(tmp_path)
        assert result.success is True
        assert result.row_count == 3
        assert "_source_file" in result.dataframe.columns
        assert result.source_info['files_loaded'] == 2

    def test_merge_csv_and_json(self, tmp_path):
        """Merge CSV and JSON files from the same folder."""
        (tmp_path / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        json_data = [{"a": 3, "b": 4}]
        (tmp_path / "data.json").write_text(json.dumps(json_data), encoding="utf-8")

        result = merge_folder_files(tmp_path)
        assert result.success is True
        assert result.row_count == 2

    def test_empty_folder(self, tmp_path):
        """merge_folder_files() returns error for folder with no data files."""
        result = merge_folder_files(tmp_path)
        assert result.success is False
        assert result.warning_level == LoadWarningLevel.ERROR

    def test_nonexistent_folder(self, tmp_path):
        """merge_folder_files() returns error for non-existent folder."""
        result = merge_folder_files(tmp_path / "nonexistent")
        assert result.success is False
        assert result.error is not None

    def test_ignores_unsupported_files(self, tmp_path):
        """merge_folder_files() ignores unsupported file types."""
        (tmp_path / "data.csv").write_text("a\n1\n", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")

        result = merge_folder_files(tmp_path)
        assert result.success is True
        assert result.source_info['files_loaded'] == 1

    def test_union_of_columns(self, tmp_path):
        """merge_folder_files() creates union of all columns."""
        (tmp_path / "a.csv").write_text("x,y\n1,2\n", encoding="utf-8")
        (tmp_path / "b.csv").write_text("x,z\n3,4\n", encoding="utf-8")

        result = merge_folder_files(tmp_path)
        assert result.success is True
        cols = set(result.dataframe.columns)
        assert "x" in cols
        assert "y" in cols
        assert "z" in cols
        assert "_source_file" in cols


class TestDataframeFromRecords:
    """Tests for dataframe_from_records()."""

    def test_basic(self):
        """Create DataFrame from list of dicts."""
        records = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        result = dataframe_from_records(records)
        assert result.success is True
        assert result.row_count == 2
        assert result.column_count == 2

    def test_with_column_order(self):
        """Create DataFrame with specified column order."""
        records = [{"b": 2, "a": 1}]
        result = dataframe_from_records(records, columns=["a", "b"])
        assert result.success is True
        assert list(result.dataframe.columns) == ["a", "b"]

    def test_empty_records(self):
        """Create DataFrame from empty list."""
        result = dataframe_from_records([])
        assert result.success is True
        assert result.row_count == 0


class TestDataframeToRecords:
    """Tests for dataframe_to_records()."""

    def test_basic(self):
        """Convert DataFrame to list of dicts."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        records = dataframe_to_records(df)
        assert len(records) == 2
        assert records[0] == {"a": 1, "b": 3}
        assert records[1] == {"a": 2, "b": 4}
