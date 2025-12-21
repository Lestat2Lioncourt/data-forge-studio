"""
Data Explorer - Explorer for projects, files, and databases
Provides hierarchical navigation and file visualization
"""

import subprocess
import sys
import json
import logging
from typing import List, Optional, Any
from pathlib import Path
from PySide6.QtWidgets import QWidget, QStackedWidget, QTextEdit, QMessageBox
from PySide6.QtCore import Qt

from .base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.form_builder import FormBuilder
from ..widgets.custom_datagridview import CustomDataGridView
from ..widgets.dialog_helper import DialogHelper
from ..widgets.edit_dialogs import EditRootFolderDialog
from ..utils.ui_helper import UIHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db
from ...database.models.file_root import FileRoot
from ...core.data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    excel_to_dataframe,
    LARGE_DATASET_THRESHOLD
)
from ...utils.file_reader import read_file_content

logger = logging.getLogger(__name__)


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
        self._replace_toolbar(toolbar_builder)

    def _setup_details(self):
        """Setup details panel with item information."""
        self.details_form = FormBuilder(title=tr("item_details")) \
            .add_field(tr("field_name"), "name") \
            .add_field(tr("field_type"), "item_type") \
            .add_field(tr("field_path"), "path") \
            .add_field(tr("field_size"), "size") \
            .add_field(tr("field_created"), "created") \
            .add_field(tr("field_modified"), "modified")

        self.details_layout.addWidget(self.details_form.container)

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
        UIHelper.apply_monospace_font(self.text_viewer)
        self.viewer_stack.addWidget(self.text_viewer)

        # Empty/default viewer
        self.empty_viewer = QWidget()
        self.viewer_stack.addWidget(self.empty_viewer)

        # Set default to empty viewer
        self.viewer_stack.setCurrentWidget(self.empty_viewer)

        self.content_layout.addWidget(self.viewer_stack)

    def _load_items(self):
        """Load projects and files into hierarchical tree view."""
        try:
            config_db = get_config_db()
            projects = config_db.get_all_projects()

            for project in projects:
                # Add project item
                project_item = self.tree_view.add_item(
                    parent=None,
                    text=[project.name, "Project", ""],
                    data={"obj": project, "type": "Project"}
                )

                # Load file roots for this project
                file_roots = config_db.get_project_file_roots(project.id)
                for file_root in file_roots:
                    file_root_item = self.tree_view.add_item(
                        parent=project_item,
                        text=[file_root.name or file_root.path, "File Root", file_root.path],
                        data={"obj": file_root, "type": "File Root"}
                    )

                    # Scan directory recursively with folder counts
                    try:
                        root_path = Path(file_root.path)
                        if root_path.exists() and root_path.is_dir():
                            self._scan_directory_recursive(root_path, file_root_item)
                    except Exception as e:
                        # Log error but continue with other file roots
                        print(f"Error scanning directory {file_root.root_path}: {e}")

            # Expand all by default
            self.tree_view.expand_all()

        except Exception as e:
            DialogHelper.error(
                tr("error_loading_projects"),
                tr("error_title"),
                self,
                details=str(e)
            )

    def _scan_directory(self, directory_path: Path) -> List[dict]:
        """
        Scan directory for files (basic implementation).

        Args:
            directory_path: Path to directory

        Returns:
            List of file info dicts
        """
        files = []
        try:
            for item in directory_path.iterdir():
                if item.is_file():
                    # Get file extension
                    extension = item.suffix.upper().lstrip(".")
                    if not extension:
                        extension = "FILE"

                    # Get file size
                    size_bytes = item.stat().st_size
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                    files.append({
                        "name": item.name,
                        "type": extension,
                        "path": str(item),
                        "size": size_str
                    })
        except Exception as e:
            print(f"Error scanning directory {directory_path}: {e}")

        return files

    def _count_files_in_directory(self, directory_path: Path) -> int:
        """
        Count total number of files in a directory (non-recursive).

        Args:
            directory_path: Path to directory

        Returns:
            Number of files in directory
        """
        try:
            return sum(1 for item in directory_path.iterdir() if item.is_file())
        except Exception:
            return 0

    def _scan_directory_recursive(self, directory_path: Path, parent_item):
        """
        Recursively scan directory and populate tree with subdirectories and files.
        Shows subdirectories with file counts like "Documents (5 files)".

        Args:
            directory_path: Path to directory to scan
            parent_item: Parent tree item to add children to
        """
        try:
            # Separate subdirectories and files
            subdirs = []
            files = []

            for item in directory_path.iterdir():
                if item.is_dir():
                    subdirs.append(item)
                elif item.is_file():
                    files.append(item)

            # Add subdirectories first (with file counts)
            for subdir in sorted(subdirs):
                file_count = self._count_files_in_directory(subdir)

                # Format directory name with file count
                if file_count == 0:
                    display_name = subdir.name
                elif file_count == 1:
                    display_name = f"{subdir.name} (1 file)"
                else:
                    display_name = f"{subdir.name} ({file_count} files)"

                # Add directory item
                dir_item = self.tree_view.add_item(
                    parent=parent_item,
                    text=[display_name, "Folder", str(subdir)],
                    data={"name": subdir.name, "type": "Folder", "path": str(subdir)}
                )

                # Recursively scan subdirectory
                self._scan_directory_recursive(subdir, dir_item)

            # Add files
            for file_path in sorted(files):
                # Get file extension
                extension = file_path.suffix.upper().lstrip(".")
                if not extension:
                    extension = "FILE"

                # Get file size
                size_bytes = file_path.stat().st_size
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                # Add file item
                self.tree_view.add_item(
                    parent=parent_item,
                    text=[file_path.name, extension, str(file_path)],
                    data={
                        "name": file_path.name,
                        "type": extension,
                        "path": str(file_path),
                        "size": size_str
                    }
                )

        except Exception as e:
            print(f"Error scanning directory {directory_path}: {e}")

    def _display_item(self, item_data: Any):
        """
        Display selected item details and content.

        Args:
            item_data: Item data object (dict with "obj" and "type", or file info dict)
        """
        # Check if this is a Project or File Root (dict with "obj" key)
        if isinstance(item_data, dict) and "obj" in item_data:
            obj = item_data["obj"]
            item_type = item_data["type"]

            if item_type == "Project":
                name = obj.name
                path = ""
                size = ""
                created = str(obj.created_at) if hasattr(obj, "created_at") else ""
                modified = str(obj.modified_at) if hasattr(obj, "modified_at") else ""
            elif item_type == "File Root":
                name = obj.root_path
                path = obj.root_path
                size = ""
                created = str(obj.created_at) if hasattr(obj, "created_at") else ""
                modified = ""
            else:
                name = ""
                path = ""
                size = ""
                created = ""
                modified = ""

            # Update details form
            self.details_form.set_value("name", name)
            self.details_form.set_value("item_type", item_type)
            self.details_form.set_value("path", path)
            self.details_form.set_value("size", size)
            self.details_form.set_value("created", created)
            self.details_form.set_value("modified", modified)

            # Show empty viewer for Projects and File Roots
            self.viewer_stack.setCurrentWidget(self.empty_viewer)

        # Handle file info dict (from _scan_directory_recursive)
        elif isinstance(item_data, dict):
            name = item_data.get("name", "")
            item_type = item_data.get("type", "")
            path = item_data.get("path", "")
            size = item_data.get("size", "")
            created = ""
            modified = ""

            # Get file stats if path exists
            if path:
                try:
                    path_obj = Path(path)
                    if path_obj.exists():
                        stat = path_obj.stat()
                        from datetime import datetime
                        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            # Update details form
            self.details_form.set_value("name", name)
            self.details_form.set_value("item_type", item_type)
            self.details_form.set_value("path", path)
            self.details_form.set_value("size", size)
            self.details_form.set_value("created", created)
            self.details_form.set_value("modified", modified)

            # Display content based on type
            if item_type == "Folder":
                # Show empty viewer for folders
                self.viewer_stack.setCurrentWidget(self.empty_viewer)
            elif item_type == "CSV":
                self._display_csv(path)
            elif item_type == "JSON":
                self._display_json(path)
            elif item_type in ["XLSX", "XLS"]:
                self._display_excel(path)
            elif item_type in ["TXT", "MD", "PY", "SQL", "JS", "HTML", "CSS",
                               "XML", "INI", "CFG", "LOG", "SH", "BAT", "YML", "YAML"]:
                self._display_text(path)
            else:
                # Try to display as text for unknown types
                try:
                    self._display_text(path)
                except Exception:
                    self.viewer_stack.setCurrentWidget(self.empty_viewer)

    def _display_csv(self, file_path: str):
        """
        Display CSV file in grid viewer with automatic encoding/separator detection.

        Args:
            file_path: Path to CSV file
        """
        result = csv_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                self.text_viewer.setPlainText(f"Error loading CSV: {result.error}")
                self.viewer_stack.setCurrentWidget(self.text_viewer)
            return

        df = result.dataframe
        if df is not None and not df.empty:
            # Use set_dataframe if available, otherwise set columns and data
            if hasattr(self.csv_viewer, 'set_dataframe'):
                self.csv_viewer.set_dataframe(df)
            else:
                self.csv_viewer.set_columns(df.columns.tolist())
                self.csv_viewer.set_data(df.values.tolist())

            self.viewer_stack.setCurrentWidget(self.csv_viewer)

            # Log detected format
            encoding = result.source_info.get('encoding', 'unknown')
            separator = result.source_info.get('separator', ',')
            logger.info(f"CSV loaded: {result.row_count} rows, encoding={encoding}, sep='{separator}'")
        else:
            self.text_viewer.setPlainText(tr("empty_csv_file"))
            self.viewer_stack.setCurrentWidget(self.text_viewer)

    def _handle_large_dataset_warning(self, row_count: int) -> bool:
        """
        Handle warning for large datasets.

        Args:
            row_count: Number of rows detected

        Returns:
            True to proceed with loading, False to cancel
        """
        row_count_fmt = f"{row_count:,}"
        threshold_fmt = f"{LARGE_DATASET_THRESHOLD:,}"

        result = QMessageBox.warning(
            self,
            tr("large_dataset_warning"),
            tr("large_dataset_message").format(
                rows=row_count_fmt,
                threshold=threshold_fmt
            ) if tr("large_dataset_message") != "large_dataset_message" else
            f"This file contains {row_count_fmt} rows.\n\n"
            f"Loading more than {threshold_fmt} rows may be slow.\n"
            f"Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return result == QMessageBox.StandardButton.Yes

    def _display_text(self, file_path: str):
        """
        Display text file in text viewer with automatic encoding detection.

        Args:
            file_path: Path to text file
        """
        content = read_file_content(Path(file_path))

        if content is None:
            self.text_viewer.setPlainText(tr("error_reading_file"))
            self.viewer_stack.setCurrentWidget(self.text_viewer)
            return

        self.text_viewer.setPlainText(content)
        self.viewer_stack.setCurrentWidget(self.text_viewer)

    def _display_json(self, file_path: str):
        """
        Display JSON file - as table if array of objects, otherwise as formatted text.

        Args:
            file_path: Path to JSON file
        """
        # First, try loading as tabular data (array of objects/rows)
        result = json_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        # If successfully loaded as table with multiple rows, show in grid
        if result.success and result.dataframe is not None and len(result.dataframe) > 1:
            df = result.dataframe
            if hasattr(self.csv_viewer, 'set_dataframe'):
                self.csv_viewer.set_dataframe(df)
            else:
                self.csv_viewer.set_columns(df.columns.tolist())
                self.csv_viewer.set_data(df.values.tolist())

            self.viewer_stack.setCurrentWidget(self.csv_viewer)
            logger.info(f"JSON loaded as table: {result.row_count} rows")
            return

        # Fallback: display as formatted JSON text
        content = read_file_content(Path(file_path))
        if content is None:
            self.text_viewer.setPlainText(tr("error_reading_file"))
            self.viewer_stack.setCurrentWidget(self.text_viewer)
            return

        try:
            data = json.loads(content)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.text_viewer.setPlainText(formatted)
        except json.JSONDecodeError:
            # If JSON parsing fails, show as-is
            self.text_viewer.setPlainText(content)

        self.viewer_stack.setCurrentWidget(self.text_viewer)

    def _display_excel(self, file_path: str):
        """
        Display Excel file in grid viewer.

        Args:
            file_path: Path to Excel file (.xlsx, .xls)
        """
        result = excel_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            error_msg = str(result.error) if result.error else tr("error_loading_excel")
            if "openpyxl" in error_msg.lower() or "xlrd" in error_msg.lower():
                self.text_viewer.setPlainText(
                    "Module openpyxl not installed.\n"
                    "Install with: pip install openpyxl"
                )
            else:
                self.text_viewer.setPlainText(f"Error: {error_msg}")
            self.viewer_stack.setCurrentWidget(self.text_viewer)
            return

        df = result.dataframe
        if df is not None and not df.empty:
            if hasattr(self.csv_viewer, 'set_dataframe'):
                self.csv_viewer.set_dataframe(df)
            else:
                self.csv_viewer.set_columns(df.columns.tolist())
                self.csv_viewer.set_data(df.values.tolist())

            self.viewer_stack.setCurrentWidget(self.csv_viewer)
            sheets = result.source_info.get('available_sheets', [])
            logger.info(f"Excel loaded: {result.row_count} rows, sheets={sheets}")
        else:
            self.text_viewer.setPlainText(tr("empty_excel_file"))
            self.viewer_stack.setCurrentWidget(self.text_viewer)

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
        # Get selected project (if any)
        selected_project_id = None
        if self._current_item:
            item_data = self._wrap_item()
            if item_data:
                obj_data = item_data.get("obj")
                if obj_data and hasattr(obj_data, "type") and obj_data.type == "Project":
                    selected_project_id = obj_data.id

        # Open dialog to add file root
        dialog = EditRootFolderDialog(self)
        if dialog.exec():
            name, description, path = dialog.get_values()

            if not path:
                DialogHelper.warning(
                    tr("path_required"),
                    tr("add_file_root_title"),
                    self
                )
                return

            # Create FileRoot object
            try:
                import uuid
                config_db = get_config_db()
                file_root = FileRoot(
                    id=str(uuid.uuid4()),
                    path=path,
                    name=name or Path(path).name,
                    description=description
                )
                config_db._save_file_root(file_root)

                DialogHelper.info(
                    tr("file_root_added"),
                    tr("add_file_root_title"),
                    self
                )
                self.refresh()

            except Exception as e:
                logger.error(f"Error adding file root: {e}")
                DialogHelper.error(
                    tr("error_adding_file_root"),
                    tr("error_title"),
                    self,
                    details=str(e)
                )

    def _delete_item(self):
        """Delete selected item."""
        if not self._check_item_selected(tr("select_item_first"), tr("delete_item_title")):
            return

        item_name = self._get_item_name()

        if DialogHelper.confirm(
            tr("confirm_delete_item").format(name=item_name),
            tr("delete_item_title"),
            self
        ):
            # TODO: Delete from database
            # config_db.delete_item(self._current_item.id)
            # self.refresh()
            DialogHelper.info(tr("item_deleted"), tr("delete_item_title"), self)

    def _open_location(self):
        """Open file location in system file explorer."""
        if not self._check_item_selected(tr("select_item_first"), tr("open_location_title")):
            return

        path = self._wrap_item().get_str("path")

        if not path:
            DialogHelper.warning(tr("no_path_for_item"), tr("open_location_title"), self)
            return

        file_path = Path(path)
        if not file_path.exists():
            DialogHelper.warning(
                tr("path_not_found"),
                tr("open_location_title"),
                self
            )
            return

        try:
            if sys.platform == 'win32':
                # Windows: open explorer and select the file
                if file_path.is_file():
                    subprocess.run(['explorer', '/select,', str(file_path)], check=False)
                else:
                    subprocess.run(['explorer', str(file_path)], check=False)
            elif sys.platform == 'darwin':
                # macOS: open Finder and select the file
                if file_path.is_file():
                    subprocess.run(['open', '-R', str(file_path)], check=False)
                else:
                    subprocess.run(['open', str(file_path)], check=False)
            else:
                # Linux: open file manager (xdg-open opens the parent folder)
                folder = file_path.parent if file_path.is_file() else file_path
                subprocess.run(['xdg-open', str(folder)], check=False)

            logger.info(f"Opened location: {file_path}")

        except Exception as e:
            logger.error(f"Error opening location: {e}")
            DialogHelper.error(
                tr("error_opening_location"),
                tr("error_title"),
                self,
                details=str(e)
            )
