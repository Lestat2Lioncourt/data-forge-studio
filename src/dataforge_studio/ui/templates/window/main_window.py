"""Main frameless window with custom title bar and resizable panels."""

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QMouseEvent

from .title_bar import TitleBar
from .menu_bar import MenuBar
from .status_bar import StatusBar


class TemplateWindow(QMainWindow):
    """
    Frameless main window template with custom title bar, menu bar, status bar,
    and resizable left/right panels.

    Note: Window resizing is handled by ResizeWrapper when using create_window().
    """

    def __init__(self, title: str = "Application", show_split_toggle: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        # Remove system frame and enable custom frame
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Note: Mouse tracking and resize are now handled by ResizeWrapper
        # when using create_window() with easy_resize=True

        # Window state tracking
        self._is_maximized = False
        self._normal_geometry = QRect()

        # Right panel mode tracking
        self._right_panel_mode = "split"  # "split" or "single"
        self._right_single_widget = None
        self._right_split_enabled = False

        # Initialize components
        self.title_bar = TitleBar(title, show_special_button=show_split_toggle, parent=self)
        self.menu_bar = MenuBar(self)
        self.status_bar = StatusBar(self)

        # Setup main layout
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the main window UI structure."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # No hardcoded styles - let global QSS handle colors
        # central_widget styled by theme via app.setStyleSheet()

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add title bar
        main_layout.addWidget(self.title_bar)

        # Add menu bar
        main_layout.addWidget(self.menu_bar)

        # Create horizontal layout for left panel (fixed) and right content
        self.main_container = QWidget()
        main_h_layout = QHBoxLayout(self.main_container)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # Left panel - fixed width (icon sidebar)
        self.left_panel = QWidget()
        self.left_panel.setFixedWidth(56)  # Fixed width for icon sidebar
        # No hardcoded style - uses theme via global QSS
        main_h_layout.addWidget(self.left_panel)

        # Right panel container with optional vertical splitter
        self.right_container = QWidget()
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Right panel splitter (vertical split)
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setHandleWidth(4)
        # No hardcoded style - uses theme via global QSS

        # Right top panel
        self.right_top_panel = QWidget()
        # No hardcoded style - uses theme via global QSS
        self.right_splitter.addWidget(self.right_top_panel)

        # Right bottom panel (initially hidden)
        self.right_bottom_panel = QWidget()
        # No hardcoded style - uses theme via global QSS
        self.right_splitter.addWidget(self.right_bottom_panel)

        # Initially hide bottom panel
        self.right_bottom_panel.hide()
        self.right_splitter.setSizes([1, 0])

        right_layout.addWidget(self.right_splitter)
        main_h_layout.addWidget(self.right_container, stretch=1)

        main_layout.addWidget(self.main_container, stretch=1)

        # Add status bar
        main_layout.addWidget(self.status_bar)

    def _connect_signals(self):
        """Connect title bar and menu bar signals to window controls."""
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.maximize_clicked.connect(self.toggle_maximize)
        self.title_bar.special_clicked.connect(self.toggle_right_split)

        # Menu bar double-click also maximizes
        self.menu_bar.maximize_clicked.connect(self.toggle_maximize)

    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self._is_maximized:
            self.setGeometry(self._normal_geometry)
            self._is_maximized = False
        else:
            self._normal_geometry = self.geometry()
            # Get available screen geometry
            screen = self.screen()
            if screen:
                self.setGeometry(screen.availableGeometry())
            self._is_maximized = True

        self.title_bar.update_maximize_button(self._is_maximized)

    def toggle_right_split(self):
        """Toggle the right panel split on/off."""
        if self._right_panel_mode == "split":
            # Toggle the split state
            self._right_split_enabled = not self._right_split_enabled
            self.enable_right_split(self._right_split_enabled)

            # Update status bar
            status = "enabled" if self._right_split_enabled else "disabled"
            self.status_bar.set_message(f"Panel split {status}")

    def enable_right_split(self, enable: bool = True):
        """
        Enable or disable the vertical split in the right panel.

        Args:
            enable: True to show two panels, False to show only one
        """
        if enable:
            self.right_bottom_panel.show()
            total_height = self.right_splitter.height()
            self.right_splitter.setSizes([total_height // 2, total_height // 2])
        else:
            self.right_bottom_panel.hide()
            self.right_splitter.setSizes([1, 0])

    def _clear_right_panel(self):
        """Clear the right panel content and reset mode."""
        # Remove single widget if present
        if self._right_single_widget:
            self._right_single_widget.setParent(None)
            self._right_single_widget = None

        # Clear layouts in split panels
        if self.right_top_panel.layout():
            while self.right_top_panel.layout().count():
                item = self.right_top_panel.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            self.right_top_panel.layout().deleteLater()

        if self.right_bottom_panel.layout():
            while self.right_bottom_panel.layout().count():
                item = self.right_bottom_panel.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            self.right_bottom_panel.layout().deleteLater()

    def set_left_panel_widget(self, widget: QWidget):
        """Set the widget for the left panel."""
        # Clear existing layout if any
        if self.left_panel.layout():
            while self.left_panel.layout().count():
                item = self.left_panel.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            self.left_panel.layout().deleteLater()

        layout = QVBoxLayout(self.left_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

        # Notify parent wrapper to reinstall event filters if needed
        self._notify_panel_change()

    def set_right_panel_widget(self, widget: QWidget):
        """
        Set a single widget for the entire right panel (no vertical split).

        This will hide the vertical splitter and use the full right panel
        for a single widget. Use this instead of set_right_top_widget/
        set_right_bottom_widget when you don't need a vertical split.

        Args:
            widget: The widget to display in the right panel
        """
        self._clear_right_panel()
        self._right_panel_mode = "single"

        # Hide the splitter and show single widget
        self.right_splitter.hide()

        # Add widget directly to right_container
        self._right_single_widget = widget
        self.right_container.layout().addWidget(widget)

        # Notify parent wrapper to reinstall event filters if needed
        self._notify_panel_change()

    def set_right_top_widget(self, widget: QWidget):
        """
        Set the widget for the right top panel (split mode).

        This will switch to split mode if currently in single mode.
        Use enable_right_split(True) to show the bottom panel as well.

        Args:
            widget: The widget to display in the right top panel
        """
        if self._right_panel_mode == "single":
            self._clear_right_panel()
            self._right_panel_mode = "split"
            self.right_splitter.show()

        # Clear existing layout if any
        if self.right_top_panel.layout():
            while self.right_top_panel.layout().count():
                item = self.right_top_panel.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            self.right_top_panel.layout().deleteLater()

        layout = QVBoxLayout(self.right_top_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

        # Notify parent wrapper to reinstall event filters if needed
        self._notify_panel_change()

    def set_right_bottom_widget(self, widget: QWidget):
        """
        Set the widget for the right bottom panel (split mode).

        This will switch to split mode if currently in single mode and
        automatically enable the vertical split.

        Args:
            widget: The widget to display in the right bottom panel
        """
        if self._right_panel_mode == "single":
            self._clear_right_panel()
            self._right_panel_mode = "split"
            self.right_splitter.show()

        # Clear existing layout if any
        if self.right_bottom_panel.layout():
            while self.right_bottom_panel.layout().count():
                item = self.right_bottom_panel.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            self.right_bottom_panel.layout().deleteLater()

        layout = QVBoxLayout(self.right_bottom_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

        # Automatically enable split when setting bottom widget
        self.enable_right_split(True)

        # Notify parent wrapper to reinstall event filters if needed
        self._notify_panel_change()

    def _notify_panel_change(self):
        """Notify parent wrapper that panels have changed (for event filter reinstallation)."""
        # Check if this window is wrapped in a ResizeWrapper
        parent = self.parent()
        if parent and hasattr(parent, '_install_event_filter_recursive'):
            # Reinstall event filters on all new widgets
            parent._install_event_filter_recursive(self)

    # NOTE: Resize handling is now done by ResizeWrapper when using create_window()
    # The old resize code has been removed to avoid conflicts.
    # If you use TemplateWindow directly without ResizeWrapper, resizing won't work.
