"""
SQL Auto-Completer Popup Widget
Non-blocking suggestion listbox for SQL editors.
"""

from typing import List, Optional
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QTextEdit
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QKeyEvent, QFocusEvent

from ..core.theme_bridge import ThemeBridge

import logging
logger = logging.getLogger(__name__)


class SQLCompleterPopup(QListWidget):
    """
    Floating suggestion listbox for SQL auto-completion.

    Features:
    - Non-blocking popup positioned below cursor
    - Keyboard navigation (Up/Down, Tab/Enter to select, Escape to close)
    - Real-time filtering as user types
    """

    # Emitted when a completion is selected
    completion_selected = Signal(str)

    def __init__(self, parent_editor: QTextEdit):
        """
        Initialize the completer popup.

        Args:
            parent_editor: The QTextEdit to attach to
        """
        super().__init__(parent_editor)

        self.parent_editor = parent_editor
        self._all_suggestions: List[str] = []
        self._filter_text: str = ""

        self._setup_ui()

    def _setup_ui(self):
        """Setup popup appearance and behavior."""
        # Window flags - Tool window that doesn't steal focus
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        # Ensure we don't take focus from editor
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Apply theme colors
        self._apply_theme()

        # Size constraints
        self.setMaximumHeight(200)
        self.setMinimumWidth(150)

    def _apply_theme(self):
        """Apply theme colors to the popup."""
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()

        # Get colors from theme
        bg = colors.get('dd_menu_bg', '#FFFFFF')
        fg = colors.get('dd_menu_fg', '#000000')
        border = colors.get('border_color', '#CCCCCC')
        selected_bg = colors.get('selected_bg', '#0078D7')
        selected_fg = colors.get('selected_fg', '#FFFFFF')
        hover_bg = colors.get('dd_menu_hover_bg', '#E5F3FF')

        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg};
                border: 1px solid {border};
                font-family: Consolas, monospace;
                font-size: 10pt;
            }}
            QListWidget::item {{
                padding: 2px 5px;
                color: {fg};
            }}
            QListWidget::item:selected {{
                background-color: {selected_bg};
                color: {selected_fg};
            }}
            QListWidget::item:hover {{
                background-color: {hover_bg};
            }}
        """)

        # Single selection
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # Connect double-click
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

        # Hide initially
        self.hide()

    def show_completions(self, suggestions: List[str], filter_text: str = "",
                         cursor_rect: Optional[object] = None):
        """
        Show the popup with filtered suggestions.

        Args:
            suggestions: All available suggestions
            filter_text: Current text to filter by
            cursor_rect: QRect from parent_editor.cursorRect() for positioning
        """
        self._all_suggestions = suggestions
        self._filter_text = filter_text.lower()

        # Filter suggestions - prioritize "starts with", then "contains"
        if self._filter_text:
            # First: items that start with the filter text
            starts_with = [s for s in suggestions if s.lower().startswith(self._filter_text)]
            # Second: items that contain the filter text (but don't start with it)
            contains = [s for s in suggestions
                       if self._filter_text in s.lower() and not s.lower().startswith(self._filter_text)]
            filtered = starts_with + contains
        else:
            filtered = suggestions

        # Nothing to show
        if not filtered:
            self.hide()
            return

        # Populate list
        self.clear()
        for suggestion in filtered[:50]:  # Limit to 50 items
            item = QListWidgetItem(suggestion)
            self.addItem(item)

        # Select first item
        if self.count() > 0:
            self.setCurrentRow(0)

        # Calculate size
        self._adjust_size()

        # Position popup below cursor
        if cursor_rect:
            self._position_popup(cursor_rect)

        self.show()
        # Keep focus on editor
        self.parent_editor.setFocus()

    def update_filter(self, filter_text: str):
        """
        Update filtering without changing suggestions.

        Args:
            filter_text: New filter text
        """
        if self._all_suggestions:
            self.show_completions(self._all_suggestions, filter_text)

    def _adjust_size(self):
        """Adjust popup size based on content."""
        # Width based on longest item
        max_width = 150
        for i in range(self.count()):
            item = self.item(i)
            width = self.fontMetrics().horizontalAdvance(item.text()) + 30
            max_width = max(max_width, width)

        self.setFixedWidth(min(max_width, 400))

        # Height based on item count
        item_height = 22
        total_height = min(self.count() * item_height + 4, 200)
        self.setFixedHeight(total_height)

    def _position_popup(self, cursor_rect):
        """Position popup below the text cursor."""
        # Get cursor position in global coordinates
        editor_pos = self.parent_editor.mapToGlobal(QPoint(0, 0))
        cursor_pos = QPoint(
            editor_pos.x() + cursor_rect.x(),
            editor_pos.y() + cursor_rect.y() + cursor_rect.height()
        )

        # Check if popup would go off-screen
        screen = self.screen()
        if screen:
            screen_rect = screen.availableGeometry()

            # Adjust horizontal position
            if cursor_pos.x() + self.width() > screen_rect.right():
                cursor_pos.setX(screen_rect.right() - self.width())

            # Adjust vertical position (show above if no room below)
            if cursor_pos.y() + self.height() > screen_rect.bottom():
                cursor_pos.setY(
                    editor_pos.y() + cursor_rect.y() - self.height()
                )

        self.move(cursor_pos)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on item."""
        self._apply_selection()

    def _apply_selection(self):
        """Apply the current selection."""
        current = self.currentItem()
        if current:
            self.completion_selected.emit(current.text())
        self.hide()

    def navigate_up(self):
        """Move selection up."""
        current_row = self.currentRow()
        if current_row > 0:
            self.setCurrentRow(current_row - 1)

    def navigate_down(self):
        """Move selection down."""
        current_row = self.currentRow()
        if current_row < self.count() - 1:
            self.setCurrentRow(current_row + 1)

    def accept_completion(self) -> bool:
        """
        Accept current selection if popup is visible.

        Returns:
            True if completion was applied, False otherwise
        """
        if self.isVisible() and self.currentItem():
            self._apply_selection()
            return True
        return False

    def cancel(self):
        """Hide popup without applying selection."""
        self.hide()

    def get_selected_text(self) -> Optional[str]:
        """Get currently selected suggestion text."""
        current = self.currentItem()
        return current.text() if current else None

    def check_editor_focus(self):
        """
        Check if parent editor still has focus.
        Called periodically or on events to auto-hide popup.
        """
        if self.isVisible() and not self.parent_editor.hasFocus():
            self.hide()
