"""
Data Loader - Universal data loading functions to pandas DataFrame.

This module provides a unified interface to load data from various sources
into pandas DataFrame, which serves as the pivot format for the application.

Supported sources:
- CSV files (with encoding detection)
- JSON files (records or nested)
- Excel files (.xlsx, .xls)
- SQL queries (via connection)

Features:
- Large dataset warning (configurable threshold)
- Encoding detection for text files
- Progress callback for long operations
- Chunked loading for very large datasets
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Union, Iterator, Any, List

import pandas as pd

logger = logging.getLogger(__name__)

# Threshold for large dataset warning (number of rows)
LARGE_DATASET_THRESHOLD = 100_000

# Default chunk size for streaming large datasets
DEFAULT_CHUNK_SIZE = 10_000


class LoadWarningLevel(Enum):
    """Warning levels for data loading operations."""
    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DataLoadResult:
    """
    Result of a data loading operation.

    Attributes:
        dataframe: The loaded DataFrame (None if error or user cancelled)
        row_count: Number of rows loaded (or estimated)
        column_count: Number of columns
        warning_level: Level of warning (NONE, INFO, WARNING, ERROR)
        warning_message: Human-readable warning message
        is_truncated: True if data was truncated due to size limits
        source_info: Additional info about the source (encoding, separator, etc.)
        error: Exception if loading failed
    """
    dataframe: Optional[pd.DataFrame] = None
    row_count: int = 0
    column_count: int = 0
    warning_level: LoadWarningLevel = LoadWarningLevel.NONE
    warning_message: str = ""
    is_truncated: bool = False
    source_info: dict = field(default_factory=dict)
    error: Optional[Exception] = None

    @property
    def success(self) -> bool:
        """Returns True if loading was successful."""
        return self.dataframe is not None and self.error is None

    @property
    def is_large_dataset(self) -> bool:
        """Returns True if dataset exceeds the large dataset threshold."""
        return self.row_count > LARGE_DATASET_THRESHOLD


def _detect_encoding(file_path: Path, sample_size: int = 100000) -> str:
    """
    Detect file encoding by trying common encodings.

    Args:
        file_path: Path to the file
        sample_size: Number of bytes to sample (default 100KB for better detection)

    Returns:
        Detected encoding name
    """
    with open(file_path, 'rb') as f:
        raw = f.read(sample_size)

    # Check for BOM markers first
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        return 'utf-16'

    # Try UTF-8 first (most common)
    try:
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass

    # Try Windows encodings (common for French/European data)
    for encoding in ['cp1252', 'iso-8859-1', 'latin-1']:
        try:
            raw.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue

    # Fallback to latin-1 which accepts any byte sequence
    return 'latin-1'


def _detect_csv_separator(file_path: Path, encoding: str = 'utf-8') -> str:
    """
    Detect CSV separator by analyzing the first few lines.

    Args:
        file_path: Path to CSV file
        encoding: File encoding

    Returns:
        Detected separator character
    """
    separators = [',', ';', '\t', '|']

    try:
        with open(file_path, 'r', encoding=encoding) as f:
            # Read first 5 lines
            lines = [f.readline() for _ in range(5)]
            sample = ''.join(lines)

        # Count occurrences of each separator
        counts = {sep: sample.count(sep) for sep in separators}

        # Return the separator with highest count (if significant)
        max_sep = max(counts, key=counts.get)
        if counts[max_sep] > 0:
            return max_sep
    except Exception:
        pass

    return ','  # Default to comma


def _count_csv_rows(file_path: Path, encoding: str = 'utf-8') -> int:
    """
    Count rows in a CSV file efficiently (without loading all data).

    Args:
        file_path: Path to CSV file
        encoding: File encoding

    Returns:
        Number of data rows (excluding header)
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            # Count lines and subtract 1 for header
            return sum(1 for _ in f) - 1
    except Exception:
        return -1  # Unknown


