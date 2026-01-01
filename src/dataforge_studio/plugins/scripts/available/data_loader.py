"""
Data Loader Module - Import files into SQL Server database.

This script imports CSV/Excel/JSON files from contract/dataset folders
into database tables.
"""
import shutil
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_FIELD_TYPE = "NVARCHAR(MAX)"
DEFAULT_IMPORTED_FOLDER = "_Imported"
DEFAULT_ERROR_FOLDER = "_Error"


class DataLoader:
    """Handles loading data files into database tables."""

    def __init__(
        self,
        connection_string: str,
        imported_folder_name: str = DEFAULT_IMPORTED_FOLDER,
        error_folder_name: str = DEFAULT_ERROR_FOLDER,
        field_type: str = DEFAULT_FIELD_TYPE
    ):
        self.connection_string = connection_string
        self.imported_folder_name = imported_folder_name
        self.error_folder_name = error_folder_name
        self.field_type = field_type
        self.stats = {
            "files_processed": 0,
            "files_imported": 0,
            "files_failed": 0,
            "tables_created": 0,
            "tables_updated": 0
        }

    def load_all_files(self, root_folder: Path) -> dict:
        """
        Load all files from contract/dataset folders into database.

        Returns:
            Statistics about the operation
        """
        self.stats = {
            "files_processed": 0,
            "files_imported": 0,
            "files_failed": 0,
            "tables_created": 0,
            "tables_updated": 0
        }

        root_folder = Path(root_folder)
        if not root_folder.exists():
            raise ValueError(f"Root folder does not exist: {root_folder}")

        contract_folders = [
            folder for folder in root_folder.iterdir()
            if folder.is_dir() and not folder.name.startswith("_")
        ]

        for contract_folder in contract_folders:
            self._process_contract_folder(contract_folder)

        return self.stats

    def _process_contract_folder(self, contract_folder: Path) -> None:
        """Process all dataset folders within a contract folder."""
        contract_name = contract_folder.name

        dataset_folders = [
            folder for folder in contract_folder.iterdir()
            if folder.is_dir() and folder.name not in [
                self.imported_folder_name, self.error_folder_name
            ]
        ]

        for dataset_folder in dataset_folders:
            self._process_dataset_folder(contract_name, dataset_folder)

    def _process_dataset_folder(self, contract_name: str, dataset_folder: Path) -> None:
        """Process all files within a dataset folder."""
        dataset_name = dataset_folder.name
        table_name = f"{contract_name}_{dataset_name}"

        imported_folder = dataset_folder / self.imported_folder_name
        error_folder = dataset_folder / self.error_folder_name
        imported_folder.mkdir(exist_ok=True)
        error_folder.mkdir(exist_ok=True)

        files = [f for f in dataset_folder.iterdir() if f.is_file()]

        for file_path in files:
            self.stats["files_processed"] += 1
            try:
                self._import_file(file_path, table_name, imported_folder)
                self.stats["files_imported"] += 1
            except Exception as e:
                logger.error(f"Error importing file {file_path.name}: {e}")
                self._move_to_error(file_path, error_folder)
                self.stats["files_failed"] += 1

    def _import_file(self, file_path: Path, table_name: str, imported_folder: Path) -> None:
        """Import a single file into the database table."""
        import pyodbc

        logger.info(f"Importing {file_path.name} into table {table_name}...")

        df = self._read_file(file_path)

        if df is None or df.empty:
            raise ValueError(f"File is empty or could not be read: {file_path.name}")

        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()

            table_exists = self._table_exists(cursor, table_name)

            if not table_exists:
                self._create_table(cursor, table_name, df.columns)
                conn.commit()
                self.stats["tables_created"] += 1
                logger.info(f"Created table: {table_name}")
            else:
                self._truncate_table(cursor, table_name)
                self._add_missing_columns(cursor, table_name, df.columns)
                conn.commit()
                self.stats["tables_updated"] += 1
                logger.info(f"Updated table structure: {table_name}")

            self._insert_data(cursor, table_name, df)
            conn.commit()
            logger.info(f"Inserted {len(df)} rows into {table_name}")

        destination = imported_folder / file_path.name
        shutil.move(str(file_path), str(destination))
        logger.info(f"Moved to imported folder: {file_path.name}")

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read file into pandas DataFrame with automatic format detection."""
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            return self._read_csv_with_detection(file_path)
        elif suffix in [".xlsx", ".xls"]:
            return pd.read_excel(file_path, dtype=str, keep_default_na=False)
        elif suffix == ".json":
            return pd.read_json(file_path, dtype=str)
        elif suffix == ".txt":
            return self._read_csv_with_detection(file_path, default_sep="\t")
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def _read_csv_with_detection(
        self,
        file_path: Path,
        default_sep: Optional[str] = None
    ) -> pd.DataFrame:
        """Read CSV file with automatic encoding and separator detection."""
        encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'windows-1252', 'cp1252', 'latin1']
        separators = [',', ';', '\t', '|'] if default_sep is None else [default_sep]

        best_result = None
        best_column_count = 0
        last_error = None

        for encoding in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(
                        file_path,
                        sep=sep,
                        encoding=encoding,
                        dtype=str,
                        keep_default_na=False,
                        on_bad_lines='skip',
                        engine='python',
                        encoding_errors='replace'
                    )

                    column_count = len(df.columns)

                    if column_count > best_column_count and len(df) > 0:
                        best_result = df
                        best_column_count = column_count

                        if column_count > 1:
                            logger.info(
                                f"Successfully read {file_path.name} with "
                                f"encoding={encoding}, separator='{sep}', "
                                f"{column_count} columns"
                            )
                            return df

                except Exception as e:
                    last_error = e
                    continue

        if best_result is not None and len(best_result) > 0:
            logger.info(f"Read {file_path.name} with {best_column_count} column(s)")
            return best_result

        if last_error:
            raise ValueError(
                f"Could not read file {file_path.name} with any "
                f"encoding/separator combination. Last error: {last_error}"
            )

        raise ValueError(
            f"Could not read file {file_path.name}: "
            "file appears to be empty or malformed"
        )

    def _table_exists(self, cursor, table_name: str) -> bool:
        """Check if table exists in database."""
        query = """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = ?
        """
        cursor.execute(query, table_name)
        count = cursor.fetchone()[0]
        return count > 0

    def _create_table(self, cursor, table_name: str, columns: List[str]) -> None:
        """Create a new table with all columns as NVARCHAR(MAX)."""
        columns_def = ", ".join([f"[{col}] {self.field_type}" for col in columns])
        query = f"CREATE TABLE [{table_name}] ({columns_def})"
        cursor.execute(query)

    def _truncate_table(self, cursor, table_name: str) -> None:
        """Empty the table."""
        query = f"TRUNCATE TABLE [{table_name}]"
        cursor.execute(query)

    def _add_missing_columns(self, cursor, table_name: str, file_columns: List[str]) -> None:
        """Add missing columns to existing table."""
        query = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
        """
        cursor.execute(query, table_name)
        existing_columns = set(row[0] for row in cursor.fetchall())

        for column in file_columns:
            if column not in existing_columns:
                alter_query = f"ALTER TABLE [{table_name}] ADD [{column}] {self.field_type}"
                cursor.execute(alter_query)
                logger.info(f"Added column [{column}] to table {table_name}")

    def _insert_data(self, cursor, table_name: str, df: pd.DataFrame) -> None:
        """Insert data from DataFrame into table."""
        df = df.fillna("")

        columns = ", ".join([f"[{col}]" for col in df.columns])
        placeholders = ", ".join(["?" for _ in df.columns])
        query = f"INSERT INTO [{table_name}] ({columns}) VALUES ({placeholders})"

        data = [tuple(row) for row in df.values]
        cursor.executemany(query, data)

    def _move_to_error(self, file_path: Path, error_folder: Path) -> None:
        """Move file to error folder."""
        destination = error_folder / file_path.name
        counter = 1
        while destination.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            destination = error_folder / f"{stem}_{counter}{suffix}"
            counter += 1

        shutil.move(str(file_path), str(destination))
        logger.error(f"Moved to error folder: {file_path.name}")


def run(
    root_folder: str,
    connection_string: str,
    dry_run: bool = False
) -> dict:
    """
    Entry point for script execution.

    Args:
        root_folder: Path to the root folder containing contract/dataset folders
        connection_string: Database connection string
        dry_run: If True, only simulate the operation

    Returns:
        Statistics dictionary
    """
    loader = DataLoader(connection_string=connection_string)

    if dry_run:
        logger.info("DRY RUN - No data will be imported")
        # TODO: Implement dry run logic
        return {
            "files_processed": 0,
            "files_imported": 0,
            "files_failed": 0,
            "tables_created": 0,
            "tables_updated": 0,
            "dry_run": True
        }

    return loader.load_all_files(Path(root_folder))
