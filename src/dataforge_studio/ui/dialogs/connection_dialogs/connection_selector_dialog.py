"""
Connection Selector Dialog - Choose database type for new connection
"""

from typing import Optional, Type
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGridLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from .base_connection_dialog import BaseConnectionDialog
from ...core.theme_bridge import ThemeBridge
from ....utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


# Database type definitions with dialog mappings
DATABASE_TYPES = [
    {
        "id": "sqlserver",
        "name": "SQL Server",
        "description": "Microsoft SQL Server",
        "icon": "database",
        "dialog_class": "SQLServerConnectionDialog",
        "enabled": True
    },
    {
        "id": "sqlite",
        "name": "SQLite",
        "description": "SQLite local database",
        "icon": "database",
        "dialog_class": "SQLiteConnectionDialog",
        "enabled": True
    },
    {
        "id": "mysql",
        "name": "MySQL",
        "description": "MySQL / MariaDB",
        "icon": "database",
        "dialog_class": "MySQLConnectionDialog",
        "enabled": True
    },
    {
        "id": "postgresql",
        "name": "PostgreSQL",
        "description": "PostgreSQL",
        "icon": "database",
        "dialog_class": "PostgreSQLConnectionDialog",
        "enabled": True
    },
    {
        "id": "access",
        "name": "Access",
        "description": "Microsoft Access",
        "icon": "database",
        "dialog_class": "AccessConnectionDialog",
        "enabled": True
    },
    {
        "id": "oracle",
        "name": "Oracle",
        "description": "Oracle Database",
        "icon": "database",
        "dialog_class": "OracleConnectionDialog",
        "enabled": False  # TODO: Implement
    },
    {
        "id": "mongodb",
        "name": "MongoDB",
        "description": "MongoDB NoSQL",
        "icon": "database",
        "dialog_class": "MongoDBConnectionDialog",
        "enabled": False  # TODO: Implement
    }
]


