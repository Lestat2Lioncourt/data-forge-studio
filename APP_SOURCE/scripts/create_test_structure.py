"""
Script pour créer une structure de test avec des fichiers d'exemple
"""
import csv
from pathlib import Path
import pandas as pd


def create_test_structure():
    """Crée une structure de dossiers et fichiers de test"""

    root = Path(r"D:\DataRootFolder")

    print("Creating test structure...")

    contracts = {
        "ContractA": ["Dataset1", "Dataset2"],
        "ContractB": ["Dataset1"],
        "ContractC": ["DatasetX", "DatasetY"]
    }

    for contract_name, datasets in contracts.items():
        contract_path = root / contract_name
        contract_path.mkdir(parents=True, exist_ok=True)

        for dataset_name in datasets:
            dataset_path = contract_path / dataset_name
            dataset_path.mkdir(parents=True, exist_ok=True)
            print(f"Created: {contract_path}\\{dataset_name}")

    print("\nCreating test CSV files at root...")

    test_files = [
        {
            "filename": "ContractA_Dataset1_data.csv",
            "data": {
                "ID": ["1", "2", "3"],
                "Name": ["Alice", "Bob", "Charlie"],
                "Age": ["25", "30", "35"],
                "City": ["Paris", "Lyon", "Marseille"]
            }
        },
        {
            "filename": "ContractA_Dataset2_info.csv",
            "data": {
                "ProductID": ["P001", "P002", "P003"],
                "ProductName": ["Widget", "Gadget", "Tool"],
                "Price": ["10.50", "25.00", "15.75"]
            }
        },
        {
            "filename": "ContractB_Dataset1_records.csv",
            "data": {
                "OrderID": ["O001", "O002"],
                "CustomerName": ["John Doe", "Jane Smith"],
                "Amount": ["150.00", "200.00"],
                "Date": ["2024-01-15", "2024-01-16"]
            }
        },
        {
            "filename": "InvalidFile_NoMatch.csv",
            "data": {
                "Column1": ["Data1"],
                "Column2": ["Data2"]
            }
        }
    ]

    for file_info in test_files:
        filepath = root / file_info["filename"]
        df = pd.DataFrame(file_info["data"])
        df.to_csv(filepath, index=False)
        print(f"Created: {filepath.name}")

    print("\nTest structure created successfully!")
    print(f"\nRoot folder: {root}")
    print("\nYou can now run:")
    print("  1. uv run python main.py DispatchFiles")
    print("  2. uv run python main.py LoadFiles")
    print("\nOr launch the GUI with:")
    print("  uv run python main.py")


if __name__ == "__main__":
    create_test_structure()
