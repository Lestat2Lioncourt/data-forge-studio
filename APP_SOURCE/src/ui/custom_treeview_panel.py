"""
CustomTreeViewPanel - Reusable TreeView panel with optional filter
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List


class CustomTreeViewPanel(ttk.Frame):
    """
    Standardized TreeView panel component

    Features:
    - Title label
    - Optional filter combobox
    - TreeView with scrollbar
    - Event binding support (select, double-click, expand, right-click)
    - Direct access to internal TreeView widget

    Usage:
        # Simple usage
        tree_panel = CustomTreeViewPanel(
            parent,
            title="Jobs",
            on_select=self._on_job_select,
            on_double_click=self._on_job_double_click
        )
        tree_panel.pack(fill=tk.BOTH, expand=True)

        # Access TreeView directly
        tree_panel.tree.insert("", "end", text="Item 1")

        # With filter
        tree_panel = CustomTreeViewPanel(
            parent,
            title="Jobs",
            show_filter=True,
            filter_label="Project:",
            filter_values=["All Projects", "Project 1", "Project 2"],
            filter_default_index=0,
            on_filter_change=self._on_filter_change
        )
    """

    def __init__(self,
                 parent,
                 title: str,
                 show_filter: bool = False,
                 filter_label: Optional[str] = None,
                 filter_values: Optional[List[str]] = None,
                 filter_default_index: int = 0,
                 filter_width: int = 15,
                 on_filter_change: Optional[Callable] = None,
                 on_select: Optional[Callable] = None,
                 on_double_click: Optional[Callable] = None,
                 on_expand: Optional[Callable] = None,
                 on_right_click: Optional[Callable] = None,
                 show_tree: str = 'tree',
                 selectmode: str = 'browse'):
        """
        Initialize CustomTreeViewPanel

        Args:
            parent: Parent widget
            title: Title text for the panel
            show_filter: Whether to show filter combobox
            filter_label: Label text for filter (e.g., "Project:")
            filter_values: List of filter options
            filter_default_index: Default selected index in filter
            filter_width: Width of filter combobox
            on_filter_change: Callback when filter selection changes
            on_select: Callback for TreeviewSelect event
            on_double_click: Callback for double-click event
            on_expand: Callback for TreeviewOpen event
            on_right_click: Callback for right-click (Button-3) event
            show_tree: TreeView show parameter ('tree', 'headings', or 'tree headings')
            selectmode: TreeView selectmode ('browse', 'extended', or 'none')
        """
        super().__init__(parent)

        self.title = title
        self.tree = None
        self.filter_combobox = None
        self.filter_var = None

        # Store callbacks
        self.on_filter_change = on_filter_change
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.on_expand = on_expand
        self.on_right_click = on_right_click

        self._create_widgets(
            show_filter,
            filter_label,
            filter_values,
            filter_default_index,
            filter_width,
            show_tree,
            selectmode
        )

    def _create_widgets(self,
                       show_filter: bool,
                       filter_label: Optional[str],
                       filter_values: Optional[List[str]],
                       filter_default_index: int,
                       filter_width: int,
                       show_tree: str,
                       selectmode: str):
        """Create panel widgets"""
        # Title label
        ttk.Label(
            self,
            text=self.title,
            font=("Arial", 10, "bold")
        ).pack(pady=5)

        # Optional filter
        if show_filter and filter_label:
            filter_frame = ttk.Frame(self)
            filter_frame.pack(fill=tk.X, padx=5, pady=5)

            ttk.Label(filter_frame, text=filter_label).pack(side=tk.LEFT)

            self.filter_var = tk.StringVar()
            self.filter_combobox = ttk.Combobox(
                filter_frame,
                textvariable=self.filter_var,
                state='readonly',
                width=filter_width
            )
            self.filter_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

            if filter_values:
                self.filter_combobox['values'] = filter_values
                if 0 <= filter_default_index < len(filter_values):
                    self.filter_combobox.current(filter_default_index)

            # Bind filter change event
            if self.on_filter_change:
                self.filter_combobox.bind("<<ComboboxSelected>>", self._handle_filter_change)

        # TreeView with scrollbar
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=tree_scroll.set,
            show=show_tree,
            selectmode=selectmode
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)

        # Bind events
        if self.on_select:
            self.tree.bind("<<TreeviewSelect>>", self._handle_select)

        if self.on_double_click:
            self.tree.bind("<Double-Button-1>", self._handle_double_click)

        if self.on_expand:
            self.tree.bind("<<TreeviewOpen>>", self._handle_expand)

        if self.on_right_click:
            self.tree.bind("<Button-3>", self._handle_right_click)

    def _handle_filter_change(self, event):
        """Handle filter combobox change"""
        if self.on_filter_change:
            self.on_filter_change(event)

    def _handle_select(self, event):
        """Handle tree selection"""
        if self.on_select:
            self.on_select(event)

    def _handle_double_click(self, event):
        """Handle double-click"""
        if self.on_double_click:
            self.on_double_click(event)

    def _handle_expand(self, event):
        """Handle tree expansion"""
        if self.on_expand:
            self.on_expand(event)

    def _handle_right_click(self, event):
        """Handle right-click"""
        if self.on_right_click:
            self.on_right_click(event)

    def clear(self):
        """Clear all items from tree"""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def get_filter_value(self) -> Optional[str]:
        """
        Get current filter value

        Returns:
            str: Current filter value, or None if no filter
        """
        if self.filter_var:
            return self.filter_var.get()
        return None

    def set_filter_value(self, value: str):
        """
        Set filter value

        Args:
            value: Value to set in filter combobox
        """
        if self.filter_var:
            self.filter_var.set(value)

    def set_filter_values(self, values: List[str], default_index: int = 0):
        """
        Update filter combobox values

        Args:
            values: List of new values
            default_index: Index to select by default
        """
        if self.filter_combobox:
            self.filter_combobox['values'] = values
            if 0 <= default_index < len(values):
                self.filter_combobox.current(default_index)

    def get_selected_item(self) -> Optional[str]:
        """
        Get currently selected tree item

        Returns:
            str: Selected item ID, or None if no selection
        """
        selection = self.tree.selection()
        if selection:
            return selection[0]
        return None

    def get_selected_values(self) -> Optional[tuple]:
        """
        Get values of currently selected tree item

        Returns:
            tuple: Item values, or None if no selection
        """
        item = self.get_selected_item()
        if item:
            return self.tree.item(item, "values")
        return None
