"""
Jobs Manager - Manager for scheduled jobs and tasks
Provides interface to view, edit, and manage automated jobs
"""

from typing import List, Optional, Any
from PySide6.QtWidgets import QTextEdit, QWidget
from PySide6.QtCore import Qt

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.log_panel import LogPanel
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr


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
        # Refresh will be called when connected to database

    def _get_tree_columns(self) -> List[str]:
        """
        Return column names for tree view.

        Returns:
            List of column names
        """
        return [tr("col_name"), tr("col_status"), tr("col_schedule")]

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

        # Replace default toolbar
        old_toolbar = self.toolbar
        self.toolbar = toolbar_builder.build()
        self.layout().replaceWidget(old_toolbar, self.toolbar)
        old_toolbar.setParent(None)

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

        # Set monospace font
        from PySide6.QtGui import QFont
        config_font = QFont("Consolas", 10)
        config_font.setStyleHint(QFont.StyleHint.Monospace)
        self.config_editor.setFont(config_font)

        self.content_layout.addWidget(self.config_editor, stretch=2)

        # Log panel with filters
        self.log_panel = LogPanel(with_filters=True)
        self.content_layout.addWidget(self.log_panel, stretch=3)

    def _load_items(self):
        """Load jobs from database into tree view."""
        # TODO: Integrate with database layer when available
        # For now, create placeholder data

        # Placeholder jobs
        placeholder_jobs = [
            {
                "name": "Daily Data Import",
                "description": "Import data from external sources daily",
                "status": "Enabled",
                "schedule": "Daily at 02:00",
                "last_run": "2025-12-10 02:00:00",
                "next_run": "2025-12-11 02:00:00",
                "script": "Data Import Script",
                "created": "2025-11-01",
                "config": "{\n  \"source\": \"external_api\",\n  \"destination\": \"database\",\n  \"schedule\": \"0 2 * * *\"\n}"
            },
            {
                "name": "Weekly Report Generation",
                "description": "Generate weekly summary reports",
                "status": "Enabled",
                "schedule": "Weekly on Monday at 08:00",
                "last_run": "2025-12-09 08:00:00",
                "next_run": "2025-12-16 08:00:00",
                "script": "Report Generator",
                "created": "2025-11-15",
                "config": "{\n  \"report_type\": \"summary\",\n  \"recipients\": [\"admin@example.com\"],\n  \"schedule\": \"0 8 * * 1\"\n}"
            },
            {
                "name": "Data Cleanup",
                "description": "Clean up old data monthly",
                "status": "Disabled",
                "schedule": "Monthly on 1st at 00:00",
                "last_run": "2025-11-01 00:00:00",
                "next_run": "Not scheduled (disabled)",
                "script": "Cleanup Script",
                "created": "2025-10-01",
                "config": "{\n  \"retention_days\": 90,\n  \"schedule\": \"0 0 1 * *\"\n}"
            }
        ]

        for job in placeholder_jobs:
            self.tree_view.add_item(
                parent=None,
                text=[job["name"], job["status"], job["schedule"]],
                data=job
            )

        # Real implementation will be:
        # try:
        #     from ...database.config_db import get_config_db
        #     config_db = get_config_db()
        #     jobs = config_db.get_all_jobs()
        #
        #     for job in jobs:
        #         status = "Enabled" if job.enabled else "Disabled"
        #         self.tree_view.add_item(
        #             parent=None,
        #             text=[job.name, status, job.schedule],
        #             data=job
        #         )
        # except Exception as e:
        #     DialogHelper.error(
        #         tr("error_loading_jobs"),
        #         tr("error_title"),
        #         self,
        #         details=str(e)
        #     )

    def _display_item(self, item_data: Any):
        """
        Display selected job details and configuration.

        Args:
            item_data: Job data object (dict or database model)
        """
        # Handle both dict (placeholder) and database model
        if isinstance(item_data, dict):
            name = item_data.get("name", "")
            description = item_data.get("description", "")
            status = item_data.get("status", "")
            schedule = item_data.get("schedule", "")
            last_run = item_data.get("last_run", "")
            next_run = item_data.get("next_run", "")
            script = item_data.get("script", "")
            created = item_data.get("created", "")
            config = item_data.get("config", "")
        else:
            # Assume it's a database model with attributes
            name = getattr(item_data, "name", "")
            description = getattr(item_data, "description", "")
            status = "Enabled" if getattr(item_data, "enabled", False) else "Disabled"
            schedule = getattr(item_data, "schedule", "")
            last_run = str(getattr(item_data, "last_run", ""))
            next_run = str(getattr(item_data, "next_run", ""))
            script = getattr(item_data, "script_name", "")
            created = str(getattr(item_data, "created_at", ""))
            config = getattr(item_data, "config_json", "")

        # Update details form
        self.details_form.set_value("name", name)
        self.details_form.set_value("description", description)
        self.details_form.set_value("status", status)
        self.details_form.set_value("schedule", schedule)
        self.details_form.set_value("last_run", last_run)
        self.details_form.set_value("next_run", next_run)
        self.details_form.set_value("script", script)
        self.details_form.set_value("created", created)

        # Update configuration editor
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
        if not self._current_item:
            DialogHelper.warning(
                tr("select_job_first"),
                tr("edit_job_title"),
                self
            )
            return

        # TODO: Open dialog to edit job
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("edit_job_title"),
            self
        )

    def _delete_job(self):
        """Delete selected job."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_job_first"),
                tr("delete_job_title"),
                self
            )
            return

        # Get job name
        if isinstance(self._current_item, dict):
            job_name = self._current_item.get("name", "")
        else:
            job_name = getattr(self._current_item, "name", "")

        # Confirm deletion
        if DialogHelper.confirm(
            tr("confirm_delete_job").format(name=job_name),
            tr("delete_job_title"),
            self
        ):
            # TODO: Delete from database
            # config_db.delete_job(self._current_item.id)
            # self.refresh()
            DialogHelper.info(
                tr("job_deleted"),
                tr("delete_job_title"),
                self
            )

    def _run_job(self):
        """Run selected job immediately."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_job_first"),
                tr("run_job_title"),
                self
            )
            return

        # TODO: Execute job immediately (bypass schedule)
        self.log_panel.clear()
        self.log_panel.add_message(tr("job_execution_started"), "INFO")

        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("run_job_title"),
            self
        )

    def _toggle_job(self):
        """Toggle job enabled/disabled status."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_job_first"),
                tr("toggle_job_title"),
                self
            )
            return

        # Get current status
        if isinstance(self._current_item, dict):
            current_status = self._current_item.get("status", "")
        else:
            current_status = "Enabled" if getattr(self._current_item, "enabled", False) else "Disabled"

        new_status = "Disabled" if current_status == "Enabled" else "Enabled"

        # TODO: Update database
        # config_db.update_job_status(self._current_item.id, new_status == "Enabled")
        # self.refresh()

        DialogHelper.info(
            tr("job_status_changed").format(status=new_status),
            tr("toggle_job_title"),
            self
        )
