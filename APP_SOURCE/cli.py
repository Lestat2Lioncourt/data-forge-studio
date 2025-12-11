"""
CLI Module - Command Line Interface for DataForge Studio
"""
import sys
from pathlib import Path

# Import from src modules
from src.core.file_dispatcher import FileDispatcher
from src.core.data_loader import DataLoader
from src.utils.config import Config


class CLI:
    """Command Line Interface handler"""

    def __init__(self):
        self.commands = {
            "DispatchFiles": self.dispatch_files,
            "LoadFiles": self.load_files,
            "help": self.show_help
        }

    def run(self, args: list = None):
        """Run CLI with provided arguments"""
        if args is None:
            args = sys.argv[1:]

        if not args or args[0] not in self.commands:
            self.show_help()
            return

        command = args[0]
        self.commands[command]()

    def dispatch_files(self):
        """Execute DispatchFiles command"""
        print("=" * 60)
        print("Starting File Dispatch Process")
        print("=" * 60)
        print(f"Root folder: {Config.DATA_ROOT_FOLDER}")
        print()

        try:
            dispatcher = FileDispatcher()
            stats = dispatcher.dispatch_files()

            print()
            print("=" * 60)
            print("File Dispatch Completed")
            print("=" * 60)
            print(f"Files dispatched: {stats['dispatched']}")
            print(f"Invalid files: {stats['invalid']}")
            print(f"Errors: {stats['errors']}")
            print("=" * 60)

        except Exception as e:
            print(f"Error during file dispatch: {e}")
            sys.exit(1)

    def load_files(self):
        """Execute LoadFiles command"""
        print("=" * 60)
        print("Starting Data Load Process")
        print("=" * 60)
        print(f"Root folder: {Config.DATA_ROOT_FOLDER}")
        print(f"Database: {Config.DB_NAME} on {Config.DB_HOST}")
        print()

        try:
            loader = DataLoader()
            stats = loader.load_all_files()

            print()
            print("=" * 60)
            print("Data Load Completed")
            print("=" * 60)
            print(f"Files processed: {stats['files_processed']}")
            print(f"Files imported: {stats['files_imported']}")
            print(f"Files failed: {stats['files_failed']}")
            print(f"Tables created: {stats['tables_created']}")
            print(f"Tables updated: {stats['tables_updated']}")
            print("=" * 60)

        except Exception as e:
            print(f"Error during data load: {e}")
            sys.exit(1)

    def show_help(self):
        """Show help message"""
        print("DataForge Studio - Command Line Interface")
        print()
        print("Usage: python main.py [command]")
        print()
        print("Commands:")
        print("  DispatchFiles  - Move files from root to contract/dataset folders")
        print("  LoadFiles      - Import files from contract/dataset folders to database")
        print("  help           - Show this help message")
        print()
        print("Configuration:")
        print(f"  Root folder: {Config.DATA_ROOT_FOLDER}")
        print(f"  Database: {Config.DB_NAME} on {Config.DB_HOST}")
        print()


def main():
    """Main entry point for CLI"""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
