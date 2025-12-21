"""
RootFolder Manager - File browser and viewer for configured root folders
"""

from typing import Optional, List, Dict
from pathlib import Path
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QTreeWidget, QTreeWidgetItem, QLabel, QMenu,
                               QFileDialog, QInputDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QColor, QTextCharFormat, QFont
import re

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.custom_datagridview import CustomDataGridView
from ..widgets.form_builder import FormBuilder
from ..widgets.pinnable_panel import PinnablePanel
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, FileRoot
from ...utils.image_loader import get_icon
from ...utils.file_reader import read_file_content

# DataFrame-Pivot pattern: centralized loading functions
from ...core.data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    excel_to_dataframe,
    DataLoadResult,
    LoadWarningLevel,
    LARGE_DATASET_THRESHOLD
)
# Using CustomDataGridView.set_dataframe() directly for optimal performance

import logging
import uuid
logger = logging.getLogger(__name__)


class RootFolderManager(QWidget):
    """
    Root folder browser and file viewer.

    Layout:
    - TOP: Toolbar (Add RootFolder, Remove RootFolder, Refresh)
    - LEFT: File tree (root folders > folders > files)
    - RIGHT TOP: File details
    - RIGHT BOTTOM: File content (CustomDataGridView for CSV/JSON/Excel)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.config_db = get_config_db()
        self.current_file_path: Optional[Path] = None
        self._loaded = False
        self._current_json_content: Optional[str] = None  # Store raw JSON for view switching
        self._workspace_filter: Optional[str] = None
        self._current_item: Optional[FileRoot] = None

        self._setup_ui()

    def showEvent(self, event):
        """Override showEvent to lazy-load data on first show"""
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            # Load in background to avoid blocking UI
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._load_root_folders)

    # ==================== ManagerProtocol Implementation ====================

    def refresh(self) -> None:
        """Refresh the view (reload root folders from database)."""
        self._load_root_folders()

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        """Set workspace filter and refresh the view."""
        self._workspace_filter = workspace_id
        if self._loaded:
            self.refresh()

    def get_workspace_filter(self) -> Optional[str]:
        """Get current workspace filter."""
        return self._workspace_filter

    def get_current_item(self) -> Optional[FileRoot]:
        """Get currently selected root folder."""
        return self._current_item

    def clear_selection(self) -> None:
        """Clear current selection."""
        self._current_item = None
        self.file_tree.clearSelection()

    # ==================== UI Setup ====================

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button("➕ Add RootFolder", self._add_rootfolder, icon="add.png")
        toolbar_builder.add_button("🗑️ Remove RootFolder", self._remove_rootfolder, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_refresh"), self._refresh, icon="refresh.png")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter (left: tree, right: details + content)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Pinnable panel with file explorer tree
        self.left_panel = PinnablePanel(
            title="RootFolders",
            icon_name="RootFolders.png"
        )
        self.left_panel.set_normal_width(280)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setIndentation(20)
        self.file_tree.setRootIsDecorated(False)  # No branch decoration for root items
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.file_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.file_tree.itemClicked.connect(self._on_tree_click)
        self.file_tree.itemExpanded.connect(self._on_item_expanded)  # Lazy loading
        tree_layout.addWidget(self.file_tree)

        self.left_panel.set_content(tree_container)
        main_splitter.addWidget(self.left_panel)

        # Right panel: Details (top) + Content (bottom)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Right top: File details
        self.details_form_builder = FormBuilder(title="File Details") \
            .add_field("Name:", "name") \
            .add_field("Type:", "type") \
            .add_field("Size:", "size") \
            .add_field("Modified:", "modified") \
            .add_field("Path:", "path")

        details_form_widget = self.details_form_builder.build()
        right_layout.addWidget(details_form_widget, stretch=1)

        # Right bottom: File content viewer
        content_header = QHBoxLayout()
        content_label = QLabel("File Content")
        content_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        content_header.addWidget(content_label)

        # View mode toggle (for JSON files)
        from PySide6.QtWidgets import QComboBox
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItem("📊 Table View", "table")
        self.view_mode_combo.addItem("📄 Raw JSON", "raw")
        self.view_mode_combo.setVisible(False)  # Hidden by default, shown for JSON
        self.view_mode_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        content_header.addWidget(self.view_mode_combo)
        content_header.addStretch()

        right_layout.addLayout(content_header)

        # Stacked widget to switch between grid and text views
        from PySide6.QtWidgets import QStackedWidget, QTextEdit
        self.content_stack = QStackedWidget()

        # Grid view (for CSV, JSON table, Excel)
        self.content_viewer = CustomDataGridView()
        self.content_stack.addWidget(self.content_viewer)

        # Text view (for raw JSON, raw text, log files)
        self.text_viewer = QTextEdit()
        self.text_viewer.setReadOnly(True)
        # Note: Styling will be applied dynamically based on theme
        # when displaying log files via _apply_text_viewer_theme()
        self.content_stack.addWidget(self.text_viewer)

        right_layout.addWidget(self.content_stack, stretch=4)

        main_splitter.addWidget(right_widget)

        # Set splitter proportions (left 30%, right 70%)
        main_splitter.setSizes([350, 850])

        layout.addWidget(main_splitter)

    def _load_root_folders(self):
        """Load all root folders into tree"""
        self.file_tree.clear()

        # Apply workspace filter if set
        if self._workspace_filter:
            root_folders = self.config_db.get_workspace_file_roots(self._workspace_filter)
        else:
            root_folders = self.config_db.get_all_file_roots()

        for root_folder in root_folders:
            self._add_rootfolder_to_tree(root_folder)

    def _count_files_in_folder(self, folder_path: Path) -> int:
        """
        Count all files (not folders) recursively in a folder.

        Args:
            folder_path: Path to the folder to count files in

        Returns:
            Total count of files in the folder and all subfolders
        """
        count = 0
        try:
            for item in folder_path.rglob("*"):
                if item.is_file():
                    count += 1
        except PermissionError:
            pass  # Skip folders we can't access
        except Exception as e:
            logger.warning(f"Error counting files in {folder_path}: {e}")
        return count

    def _add_rootfolder_to_tree(self, root_folder: FileRoot):
        """Add a root folder and its contents to the tree"""
        root_path = Path(root_folder.path)

        if not root_path.exists():
            logger.warning(f"RootFolder path does not exist: {root_path}")
            return

        # Create root item
        root_item = QTreeWidgetItem(self.file_tree)

        # Icon for root folder
        root_icon = get_icon("RootFolders.png", size=16)
        if root_icon:
            root_item.setIcon(0, root_icon)

        # Count files recursively for display
        file_count = self._count_files_in_folder(root_path)
        display_name = root_folder.name or root_path.name
        root_item.setText(0, f"{display_name} ({file_count})")
        root_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "rootfolder",
            "rootfolder_obj": root_folder,  # Store complete FileRoot object
            "id": root_folder.id,
            "path": str(root_path),
            "name": root_folder.name or root_path.name
        })

        # Load children (only direct contents, not recursive)
        self._load_folder_contents(root_item, root_path, recursive=False)

    def _load_folder_contents(self, parent_item: QTreeWidgetItem, folder_path: Path, recursive: bool = True):
        """Load contents of a folder (subfolders and files)"""
        try:
            # Sort: folders first, then files
            entries = sorted(folder_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

            for entry in entries:
                if entry.is_dir():
                    # Folder
                    folder_item = QTreeWidgetItem(parent_item)

                    # Icon for folder
                    folder_icon = get_icon("folder.png", size=16)
                    if folder_icon:
                        folder_item.setIcon(0, folder_icon)

                    # Count files in folder for display
                    file_count = self._count_files_in_folder(entry)
                    folder_item.setText(0, f"{entry.name} ({file_count})")
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "folder",
                        "path": str(entry),
                        "name": entry.name
                    })

                    # Only load subfolders recursively if requested
                    if recursive:
                        self._load_folder_contents(folder_item, entry, recursive=True)
                    else:
                        # Add a dummy child to show the expand arrow (lazy loading)
                        dummy = QTreeWidgetItem(folder_item)
                        dummy.setText(0, "Loading...")
                        dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})

                elif entry.is_file():
                    # File
                    file_item = QTreeWidgetItem(parent_item)

                    # Icon based on file extension
                    file_icon = self._get_file_icon(entry)
                    if file_icon:
                        file_item.setIcon(0, file_icon)

                    file_item.setText(0, entry.name)
                    file_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "file",
                        "path": str(entry),
                        "name": entry.name,
                        "extension": entry.suffix.lower()
                    })

        except PermissionError:
            logger.warning(f"Permission denied: {folder_path}")
        except Exception as e:
            logger.error(f"Error loading folder contents: {e}")

    def _count_files_recursive(self, folder_path: Path) -> int:
        """Count total number of files in folder (including subfolders)"""
        try:
            count = 0
            for entry in folder_path.rglob('*'):
                if entry.is_file():
                    count += 1
            return count
        except (OSError, PermissionError):
            return 0

    def _get_file_icon(self, file_path: Path) -> Optional[QIcon]:
        """Get icon based on file extension"""
        extension = file_path.suffix.lower()

        icon_map = {
            '.csv': 'csv.png',
            '.json': 'json.png',
            '.xlsx': 'excel.png',
            '.xls': 'excel.png',
            '.txt': 'text.png',
            '.xml': 'xml.png',
            '.sql': 'sql.png',
            '.py': 'python.png',
            '.md': 'markdown.png',
        }

        icon_name = icon_map.get(extension, 'file.png')
        return get_icon(icon_name, size=16)

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion (lazy loading)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        # Check if this folder has a dummy "Loading..." child
        if item.childCount() == 1:
            first_child = item.child(0)
            child_data = first_child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("type") == "dummy":
                # Remove dummy
                item.removeChild(first_child)

                # Load real contents
                if data["type"] in ["folder", "rootfolder"]:
                    folder_path = Path(data["path"])
                    self._load_folder_contents(item, folder_path, recursive=False)

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        """Handle single click on tree item (show details)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data["type"] == "rootfolder":
            self._show_rootfolder_details(data["rootfolder_obj"])
        elif data["type"] == "file":
            self._show_file_details(Path(data["path"]))

    def _on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item (open file)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data["type"] == "file":
            self._open_file(Path(data["path"]))

    def _show_file_details(self, file_path: Path):
        """Show file details in the details panel"""
        try:
            stat = file_path.stat()

            # Format size
            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.2f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
            else:
                size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

            # Format modified date
            from datetime import datetime
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            # File type
            file_type = file_path.suffix.upper()[1:] if file_path.suffix else "File"

            # Update details form
            self.details_form_builder.set_value("name", file_path.name)
            self.details_form_builder.set_value("type", file_type)
            self.details_form_builder.set_value("size", size_str)
            self.details_form_builder.set_value("modified", modified)
            self.details_form_builder.set_value("path", str(file_path))

        except Exception as e:
            logger.error(f"Error showing file details: {e}")

    def _show_rootfolder_details(self, rootfolder: FileRoot):
        """Show root folder details in the details panel"""
        try:
            root_path = Path(rootfolder.path)

            # Format dates
            from datetime import datetime
            created = datetime.fromisoformat(rootfolder.created_at).strftime("%Y-%m-%d %H:%M:%S") if rootfolder.created_at else "N/A"
            modified = datetime.fromisoformat(rootfolder.updated_at).strftime("%Y-%m-%d %H:%M:%S") if rootfolder.updated_at else "N/A"

            # Update details form
            self.details_form_builder.set_value("name", rootfolder.name or root_path.name)
            self.details_form_builder.set_value("type", "Root Folder")
            self.details_form_builder.set_value("size", "-")
            self.details_form_builder.set_value("modified", modified)
            self.details_form_builder.set_value("path", str(root_path))

            # Clear content viewer
            self.content_viewer.clear()

        except Exception as e:
            logger.error(f"Error showing root folder details: {e}")

    def _open_file(self, file_path: Path):
        """Open and display file content"""
        try:
            self.current_file_path = file_path
            extension = file_path.suffix.lower()

            # Read file content
            content = read_file_content(file_path)

            if content is None:
                DialogHelper.warning(f"Cannot read file: {file_path.name}")
                return

            # Display based on type
            if extension == '.csv':
                self.view_mode_combo.setVisible(False)
                self._display_csv(content)
            elif extension == '.json':
                self.view_mode_combo.setVisible(True)
                self.view_mode_combo.setCurrentIndex(0)  # Default to table view
                self._current_json_content = content
                self._display_json(content)
            elif extension in ['.xlsx', '.xls']:
                self.view_mode_combo.setVisible(False)
                self._display_excel(file_path)
            elif extension == '.log':
                self.view_mode_combo.setVisible(False)
                self._display_log_file(file_path)
            elif extension in ['.txt', '.py', '.sql', '.md', '.ini', '.cfg', '.xml', '.html', '.css', '.js']:
                self.view_mode_combo.setVisible(False)
                self._display_text_file(content)
            else:
                self.view_mode_combo.setVisible(False)
                # Try as text for unknown types
                self._display_text_file(content)

        except Exception as e:
            logger.error(f"Error opening file: {e}")
            DialogHelper.error("Error opening file", details=str(e))

    def _display_csv(self, content: str):
        """Display CSV content in grid using DataFrame-Pivot pattern"""
        # Use centralized data_loader
        result = csv_to_dataframe(
            self.current_file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                DialogHelper.error("Error loading CSV", details=str(result.error))
            return

        # Display warning if there was one (but user chose to proceed)
        if result.warning_level == LoadWarningLevel.WARNING and result.warning_message:
            logger.warning(result.warning_message)

        # Use centralized data_viewer to populate the grid
        df = result.dataframe
        if df is not None and not df.empty:
            # Update source info in details
            encoding = result.source_info.get('encoding', 'unknown')
            separator = result.source_info.get('separator', ',')
            sep_display = {',' : 'comma', ';': 'semicolon', '\t': 'tab', '|': 'pipe'}.get(separator, separator)

            # Log info
            logger.info(f"CSV loaded: {result.row_count} rows, encoding={encoding}, separator={sep_display}")

            # Populate grid using optimized set_dataframe method
            self.content_viewer.set_dataframe(df)
        else:
            self.content_viewer.clear()

    def _on_view_mode_changed(self, index: int):
        """Handle view mode change for JSON files"""
        if self._current_json_content is None:
            return

        view_mode = self.view_mode_combo.currentData()

        if view_mode == "table":
            self.content_stack.setCurrentWidget(self.content_viewer)
            self._display_json_table(self._current_json_content)
        elif view_mode == "raw":
            self.content_stack.setCurrentWidget(self.text_viewer)
            self._display_json_raw(self._current_json_content)

    def _display_json(self, content: str):
        """Display JSON content (default to table view)"""
        view_mode = self.view_mode_combo.currentData()

        if view_mode == "raw":
            self.content_stack.setCurrentWidget(self.text_viewer)
            self._display_json_raw(content)
        else:
            self.content_stack.setCurrentWidget(self.content_viewer)
            self._display_json_table(content)

    def _display_json_table(self, content: str):
        """Display JSON content as table in grid using DataFrame-Pivot pattern"""
        # Use centralized data_loader
        result = json_to_dataframe(
            self.current_file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                # Fallback to legacy display for complex JSON structures
                self._display_json_table_legacy(content)
            return

        # Display warning if there was one (but user chose to proceed)
        if result.warning_level == LoadWarningLevel.WARNING and result.warning_message:
            logger.warning(result.warning_message)

        # Use optimized set_dataframe to populate the grid
        df = result.dataframe
        if df is not None and not df.empty:
            logger.info(f"JSON loaded: {result.row_count} rows, {result.column_count} cols")
            self.content_viewer.set_dataframe(df)
        else:
            # Fallback to legacy for non-tabular JSON
            self._display_json_table_legacy(content)

    def _display_json_table_legacy(self, content: str):
        """Fallback for complex JSON structures that don't fit DataFrame model"""
        import json

        try:
            data = json.loads(content)

            # For non-tabular JSON, display as key-value pairs
            headers = ["Key", "Value"]
            rows = []

            def flatten_json(obj, prefix=''):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        full_key = f"{prefix}.{key}" if prefix else key
                        if isinstance(value, (dict, list)):
                            flatten_json(value, full_key)
                        else:
                            rows.append([full_key, str(value)])
                elif isinstance(obj, list):
                    for i, value in enumerate(obj):
                        full_key = f"{prefix}[{i}]"
                        if isinstance(value, (dict, list)):
                            flatten_json(value, full_key)
                        else:
                            rows.append([full_key, str(value)])

            flatten_json(data)

            self.content_viewer.set_columns(headers)
            self.content_viewer.set_data(rows)

        except Exception as e:
            logger.error(f"Error displaying JSON (legacy): {e}")
            DialogHelper.error("Error displaying JSON", details=str(e))

    def _display_json_raw(self, content: str):
        """Display JSON content as formatted raw text"""
        import json

        try:
            # Parse and re-format JSON for pretty display
            data = json.loads(content)
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)

            # Display in text viewer (QTextEdit)
            self.text_viewer.setPlainText(formatted_json)

        except Exception as e:
            logger.error(f"Error displaying raw JSON: {e}")
            DialogHelper.error("Error displaying raw JSON", details=str(e))

    def _display_excel(self, file_path: Path):
        """Display Excel content in grid using DataFrame-Pivot pattern"""
        # Use centralized data_loader
        result = excel_to_dataframe(
            file_path,
            on_large_dataset=self._handle_large_dataset_warning
        )

        if not result.success:
            if result.error:
                DialogHelper.error("Error loading Excel", details=str(result.error))
            return

        # Display warning if there was one (but user chose to proceed)
        if result.warning_level == LoadWarningLevel.WARNING and result.warning_message:
            logger.warning(result.warning_message)

        # Use optimized set_dataframe to populate the grid
        df = result.dataframe
        if df is not None and not df.empty:
            # Log sheet info
            sheets = result.source_info.get('available_sheets', [])
            current_sheet = result.source_info.get('sheet', 0)
            logger.info(f"Excel loaded: {result.row_count} rows, sheet={current_sheet}, available={sheets}")

            self.content_viewer.set_dataframe(df)
        else:
            self.content_viewer.clear()

    def _display_text_file(self, content: str):
        """Display text file content in text viewer."""
        self._apply_text_viewer_theme()
        self.text_viewer.setFont(QFont("Consolas", 10))
        self.text_viewer.setPlainText(content)
        self.content_stack.setCurrentWidget(self.text_viewer)

    def _display_log_file(self, file_path: Path):
        """Display log file with themed coloring based on log levels."""
        # Read file with proper encoding
        content = read_file_content(file_path)
        if content is None:
            self.text_viewer.setPlainText("(Cannot read file)")
            self.content_stack.setCurrentWidget(self.text_viewer)
            return

        lines = content.splitlines(keepends=True)

        # Get theme colors for log levels and apply theme to text viewer
        log_colors = self._get_log_colors()
        self._apply_text_viewer_theme()

        # Clear and prepare text viewer
        self.text_viewer.clear()
        self.text_viewer.setFont(QFont("Consolas", 10))

        # Pattern to detect log level in a line
        level_pattern = re.compile(
            r'\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|SUCCESS|FATAL)\b',
            re.IGNORECASE
        )

        # Process each line with appropriate color
        cursor = self.text_viewer.textCursor()
        for line in lines:
            # Detect log level
            match = level_pattern.search(line)
            if match:
                level = match.group(1).upper()
                # Normalize WARN -> WARNING, FATAL -> CRITICAL
                if level == "WARN":
                    level = "WARNING"
                elif level == "FATAL":
                    level = "CRITICAL"
                color = log_colors.get(level, log_colors.get("INFO"))
            else:
                # Default color for lines without level
                color = log_colors.get("INFO")

            # Create format with color
            fmt = QTextCharFormat()
            fmt.setForeground(color)

            # Insert line with color
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(line, fmt)

        self.content_stack.setCurrentWidget(self.text_viewer)

    def _apply_text_viewer_theme(self):
        """Apply theme colors to the text viewer background."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            theme_colors = theme.get_theme_colors()

            log_bg = theme_colors.get("log_bg", theme_colors.get("editor_bg", "#1e1e1e"))
            log_fg = theme_colors.get("log_fg", theme_colors.get("editor_fg", "#d4d4d4"))

            self.text_viewer.setStyleSheet(f"""
                QTextEdit {{
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 10pt;
                    background-color: {log_bg};
                    color: {log_fg};
                }}
            """)
        except Exception as e:
            logger.error(f"Error applying text viewer theme: {e}")
            # Fallback to default dark colors
            self.text_viewer.setStyleSheet("""
                QTextEdit {
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 10pt;
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
            """)

    def _get_log_colors(self) -> dict:
        """Get themed colors for log levels."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            theme_colors = theme.get_theme_colors()

            # Log current theme for debugging
            current = getattr(theme, 'current_theme', 'unknown')
            logger.debug(f"Loading log colors from theme: {current}")
            logger.debug(f"log_info_fg={theme_colors.get('log_info_fg')}, "
                        f"log_warning_fg={theme_colors.get('log_warning_fg')}, "
                        f"log_error_fg={theme_colors.get('log_error_fg')}")

            return {
                "DEBUG": QColor(theme_colors.get("log_debug_fg", "#888888")),
                "INFO": QColor(theme_colors.get("log_info_fg", "#ffffff")),
                "WARNING": QColor(theme_colors.get("log_warning_fg", "#ffa500")),
                "ERROR": QColor(theme_colors.get("log_error_fg", "#ff4444")),
                "CRITICAL": QColor(theme_colors.get("log_error_fg", "#ff4444")),
                "SUCCESS": QColor(theme_colors.get("log_success_fg", "#4ade80")),
            }
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error loading log colors from theme: {e}", exc_info=True)
            # Fallback colors
            return {
                "DEBUG": QColor("#888888"),
                "INFO": QColor("#ffffff"),
                "WARNING": QColor("#ffa500"),
                "ERROR": QColor("#ff4444"),
                "CRITICAL": QColor("#ff4444"),
                "SUCCESS": QColor("#4ade80"),
            }

    def _handle_large_dataset_warning(self, row_count: int) -> bool:
        """
        Handle warning for large datasets (> 100k rows).

        Args:
            row_count: Number of rows detected

        Returns:
            True to proceed with loading, False to cancel
        """
        from PySide6.QtWidgets import QMessageBox

        # Format numbers with thousands separator
        row_count_fmt = f"{row_count:,}"
        threshold_fmt = f"{LARGE_DATASET_THRESHOLD:,}"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Large Dataset Warning")
        msg.setText(f"This file contains {row_count_fmt} rows.")
        msg.setInformativeText(
            f"Loading more than {threshold_fmt} rows may:\n"
            f"• Be slow to load\n"
            f"• Consume significant memory\n"
            f"• Slow down the interface\n\n"
            f"Do you want to continue?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        result = msg.exec()
        return result == QMessageBox.StandardButton.Yes

    def _on_tree_context_menu(self, position):
        """Show context menu for tree item"""
        item = self.file_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if data["type"] == "rootfolder":
            # RootFolder context menu
            edit_action = QAction("Edit Name & Description", self)
            edit_action.triggered.connect(lambda: self._edit_rootfolder(data["rootfolder_obj"]))
            menu.addAction(edit_action)

            menu.addSeparator()

            # Add to Workspace submenu
            workspace_menu = self._build_workspace_submenu(data["id"], None)
            menu.addMenu(workspace_menu)

            menu.addSeparator()

            remove_action = QAction("Remove RootFolder", self)
            remove_action.triggered.connect(lambda: self._remove_rootfolder_by_id(data["id"]))
            menu.addAction(remove_action)

            refresh_action = QAction("Refresh", self)
            refresh_action.triggered.connect(self._refresh)
            menu.addAction(refresh_action)

        elif data["type"] == "folder":
            # Folder context menu - can be added to workspace as subfolder
            rootfolder_id, subfolder_path = self._get_rootfolder_info(item)
            if rootfolder_id:
                workspace_menu = self._build_workspace_submenu(rootfolder_id, subfolder_path)
                menu.addMenu(workspace_menu)

        elif data["type"] == "file":
            # File context menu
            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self._open_file(Path(data["path"])))
            menu.addAction(open_action)

            open_location_action = QAction("Open File Location", self)
            open_location_action.triggered.connect(lambda: self._open_file_location(Path(data["path"])))
            menu.addAction(open_location_action)

        menu.exec(self.file_tree.viewport().mapToGlobal(position))

    def _open_file_location(self, file_path: Path):
        """Open file location in file explorer"""
        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                subprocess.run(['explorer', '/select,', str(file_path)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', '-R', str(file_path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(file_path.parent)])
        except Exception as e:
            logger.error(f"Error opening file location: {e}")

    def _add_rootfolder(self):
        """Add a new root folder"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Root Folder",
            str(Path.home())
        )

        if not folder_path:
            return

        try:
            # Create FileRoot
            root_folder = FileRoot(
                id=str(uuid.uuid4()),
                path=folder_path,
                description=""
            )

            # Save to database
            self.config_db._save_file_root(root_folder)

            # Refresh tree
            self._refresh()

            DialogHelper.info(f"RootFolder added: {folder_path}")

        except Exception as e:
            logger.error(f"Error adding RootFolder: {e}")
            DialogHelper.error("Error adding RootFolder", details=str(e))

    def _edit_rootfolder(self, rootfolder: FileRoot):
        """Edit root folder name and description"""
        from ..widgets.edit_dialogs import EditRootFolderDialog

        dialog = EditRootFolderDialog(
            parent=self,
            name=rootfolder.name or Path(rootfolder.path).name,
            description=rootfolder.description or "",
            path=rootfolder.path
        )

        if dialog.exec():
            name, description, path = dialog.get_values()

            if not name:
                DialogHelper.warning("Name cannot be empty")
                return

            try:
                # Update rootfolder
                rootfolder.name = name
                rootfolder.description = description

                # Save to database
                self.config_db._save_file_root(rootfolder)

                # Refresh tree
                self._refresh()

                DialogHelper.info("RootFolder updated successfully")

            except Exception as e:
                logger.error(f"Error updating RootFolder: {e}")
                DialogHelper.error("Error updating RootFolder", details=str(e))

    def _remove_rootfolder(self):
        """Remove selected root folder"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            DialogHelper.warning("Please select a RootFolder to remove")
            return

        item = selected_items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data["type"] == "rootfolder":
            self._remove_rootfolder_by_id(data["id"])
        else:
            DialogHelper.warning("Please select a RootFolder (not a file or subfolder)")

    def _remove_rootfolder_by_id(self, root_id: str):
        """Remove root folder by ID"""
        if not DialogHelper.confirm("Remove this RootFolder?\n\n(The folder itself will not be deleted)"):
            return

        try:
            self.config_db._delete_file_root(root_id)
            self._refresh()
            DialogHelper.info("RootFolder removed")

        except Exception as e:
            logger.error(f"Error removing RootFolder: {e}")
            DialogHelper.error("Error removing RootFolder", details=str(e))

    def get_tree_widget(self):
        """Return the tree widget for embedding in ResourcesManager."""
        return self.file_tree

    def _refresh(self):
        """Refresh the tree"""
        self._load_root_folders()
        self.content_viewer.clear()
        self.details_form_builder.clear()

    # ==================== Workspace Management ====================

    def _get_rootfolder_info(self, item: QTreeWidgetItem) -> tuple:
        """
        Get rootfolder ID and subfolder path for a tree item.

        Args:
            item: The tree item (folder)

        Returns:
            Tuple (rootfolder_id, subfolder_path) or (None, None) if not found
        """
        # Get the folder's full path
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or "path" not in data:
            return None, None

        folder_path = Path(data["path"])

        # Traverse up the tree to find the rootfolder
        current = item.parent()
        while current:
            parent_data = current.data(0, Qt.ItemDataRole.UserRole)
            if parent_data and parent_data.get("type") == "rootfolder":
                rootfolder_id = parent_data["id"]
                rootfolder_obj = parent_data.get("rootfolder_obj")
                if rootfolder_obj:
                    rootfolder_path = Path(rootfolder_obj.path)
                    # Calculate relative path
                    try:
                        subfolder_path = str(folder_path.relative_to(rootfolder_path))
                        return rootfolder_id, subfolder_path
                    except ValueError:
                        # folder_path is not relative to rootfolder_path
                        return rootfolder_id, str(folder_path)
                return rootfolder_id, None
            current = current.parent()

        return None, None

    def _build_workspace_submenu(self, rootfolder_id: str, subfolder_path: Optional[str]) -> QMenu:
        """
        Build a submenu for adding/removing a file root to/from workspaces.

        Args:
            rootfolder_id: ID of the rootfolder
            subfolder_path: Subfolder path relative to rootfolder (None for root)

        Returns:
            QMenu with workspace options
        """
        from ...database.config_db import Workspace

        menu = QMenu(tr("menu_workspaces"), self)

        # Get all workspaces
        workspaces = self.config_db.get_all_workspaces()

        # Get workspaces this resource belongs to
        current_workspaces = self.config_db.get_file_root_workspaces(rootfolder_id, subfolder_path)
        current_workspace_ids = {ws.id for ws in current_workspaces}

        # Add workspace options
        for ws in workspaces:
            is_in_workspace = ws.id in current_workspace_ids
            action_text = f"✓ {ws.name}" if is_in_workspace else ws.name

            action = QAction(action_text, self)
            action.triggered.connect(
                lambda checked, wid=ws.id, rid=rootfolder_id, sp=subfolder_path, in_ws=is_in_workspace:
                    self._toggle_workspace(wid, rid, sp, in_ws)
            )
            menu.addAction(action)

        # Separator and New Workspace option
        if workspaces:
            menu.addSeparator()

        new_action = QAction("+ " + tr("menu_workspaces_manage").replace("...", ""), self)
        new_action.triggered.connect(
            lambda: self._create_new_workspace_and_add(rootfolder_id, subfolder_path)
        )
        menu.addAction(new_action)

        return menu

    def _toggle_workspace(self, workspace_id: str, rootfolder_id: str, subfolder_path: Optional[str], is_in_workspace: bool):
        """Toggle a file root in/out of a workspace"""
        try:
            if is_in_workspace:
                self.config_db.remove_file_root_from_workspace(workspace_id, rootfolder_id)
            else:
                self.config_db.add_file_root_to_workspace(workspace_id, rootfolder_id, subfolder_path)

            logger.info(f"{'Removed from' if is_in_workspace else 'Added to'} workspace: rootfolder {rootfolder_id} subfolder {subfolder_path}")

        except Exception as e:
            logger.error(f"Error toggling workspace: {e}")
            DialogHelper.error("Error updating workspace", details=str(e))

    def _create_new_workspace_and_add(self, rootfolder_id: str, subfolder_path: Optional[str]):
        """Create a new workspace and add the file root to it"""
        from ...database.config_db import Workspace

        name, ok = QInputDialog.getText(self, "New Workspace", "Workspace name:")
        if ok and name.strip():
            ws = Workspace(
                id=str(uuid.uuid4()),
                name=name.strip(),
                description=""
            )

            if self.config_db.add_workspace(ws):
                # Add resource to the new workspace
                self._toggle_workspace(ws.id, rootfolder_id, subfolder_path, False)
                logger.info(f"Created workspace '{ws.name}' and added rootfolder")
            else:
                DialogHelper.warning("Failed to create workspace. Name may already exist.")
