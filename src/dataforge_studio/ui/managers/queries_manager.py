"""
Queries Manager - Manager for saved SQL queries
Provides interface to view, edit, and execute saved queries
"""

from typing import List, Optional, Any
from PySide6.QtWidgets import QTextEdit, QWidget
from PySide6.QtCore import Qt

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr


class QueriesManager(BaseManagerView):
    """Manager for saved SQL queries."""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize queries manager.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent, title="Queries Manager")
        self._setup_toolbar()
        self._setup_details()
        self._setup_content()
        # Refresh will be called when connected to database

    def _get_tree_columns(self) -> List[str]:
        """
        Return column names for tree view.

        Returns:
            List of column names
        """
        return [tr("col_name"), tr("col_database"), tr("col_description")]

    def _setup_toolbar(self):
        """Setup toolbar with query management buttons."""
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_refresh"), self.refresh, icon="refresh.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_add"), self._add_query, icon="add.png")
        toolbar_builder.add_button(tr("btn_edit"), self._edit_query, icon="edit.png")
        toolbar_builder.add_button(tr("btn_delete"), self._delete_query, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_execute"), self._execute_query, icon="play.png")

        # Replace default toolbar
        old_toolbar = self.toolbar
        self.toolbar = toolbar_builder.build()
        self.layout().replaceWidget(old_toolbar, self.toolbar)
        old_toolbar.setParent(None)

    def _setup_details(self):
        """Setup details panel with query information."""
        self.details_form = FormBuilder(title=tr("query_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("field_description"), "description") \
            .add_field(tr("field_database"), "database") \
            .add_field(tr("field_created"), "created") \
            .add_field(tr("field_modified"), "modified") \
            .build()

        self.details_layout.addWidget(self.details_form)

    def _setup_content(self):
        """Setup content panel with SQL editor."""
        # SQL editor (read-only for now)
        self.sql_editor = QTextEdit()
        self.sql_editor.setReadOnly(True)
        self.sql_editor.setPlaceholderText(tr("sql_placeholder"))

        # TODO: Apply SQL syntax highlighting when available
        # from ...utils.sql_highlighter import SQLHighlighter
        # self.highlighter = SQLHighlighter(self.sql_editor.document())

        self.content_layout.addWidget(self.sql_editor)

    def _load_items(self):
        """Load queries from database into tree view."""
        # TODO: Integrate with database layer when available
        # For now, create placeholder data

        # Placeholder queries
        placeholder_queries = [
            {
                "name": "Sample Query 1",
                "database": "Database1",
                "description": "Example query",
                "query_text": "SELECT * FROM users WHERE active = 1;",
                "created": "2025-12-01",
                "modified": "2025-12-10"
            },
            {
                "name": "Sample Query 2",
                "database": "Database2",
                "description": "Another example",
                "query_text": "SELECT COUNT(*) FROM orders;",
                "created": "2025-12-05",
                "modified": "2025-12-08"
            }
        ]

        for query in placeholder_queries:
            self.tree_view.add_item(
                parent=None,
                text=[query["name"], query["database"], query["description"]],
                data=query
            )

        # Real implementation will be:
        # try:
        #     from ...database.config_db import get_config_db
        #     config_db = get_config_db()
        #     queries = config_db.get_all_queries()
        #
        #     for query in queries:
        #         self.tree_view.add_item(
        #             parent=None,
        #             text=[query.name, query.database_name, query.description],
        #             data=query
        #         )
        # except Exception as e:
        #     DialogHelper.error(
        #         tr("error_loading_queries"),
        #         tr("error_title"),
        #         self,
        #         details=str(e)
        #     )

    def _display_item(self, item_data: Any):
        """
        Display selected query details and SQL text.

        Args:
            item_data: Query data object (dict or database model)
        """
        # Handle both dict (placeholder) and database model
        if isinstance(item_data, dict):
            name = item_data.get("name", "")
            description = item_data.get("description", "")
            database = item_data.get("database", "")
            created = item_data.get("created", "")
            modified = item_data.get("modified", "")
            query_text = item_data.get("query_text", "")
        else:
            # Assume it's a database model with attributes
            name = getattr(item_data, "name", "")
            description = getattr(item_data, "description", "")
            database = getattr(item_data, "database_name", "")
            created = str(getattr(item_data, "created_at", ""))
            modified = str(getattr(item_data, "modified_at", ""))
            query_text = getattr(item_data, "query_text", "")

        # Update details form
        self.details_form.set_value("name", name)
        self.details_form.set_value("description", description)
        self.details_form.set_value("database", database)
        self.details_form.set_value("created", created)
        self.details_form.set_value("modified", modified)

        # Update SQL editor
        self.sql_editor.setPlainText(query_text)

    def _add_query(self):
        """Add a new query."""
        # TODO: Open dialog to create new query
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("add_query_title"),
            self
        )

    def _edit_query(self):
        """Edit selected query."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_query_first"),
                tr("edit_query_title"),
                self
            )
            return

        # TODO: Open dialog to edit query
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("edit_query_title"),
            self
        )

    def _delete_query(self):
        """Delete selected query."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_query_first"),
                tr("delete_query_title"),
                self
            )
            return

        # Get query name
        if isinstance(self._current_item, dict):
            query_name = self._current_item.get("name", "")
        else:
            query_name = getattr(self._current_item, "name", "")

        # Confirm deletion
        if DialogHelper.confirm(
            tr("confirm_delete_query").format(name=query_name),
            tr("delete_query_title"),
            self
        ):
            # TODO: Delete from database
            # config_db.delete_query(self._current_item.id)
            # self.refresh()
            DialogHelper.info(
                tr("query_deleted"),
                tr("delete_query_title"),
                self
            )

    def _execute_query(self):
        """Execute selected query."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_query_first"),
                tr("execute_query_title"),
                self
            )
            return

        # TODO: Execute query and display results in a separate window/dialog
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("execute_query_title"),
            self
        )
