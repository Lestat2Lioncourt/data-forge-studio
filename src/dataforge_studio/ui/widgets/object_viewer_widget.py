"""
ObjectViewerWidget - Unified object viewer for Resources and Workspace managers.

This widget provides a consistent viewing experience across all managers for:
- Files (CSV, JSON, Excel, text, log)
- Database tables and saved queries
- Scripts
- Jobs
- Database connections

Each object type has its own specialized viewer, but the API is unified.
"""

from pathlib import Path
from typing import Optional, Any
import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtCore import Signal

from .file_viewer_widget import FileViewerWidget
from .data_viewer_widget import DataViewerWidget

logger = logging.getLogger(__name__)


class ObjectViewerWidget(QWidget):
    """
    Unified object viewer that dispatches to specialized viewers.

    Usage:
        viewer = ObjectViewerWidget()
        viewer.show_file(Path("/path/to/file.csv"))
        viewer.show_table(connection, "users")
        viewer.show_query(saved_query)
    """

    # Signals
    object_displayed = Signal(str, object)  # (object_type, object_data)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_type: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI with stacked widget containing all viewers."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stacked widget to switch between viewer types
        self.stack = QStackedWidget()

        # Initialize all viewers
        self.file_viewer = FileViewerWidget()
        self.data_viewer = DataViewerWidget()
        # Future: self.script_viewer = ScriptViewerWidget()
        # Future: self.job_viewer = JobViewerWidget()
        # Future: self.connection_viewer = ConnectionViewerWidget()

        # Add to stack
        self.stack.addWidget(self.file_viewer)      # Index 0
        self.stack.addWidget(self.data_viewer)      # Index 1

        layout.addWidget(self.stack)

    # ==================== File Methods ====================

    def show_file(self, file_path: Path):
        """
        Display a file (CSV, JSON, Excel, text, log, etc.).

        Args:
            file_path: Path to the file
        """
        self._current_type = "file"
        self.file_viewer.load_file(file_path)
        self.stack.setCurrentWidget(self.file_viewer)
        self.object_displayed.emit("file", file_path)

    def show_folder(self, name: str, path: str, modified: str = "-"):
        """
        Display folder details (no content).

        Args:
            name: Folder name
            path: Folder path
            modified: Last modified date
        """
        self._current_type = "folder"
        self.file_viewer.show_folder_details(name, path, modified)
        self.stack.setCurrentWidget(self.file_viewer)
        self.object_displayed.emit("folder", {"name": name, "path": path})

    # ==================== Database Methods ====================

    def show_table(self, connection: Any, table_name: str, schema: str = None, db_type: str = None):
        """
        Display a database table (exploration mode).

        Args:
            connection: Database connection object
            table_name: Name of the table
            schema: Optional schema name (or db_name for SQL Server)
            db_type: Database type (sqlite, sqlserver, postgresql, etc.)
        """
        self._current_type = "table"
        self.data_viewer.show_table(connection, table_name, schema, db_type)
        self.stack.setCurrentWidget(self.data_viewer)
        self.object_displayed.emit("table", {"connection": connection, "table": table_name})

    def show_query(self, query: Any, connection: Any = None):
        """
        Display a saved query with its details.

        Args:
            query: SavedQuery object
            connection: Optional database connection for execution
        """
        self._current_type = "query"
        self.data_viewer.show_query(query, connection)
        self.stack.setCurrentWidget(self.data_viewer)
        self.object_displayed.emit("query", query)

    def show_query_results(self, sql: str, connection: Any, query: Any = None):
        """
        Execute and display query results.

        Args:
            sql: SQL query string
            connection: Database connection
            query: Optional SavedQuery object for details tab
        """
        self._current_type = "query_results"
        self.data_viewer.execute_query(sql, connection, query)
        self.stack.setCurrentWidget(self.data_viewer)
        self.object_displayed.emit("query_results", {"sql": sql, "query": query})

    # ==================== Script/Job Methods (Future) ====================

    def show_script(self, script: Any):
        """
        Display a script with its details and code.

        Args:
            script: Script object
        """
        self._current_type = "script"
        # Future: self.script_viewer.show_script(script)
        # Future: self.stack.setCurrentWidget(self.script_viewer)
        logger.warning("ScriptViewerWidget not yet implemented")
        self.object_displayed.emit("script", script)

    def show_job(self, job: Any, script: Any = None):
        """
        Display a job with its details and linked script code.

        Args:
            job: Job object
            script: Optional linked Script object
        """
        self._current_type = "job"
        # Future: self.job_viewer.show_job(job, script)
        # Future: self.stack.setCurrentWidget(self.job_viewer)
        logger.warning("JobViewerWidget not yet implemented")
        self.object_displayed.emit("job", job)

    # ==================== Connection Methods (Future) ====================

    def show_connection(self, connection: Any):
        """
        Display database connection details.

        Args:
            connection: DatabaseConnection object
        """
        self._current_type = "connection"
        # Future: self.connection_viewer.show_connection(connection)
        # Future: self.stack.setCurrentWidget(self.connection_viewer)
        logger.warning("ConnectionViewerWidget not yet implemented")
        self.object_displayed.emit("connection", connection)

    # ==================== Generic Details Methods ====================

    def show_details(self, name: str, obj_type: str, description: str = "",
                     created: str = "", updated: str = "", extra_fields: dict = None):
        """
        Show generic details for any object type.

        Args:
            name: Object name
            obj_type: Object type (e.g., "Workspace", "Database", "Query Category")
            description: Description or additional info
            created: Created date string
            updated: Updated date string
            extra_fields: Additional fields as dict {label: value}
        """
        self._current_type = "details"

        # Use file_viewer's details panel for generic details
        if self.file_viewer.details_form_builder:
            self.file_viewer.details_form_builder.set_value("name", name)
            self.file_viewer.details_form_builder.set_value("type", obj_type)
            self.file_viewer.details_form_builder.set_value("size", "-")
            self.file_viewer.details_form_builder.set_value("modified", updated or created or "-")
            self.file_viewer.details_form_builder.set_value("path", description)
            self.file_viewer.details_form_builder.set_value("encoding", "-")
            self.file_viewer.details_form_builder.set_value("separator", "-")
            self.file_viewer.details_form_builder.set_value("delimiter", "-")

        self.file_viewer.clear_content()
        self.stack.setCurrentWidget(self.file_viewer)
        self.object_displayed.emit("details", {"name": name, "type": obj_type})

    # ==================== Utility Methods ====================

    def clear(self):
        """Clear all viewers."""
        self._current_type = None
        self.file_viewer.clear()
        self.data_viewer.clear()

    def get_current_type(self) -> Optional[str]:
        """Get the type of currently displayed object."""
        return self._current_type

    def get_current_viewer(self) -> QWidget:
        """Get the currently active viewer widget."""
        return self.stack.currentWidget()
