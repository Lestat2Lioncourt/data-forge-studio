"""
DataForge Studio - Main Entry Point
"""
import sys
import os

# Add parent directory to path to allow imports from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import gui main function
try:
    # Try relative import first (when run as module)
    from .ui.gui import main as gui_main
except ImportError:
    # Fall back to absolute import (when run directly)
    from src.ui.gui import main as gui_main


def main():
    """Main entry point - launches GUI"""
    gui_main()


if __name__ == "__main__":
    main()
