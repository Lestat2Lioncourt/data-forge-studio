"""
UI Templates - Reusable framework components for windows and dialogs.

This package contains base templates that can be reused across different applications:
- window/: Main window templates (title bar, menu bar, status bar, etc.)
- dialog/: Dialog templates (selector dialog, form dialog, etc.)
"""

from .window import (
    TitleBar,
    MenuBar,
    StatusBar,
    ResizeWrapper,
    TemplateWindow,
    ThemeManager,
    create_window,
    get_icon_path,
    get_resource_path,
)

from .dialog import (
    SelectorDialog,
    SelectorTitleBar,
)

__all__ = [
    # Window components
    "TitleBar",
    "MenuBar",
    "StatusBar",
    "ResizeWrapper",
    "TemplateWindow",
    "ThemeManager",
    "create_window",
    "get_icon_path",
    "get_resource_path",
    # Dialog components
    "SelectorDialog",
    "SelectorTitleBar",
]
