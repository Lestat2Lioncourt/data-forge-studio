"""
Queries Manager - Manager for saved SQL queries with hierarchical TreeView
Provides interface to view, edit, and execute saved queries organized by category
"""

from typing import List, Optional, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QTextEdit, QLabel, QMenu
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction

from .base import HierarchicalManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.workspace_menu_builder import build_workspace_menu
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, SavedQuery
from ...utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


class QueriesManager(HierarchicalManagerView):
    """
    Manager for saved SQL queries with hierarchical TreeView.

    Layout:
    - TOP: Toolbar
    - LEFT: TreeView (Category > Query)
    - RIGHT: Details panel + SQL editor
    """

    # Signal emitted when query execution is requested (emits SavedQuery object)
    query_execute_requested = Signal(object)

    def __init__(self, parent=None):
        self._db_names = {}  # Cache for database names
        super().__init__(parent)

    # ==================== Abstract Method Implementations ====================

    def _get_explorer_title(self) -> str:
        return tr("queries_explorer")

    def _get_explorer_icon(self) -> str:
        return "queries.png"

    def _get_item_type(self) -> str:
        return "query"

    def _get_category_field(self) -> str:
        return "category"

    def _setup_toolbar_buttons(self, builder: ToolbarBuilder):
        """Add query-specific toolbar buttons."""
        builder.add_button(tr("btn_add"), self._add_query, icon="add.png")
        builder.add_button(tr("btn_edit"), self._edit_query, icon="edit.png")
        builder.add_button(tr("btn_delete"), self._delete_query, icon="delete.png")
        builder.add_separator()
        builder.add_button(tr("btn_execute"), self._execute_query, icon="play.png")

    def _setup_detail_fields(self, form_builder: FormBuilder):
        """Add query detail fields."""
        form_builder.add_field(tr("field_name"), "name")
        form_builder.add_field(tr("field_category"), "category")
        form_builder.add_field(tr("field_description"), "description")
        form_builder.add_field(tr("field_database"), "database")
        form_builder.add_field(tr("field_created"), "created")
        form_builder.add_field(tr("field_modified"), "modified")

    def _setup_content_widgets(self, layout: QVBoxLayout):
        """Add SQL editor to content panel."""
        sql_label = QLabel(tr("sql_query"))
        sql_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(sql_label)

        self.sql_editor = QTextEdit()
        self.sql_editor.setReadOnly(True)
        self.sql_editor.setPlaceholderText(tr("sql_placeholder"))
        UIHelper.apply_monospace_font(self.sql_editor)
        layout.addWidget(self.sql_editor)

    def _load_items(self) -> List[SavedQuery]:
        """Load queries from database, filtered by workspace if set."""
        config_db = get_config_db()

        # Apply workspace filter if set
        if self._workspace_filter:
            queries = config_db.get_workspace_queries(self._workspace_filter)
        else:
            queries = config_db.get_all_saved_queries()

        # Build cache of database names
        db_connections = config_db.get_all_database_connections()
        self._db_names = {db.id: db.name for db in db_connections}

        return queries

    def _get_item_category(self, item: SavedQuery) -> str:
        return item.category or ""

    def _get_item_name(self, item: SavedQuery) -> str:
        return item.name

    def _display_item(self, query: SavedQuery):
        """Display query details and SQL text."""
        if not query:
            self._clear_item_display()
            return

        # Get database name
        db_name = self._db_names.get(query.target_database_id, query.target_database_id or "")

        # Update details form
        self.details_form.set_value("name", query.name)
        self.details_form.set_value("category", query.category or "")
        self.details_form.set_value("description", query.description or "")
        self.details_form.set_value("database", db_name)
        self.details_form.set_value("created", query.created_at or "")
        self.details_form.set_value("modified", query.updated_at or "")

        # Update SQL editor
        self.sql_editor.setPlainText(query.query_text or "")

    def _clear_item_display(self):
        """Clear all details fields."""
        self.details_form.set_value("name", "")
        self.details_form.set_value("category", "")
        self.details_form.set_value("description", "")
        self.details_form.set_value("database", "")
        self.details_form.set_value("created", "")
        self.details_form.set_value("modified", "")
        self.sql_editor.clear()

    def _on_item_action(self, item: SavedQuery):
        """Execute query on double-click."""
        self._execute_query()

    # ==================== Context Menu ====================

    def _build_category_context_menu(self, menu: QMenu, category_name: str):
        """Build context menu for category folder."""
        add_action = QAction(tr("btn_add_query"), self)
        add_action.triggered.connect(self._add_query)
        menu.addAction(add_action)

    def _build_item_context_menu(self, menu: QMenu, query: SavedQuery):
        """Build context menu for a query."""
        # Execute action
        exec_action = QAction(tr("btn_execute"), self)
        exec_action.triggered.connect(self._execute_query)
        menu.addAction(exec_action)

        menu.addSeparator()

        # Edit action
        edit_action = QAction(tr("btn_edit"), self)
        edit_action.triggered.connect(self._edit_query)
        menu.addAction(edit_action)

        # Delete action
        delete_action = QAction(tr("btn_delete"), self)
        delete_action.triggered.connect(self._delete_query)
        menu.addAction(delete_action)

        menu.addSeparator()

        # Workspaces submenu
        workspace_menu = self._build_workspace_submenu(query.id)
        if workspace_menu:
            menu.addMenu(workspace_menu)

    def _build_workspace_submenu(self, query_id: str) -> QMenu:
        """Build a submenu for adding/removing a query to/from workspaces."""
        config_db = get_config_db()
        return build_workspace_menu(
            parent=self,
            item_id=query_id,
            get_item_workspaces=lambda: config_db.get_query_workspaces(query_id),
            add_to_workspace=lambda ws_id: config_db.add_query_to_workspace(ws_id, query_id),
            remove_from_workspace=lambda ws_id: config_db.remove_query_from_workspace(ws_id, query_id),
        )

    # ==================== Actions ====================

    def _add_query(self):
        """Add a new query."""
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("add_query_title"),
            self
        )

    def _edit_query(self):
        """Edit selected query."""
        if not self._current_item:
            DialogHelper.warning(tr("select_query_first"), tr("edit_query_title"), self)
            return
        DialogHelper.info(tr("feature_coming_soon"), tr("edit_query_title"), self)

    def _delete_query(self):
        """Delete selected query."""
        if not self._current_item:
            DialogHelper.warning(tr("select_query_first"), tr("delete_query_title"), self)
            return

        query_name = self._current_item.name

        if DialogHelper.confirm(
            tr("confirm_delete_query").format(name=query_name),
            tr("delete_query_title"),
            self
        ):
            try:
                config_db = get_config_db()
                config_db.delete_query(self._current_item.id)
                self.refresh()
                DialogHelper.info(tr("query_deleted"), tr("delete_query_title"), self)
            except Exception as e:
                DialogHelper.error(str(e), tr("error"), self)

    def _execute_query(self):
        """Execute selected query."""
        if not self._current_item:
            DialogHelper.warning(tr("select_query_first"), tr("execute_query_title"), self)
            return
        # Emit signal with the query object for external handling
        self.query_execute_requested.emit(self._current_item)
