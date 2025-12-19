"""
Resources Manager V2 - Icon sidebar navigation

Architecture:
- Left: Vertical icon bar with large icons
- Right: Currently selected manager's complete interface
"""

from typing import Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QCursor

from ..core.theme_bridge import ThemeBridge
from ...utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


class IconButton(QPushButton):
    """Large icon button with tooltip for sidebar."""

    def __init__(self, icon_name: str, tooltip: str, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._tooltip = tooltip
        self._selected = False

        # Set icon
        icon = get_icon(icon_name)
        if icon:
            self.setIcon(icon)
        self.setIconSize(QSize(32, 32))

        # Set tooltip
        self.setToolTip(tooltip)

        # Fixed size for icon button
        self.setFixedSize(48, 48)

        # Cursor
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Apply style
        self._apply_style()

        # Listen for theme changes
        self._theme_bridge = ThemeBridge.get_instance()
        self._theme_bridge.register_observer(self._on_theme_changed)

    def _on_theme_changed(self, theme_colors: dict):
        self._apply_style()

    def set_selected(self, selected: bool):
        """Set selection state."""
        self._selected = selected
        self._apply_style()

    def _apply_style(self):
        """Apply themed style."""
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()

        bg = colors.get("sectionheader_bg", "#3c3c3c")
        hover_bg = colors.get("sectionheader_hover_bg", "#4a4a4a")
        selected_bg = colors.get("selected_bg", "#0078d7")
        tooltip_bg = colors.get("tooltip_bg", "#3d3d3d")
        tooltip_fg = colors.get("tooltip_fg", "#ffffff")

        # Common tooltip style
        tooltip_style = f"""
            QToolTip {{
                background-color: {tooltip_bg};
                color: {tooltip_fg};
                border: 1px solid {hover_bg};
                padding: 4px 8px;
                font-size: 12px;
            }}
        """

        if self._selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {selected_bg};
                    border: none;
                    border-radius: 6px;
                }}
                {tooltip_style}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                }}
                {tooltip_style}
            """)


class ResourcesManagerV2(QWidget):
    """
    Icon sidebar navigation for managers.

    Emits signals when icons are clicked - main_window handles displaying managers.
    """

    # Signal emitted when user wants to open a resource in dedicated view
    open_resource_requested = Signal(str, str)  # (resource_type, resource_id)

    # Signal emitted when user wants to open the Image Library Manager
    open_image_library_requested = Signal()

    # Signal emitted when a manager icon is clicked
    manager_selected = Signal(str)  # manager_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Icon buttons
        self._icon_buttons: Dict[str, IconButton] = {}
        self._current_manager_id: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the main UI layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Icon sidebar only
        self._setup_sidebar()
        main_layout.addWidget(self.sidebar)

    def _setup_sidebar(self):
        """Setup the icon sidebar."""
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(56)
        self._apply_sidebar_style()

        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(4, 8, 4, 8)
        self.sidebar_layout.setSpacing(8)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Listen for theme changes
        theme_bridge = ThemeBridge.get_instance()
        theme_bridge.register_observer(self._on_theme_changed)

    def _apply_sidebar_style(self):
        """Apply theme to sidebar."""
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()
        bg = colors.get("panel_bg", "#252525")
        border = colors.get("border_color", "#3d3d3d")

        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border-right: 1px solid {border};
            }}
        """)

    def _on_theme_changed(self, theme_colors: dict):
        """Handle theme change."""
        self._apply_sidebar_style()

    def set_managers(self, database_manager=None, rootfolder_manager=None,
                     queries_manager=None, jobs_manager=None, scripts_manager=None,
                     image_library_manager=None):
        """Create icon buttons for each manager."""

        # Define modules with their icons and labels
        module_config = [
            ("database", database_manager, "database.png", "Module : Bases de données"),
            ("rootfolders", rootfolder_manager, "folder.png", "Module : Dossiers racine"),
            ("queries", queries_manager, "queries.png", "Module : Requêtes"),
            ("jobs", jobs_manager, "jobs.png", "Module : Jobs"),
            ("scripts", scripts_manager, "scripts.png", "Module : Scripts"),
            ("images", image_library_manager, "images.png", "Module : Images"),
        ]

        for module_id, module, icon_name, label in module_config:
            if module:
                self._add_icon(module_id, icon_name, label)

        # Select first by default
        if self._icon_buttons:
            first_id = list(self._icon_buttons.keys())[0]
            self._select_manager(first_id)

    def _add_icon(self, manager_id: str, icon_name: str, label: str):
        """Add an icon button to the sidebar."""
        btn = IconButton(icon_name, label)
        btn.clicked.connect(lambda checked, mid=manager_id: self._select_manager(mid))
        self.sidebar_layout.addWidget(btn)
        self._icon_buttons[manager_id] = btn

    def _select_manager(self, manager_id: str):
        """Select a manager and emit signal."""
        if manager_id not in self._icon_buttons:
            return

        # Update selection state
        for mid, btn in self._icon_buttons.items():
            btn.set_selected(mid == manager_id)

        self._current_manager_id = manager_id

        # Emit signal for main_window to handle
        self.manager_selected.emit(manager_id)

    def select_manager(self, manager_id: str):
        """Public method to select a manager."""
        self._select_manager(manager_id)

    def update_selection(self, manager_id: str):
        """Update icon selection state without emitting signal."""
        if manager_id not in self._icon_buttons:
            return
        for mid, btn in self._icon_buttons.items():
            btn.set_selected(mid == manager_id)
        self._current_manager_id = manager_id

    def refresh(self):
        """Placeholder - managers handle their own refresh."""
        pass

    def refresh_queries(self):
        """Placeholder - handled by main_window."""
        pass

    def refresh_images(self):
        """Placeholder - handled by main_window."""
        pass
