"""
Data Explorer - Explorer for projects, files, and databases
Provides hierarchical navigation and file visualization
"""

from typing import List, Optional, Any
from pathlib import Path
from PySide6.QtWidgets import QWidget, QStackedWidget, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.custom_datagridview import CustomDataGridView
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr


class DataExplorer(BaseManagerView):
    """Explorer for projects, files, and databases with hierarchical navigation."""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize data explorer.

        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent, title="Data Explorer")
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
        return [tr("col_name"), tr("col_type"), tr("col_path")]

    def _setup_toolbar(self):
        """Setup toolbar with explorer management buttons."""
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_refresh"), self.refresh, icon="refresh.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_add_project"), self._add_project, icon="add.png")
        toolbar_builder.add_button(tr("btn_add_file_root"), self._add_file_root, icon="folder.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_delete"), self._delete_item, icon="delete.png")
        toolbar_builder.add_button(tr("btn_open_location"), self._open_location, icon="open.png")

        # Replace default toolbar
        old_toolbar = self.toolbar
        self.toolbar = toolbar_builder.build()
        self.layout().replaceWidget(old_toolbar, self.toolbar)
        old_toolbar.setParent(None)

    def _setup_details(self):
        """Setup details panel with item information."""
        self.details_form = FormBuilder(title=tr("item_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("field_type"), "item_type") \
            .add_field(tr("field_path"), "path") \
            .add_field(tr("field_size"), "size") \
            .add_field(tr("field_created"), "created") \
            .add_field(tr("field_modified"), "modified") \
            .build()

        self.details_layout.addWidget(self.details_form)

    def _setup_content(self):
        """Setup content panel with stacked viewers for different file types."""
        # Stacked widget to switch between different viewers
        self.viewer_stack = QStackedWidget()

        # CSV viewer (grid)
        self.csv_viewer = CustomDataGridView(show_toolbar=True)
        self.viewer_stack.addWidget(self.csv_viewer)

        # Text viewer (JSON, TXT, etc.)
        self.text_viewer = QTextEdit()
        self.text_viewer.setReadOnly(True)
        self.text_viewer.setPlaceholderText(tr("text_viewer_placeholder"))

        # Set monospace font for text viewer
        text_font = QFont("Consolas", 10)
        text_font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_viewer.setFont(text_font)

        self.viewer_stack.addWidget(self.text_viewer)

        # Empty/default viewer
        self.empty_viewer = QWidget()
        self.viewer_stack.addWidget(self.empty_viewer)

        # Set default to empty viewer
        self.viewer_stack.setCurrentWidget(self.empty_viewer)

        self.content_layout.addWidget(self.viewer_stack)

    def _load_items(self):
        """Load projects and files into hierarchical tree view."""
        # TODO: Integrate with database layer when available
        # For now, create placeholder hierarchical data

        # Placeholder projects
        placeholder_projects = [
            {
                "name": "Project Alpha",
                "type": "Project",
                "description": "Main data project",
                "created": "2025-01-01",
                "file_roots": [
                    {
                        "name": "Data Files",
                        "type": "File Root",
                        "path": "C:/Data/Alpha",
                        "files": [
                            {"name": "users.csv", "type": "CSV", "path": "C:/Data/Alpha/users.csv", "size": "2.5 MB"},
                            {"name": "orders.csv", "type": "CSV", "path": "C:/Data/Alpha/orders.csv", "size": "5.1 MB"},
                            {"name": "config.json", "type": "JSON", "path": "C:/Data/Alpha/config.json", "size": "1.2 KB"}
                        ]
                    }
                ]
            },
            {
                "name": "Project Beta",
                "type": "Project",
                "description": "Secondary project",
                "created": "2025-02-01",
                "file_roots": [
                    {
                        "name": "Export Files",
                        "type": "File Root",
                        "path": "C:/Data/Beta",
                        "files": [
                            {"name": "report.txt", "type": "TXT", "path": "C:/Data/Beta/report.txt", "size": "850 KB"}
                        ]
                    }
                ]
            }
        ]

        # Build hierarchical tree
        for project in placeholder_projects:
            # Add project item
            project_item = self.tree_view.add_item(
                parent=None,
                text=[project["name"], project["type"], ""],
                data=project
            )

            # Add file roots under project
            for file_root in project.get("file_roots", []):
                file_root_item = self.tree_view.add_item(
                    parent=project_item,
                    text=[file_root["name"], file_root["type"], file_root["path"]],
                    data=file_root
                )

                # Add files under file root
                for file in file_root.get("files", []):
                    self.tree_view.add_item(
                        parent=file_root_item,
                        text=[file["name"], file["type"], file["path"]],
                        data=file
                    )

        # Expand all by default
        self.tree_view.expand_all()

        # Real implementation:
        # try:
        #     from ...database.config_db import get_config_db
        #     config_db = get_config_db()
        #     projects = config_db.get_all_projects()
        #
        #     for project in projects:
        #         project_item = self.tree_view.add_item(
        #             parent=None,
        #             text=[project.name, "Project", ""],
        #             data=project
        #         )
        #
        #         file_roots = config_db.get_file_roots_for_project(project.id)
        #         for file_root in file_roots:
        #             file_root_item = self.tree_view.add_item(
        #                 parent=project_item,
        #                 text=[file_root.name, "File Root", file_root.path],
        #                 data=file_root
        #             )
        #
        #             # Load files from file system
        #             files = self._scan_directory(file_root.path)
        #             for file in files:
        #                 self.tree_view.add_item(
        #                     parent=file_root_item,
        #                     text=[file.name, file.extension, file.path],
        #                     data=file
        #                 )
        # except Exception as e:
        #     DialogHelper.error(
        #         tr("error_loading_projects"),
        #         tr("error_title"),
        #         self,
        #         details=str(e)
        #     )

    def _display_item(self, item_data: Any):
        """
        Display selected item details and content.

        Args:
            item_data: Item data object (dict or database model)
        """
        # Handle both dict (placeholder) and database model
        if isinstance(item_data, dict):
            name = item_data.get("name", "")
            item_type = item_data.get("type", "")
            path = item_data.get("path", "")
            size = item_data.get("size", "")
            created = item_data.get("created", "")
            modified = item_data.get("modified", "")
        else:
            # Assume it's a database model with attributes
            name = getattr(item_data, "name", "")
            item_type = getattr(item_data, "type", "")
            path = getattr(item_data, "path", "")
            size = getattr(item_data, "size", "")
            created = str(getattr(item_data, "created_at", ""))
            modified = str(getattr(item_data, "modified_at", ""))

        # Update details form
        self.details_form.set_value("name", name)
        self.details_form.set_value("item_type", item_type)
        self.details_form.set_value("path", path)
        self.details_form.set_value("size", size)
        self.details_form.set_value("created", created)
        self.details_form.set_value("modified", modified)

        # Display content based on type
        if item_type == "CSV":
            self._display_csv(path)
        elif item_type in ["JSON", "TXT"]:
            self._display_text(path)
        else:
            # Project or File Root - show empty viewer
            self.viewer_stack.setCurrentWidget(self.empty_viewer)

    def _display_csv(self, file_path: str):
        """
        Display CSV file in grid viewer.

        Args:
            file_path: Path to CSV file
        """
        # TODO: Load actual CSV file
        # For now, show placeholder data
        self.csv_viewer.set_columns(["ID", "Name", "Email", "Created"])
        sample_data = [
            ["1", "John Doe", "john@example.com", "2025-01-01"],
            ["2", "Jane Smith", "jane@example.com", "2025-01-02"],
            ["3", "Bob Johnson", "bob@example.com", "2025-01-03"]
        ]
        self.csv_viewer.set_data(sample_data)
        self.viewer_stack.setCurrentWidget(self.csv_viewer)

        # Real implementation:
        # try:
        #     import pandas as pd
        #     df = pd.read_csv(file_path)
        #
        #     # Set columns
        #     self.csv_viewer.set_columns(df.columns.tolist())
        #
        #     # Set data (convert to list of lists)
        #     data = df.values.tolist()
        #     self.csv_viewer.set_data(data)
        #
        #     self.viewer_stack.setCurrentWidget(self.csv_viewer)
        # except Exception as e:
        #     DialogHelper.error(
        #         tr("error_loading_csv"),
        #         tr("error_title"),
        #         self,
        #         details=str(e)
        #     )

    def _display_text(self, file_path: str):
        """
        Display text file (JSON, TXT) in text viewer.

        Args:
            file_path: Path to text file
        """
        # TODO: Load actual text file
        # For now, show placeholder text
        if "json" in file_path.lower():
            placeholder_text = '{\n  "setting1": "value1",\n  "setting2": "value2",\n  "nested": {\n    "key": "value"\n  }\n}'
        else:
            placeholder_text = "Sample text file content.\n\nThis is a placeholder for the actual file content."

        self.text_viewer.setPlainText(placeholder_text)
        self.viewer_stack.setCurrentWidget(self.text_viewer)

        # Real implementation:
        # try:
        #     with open(file_path, 'r', encoding='utf-8') as f:
        #         content = f.read()
        #
        #     # Pretty print JSON
        #     if file_path.lower().endswith('.json'):
        #         import json
        #         try:
        #             parsed = json.loads(content)
        #             content = json.dumps(parsed, indent=2)
        #         except:
        #             pass  # If JSON parsing fails, show as-is
        #
        #     self.text_viewer.setPlainText(content)
        #     self.viewer_stack.setCurrentWidget(self.text_viewer)
        # except Exception as e:
        #     DialogHelper.error(
        #         tr("error_loading_file"),
        #         tr("error_title"),
        #         self,
        #         details=str(e)
        #     )

    def _add_project(self):
        """Add a new project."""
        # TODO: Open dialog to create new project
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("add_project_title"),
            self
        )

    def _add_file_root(self):
        """Add a new file root to selected project."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_project_first"),
                tr("add_file_root_title"),
                self
            )
            return

        # TODO: Open dialog to add file root
        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("add_file_root_title"),
            self
        )

    def _delete_item(self):
        """Delete selected item."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_item_first"),
                tr("delete_item_title"),
                self
            )
            return

        # Get item name
        if isinstance(self._current_item, dict):
            item_name = self._current_item.get("name", "")
        else:
            item_name = getattr(self._current_item, "name", "")

        # Confirm deletion
        if DialogHelper.confirm(
            tr("confirm_delete_item").format(name=item_name),
            tr("delete_item_title"),
            self
        ):
            # TODO: Delete from database
            # config_db.delete_item(self._current_item.id)
            # self.refresh()
            DialogHelper.info(
                tr("item_deleted"),
                tr("delete_item_title"),
                self
            )

    def _open_location(self):
        """Open file location in file explorer."""
        if not self._current_item:
            DialogHelper.warning(
                tr("select_item_first"),
                tr("open_location_title"),
                self
            )
            return

        # Get path
        if isinstance(self._current_item, dict):
            path = self._current_item.get("path", "")
        else:
            path = getattr(self._current_item, "path", "")

        if not path:
            DialogHelper.warning(
                tr("no_path_for_item"),
                tr("open_location_title"),
                self
            )
            return

        # TODO: Open in file explorer
        # import subprocess
        # import os
        # import platform
        #
        # if platform.system() == "Windows":
        #     subprocess.run(["explorer", "/select,", os.path.normpath(path)])
        # elif platform.system() == "Darwin":  # macOS
        #     subprocess.run(["open", "-R", path])
        # else:  # Linux
        #     subprocess.run(["xdg-open", os.path.dirname(path)])

        DialogHelper.info(
            tr("feature_coming_soon"),
            tr("open_location_title"),
            self
        )