class DatabaseTypeCard(QFrame):
    """A card widget representing a database type option."""

    clicked = Signal(dict)  # Emits the database type info when clicked

    def __init__(self, db_type: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._db_type = db_type
        self._is_enabled = db_type.get("enabled", True)

        self._setup_ui()
        self._apply_style()

        # Register for theme changes
        theme_bridge = ThemeBridge.get_instance()
        theme_bridge.register_observer(self._on_theme_changed)

    def _setup_ui(self):
        """Setup the card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon = get_icon(self._db_type.get("icon", "database"), size=32)
        icon_label = QLabel()
        if icon and not icon.isNull():
            icon_label.setPixmap(icon.pixmap(32, 32))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Name
        name_label = QLabel(self._db_type["name"])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(name_label)

        # Description
        desc_label = QLabel(self._db_type.get("description", ""))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("font-size: 10px; color: gray;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Set fixed size for consistent grid
        self.setFixedSize(130, 110)

        # Set cursor
        if self._is_enabled:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ForbiddenCursor))
            self.setToolTip("Coming soon...")

    def _apply_style(self):
        """Apply themed style."""
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()

        bg = colors.get("panel_bg", "#252525")
        border = colors.get("border_color", "#3d3d3d")
        hover_bg = colors.get("selected_bg", "#0078d7")

        if self._is_enabled:
            self.setStyleSheet(f"""
                DatabaseTypeCard {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 6px;
                }}
                DatabaseTypeCard:hover {{
                    border: 2px solid {hover_bg};
                    background-color: {colors.get("tree_item_hover_bg", "#2d2d2d")};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                DatabaseTypeCard {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 6px;
                    opacity: 0.5;
                }}
            """)

    def _on_theme_changed(self, colors: dict):
        """Handle theme change."""
        self._apply_style()

    def mousePressEvent(self, event):
        """Handle mouse press - emit clicked signal if enabled."""
        if self._is_enabled and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._db_type)
        super().mousePressEvent(event)


class ConnectionSelectorDialog(QDialog):
    """
    Dialog to select database type for new connection.

    Shows a grid of database type cards. When user selects one,
    opens the corresponding connection dialog.
    """

    connection_created = Signal()  # Emitted when a new connection is saved

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowTitle("New Connection")
        self.setMinimumSize(500, 400)

        self._selected_type: Optional[dict] = None
        self._setup_ui()
        self._apply_style()

        # Register for theme changes
        theme_bridge = ThemeBridge.get_instance()
        theme_bridge.register_observer(self._on_theme_changed)

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header_label = QLabel("Select Database Type")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Subtitle
        subtitle_label = QLabel("Choose the type of database you want to connect to")
        subtitle_label.setStyleSheet("color: gray;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)

        # Database type grid
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(12)
        grid_layout.setContentsMargins(20, 20, 20, 20)

        # Create cards for each database type
        row, col = 0, 0
        max_cols = 4

        for db_type in DATABASE_TYPES:
            card = DatabaseTypeCard(db_type, self)
            card.clicked.connect(self._on_card_clicked)
            grid_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        layout.addWidget(grid_container, stretch=1)

        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _apply_style(self):
        """Apply themed style."""
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors.get("window_bg", "#1e1e1e")};
            }}
            QLabel {{
                color: {colors.get("foreground", "#ffffff")};
            }}
        """)

    def _on_theme_changed(self, colors: dict):
        """Handle theme change."""
        self._apply_style()

    def _on_card_clicked(self, db_type: dict):
        """Handle database type card click."""
        self._selected_type = db_type
        self._open_connection_dialog(db_type)

    def _open_connection_dialog(self, db_type: dict):
        """Open the appropriate connection dialog for the selected type."""
        dialog_class_name = db_type.get("dialog_class")
        if not dialog_class_name:
            logger.error(f"No dialog class defined for {db_type['id']}")
            return

        # Import the dialog class dynamically
        dialog_class = self._get_dialog_class(dialog_class_name)
        if not dialog_class:
            from ...widgets.dialog_helper import DialogHelper
            DialogHelper.error(
                f"Connection dialog not found: {dialog_class_name}",
                parent=self
            )
            return

        # Create and show the dialog
        dialog = dialog_class(parent=self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            # Connection was saved - emit signal and close selector
            self.connection_created.emit()
            self.accept()

    def _get_dialog_class(self, class_name: str) -> Optional[Type[BaseConnectionDialog]]:
        """
        Get dialog class by name.

        Args:
            class_name: Name of the dialog class

        Returns:
            Dialog class or None if not found
        """
        try:
            if class_name == "SQLServerConnectionDialog":
                from .sqlserver_dialog import SQLServerConnectionDialog
                return SQLServerConnectionDialog
            elif class_name == "SQLiteConnectionDialog":
                from .sqlite_dialog import SQLiteConnectionDialog
                return SQLiteConnectionDialog
            elif class_name == "MySQLConnectionDialog":
                from .mysql_dialog import MySQLConnectionDialog
                return MySQLConnectionDialog
            elif class_name == "PostgreSQLConnectionDialog":
                from .postgresql_dialog import PostgreSQLConnectionDialog
                return PostgreSQLConnectionDialog
            elif class_name == "AccessConnectionDialog":
                from .access_dialog import AccessConnectionDialog
                return AccessConnectionDialog
            elif class_name == "OracleConnectionDialog":
                from .oracle_dialog import OracleConnectionDialog
                return OracleConnectionDialog
            elif class_name == "MongoDBConnectionDialog":
                from .mongodb_dialog import MongoDBConnectionDialog
                return MongoDBConnectionDialog
            else:
                logger.warning(f"Unknown dialog class: {class_name}")
                return None
        except ImportError as e:
            logger.error(f"Failed to import {class_name}: {e}")
            return None


def open_new_connection_dialog(parent: Optional[QWidget] = None) -> bool:
    """
    Convenience function to open the connection selector dialog.

    Args:
        parent: Parent widget

    Returns:
        True if a new connection was created, False otherwise
    """
    dialog = ConnectionSelectorDialog(parent)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted
