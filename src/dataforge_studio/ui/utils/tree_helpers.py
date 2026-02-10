"""
Tree Helpers - Generic utilities for populating tree widgets.

These functions are plugin-independent and can be used by any manager
or view that needs to display files/folders in a QTreeWidget.

This module ensures no code duplication across plugins while maintaining
complete plugin independence.
"""

from pathlib import Path
from typing import Optional, List, Any, Protocol, runtime_checkable
from dataclasses import dataclass

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtGui import QIcon

from ...utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


# ==================== File Icon Utilities ====================

# Standard file extension to icon mapping
FILE_ICON_MAP = {
    # Data files
    '.csv': 'csv.png',
    '.json': 'json.png',
    '.xml': 'xml.png',
    '.yaml': 'yaml.png',
    '.yml': 'yaml.png',

    # Spreadsheets
    '.xlsx': 'excel.png',
    '.xls': 'excel.png',
    '.xlsm': 'excel.png',

    # Documents
    '.txt': 'text.png',
    '.md': 'markdown.png',
    '.pdf': 'pdf.png',
    '.doc': 'word.png',
    '.docx': 'word.png',

    # Code
    '.sql': 'sql.png',
    '.py': 'python.png',
    '.js': 'javascript.png',
    '.ts': 'typescript.png',
    '.html': 'html.png',
    '.css': 'css.png',

    # Images
    '.png': 'image.png',
    '.jpg': 'image.png',
    '.jpeg': 'image.png',
    '.gif': 'image.png',
    '.svg': 'image.png',
    '.ico': 'image.png',

    # Archives
    '.zip': 'archive.png',
    '.rar': 'archive.png',
    '.7z': 'archive.png',
    '.tar': 'archive.png',
    '.gz': 'archive.png',

    # Logs
    '.log': 'file.png',
}


def get_file_icon_for_extension(extension: str, size: int = 16) -> Optional[QIcon]:
    """
    Get icon based on file extension.

    Args:
        extension: File extension (with or without dot, e.g., '.csv' or 'csv')
        size: Icon size in pixels

    Returns:
        QIcon for the file type, or default file icon
    """
    # Normalize extension
    ext = extension.lower()
    if not ext.startswith('.'):
        ext = '.' + ext

    icon_name = FILE_ICON_MAP.get(ext, 'file.png')
    return get_icon(icon_name, size=size)


def get_file_icon(file_path: Path, size: int = 16) -> Optional[QIcon]:
    """
    Get icon for a file based on its path.

    Args:
        file_path: Path to the file
        size: Icon size in pixels

    Returns:
        QIcon for the file type
    """
    return get_file_icon_for_extension(file_path.suffix, size=size)


# ==================== File Size Formatting ====================

