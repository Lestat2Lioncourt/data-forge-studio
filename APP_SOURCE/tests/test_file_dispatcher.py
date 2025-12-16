"""
Unit tests for FileDispatcher module
"""
import pytest
import shutil
from pathlib import Path
from src.core.file_dispatcher import FileDispatcher


class TestFileDispatcher:
    """Test suite for FileDispatcher class"""

    @pytest.fixture
    def temp_root(self, tmp_path):
        """Create temporary root folder structure for testing"""
        root = tmp_path / "data_root"
        root.mkdir()

        # Create contract/dataset structure
        contract1 = root / "Contract_A"
        contract1.mkdir()
        (contract1 / "dataset_sales").mkdir()
        (contract1 / "dataset_inventory").mkdir()

        contract2 = root / "Contract_B"
        contract2.mkdir()
        (contract2 / "dataset_orders").mkdir()

        # Create invalid folder
        invalid = tmp_path / "invalid"
        invalid.mkdir()

        return root

    @pytest.fixture
    def dispatcher(self, temp_root):
        """Create FileDispatcher instance with temp root"""
        return FileDispatcher(root_folder=temp_root)

    def test_initialization(self, dispatcher, temp_root):
        """Test FileDispatcher initialization"""
        assert dispatcher.root_folder == temp_root
        assert dispatcher.stats == {"dispatched": 0, "invalid": 0, "errors": 0}

    def test_get_contract_folders(self, dispatcher, temp_root):
        """Test getting list of contract folders"""
        contracts = dispatcher.get_contract_folders()
        assert len(contracts) == 2
        contract_names = {c.name for c in contracts}
        assert "Contract_A" in contract_names
        assert "Contract_B" in contract_names

    def test_get_contract_folders_excludes_special(self, dispatcher, temp_root):
        """Test that contract folders starting with _ are excluded"""
        # Create special folder
        (temp_root / "_Special").mkdir()

        contracts = dispatcher.get_contract_folders()
        contract_names = {c.name for c in contracts}
        assert "_Special" not in contract_names

    def test_get_dataset_folders(self, dispatcher, temp_root):
        """Test getting list of dataset folders"""
        contract_a = temp_root / "Contract_A"
        datasets = dispatcher.get_dataset_folders(contract_a)

        assert len(datasets) == 2
        dataset_names = {d.name for d in datasets}
        assert "dataset_sales" in dataset_names
        assert "dataset_inventory" in dataset_names

    def test_parse_filename_valid(self, dispatcher):
        """Test parsing valid filename"""
        contract, dataset = dispatcher._parse_filename("Contract_A_dataset_sales_2024.csv")
        assert contract == "Contract_A"
        assert dataset == "dataset_sales"

    def test_parse_filename_with_extension(self, dispatcher):
        """Test parsing filename with just extension (no underscore suffix)"""
        contract, dataset = dispatcher._parse_filename("Contract_A_dataset_sales.csv")
        assert contract == "Contract_A"
        assert dataset == "dataset_sales"

    def test_parse_filename_case_insensitive(self, dispatcher):
        """Test parsing with different case"""
        contract, dataset = dispatcher._parse_filename("contract_a_DATASET_SALES_2024.csv")
        assert contract == "Contract_A"
        assert dataset == "dataset_sales"

    def test_parse_filename_invalid(self, dispatcher):
        """Test parsing invalid filename"""
        contract, dataset = dispatcher._parse_filename("InvalidFile.csv")
        assert contract is None
        assert dataset is None

    def test_parse_filename_longest_match(self, dispatcher, temp_root):
        """Test that longest dataset name is matched first"""
        # Create datasets with similar names
        contract_a = temp_root / "Contract_A"
        (contract_a / "dataset_sales_report").mkdir()

        # Should match the longest
        contract, dataset = dispatcher._parse_filename("Contract_A_dataset_sales_report_2024.csv")
        assert dataset == "dataset_sales_report"

    def test_dispatch_single_file_success(self, dispatcher, temp_root):
        """Test successfully dispatching a single file"""
        # Create test file
        test_file = temp_root / "Contract_A_dataset_sales_2024.csv"
        test_file.write_text("test,data")

        dispatcher._dispatch_single_file(test_file)

        # Check file was moved to correct location
        expected_location = temp_root / "Contract_A" / "dataset_sales" / "Contract_A_dataset_sales_2024.csv"
        assert expected_location.exists()
        assert not test_file.exists()
        assert dispatcher.stats["dispatched"] == 1

    def test_dispatch_single_file_invalid(self, dispatcher, temp_root):
        """Test dispatching file with invalid name"""
        # Create test file with invalid name
        test_file = temp_root / "InvalidFile.csv"
        test_file.write_text("test,data")

        dispatcher._dispatch_single_file(test_file)

        # Check file was moved to invalid folder
        assert dispatcher.stats["invalid"] == 1
        assert not test_file.exists()

    def test_dispatch_files_multiple(self, dispatcher, temp_root):
        """Test dispatching multiple files"""
        # Create test files
        files = [
            temp_root / "Contract_A_dataset_sales_2024.csv",
            temp_root / "Contract_A_dataset_inventory_2024.csv",
            temp_root / "Contract_B_dataset_orders_2024.csv",
            temp_root / "InvalidFile.txt"
        ]

        for file in files:
            file.write_text("test,data")

        stats = dispatcher.dispatch_files()

        assert stats["dispatched"] == 3
        assert stats["invalid"] == 1
        assert stats["errors"] == 0

        # Verify files were moved correctly
        assert (temp_root / "Contract_A" / "dataset_sales" / "Contract_A_dataset_sales_2024.csv").exists()
        assert (temp_root / "Contract_A" / "dataset_inventory" / "Contract_A_dataset_inventory_2024.csv").exists()
        assert (temp_root / "Contract_B" / "dataset_orders" / "Contract_B_dataset_orders_2024.csv").exists()

    def test_move_to_invalid_with_duplicate(self, dispatcher, temp_root):
        """Test moving file to invalid folder when duplicate exists"""
        # Create test file
        test_file = temp_root / "test.csv"
        test_file.write_text("data1")

        # Create duplicate in invalid folder
        invalid_file = dispatcher.invalid_folder / "test.csv"
        invalid_file.write_text("data2")

        dispatcher._move_to_invalid(test_file)

        # Check file was renamed
        assert (dispatcher.invalid_folder / "test_1.csv").exists()
        assert dispatcher.stats["invalid"] == 1

    def test_dispatch_files_empty_folder(self, dispatcher, temp_root):
        """Test dispatching with no files in root folder"""
        stats = dispatcher.dispatch_files()

        assert stats["dispatched"] == 0
        assert stats["invalid"] == 0
        assert stats["errors"] == 0

    def test_dispatch_files_nonexistent_root(self, tmp_path):
        """Test error when root folder doesn't exist"""
        nonexistent = tmp_path / "nonexistent"
        dispatcher = FileDispatcher(root_folder=nonexistent)

        with pytest.raises(ValueError, match="Root folder does not exist"):
            dispatcher.dispatch_files()

    def test_dispatch_file_target_not_exists(self, dispatcher, temp_root):
        """Test dispatching file when target dataset folder doesn't exist"""
        # Create file for non-existent dataset
        test_file = temp_root / "Contract_A_dataset_nonexistent_2024.csv"
        test_file.write_text("test,data")

        dispatcher._dispatch_single_file(test_file)

        # Should be moved to invalid folder
        assert dispatcher.stats["invalid"] == 1
        assert not test_file.exists()

    def test_stats_reset_on_dispatch(self, dispatcher, temp_root):
        """Test that stats are reset when dispatch_files is called"""
        # Set some initial stats
        dispatcher.stats = {"dispatched": 10, "invalid": 5, "errors": 2}

        # Create a test file
        test_file = temp_root / "Contract_A_dataset_sales_2024.csv"
        test_file.write_text("test,data")

        stats = dispatcher.dispatch_files()

        # Stats should be reset
        assert stats["dispatched"] == 1
        assert stats["invalid"] == 0
        assert stats["errors"] == 0
