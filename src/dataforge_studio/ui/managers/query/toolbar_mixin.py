"""
Toolbar Mixin - Toolbar actions, formatting and save for QueryTab.
"""
from __future__ import annotations

import logging

from PySide6.QtWidgets import QDialog

from ...widgets.dialog_helper import DialogHelper
from ...core.i18n_bridge import tr
from ....utils.sql_formatter import format_sql
from ....config.user_preferences import UserPreferences

logger = logging.getLogger(__name__)


class QueryToolbarMixin:
    """Toolbar action methods for QueryTab."""

    def _on_execute_mode_changed(self, index: int):
        """Update tooltip when execute mode changes."""
        mode = self.execute_combo.currentData()
        if mode == "auto":
            self.run_btn.setToolTip(tr("query_execute_auto_tooltip"))
            self.run_btn.setShortcut("F5")
        elif mode == "query":
            self.run_btn.setToolTip(tr("query_execute_query_tooltip"))
            self.run_btn.setShortcut("F5")
        else:
            self.run_btn.setToolTip(tr("query_execute_script_tooltip"))
            self.run_btn.setShortcut("F6")

    def _run_execute(self):
        """Execute query based on selected mode."""
        from ....utils.sql_splitter import needs_script_mode

        mode = self.execute_combo.currentData()
        if mode == "auto":
            sql = self._get_executable_sql()
            if not sql:
                self._execute_as_query()  # Let it show the "no query" warning
                return
            if needs_script_mode(sql, self.db_type):
                logger.debug("Auto mode: detected non-SELECT statements, using script mode")
                self._execute_as_script()
            else:
                logger.debug("Auto mode: all SELECT statements, using query mode")
                self._execute_as_query()
        elif mode == "script":
            self._execute_as_script()
        else:
            self._execute_as_query()

    def _on_format_changed(self, index: int):
        """Save format preference when changed."""
        style = self.format_combo.currentData()
        prefs = UserPreferences.instance()
        prefs.set("sql_format_style", style)

    def _run_format(self):
        """Format SQL based on selected style."""
        style = self.format_combo.currentData()
        self._format_sql(style)

    def _run_export(self):
        """Export SQL - opens dialog with language selection."""
        from ..script_format_dialog import ScriptFormatDialog

        query_text = self.sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_format"), parent=self)
            return

        dialog = ScriptFormatDialog(
            parent=self,
            query_text=query_text
        )
        dialog.exec()

    def _format_sql(self, style: str):
        """
        Format SQL query with specified style.

        Args:
            style: Format style ("compact", "expanded", "comma_first", "ultimate")
        """
        query_text = self.sql_editor.toPlainText().strip()

        if not query_text:
            return

        try:
            formatted = format_sql(query_text, style)
            self.sql_editor.setPlainText(formatted)

        except Exception as e:
            logger.error(f"SQL formatting error: {e}")
            DialogHelper.error("Formatting failed", parent=self, details=str(e))

    def _format_for_python(self):
        """
        Format the SQL query as a Python variable assignment.
        Shows result in a dialog with copy option.
        """
        from ..script_format_dialog import ScriptFormatDialog

        query_text = self.sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_format"), parent=self)
            return

        # Show format dialog
        dialog = ScriptFormatDialog(
            parent=self,
            query_text=query_text,
            format_type="python"
        )
        dialog.exec()

    def _format_for_tsql(self):
        """
        Format the SQL query as a T-SQL variable assignment.
        Shows result in a dialog with copy option.
        """
        from ..script_format_dialog import ScriptFormatDialog

        query_text = self.sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_format"), parent=self)
            return

        # Show format dialog
        dialog = ScriptFormatDialog(
            parent=self,
            query_text=query_text,
            format_type="tsql"
        )
        dialog.exec()

    def set_query_text(self, query: str):
        """Set the SQL query text"""
        self.sql_editor.setPlainText(query)

    def get_query_text(self) -> str:
        """Get the SQL query text"""
        return self.sql_editor.toPlainText()

    def _clear_query(self):
        """Clear the SQL editor"""
        self.sql_editor.clear()

    def _on_edit_query_requested(self, query_text: str):
        """Open a new query tab with the given query formatted in ultimate style."""
        if not self._database_manager:
            return

        # Format the query using ultimate style
        formatted_query = format_sql(query_text, style="ultimate")

        # Find the tab widget that contains this QueryTab (same context: Workspace or Resources)
        parent_tw = self._get_parent_tab_widget()

        # Get current database ID
        db_id = self.db_connection.id if self.db_connection else None

        # Create new query tab in the same context
        new_tab = self._database_manager._new_query_tab(
            db_id=db_id,
            target_tab_widget=parent_tw
        )

        if new_tab:
            new_tab.set_query_text(formatted_query)

    def _get_parent_tab_widget(self):
        """Find the QTabWidget that contains this QueryTab."""
        from PySide6.QtWidgets import QTabWidget
        parent = self.parentWidget()
        while parent:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parentWidget()
        return None

    def _save_query(self):
        """Save the current query to saved queries collection.

        If this tab was opened from a saved query (_saved_query is set),
        updates the existing query. Otherwise creates a new one.
        """
        from ...widgets.save_query_dialog import SaveQueryDialog
        from ....database.config_db import get_config_db, SavedQuery

        # Get query text
        query_text = self.sql_editor.toPlainText().strip()
        if not query_text:
            DialogHelper.warning(tr("no_query_to_save"), parent=self)
            return

        # Get database info
        database_name = ""
        database_id = ""
        current_db_name = self.current_database or ""

        if self.db_connection:
            database_name = self.db_connection.name
            database_id = self.db_connection.id
        else:
            logger.warning("No db_connection available in QueryTab")

        # Build display: "Connection — Database" or just connection name
        display_name = database_name
        if current_db_name and current_db_name != database_name:
            display_name = f"{database_name} — {current_db_name}"

        # If opened from an existing saved query, use edit mode
        if self._saved_query:
            # Update the saved query's text with current editor content
            self._saved_query.query_text = query_text

            dialog = SaveQueryDialog(
                parent=self,
                database_name=display_name,
                existing_query=self._saved_query
            )
        else:
            dialog = SaveQueryDialog(
                parent=self,
                query_text=query_text,
                database_name=display_name,
                database_id=database_id
            )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_query_data()

            try:
                config_db = get_config_db()

                if self._saved_query:
                    # UPDATE existing saved query
                    self._saved_query.name = data["name"]
                    self._saved_query.description = data["description"]
                    self._saved_query.category = data["category"]
                    self._saved_query.query_text = data["query_text"]
                    self._saved_query.target_database_name = current_db_name or self._saved_query.target_database_name

                    result = config_db.update_saved_query(self._saved_query)

                    if result:
                        DialogHelper.info(
                            f"Query '{data['name']}' updated.",
                            parent=self
                        )
                        logger.info(f"Updated saved query: {data['name']}")
                        self.query_saved.emit()
                    else:
                        DialogHelper.error("Failed to update query.", parent=self)
                else:
                    # CREATE new saved query
                    saved_query = SavedQuery(
                        id="",  # Will be generated
                        name=data["name"],
                        target_database_id=data["target_database_id"],
                        query_text=data["query_text"],
                        category=data["category"],
                        description=data["description"],
                        target_database_name=current_db_name
                    )

                    result = config_db.add_saved_query(saved_query)

                    if result:
                        # Auto-link to workspace if created from workspace context
                        if self._workspace_id:
                            config_db.add_query_to_workspace(self._workspace_id, saved_query.id)
                            logger.info(f"Auto-linked query '{data['name']}' to workspace {self._workspace_id}")

                        # Keep reference so next save will update instead of create
                        self._saved_query = saved_query

                        DialogHelper.info(
                            tr("query_saved_success", name=data['name']),
                            parent=self
                        )
                        logger.info(f"Saved query: {data['name']} to category: {data['category']}")
                        self.query_saved.emit()
                    else:
                        DialogHelper.error(
                            tr("query_save_db_constraint"),
                            parent=self,
                            details=f"Database ID: {data['target_database_id']}"
                        )

            except Exception as e:
                logger.error(f"Error saving query: {e}")
                DialogHelper.error(
                    tr("query_save_failed"),
                    parent=self,
                    details=str(e)
                )