def csv_to_dataframe(
    path: Union[str, Path],
    encoding: Optional[str] = None,
    separator: Optional[str] = None,
    nrows: Optional[int] = None,
    skip_large_warning: bool = False,
    on_large_dataset: Optional[Callable[[int], bool]] = None
) -> DataLoadResult:
    """
    Load a CSV file into a DataFrame.

    Args:
        path: Path to the CSV file
        encoding: File encoding (auto-detected if None)
        separator: Column separator (auto-detected if None)
        nrows: Maximum number of rows to load (None = all)
        skip_large_warning: If True, skip the large dataset warning
        on_large_dataset: Callback when large dataset detected.
                         Receives row_count, returns True to proceed, False to cancel.

    Returns:
        DataLoadResult with DataFrame and metadata
    """
    path = Path(path)
    result = DataLoadResult()

    try:
        # Auto-detect encoding if not specified
        if encoding is None:
            encoding = _detect_encoding(path)

        result.source_info['encoding'] = encoding

        # Auto-detect separator if not specified
        if separator is None:
            separator = _detect_csv_separator(path, encoding)

        result.source_info['separator'] = separator

        # Count rows first to check for large dataset
        row_count = _count_csv_rows(path, encoding)
        result.source_info['total_rows'] = row_count

        # Check for large dataset
        if row_count > LARGE_DATASET_THRESHOLD and not skip_large_warning:
            result.warning_level = LoadWarningLevel.WARNING
            result.warning_message = (
                f"Large dataset detected: {row_count:,} rows "
                f"(threshold: {LARGE_DATASET_THRESHOLD:,}). "
                f"Loading may be slow and consume significant memory."
            )

            # Call callback if provided
            if on_large_dataset is not None:
                proceed = on_large_dataset(row_count)
                if not proceed:
                    result.warning_message = "Loading cancelled by user."
                    result.warning_level = LoadWarningLevel.INFO
                    return result

        # Load the data
        df = pd.read_csv(
            path,
            encoding=encoding,
            sep=separator,
            nrows=nrows,
            low_memory=False  # Avoid mixed type warnings
        )

        result.dataframe = df
        result.row_count = len(df)
        result.column_count = len(df.columns)
        result.is_truncated = nrows is not None and row_count > nrows

        logger.info(f"Loaded CSV: {path.name} ({result.row_count} rows, {result.column_count} cols)")

    except Exception as e:
        result.error = e
        result.warning_level = LoadWarningLevel.ERROR
        result.warning_message = f"Failed to load CSV: {str(e)}"
        logger.error(f"Error loading CSV {path}: {e}")

    return result


def json_to_dataframe(
    path: Union[str, Path],
    orient: Optional[str] = None,
    nrows: Optional[int] = None,
    skip_large_warning: bool = False,
    on_large_dataset: Optional[Callable[[int], bool]] = None
) -> DataLoadResult:
    """
    Load a JSON file into a DataFrame.

    Args:
        path: Path to the JSON file
        orient: JSON orientation ('records', 'columns', 'index', etc.)
                Auto-detected if None.
        nrows: Maximum number of rows to load (None = all)
        skip_large_warning: If True, skip the large dataset warning
        on_large_dataset: Callback when large dataset detected.

    Returns:
        DataLoadResult with DataFrame and metadata
    """
    path = Path(path)
    result = DataLoadResult()

    try:
        import json

        # First, peek at the JSON structure to determine orient
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            data = json.loads(content)

        # Determine structure
        if isinstance(data, list):
            result.source_info['structure'] = 'array'
            row_count = len(data)

            # Check for large dataset
            if row_count > LARGE_DATASET_THRESHOLD and not skip_large_warning:
                result.warning_level = LoadWarningLevel.WARNING
                result.warning_message = (
                    f"Large dataset detected: {row_count:,} rows "
                    f"(threshold: {LARGE_DATASET_THRESHOLD:,})."
                )

                if on_large_dataset is not None:
                    proceed = on_large_dataset(row_count)
                    if not proceed:
                        result.warning_message = "Loading cancelled by user."
                        result.warning_level = LoadWarningLevel.INFO
                        return result

            # Load as records
            df = pd.DataFrame(data)

            if nrows is not None:
                df = df.head(nrows)
                result.is_truncated = row_count > nrows

        elif isinstance(data, dict):
            result.source_info['structure'] = 'object'

            # Check for row-keyed structure: {"row1": {...}, "row2": {...}}
            # All values must be dicts with similar keys
            if len(data) >= 2 and all(isinstance(v, dict) for v in data.values()):
                # Collect all keys from sub-dicts to check similarity
                all_keys = [set(v.keys()) for v in data.values()]
                # Check if there's significant overlap (at least 50% common keys)
                if all_keys:
                    common_keys = all_keys[0]
                    for keys in all_keys[1:]:
                        common_keys = common_keys & keys

                    # If sub-dicts share at least one common key, treat as row-keyed
                    if len(common_keys) > 0:
                        result.source_info['structure'] = 'row_keyed'
                        # Convert to list of records, adding the key as '_id' column
                        records = []
                        for key, value in data.items():
                            record = {'_id': key, **value}
                            records.append(record)
                        df = pd.DataFrame(records)

                        row_count = len(df)
                        if row_count > LARGE_DATASET_THRESHOLD and not skip_large_warning:
                            result.warning_level = LoadWarningLevel.WARNING
                            result.warning_message = (
                                f"Large dataset detected: {row_count:,} rows "
                                f"(threshold: {LARGE_DATASET_THRESHOLD:,})."
                            )
                            if on_large_dataset is not None:
                                proceed = on_large_dataset(row_count)
                                if not proceed:
                                    result.warning_message = "Loading cancelled by user."
                                    result.warning_level = LoadWarningLevel.INFO
                                    return result

                        if nrows is not None:
                            df = df.head(nrows)
                            result.is_truncated = row_count > nrows

                        result.dataframe = df
                        result.row_count = len(df)
                        result.column_count = len(df.columns)
                        logger.info(f"Loaded JSON (row-keyed): {path.name} ({result.row_count} rows)")
                        return result

            # Check for columns-oriented: {"col1": [...], "col2": [...]}
            if all(isinstance(v, list) for v in data.values()):
                result.source_info['structure'] = 'columns'
                df = pd.DataFrame(data)
            else:
                # Fallback: try json_normalize for nested objects, or single record
                try:
                    df = pd.json_normalize(data)
                except Exception:
                    df = pd.DataFrame([data])
        else:
            raise ValueError(f"Unsupported JSON structure: {type(data)}")

        result.dataframe = df
        result.row_count = len(df)
        result.column_count = len(df.columns)

        logger.info(f"Loaded JSON: {path.name} ({result.row_count} rows, {result.column_count} cols)")

    except Exception as e:
        result.error = e
        result.warning_level = LoadWarningLevel.ERROR
        result.warning_message = f"Failed to load JSON: {str(e)}"
        logger.error(f"Error loading JSON {path}: {e}")

    return result


