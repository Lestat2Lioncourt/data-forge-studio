"""
Window Template Library
=======================

A reusable PySide6-based window template with custom title bar, menu bar,
status bar, and resizable panels.

Main Components:
- TemplateWindow: The main frameless window
- TitleBar: Custom title bar with window controls
- MenuBar: Customizable horizontal menu bar
- StatusBar: Bottom status bar for messages

Example usage:
    from dataforge_studio.ui.templates.window import TemplateWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    window = TemplateWindow("My Application")
    window.show()
    app.exec()
"""

from .main_window import TemplateWindow
from .title_bar import TitleBar
from .menu_bar import MenuBar
from .status_bar import StatusBar
from .resources import get_icon_path, get_resource_path
from .resize_wrapper import ResizeWrapper
from .theme_manager import ThemeManager


def create_window(title: str = "Application", easy_resize: bool = True, show_split_toggle: bool = False):
    """
    Create a template window with optional easy-resize wrapper.

    Args:
        title: Window title
        easy_resize: If True, wraps window in transparent border for easier resizing
        show_split_toggle: If True, shows special button to toggle right panel split

    Returns:
        ResizeWrapper containing TemplateWindow if easy_resize=True,
        otherwise TemplateWindow directly
    """
    window = TemplateWindow(title, show_split_toggle=show_split_toggle)

    if easy_resize:
        wrapper = ResizeWrapper(window)

        # Connect window controls to wrapper (not inner window)
        window.title_bar.close_clicked.connect(wrapper.close)
        window.title_bar.minimize_clicked.connect(wrapper.showMinimized)
        window.title_bar.maximize_clicked.connect(wrapper.toggle_maximize)

        # Menu bar double-click also maximizes
        window.menu_bar.maximize_clicked.connect(wrapper.toggle_maximize)

        return wrapper
    else:
        return window


__version__ = "0.1.0"
__all__ = [
    "TemplateWindow",
    "TitleBar",
    "MenuBar",
    "StatusBar",
    "ResizeWrapper",
    "ThemeManager",
    "create_window",
    "get_icon_path",
    "get_resource_path"
]
