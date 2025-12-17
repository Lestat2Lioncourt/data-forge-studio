#!/usr/bin/env python
"""
Launcher for DataForge Studio v0.50
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from dataforge_studio.main import main

if __name__ == "__main__":
    main()
