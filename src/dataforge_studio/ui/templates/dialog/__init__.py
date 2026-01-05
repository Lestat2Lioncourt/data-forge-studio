"""
Dialog Templates - Reusable dialog base classes.

This package contains base dialog templates:
- SelectorDialog: Dialog with custom title bar for selection interfaces
- SelectorTitleBar: Simplified title bar for selector dialogs
- PopupWindow: Full-featured popup window with theme support
- PopupTitleBar: Title bar for popup windows
"""

from .selector_dialog import SelectorDialog, SelectorTitleBar
from .popup_window import PopupWindow, PopupTitleBar

__all__ = [
    "SelectorDialog",
    "SelectorTitleBar",
    "PopupWindow",
    "PopupTitleBar",
]
