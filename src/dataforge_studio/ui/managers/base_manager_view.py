"""
Base Manager View - Base class for all manager views
Provides common structure and functionality for Queries, Scripts, Jobs managers
"""

from typing import Optional, List, Any, Tuple
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.custom_treeview import CustomTreeView
from ..widgets.pinnable_panel import PinnablePanel
from ..widgets.dialog_helper import DialogHelper
from ..utils.item_data_wrapper import ItemDataWrapper
from ..utils.ui_helper import UIHelper


class BaseManagerView(QWidget):
    """
    Base class for all manager views (queries, scripts, jobs).

    Provides a standard layout:
    - Toolbar at the top
    - Main horizontal splitter:
      - Left: Pinnable panel with tree view for items list
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

    Subclasses may override:
    - _get_panel_title() -> str: Title for the left pinnable panel
    - _get_panel_icon() -> str: Icon name for the left pinnable panel
    """

    # Signals
    item_selected = Signal(object)  # Emitted when item is selected (passes item data)

    def __init__(self, parent: Optional[QWidget] = None, title: str = "Manager", enable_details_panel: bool = True):
        """
        Initialize base manager view.

        Args:
            parent: Parent widget (optional)
            title: Manager title
            enable_details_panel: If True, right panel has details+content split. If False, only content panel.
        """
        super().__init__(parent)
        self.title = title
        self._current_item = None
        self.enable_details_panel = enable_details_panel
        self._setup_base_ui()

    def _get_panel_title(self) -> str:
        """Return title for the left pinnable panel. Override in subclasses."""
        return self.title

    def _get_panel_icon(self) -> Optional[str]:
        """Return icon name for the left pinnable panel. Override in subclasses."""
        return None

    def _setup_base_ui(self):
        """Setup base UI structure."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove outer margins
        layout.setSpacing(2)  # Minimal spacing between widgets

        # Toolbar (placeholder - subclasses will replace)
        self.toolbar = ToolbarBuilder(self).build()
        layout.addWidget(self.toolbar)

        # Main splitter (horizontal: left tree, right content or details+content)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Pinnable panel with tree view
        self.left_panel = PinnablePanel(
            title=self._get_panel_title(),
            icon_name=self._get_panel_icon()
        )
        self.left_panel.set_normal_width(280)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        self.tree_view = CustomTreeView(
            columns=self._get_tree_columns(),
            on_select=self._on_tree_select,
            on_double_click=self._on_tree_double_click
        )
        tree_layout.addWidget(self.tree_view)

        self.left_panel.set_content(tree_container)
        self.main_splitter.addWidget(self.left_panel)

        if self.enable_details_panel:
            # Right panel: Vertical splitter (top: details, bottom: content)
            self.right_splitter = QSplitter(Qt.Orientation.Vertical)

            # Top: Details panel (subclasses will populate)
            self.details_panel = QWidget()
            self.details_layout = QVBoxLayout(self.details_panel)
            self.details_layout.setContentsMargins(5, 5, 5, 5)  # Minimal margins
            self.details_layout.setSpacing(2)
            self.right_splitter.addWidget(self.details_panel)

            # Bottom: Content panel (subclasses will populate)
            self.content_panel = QWidget()
            self.content_layout = QVBoxLayout(self.content_panel)
            self.content_layout.setContentsMargins(5, 5, 5, 5)  # Minimal margins
            self.content_layout.setSpacing(2)
            self.right_splitter.addWidget(self.content_panel)

            self.main_splitter.addWidget(self.right_splitter)

            # Set splitter proportions
            self.main_splitter.setSizes([300, 700])
            self.right_splitter.setSizes([150, 850])  # Details panel smaller
        else:
            # Right panel: Only content panel (no details)
            self.details_panel = None
            self.details_layout = None
            self.right_splitter = None

            self.content_panel = QWidget()
            self.content_layout = QVBoxLayout(self.content_panel)
            self.content_layout.setContentsMargins(5, 5, 5, 5)
            self.content_layout.setSpacing(2)

            self.main_splitter.addWidget(self.content_panel)

            # Set splitter proportions (30% left, 70% right)
            self.main_splitter.setSizes([300, 700])

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
        """Setup details panel. Subclasses must implement if enable_details_panel=True."""
        if self.enable_details_panel:
            raise NotImplementedError("Subclasses must implement _setup_details when enable_details_panel=True")
        # If details panel disabled, this method can be empty
        pass

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

    # Utility methods for subclasses

    def _replace_toolbar(self, toolbar_builder: ToolbarBuilder):
        """
        Replace the default toolbar with a customized one.

        Eliminates repeated pattern:
            old_toolbar = self.toolbar
            self.toolbar = toolbar_builder.build()
            self.layout().replaceWidget(old_toolbar, self.toolbar)
            old_toolbar.setParent(None)

        Args:
            toolbar_builder: Configured ToolbarBuilder instance
        """
        old_toolbar = self.toolbar
        self.toolbar = toolbar_builder.build()
        self.layout().replaceWidget(old_toolbar, self.toolbar)
        old_toolbar.setParent(None)

    def _check_item_selected(self, warning_message: str, title: str) -> bool:
        """
        Check if an item is selected, show warning if not.

        Eliminates repeated pattern:
            if not self._current_item:
                DialogHelper.warning(message, title, self)
                return

        Args:
            warning_message: Message to display if no item selected
            title: Dialog title

        Returns:
            True if item is selected, False otherwise
        """
        if not self._current_item:
            DialogHelper.warning(warning_message, title, self)
            return False
        return True

    def _wrap_item(self, item_data: Any = None) -> ItemDataWrapper:
        """
        Wrap item data for unified access.

        Args:
            item_data: Item data to wrap (defaults to _current_item)

        Returns:
            ItemDataWrapper instance
        """
        data = item_data if item_data is not None else self._current_item
        return ItemDataWrapper(data)

    def _get_item_name(self, item_data: Any = None) -> str:
        """
        Get item name from current or specified item.

        Eliminates repeated pattern:
            if isinstance(item, dict):
                name = item.get("name", "")
            else:
                name = getattr(item, "name", "")

        Args:
            item_data: Item to get name from (defaults to _current_item)

        Returns:
            Item name or empty string
        """
        return self._wrap_item(item_data).get_str("name")

    def _handle_error(self, operation: str, error: Exception, show_dialog: bool = True):
        """
        Standard error handling pattern.

        Logs error and optionally shows dialog.

        Args:
            operation: Description of operation that failed
            error: Exception that was raised
            show_dialog: If True, show error dialog to user
        """
        import logging
        logger = logging.getLogger(self.__class__.__name__)
        logger.error(f"{operation} failed: {error}")

        if show_dialog:
            DialogHelper.error(
                f"{operation} failed.",
                parent=self,
                details=str(error)
            )

    def _confirm_action(self, message: str, title: str = "Confirm") -> bool:
        """
        Show confirmation dialog for destructive actions.

        Args:
            message: Confirmation message
            title: Dialog title

        Returns:
            True if user confirmed, False otherwise
        """
        return DialogHelper.confirm(message, title, self)

    def _show_success(self, message: str):
        """
        Show success message to user.

        Args:
            message: Success message
        """
        DialogHelper.info(message, parent=self)
