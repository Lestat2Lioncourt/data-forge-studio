"""
Schema Mixin - Tree population from database schema.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QTreeWidgetItem, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from ...core.i18n_bridge import tr
from ....database.config_db import DatabaseConnection
from ....database.schema_loaders import SchemaLoaderFactory, SchemaNode, SchemaNodeType
from ....utils.image_loader import get_icon

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DatabaseSchemaMixin:
    """Mixin providing schema tree population for database connections."""

    def _populate_tree_from_schema(self, parent_item: QTreeWidgetItem,
                                    schema: SchemaNode, db_conn: DatabaseConnection):
        """
        Populate tree widget from SchemaNode structure.

        Converts the abstract SchemaNode tree into QTreeWidgetItem hierarchy,
        setting appropriate icons, text, and metadata for each node.
        """
        folder_icon = get_icon("RootFolders", size=16)
        db_icon = get_icon("database.png", size=16)
        proc_icon = get_icon("scripts.png", size=16)
        func_icon = get_icon("jobs.png", size=16)
        tables_folder_icon = get_icon("tables.png", size=16) or folder_icon
        table_icon = get_icon("table.png", size=16) or self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogListView)
        view_icon = get_icon("view.png", size=16) or self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView)

        def create_item(node: SchemaNode, parent: QTreeWidgetItem) -> QTreeWidgetItem:
            """Recursively create tree items from schema nodes."""
            item = QTreeWidgetItem(parent)
            item.setText(0, node.display_name)

            # Build metadata from node type and node.metadata
            metadata = dict(node.metadata)  # Copy existing metadata
            metadata["db_id"] = db_conn.id

            # Map SchemaNodeType to tree item type and icon
            if node.node_type == SchemaNodeType.DATABASE:
                if metadata.get("is_server"):
                    metadata["type"] = "server"
                else:
                    metadata["type"] = "database"
                    metadata["name"] = node.name  # Database name for workspace menu
                    if db_icon:
                        item.setIcon(0, db_icon)

            elif node.node_type == SchemaNodeType.TABLES_FOLDER:
                metadata["type"] = "tables_folder"
                if tables_folder_icon:
                    item.setIcon(0, tables_folder_icon)

            elif node.node_type == SchemaNodeType.VIEWS_FOLDER:
                metadata["type"] = "views_folder"
                if folder_icon:
                    item.setIcon(0, folder_icon)

            elif node.node_type == SchemaNodeType.PROCEDURES_FOLDER:
                if metadata.get("is_functions"):
                    metadata["type"] = "functions_folder"
                    if func_icon:
                        item.setIcon(0, func_icon)
                    elif folder_icon:
                        item.setIcon(0, folder_icon)
                else:
                    metadata["type"] = "procedures_folder"
                    if proc_icon:
                        item.setIcon(0, proc_icon)
                    elif folder_icon:
                        item.setIcon(0, folder_icon)

            elif node.node_type == SchemaNodeType.TABLE:
                metadata["type"] = "table"
                metadata["name"] = node.name
                # Set db_name from node metadata or fallback to connection name
                if "db_name" not in metadata:
                    metadata["db_name"] = db_conn.name
                item.setIcon(0, table_icon)

            elif node.node_type == SchemaNodeType.VIEW:
                metadata["type"] = "view"
                metadata["name"] = node.name
                if "db_name" not in metadata:
                    metadata["db_name"] = db_conn.name
                item.setIcon(0, view_icon)

            elif node.node_type == SchemaNodeType.COLUMN:
                metadata["type"] = "column"
                metadata["column"] = node.name
                # table should already be in metadata from schema loader

            elif node.node_type == SchemaNodeType.PROCEDURE:
                if metadata.get("is_function"):
                    metadata["type"] = "function"
                    if func_icon:
                        item.setIcon(0, func_icon)
                else:
                    metadata["type"] = "procedure"
                    if proc_icon:
                        item.setIcon(0, proc_icon)

            item.setData(0, Qt.ItemDataRole.UserRole, metadata)

            # Recursively create children
            for child in node.children:
                create_item(child, item)

            return item

        # Create items for all children of the schema root
        for child in schema.children:
            create_item(child, parent_item)

    def load_specific_database_schema(
        self,
        parent_item: QTreeWidgetItem,
        db_conn: DatabaseConnection,
        database_name: str
    ) -> bool:
        """
        Load schema for a specific database (not the whole server).

        Used by WorkspaceManager when a specific database is attached to a workspace.
        Shows loading indicator for consistent UX with DatabaseManager.

        Args:
            parent_item: Tree item to populate with database schema
            db_conn: Database connection config
            database_name: Name of the specific database to load

        Returns:
            True if successfully loaded, False otherwise
        """
        # Show loading indicator (same as _connect_and_load_schema)
        while parent_item.childCount() > 0:
            parent_item.removeChild(parent_item.child(0))

        loading_item = QTreeWidgetItem(parent_item)
        loading_item.setText(0, tr("db_connecting_in_progress"))
        loading_item.setForeground(0, Qt.GlobalColor.gray)
        loading_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "loading"})

        # Expand parent and get the tree widget to force repaint
        parent_item.setExpanded(True)
        tree = parent_item.treeWidget()
        if tree:
            tree.repaint()

        # Force multiple UI updates to ensure loading indicator is visible
        QApplication.processEvents()
        QApplication.processEvents()

        try:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

            # Get or create connection
            connection = self.connections.get(db_conn.id)
            if not connection:
                connection = self._create_connection(db_conn)
                if connection is None:
                    # Remove loading indicator on failure
                    while parent_item.childCount() > 0:
                        parent_item.removeChild(parent_item.child(0))
                    return False
                self.connections[db_conn.id] = connection

            # Use the schema loader to load just the specific database
            loader = SchemaLoaderFactory.create(
                db_conn.db_type, connection, db_conn.id, db_conn.name
            )

            if not loader:
                logger.warning(f"No loader for db_type: {db_conn.db_type}")
                # Remove loading indicator on failure
                while parent_item.childCount() > 0:
                    parent_item.removeChild(parent_item.child(0))
                return False

            # Remove loading indicator before populating
            while parent_item.childCount() > 0:
                parent_item.removeChild(parent_item.child(0))

            # For SQL Server, use _load_database_schema for a specific database
            if hasattr(loader, '_load_database_schema'):
                db_schema = loader._load_database_schema(database_name)
                # Populate with just this database's contents (Tables, Views, etc.)
                self._populate_tree_from_schema(parent_item, db_schema, db_conn)
                return True
            else:
                # For other DB types, load full schema
                schema = loader.load_schema()
                self._populate_tree_from_schema(parent_item, schema, db_conn)
                return True

        except Exception as e:
            logger.error(f"Error loading specific database schema: {e}")
            # Remove loading indicator on failure
            while parent_item.childCount() > 0:
                parent_item.removeChild(parent_item.child(0))
            return False

        finally:
            QApplication.restoreOverrideCursor()
