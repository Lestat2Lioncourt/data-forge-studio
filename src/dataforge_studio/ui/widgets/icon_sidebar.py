"""
Icon Sidebar - Vertical icon bar for quick navigation between managers

A minimal sidebar with icons for each manager type:
- Database, RootFolders, Queries, Jobs, Scripts, Images
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon


class IconSidebar(QWidget):
    """
    Vertical icon sidebar for quick navigation between managers.

    Emits manager_selected signal when an icon is clicked.
    Uses theme colors for selection/hover states with transparency.
    """

    # Signal emitted when a manager icon is clicked
    manager_selected = Signal(str)

    # Signal to open resource in dedicated manager (for compatibility)
    open_resource_requested = Signal(str, str)

    # Signal to open image library
    open_image_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_selection = None
        self._buttons = {}
        self._assets_path = Path(__file__).parent.parent / "assets" / "images"
        self._theme_colors = self._load_theme_colors()
        self._setup_ui()
        self._register_theme_observer()

    def _load_theme_colors(self) -> dict:
        """Load theme colors for IconSidebar."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            colors = theme.get_theme_colors()
            return {
                "bg": colors.get("iconsidebar_bg", "#252525"),
                "selected_bg": colors.get("iconsidebar_selected_bg", "rgba(100, 150, 255, 0.3)"),
                "hover_bg": colors.get("iconsidebar_hover_bg", "rgba(255, 255, 255, 0.15)"),
                "pressed_bg": colors.get("iconsidebar_pressed_bg", "rgba(255, 255, 255, 0.25)"),
            }
        except Exception:
            # Fallback colors
            return {
                "bg": "#252525",
                "selected_bg": "rgba(100, 150, 255, 0.3)",
                "hover_bg": "rgba(255, 255, 255, 0.15)",
                "pressed_bg": "rgba(255, 255, 255, 0.25)",
            }

    def _register_theme_observer(self):
        """Register as theme observer to update colors on theme change."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            theme.register_observer(self._on_theme_changed)
        except Exception:
            pass

    def _on_theme_changed(self, theme_colors: dict):
        """Handle theme change - update colors."""
        self._theme_colors = {
            "bg": theme_colors.get("iconsidebar_bg", "#252525"),
            "selected_bg": theme_colors.get("iconsidebar_selected_bg", "rgba(100, 150, 255, 0.3)"),
            "hover_bg": theme_colors.get("iconsidebar_hover_bg", "rgba(255, 255, 255, 0.15)"),
            "pressed_bg": theme_colors.get("iconsidebar_pressed_bg", "rgba(255, 255, 255, 0.25)"),
        }
        # Re-apply styles to all buttons
        for mid, btn in self._buttons.items():
            btn.setStyleSheet(self._get_button_style(selected=(mid == self._current_selection)))

    def _setup_ui(self):
        """Setup the icon sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)

        # Define managers with icon filenames and IDs
        managers = [
            ("databases.png", "database", "Databases / Bases de données"),
            ("RootFolders.png", "rootfolders", "Root Folders / Dossiers racine"),
            ("queries.png", "queries", "Queries / Requêtes"),
            ("jobs.png", "jobs", "Jobs / Tâches"),
            ("scripts.png", "scripts", "Scripts"),
            ("images.png", "images", "Image Library / Bibliothèque d'images"),
        ]

        for icon_file, manager_id, tooltip in managers:
            btn = QPushButton()
            btn.setToolTip(tooltip)
            btn.setFixedSize(40, 40)
            btn.setIconSize(QSize(24, 24))

            # Load icon from assets
            icon_path = self._assets_path / icon_file
            if icon_path.exists():
                btn.setIcon(QIcon(str(icon_path)))

            btn.setStyleSheet(self._get_button_style(selected=False))
            btn.clicked.connect(lambda checked, mid=manager_id: self._on_button_clicked(mid))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._buttons[manager_id] = btn

        # Add stretch to push buttons to top
        layout.addStretch()

        # Set fixed width for sidebar
        self.setFixedWidth(52)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # Default selection
        self.update_selection("database")

    def _get_button_style(self, selected: bool = False) -> str:
        """Get button stylesheet based on selection state using theme colors."""
        selected_bg = self._theme_colors.get("selected_bg", "rgba(100, 150, 255, 0.3)")
        hover_bg = self._theme_colors.get("hover_bg", "rgba(255, 255, 255, 0.15)")
        pressed_bg = self._theme_colors.get("pressed_bg", "rgba(255, 255, 255, 0.25)")

        if selected:
            # Selected state: use selected color with slightly more opacity on hover
            return f"""
                QPushButton {{
                    border: none;
                    border-radius: 6px;
                    background-color: {selected_bg};
                    padding: 4px;
                }}
                QPushButton:hover {{
                    background-color: {selected_bg};
                }}
            """
        else:
            # Normal state: transparent, show hover/pressed colors
            return f"""
                QPushButton {{
                    border: none;
                    border-radius: 6px;
                    background-color: transparent;
                    padding: 4px;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                }}
                QPushButton:pressed {{
                    background-color: {pressed_bg};
                }}
            """

    def _on_button_clicked(self, manager_id: str):
        """Handle button click."""
        self.update_selection(manager_id)
        self.manager_selected.emit(manager_id)

        # Also emit image library signal if images selected
        if manager_id == "images":
            self.open_image_library_requested.emit()

    def update_selection(self, manager_id: str):
        """
        Update which button is shown as selected.

        Args:
            manager_id: ID of the manager to select
        """
        self._current_selection = manager_id

        for mid, btn in self._buttons.items():
            btn.setStyleSheet(self._get_button_style(selected=(mid == manager_id)))

    def refresh_queries(self):
        """Refresh queries - stub for compatibility with main_window expectations."""
        # IconSidebar doesn't need to refresh, but this method is expected
        pass
