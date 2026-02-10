"""
UI Utilities - Common utilities for UI components
"""

from .ui_helper import UIHelper
from .item_data_wrapper import ItemDataWrapper
from .themed_widget import ThemedWidgetMixin
from .tree_helpers import (
    # File icons
    get_file_icon,
    get_file_icon_for_extension,
    FILE_ICON_MAP,
    # File size
    format_file_size,
    # File counting
    count_files_recursive,
    # Tree item helpers
    add_dummy_child,
    has_dummy_child,
    remove_dummy_children,
    update_item_count,
    # Local file tree population
    add_folder_to_tree,
    add_file_to_tree,
    populate_tree_with_local_folder,
    # Remote file tree population
    add_remote_folder_to_tree,
    add_remote_file_to_tree,
    populate_tree_with_remote_files,
)

__all__ = [
    "UIHelper",
    "ItemDataWrapper",
    "ThemedWidgetMixin",
    # Tree helpers
    "get_file_icon",
    "get_file_icon_for_extension",
    "FILE_ICON_MAP",
    "format_file_size",
    "count_files_recursive",
    "add_dummy_child",
    "has_dummy_child",
    "remove_dummy_children",
    "update_item_count",
    "add_folder_to_tree",
    "add_file_to_tree",
    "populate_tree_with_local_folder",
    "add_remote_folder_to_tree",
    "add_remote_file_to_tree",
    "populate_tree_with_remote_files",
]
