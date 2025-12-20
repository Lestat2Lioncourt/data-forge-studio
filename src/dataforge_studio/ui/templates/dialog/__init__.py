"""
Dialog Templates - Reusable dialog base classes.

This package contains base dialog templates:
- SelectorDialog: Dialog with custom title bar for selection interfaces
- SelectorTitleBar: Simplified title bar for selector dialogs
"""

from .selector_dialog import SelectorDialog, SelectorTitleBar

__all__ = [
    "SelectorDialog",
    "SelectorTitleBar",
]
