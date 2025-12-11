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
from ..core.i18n_bridge import tr


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
        # Refresh will be called when connected to database

    def _get_tree_columns(self) -> List[str]:
        """
        Return column names for tree view.

        Returns:
            List of column names
        """
        return [tr("col_name"), tr("col_type"), tr("col_description")]

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

        # Replace default toolbar
        old_toolbar = self.toolbar
        self.toolbar = toolbar_builder.build()
        self.layout().replaceWidget(old_toolbar, self.toolbar)
        old_toolbar.setParent(None)

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

        # Set monospace font for code
        from PySide6.QtGui import QFont
        code_font = QFont("Consolas", 10)
        code_font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_editor.setFont(code_font)

        # TODO: Apply Python syntax highlighting when available
        # from ...utils.python_highlighter import PythonHighlighter
        # self.highlighter = PythonHighlighter(self.code_editor.document())

        content_splitter.addWidget(self.code_editor)

        # Log panel with filters
        self.log_panel = LogPanel(with_filters=True)
        content_splitter.addWidget(self.log_panel)

        # Set proportions (60% code, 40% logs)
        content_splitter.setSizes([600, 400])

        self.content_layout.addWidget(content_splitter)

    def _load_items(self):
        """Load scripts from database into tree view."""
        # TODO: Integrate with database layer when available
        # For now, create placeholder data

        # Placeholder scripts
        placeholder_scripts = [
            {
                "name": "Sample Script 1",
                "script_type": "Data Processing",
                "description": "Example data processing script",
                "script_content": "import pandas as pd\n\n# Sample script\ndf = pd.read_csv('data.csv')\nprint(df.head())",
                "created": "2025-12-01",
                "modified": "2025-12-10"
            },
            {
                "name": "Sample Script 2",
                "script_type": "Data Export",
                "description": "Export data to Excel",
                "script_content": "import pandas as pd\n\n# Export script\ndf.to_excel('output.xlsx', index=False)\nprint('Export complete')",
                "created": "2025-12-05",
                "modified": "2025-12-08"
            }
        ]

        for script in placeholder_scripts:
            self.tree_view.add_item(
                parent=None,
                text=[script["name"], script["script_type"], script["description"]],
                data=script
            )

        # Real implementation will be:
        # try:
        #     from ...database.config_db import get_config_db
        #     config_db = get_config_db()
        #     scripts = config_db.get_all_scripts()
        #
        #     for script in scripts:
        #         self.tree_view.add_item(
        #             parent=None,
        #             text=[script.name, script.script_type, script.description],
        #             data=script
        #         )
        # except Exception as e:
        #     DialogHelper.error(
        #         tr("error_loading_scripts"),
        #         tr("error_title"),
        #         self,
        #         details=str(e)
        #     )

    def _display_item(self, item_data: Any):
        """
        Display selected script details and code.

        Args:
            item_data: Script data object (dict or database model)
        """
        # Handle both dict (placeholder) and database model
        if isinstance(item_data, dict):
            name = item_data.get("name", "")
            description = item_data.get("description", "")
            script_type = item_data.get("script_type", "")
            created = item_data.get("created", "")
            modified = item_data.get("modified", "")
            script_content = item_data.get("script_content", "")
        else:
            # Assume it's a database model with attributes
            name = getattr(item_data, "name", "")
            description = getattr(item_data, "description", "")
            script_type = getattr(item_data, "script_type", "")
            created = str(getattr(item_data, "created_at", ""))
            modified = str(getattr(item_data, "modified_at", ""))
            script_content = getattr(item_data, "script_content", "")

        # Update details form
        self.details_form.set_value("name", name)
        self.details_form.set_value("description", description)
        self.details_form.set_value("script_type", script_type)
        self.details_form.set_value("created", created)
        self.details_form.set_value("modified", modified)

        # Update code editor
        self.code_editor.setPlainText(script_content)

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
        if not self._current_item:
            DialogHelper.warning(
                tr("select_script_first"),
                tr("edit_script_title"),
                self
            )
            return

        # TODO: Open dialog to edit script
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("edit_script_title"),
            self
        )

    def _delete_script(self):
        """Delete selected script."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_script_first"),
                tr("delete_script_title"),
                self
            )
            return

        # Get script name
        if isinstance(self._current_item, dict):
            script_name = self._current_item.get("name", "")
        else:
            script_name = getattr(self._current_item, "name", "")

        # Confirm deletion
        if DialogHelper.confirm(
            tr("confirm_delete_script").format(name=script_name),
            tr("delete_script_title"),
            self
        ):
            # TODO: Delete from database
            # config_db.delete_script(self._current_item.id)
            # self.refresh()
            DialogHelper.info(
                tr("script_deleted"),
                tr("delete_script_title"),
                self
            )

    def _run_script(self):
        """Run selected script."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_script_first"),
                tr("run_script_title"),
                self
            )
            return

        # TODO: Execute script in separate thread and capture output
        # For now, show placeholder message
        self.log_panel.clear()
        self.log_panel.add_message(tr("script_execution_started"), "INFO")

        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("run_script_title"),
            self
        )
