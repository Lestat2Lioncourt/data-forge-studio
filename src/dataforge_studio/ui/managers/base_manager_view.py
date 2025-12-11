"""
Base Manager View - Base class for all manager views
Provides common structure and functionality for Queries, Scripts, Jobs managers
"""

from typing import Optional, List, Any
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.custom_treeview import CustomTreeView


class BaseManagerView(QWidget):
    """
    Base class for all manager views (queries, scripts, jobs).

    Provides a standard layout:
    - Toolbar at the top
    - Main horizontal splitter:
      - Left: Tree view for items list
      - Right: Vertical splitter:
        - Top: Details panel
        - Bottom: Content panel

    Subclasses must implement:
    - _get_tree_columns() -> List[str]
    - _load_items()
    - _display_item(item_data)
    - _setup_toolbar()
    - _setup_details()
    - _setup_content()
    """

    # Signals
    item_selected = Signal(object)  # Emitted when item is selected (passes item data)

    def __init__(self, parent: Optional[QWidget] = None, title: str = "Manager"):
        """
        Initialize base manager view.

        Args:
            parent: Parent widget (optional)
            title: Manager title
        """
        super().__init__(parent)
        self.title = title
        self._current_item = None
        self._setup_base_ui()

    def _setup_base_ui(self):
        """Setup base UI structure."""
        layout = QVBoxLayout(self)

        # Toolbar (placeholder - subclasses will replace)
        self.toolbar = ToolbarBuilder(self).build()
        layout.addWidget(self.toolbar)

        # Main splitter (horizontal: left tree, right details+content)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Tree view
        self.tree_view = CustomTreeView(
            columns=self._get_tree_columns(),
            on_select=self._on_tree_select,
            on_double_click=self._on_tree_double_click
        )
        self.main_splitter.addWidget(self.tree_view)

        # Right panel: Vertical splitter (top: details, bottom: content)
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: Details panel (subclasses will populate)
        self.details_panel = QWidget()
        self.details_layout = QVBoxLayout(self.details_panel)
        self.right_splitter.addWidget(self.details_panel)

        # Bottom: Content panel (subclasses will populate)
        self.content_panel = QWidget()
        self.content_layout = QVBoxLayout(self.content_panel)
        self.right_splitter.addWidget(self.content_panel)

        self.main_splitter.addWidget(self.right_splitter)

        # Set splitter proportions (30% left, 70% right)
        self.main_splitter.setSizes([300, 700])
        self.right_splitter.setSizes([200, 500])

        layout.addWidget(self.main_splitter)

    # Abstract methods (subclasses must implement)

    def _get_tree_columns(self) -> List[str]:
        """
        Return column names for tree view.

        Returns:
            List of column names
        """
        return ["Name", "Description"]

    def _load_items(self):
        """Load items into tree view. Subclasses must implement."""
        raise NotImplementedError("Subclasses must implement _load_items")

    def _on_tree_select(self, items: List):
        """
        Handle tree selection.

        Args:
            items: List of selected QTreeWidgetItem
        """
        if items:
            item = items[0]
            data = self.tree_view.get_item_data(item)
            self._current_item = data
            self._display_item(data)
            self.item_selected.emit(data)

    def _on_tree_double_click(self, item, column: int):
        """
        Handle tree double click. Subclasses can override.

        Args:
            item: QTreeWidgetItem that was double-clicked
            column: Column index
        """
        pass  # Default: do nothing

    def _display_item(self, item_data: Any):
        """
        Display item details and content. Subclasses must implement.

        Args:
            item_data: Item data object
        """
        raise NotImplementedError("Subclasses must implement _display_item")

    def _setup_toolbar(self):
        """Setup toolbar. Subclasses must implement."""
        raise NotImplementedError("Subclasses must implement _setup_toolbar")

    def _setup_details(self):
        """Setup details panel. Subclasses must implement."""
        raise NotImplementedError("Subclasses must implement _setup_details")

    def _setup_content(self):
        """Setup content panel. Subclasses must implement."""
        raise NotImplementedError("Subclasses must implement _setup_content")

    # Helper methods

    def refresh(self):
        """Refresh the view (reload items from database)."""
        self.tree_view.clear()
        self._load_items()

    def get_selected_item(self) -> Optional[Any]:
        """
        Get currently selected item data.

        Returns:
            Selected item data or None
        """
        return self._current_item

    def clear_selection(self):
        """Clear current selection."""
        self.tree_view.clear()
        self._current_item = None
