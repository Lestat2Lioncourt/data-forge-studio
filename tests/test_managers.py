#!/usr/bin/env python
"""
Test script for managers - Displays each manager in a window
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from dataforge_studio.ui.managers import (
    QueriesManager,
    ScriptsManager,
    JobsManager,
    DatabaseManager,
    DataExplorer
)


class ManagerTestWindow(QMainWindow):
    """Test window to display all managers in tabs."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DataForge Studio - Managers Test")
        self.setGeometry(100, 100, 1200, 800)

        # Create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add each manager as a tab
        self.queries_manager = QueriesManager()
        self.tabs.addTab(self.queries_manager, "Queries Manager")

        self.scripts_manager = ScriptsManager()
        self.tabs.addTab(self.scripts_manager, "Scripts Manager")

        self.jobs_manager = JobsManager()
        self.tabs.addTab(self.jobs_manager, "Jobs Manager")

        self.database_manager = DatabaseManager()
        self.tabs.addTab(self.database_manager, "Database Manager")

        self.data_explorer = DataExplorer()
        self.tabs.addTab(self.data_explorer, "Data Explorer")

        print("All managers loaded successfully!")
        print("- QueriesManager: OK")
        print("- ScriptsManager: OK")
        print("- JobsManager: OK")
        print("- DatabaseManager: OK")
        print("- DataExplorer: OK")


def main():
    """Main entry point for manager tests."""
    app = QApplication(sys.argv)
    app.setApplicationName("DataForge Studio - Manager Tests")

    window = ManagerTestWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
