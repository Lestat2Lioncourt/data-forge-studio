"""
EditableTabWidget - QTabWidget with inline tab renaming and optional "+" tab.

Features:
- Double-click a tab to rename it inline (QLineEdit overlay)
- Optional "+" tab always at the end to request new tab creation
- Configurable protected tabs (by index or suffix count)

Usage:
    tab_widget = EditableTabWidget()
    tab_widget.set_protected_tabs({0})      # Indices that cannot be renamed
    tab_widget.set_protected_suffix_tabs(1) # Last N tabs cannot be renamed
    tab_widget.tabRenamed.connect(callback)  # (index, old_name, new_name)

    tab_widget.enable_new_tab_button()       # Show "+" tab
    tab_widget.newTabRequested.connect(on_new_tab)
"""
from PySide6.QtWidgets import QTabWidget, QTabBar, QLineEdit, QWidget
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QIcon

import logging
logger = logging.getLogger(__name__)


class _EditableTabBar(QTabBar):
    """Tab bar with a compact "+" tab at the end."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._has_plus_tab = False

    def set_has_plus_tab(self, enabled: bool):
        self._has_plus_tab = enabled
        self.setExpanding(not enabled)

    def tabSizeHint(self, index: int) -> QSize:
        size = super().tabSizeHint(index)
        if self._has_plus_tab and index == self.count() - 1:
            # Square-ish tab + 4px breathing room
            size.setWidth(size.height() + 4)
        return size

    def minimumTabSizeHint(self, index: int) -> QSize:
        if self._has_plus_tab and index == self.count() - 1:
            return self.tabSizeHint(index)
        return super().minimumTabSizeHint(index)


class EditableTabWidget(QTabWidget):
    """QTabWidget with inline tab renaming and optional new-tab button."""

    tabRenamed = Signal(int, str, str)  # (index, old_name, new_name)
    newTabRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tab_bar = _EditableTabBar(self)
        self.setTabBar(self._tab_bar)
        self._protected_indices: set = set()
        self._protected_suffix_count: int = 0
        self._edit: QLineEdit | None = None
        self._has_new_tab_button: bool = False

        self.tabBarDoubleClicked.connect(self._start_edit)

    # -----------------------------------------------------------------
    # Protected tabs configuration
    # -----------------------------------------------------------------

    def set_protected_tabs(self, indices: set):
        """Set tab indices that cannot be renamed (e.g. welcome tab at 0)."""
        self._protected_indices = indices

    def set_protected_suffix_tabs(self, count: int):
        """Protect the last N tabs from renaming (e.g. Messages tab)."""
        self._protected_suffix_count = count

    def _is_protected(self, index: int) -> bool:
        if index < 0:
            return True
        if index in self._protected_indices:
            return True
        if self._protected_suffix_count > 0:
            if index >= self.count() - self._protected_suffix_count:
                return True
        # The "+" tab is always protected
        if self._has_new_tab_button and index == self.count() - 1:
            return True
        return False

    # -----------------------------------------------------------------
    # New tab button (as a permanent "+" tab at the end)
    # -----------------------------------------------------------------

    def enable_new_tab_button(self):
        """Add a "+" tab at the end that emits newTabRequested when clicked."""
        self._has_new_tab_button = True
        placeholder = QWidget()
        placeholder.setEnabled(False)

        # Use plain text "+" — no icon avoids Qt icon/text gap issues
        super().addTab(placeholder, "+")
        self._plus_placeholder = placeholder

        plus_index = self.count() - 1
        # Make the "+" tab non-closable
        tab_bar = self.tabBar()
        tab_bar.setTabButton(plus_index, QTabBar.RightSide, None)
        tab_bar.setTabButton(plus_index, QTabBar.LeftSide, None)

        self._tab_bar.set_has_plus_tab(True)

        self.tabBar().tabBarClicked.connect(self._intercept_plus_tab)

    def _intercept_plus_tab(self, index: int):
        """If the "+" tab is clicked, emit newTabRequested and revert selection."""
        if not self._has_new_tab_button:
            return
        plus_index = self.count() - 1
        if index == plus_index:
            # Revert to previous tab before emitting (avoid showing empty widget)
            prev = plus_index - 1 if plus_index > 0 else 0
            self.blockSignals(True)
            self.setCurrentIndex(prev)
            self.blockSignals(False)
            self.newTabRequested.emit()

    def addTab(self, widget, *args):
        """Override to insert before the "+" tab when it exists."""
        if self._has_new_tab_button and self.count() > 0:
            # Don't redirect if we're adding the "+" placeholder itself
            if widget is getattr(self, '_plus_placeholder', None):
                return super().addTab(widget, *args)
            # Insert before the "+" tab
            plus_index = self.count() - 1
            return self.insertTab(plus_index, widget, *args)
        return super().addTab(widget, *args)

    # -----------------------------------------------------------------
    # Inline renaming
    # -----------------------------------------------------------------

    def _start_edit(self, index: int):
        """Show an inline QLineEdit over the tab being renamed."""
        if self._is_protected(index):
            return

        # Cancel any existing edit
        if self._edit is not None:
            self._commit_edit()

        tab_bar = self.tabBar()
        rect = tab_bar.tabRect(index)

        edit = QLineEdit(tab_bar)
        # Use the tab bar font to avoid QFont warnings
        bar_font = tab_bar.font()
        if bar_font.pointSize() > 0:
            edit.setFont(bar_font)
        edit.setText(self.tabText(index))
        edit.setGeometry(rect)
        edit.selectAll()
        edit.setFocus()

        edit.setProperty("_tab_index", index)
        edit.setProperty("_old_name", self.tabText(index))

        edit.editingFinished.connect(self._commit_edit)
        edit.installEventFilter(self)

        edit.show()
        self._edit = edit

    def _commit_edit(self):
        """Apply the edit and remove the QLineEdit."""
        edit = self._edit
        if edit is None:
            return
        self._edit = None

        index = edit.property("_tab_index")
        old_name = edit.property("_old_name")
        new_name = edit.text().strip()

        edit.hide()
        # Defer deletion to avoid issues during signal handling
        QTimer.singleShot(0, edit.deleteLater)

        if new_name and new_name != old_name:
            self.setTabText(index, new_name)
            # Update widget's tab_name attribute if it has one
            widget = self.widget(index)
            if hasattr(widget, 'tab_name'):
                widget.tab_name = new_name
            self.tabRenamed.emit(index, old_name, new_name)
            logger.info(f"Renamed tab from '{old_name}' to '{new_name}'")

    def _cancel_edit(self):
        """Discard the edit and remove the QLineEdit."""
        edit = self._edit
        if edit is None:
            return
        self._edit = None
        edit.hide()
        QTimer.singleShot(0, edit.deleteLater)

    def eventFilter(self, obj, event):
        """Handle Escape key to cancel editing."""
        if obj is self._edit and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key_Escape:
                self._cancel_edit()
                return True
        return super().eventFilter(obj, event)
