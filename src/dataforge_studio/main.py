"""
DataForge Studio - Main entry point
"""

import sys
from PySide6.QtWidgets import QApplication

from .ui.core.main_window import DataForgeMainWindow
from .ui.frames.data_lake_frame import DataLakeFrame
from .ui.frames.settings_frame import SettingsFrame
from .ui.frames.help_frame import HelpFrame
from .ui.managers import (
    QueriesManager,
    ScriptsManager,
    JobsManager,
    DatabaseManager,
    DataExplorer
)


def main():
    """Main entry point for DataForge Studio."""
    print("Starting DataForge Studio v0.50...")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("DataForge Studio")
    app.setApplicationVersion("0.50.0")
    app.setOrganizationName("DataForge")

    # Create main window
    main_window = DataForgeMainWindow()

    # Create frames
    data_lake_frame = DataLakeFrame()
    settings_frame = SettingsFrame()
    help_frame = HelpFrame()

    # Create managers
    print("Creating managers...")
    queries_manager = QueriesManager()
    scripts_manager = ScriptsManager()
    jobs_manager = JobsManager()
    database_manager = DatabaseManager()
    data_explorer = DataExplorer()
    print("Managers created successfully")

    # Set frames and managers in main window
    main_window.set_frames(
        data_lake_frame, settings_frame, help_frame,
        queries_manager=queries_manager,
        scripts_manager=scripts_manager,
        jobs_manager=jobs_manager,
        database_manager=database_manager,
        data_explorer=data_explorer
    )

    # Show window
    main_window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
