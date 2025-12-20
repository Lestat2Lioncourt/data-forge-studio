"""
Unit tests for DataLoader module
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from dataforge_studio.core.data_loader import (
    csv_to_dataframe, json_to_dataframe, excel_to_dataframe,
    DataLoadResult, LoadWarningLevel
)


class TestDataLoader:
    """Test suite for DataLoader class"""

    @pytest.fixture
    def mock_connection_string(self):
        """Mock connection string"""
        return "DRIVER={SQL Server};SERVER=localhost;DATABASE=test;UID=user;PWD=pass"

    @pytest.fixture
    def loader(self, mock_connection_string):
        """Create DataLoader instance"""
        return DataLoader(connection_string=mock_connection_string)

    @pytest.fixture
    def temp_data_structure(self, tmp_path):
        """Create temporary data folder structure"""
        root = tmp_path / "data"
        root.mkdir()

        # Create contract/dataset structure
        contract = root / "ContractA"
        contract.mkdir()
        dataset = contract / "dataset_sales"
        dataset.mkdir()

        return root, contract, dataset

    def test_initialization(self, loader, mock_connection_string):
        """Test DataLoader initialization"""
        assert loader.connection_string == mock_connection_string
        assert loader.stats["files_processed"] == 0
        assert loader.stats["files_imported"] == 0
        assert loader.stats["files_failed"] == 0
        assert loader.stats["tables_created"] == 0
        assert loader.stats["tables_updated"] == 0

    def test_read_csv_file(self, loader, tmp_path):
        """Test reading CSV file"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Name,Age,City\nJohn,30,Paris\nJane,25,London")

        df = loader._read_file(csv_file)

        assert len(df) == 2
        assert list(df.columns) == ["Name", "Age", "City"]
        assert df.loc[0, "Name"] == "John"
        assert df.loc[1, "City"] == "London"

    def test_read_csv_with_semicolon(self, loader, tmp_path):
        """Test reading CSV file with semicolon separator"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Name;Age;City\nJohn;30;Paris\nJane;25;London")

        df = loader._read_file(csv_file)

        assert len(df) == 2
        assert list(df.columns) == ["Name", "Age", "City"]

    def test_read_csv_with_encoding(self, loader, tmp_path):
        """Test reading CSV file with different encoding"""
        csv_file = tmp_path / "test.csv"
        # Write with latin-1 encoding
        csv_file.write_bytes("Name,City\nJohn,Montréal\n".encode('latin-1'))

        df = loader._read_file(csv_file)

        assert len(df) == 1
        assert "Name" in df.columns
        assert "City" in df.columns

    @pytest.mark.skipif(
        not __import__('importlib.util').util.find_spec('openpyxl'),
        reason="openpyxl not installed"
    )
    def test_read_excel_file(self, loader, tmp_path):
        """Test reading Excel file"""
        excel_file = tmp_path / "test.xlsx"
        df_original = pd.DataFrame({
            "Name": ["John", "Jane"],
            "Age": [30, 25],
            "City": ["Paris", "London"]
        })
        df_original.to_excel(excel_file, index=False)

        df = loader._read_file(excel_file)

        assert len(df) == 2
        assert list(df.columns) == ["Name", "Age", "City"]

    def test_read_json_file(self, loader, tmp_path):
        """Test reading JSON file"""
        json_file = tmp_path / "test.json"
        json_file.write_text('[{"Name":"John","Age":30},{"Name":"Jane","Age":25}]')

        df = loader._read_file(json_file)

        assert len(df) == 2
        assert "Name" in df.columns
        assert "Age" in df.columns

    def test_read_unsupported_format(self, loader, tmp_path):
        """Test error when reading unsupported file format"""
        file = tmp_path / "test.pdf"
        file.write_text("dummy content")

        with pytest.raises(ValueError, match="Unsupported file format"):
            loader._read_file(file)

    def test_read_empty_file(self, loader, tmp_path):
        """Test reading empty CSV file"""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        with pytest.raises(ValueError, match="Could not read file"):
            loader._read_file(csv_file)

    @patch('pyodbc.connect')
    def test_table_exists(self, mock_connect, loader):
        """Test checking if table exists"""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        # This would normally be called within a context manager
        with patch.object(loader, 'connection_string', 'mock_connection'):
            cursor = mock_cursor
            result = loader._table_exists(cursor, "test_table")

        assert result is True
        mock_cursor.execute.assert_called_once()

    @patch('pyodbc.connect')
    def test_table_not_exists(self, mock_connect, loader):
        """Test checking if table doesn't exist"""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [0]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        cursor = mock_cursor
        result = loader._table_exists(cursor, "nonexistent_table")

        assert result is False

    def test_create_table(self, loader):
        """Test creating a new table"""
        mock_cursor = Mock()
        columns = ["Name", "Age", "City"]

        loader._create_table(mock_cursor, "test_table", columns)

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        assert "CREATE TABLE [test_table]" in call_args
        assert "[Name]" in call_args
        assert "[Age]" in call_args
        assert "[City]" in call_args

    def test_truncate_table(self, loader):
        """Test truncating a table"""
        mock_cursor = Mock()

        loader._truncate_table(mock_cursor, "test_table")

        mock_cursor.execute.assert_called_once_with("TRUNCATE TABLE [test_table]")

    def test_add_missing_columns(self, loader):
        """Test adding missing columns to existing table"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [("Name",), ("Age",)]

        file_columns = ["Name", "Age", "City", "Country"]

        loader._add_missing_columns(mock_cursor, "test_table", file_columns)

        # Should execute SELECT for existing columns, then ALTER for missing ones
        assert mock_cursor.execute.call_count == 3  # 1 SELECT + 2 ALTERs
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        assert any("ALTER TABLE" in str(call) and "[City]" in str(call) for call in calls)
        assert any("ALTER TABLE" in str(call) and "[Country]" in str(call) for call in calls)

    def test_insert_data(self, loader):
        """Test inserting data into table"""
        mock_cursor = Mock()
        df = pd.DataFrame({
            "Name": ["John", "Jane"],
            "Age": ["30", "25"],
            "City": ["Paris", "London"]
        })

        loader._insert_data(mock_cursor, "test_table", df)

        mock_cursor.executemany.assert_called_once()
        call_args = mock_cursor.executemany.call_args
        query = call_args[0][0]
        data = call_args[0][1]

        assert "INSERT INTO [test_table]" in query
        assert "[Name]" in query and "[Age]" in query and "[City]" in query
        assert len(data) == 2
        assert data[0] == ("John", "30", "Paris")
        assert data[1] == ("Jane", "25", "London")

    def test_move_to_error(self, loader, tmp_path):
        """Test moving file to error folder"""
        # Create test file
        test_file = tmp_path / "test.csv"
        test_file.write_text("data")

        error_folder = tmp_path / "error"
        error_folder.mkdir()

        loader._move_to_error(test_file, error_folder)

        assert not test_file.exists()
        assert (error_folder / "test.csv").exists()

    def test_move_to_error_with_duplicate(self, loader, tmp_path):
        """Test moving file to error folder when duplicate exists"""
        # Create test file
        test_file = tmp_path / "test.csv"
        test_file.write_text("data1")

        error_folder = tmp_path / "error"
        error_folder.mkdir()

        # Create duplicate
        (error_folder / "test.csv").write_text("data2")

        loader._move_to_error(test_file, error_folder)

        assert not test_file.exists()
        assert (error_folder / "test_1.csv").exists()

    @patch('pyodbc.connect')
    @patch.object(DataLoader, '_read_file')
    def test_import_file_new_table(self, mock_read_file, mock_connect, loader, tmp_path):
        """Test importing file and creating new table"""
        # Setup
        test_file = tmp_path / "test.csv"
        test_file.write_text("Name,Age\nJohn,30")

        imported_folder = tmp_path / "imported"
        imported_folder.mkdir()

        df = pd.DataFrame({"Name": ["John"], "Age": ["30"]})
        mock_read_file.return_value = df

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [0]  # Table doesn't exist
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        # Execute
        loader._import_file(test_file, "test_table", imported_folder)

        # Verify table was created
        assert loader.stats["tables_created"] == 1
        assert not test_file.exists()
        assert (imported_folder / "test.csv").exists()

    @patch('pyodbc.connect')
    @patch.object(DataLoader, '_read_file')
    def test_import_file_existing_table(self, mock_read_file, mock_connect, loader, tmp_path):
        """Test importing file into existing table"""
        # Setup
        test_file = tmp_path / "test.csv"
        test_file.write_text("Name,Age\nJohn,30")

        imported_folder = tmp_path / "imported"
        imported_folder.mkdir()

        df = pd.DataFrame({"Name": ["John"], "Age": ["30"]})
        mock_read_file.return_value = df

        mock_cursor = Mock()
        # First call: table exists, second call: get existing columns
        mock_cursor.fetchone.return_value = [1]
        mock_cursor.fetchall.return_value = [("Name",), ("Age",)]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        # Execute
        loader._import_file(test_file, "test_table", imported_folder)

        # Verify table was updated
        assert loader.stats["tables_updated"] == 1

    def test_process_dataset_folder(self, loader, temp_data_structure, tmp_path):
        """Test processing dataset folder"""
        root, contract, dataset = temp_data_structure

        # Create test files in dataset
        (dataset / "file1.csv").write_text("Name,Age\nJohn,30")
        (dataset / "file2.csv").write_text("Name,Age\nJane,25")

        with patch.object(loader, '_import_file') as mock_import:
            loader._process_dataset_folder("ContractA", dataset)

            # Should have tried to import both files
            assert mock_import.call_count == 2
            assert loader.stats["files_processed"] == 2

    @patch.object(DataLoader, '_process_contract_folder')
    def test_load_all_files(self, mock_process_contract, loader, temp_data_structure):
        """Test loading all files from root folder"""
        root, contract, dataset = temp_data_structure

        stats = loader.load_all_files(root_folder=root)

        # Should process the contract folder
        mock_process_contract.assert_called_once()
        assert stats is not None
        assert "files_processed" in stats

    def test_load_all_files_nonexistent_root(self, loader, tmp_path):
        """Test error when root folder doesn't exist"""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Root folder does not exist"):
            loader.load_all_files(root_folder=nonexistent)

    def test_stats_reset_on_load(self, loader, temp_data_structure):
        """Test that stats are reset when load_all_files is called"""
        root, contract, dataset = temp_data_structure

        # Set some initial stats
        loader.stats = {
            "files_processed": 10,
            "files_imported": 5,
            "files_failed": 2,
            "tables_created": 3,
            "tables_updated": 1
        }

        with patch.object(loader, '_process_contract_folder'):
            stats = loader.load_all_files(root_folder=root)

        # Stats should be reset
        assert stats["files_processed"] == 0
        assert stats["files_imported"] == 0
        assert stats["files_failed"] == 0
        assert stats["tables_created"] == 0
        assert stats["tables_updated"] == 0
