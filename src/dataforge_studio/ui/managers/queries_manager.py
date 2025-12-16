"""
Queries Manager - Manager for saved SQL queries
Provides interface to view, edit, and execute saved queries
"""

from typing import List, Optional, Any
import uuid
from PySide6.QtWidgets import QTextEdit, QWidget, QMenu, QInputDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.dialog_helper import DialogHelper
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db


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
        self._setup_context_menu()
        self.refresh()

    def _get_tree_columns(self) -> List[str]:
        """
        Return column names for tree view.

        Returns:
            List of column names
        """
        return [tr("col_name"), tr("col_database"), tr("col_description")]

    def get_tree_widget(self):
        """Return the tree widget for embedding in ResourcesManager."""
        return self.tree_view.tree

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
        self._replace_toolbar(toolbar_builder)

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
        UIHelper.apply_monospace_font(self.sql_editor)

        # TODO: Apply SQL syntax highlighting when available
        self.content_layout.addWidget(self.sql_editor)

    def _load_items(self):
        """Load queries from database into tree view."""
        try:
            config_db = get_config_db()
            queries = config_db.get_all_saved_queries()

            # Build a cache of database names
            db_connections = config_db.get_all_database_connections()
            db_names = {db.id: db.name for db in db_connections}

            for query in queries:
                # Get database name from target_database_id
                db_name = db_names.get(query.target_database_id, query.target_database_id)
                self.tree_view.add_item(
                    parent=None,
                    text=[query.name, db_name, query.description or ""],
                    data=query
                )
        except Exception as e:
            print(f"Error loading queries: {e}")  # Log to console during startup

    def _display_item(self, item_data: Any):
        """
        Display selected query details and SQL text.

        Args:
            item_data: Query data object (dict or database model)
        """
        wrapper = self._wrap_item(item_data)

        # Get database name from target_database_id
        target_db_id = wrapper.get_str("target_database_id")
        db_name = target_db_id  # Default to ID
        if target_db_id:
            config_db = get_config_db()
            db_conn = config_db.get_database_connection(target_db_id)
            if db_conn:
                db_name = db_conn.name

        # Update details form
        self.details_form.set_value("name", wrapper.get_str("name"))
        self.details_form.set_value("description", wrapper.get_str("description"))
        self.details_form.set_value("database", db_name)
        self.details_form.set_value("created", wrapper.get_str("created_at"))
        self.details_form.set_value("modified", wrapper.get_str("updated_at"))

        # Update SQL editor
        self.sql_editor.setPlainText(wrapper.get_str("query_text"))

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
        if not self._check_item_selected(tr("select_query_first"), tr("edit_query_title")):
            return

        # TODO: Open dialog to edit query
        DialogHelper.info(tr("feature_coming_soon"), tr("edit_query_title"), self)

    def _delete_query(self):
        """Delete selected query."""
        if not self._check_item_selected(tr("select_query_first"), tr("delete_query_title")):
            return

        query_name = self._get_item_name()

        if DialogHelper.confirm(
            tr("confirm_delete_query").format(name=query_name),
            tr("delete_query_title"),
            self
        ):
            # TODO: Delete from database
            # config_db.delete_query(self._current_item.id)
            # self.refresh()
            DialogHelper.info(tr("query_deleted"), tr("delete_query_title"), self)

    def _execute_query(self):
        """Execute selected query."""
        if not self._check_item_selected(tr("select_query_first"), tr("execute_query_title")):
            return

        # TODO: Execute query and display results in a separate window/dialog
        DialogHelper.info(tr("feature_coming_soon"), tr("execute_query_title"), self)

    # ===== Context Menu Methods =====

    def _setup_context_menu(self):
        """Setup context menu for tree items."""
        self.tree_view.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.tree.customContextMenuRequested.connect(self._on_context_menu)

    def _on_context_menu(self, position):
        """Handle context menu request on tree item."""
        item = self.tree_view.tree.itemAt(position)
        if not item:
            return

        data = self.tree_view.get_item_data(item)
        if not data:
            return

        # Get query ID
        query_id = getattr(data, 'id', None) or (data.get('id') if isinstance(data, dict) else None)
        if not query_id:
            return

        menu = QMenu(self)

        # Add "Workspaces" submenu
        workspace_menu = self._build_workspace_submenu(query_id)
        if workspace_menu:
            menu.addMenu(workspace_menu)

        if menu.actions():
            menu.exec(self.tree_view.tree.viewport().mapToGlobal(position))

    def _build_workspace_submenu(self, query_id: str) -> QMenu:
        """Build a submenu for adding/removing a query to/from workspaces."""
        config_db = get_config_db()
        workspaces = config_db.get_all_workspaces()

        menu = QMenu(tr("menu_workspaces"), self)
        menu.setIcon(self._get_workspace_icon())

        if not workspaces:
            # No workspaces - show option to create one
            new_action = QAction(tr("new_workspace"), self)
            new_action.triggered.connect(lambda: self._create_new_workspace_and_add(query_id))
            menu.addAction(new_action)
            return menu

        # Get workspaces that contain this query
        query_workspaces = config_db.get_query_workspaces(query_id)
        workspace_ids_with_query = {ws.id for ws in query_workspaces}

        # Add each workspace with checkmark if query is in it
        for ws in workspaces:
            is_in_workspace = ws.id in workspace_ids_with_query
            action = QAction(ws.name, self)
            action.setCheckable(True)
            action.setChecked(is_in_workspace)
            action.triggered.connect(
                lambda checked, wid=ws.id, in_ws=is_in_workspace:
                self._toggle_workspace(wid, query_id, in_ws)
            )
            menu.addAction(action)

        menu.addSeparator()

        # Add "New Workspace..." option
        new_action = QAction(tr("new_workspace") + "...", self)
        new_action.triggered.connect(lambda: self._create_new_workspace_and_add(query_id))
        menu.addAction(new_action)

        return menu

    def _get_workspace_icon(self):
        """Get workspace icon."""
        from ...utils.image_loader import get_icon
        return get_icon("workspace.png", size=16) or get_icon("folder.png", size=16)

    def _toggle_workspace(self, workspace_id: str, query_id: str, is_in_workspace: bool):
        """Toggle a query in/out of a workspace."""
        config_db = get_config_db()

        if is_in_workspace:
            # Remove from workspace
            config_db.remove_query_from_workspace(workspace_id, query_id)
        else:
            # Add to workspace
            config_db.add_query_to_workspace(workspace_id, query_id)

    def _create_new_workspace_and_add(self, query_id: str):
        """Create a new workspace and add the query to it."""
        from ...database.config_db import Workspace

        name, ok = QInputDialog.getText(self, tr("new_workspace"), tr("workspace_name") + ":")
        if ok and name.strip():
            config_db = get_config_db()
            ws = Workspace(
                id=str(uuid.uuid4()),
                name=name.strip(),
                description=""
            )
            if config_db.add_workspace(ws):
                config_db.add_query_to_workspace(ws.id, query_id)
            else:
                DialogHelper.warning(tr("workspace_create_failed"), tr("error"), self)
