"""
HierarchicalManagerView - Base class for managers with hierarchical TreeView

Provides common structure for Queries, Scripts, and Jobs managers:
- Toolbar at top
- Left panel: Pinnable tree view (Category > Items)
- Right panel: Details form + Content area (splitter)

Subclasses must implement:
- _get_explorer_title() -> str: Title for left panel
- _get_explorer_icon() -> str: Icon name for left panel
- _get_item_type() -> str: Type key for items (e.g., "query", "script", "job")
- _get_category_field() -> str: Field name for grouping (e.g., "category", "script_type")
- _setup_toolbar_buttons(builder): Add manager-specific toolbar buttons
- _setup_detail_fields(form_builder): Add detail form fields
- _setup_content_widgets(layout): Add content area widgets
- _load_items() -> list: Load items from database
- _get_item_category(item) -> str: Get category value from item
- _get_item_name(item) -> str: Get display name from item
- _display_item(item): Display item in details/content
- _clear_item_display(): Clear details/content display
"""

from abc import ABCMeta, abstractmethod
from typing import Dict, List, Optional, Any
import uuid

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from ...widgets.toolbar_builder import ToolbarBuilder


# Combined metaclass for QWidget and ABC
class QWidgetABCMeta(type(QWidget), ABCMeta):
    """Combined metaclass for QWidget and ABC."""
    pass
from ...widgets.form_builder import FormBuilder
from ...widgets.dialog_helper import DialogHelper
from ...widgets.pinnable_panel import PinnablePanel
from ...core.i18n_bridge import tr
from ....database.config_db import get_config_db
from ....utils.image_loader import get_icon

import logging
logger = logging.getLogger(__name__)


