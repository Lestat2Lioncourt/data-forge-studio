"""
Scripts Manager - Manager for Python scripts with hierarchical TreeView
Provides interface to view, edit, and execute Python scripts organized by type
"""

import json
import os
import subprocess
from typing import List, Optional, TYPE_CHECKING
from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QMenu, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtCore import QUrl

if TYPE_CHECKING:
    from .workspace_manager import WorkspaceManager

from .base import HierarchicalManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.log_panel import LogPanel
from ..widgets.code_viewer import CodeViewerWidget
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Script
from ...core.script_template_loader import get_template_loader
from ..dialogs.script_dialog import ScriptDialog

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
        self._workspace_manager: Optional["WorkspaceManager"] = None
        super().__init__(parent)

    def set_workspace_manager(self, workspace_manager: "WorkspaceManager"):
        """Set reference to WorkspaceManager for auto-refresh on workspace changes."""
        self._workspace_manager = workspace_manager

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
        """Add script detail fields - called by _setup_right_panel."""
        form_builder.add_field(tr("field_name"), "name")
        form_builder.add_field(tr("field_type"), "script_type")
        form_builder.add_field(tr("field_file_path") if tr("field_file_path") != "field_file_path" else "File", "file_path")
        form_builder.add_field(tr("field_description"), "description")
        form_builder.add_field(tr("field_created"), "created")
        form_builder.add_field(tr("field_modified"), "modified")

    def _setup_content_widgets(self, layout: QVBoxLayout):
        """Not used - layout handled by _setup_right_panel."""
        pass

    def _setup_right_panel(self):
        """
        Override base class to create tabbed Details/Parameters layout.

        Layout:
        - Top: QTabWidget with "Details" and "Parameters" tabs
        - Bottom: Code viewer (JSON schema) + Log panel
        """
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)

        # === Top: Tabbed panel (Details + Parameters) ===
        self.info_tabs = QTabWidget()

        # Tab 1: Details
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(5, 5, 5, 5)

        self.details_form = FormBuilder(title=tr("script_details"))
        self._setup_detail_fields(self.details_form)
        details_layout.addWidget(self.details_form.container)
        details_layout.addStretch()

        self.info_tabs.addTab(details_widget, tr("tab_details") if tr("tab_details") != "tab_details" else "Details")

        # Tab 2: Parameters (read-only table)
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setContentsMargins(5, 5, 5, 5)

        self.params_table = QTableWidget()
        self.params_table.setColumnCount(4)
        self.params_table.setHorizontalHeaderLabels([
            tr("param_name") if tr("param_name") != "param_name" else "Name",
            tr("param_type") if tr("param_type") != "param_type" else "Type",
            tr("param_label") if tr("param_label") != "param_label" else "Label",
            tr("param_required") if tr("param_required") != "param_required" else "Required"
        ])
        self.params_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.params_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.params_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.params_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.params_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.params_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.params_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        params_layout.addWidget(self.params_table)

        self.info_tabs.addTab(params_widget, tr("tab_parameters") if tr("tab_parameters") != "tab_parameters" else "Parameters")

        self.right_splitter.addWidget(self.info_tabs)

        # === Bottom: Tabbed panel (Source + Log) ===
        self.content_tabs = QTabWidget()

        # Tab 1: Source (read-only code viewer)
        source_widget = QWidget()
        source_layout = QVBoxLayout(source_widget)
        source_layout.setContentsMargins(0, 0, 0, 0)

        self.code_viewer = CodeViewerWidget(show_header=False)
        source_layout.addWidget(self.code_viewer)

        self.content_tabs.addTab(source_widget, tr("tab_source") if tr("tab_source") != "tab_source" else "Source")

        # Tab 2: Log panel
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_panel = LogPanel(with_filters=True)
        log_layout.addWidget(self.log_panel)

        self.content_tabs.addTab(log_widget, tr("tab_log") if tr("tab_log") != "tab_log" else "Log")

        self.right_splitter.addWidget(self.content_tabs)

        # Set proportions: info tabs smaller, content larger
        self.right_splitter.setSizes([200, 400])

    def _load_items(self) -> List[Script]:
        """Load scripts from database."""
        config_db = get_config_db()
        return config_db.get_all_scripts()

    def _get_item_category(self, item: Script) -> str:
        return item.script_type or "other"

    def _get_item_name(self, item: Script) -> str:
        return item.name

    def _display_item(self, script: Script):
        """Display script details, parameters table, and source code."""
        if not script:
            self._clear_item_display()
            return

        # === Tab 1: Details form ===
        self.details_form.set_value("name", script.name)
        self.details_form.set_value("script_type", script.script_type or "")
        self.details_form.set_value("file_path", script.file_path or "")
        self.details_form.set_value("description", script.description or "")
        self.details_form.set_value("created", script.created_at or "")
        self.details_form.set_value("modified", script.updated_at or "")

        # === Tab 2: Parameters table ===
        self._populate_parameters_table(script)

        # === Bottom Source tab: Read and display file with syntax highlighting ===
        # Try to get source code from script's file_path first
        source_code = script.get_source_code()
        file_path = script.file_path

        # If no file_path in script, try to find it from template
        if not source_code and not file_path:
            loader = get_template_loader()
            template = loader.get_template_by_name(script.name)
            if template and template.has_file:
                file_path = template.file_path
                source_code = template.get_source_code()

        if source_code:
            # Get file extension for syntax highlighting
            if file_path:
                import os
                _, ext = os.path.splitext(file_path)
                file_ext = ext.lstrip(".").lower() if ext else "python"
            else:
                file_ext = script.get_file_extension() or "python"
            self.code_viewer.set_code(source_code, file_ext)
        elif file_path:
            # File path set but file not found
            self.code_viewer.set_code(
                f"# File not found: {file_path}\n"
                f"# Fichier non trouvé: {file_path}",
                "python"
            )
        else:
            # No file path set - show informative message
            self.code_viewer.set_code(
                "# No file path configured for this script.\n"
                "# Edit the script to set a file path.\n"
                "#\n"
                "# Aucun chemin de fichier configuré pour ce script.\n"
                "# Modifiez le script pour définir un chemin de fichier.",
                "python"
            )

        # Clear log
        self.log_panel.clear()

    def _populate_parameters_table(self, script: Script):
        """Populate the parameters table from script.parameters_schema."""
        self.params_table.setRowCount(0)

        if not script.parameters_schema:
            return

        try:
            params = json.loads(script.parameters_schema)
            if not isinstance(params, list):
                return

            self.params_table.setRowCount(len(params))

            for row, param in enumerate(params):
                # Name
                name_item = QTableWidgetItem(param.get("name", ""))
                self.params_table.setItem(row, 0, name_item)

                # Type
                type_item = QTableWidgetItem(param.get("type", "string"))
                self.params_table.setItem(row, 1, type_item)

                # Label
                label_item = QTableWidgetItem(param.get("label", ""))
                self.params_table.setItem(row, 2, label_item)

                # Required
                required = tr("yes") if param.get("required", True) else tr("no")
                required_item = QTableWidgetItem(required)
                self.params_table.setItem(row, 3, required_item)

        except json.JSONDecodeError:
            logger.warning(f"Invalid parameters_schema JSON for script {script.name}")

    def _clear_item_display(self):
        """Clear all details fields, parameters table, and code viewer."""
        self.details_form.set_value("name", "")
        self.details_form.set_value("script_type", "")
        self.details_form.set_value("file_path", "")
        self.details_form.set_value("description", "")
        self.details_form.set_value("created", "")
        self.details_form.set_value("modified", "")
        self.params_table.setRowCount(0)
        self.code_viewer.clear()
        self.log_panel.clear()

    def _on_item_action(self, item: Script):
        """Display script code on double-click."""
        # The script is already displayed via _display_item when selected
        # Just ensure focus is on the code viewer
        self.code_viewer.setFocus()

    # ==================== Context Menu ====================

    def _build_category_context_menu(self, menu: QMenu, category_name: str):
        """Build context menu for script type folder."""
        add_action = QAction(tr("btn_add_script"), self)
        add_action.triggered.connect(self._add_script)
        menu.addAction(add_action)

    def _build_item_context_menu(self, menu: QMenu, script: Script):
        """Build context menu for a script."""
        # Open in external editor action
        open_external_action = QAction(tr("open_in_editor") if tr("open_in_editor") != "open_in_editor" else "Open in External Editor", self)
        open_external_action.triggered.connect(lambda: self._open_in_external_editor(script))
        menu.addAction(open_external_action)

        menu.addSeparator()

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

        menu.addSeparator()

        # Workspace submenu
        from ..widgets.workspace_menu_builder import build_workspace_menu
        config_db = get_config_db()
        ws_menu = build_workspace_menu(
            parent=self,
            item_id=script.id,
            get_item_workspaces=lambda: config_db.get_script_workspaces(script.id),
            add_to_workspace=lambda ws_id: config_db.add_script_to_workspace(ws_id, script.id),
            remove_from_workspace=lambda ws_id: config_db.remove_script_from_workspace(ws_id, script.id),
            on_workspace_changed=self._on_workspace_changed,
        )
        menu.addMenu(ws_menu)

    def _on_workspace_changed(self, workspace_id: str):
        """Callback when item is added/removed from a workspace."""
        if self._workspace_manager:
            self._workspace_manager.refresh_workspace(workspace_id)

    # ==================== Actions ====================

    def _add_script(self):
        """Add a new script."""
        dialog = ScriptDialog(self)
        if dialog.exec() == ScriptDialog.DialogCode.Accepted:
            self.refresh()
            DialogHelper.info(tr("script_added"), tr("add_script_title"), self)

    def _edit_script(self):
        """Edit selected script."""
        if not self._current_item:
            DialogHelper.warning(tr("select_script_first"), tr("edit_script_title"), self)
            return

        dialog = ScriptDialog(self, script=self._current_item)
        if dialog.exec() == ScriptDialog.DialogCode.Accepted:
            self.refresh()
            DialogHelper.info(tr("script_updated"), tr("edit_script_title"), self)

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

    def _open_in_external_editor(self, script: Script):
        """
        Open script file in external editor.

        Opens the script's file_path directly in the external editor.
        """
        if not script or not script.file_path:
            DialogHelper.warning(
                tr("no_file_to_edit") if tr("no_file_to_edit") != "no_file_to_edit" else "No file path defined",
                tr("open_in_editor") if tr("open_in_editor") != "open_in_editor" else "Open in Editor",
                self
            )
            return

        if not os.path.isfile(script.file_path):
            DialogHelper.warning(
                tr("file_not_found") if tr("file_not_found") != "file_not_found" else f"File not found: {script.file_path}",
                tr("open_in_editor") if tr("open_in_editor") != "open_in_editor" else "Open in Editor",
                self
            )
            return

        try:
            # Try VS Code first, then fall back to system default
            try:
                # Try to open with VS Code
                subprocess.Popen(["code", script.file_path], shell=True)
                logger.info(f"Opened script in VS Code: {script.file_path}")
            except Exception:
                # Fall back to system default
                if os.name == "nt":  # Windows
                    os.startfile(script.file_path)
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(script.file_path))
                logger.info(f"Opened script in default editor: {script.file_path}")

        except Exception as e:
            logger.error(f"Error opening script in external editor: {e}")
            DialogHelper.error(
                tr("error_opening_editor") if tr("error_opening_editor") != "error_opening_editor" else "Error opening editor",
                details=str(e),
                parent=self
            )

    def _run_script(self):
        """Run selected script."""
        if not self._current_item:
            DialogHelper.warning(tr("select_script_first"), tr("run_script_title"), self)
            return

        self.run_script_by_obj(self._current_item)

    # ==================== Public API (for WorkspaceManager) ====================

    def show_script(self, script: Script, target_viewer=None):
        """
        Display script details in a viewer.

        Args:
            script: Script object to display
            target_viewer: Optional ObjectViewerWidget (default: internal display)
        """
        if target_viewer:
            # Use external viewer for basic details
            target_viewer.show_details(
                name=script.name,
                obj_type=f"Script ({script.script_type or 'other'})",
                description=script.description or "",
                created=script.created_at or "",
                updated=script.updated_at or ""
            )
        else:
            # Use internal display
            self._display_item(script)

    def run_script_by_obj(self, script: Script):
        """
        Run a specific script.

        Args:
            script: Script object to run
        """
        self.log_panel.clear()
        self.log_panel.add_message(tr("script_execution_started"), "INFO")
        DialogHelper.info(tr("feature_coming_soon"), tr("run_script_title"), self)

    def edit_script_by_obj(self, script: Script):
        """
        Open edit dialog for a specific script.

        Args:
            script: Script object to edit
        """
        dialog = ScriptDialog(self, script=script)
        if dialog.exec() == ScriptDialog.DialogCode.Accepted:
            self.refresh()
            DialogHelper.info(tr("script_updated"), tr("edit_script_title"), self)

    def delete_script_by_obj(self, script: Script):
        """
        Delete a specific script.

        Args:
            script: Script object to delete
        """
        if DialogHelper.confirm(
            tr("confirm_delete_script").format(name=script.name),
            tr("delete_script_title"),
            self
        ):
            try:
                config_db = get_config_db()
                config_db.delete_script(script.id)
                self.refresh()
                DialogHelper.info(tr("script_deleted"), tr("delete_script_title"), self)
            except Exception as e:
                DialogHelper.error(str(e), tr("error"), self)

    def get_script_context_actions(self, script: Script, parent, target_viewer=None) -> list:
        """
        Get context menu actions for a script.

        Args:
            script: Script object
            parent: Parent widget for actions
            target_viewer: Optional ObjectViewerWidget for display

        Returns:
            List of QAction objects
        """
        actions = []

        # Open in external editor action
        open_external_action = QAction(tr("open_in_editor") if tr("open_in_editor") != "open_in_editor" else "Open in External Editor", parent)
        open_external_action.triggered.connect(lambda: self._open_in_external_editor(script))
        actions.append(open_external_action)

        # View action
        view_action = QAction(tr("btn_view") if tr("btn_view") != "btn_view" else "View", parent)
        view_action.triggered.connect(lambda: self.show_script(script, target_viewer))
        actions.append(view_action)

        # Run action
        run_action = QAction(tr("btn_run"), parent)
        run_action.triggered.connect(lambda: self.run_script_by_obj(script))
        actions.append(run_action)

        # Edit action
        edit_action = QAction(tr("btn_edit"), parent)
        edit_action.triggered.connect(lambda: self.edit_script_by_obj(script))
        actions.append(edit_action)

        # Delete action
        delete_action = QAction(tr("btn_delete"), parent)
        delete_action.triggered.connect(lambda: self.delete_script_by_obj(script))
        actions.append(delete_action)

        return actions