def excel_to_dataframe(
    path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = 0,
    nrows: Optional[int] = None,
    skip_large_warning: bool = False,
    on_large_dataset: Optional[Callable[[int], bool]] = None
) -> DataLoadResult:
    """
    Load an Excel file into a DataFrame.

    Args:
        path: Path to the Excel file (.xlsx or .xls)
        sheet_name: Sheet name or index (0-based). Default is first sheet.
        nrows: Maximum number of rows to load (None = all)
        skip_large_warning: If True, skip the large dataset warning
        on_large_dataset: Callback when large dataset detected.

    Returns:
        DataLoadResult with DataFrame and metadata
    """
    path = Path(path)
    result = DataLoadResult()

    try:
        # Determine engine based on extension
        if path.suffix.lower() == '.xls':
            engine = 'xlrd'
        else:
            engine = 'openpyxl'

        result.source_info['engine'] = engine
        result.source_info['sheet'] = sheet_name

        # Get sheet names
        excel_file = pd.ExcelFile(path, engine=engine)
        result.source_info['available_sheets'] = excel_file.sheet_names

        # First pass: count rows (if checking for large dataset)
        if not skip_large_warning:
            # Quick count by loading just first column
            df_count = pd.read_excel(
                path,
                sheet_name=sheet_name,
                engine=engine,
                usecols=[0],
                header=None
            )
            row_count = len(df_count) - 1  # Subtract header

            if row_count > LARGE_DATASET_THRESHOLD:
                result.warning_level = LoadWarningLevel.WARNING
                result.warning_message = (
                    f"Large dataset detected: {row_count:,} rows "
                    f"(threshold: {LARGE_DATASET_THRESHOLD:,})."
                )

                if on_large_dataset is not None:
                    proceed = on_large_dataset(row_count)
                    if not proceed:
                        result.warning_message = "Loading cancelled by user."
                        result.warning_level = LoadWarningLevel.INFO
                        return result

        # Load the full data
        df = pd.read_excel(
            path,
            sheet_name=sheet_name,
            engine=engine,
            nrows=nrows
        )

        result.dataframe = df
        result.row_count = len(df)
        result.column_count = len(df.columns)
        result.is_truncated = nrows is not None

        logger.info(f"Loaded Excel: {path.name} ({result.row_count} rows, {result.column_count} cols)")

    except Exception as e:
        result.error = e
        result.warning_level = LoadWarningLevel.ERROR
        result.warning_message = f"Failed to load Excel: {str(e)}"
        logger.error(f"Error loading Excel {path}: {e}")

    return result


