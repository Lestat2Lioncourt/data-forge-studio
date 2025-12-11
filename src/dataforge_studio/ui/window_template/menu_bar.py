"""Customizable menu bar with icon/text buttons."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QMenu
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QMouseEvent, QAction
from typing import Callable, Optional, List, Tuple


class MenuBar(QWidget):
    """Horizontal menu bar with customizable icon/text buttons."""

    # Signal for maximize on double-click
    maximize_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            MenuBar {
                background-color: #3d3d3d;
                border-bottom: 1px solid #4d4d4d;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: #ffffff;
                padding: 5px 15px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #5d5d5d;
            }
        """)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.setSpacing(5)
        self.layout.addStretch()

        self.buttons = {}

    def add_menu_item(
        self,
        name: str,
        text: str,
        callback: Optional[Callable] = None,
        icon_path: Optional[str] = None
    ):
        """
        Add a menu item to the bar.

        Args:
            name: Unique identifier for the menu item
            text: Display text for the button
            callback: Function to call when clicked
            icon_path: Optional path to icon image
        """
        button = QPushButton(text)
        button.setMinimumWidth(80)

        if icon_path:
            button.setIcon(QIcon(icon_path))

        if callback:
            button.clicked.connect(callback)

        # Remove stretch before adding new button
        if self.layout.count() > 0:
            item = self.layout.takeAt(self.layout.count() - 1)
            if item:
                item.widget()

        self.layout.addWidget(button)
        self.layout.addStretch()

        self.buttons[name] = button

    def add_menu_with_submenu(
        self,
        name: str,
        text: str,
        submenu_items: List[Tuple[Optional[str], Optional[Callable]]],
        icon_path: Optional[str] = None
    ):
        """
        Add a menu button with dropdown submenu.

        Args:
            name: Unique identifier for the menu item
            text: Display text for the button
            submenu_items: List of (label, callback) tuples. Use (None, None) for separator
            icon_path: Optional path to icon image
        """
        button = QPushButton(text)
        button.setMinimumWidth(80)

        if icon_path:
            button.setIcon(QIcon(icon_path))

        # Create the dropdown menu
        menu = QMenu(button)
        menu.setStyleSheet("""
            QMenu {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                color: #ffffff;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #4d4d4d;
            }
            QMenu::separator {
                height: 1px;
                background-color: #4d4d4d;
                margin: 5px 0px;
            }
        """)

        # Add items to menu
        for label, callback in submenu_items:
            if label is None:
                # Add separator
                menu.addSeparator()
            else:
                action = menu.addAction(label)
                if callback:
                    action.triggered.connect(callback)

        # Attach menu to button
        button.setMenu(menu)

        # Remove stretch before adding new button
        if self.layout.count() > 0:
            item = self.layout.takeAt(self.layout.count() - 1)
            if item:
                item.widget()

        self.layout.addWidget(button)
        self.layout.addStretch()

        self.buttons[name] = button

    def remove_menu_item(self, name: str):
        """Remove a menu item by name."""
        if name in self.buttons:
            button = self.buttons.pop(name)
            self.layout.removeWidget(button)
            button.deleteLater()

    def get_button(self, name: str) -> Optional[QPushButton]:
        """Get a menu button by name."""
        return self.buttons.get(name)

    def clear_menu(self):
        """Remove all menu items."""
        for name in list(self.buttons.keys()):
            self.remove_menu_item(name)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to maximize/restore window (if not on a button)."""
        if event.button() == Qt.LeftButton:
            # Check if we clicked on a button
            widget_at_pos = self.childAt(event.pos())
            if widget_at_pos is None or not isinstance(widget_at_pos, QPushButton):
                # Not on a button - emit maximize signal
                self.maximize_clicked.emit()
                event.accept()
                return

        super().mouseDoubleClickEvent(event)