def format_file_size(size: int) -> str:
    """
    Format file size for display.

    Args:
        size: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 KB", "2.3 MB")
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


# ==================== File Counting ====================

def count_files_recursive(folder_path: Path) -> int:
    """
    Count all files recursively in a folder.

    Args:
        folder_path: Path to the folder

    Returns:
        Number of files (recursive)
    """
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


# ==================== Tree Population - Local Files ====================

def add_dummy_child(parent_item: QTreeWidgetItem, text: str = "Loading..."):
    """
    Add a dummy child for lazy loading.

    Args:
        parent_item: Parent tree item
        text: Text to display for the dummy item
    """
    dummy = QTreeWidgetItem(parent_item)
    dummy.setText(0, text)
    dummy.setData(0, 256, {"type": "dummy"})  # Qt.ItemDataRole.UserRole = 256


def has_dummy_child(item: QTreeWidgetItem) -> bool:
    """Check if item has a dummy child for lazy loading."""
    if item.childCount() == 1:
        child = item.child(0)
        data = child.data(0, 256)
        return data and data.get("type") == "dummy"
    return False


def remove_dummy_children(parent_item: QTreeWidgetItem):
    """
    Remove dummy/loading children from a tree item.

    Args:
        parent_item: Parent tree item
    """
    for i in range(parent_item.childCount() - 1, -1, -1):
        child = parent_item.child(i)
        child_data = child.data(0, 256)  # Qt.ItemDataRole.UserRole
        if child_data and child_data.get("type") in ["dummy", "loading"]:
            parent_item.removeChild(child)


def add_folder_to_tree(
    parent_item: QTreeWidgetItem,
    folder_path: Path,
    show_file_count: bool = True,
    lazy_load: bool = True
) -> QTreeWidgetItem:
    """
    Add a folder item to a tree widget.

    Args:
        parent_item: Parent tree item
        folder_path: Path to the folder
        show_file_count: Whether to show recursive file count
        lazy_load: Whether to add dummy child for lazy loading

    Returns:
        The created folder item
    """
    folder_item = QTreeWidgetItem(parent_item)

    folder_icon = get_icon("folder.png", size=16)
    if folder_icon:
        folder_item.setIcon(0, folder_icon)

    display_name = folder_path.name
    if show_file_count:
        file_count = count_files_recursive(folder_path)
        display_name = f"{folder_path.name} ({file_count})"

    folder_item.setText(0, display_name)
    folder_item.setData(0, 256, {
        "type": "folder",
        "path": str(folder_path),
        "name": folder_path.name
    })

    if lazy_load:
        add_dummy_child(folder_item)

    return folder_item


def add_file_to_tree(
    parent_item: QTreeWidgetItem,
    file_path: Path
) -> QTreeWidgetItem:
    """
    Add a file item to a tree widget.

    Args:
        parent_item: Parent tree item
        file_path: Path to the file

    Returns:
        The created file item
    """
    file_item = QTreeWidgetItem(parent_item)

    file_icon = get_file_icon(file_path)
    if file_icon:
        file_item.setIcon(0, file_icon)

    file_item.setText(0, file_path.name)
    file_item.setData(0, 256, {
        "type": "file",
        "path": str(file_path),
        "name": file_path.name,
        "extension": file_path.suffix.lower()
    })

    return file_item


def populate_tree_with_local_folder(
    parent_item: QTreeWidgetItem,
    folder_path: Path,
    recursive: bool = False,
    show_file_count: bool = True
) -> bool:
    """
    Populate a tree item with local folder contents.

    This is the main function for loading local file system contents
    into any tree widget, without any plugin dependency.

    Args:
        parent_item: Parent tree item to populate
        folder_path: Path to the folder to load
        recursive: If True, load all subfolders recursively
        show_file_count: Whether to show file counts for folders

    Returns:
        True if successful, False if error occurred
    """
    if not folder_path.exists():
        logger.warning(f"Folder does not exist: {folder_path}")
        return False

    try:
        # Remove any dummy/loading items first
        remove_dummy_children(parent_item)

        # Sort entries: directories first, then files (case-insensitive)
        entries = sorted(
            folder_path.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower())
        )

        for entry in entries:
            if entry.is_dir():
                folder_item = add_folder_to_tree(
                    parent_item,
                    entry,
                    show_file_count=show_file_count,
                    lazy_load=not recursive
                )

                if recursive:
                    populate_tree_with_local_folder(
                        folder_item, entry,
                        recursive=True,
                        show_file_count=show_file_count
                    )

            elif entry.is_file():
                add_file_to_tree(parent_item, entry)

        return True

    except PermissionError:
        logger.warning(f"Permission denied: {folder_path}")
        return False
    except Exception as e:
        logger.error(f"Error loading folder contents: {e}")
        return False


# ==================== Tree Population - Remote Files (Generic) ====================

@runtime_checkable
class RemoteFileProtocol(Protocol):
    """Protocol for remote file objects (FTP, S3, etc.)."""
    name: str
    path: str
    is_dir: bool
    size: int


def add_remote_folder_to_tree(
    parent_item: QTreeWidgetItem,
    name: str,
    path: str,
    source_id: str,
    source_id_key: str = "ftproot_id"
) -> QTreeWidgetItem:
    """
    Add a remote folder item to a tree widget.

    Args:
        parent_item: Parent tree item
        name: Folder name
        path: Remote path
        source_id: ID of the remote source (e.g., ftp_root_id)
        source_id_key: Key name for the source ID in item data

    Returns:
        The created folder item
    """
    folder_item = QTreeWidgetItem(parent_item)

    folder_icon = get_icon("folder.png", size=16)
    if folder_icon:
        folder_item.setIcon(0, folder_icon)

    folder_item.setText(0, name)
    folder_item.setData(0, 256, {
        "type": "remote_folder",
        source_id_key: source_id,
        "path": path,
        "name": name
    })

    add_dummy_child(folder_item)
    return folder_item


def add_remote_file_to_tree(
    parent_item: QTreeWidgetItem,
    name: str,
    path: str,
    size: int,
    source_id: str,
    source_id_key: str = "ftproot_id",
    modified: Any = None
) -> QTreeWidgetItem:
    """
    Add a remote file item to a tree widget.

    Args:
        parent_item: Parent tree item
        name: File name
        path: Remote path
        size: File size in bytes
        source_id: ID of the remote source
        source_id_key: Key name for the source ID in item data
        modified: Last modified timestamp (optional)

    Returns:
        The created file item
    """
    file_item = QTreeWidgetItem(parent_item)

    # Get icon based on extension
    extension = Path(name).suffix
    file_icon = get_file_icon_for_extension(extension)
    if file_icon:
        file_item.setIcon(0, file_icon)

    # Format display with size
    size_str = format_file_size(size)
    file_item.setText(0, f"{name} ({size_str})")

    data = {
        "type": "remote_file",
        source_id_key: source_id,
        "path": path,
        "name": name,
        "size": size
    }
    if modified:
        data["modified"] = modified

    file_item.setData(0, 256, data)
    return file_item


def populate_tree_with_remote_files(
    parent_item: QTreeWidgetItem,
    files: List[Any],
    source_id: str,
    source_id_key: str = "ftproot_id",
    show_item_count: bool = True
) -> bool:
    """
    Populate a tree item with remote files.

    This is the main function for loading remote file listings
    into any tree widget, without any plugin dependency.

    Args:
        parent_item: Parent tree item to populate
        files: List of remote file objects (must have name, path, is_dir, size)
        source_id: ID of the remote source (e.g., ftp_root_id)
        source_id_key: Key name for the source ID in item data
        show_item_count: Whether to update parent item text with child count

    Returns:
        True if successful
    """
    try:
        # Remove any dummy/loading items first
        remove_dummy_children(parent_item)

        # Sort: directories first, then files (case-insensitive)
        files_sorted = sorted(files, key=lambda f: (not f.is_dir, f.name.lower()))

        for remote_file in files_sorted:
            if remote_file.is_dir:
                add_remote_folder_to_tree(
                    parent_item,
                    remote_file.name,
                    remote_file.path,
                    source_id,
                    source_id_key
                )
            else:
                modified = getattr(remote_file, 'modified', None)
                add_remote_file_to_tree(
                    parent_item,
                    remote_file.name,
                    remote_file.path,
                    remote_file.size,
                    source_id,
                    source_id_key,
                    modified
                )

        # Update parent item text with child count
        if show_item_count and len(files_sorted) > 0:
            update_item_count(parent_item, len(files_sorted))

        return True

    except Exception as e:
        logger.error(f"Error populating tree with remote files: {e}")
        return False


def update_item_count(item: QTreeWidgetItem, count: int):
    """
    Update a tree item's text to include a count suffix.

    Args:
        item: Tree item to update
        count: Number to display in parentheses
    """
    current_text = item.text(0)
    # Remove existing count if present
    if " (" in current_text and current_text.endswith(")"):
        current_text = current_text.rsplit(" (", 1)[0]
    # Add new count
    item.setText(0, f"{current_text} ({count})")
