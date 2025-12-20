"""
Core translations registration.

This module registers the core/common translations that are used
throughout the application (menu, common buttons, status messages, etc.).
"""

from pathlib import Path
from ..manager import get_manager


def register_core_translations():
    """Register core translations from this directory."""
    translations_path = Path(__file__).parent
    get_manager().register_core(translations_path)


# Auto-register when this module is imported
register_core_translations()
