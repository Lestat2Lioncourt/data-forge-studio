"""
Completion Mixin - SQL auto-completion for QueryTab.
"""
from __future__ import annotations

import re
import logging
from typing import Optional, Tuple

from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt, QObject, QEvent, QTimer
from PySide6.QtGui import QKeyEvent

from ...widgets.sql_completer import SQLCompleterPopup

logger = logging.getLogger(__name__)


class QueryCompletionMixin:
    """SQL auto-completion methods for QueryTab."""

    def _setup_completer(self):
        """Setup SQL auto-completer."""
        self.completer = SQLCompleterPopup(self.sql_editor)
        self.completer.completion_selected.connect(self._insert_completion)

        # Install event filter to intercept key events
        self.sql_editor.installEventFilter(self)

        # Override focusOutEvent to hide completer when editor loses focus
        self.sql_editor.focusOutEvent = self._editor_focus_out

    def _editor_focus_out(self, event):
        """Handle editor losing focus - hide completer."""
        # Hide completer when editor loses focus
        if self.completer.isVisible():
            self.completer.cancel()
        # Call original focusOutEvent
        QTextEdit.focusOutEvent(self.sql_editor, event)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events for the SQL editor to handle auto-completion."""
        if obj != self.sql_editor:
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            return self._handle_key_press(key_event)

        return super().eventFilter(obj, event)

    def _handle_key_press(self, event: QKeyEvent) -> bool:
        """
        Handle key press for auto-completion.

        Returns:
            True if event was consumed, False to pass to editor
        """
        key = event.key()
        modifiers = event.modifiers()

        # Ctrl+Space: Manual trigger
        if key == Qt.Key.Key_Space and modifiers == Qt.KeyboardModifier.ControlModifier:
            self._trigger_completion(force=True)
            return True

        # If completer is visible, handle navigation
        if self.completer.isVisible():
            if key == Qt.Key.Key_Escape:
                self.completer.cancel()
                return True

            if key == Qt.Key.Key_Up:
                self.completer.navigate_up()
                return True

            if key == Qt.Key.Key_Down:
                self.completer.navigate_down()
                return True

            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                if self.completer.accept_completion():
                    return True

            # For normal characters or backspace, let editor handle it
            # then update the filter dynamically
            if event.text() or key == Qt.Key.Key_Backspace:
                QTimer.singleShot(0, self._update_completer_filter)
                return False  # Let editor process the key

            # Space or other non-word characters close the completer
            if key == Qt.Key.Key_Space:
                self.completer.cancel()
                return False

        # Let the editor handle the key first
        # We'll check for triggers after text changes
        # Schedule trigger check after key is processed
        QTimer.singleShot(0, self._check_auto_trigger)

        return False

    def _update_completer_filter(self):
        """Update the completer filter based on current prefix."""
        if not self.completer.isVisible():
            return

        context, prefix, table_name = self._get_context()

        # If we've typed something that breaks the context, close completer
        if context is None:
            self.completer.cancel()
            return

        # Update the filter with new prefix
        self._completer_prefix = prefix
        self.completer.update_filter(prefix)

    def _check_auto_trigger(self):
        """Check if we should auto-trigger completion after typing."""
        if not self.connection:
            return

        context, prefix, table_name = self._get_context()

        # Auto-trigger rules:
        # - "table_column" (after table.): always trigger (user explicitly wants columns)
        # - "table" (after FROM/JOIN): trigger with 1+ char prefix (helps find tables)
        # - "column" (after SELECT/WHERE): only trigger with 2+ char prefix
        #   (avoids loading all columns which can be slow and annoying)

        if context == "table_column":
            # After "table." - always show columns for that table
            self._trigger_completion(context=context, prefix=prefix, table_name=table_name)

        elif context == "table" and len(prefix) >= 1:
            # After FROM/JOIN with at least 1 char - show matching tables
            self._trigger_completion(context=context, prefix=prefix, table_name=table_name)

        elif context == "column" and len(prefix) >= 2:
            # After SELECT/WHERE with at least 2 chars - show matching columns
            self._trigger_completion(context=context, prefix=prefix, table_name=table_name)

        elif self.completer.isVisible():
            # Update filter if completer is already visible
            if prefix:
                self.completer.update_filter(prefix)
            else:
                self.completer.cancel()

    def _trigger_completion(self, force: bool = False, context: str = None,
                            prefix: str = "", table_name: str = None):
        """
        Trigger the auto-completion popup.

        Args:
            force: If True, show all suggestions (Ctrl+Space)
            context: Detected context ("table", "column", "table_column")
            prefix: Current word prefix for filtering
            table_name: Table name for column completion
        """
        if not self.connection:
            return

        # Get context if not provided
        if context is None:
            context, prefix, table_name = self._get_context()

        suggestions = []

        try:
            if force:
                # Show everything
                tables = self.schema_cache.get_tables(self.connection, self.db_type)
                columns = self.schema_cache.get_all_columns(self.connection, self.db_type)
                suggestions = sorted(set(tables + columns))

            elif context == "table":
                # After FROM/JOIN - show tables
                suggestions = self.schema_cache.get_tables(self.connection, self.db_type)

            elif context == "column":
                # After SELECT/WHERE - show all columns
                suggestions = self.schema_cache.get_all_columns(self.connection, self.db_type)

            elif context == "table_column" and table_name:
                # After table. - show columns for that table
                suggestions = self.schema_cache.get_columns(
                    self.connection, self.db_type, table_name
                )

        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return

        if suggestions:
            self._completer_prefix = prefix
            cursor_rect = self.sql_editor.cursorRect()
            self.completer.show_completions(suggestions, prefix, cursor_rect)

    def _get_context(self) -> Tuple[Optional[str], str, Optional[str]]:
        """
        Analyze text before cursor to determine completion context.

        Returns:
            Tuple of (context_type, prefix, table_name)
            context_type: "table", "column", "table_column", or None
            prefix: Current word being typed
            table_name: For table_column context, the table name
        """
        cursor = self.sql_editor.textCursor()
        text = self.sql_editor.toPlainText()
        pos = cursor.position()

        # Get text before cursor (last 200 chars should be enough)
        text_before = text[max(0, pos - 200):pos]

        # Pattern: table.prefix - columns for specific table
        match = re.search(r'(\w+)\.(\w*)$', text_before)
        if match:
            table_name = match.group(1)
            prefix = match.group(2)
            return ("table_column", prefix, table_name)

        # Pattern: FROM/JOIN table_prefix - tables
        match = re.search(r'(?:FROM|JOIN)\s+(\w*)$', text_before, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            return ("table", prefix, None)

        # Pattern: SELECT columns - all columns
        match = re.search(r'SELECT\s+(?:.*,\s*)?(\w*)$', text_before, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            return ("column", prefix, None)

        # Pattern: WHERE/AND/OR column - all columns
        match = re.search(r'(?:WHERE|AND|OR)\s+(\w*)$', text_before, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            return ("column", prefix, None)

        return (None, "", None)

    def _insert_completion(self, text: str):
        """
        Insert the selected completion into the editor.

        Args:
            text: The completion text to insert
        """
        cursor = self.sql_editor.textCursor()

        # Remove the prefix we're replacing
        if self._completer_prefix:
            for _ in range(len(self._completer_prefix)):
                cursor.deletePreviousChar()

        # Insert the completion
        cursor.insertText(text)
        self.sql_editor.setTextCursor(cursor)
