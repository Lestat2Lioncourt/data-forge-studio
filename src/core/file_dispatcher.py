"""
File Dispatcher Module - Step 1: Move files to their respective dataset folders
"""
import shutil
from pathlib import Path
from typing import List, Tuple
from ..utils.config import Config
from ..utils.logger import logger


class FileDispatcher:
    """Handles dispatching files from root folder to contract/dataset folders"""

    def __init__(self, root_folder: Path = None):
        self.root_folder = root_folder or Config.DATA_ROOT_FOLDER
        self.invalid_folder = Config.INVALID_FILES_FOLDER
        self.stats = {
            "dispatched": 0,
            "invalid": 0,
            "errors": 0
        }

    def dispatch_files(self) -> dict:
        """
        Dispatch all files from root folder to their respective dataset folders
        Returns statistics about the operation
        """
        self.stats = {"dispatched": 0, "invalid": 0, "errors": 0}

        if not self.root_folder.exists():
            raise ValueError(f"Root folder does not exist: {self.root_folder}")

        self.invalid_folder.mkdir(parents=True, exist_ok=True)

        files = [f for f in self.root_folder.iterdir() if f.is_file()]

        for file_path in files:
            try:
                self._dispatch_single_file(file_path)
            except Exception as e:
                logger.error(f"Error processing file {file_path.name}: {e}")
                self.stats["errors"] += 1

        return self.stats

    def _dispatch_single_file(self, file_path: Path) -> None:
        """Dispatch a single file to its appropriate location"""
        filename = file_path.name
        contract_name, dataset_name = self._parse_filename(filename)

        if not contract_name or not dataset_name:
            logger.warning(f"Could not parse filename: {filename}")
            self._move_to_invalid(file_path)
            return

        target_folder = self.root_folder / contract_name / dataset_name

        if target_folder.exists() and target_folder.is_dir():
            destination = target_folder / filename
            shutil.move(str(file_path), str(destination))
            logger.info(f"Dispatched: {filename} -> {contract_name}/{dataset_name}/")
            self.stats["dispatched"] += 1
        else:
            logger.warning(f"Target folder does not exist for {filename}: {contract_name}/{dataset_name}")
            self._move_to_invalid(file_path)

    def _parse_filename(self, filename: str) -> Tuple[str, str]:
        """
        Parse filename to extract contract name and dataset name
        Format: ContractName_DatasetName_*.extension
        Returns: (contract_name, dataset_name)

        This method searches through existing contract/dataset folders to find
        the best match, handling underscores in contract and dataset names.
        The comparison is case-insensitive.

        Dataset folders are sorted by name length (descending) to match
        the most specific names first (e.g., 'assessment_result' before 'assessment').
        """
        filename_lower = filename.lower()

        contract_folders = sorted(self.get_contract_folders(), key=lambda x: len(x.name), reverse=True)

        for contract_folder in contract_folders:
            contract_name = contract_folder.name

            if not filename_lower.startswith(contract_name.lower() + "_"):
                continue

            dataset_folders = sorted(self.get_dataset_folders(contract_folder), key=lambda x: len(x.name), reverse=True)

            for dataset_folder in dataset_folders:
                dataset_name = dataset_folder.name
                expected_prefix = f"{contract_name}_{dataset_name}_".lower()
                expected_prefix_with_ext = f"{contract_name}_{dataset_name}.".lower()

                if filename_lower.startswith(expected_prefix) or \
                   filename_lower.startswith(expected_prefix_with_ext):
                    return contract_name, dataset_name

        return None, None

    def _move_to_invalid(self, file_path: Path) -> None:
        """Move file to invalid files folder"""
        destination = self.invalid_folder / file_path.name
        counter = 1
        while destination.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            destination = self.invalid_folder / f"{stem}_{counter}{suffix}"
            counter += 1

        shutil.move(str(file_path), str(destination))
        logger.warning(f"Moved to invalid folder: {file_path.name}")
        self.stats["invalid"] += 1

    def get_contract_folders(self) -> List[Path]:
        """Get list of contract folders (excluding special folders)"""
        if not self.root_folder.exists():
            return []

        return [
            folder for folder in self.root_folder.iterdir()
            if folder.is_dir() and not folder.name.startswith("_")
        ]

    def get_dataset_folders(self, contract_folder: Path) -> List[Path]:
        """Get list of dataset folders within a contract folder"""
        if not contract_folder.exists():
            return []

        return [
            folder for folder in contract_folder.iterdir()
            if folder.is_dir()
        ]
