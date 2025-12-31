"""
Workspace Manager - Managing workspaces and their resources.

Uses ObjectViewerWidget for unified content display (same as RootFolderManager).
"""

from pathlib import Path
from typing import Optional, TYPE_CHECKING
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QLabel, QMenu, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.tree_populator import TreePopulator
from ..widgets.object_viewer_widget import ObjectViewerWidget
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Workspace, Script
from ...database.models.workspace_resource import WorkspaceFileRoot, WorkspaceDatabase
from ...utils.image_loader import get_icon, get_database_icon
from ...utils.workspace_export import (
    export_workspace_to_json, save_export_to_file, get_export_summary,
    load_import_from_file, check_workspace_conflict, import_workspace_from_json,
    ImportConflictMode, get_import_summary
)

import logging
import uuid
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .database_manager import DatabaseManager
    from .rootfolder_manager import RootFolderManager


class WorkspaceManager(QWidget):
    """
    Workspace manager - browse and manage workspaces and their resources.

    Layout:
    - TOP: Toolbar (New, Rename, Delete, Refresh)
    - LEFT: Tree (workspaces > databases/queries/rootfolders)
    - RIGHT: ObjectViewerWidget (unified content display)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.config_db = get_config_db()
        self._loaded = False
        self._current_workspace_id = None
        self._current_item: Optional[Workspace] = None

        self._database_manager: Optional["DatabaseManager"] = None
        self._rootfolder_manager: Optional["RootFolderManager"] = None

        self._setup_ui()

    def set_managers(
        self,
        database_manager: Optional["DatabaseManager"] = None,
        rootfolder_manager: Optional["RootFolderManager"] = None
    ):
        """Set references to managers for delegation."""
        self._database_manager = database_manager
        self._rootfolder_manager = rootfolder_manager

    def showEvent(self, event):
        """Lazy-load data on first show."""
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._load_workspaces)

    # ==================== ManagerProtocol Implementation ====================

    def refresh(self) -> None:
        self._refresh()

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        pass  # WorkspaceManager doesn't filter by workspace

    def get_workspace_filter(self) -> Optional[str]:
        return None

    def get_current_item(self) -> Optional[Workspace]:
        return self._current_item

    def clear_selection(self) -> None:
        self._current_item = None
        self._current_workspace_id = None
        self.workspace_tree.clearSelection()

    # ==================== UI Setup ====================

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button("+ New", self._new_workspace, icon="add.png")
        toolbar_builder.add_button("Edit", self._edit_workspace, icon="edit.png")
        toolbar_builder.add_button("Delete", self._delete_workspace, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Import", self._import_workspace, icon="import.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_refresh"), self._refresh, icon="refresh.png")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.setChildrenCollapsible(False)

        # Left panel: Workspace tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        tree_label = QLabel(tr("menu_workspaces"))
        tree_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(tree_label)

        self.workspace_tree = QTreeWidget()
        self.workspace_tree.setHeaderHidden(True)
        self.workspace_tree.setIndentation(20)
        self.workspace_tree.setRootIsDecorated(False)
        self.workspace_tree.setExpandsOnDoubleClick(False)
        self.workspace_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.workspace_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.workspace_tree.itemClicked.connect(self._on_tree_click)
        self.workspace_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.workspace_tree.itemExpanded.connect(self._on_item_expanded)
        left_layout.addWidget(self.workspace_tree)

        self.main_splitter.addWidget(left_widget)

        # Right panel: ObjectViewerWidget (unified display)
        self.object_viewer = ObjectViewerWidget()
        self.main_splitter.addWidget(self.object_viewer)

        # Set splitter proportions
        self.main_splitter.setSizes([350, 850])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.main_splitter)

    # ==================== Tree Loading ====================

    def _load_workspaces(self):
        """Load all workspaces into tree."""
        self.workspace_tree.clear()
        workspaces = self.config_db.get_all_workspaces()
        for ws in workspaces:
            self._add_workspace_to_tree(ws)

    def _add_workspace_to_tree(self, workspace: Workspace):
        """Add a workspace to the tree."""
        ws_item = QTreeWidgetItem(self.workspace_tree)
        ws_icon = get_icon("workspace.png", size=16) or get_icon("folder.png", size=16)
        if ws_icon:
            ws_item.setIcon(0, ws_icon)
        ws_item.setText(0, workspace.name)
        ws_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "workspace",
            "id": workspace.id,
            "workspace_obj": workspace
        })
        TreePopulator.add_dummy_child(ws_item)

    def _load_workspace_resources(self, ws_item: QTreeWidgetItem, workspace_id: str):
        """Load resources for a workspace."""
        # Databases
        ws_databases = self.config_db.get_workspace_databases_with_context(workspace_id)
        for ws_db in ws_databases:
            db = ws_db.connection
            db_item = QTreeWidgetItem(ws_item)
            db_icon = get_database_icon(db.db_type, size=16)
            if db_icon:
                db_item.setIcon(0, db_icon)
            db_item.setText(0, ws_db.display_name)
            db_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "database",
                "id": db.id,
                "database_name": ws_db.database_name,
                "resource_obj": db,
                "ws_database": ws_db
            })
            TreePopulator.add_dummy_child(db_item)

        # Queries
        queries = self.config_db.get_workspace_queries(workspace_id)
        if queries:
            self._add_queries_grouped_by_category(ws_item, queries)

        # Scripts
        scripts = self.config_db.get_workspace_scripts(workspace_id)
        if scripts:
            self._add_scripts_grouped_by_type(ws_item, scripts)

        # RootFolders
        ws_file_roots = self.config_db.get_workspace_file_roots_with_context(workspace_id)
        for ws_fr in ws_file_roots:
            fr = ws_fr.file_root
            fr_item = QTreeWidgetItem(ws_item)
            fr_icon = get_icon("RootFolders.png", size=16)
            if fr_icon:
                fr_item.setIcon(0, fr_icon)
            fr_item.setText(0, ws_fr.display_name)

            full_path = Path(fr.path)
            if ws_fr.subfolder_path:
                full_path = full_path / ws_fr.subfolder_path

            fr_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "rootfolder",
                "id": fr.id,
                "subfolder_path": ws_fr.subfolder_path,
                "full_path": str(full_path),
                "resource_obj": fr,
                "ws_file_root": ws_fr
            })
            TreePopulator.add_dummy_child(fr_item)

    def _add_queries_grouped_by_category(self, parent: QTreeWidgetItem, queries: list):
        """Add queries grouped by category."""
        categories = {}
        for q in queries:
            cat = q.category or "Uncategorized"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(q)

        for cat_name, cat_queries in sorted(categories.items()):
            cat_item = QTreeWidgetItem(parent)
            cat_icon = get_icon("folder.png", size=16)
            if cat_icon:
                cat_item.setIcon(0, cat_icon)
            cat_item.setText(0, f"{cat_name} ({len(cat_queries)})")
            cat_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "query_category",
                "name": cat_name
            })

            for query in cat_queries:
                q_item = QTreeWidgetItem(cat_item)
                q_icon = get_icon("query.png", size=16)
                if q_icon:
                    q_item.setIcon(0, q_icon)
                q_item.setText(0, query.name)
                q_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "query",
                    "id": query.id,
                    "resource_obj": query
                })

    def _add_scripts_grouped_by_type(self, parent: QTreeWidgetItem, scripts: list):
        """Add scripts grouped by type."""
        types = {}
        for s in scripts:
            stype = s.script_type or "Other"
            if stype not in types:
                types[stype] = []
            types[stype].append(s)

        for type_name, type_scripts in sorted(types.items()):
            type_item = QTreeWidgetItem(parent)
            type_icon = get_icon("folder.png", size=16)
            if type_icon:
                type_item.setIcon(0, type_icon)
            type_item.setText(0, f"{type_name} ({len(type_scripts)})")
            type_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "script_type",
                "name": type_name
            })

            for script in type_scripts:
                s_item = QTreeWidgetItem(type_item)
                s_icon = get_icon("script.png", size=16)
                if s_icon:
                    s_item.setIcon(0, s_icon)
                s_item.setText(0, script.name)
                s_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "script",
                    "id": script.id,
                    "resource_obj": script
                })

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion (lazy loading)."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if not TreePopulator.has_dummy_child(item):
            return

        TreePopulator.remove_dummy_child(item)
        item_type = data.get("type", "")

        if item_type == "workspace":
            self._load_workspace_resources(item, data["id"])
        elif item_type == "database":
            self._load_database_schema(item, data)
        elif item_type == "rootfolder":
            self._load_rootfolder_contents(item, data)
        elif item_type == "folder":
            # Load folder contents with file counts (same as RootFolderManager)
            folder_path = data.get("path")
            if folder_path:
                self._load_folder_contents(item, Path(folder_path), recursive=False)
        elif item_type in ["tables_folder", "views_folder", "procedures_folder", "functions_folder"]:
            pass  # Database schema folders - already loaded

    def _load_database_schema(self, db_item: QTreeWidgetItem, data: dict):
        """Load database schema using DatabaseManager."""
        if not self._database_manager:
            return

        db_id = data.get("id")
        database_name = data.get("database_name")
        db_conn = data.get("resource_obj")

        if not db_conn:
            return

        connection = self._database_manager.connections.get(db_id)
        if not connection:
            try:
                connection = self._database_manager.connect_to_database(db_id)
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
                return

        if not connection:
            return

        # Load schema
        try:
            if db_conn.db_type == "sqlite":
                self._load_sqlite_schema(db_item, connection, db_id)
            elif db_conn.db_type == "sqlserver" and database_name:
                self._load_sqlserver_schema(db_item, connection, db_id, database_name)
        except Exception as e:
            logger.error(f"Error loading schema: {e}")

    def _load_sqlite_schema(self, parent: QTreeWidgetItem, connection, db_id: str):
        """Load SQLite schema."""
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        tables_folder = QTreeWidgetItem(parent)
        tables_folder.setText(0, f"Tables ({len(tables)})")
        tables_folder.setIcon(0, get_icon("folder.png", size=16))
        tables_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "tables_folder", "db_id": db_id})

        for (table_name,) in tables:
            t_item = QTreeWidgetItem(tables_folder)
            t_item.setText(0, table_name)
            t_item.setIcon(0, get_icon("table.png", size=16))
            t_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "table",
                "name": table_name,
                "db_id": db_id
            })

    def _load_sqlserver_schema(self, parent: QTreeWidgetItem, connection, db_id: str, db_name: str):
        """Load SQL Server schema."""
        cursor = connection.cursor()

        # Tables
        cursor.execute(f"""
            SELECT s.name + '.' + t.name AS full_name
            FROM [{db_name}].sys.tables t
            INNER JOIN [{db_name}].sys.schemas s ON t.schema_id = s.schema_id
            ORDER BY s.name, t.name
        """)
        tables = cursor.fetchall()

        tables_folder = QTreeWidgetItem(parent)
        tables_folder.setText(0, f"Tables ({len(tables)})")
        tables_folder.setIcon(0, get_icon("folder.png", size=16))
        tables_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "tables_folder", "db_id": db_id, "db_name": db_name})

        for (table_name,) in tables:
            t_item = QTreeWidgetItem(tables_folder)
            t_item.setText(0, table_name)
            t_item.setIcon(0, get_icon("table.png", size=16))
            t_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "table",
                "name": table_name,
                "db_id": db_id,
                "db_name": db_name
            })

        # Views
        cursor.execute(f"""
            SELECT s.name + '.' + v.name AS full_name
            FROM [{db_name}].sys.views v
            INNER JOIN [{db_name}].sys.schemas s ON v.schema_id = s.schema_id
            ORDER BY s.name, v.name
        """)
        views = cursor.fetchall()

        if views:
            views_folder = QTreeWidgetItem(parent)
            views_folder.setText(0, f"Views ({len(views)})")
            views_folder.setIcon(0, get_icon("folder.png", size=16))
            views_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "views_folder", "db_id": db_id, "db_name": db_name})

            for (view_name,) in views:
                v_item = QTreeWidgetItem(views_folder)
                v_item.setText(0, view_name)
                v_item.setIcon(0, get_icon("view.png", size=16))
                v_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "view",
                    "name": view_name,
                    "db_id": db_id,
                    "db_name": db_name
                })

    def _count_files_in_folder(self, folder_path: Path) -> int:
        """Count all files recursively in a folder."""
        count = 0
        try:
            for item in folder_path.rglob("*"):
                if item.is_file():
                    count += 1
        except PermissionError:
            pass
        except Exception as e:
            logger.warning(f"Error counting files in {folder_path}: {e}")
        return count

    def _get_file_icon(self, file_path: Path):
        """Get icon based on file extension."""
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
            '.log': 'file.png',
        }

        icon_name = icon_map.get(extension, 'file.png')
        return get_icon(icon_name, size=16)

    def _load_folder_contents(self, parent_item: QTreeWidgetItem, folder_path: Path, recursive: bool = True):
        """Load contents of a folder (subfolders and files) with file counts."""
        try:
            entries = sorted(folder_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

            for entry in entries:
                if entry.is_dir():
                    folder_item = QTreeWidgetItem(parent_item)

                    folder_icon = get_icon("folder.png", size=16)
                    if folder_icon:
                        folder_item.setIcon(0, folder_icon)

                    file_count = self._count_files_in_folder(entry)
                    folder_item.setText(0, f"{entry.name} ({file_count})")
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "folder",
                        "path": str(entry),
                        "name": entry.name
                    })

                    if recursive:
                        self._load_folder_contents(folder_item, entry, recursive=True)
                    else:
                        # Add dummy child for lazy loading
                        dummy = QTreeWidgetItem(folder_item)
                        dummy.setText(0, "Loading...")
                        dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})

                elif entry.is_file():
                    file_item = QTreeWidgetItem(parent_item)

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

    def _load_rootfolder_contents(self, parent_item: QTreeWidgetItem, data: dict):
        """Load rootfolder contents."""
        full_path = data.get("full_path")
        if not full_path:
            return

        folder_path = Path(full_path)
        if not folder_path.exists():
            return

        self._load_folder_contents(parent_item, folder_path, recursive=False)

    def _add_tree_item(self, parent: QTreeWidgetItem, text: list, data: dict) -> QTreeWidgetItem:
        """Callback for TreePopulator."""
        item = QTreeWidgetItem(parent)
        item.setText(0, text[0])
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        return item

    # ==================== Tree Event Handlers ====================

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        """Handle click - show details."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        if item_type == "workspace":
            ws = data["workspace_obj"]
            self._current_workspace_id = ws.id
            self._current_item = ws
            self.object_viewer.show_details(
                name=ws.name,
                obj_type="Workspace",
                description=ws.description or "",
                created=ws.created_at or "",
                updated=ws.updated_at or ""
            )

        elif item_type == "database":
            db = data.get("resource_obj")
            db_name = data.get("database_name", "")
            if db_name:
                self.object_viewer.show_details(db_name, f"Database on {db.name}", db.description or "")
            else:
                self.object_viewer.show_details(db.name, f"Server ({db.db_type})", db.description or "")

        elif item_type == "query":
            query = data["resource_obj"]
            self.object_viewer.show_details(query.name, "Query", query.description or "")

        elif item_type == "script":
            script = data["resource_obj"]
            self.object_viewer.show_details(script.name, f"Script ({script.script_type})", script.description or "")

        elif item_type == "rootfolder":
            fr = data.get("resource_obj")
            full_path = data.get("full_path", "")
            subfolder = data.get("subfolder_path", "")
            if subfolder:
                self.object_viewer.show_details(Path(subfolder).name, "Subfolder", full_path)
            else:
                self.object_viewer.show_details(fr.name or fr.path, "RootFolder", fr.path)

        elif item_type == "folder":
            path = data.get("path", "")
            self.object_viewer.show_folder(Path(path).name, path)

        elif item_type == "file":
            file_path = data.get("path")
            if file_path:
                self.object_viewer.show_file(Path(file_path))

        elif item_type in ["table", "view"]:
            name = data.get("name", "")
            db_name = data.get("db_name", "")
            self.object_viewer.show_details(name, item_type.title(), f"Database: {db_name}" if db_name else "")

        elif item_type in ["query_category", "script_type", "tables_folder", "views_folder"]:
            name = data.get("name", item_type)
            self.object_viewer.show_details(name, item_type.replace("_", " ").title(), "")

    def _on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click - display content or expand."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")

        if item_type in ["table", "view"]:
            self._execute_select_query(data, limit=100)
        elif item_type == "file":
            file_path = data.get("path")
            if file_path:
                self.object_viewer.show_file(Path(file_path))
        elif item_type in ["workspace", "database", "rootfolder", "folder",
                           "tables_folder", "views_folder", "query_category", "script_type"]:
            item.setExpanded(not item.isExpanded())

    def _execute_select_query(self, data: dict, limit: Optional[int] = None):
        """Execute SELECT query using DataViewerWidget."""
        if not self._database_manager:
            DialogHelper.warning("Database manager not available")
            return

        db_id = data.get("db_id")
        db_name = data.get("db_name")
        table_name = data.get("name")

        if not db_id or not table_name:
            return

        connection = self._database_manager.connections.get(db_id)
        if not connection:
            DialogHelper.warning("Not connected. Please expand the database first.")
            return

        db_conn = self._database_manager._get_connection_by_id(db_id)
        if not db_conn:
            return

        # Build and execute query via ObjectViewerWidget
        self.object_viewer.show_table(connection, table_name, db_name)

    # ==================== Context Menu ====================

    def _on_tree_context_menu(self, position):
        """Show context menu."""
        item = self.workspace_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type", "")
        menu = QMenu(self)

        if item_type == "workspace":
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self._edit_workspace_item(item, data))
            menu.addAction(edit_action)

            menu.addSeparator()

            delete_action = QAction("Delete Workspace", self)
            delete_action.triggered.connect(lambda: self._delete_workspace_item(data["id"]))
            menu.addAction(delete_action)

            menu.addSeparator()

            export_action = QAction("Export Workspace...", self)
            export_action.triggered.connect(lambda: self._export_workspace(data["id"], data.get("workspace_obj").name))
            menu.addAction(export_action)

        elif item_type in ["database", "query", "rootfolder", "script"]:
            remove_action = QAction("Remove from Workspace", self)
            remove_action.triggered.connect(lambda: self._remove_resource_from_workspace(item, data))
            menu.addAction(remove_action)

        elif item_type in ["table", "view"]:
            select_action = QAction("SELECT *", self)
            select_action.triggered.connect(lambda: self._execute_select_query(data, limit=100))
            menu.addAction(select_action)

        if menu.actions():
            menu.exec(self.workspace_tree.viewport().mapToGlobal(position))

    def _remove_resource_from_workspace(self, item: QTreeWidgetItem, data: dict):
        """Remove resource from workspace."""
        parent = item.parent()
        if not parent:
            return

        parent_data = parent.data(0, Qt.ItemDataRole.UserRole)
        if not parent_data or parent_data.get("type") != "workspace":
            parent = parent.parent()
            if parent:
                parent_data = parent.data(0, Qt.ItemDataRole.UserRole)

        if not parent_data or parent_data.get("type") != "workspace":
            return

        workspace_id = parent_data.get("id")
        item_type = data.get("type")
        resource_id = data.get("id")

        if not workspace_id or not resource_id:
            return

        if not DialogHelper.confirm(f"Remove this {item_type} from the workspace?"):
            return

        try:
            if item_type == "database":
                self.config_db.remove_database_from_workspace(workspace_id, resource_id)
            elif item_type == "query":
                self.config_db.remove_query_from_workspace(workspace_id, resource_id)
            elif item_type == "rootfolder":
                self.config_db.remove_file_root_from_workspace(workspace_id, resource_id)
            elif item_type == "script":
                self.config_db.remove_script_from_workspace(workspace_id, resource_id)

            parent.removeChild(item)
            logger.info(f"Removed {item_type} {resource_id} from workspace {workspace_id}")

        except Exception as e:
            logger.error(f"Error removing resource: {e}")
            DialogHelper.error("Error removing resource", details=str(e))

    # ==================== Workspace CRUD ====================

    def _new_workspace(self):
        """Create a new workspace."""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "New Workspace", "Workspace name:")
        if ok and name.strip():
            ws = Workspace(
                id=str(uuid.uuid4()),
                name=name.strip(),
                description=""
            )
            if self.config_db.add_workspace(ws):
                self._refresh()
                DialogHelper.info(f"Workspace '{name}' created")
            else:
                DialogHelper.warning("Failed to create workspace. Name may already exist.")

    def _edit_workspace(self):
        """Edit selected workspace."""
        selected = self.workspace_tree.selectedItems()
        if not selected:
            DialogHelper.warning("Please select a workspace")
            return

        data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "workspace":
            self._edit_workspace_item(selected[0], data)

    def _edit_workspace_item(self, item: QTreeWidgetItem, data: dict):
        """Edit workspace dialog."""
        from PySide6.QtWidgets import QInputDialog

        ws = data.get("workspace_obj")
        if not ws:
            return

        name, ok = QInputDialog.getText(self, "Edit Workspace", "Workspace name:", text=ws.name)
        if ok and name.strip():
            ws.name = name.strip()
            if self.config_db.update_workspace(ws):
                item.setText(0, ws.name)
                DialogHelper.info("Workspace updated")
            else:
                DialogHelper.warning("Failed to update workspace")

    def _delete_workspace(self):
        """Delete selected workspace."""
        selected = self.workspace_tree.selectedItems()
        if not selected:
            DialogHelper.warning("Please select a workspace")
            return

        data = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "workspace":
            self._delete_workspace_item(data["id"])

    def _delete_workspace_item(self, workspace_id: str):
        """Delete workspace by ID."""
        if not DialogHelper.confirm("Delete this workspace?\n\n(Resources will not be deleted)"):
            return

        try:
            self.config_db.delete_workspace(workspace_id)
            self._refresh()
            DialogHelper.info("Workspace deleted")
        except Exception as e:
            logger.error(f"Error deleting workspace: {e}")
            DialogHelper.error("Error deleting workspace", details=str(e))

    def _refresh(self):
        """Refresh the tree."""
        self._load_workspaces()
        self.object_viewer.clear()

    # ==================== Import/Export ====================

    def _export_workspace(self, workspace_id: str, workspace_name: str):
        """Export workspace to JSON file."""
        try:
            default_filename = f"{workspace_name.replace(' ', '_')}_export.json"
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Export Workspace", default_filename,
                "JSON Files (*.json);;All Files (*)"
            )
            if not filepath:
                return

            export_data = export_workspace_to_json(
                workspace_id,
                include_credentials=False,
                include_databases=True,
                include_rootfolders=True,
                include_queries=True,
                include_scripts=True,
                include_jobs=True
            )
            save_export_to_file(export_data, filepath)

            summary = get_export_summary(export_data)
            DialogHelper.info(f"Export successful!\n\n{summary}\n\nFile: {filepath}")

        except Exception as e:
            logger.error(f"Export failed: {e}")
            DialogHelper.error(f"Export failed: {str(e)}")

    def _import_workspace(self):
        """Import workspace from JSON file."""
        try:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Import Workspace", "",
                "JSON Files (*.json);;All Files (*)"
            )
            if not filepath:
                return

            import_data = load_import_from_file(filepath)

            export_type = import_data.get("export_type", "")
            if export_type not in ["workspace", "connections"]:
                DialogHelper.error(f"Unsupported export type: {export_type}")
                return

            ws_name = import_data.get("workspace", {}).get("name", "Imported Workspace")
            conflict = check_workspace_conflict(ws_name)

            mode = ImportConflictMode.CREATE_NEW
            if conflict:
                from PySide6.QtWidgets import QMessageBox
                result = QMessageBox.question(
                    self, "Workspace Exists",
                    f"Workspace '{ws_name}' already exists.\n\nCreate new or merge?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                if result == QMessageBox.StandardButton.Cancel:
                    return
                elif result == QMessageBox.StandardButton.No:
                    mode = ImportConflictMode.MERGE

            result = import_workspace_from_json(import_data, mode)
            summary = get_import_summary(result)
            DialogHelper.info(f"Import successful!\n\n{summary}")
            self._refresh()

        except Exception as e:
            logger.error(f"Import failed: {e}")
            DialogHelper.error(f"Import failed: {str(e)}")
