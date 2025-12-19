"""
Queries Manager - Manager for saved SQL queries with hierarchical TreeView
Provides interface to view, edit, and execute saved queries organized by category
"""

from typing import List, Optional, Any, Dict
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QLabel,
    QMenu, QInputDialog, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.pinnable_panel import PinnablePanel
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, SavedQuery
from ...utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


class QueriesManager(QWidget):
    """
    Manager for saved SQL queries with hierarchical TreeView.

    Layout:
    - TOP: Toolbar
    - LEFT: TreeView (Category > Query)
    - RIGHT: Details panel + SQL editor
    """

    # Signal emitted when item is selected
    item_selected = Signal(object)
    # Signal emitted when query execution is requested (emits SavedQuery object)
    query_execute_requested = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._current_item = None
        self._category_items: Dict[str, QTreeWidgetItem] = {}

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toolbar
        self._setup_toolbar()
        layout.addWidget(self.toolbar)

        # Main splitter (horizontal: left tree, right content)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Pinnable panel with hierarchical tree
        self.left_panel = PinnablePanel(
            title=tr("queries_explorer"),
            icon_name="queries.png"
        )
        self.left_panel.set_normal_width(250)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        tree_layout.addWidget(self.tree)

        self.left_panel.set_content(tree_container)
        self.main_splitter.addWidget(self.left_panel)

        # Right panel: Details + SQL editor
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Details panel
        self.details_panel = QWidget()
        self.details_layout = QVBoxLayout(self.details_panel)
        self.details_layout.setContentsMargins(5, 5, 5, 5)
        self._setup_details()
        right_splitter.addWidget(self.details_panel)

        # SQL editor panel
        self.content_panel = QWidget()
        self.content_layout = QVBoxLayout(self.content_panel)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self._setup_content()
        right_splitter.addWidget(self.content_panel)

        right_splitter.setSizes([150, 400])
        self.main_splitter.addWidget(right_splitter)

        self.main_splitter.setSizes([250, 750])
        layout.addWidget(self.main_splitter)

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
        self.toolbar = toolbar_builder.build()

    def _setup_details(self):
        """Setup details panel with query information."""
        self.details_form = FormBuilder(title=tr("query_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("field_category"), "category") \
            .add_field(tr("field_description"), "description") \
            .add_field(tr("field_database"), "database") \
            .add_field(tr("field_created"), "created") \
            .add_field(tr("field_modified"), "modified")

        self.details_layout.addWidget(self.details_form.container)

    def _setup_content(self):
        """Setup content panel with SQL editor."""
        sql_label = QLabel(tr("sql_query"))
        sql_label.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(sql_label)

        self.sql_editor = QTextEdit()
        self.sql_editor.setReadOnly(True)
        self.sql_editor.setPlaceholderText(tr("sql_placeholder"))
        UIHelper.apply_monospace_font(self.sql_editor)
        self.content_layout.addWidget(self.sql_editor)

    def get_tree_widget(self):
        """Return the tree widget for embedding."""
        return self.tree

    def refresh(self):
        """Reload all queries from database."""
        self.tree.clear()
        self._category_items.clear()
        self._current_item = None
        self._clear_details()
        self._load_queries()

    def _load_queries(self):
        """Load queries from database into hierarchical tree."""
        try:
            config_db = get_config_db()
            queries = config_db.get_all_saved_queries()

            # Build cache of database names
            db_connections = config_db.get_all_database_connections()
            self._db_names = {db.id: db.name for db in db_connections}

            # Group queries by category
            categories: Dict[str, List[SavedQuery]] = {}
            for query in queries:
                cat = query.category or "No category"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(query)

            # Create tree structure
            folder_icon = get_icon("Category", size=16)
            query_icon = get_icon("queries", size=16)

            for category_name in sorted(categories.keys()):
                # Create category folder
                category_item = QTreeWidgetItem(self.tree)
                category_item.setText(0, f"{category_name} ({len(categories[category_name])})")
                if folder_icon:
                    category_item.setIcon(0, folder_icon)
                category_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "category",
                    "name": category_name
                })
                category_item.setExpanded(True)
                self._category_items[category_name] = category_item

                # Add queries under category
                for query in sorted(categories[category_name], key=lambda q: q.name):
                    query_item = QTreeWidgetItem(category_item)
                    query_item.setText(0, query.name)
                    if query_icon:
                        query_item.setIcon(0, query_icon)
                    query_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "query",
                        "query": query
                    })

        except Exception as e:
            logger.error(f"Error loading queries: {e}")

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle single click on tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "query":
            self._current_item = data.get("query")
            self._display_query(self._current_item)
            self.item_selected.emit(self._current_item)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "query":
            # Execute query on double-click
            self._current_item = data.get("query")
            self._execute_query()

    def _display_query(self, query: SavedQuery):
        """Display query details and SQL text."""
        if not query:
            self._clear_details()
            return

        # Get database name
        db_name = self._db_names.get(query.target_database_id, query.target_database_id)

        # Update details form
        self.details_form.set_value("name", query.name)
        self.details_form.set_value("category", query.category or "")
        self.details_form.set_value("description", query.description or "")
        self.details_form.set_value("database", db_name)
        self.details_form.set_value("created", query.created_at or "")
        self.details_form.set_value("modified", query.updated_at or "")

        # Update SQL editor
        self.sql_editor.setPlainText(query.query_text or "")

    def _clear_details(self):
        """Clear all details fields."""
        self.details_form.set_value("name", "")
        self.details_form.set_value("category", "")
        self.details_form.set_value("description", "")
        self.details_form.set_value("database", "")
        self.details_form.set_value("created", "")
        self.details_form.set_value("modified", "")
        self.sql_editor.clear()

    # ===== Actions =====

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

    # ===== Context Menu =====

    def _on_context_menu(self, position):
        """Handle context menu request on tree item."""
        item = self.tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if data.get("type") == "category":
            # Context menu for category
            add_action = QAction(tr("btn_add_query"), self)
            add_action.triggered.connect(self._add_query)
            menu.addAction(add_action)

        elif data.get("type") == "query":
            query = data.get("query")
            query_id = query.id if query else None

            if query_id:
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
                workspace_menu = self._build_workspace_submenu(query_id)
                if workspace_menu:
                    menu.addMenu(workspace_menu)

        if menu.actions():
            menu.exec(self.tree.viewport().mapToGlobal(position))

    def _build_workspace_submenu(self, query_id: str) -> QMenu:
        """Build a submenu for adding/removing a query to/from workspaces."""
        config_db = get_config_db()
        workspaces = config_db.get_all_workspaces()

        menu = QMenu(tr("menu_workspaces"), self)
        workspace_icon = get_icon("Workspace", size=16) or get_icon("folder", size=16)
        if workspace_icon:
            menu.setIcon(workspace_icon)

        if not workspaces:
            new_action = QAction(tr("new_workspace"), self)
            new_action.triggered.connect(lambda: self._create_new_workspace_and_add(query_id))
            menu.addAction(new_action)
            return menu

        # Get workspaces that contain this query
        query_workspaces = config_db.get_query_workspaces(query_id)
        workspace_ids_with_query = {ws.id for ws in query_workspaces}

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

        new_action = QAction(tr("new_workspace") + "...", self)
        new_action.triggered.connect(lambda: self._create_new_workspace_and_add(query_id))
        menu.addAction(new_action)

        return menu

    def _toggle_workspace(self, workspace_id: str, query_id: str, is_in_workspace: bool):
        """Toggle a query in/out of a workspace."""
        config_db = get_config_db()
        if is_in_workspace:
            config_db.remove_query_from_workspace(workspace_id, query_id)
        else:
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
