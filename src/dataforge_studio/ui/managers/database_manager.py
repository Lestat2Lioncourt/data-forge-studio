"""
Database Manager - Multi-tab SQL query interface with SSMS-style tree

Facade module: assembles DatabaseManager from mixins.
The actual method implementations live in the database/ subpackage.
"""

from __future__ import annotations
from typing import Optional, Dict, Union, TYPE_CHECKING

try:
    import pyodbc
except ImportError:
    pyodbc = None
import sqlite3

if TYPE_CHECKING:
    from .workspace_manager import WorkspaceManager

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QSplitter,
                               QTreeWidget)
from PySide6.QtCore import Qt, Signal

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.pinnable_panel import PinnablePanel
from ..core.i18n_bridge import tr
from ...database.config_db import DatabaseConnection
from ...database.dialects import DatabaseDialect
from ...config.user_preferences import UserPreferences

from .database import (
    DatabaseConnectionWorker,
    DatabaseConnectionMixin,
    DatabaseSchemaMixin,
    DatabaseContextMenuMixin,
    DatabaseQueryGenMixin,
    DatabaseTabMixin,
    DatabaseCrudMixin,
    DatabaseWorkspaceMixin,
    DatabaseImportExportMixin,
)

import logging
logger = logging.getLogger(__name__)


class DatabaseManager(
    DatabaseConnectionMixin,
    DatabaseSchemaMixin,
    DatabaseContextMenuMixin,
    DatabaseQueryGenMixin,
    DatabaseTabMixin,
    DatabaseCrudMixin,
    DatabaseWorkspaceMixin,
    DatabaseImportExportMixin,
    QWidget,
):
    """
    Multi-tab SQL query manager with SSMS-style database explorer.

    Layout:
    - TOP: Toolbar (New Tab, Refresh, etc.)
    - LEFT: Database tree (connections > databases > tables/views > columns)
    - RIGHT: QTabWidget with multiple QueryTab instances
    """

    # Signal emitted when a query is saved in any QueryTab
    query_saved = Signal()
    # Signal emitted when the set of active connections changes
    connections_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.connections: Dict[str, Union[pyodbc.Connection, sqlite3.Connection]] = {}
        self._dialects: Dict[str, DatabaseDialect] = {}  # Database-specific SQL dialects
        self.tab_counter = 1
        self._expand_connected = False
        self._workspace_filter: Optional[str] = None
        self._current_item = None
        self._pending_workers: Dict[str, DatabaseConnectionWorker] = {}  # Track active connection workers
        self._workspace_manager: Optional["WorkspaceManager"] = None

        self._setup_ui()
        self._load_all_connections()

    def set_workspace_manager(self, workspace_manager: "WorkspaceManager"):
        """Set reference to WorkspaceManager for auto-refresh on workspace changes."""
        self._workspace_manager = workspace_manager

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_refresh_schema"), self._refresh_schema, icon="refresh.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("menu_new_connection"), self._new_connection)
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Import", self._import_connections, icon="import.png")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter (left: tree, right: tabs)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(6)  # Larger handle for easier grabbing
        self.main_splitter.setChildrenCollapsible(False)  # Prevent collapsing children

        # Left panel: Pinnable panel with database explorer tree
        self.left_panel = PinnablePanel(
            title="Database Explorer",
            icon_name="database.png"
        )
        self.left_panel.set_normal_width(280)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self.schema_tree = QTreeWidget()
        self.schema_tree.setHeaderHidden(True)
        self.schema_tree.setIndentation(20)
        self.schema_tree.setRootIsDecorated(False)  # No branch decoration for root items
        self.schema_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.schema_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.schema_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        tree_layout.addWidget(self.schema_tree)

        self.left_panel.set_content(tree_container)
        self.main_splitter.addWidget(self.left_panel)

        # Right panel: Query tabs
        from ..widgets.editable_tab_widget import EditableTabWidget
        self.tab_widget = EditableTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.enable_new_tab_button()
        self.tab_widget.newTabRequested.connect(lambda: self._new_query_tab())
        # Set minimum width to prevent it from pushing left panel
        self.tab_widget.setMinimumWidth(200)

        self.main_splitter.addWidget(self.tab_widget)

        # Set splitter proportions (left 25%, right 75%) - default values
        self.main_splitter.setSizes([300, 900])

        # Restore saved splitter sizes from preferences
        self._restore_splitter_sizes()

        # Save splitter sizes when changed
        self.main_splitter.splitterMoved.connect(self._save_splitter_sizes)

        # Allow both panels to be resized freely
        self.main_splitter.setStretchFactor(0, 0)  # Left panel: don't auto-stretch
        self.main_splitter.setStretchFactor(1, 1)  # Right panel: takes remaining space

        layout.addWidget(self.main_splitter)

    def _restore_splitter_sizes(self):
        """Restore splitter sizes from user preferences."""
        try:
            prefs = UserPreferences.instance()
            saved_sizes = prefs.get("db_manager_splitter_sizes")
            if saved_sizes:
                # Parse "300,900" format
                sizes = [int(s) for s in saved_sizes.split(",")]
                if len(sizes) == 2 and all(s > 0 for s in sizes):
                    self.main_splitter.setSizes(sizes)
        except Exception as e:
            logger.debug(f"Could not restore splitter sizes: {e}")

    def _save_splitter_sizes(self):
        """Save splitter sizes to user preferences."""
        try:
            sizes = self.main_splitter.sizes()
            if sizes and len(sizes) == 2:
                prefs = UserPreferences.instance()
                prefs.set("db_manager_splitter_sizes", f"{sizes[0]},{sizes[1]}")
        except Exception as e:
            logger.debug(f"Could not save splitter sizes: {e}")

    def refresh(self):
        """Public refresh method."""
        self._load_all_connections()

    # ==================== ManagerProtocol Implementation ====================

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        """Set workspace filter and refresh the view."""
        self._workspace_filter = workspace_id
        self.refresh()

    def get_workspace_filter(self) -> Optional[str]:
        """Get current workspace filter."""
        return self._workspace_filter

    def get_current_item(self) -> Optional[DatabaseConnection]:
        """Get currently selected database connection."""
        return self._current_item

    def clear_selection(self) -> None:
        """Clear current selection."""
        self._current_item = None
        self.schema_tree.clearSelection()