def query_to_dataframe(
    connection: Any,
    sql: str,
    params: Optional[Union[tuple, dict]] = None,
    nrows: Optional[int] = None,
    skip_large_warning: bool = False,
    row_count_hint: Optional[int] = None,
    on_large_dataset: Optional[Callable[[int], bool]] = None,
    chunksize: Optional[int] = None
) -> Union[DataLoadResult, Iterator[pd.DataFrame]]:
    """
    Execute a SQL query and return results as DataFrame.

    Args:
        connection: Database connection (pyodbc, sqlite3, or SQLAlchemy)
        sql: SQL query string
        params: Query parameters (optional)
        nrows: Maximum number of rows to load (None = all)
        skip_large_warning: If True, skip the large dataset warning
        row_count_hint: Pre-computed row count (avoids COUNT query if provided)
        on_large_dataset: Callback when large dataset detected.
        chunksize: If provided, return an iterator yielding DataFrames of this size

    Returns:
        DataLoadResult with DataFrame and metadata, or Iterator if chunksize specified
    """
    result = DataLoadResult()

    try:
        result.source_info['sql'] = sql[:200] + '...' if len(sql) > 200 else sql

        # Check row count if not skipping warning and no hint provided
        if not skip_large_warning and row_count_hint is None:
            # Try to get row count with a COUNT query
            try:
                # Wrap the query to count rows
                count_sql = f"SELECT COUNT(*) FROM ({sql}) AS _count_subquery"

                cursor = connection.cursor()
                cursor.execute(count_sql)
                row_count_hint = cursor.fetchone()[0]
                cursor.close()

            except Exception:
                # COUNT query failed - proceed without warning
                pass

        # Check for large dataset
        if row_count_hint is not None:
            result.source_info['estimated_rows'] = row_count_hint

            if row_count_hint > LARGE_DATASET_THRESHOLD and not skip_large_warning:
                result.warning_level = LoadWarningLevel.WARNING
                result.warning_message = (
                    f"Large dataset detected: {row_count_hint:,} rows "
                    f"(threshold: {LARGE_DATASET_THRESHOLD:,}). "
                    f"Loading may be slow and consume significant memory."
                )

                if on_large_dataset is not None:
                    proceed = on_large_dataset(row_count_hint)
                    if not proceed:
                        result.warning_message = "Loading cancelled by user."
                        result.warning_level = LoadWarningLevel.INFO
                        return result

        # Chunked loading
        if chunksize is not None:
            return pd.read_sql(sql, connection, params=params, chunksize=chunksize)

        # Regular loading
        df = pd.read_sql(sql, connection, params=params)

        # Apply nrows limit after loading (pandas read_sql doesn't support nrows)
        if nrows is not None and len(df) > nrows:
            df = df.head(nrows)
            result.is_truncated = True

        result.dataframe = df
        result.row_count = len(df)
        result.column_count = len(df.columns)

        logger.info(f"Executed query: {result.row_count} rows, {result.column_count} cols")

    except Exception as e:
        result.error = e
        result.warning_level = LoadWarningLevel.ERROR
        result.warning_message = f"Query execution failed: {str(e)}"
        logger.error(f"Error executing query: {e}")

    return result


def dataframe_from_records(
    records: List[dict],
    columns: Optional[List[str]] = None
) -> DataLoadResult:
    """
    Create a DataFrame from a list of dictionaries.

    Args:
        records: List of dictionaries (each dict is a row)
        columns: Optional column order

    Returns:
        DataLoadResult with DataFrame
    """
    result = DataLoadResult()

    try:
        df = pd.DataFrame(records, columns=columns)
        result.dataframe = df
        result.row_count = len(df)
        result.column_count = len(df.columns)
        result.source_info['source'] = 'records'

    except Exception as e:
        result.error = e
        result.warning_level = LoadWarningLevel.ERROR
        result.warning_message = f"Failed to create DataFrame: {str(e)}"

    return result


def dataframe_to_records(df: pd.DataFrame) -> List[dict]:
    """
    Convert a DataFrame to a list of dictionaries.

    Args:
        df: Source DataFrame

    Returns:
        List of dictionaries (one per row)
    """
    return df.to_dict(orient='records')
