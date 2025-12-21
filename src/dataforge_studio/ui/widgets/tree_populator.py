"""
Tree Populator - Shared logic for populating tree widgets with resource subtrees.

Used by ResourcesManager and WorkspaceManager to avoid code duplication.
Handles lazy loading of:
- Database schemas (tables, views, columns)
- Folder contents (subfolders, files)
"""

from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING
from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt

from ...utils.image_loader import get_icon
from ..core.i18n_bridge import tr

import logging
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..managers.database_manager import DatabaseManager


class TreePopulator:
    """
    Static methods for populating tree items with resource subtrees.

    Usage:
        TreePopulator.add_dummy_child(parent_item)
        TreePopulator.load_folder_subtree(parent_item, folder_path)
        TreePopulator.load_database_subtree(parent_item, db_config, database_manager)
    """

    # File extension to icon mapping
    FILE_ICONS = {
        ".csv": "CSV",
        ".xlsx": "Excel",
        ".xls": "Excel",
        ".json": "json",
        ".py": "scripts",
        ".sql": "queries",
        ".txt": "file",
        ".md": "file",
        ".log": "file",
    }

    @staticmethod
    def add_dummy_child(parent_item: QTreeWidgetItem, text: str = "...") -> QTreeWidgetItem:
        """
        Add a dummy child to show expand arrow (for lazy loading).

        Args:
            parent_item: Parent tree item
            text: Text to display (default "...")

        Returns:
            The dummy child item
        """
        dummy = QTreeWidgetItem(parent_item)
        dummy.setText(0, text)
        dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})
        return dummy

    @staticmethod
    def has_dummy_child(item: QTreeWidgetItem) -> bool:
        """Check if item has a dummy child (needs lazy loading)."""
        if item.childCount() == 1:
            first_child = item.child(0)
            child_data = first_child.data(0, Qt.ItemDataRole.UserRole)
            return child_data and child_data.get("type") == "dummy"
        return False

    @staticmethod
    def remove_dummy_child(item: QTreeWidgetItem) -> bool:
        """
        Remove dummy child if present.

        Returns:
            True if dummy was removed, False otherwise
        """
        if TreePopulator.has_dummy_child(item):
            item.removeChild(item.child(0))
            return True
        return False

    @staticmethod
    def set_item_icon(item: QTreeWidgetItem, icon_name: str, size: int = 16):
        """Set icon on a tree item."""
        icon = get_icon(icon_name, size=size)
        if icon:
            item.setIcon(0, icon)

    @staticmethod
    def get_file_icon(file_path: Path) -> str:
        """Get icon name for a file based on extension."""
        ext = file_path.suffix.lower()
        return TreePopulator.FILE_ICONS.get(ext, "file")

    @staticmethod
    def load_folder_subtree(
        parent_item: QTreeWidgetItem,
        folder_path: Path,
        add_item_callback: Callable,
        recursive: bool = True
    ) -> int:
        """
        Load folder contents into tree.

        Args:
            parent_item: Parent tree item to add children to
            folder_path: Path to folder to scan
            add_item_callback: Function to add items (tree_view.add_item or similar)
            recursive: Whether to add dummy children for subfolders

        Returns:
            Number of items added
        """
        if not folder_path.exists() or not folder_path.is_dir():
            return 0

        count = 0
        try:
            entries = sorted(
                folder_path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )

            for entry in entries:
                if entry.is_dir():
                    folder_item = add_item_callback(
                        parent=parent_item,
                        text=[entry.name],
                        data={"type": "folder", "path": str(entry)}
                    )
                    TreePopulator.set_item_icon(folder_item, "folder")
                    if recursive:
                        TreePopulator.add_dummy_child(folder_item)
                    count += 1
                else:
                    file_item = add_item_callback(
                        parent=parent_item,
                        text=[entry.name],
                        data={"type": "file", "path": str(entry)}
                    )
                    icon_name = TreePopulator.get_file_icon(entry)
                    TreePopulator.set_item_icon(file_item, icon_name)
                    count += 1

        except PermissionError as e:
            logger.warning(f"Permission denied accessing {folder_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading folder {folder_path}: {e}")

        return count

    @staticmethod
    def load_database_subtree(
        parent_item: QTreeWidgetItem,
        db_config,
        database_manager: "DatabaseManager",
        database_name: Optional[str] = None
    ) -> bool:
        """
        Load database schema into tree.

        Args:
            parent_item: Parent tree item (database node)
            db_config: Database connection config object
            database_manager: DatabaseManager instance for connection handling
            database_name: Specific database name (for servers with multiple DBs)

        Returns:
            True if successfully loaded, False otherwise
        """
        if not database_manager:
            logger.warning("No database_manager provided for loading schema")
            return False

        try:
            # Store original data for restoration on failure
            original_data = parent_item.data(0, Qt.ItemDataRole.UserRole)

            # Update item data to match DatabaseManager's expected format
            parent_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "server",
                "config": db_config,
                "connected": False,
                "database_name": database_name
            })

            # Delegate to DatabaseManager's connection and schema loading
            database_manager._connect_and_load_schema(parent_item, db_config)

            # Check if connection succeeded
            if not database_manager.connections.get(db_config.id):
                # Connection failed - restore original data
                parent_item.setData(0, Qt.ItemDataRole.UserRole, original_data)
                return False

            return True

        except Exception as e:
            logger.error(f"Error loading database schema: {e}")
            return False

    @staticmethod
    def create_category_node(
        parent_item: QTreeWidgetItem,
        category_name: str,
        add_item_callback: Callable,
        icon_name: str = "folder"
    ) -> QTreeWidgetItem:
        """
        Create a category grouping node.

        Args:
            parent_item: Parent tree item
            category_name: Name of the category
            add_item_callback: Function to add items
            icon_name: Icon for the category

        Returns:
            The created category item
        """
        category_item = add_item_callback(
            parent=parent_item,
            text=[category_name],
            data={"type": "category", "name": category_name}
        )
        TreePopulator.set_item_icon(category_item, icon_name)
        return category_item
