"""
Jobs Manager - Manager for scheduled jobs with hierarchical TreeView
Provides interface to view, edit, and manage automated jobs organized by type
"""

from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QVBoxLayout, QTextEdit, QLabel, QMenu, QTreeWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from .base import HierarchicalManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.log_panel import LogPanel
from ..widgets.dialog_helper import DialogHelper
from ..widgets.workspace_menu_builder import build_workspace_menu
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Job
from ...utils.image_loader import get_icon
from ..dialogs.job_dialog import JobDialog

import logging
logger = logging.getLogger(__name__)


class JobsManager(HierarchicalManagerView):
    """
    Manager for scheduled jobs with hierarchical TreeView.

    Layout:
    - TOP: Toolbar
    - LEFT: TreeView (Type > Job)
    - RIGHT: Details panel + Config editor + Log panel
    """

    # Type labels for display
    TYPE_LABELS = {
        "script": "Scripts",
        "workflow": "Workflows"
    }

    def __init__(self, parent=None):
        super().__init__(parent)

    # ==================== Abstract Method Implementations ====================

    def _get_explorer_title(self) -> str:
        return tr("jobs_explorer")

    def _get_explorer_icon(self) -> str:
        return "jobs.png"

    def _get_item_type(self) -> str:
        return "job"

    def _get_category_field(self) -> str:
        return "job_type"

    def _setup_toolbar_buttons(self, builder: ToolbarBuilder):
        """Add job-specific toolbar buttons."""
        builder.add_button(tr("btn_add"), self._add_job, icon="add.png")
        builder.add_button(tr("btn_edit"), self._edit_job, icon="edit.png")
        builder.add_button(tr("btn_delete"), self._delete_job, icon="delete.png")
        builder.add_separator()
        builder.add_button(tr("btn_run_now"), self._run_job, icon="play.png")
        builder.add_button(tr("btn_enable"), self._toggle_job, icon="toggle.png")

    def _setup_detail_fields(self, form_builder: FormBuilder):
        """Add job detail fields."""
        form_builder.add_field(tr("field_name"), "name")
        form_builder.add_field(tr("field_type"), "job_type")
        form_builder.add_field(tr("field_description"), "description")
        form_builder.add_field(tr("field_status"), "status")
        form_builder.add_field(tr("field_script"), "script")
        form_builder.add_field(tr("field_last_run"), "last_run")
        form_builder.add_field(tr("field_created"), "created")

    def _setup_content_widgets(self, layout: QVBoxLayout):
        """Add config editor and log panel to content panel."""
        # Configuration text area
        config_label = QLabel(tr("job_config"))
        config_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(config_label)

        self.config_editor = QTextEdit()
        self.config_editor.setReadOnly(True)
        self.config_editor.setPlaceholderText(tr("job_config_placeholder"))
        self.config_editor.setMaximumHeight(100)
        UIHelper.apply_monospace_font(self.config_editor)
        layout.addWidget(self.config_editor)

        # Log panel
        self.log_panel = LogPanel(with_filters=True)
        layout.addWidget(self.log_panel, stretch=1)

    def _load_items(self) -> List[Job]:
        """Load jobs from database, filtered by workspace if set."""
        config_db = get_config_db()

        # Apply workspace filter if set
        if self._workspace_filter:
            return config_db.get_workspace_jobs(self._workspace_filter)
        else:
            return config_db.get_all_jobs()

    def _get_item_category(self, item: Job) -> str:
        job_type = item.job_type or "script"
        # Return display label for category
        return self.TYPE_LABELS.get(job_type, job_type)

    def _get_item_name(self, item: Job) -> str:
        # Include status icon in name
        status_icon = "✓" if item.enabled else "✗"
        return f"{status_icon} {item.name}"

    def _display_item(self, job: Job):
        """Display job details."""
        if not job:
            self._clear_item_display()
            return

        status = tr("status_enabled") if job.enabled else tr("status_disabled")

        self.details_form.set_value("name", job.name)
        self.details_form.set_value("job_type", job.job_type or "")
        self.details_form.set_value("description", job.description or "")
        self.details_form.set_value("status", status)
        self.details_form.set_value("script", job.script_id or "")
        self.details_form.set_value("last_run", job.last_run_at or "")
        self.details_form.set_value("created", job.created_at or "")

        # Update config editor
        self.config_editor.setPlainText(job.parameters or "")

        # Clear log
        self.log_panel.clear()

    def _clear_item_display(self):
        """Clear all details fields."""
        self.details_form.set_value("name", "")
        self.details_form.set_value("job_type", "")
        self.details_form.set_value("description", "")
        self.details_form.set_value("status", "")
        self.details_form.set_value("script", "")
        self.details_form.set_value("last_run", "")
        self.details_form.set_value("created", "")
        self.config_editor.clear()
        self.log_panel.clear()

    def _on_item_action(self, item: Job):
        """Run job on double-click."""
        self._run_job()

    # ==================== Context Menu ====================

    def _build_category_context_menu(self, menu: QMenu, category_name: str):
        """Build context menu for job type folder."""
        add_action = QAction(tr("btn_add_job"), self)
        add_action.triggered.connect(self._add_job)
        menu.addAction(add_action)

    def _build_item_context_menu(self, menu: QMenu, job: Job):
        """Build context menu for a job."""
        # Run action
        run_action = QAction(tr("btn_run_now"), self)
        run_action.triggered.connect(self._run_job)
        menu.addAction(run_action)

        # Toggle action
        toggle_text = tr("btn_disable") if job.enabled else tr("btn_enable")
        toggle_action = QAction(toggle_text, self)
        toggle_action.triggered.connect(self._toggle_job)
        menu.addAction(toggle_action)

        menu.addSeparator()

        # Edit action
        edit_action = QAction(tr("btn_edit"), self)
        edit_action.triggered.connect(self._edit_job)
        menu.addAction(edit_action)

        # Delete action
        delete_action = QAction(tr("btn_delete"), self)
        delete_action.triggered.connect(self._delete_job)
        menu.addAction(delete_action)

        menu.addSeparator()

        # Workspaces submenu
        workspace_menu = self._build_workspace_submenu(job.id)
        if workspace_menu:
            menu.addMenu(workspace_menu)

    def _build_workspace_submenu(self, job_id: str) -> QMenu:
        """Build a submenu for adding/removing a job to/from workspaces."""
        config_db = get_config_db()
        return build_workspace_menu(
            parent=self,
            item_id=job_id,
            get_item_workspaces=lambda: config_db.get_job_workspaces(job_id),
            add_to_workspace=lambda ws_id: config_db.add_job_to_workspace(ws_id, job_id),
            remove_from_workspace=lambda ws_id: config_db.remove_job_from_workspace(ws_id, job_id),
        )

    # ==================== Actions ====================

    def _add_job(self):
        """Add a new job."""
        dialog = JobDialog(self)
        if dialog.exec() == JobDialog.DialogCode.Accepted:
            self.refresh()
            DialogHelper.info(tr("job_added"), tr("add_job_title"), self)

    def _edit_job(self):
        """Edit selected job."""
        if not self._current_item:
            DialogHelper.warning(tr("select_job_first"), tr("edit_job_title"), self)
            return

        dialog = JobDialog(self, job=self._current_item)
        if dialog.exec() == JobDialog.DialogCode.Accepted:
            self.refresh()
            DialogHelper.info(tr("job_updated"), tr("edit_job_title"), self)

    def _delete_job(self):
        """Delete selected job."""
        if not self._current_item:
            DialogHelper.warning(tr("select_job_first"), tr("delete_job_title"), self)
            return

        job_name = self._current_item.name

        if DialogHelper.confirm(
            tr("confirm_delete_job").format(name=job_name),
            tr("delete_job_title"),
            self
        ):
            try:
                config_db = get_config_db()
                config_db.delete_job(self._current_item.id)
                self.refresh()
                DialogHelper.info(tr("job_deleted"), tr("delete_job_title"), self)
            except Exception as e:
                DialogHelper.error(str(e), tr("error"), self)

    def _run_job(self):
        """Run selected job immediately."""
        if not self._current_item:
            DialogHelper.warning(tr("select_job_first"), tr("run_job_title"), self)
            return

        self.log_panel.clear()
        self.log_panel.add_message(tr("job_execution_started"), "INFO")
        DialogHelper.info(tr("feature_coming_soon"), tr("run_job_title"), self)

    def _toggle_job(self):
        """Toggle job enabled/disabled status."""
        if not self._current_item:
            DialogHelper.warning(tr("select_job_first"), tr("toggle_job_title"), self)
            return

        new_enabled = not self._current_item.enabled
        new_status = tr("status_enabled") if new_enabled else tr("status_disabled")

        try:
            config_db = get_config_db()
            self._current_item.enabled = new_enabled
            config_db.update_job(self._current_item)
            self.refresh()
            DialogHelper.info(
                tr("job_status_changed").format(status=new_status),
                tr("toggle_job_title"),
                self
            )
        except Exception as e:
            DialogHelper.error(str(e), tr("error"), self)
