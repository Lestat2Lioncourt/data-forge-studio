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
        self._setup_ui()

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
        """Get button stylesheet based on selection state."""
        if selected:
            return """
                QPushButton {
                    border: none;
                    border-radius: 6px;
                    background-color: rgba(100, 150, 255, 0.3);
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: rgba(100, 150, 255, 0.4);
                }
            """
        else:
            return """
                QPushButton {
                    border: none;
                    border-radius: 6px;
                    background-color: transparent;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.2);
                }
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
