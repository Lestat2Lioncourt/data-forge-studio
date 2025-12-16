"""
Custom Tree View - Simplified QTreeWidget wrapper
Provides convenient API similar to the original TKinter TreeView
"""

from typing import Optional, Callable, List, Any
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QHeaderView
from PySide6.QtCore import Signal, Qt


class CustomTreeView(QWidget):
    """
    Custom tree view widget with convenient API.

    Wraps QTreeWidget to provide a simpler API similar to the original
    TKinter ttk.Treeview, making migration easier.

    Signals:
        selection_changed(list): Emitted when selection changes (list of items)
        item_double_clicked(QTreeWidgetItem, int): Emitted on double-click (item, column)
    """

    # Signals
    selection_changed = Signal(list)  # List of selected QTreeWidgetItem
    item_double_clicked = Signal(QTreeWidgetItem, int)  # Item, column index

    def __init__(self, parent: Optional[QWidget] = None,
                 columns: Optional[List[str]] = None,
                 on_select: Optional[Callable] = None,
                 on_double_click: Optional[Callable] = None,
                 show_headers: bool = True):
        """
        Initialize custom tree view.

        Args:
            parent: Parent widget (optional)
            columns: List of column names (optional)
            on_select: Callback for selection change (optional)
            on_double_click: Callback for double-click (optional)
            show_headers: Whether to show column headers (default: True)
        """
        super().__init__(parent)

        self._setup_ui(columns, show_headers)

        # Connect callbacks
        if on_select:
            self.selection_changed.connect(on_select)
        if on_double_click:
            self.item_double_clicked.connect(on_double_click)

    def _setup_ui(self, columns: Optional[List[str]], show_headers: bool):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tree widget
        self.tree = QTreeWidget()

        # Let global theme handle colors - no hardcoded styles

        if columns:
            self.tree.setColumnCount(len(columns))
            self.tree.setHeaderLabels(columns)

            if show_headers:
                self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            else:
                self.tree.setHeaderHidden(True)

        # Enable features
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.tree.setRootIsDecorated(False)  # No branch decoration for root items

        layout.addWidget(self.tree)

        # Connect internal signals
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_double_clicked)

    def _on_selection_changed(self):
        """Internal handler for selection changes."""
        selected = self.tree.selectedItems()
        self.selection_changed.emit(selected)

    def _on_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Internal handler for double clicks."""
        self.item_double_clicked.emit(item, column)

    def add_item(self, parent: Optional[QTreeWidgetItem], text: List[str],
                data: Optional[Any] = None) -> QTreeWidgetItem:
        """
        Add an item to the tree.

        Args:
            parent: Parent item (None for root level)
            text: List of column values
            data: Optional data to store with item (accessible via get_item_data)

        Returns:
            Created QTreeWidgetItem
        """
        if parent is None:
            item = QTreeWidgetItem(self.tree, text)
        else:
            item = QTreeWidgetItem(parent, text)

        if data is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, data)

        return item

    def clear(self):
        """Clear all items from the tree."""
        self.tree.clear()

    def get_selected(self) -> List[QTreeWidgetItem]:
        """
        Get selected items.

        Returns:
            List of selected QTreeWidgetItem
        """
        return self.tree.selectedItems()

    def get_selected_data(self) -> List[Any]:
        """
        Get data from selected items.

        Returns:
            List of data objects from selected items
        """
        return [item.data(0, Qt.ItemDataRole.UserRole) for item in self.tree.selectedItems()]

    def get_item_data(self, item: QTreeWidgetItem) -> Any:
        """
        Get data stored in an item.

        Args:
            item: Tree widget item

        Returns:
            Stored data or None
        """
        return item.data(0, Qt.ItemDataRole.UserRole)

    def set_column_widths(self, widths: List[int]):
        """
        Set column widths.

        Args:
            widths: List of column widths in pixels
        """
        for i, width in enumerate(widths):
            if i < self.tree.columnCount():
                self.tree.setColumnWidth(i, width)

    def expand_all(self):
        """Expand all items in the tree."""
        self.tree.expandAll()

    def collapse_all(self):
        """Collapse all items in the tree."""
        self.tree.collapseAll()

    def set_selection_mode(self, mode: str):
        """
        Set selection mode.

        Args:
            mode: "single", "multi", or "extended"
        """
        if mode == "single":
            self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        elif mode == "multi":
            self.tree.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        elif mode == "extended":
            self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)

    def set_sortable(self, enabled: bool = True):
        """
        Enable/disable column sorting.

        Args:
            enabled: Whether to enable sorting
        """
        self.tree.setSortingEnabled(enabled)

    def apply_theme_style(self, stylesheet: str):
        """
        Apply QSS stylesheet to the tree.

        Args:
            stylesheet: QSS stylesheet string
        """
        self.tree.setStyleSheet(stylesheet)
