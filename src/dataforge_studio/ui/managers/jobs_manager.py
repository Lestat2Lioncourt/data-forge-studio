"""
Jobs Manager - Manager for scheduled jobs with hierarchical TreeView
Provides interface to view, edit, and manage automated jobs organized by type
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
from ...database.config_db import get_config_db, Job
from ...utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


class JobsManager(QWidget):
    """
    Manager for scheduled jobs with hierarchical TreeView.

    Layout:
    - TOP: Toolbar
    - LEFT: TreeView (Type > Job)
    - RIGHT: Details panel + Log panel
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
            title=tr("jobs_explorer"),
            icon_name="jobs.png"
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

        # Right panel: Details + Log
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Details panel
        self.details_panel = QWidget()
        self.details_layout = QVBoxLayout(self.details_panel)
        self.details_layout.setContentsMargins(5, 5, 5, 5)
        self._setup_details()
        right_splitter.addWidget(self.details_panel)

        # Content panel (config + log)
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
        self.toolbar = toolbar_builder.build()

    def _setup_details(self):
        """Setup details panel with job information."""
        self.details_form = FormBuilder(title=tr("job_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("field_type"), "job_type") \
            .add_field(tr("field_description"), "description") \
            .add_field(tr("field_status"), "status") \
            .add_field(tr("field_script"), "script") \
            .add_field(tr("field_last_run"), "last_run") \
            .add_field(tr("field_created"), "created")

        self.details_layout.addWidget(self.details_form.container)

    def _setup_content(self):
        """Setup content panel with config editor and log panel."""
        # Configuration text area
        config_label = QLabel(tr("job_config"))
        config_label.setStyleSheet("font-weight: bold;")
        self.content_layout.addWidget(config_label)

        self.config_editor = QTextEdit()
        self.config_editor.setReadOnly(True)
        self.config_editor.setPlaceholderText(tr("job_config_placeholder"))
        self.config_editor.setMaximumHeight(100)
        UIHelper.apply_monospace_font(self.config_editor)
        self.content_layout.addWidget(self.config_editor)

        # Log panel
        self.log_panel = LogPanel(with_filters=True)
        self.content_layout.addWidget(self.log_panel, stretch=1)

    def get_tree_widget(self):
        """Return the tree widget for embedding."""
        return self.tree

    def refresh(self):
        """Reload all jobs from database."""
        self.tree.clear()
        self._type_items.clear()
        self._current_item = None
        self._clear_details()
        self._load_jobs()

    def _load_jobs(self):
        """Load jobs from database into hierarchical tree."""
        try:
            config_db = get_config_db()
            jobs = config_db.get_all_jobs()

            # Group jobs by type
            job_types: Dict[str, List[Job]] = {
                "script": [],
                "workflow": []
            }

            for job in jobs:
                job_type = job.job_type or "script"
                if job_type not in job_types:
                    job_types[job_type] = []
                job_types[job_type].append(job)

            # Create tree structure
            folder_icon = get_icon("Category", size=16)
            job_icon = get_icon("jobs", size=16)

            type_labels = {
                "script": tr("job_type_scripts"),
                "workflow": tr("job_type_workflows")
            }

            for job_type in ["script", "workflow"]:
                jobs_list = job_types.get(job_type, [])
                if not jobs_list:
                    continue

                # Create type folder
                type_item = QTreeWidgetItem(self.tree)
                label = type_labels.get(job_type, job_type)
                type_item.setText(0, f"{label} ({len(jobs_list)})")
                if folder_icon:
                    type_item.setIcon(0, folder_icon)
                type_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "job_type",
                    "job_type": job_type
                })
                type_item.setExpanded(True)
                self._type_items[job_type] = type_item

                # Add jobs under type
                for job in sorted(jobs_list, key=lambda j: j.name):
                    job_item = QTreeWidgetItem(type_item)
                    status_icon = "✓" if job.enabled else "✗"
                    job_item.setText(0, f"{status_icon} {job.name}")
                    if job_icon:
                        job_item.setIcon(0, job_icon)
                    job_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "job",
                        "job": job
                    })

        except Exception as e:
            logger.error(f"Error loading jobs: {e}")

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle single click on tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "job":
            self._current_item = data.get("job")
            self._display_job(self._current_item)
            self.item_selected.emit(self._current_item)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == "job":
            self._current_item = data.get("job")
            self._run_job()

    def _display_job(self, job: Job):
        """Display job details."""
        if not job:
            self._clear_details()
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

    def _clear_details(self):
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

    # ===== Actions =====

    def _add_job(self):
        """Add a new job."""
        DialogHelper.info(tr("feature_coming_soon"), tr("add_job_title"), self)

    def _edit_job(self):
        """Edit selected job."""
        if not self._current_item:
            DialogHelper.warning(tr("select_job_first"), tr("edit_job_title"), self)
            return
        DialogHelper.info(tr("feature_coming_soon"), tr("edit_job_title"), self)

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

        if data.get("type") == "job_type":
            # Context menu for job type folder
            add_action = QAction(tr("btn_add_job"), self)
            add_action.triggered.connect(self._add_job)
            menu.addAction(add_action)

        elif data.get("type") == "job":
            job = data.get("job")
            job_id = job.id if job else None

            if job_id:
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
                workspace_menu = self._build_workspace_submenu(job_id)
                if workspace_menu:
                    menu.addMenu(workspace_menu)

        if menu.actions():
            menu.exec(self.tree.viewport().mapToGlobal(position))

    def _build_workspace_submenu(self, job_id: str) -> QMenu:
        """Build a submenu for adding/removing a job to/from workspaces."""
        config_db = get_config_db()
        workspaces = config_db.get_all_workspaces()

        menu = QMenu(tr("menu_workspaces"), self)
        workspace_icon = get_icon("Workspace", size=16) or get_icon("folder", size=16)
        if workspace_icon:
            menu.setIcon(workspace_icon)

        if not workspaces:
            new_action = QAction(tr("new_workspace"), self)
            new_action.triggered.connect(lambda: self._create_new_workspace_and_add(job_id))
            menu.addAction(new_action)
            return menu

        job_workspaces = config_db.get_job_workspaces(job_id)
        workspace_ids_with_job = {ws.id for ws in job_workspaces}

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

        new_action = QAction(tr("new_workspace") + "...", self)
        new_action.triggered.connect(lambda: self._create_new_workspace_and_add(job_id))
        menu.addAction(new_action)

        return menu

    def _toggle_workspace(self, workspace_id: str, job_id: str, is_in_workspace: bool):
        """Toggle a job in/out of a workspace."""
        config_db = get_config_db()
        if is_in_workspace:
            config_db.remove_job_from_workspace(workspace_id, job_id)
        else:
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
