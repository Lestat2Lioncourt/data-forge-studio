"""
Scripts Manager - Manager for Python scripts with hierarchical TreeView
Provides interface to view, edit, and execute Python scripts organized by type
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QTextEdit, QLabel, QMenu, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from .base import HierarchicalManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.log_panel import LogPanel
from ..widgets.dialog_helper import DialogHelper
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Script

import logging
logger = logging.getLogger(__name__)


class ScriptsManager(HierarchicalManagerView):
    """
    Manager for Python scripts with hierarchical TreeView.

    Layout:
    - TOP: Toolbar
    - LEFT: TreeView (Type > Script)
    - RIGHT: Details panel + Code editor + Log panel
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    # ==================== Abstract Method Implementations ====================

    def _get_explorer_title(self) -> str:
        return tr("scripts_explorer")

    def _get_explorer_icon(self) -> str:
        return "scripts.png"

    def _get_item_type(self) -> str:
        return "script"

    def _get_category_field(self) -> str:
        return "script_type"

    def _setup_toolbar_buttons(self, builder: ToolbarBuilder):
        """Add script-specific toolbar buttons."""
        builder.add_button(tr("btn_add"), self._add_script, icon="add.png")
        builder.add_button(tr("btn_edit"), self._edit_script, icon="edit.png")
        builder.add_button(tr("btn_delete"), self._delete_script, icon="delete.png")
        builder.add_separator()
        builder.add_button(tr("btn_run"), self._run_script, icon="play.png")

    def _setup_detail_fields(self, form_builder: FormBuilder):
        """Add script detail fields."""
        form_builder.add_field(tr("field_name"), "name")
        form_builder.add_field(tr("field_type"), "script_type")
        form_builder.add_field(tr("field_description"), "description")
        form_builder.add_field(tr("field_created"), "created")
        form_builder.add_field(tr("field_modified"), "modified")

    def _setup_content_widgets(self, layout: QVBoxLayout):
        """Add code editor and log panel to content panel."""
        # Code editor
        code_label = QLabel(tr("script_code"))
        code_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(code_label)

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
        layout.addWidget(content_splitter)

    def _load_items(self) -> List[Script]:
        """Load scripts from database."""
        config_db = get_config_db()
        return config_db.get_all_scripts()

    def _get_item_category(self, item: Script) -> str:
        return item.script_type or "other"

    def _get_item_name(self, item: Script) -> str:
        return item.name

    def _display_item(self, script: Script):
        """Display script details and code."""
        if not script:
            self._clear_item_display()
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

    def _clear_item_display(self):
        """Clear all details fields."""
        self.details_form.set_value("name", "")
        self.details_form.set_value("script_type", "")
        self.details_form.set_value("description", "")
        self.details_form.set_value("created", "")
        self.details_form.set_value("modified", "")
        self.code_editor.clear()
        self.log_panel.clear()

    def _on_item_action(self, item: Script):
        """Run script on double-click."""
        self._run_script()

    # ==================== Context Menu ====================

    def _build_category_context_menu(self, menu: QMenu, category_name: str):
        """Build context menu for script type folder."""
        add_action = QAction(tr("btn_add_script"), self)
        add_action.triggered.connect(self._add_script)
        menu.addAction(add_action)

    def _build_item_context_menu(self, menu: QMenu, script: Script):
        """Build context menu for a script."""
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

    # ==================== Actions ====================

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
