"""
Scripts Manager - Manager for Python scripts with hierarchical TreeView
Provides interface to view, edit, and execute Python scripts organized by type
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
from ..widgets.log_panel import LogPanel
from ..widgets.dialog_helper import DialogHelper
from ..widgets.pinnable_panel import PinnablePanel
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Script
from ...utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


class ScriptsManager(QWidget):
    """
    Manager for Python scripts with hierarchical TreeView.

    Layout:
    - TOP: Toolbar
    - LEFT: TreeView (Type > Script)
    - RIGHT: Details panel + Code editor + Log panel
    """

    # Signal emitted when item is selected
    item_selected = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._current_item = None
        self._type_items: Dict[str, QTreeWidgetItem] = {}

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
            title=tr("scripts_explorer"),
            icon_name="scripts.png"
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

        # Right panel: Details + Code + Log
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Details panel
        self.details_panel = QWidget()
        self.details_layout = QVBoxLayout(self.details_panel)
        self.details_layout.setContentsMargins(5, 5, 5, 5)
        self._setup_details()
        right_splitter.addWidget(self.details_panel)

        # Content panel (code editor + log)
        self.content_panel = QWidget()
        self.content_layout = QVBoxLayout(self.content_panel)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self._setup_content()
        right_splitter.addWidget(self.content_panel)

        right_splitter.setSizes([120, 480])
        self.main_splitter.addWidget(right_splitter)

        self.main_splitter.setSizes([250, 750])
        layout.addWidget(self.main_splitter)

    def _setup_toolbar(self):
        """Setup toolbar with script management buttons."""
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_refresh"), self.refresh, icon="refresh.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_add"), self._add_script, icon="add.png")
        toolbar_builder.add_button(tr("btn_edit"), self._edit_script, icon="edit.png")
        toolbar_builder.add_button(tr("btn_delete"), self._delete_script, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_run"), self._run_script, icon="play.png")
        self.toolbar = toolbar_builder.build()

    def _setup_details(self):
        """Setup details panel with script information."""
        self.details_form = FormBuilder(title=tr("script_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("field_type"), "script_type") \
            .add_field(tr("field_description"), "description") \
            .add_field(tr("field_created"), "created") \
            .add_field(tr("field_modified"), "modified")

        self.details_layout.addWidget(self.details_form.container)

    def _setup_content(self):
        """Setup content panel with code editor and log panel."""
        # Code editor
        code_label = QLabel(tr("script_code"))
        code_label.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(code_label)

        # Create splitter for code and log
        content_splitter = QSplitter(Qt.Orientation.Vertical)

        self.code_editor = QTextEdit()
        self.code_editor.setReadOnly(True)
        self.code_editor.setPlaceholderText(tr("code_placeholder"))
        UIHelper.apply_monospace_font(self.code_editor)
        content_splitter.addWidget(self.code_editor)

        # Log panel
        self.log_panel = LogPanel(with_filters=True)
        content_splitter.addWidget(self.log_panel)

        content_splitter.setSizes([400, 200])
        self.content_layout.addWidget(content_splitter)

    def get_tree_widget(self):
        """Return the tree widget for embedding."""
        return self.tree

    def refresh(self):
        """Reload all scripts from database."""
        self.tree.clear()
        self._type_items.clear()
        self._current_item = None
        self._clear_details()
        self._load_scripts()

    def _load_scripts(self):
        """Load scripts from database into hierarchical tree."""
        try:
            config_db = get_config_db()
            scripts = config_db.get_all_scripts()

            # Group scripts by type
            script_types: Dict[str, List[Script]] = {}

            for script in scripts:
                script_type = script.script_type or "other"
                if script_type not in script_types:
                    script_types[script_type] = []
                script_types[script_type].append(script)

            # Create tree structure
            folder_icon = get_icon("Category", size=16)
            script_icon = get_icon("scripts", size=16)

            for script_type in sorted(script_types.keys()):
                scripts_list = script_types[script_type]

                # Create type folder
                type_item = QTreeWidgetItem(self.tree)
                type_item.setText(0, f"{script_type} ({len(scripts_list)})")
                if folder_icon:
                    type_item.setIcon(0, folder_icon)
                type_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "script_type",
                    "script_type": script_type
                })
                type_item.setExpanded(True)
                self._type_items[script_type] = type_item

                # Add scripts under type
                for script in sorted(scripts_list, key=lambda s: s.name):
                    script_item = QTreeWidgetItem(type_item)
                    script_item.setText(0, script.name)
                    if script_icon:
                        script_item.setIcon(0, script_icon)
                    script_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "script",
                        "script": script
                    })

        except Exception as e:
            logger.error(f"Error loading scripts: {e}")

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle single click on tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "script":
            self._current_item = data.get("script")
            self._display_script(self._current_item)
            self.item_selected.emit(self._current_item)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "script":
            self._current_item = data.get("script")
            self._run_script()

    def _display_script(self, script: Script):
        """Display script details and code."""
        if not script:
            self._clear_details()
            return

        self.details_form.set_value("name", script.name)
        self.details_form.set_value("script_type", script.script_type or "")
        self.details_form.set_value("description", script.description or "")
        self.details_form.set_value("created", script.created_at or "")
        self.details_form.set_value("modified", script.updated_at or "")

        # Update code editor (parameters_schema contains the code or schema)
        self.code_editor.setPlainText(script.parameters_schema or "")

        # Clear log
        self.log_panel.clear()

    def _clear_details(self):
        """Clear all details fields."""
        self.details_form.set_value("name", "")
        self.details_form.set_value("script_type", "")
        self.details_form.set_value("description", "")
        self.details_form.set_value("created", "")
        self.details_form.set_value("modified", "")
        self.code_editor.clear()
        self.log_panel.clear()

    # ===== Actions =====

    def _add_script(self):
        """Add a new script."""
        DialogHelper.info(tr("feature_coming_soon"), tr("add_script_title"), self)

    def _edit_script(self):
        """Edit selected script."""
        if not self._current_item:
            DialogHelper.warning(tr("select_script_first"), tr("edit_script_title"), self)
            return
        DialogHelper.info(tr("feature_coming_soon"), tr("edit_script_title"), self)

    def _delete_script(self):
        """Delete selected script."""
        if not self._current_item:
            DialogHelper.warning(tr("select_script_first"), tr("delete_script_title"), self)
            return

        script_name = self._current_item.name

        if DialogHelper.confirm(
            tr("confirm_delete_script").format(name=script_name),
            tr("delete_script_title"),
            self
        ):
            try:
                config_db = get_config_db()
                config_db.delete_script(self._current_item.id)
                self.refresh()
                DialogHelper.info(tr("script_deleted"), tr("delete_script_title"), self)
            except Exception as e:
                DialogHelper.error(str(e), tr("error"), self)

    def _run_script(self):
        """Run selected script."""
        if not self._current_item:
            DialogHelper.warning(tr("select_script_first"), tr("run_script_title"), self)
            return

        self.log_panel.clear()
        self.log_panel.add_message(tr("script_execution_started"), "INFO")
        DialogHelper.info(tr("feature_coming_soon"), tr("run_script_title"), self)

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

        if data.get("type") == "script_type":
            # Context menu for script type folder
            add_action = QAction(tr("btn_add_script"), self)
            add_action.triggered.connect(self._add_script)
            menu.addAction(add_action)

        elif data.get("type") == "script":
            script = data.get("script")
            script_id = script.id if script else None

            if script_id:
                # Run action
                run_action = QAction(tr("btn_run"), self)
                run_action.triggered.connect(self._run_script)
                menu.addAction(run_action)

                menu.addSeparator()

                # Edit action
                edit_action = QAction(tr("btn_edit"), self)
                edit_action.triggered.connect(self._edit_script)
                menu.addAction(edit_action)

                # Delete action
                delete_action = QAction(tr("btn_delete"), self)
                delete_action.triggered.connect(self._delete_script)
                menu.addAction(delete_action)

        if menu.actions():
            menu.exec(self.tree.viewport().mapToGlobal(position))
