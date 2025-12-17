"""
Scripts Manager - Manager for Python scripts
Provides interface to view, edit, and execute Python scripts
"""

from typing import List, Optional, Any
from PySide6.QtWidgets import QTextEdit, QWidget, QSplitter
from PySide6.QtCore import Qt

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.log_panel import LogPanel
from ..widgets.dialog_helper import DialogHelper
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db


class ScriptsManager(BaseManagerView):
    """Manager for Python scripts."""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize scripts manager.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent, title="Scripts Manager")
        self._setup_toolbar()
        self._setup_details()
        self._setup_content()
        self.refresh()

    def _get_tree_columns(self) -> List[str]:
        """
        Return column names for tree view.

        Returns:
            List of column names
        """
        return [tr("col_name"), tr("col_type"), tr("col_description")]

    def get_tree_widget(self):
        """Return the tree widget for embedding in ResourcesManager."""
        return self.tree_view.tree

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
        self._replace_toolbar(toolbar_builder)

    def _setup_details(self):
        """Setup details panel with script information."""
        self.details_form = FormBuilder(title=tr("script_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("field_description"), "description") \
            .add_field(tr("field_type"), "script_type") \
            .add_field(tr("field_created"), "created") \
            .add_field(tr("field_modified"), "modified") \
            .build()

        self.details_layout.addWidget(self.details_form)

    def _setup_content(self):
        """Setup content panel with code editor and log panel."""
        # Create vertical splitter for code editor (top) and log panel (bottom)
        content_splitter = QSplitter(Qt.Orientation.Vertical)

        # Code editor (read-only for now)
        self.code_editor = QTextEdit()
        self.code_editor.setReadOnly(True)
        self.code_editor.setPlaceholderText(tr("code_placeholder"))
        UIHelper.apply_monospace_font(self.code_editor)

        # TODO: Apply Python syntax highlighting when available
        content_splitter.addWidget(self.code_editor)

        # Log panel with filters
        self.log_panel = LogPanel(with_filters=True)
        content_splitter.addWidget(self.log_panel)

        # Set proportions (60% code, 40% logs)
        content_splitter.setSizes([600, 400])

        self.content_layout.addWidget(content_splitter)

    def _load_items(self):
        """Load scripts from database into tree view."""
        try:
            config_db = get_config_db()
            scripts = config_db.get_all_scripts()

            for script in scripts:
                self.tree_view.add_item(
                    parent=None,
                    text=[script.name, script.script_type, script.description],
                    data=script
                )
        except Exception as e:
            DialogHelper.error(
                tr("error_loading_scripts"),
                tr("error_title"),
                self,
                details=str(e)
            )

    def _display_item(self, item_data: Any):
        """
        Display selected script details and code.

        Args:
            item_data: Script data object (dict or database model)
        """
        wrapper = self._wrap_item(item_data)

        # Update details form
        self.details_form.set_value("name", wrapper.get_str("name"))
        self.details_form.set_value("description", wrapper.get_str("description"))
        self.details_form.set_value("script_type", wrapper.get_str("script_type"))
        self.details_form.set_value("created", wrapper.get_str("created_at", wrapper.get_str("created")))
        self.details_form.set_value("modified", wrapper.get_str("modified_at", wrapper.get_str("modified")))

        # Update code editor
        self.code_editor.setPlainText(wrapper.get_str("script_content"))

        # Clear log panel
        self.log_panel.clear()

    def _add_script(self):
        """Add a new script."""
        # TODO: Open dialog to create new script
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("add_script_title"),
            self
        )

    def _edit_script(self):
        """Edit selected script."""
        if not self._check_item_selected(tr("select_script_first"), tr("edit_script_title")):
            return

        # TODO: Open dialog to edit script
        DialogHelper.info(tr("feature_coming_soon"), tr("edit_script_title"), self)

    def _delete_script(self):
        """Delete selected script."""
        if not self._check_item_selected(tr("select_script_first"), tr("delete_script_title")):
            return

        script_name = self._get_item_name()

        if DialogHelper.confirm(
            tr("confirm_delete_script").format(name=script_name),
            tr("delete_script_title"),
            self
        ):
            # TODO: Delete from database
            # config_db.delete_script(self._current_item.id)
            # self.refresh()
            DialogHelper.info(tr("script_deleted"), tr("delete_script_title"), self)

    def _run_script(self):
        """Run selected script."""
        if not self._check_item_selected(tr("select_script_first"), tr("run_script_title")):
            return

        # TODO: Execute script in separate thread and capture output
        self.log_panel.clear()
        self.log_panel.add_message(tr("script_execution_started"), "INFO")
        DialogHelper.info(tr("feature_coming_soon"), tr("run_script_title"), self)
