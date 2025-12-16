"""
Jobs Manager - Manager for scheduled jobs and tasks
Provides interface to view, edit, and manage automated jobs
"""

from typing import List, Optional, Any
import uuid
from PySide6.QtWidgets import QTextEdit, QWidget, QMenu, QInputDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.log_panel import LogPanel
from ..widgets.dialog_helper import DialogHelper
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db


class JobsManager(BaseManagerView):
    """Manager for scheduled jobs and automated tasks."""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize jobs manager.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent, title="Jobs Manager")
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
        return [tr("col_name"), tr("col_status"), tr("col_schedule")]

    def get_tree_widget(self):
        """Return the tree widget for embedding in ResourcesManager."""
        return self.tree_view.tree

    def _setup_toolbar(self):
        """Setup toolbar with job management buttons."""
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_refresh"), self.refresh, icon="refresh.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_add"), self._add_job, icon="add.png")
        toolbar_builder.add_button(tr("btn_edit"), self._edit_job, icon="edit.png")
        toolbar_builder.add_button(tr("btn_delete"), self._delete_job, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_run_now"), self._run_job, icon="play.png")
        toolbar_builder.add_button(tr("btn_enable"), self._toggle_job, icon="toggle.png")
        self._replace_toolbar(toolbar_builder)

    def _setup_details(self):
        """Setup details panel with job information."""
        self.details_form = FormBuilder(title=tr("job_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("field_description"), "description") \
            .add_field(tr("field_status"), "status") \
            .add_field(tr("field_schedule"), "schedule") \
            .add_field(tr("field_last_run"), "last_run") \
            .add_field(tr("field_next_run"), "next_run") \
            .add_field(tr("field_script"), "script") \
            .add_field(tr("field_created"), "created") \
            .build()

        self.details_layout.addWidget(self.details_form)

    def _setup_content(self):
        """Setup content panel with job configuration and log panel."""
        # Configuration text area (read-only for now)
        self.config_editor = QTextEdit()
        self.config_editor.setReadOnly(True)
        self.config_editor.setPlaceholderText(tr("job_config_placeholder"))
        UIHelper.apply_monospace_font(self.config_editor)
        self.content_layout.addWidget(self.config_editor, stretch=2)

        # Log panel with filters
        self.log_panel = LogPanel(with_filters=True)
        self.content_layout.addWidget(self.log_panel, stretch=3)

    def _load_items(self):
        """Load jobs from database into tree view."""
        try:
            config_db = get_config_db()
            jobs = config_db.get_all_jobs()

            for job in jobs:
                status = "Enabled" if job.enabled else "Disabled"
                self.tree_view.add_item(
                    parent=None,
                    text=[job.name, status, job.schedule],
                    data=job
                )
        except Exception as e:
            DialogHelper.error(
                tr("error_loading_jobs"),
                tr("error_title"),
                self,
                details=str(e)
            )

    def _display_item(self, item_data: Any):
        """
        Display selected job details and configuration.

        Args:
            item_data: Job data object (dict or database model)
        """
        wrapper = self._wrap_item(item_data)

        # Get status - handle enabled boolean for model objects
        if wrapper.is_dict:
            status = wrapper.get_str("status")
        else:
            status = wrapper.get_status_str("enabled")

        # Update details form
        self.details_form.set_value("name", wrapper.get_str("name"))
        self.details_form.set_value("description", wrapper.get_str("description"))
        self.details_form.set_value("status", status)
        self.details_form.set_value("schedule", wrapper.get_str("schedule"))
        self.details_form.set_value("last_run", wrapper.get_str("last_run"))
        self.details_form.set_value("next_run", wrapper.get_str("next_run"))
        self.details_form.set_value("script", wrapper.get_str("script_name", wrapper.get_str("script")))
        self.details_form.set_value("created", wrapper.get_str("created_at", wrapper.get_str("created")))

        # Update configuration editor
        config = wrapper.get_str("config_json", wrapper.get_str("config"))
        self.config_editor.setPlainText(config)

        # Clear log panel
        self.log_panel.clear()

    def _add_job(self):
        """Add a new job."""
        # TODO: Open dialog to create new job
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("add_job_title"),
            self
        )

    def _edit_job(self):
        """Edit selected job."""
        if not self._check_item_selected(tr("select_job_first"), tr("edit_job_title")):
            return

        # TODO: Open dialog to edit job
        DialogHelper.info(tr("feature_coming_soon"), tr("edit_job_title"), self)

    def _delete_job(self):
        """Delete selected job."""
        if not self._check_item_selected(tr("select_job_first"), tr("delete_job_title")):
            return

        job_name = self._get_item_name()

        if DialogHelper.confirm(
            tr("confirm_delete_job").format(name=job_name),
            tr("delete_job_title"),
            self
        ):
            # TODO: Delete from database
            # config_db.delete_job(self._current_item.id)
            # self.refresh()
            DialogHelper.info(tr("job_deleted"), tr("delete_job_title"), self)

    def _run_job(self):
        """Run selected job immediately."""
        if not self._check_item_selected(tr("select_job_first"), tr("run_job_title")):
            return

        # TODO: Execute job immediately (bypass schedule)
        self.log_panel.clear()
        self.log_panel.add_message(tr("job_execution_started"), "INFO")
        DialogHelper.info(tr("feature_coming_soon"), tr("run_job_title"), self)

    def _toggle_job(self):
        """Toggle job enabled/disabled status."""
        if not self._check_item_selected(tr("select_job_first"), tr("toggle_job_title")):
            return

        wrapper = self._wrap_item()
        if wrapper.is_dict:
            current_status = wrapper.get_str("status")
        else:
            current_status = wrapper.get_status_str("enabled")

        new_status = "Disabled" if current_status == "Enabled" else "Enabled"

        # TODO: Update database
        # config_db.update_job_status(self._current_item.id, new_status == "Enabled")
        # self.refresh()

        DialogHelper.info(tr("job_status_changed").format(status=new_status), tr("toggle_job_title"), self)

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

        # Get job ID
        job_id = getattr(data, 'id', None) or (data.get('id') if isinstance(data, dict) else None)
        if not job_id:
            return

        menu = QMenu(self)

        # Add "Workspaces" submenu
        workspace_menu = self._build_workspace_submenu(job_id)
        if workspace_menu:
            menu.addMenu(workspace_menu)

        if menu.actions():
            menu.exec(self.tree_view.tree.viewport().mapToGlobal(position))

    def _build_workspace_submenu(self, job_id: str) -> QMenu:
        """Build a submenu for adding/removing a job to/from workspaces."""
        config_db = get_config_db()
        workspaces = config_db.get_all_workspaces()

        menu = QMenu(tr("menu_workspaces"), self)
        menu.setIcon(self._get_workspace_icon())

        if not workspaces:
            # No workspaces - show option to create one
            new_action = QAction(tr("new_workspace"), self)
            new_action.triggered.connect(lambda: self._create_new_workspace_and_add(job_id))
            menu.addAction(new_action)
            return menu

        # Get workspaces that contain this job
        job_workspaces = config_db.get_job_workspaces(job_id)
        workspace_ids_with_job = {ws.id for ws in job_workspaces}

        # Add each workspace with checkmark if job is in it
        for ws in workspaces:
            is_in_workspace = ws.id in workspace_ids_with_job
            action = QAction(ws.name, self)
            action.setCheckable(True)
            action.setChecked(is_in_workspace)
            action.triggered.connect(
                lambda checked, wid=ws.id, in_ws=is_in_workspace:
                self._toggle_workspace(wid, job_id, in_ws)
            )
            menu.addAction(action)

        menu.addSeparator()

        # Add "New Workspace..." option
        new_action = QAction(tr("new_workspace") + "...", self)
        new_action.triggered.connect(lambda: self._create_new_workspace_and_add(job_id))
        menu.addAction(new_action)

        return menu

    def _get_workspace_icon(self):
        """Get workspace icon."""
        from ...utils.image_loader import get_icon
        return get_icon("workspace.png", size=16) or get_icon("folder.png", size=16)

    def _toggle_workspace(self, workspace_id: str, job_id: str, is_in_workspace: bool):
        """Toggle a job in/out of a workspace."""
        config_db = get_config_db()

        if is_in_workspace:
            # Remove from workspace
            config_db.remove_job_from_workspace(workspace_id, job_id)
        else:
            # Add to workspace
            config_db.add_job_to_workspace(workspace_id, job_id)

    def _create_new_workspace_and_add(self, job_id: str):
        """Create a new workspace and add the job to it."""
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
                config_db.add_job_to_workspace(ws.id, job_id)
            else:
                DialogHelper.warning(tr("workspace_create_failed"), tr("error"), self)
