"""Customizable menu bar with icon/text buttons."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QMenu
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QIcon, QPixmap, QMouseEvent, QAction
from typing import Callable, Optional, List, Tuple


class MenuBar(QWidget):
    """Horizontal menu bar with customizable icon/text buttons."""

    # Signal for maximize on double-click
    maximize_clicked = Signal()
    # Signal when a view button is selected (name of view)
    view_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        # Enable styled background for QSS to work
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # No hardcoded styles - will be set by theme manager

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.setSpacing(5)
        self.layout.addStretch()

        self.buttons = {}
        self._current_view = None  # Track current view for highlighting

        # Drag state
        self._is_dragging = False
        self._drag_position = QPoint()
        self._click_x_ratio = 0.5

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
        button.setCheckable(True)  # Allow selection state

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
        # No hardcoded styles - will be set by theme manager via apply_theme()
        menu = QMenu(button)

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
            button.setVisible(False)  # Hide immediately to prevent visual duplication
            self.layout.removeWidget(button)
            button.deleteLater()

    def get_button(self, name: str) -> Optional[QPushButton]:
        """Get a menu button by name."""
        return self.buttons.get(name)

    def set_selected_button(self, name: str):
        """
        Set which button is currently selected (active view).

        Args:
            name: Name of the button to mark as selected
        """
        old_view = self._current_view
        self._current_view = name

        # Update checkable state for buttons
        for btn_name, button in self.buttons.items():
            # Only toggle selection for menu buttons (not dropdowns)
            if not button.menu():
                if btn_name == name:
                    button.setChecked(True)
                elif btn_name == old_view:
                    button.setChecked(False)

        # Emit signal for any external listeners
        self.view_selected.emit(name)

    def get_current_view(self) -> Optional[str]:
        """Get the name of the currently selected view."""
        return self._current_view

    def set_active_menu(self, name: str, colors: dict = None):
        """
        Mark a menu button as active (for dropdown menus).

        Args:
            name: Name of the menu button to mark as active
            colors: Optional dict with 'selected_bg' and 'selected_fg' keys
        """
        # Reset previous active button style
        if hasattr(self, '_active_menu') and self._active_menu:
            old_btn = self.buttons.get(self._active_menu)
            if old_btn:
                old_btn.setStyleSheet("")  # Reset to inherit from parent
                # Also uncheck if it's a checkable button
                if old_btn.isCheckable():
                    old_btn.setChecked(False)

        # Uncheck all other checkable buttons (simple menu items)
        for btn_name, btn in self.buttons.items():
            if btn_name != name and btn.isCheckable():
                btn.setChecked(False)
                btn.setStyleSheet("")

        self._active_menu = name
        button = self.buttons.get(name)
        if button and colors:
            # Apply style
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.get('selected_bg', '#4d4d4d')};
                    color: {colors.get('selected_fg', '#ffffff')};
                }}
            """)
            # Also check if it's a checkable button
            if button.isCheckable():
                button.setChecked(True)

    def clear_menu(self):
        """Remove all menu items."""
        for name in list(self.buttons.keys()):
            self.remove_menu_item(name)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for window dragging (if not on a button)."""
        if event.button() == Qt.LeftButton:
            # Check if we clicked on a button
            widget_at_pos = self.childAt(event.pos())
            if widget_at_pos is None or not isinstance(widget_at_pos, QPushButton):
                self._is_dragging = True
                # Store click position relative to menu bar (as percentage for restore calculation)
                self._click_x_ratio = event.position().x() / self.width() if self.width() > 0 else 0.5
                self._drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            window = self.window()

            # Check if window is maximized (using custom _is_maximized flag)
            is_maximized = getattr(window, '_is_maximized', False) or window.isMaximized()

            if is_maximized:
                # Get the normal geometry before restoring
                # ResizeWrapper uses _resize_start_geometry, TemplateWindow uses _normal_geometry
                normal_geometry = getattr(window, '_resize_start_geometry', None) or \
                                  getattr(window, '_normal_geometry', None)
                if normal_geometry and normal_geometry.isValid():
                    normal_width = normal_geometry.width()
                else:
                    normal_width = 1200  # Default width

                # Restore window using toggle_maximize if available
                if hasattr(window, 'toggle_maximize'):
                    window.toggle_maximize()
                else:
                    window.showNormal()

                # Calculate new position: cursor should stay at same relative X position
                cursor_pos = event.globalPosition().toPoint()
                new_x = cursor_pos.x() - int(normal_width * self._click_x_ratio)
                new_y = cursor_pos.y() - 45  # Offset for title bar + menu bar height

                window.move(new_x, new_y)

                # Update drag position for continued dragging
                self._drag_position = cursor_pos - window.frameGeometry().topLeft()
            else:
                window.move(event.globalPosition().toPoint() - self._drag_position)

            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop dragging."""
        if self._is_dragging:
            self._is_dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

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