class HierarchicalManagerView(QWidget, metaclass=QWidgetABCMeta):
    """
    Abstract base class for hierarchical manager views.

    Provides common UI structure and behavior for managers that display
    items organized in categories (folders) with a tree view on the left
    and details/content on the right.
    """

    # Signal emitted when item is selected (emits the item object)
    item_selected = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._current_item = None
        self._category_items: Dict[str, QTreeWidgetItem] = {}
        self._workspace_filter: Optional[str] = None  # Workspace filter ID

        self._setup_ui()
        self.refresh()

    # ==================== Workspace Filtering ====================

    def set_workspace_filter(self, workspace_id: Optional[str]):
        """
        Set workspace filter and refresh the view.

        Args:
            workspace_id: Workspace ID to filter by, or None for all items
        """
        self._workspace_filter = workspace_id
        self.refresh()

    def get_workspace_filter(self) -> Optional[str]:
        """Get the current workspace filter ID."""
        return self._workspace_filter

    # ==================== Abstract Methods ====================

    @abstractmethod
    def _get_explorer_title(self) -> str:
        """Return title for the left panel explorer."""
        pass

    @abstractmethod
    def _get_explorer_icon(self) -> str:
        """Return icon name for the left panel explorer."""
        pass

    @abstractmethod
    def _get_item_type(self) -> str:
        """Return the type key for items (e.g., 'query', 'script', 'job')."""
        pass

    @abstractmethod
    def _get_category_field(self) -> str:
        """Return the field name used for grouping (e.g., 'category', 'script_type')."""
        pass

    @abstractmethod
    def _setup_toolbar_buttons(self, builder: ToolbarBuilder):
        """
        Add manager-specific toolbar buttons.

        Args:
            builder: ToolbarBuilder instance to add buttons to
        """
        pass

    @abstractmethod
    def _setup_detail_fields(self, form_builder: FormBuilder):
        """
        Add detail form fields.

        Args:
            form_builder: FormBuilder instance to add fields to
        """
        pass

    @abstractmethod
    def _setup_content_widgets(self, layout: QVBoxLayout):
        """
        Add content area widgets (editor, log panel, etc.).

        Args:
            layout: Layout to add widgets to
        """
        pass

    @abstractmethod
    def _load_items(self) -> List[Any]:
        """
        Load items from database.

        Returns:
            List of items to display in tree
        """
        pass

    @abstractmethod
    def _get_item_category(self, item: Any) -> str:
        """
        Get category value from an item.

        Args:
            item: The item object

        Returns:
            Category string (used for grouping in tree)
        """
        pass

    @abstractmethod
    def _get_item_name(self, item: Any) -> str:
        """
        Get display name from an item.

        Args:
            item: The item object

        Returns:
            Display name string
        """
        pass

    @abstractmethod
    def _display_item(self, item: Any):
        """
        Display an item in the details form and content area.

        Args:
            item: The item to display
        """
        pass

    @abstractmethod
    def _clear_item_display(self):
        """Clear all details and content display."""
        pass

    # ==================== UI Setup ====================

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toolbar
        self._setup_toolbar()
        layout.addWidget(self.toolbar)

        # Main splitter (horizontal: left tree, right content)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Pinnable panel with hierarchical tree
        self._setup_left_panel()
        self.main_splitter.addWidget(self.left_panel)

        # Right panel: Details + Content
        self._setup_right_panel()
        self.main_splitter.addWidget(self.right_splitter)

        self.main_splitter.setSizes([250, 750])
        layout.addWidget(self.main_splitter)

    def _setup_toolbar(self):
        """Setup toolbar with common structure."""
        builder = ToolbarBuilder(self)

        # Refresh is always first
        builder.add_button(tr("btn_refresh"), self.refresh, icon="refresh.png")
        builder.add_separator()

        # Let subclass add its buttons
        self._setup_toolbar_buttons(builder)

        self.toolbar = builder.build()

    def _setup_left_panel(self):
        """Setup left panel with pinnable tree."""
        self.left_panel = PinnablePanel(
            title=self._get_explorer_title(),
            icon_name=self._get_explorer_icon()
        )
        self.left_panel.set_normal_width(250)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        tree_layout.addWidget(self.tree)

        self.left_panel.set_content(tree_container)

    def _setup_right_panel(self):
        """Setup right panel with details and content."""
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Details panel
        self.details_panel = QWidget()
        self.details_layout = QVBoxLayout(self.details_panel)
        self.details_layout.setContentsMargins(5, 5, 5, 5)
        self._setup_details()
        self.right_splitter.addWidget(self.details_panel)

        # Content panel
        self.content_panel = QWidget()
        self.content_layout = QVBoxLayout(self.content_panel)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self._setup_content_widgets(self.content_layout)
        self.right_splitter.addWidget(self.content_panel)

        self.right_splitter.setSizes([150, 400])

    def _setup_details(self):
        """Setup details panel with form fields."""
        self.details_form = FormBuilder(title=self._get_details_title())
        self._setup_detail_fields(self.details_form)
        self.details_layout.addWidget(self.details_form.container)

    def _get_details_title(self) -> str:
        """Get title for details panel. Override if needed."""
        return tr(f"{self._get_item_type()}_details")

    # ==================== Tree Operations ====================

    def get_tree_widget(self) -> QTreeWidget:
        """Return the tree widget for embedding."""
        return self.tree

    def refresh(self):
        """Reload all items from database."""
        self.tree.clear()
        self._category_items.clear()
        self._current_item = None
        self._clear_item_display()
        self._populate_tree()

    def _populate_tree(self):
        """Populate tree with items grouped by category."""
        try:
            items = self._load_items()

            # Group items by category
            categories: Dict[str, List[Any]] = {}
            for item in items:
                cat = self._get_item_category(item) or self._get_default_category()
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            # Create tree structure
            folder_icon = get_icon("Category", size=16)
            item_icon = get_icon(self._get_explorer_icon(), size=16)
            item_type = self._get_item_type()

            for category_name in sorted(categories.keys()):
                items_in_cat = categories[category_name]

                # Create category folder
                category_item = QTreeWidgetItem(self.tree)
                category_item.setText(0, f"{category_name} ({len(items_in_cat)})")
                if folder_icon:
                    category_item.setIcon(0, folder_icon)
                category_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "category",
                    "name": category_name
                })
                category_item.setExpanded(True)
                self._category_items[category_name] = category_item

                # Add items under category
                for item in sorted(items_in_cat, key=lambda i: self._get_item_name(i)):
                    tree_item = QTreeWidgetItem(category_item)
                    tree_item.setText(0, self._get_item_name(item))
                    if item_icon:
                        tree_item.setIcon(0, item_icon)
                    tree_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": item_type,
                        "item": item
                    })

        except Exception as e:
            logger.error(f"Error loading items: {e}")

    def _get_default_category(self) -> str:
        """Get default category name for items without category."""
        return tr("no_category") if tr("no_category") != "no_category" else "No category"

    # ==================== Event Handlers ====================

    def _on_item_clicked(self, tree_item: QTreeWidgetItem, column: int):
        """Handle single click on tree item."""
        data = tree_item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == self._get_item_type():
            self._current_item = data.get("item")
            self._display_item(self._current_item)
            self.item_selected.emit(self._current_item)

    def _on_item_double_clicked(self, tree_item: QTreeWidgetItem, column: int):
        """
        Handle double-click on tree item.

        Override in subclass for custom behavior (e.g., execute query).
        Default: same as single click.
        """
        data = tree_item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data.get("type") == self._get_item_type():
            self._current_item = data.get("item")
            self._on_item_action(self._current_item)

    def _on_item_action(self, item: Any):
        """
        Handle primary action on item (e.g., double-click).

        Override in subclass for custom behavior.
        """
        pass

    def _on_context_menu(self, position):
        """Handle context menu request on tree item."""
        tree_item = self.tree.itemAt(position)
        if not tree_item:
            return

        data = tree_item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)
        item_type = self._get_item_type()

        if data.get("type") == "category":
            # Context menu for category folder
            self._build_category_context_menu(menu, data.get("name"))

        elif data.get("type") == item_type:
            # Context menu for item
            item = data.get("item")
            self._current_item = item
            self._build_item_context_menu(menu, item)

        if menu.actions():
            menu.exec(self.tree.viewport().mapToGlobal(position))

    def _build_category_context_menu(self, menu: QMenu, category_name: str):
        """
        Build context menu for category folder.

        Override in subclass to add actions.
        """
        pass

    def _build_item_context_menu(self, menu: QMenu, item: Any):
        """
        Build context menu for an item.

        Override in subclass to add actions.
        """
        pass

    # ==================== Workspace Integration ====================

    def _build_workspace_submenu(self, item_id: str) -> Optional[QMenu]:
        """
        Build a submenu for adding/removing an item to/from workspaces.

        Override in subclass to implement workspace support.

        Args:
            item_id: ID of the item

        Returns:
            QMenu with workspace options, or None if not supported
        """
        return None

    # ==================== Utility Methods ====================

    def get_current_item(self) -> Optional[Any]:
        """Get the currently selected item."""
        return self._current_item

    def select_item_by_id(self, item_id: str) -> bool:
        """
        Select an item in the tree by its ID.

        Args:
            item_id: ID of the item to select

        Returns:
            True if item was found and selected
        """
        item_type = self._get_item_type()

        def find_in_tree(parent_item: QTreeWidgetItem) -> bool:
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("type") == item_type:
                    item = data.get("item")
                    if hasattr(item, 'id') and item.id == item_id:
                        self.tree.setCurrentItem(child)
                        self._on_item_clicked(child, 0)
                        return True
                if child.childCount() > 0:
                    if find_in_tree(child):
                        return True
            return False

        # Search in root items
        for i in range(self.tree.topLevelItemCount()):
            if find_in_tree(self.tree.topLevelItem(i)):
                return True

        return False
