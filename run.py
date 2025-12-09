"""
Quick launcher for DataForge Studio Application
"""
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Launch the application
from main import main

if __name__ == "__main__":
    main()
