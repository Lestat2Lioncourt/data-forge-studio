"""
CustomTreeView - Reusable TreeView component with integrated toolbar
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List, Tuple, Dict


class CustomTreeView(ttk.Frame):
    """
    Reusable TreeView component with integrated mini-toolbar

    Features:
    - Configurable toolbar buttons
    - Horizontal and vertical scrollbars
    - Event callbacks (select, double-click, expand, right-click)
    - Tag configuration support
    """

    def __init__(self, parent, toolbar_buttons: Optional[List[Tuple[str, str, Callable]]] = None, **tree_kwargs):
        """
        Initialize CustomTreeView

        Args:
            parent: Parent widget
            toolbar_buttons: List of (icon, tooltip, callback) tuples for toolbar
            **tree_kwargs: Additional arguments passed to ttk.Treeview
        """
        super().__init__(parent)

        self.toolbar_buttons = toolbar_buttons or []
        self.tree_kwargs = tree_kwargs

        # Callbacks
        self.on_select_callback: Optional[Callable] = None
        self.on_double_click_callback: Optional[Callable] = None
        self.on_expand_callback: Optional[Callable] = None
        self.on_right_click_callback: Optional[Callable] = None

        self._create_widgets()

    def _create_widgets(self):
        """Create toolbar, treeview and scrollbars"""
        # Toolbar frame
        if self.toolbar_buttons:
            toolbar_frame = ttk.Frame(self, padding="5")
            toolbar_frame.pack(fill=tk.X)

            for icon, tooltip, callback in self.toolbar_buttons:
                btn = ttk.Button(toolbar_frame, text=icon, command=callback)
                btn.pack(side=tk.LEFT, padx=2)
                # TODO: Add tooltip support if needed

        # TreeView frame with scrollbars
        tree_container = ttk.Frame(self)
        tree_container.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # TreeView
        self.tree = ttk.Treeview(
            tree_container,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            **self.tree_kwargs
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure scrollbars
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)

        # Bind events
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<<TreeviewOpen>>", self._on_expand)
        self.tree.bind("<Button-3>", self._on_right_click)

    # ==================== Event Handlers ====================

    def _on_select(self, event):
        """Handle selection event"""
        if self.on_select_callback:
            self.on_select_callback(event)

    def _on_double_click(self, event):
        """Handle double-click event"""
        if self.on_double_click_callback:
            self.on_double_click_callback(event)

    def _on_expand(self, event):
        """Handle expand event"""
        if self.on_expand_callback:
            self.on_expand_callback(event)

    def _on_right_click(self, event):
        """Handle right-click event"""
        if self.on_right_click_callback:
            self.on_right_click_callback(event)

    # ==================== Public API ====================

    def set_on_select(self, callback: Callable):
        """Set callback for selection event"""
        self.on_select_callback = callback

    def set_on_double_click(self, callback: Callable):
        """Set callback for double-click event"""
        self.on_double_click_callback = callback

    def set_on_expand(self, callback: Callable):
        """Set callback for expand event"""
        self.on_expand_callback = callback

    def set_on_right_click(self, callback: Callable):
        """Set callback for right-click event"""
        self.on_right_click_callback = callback

    def insert(self, parent, index, **kwargs):
        """Insert item into tree"""
        return self.tree.insert(parent, index, **kwargs)

    def delete(self, *items):
        """Delete items from tree"""
        self.tree.delete(*items)

    def get_children(self, item=""):
        """Get children of item"""
        return self.tree.get_children(item)

    def item(self, item, **kwargs):
        """Configure or query item"""
        return self.tree.item(item, **kwargs)

    def focus(self):
        """Get focused item"""
        return self.tree.focus()

    def selection_set(self, items):
        """Set selection"""
        self.tree.selection_set(items)

    def selection(self):
        """Get current selection"""
        return self.tree.selection()

    def tag_configure(self, tagname, **kwargs):
        """Configure tag"""
        self.tree.tag_configure(tagname, **kwargs)

    def identify_row(self, y):
        """Identify row at y coordinate"""
        return self.tree.identify_row(y)

    def see(self, item):
        """Ensure item is visible"""
        self.tree.see(item)

    def clear(self):
        """Clear all items from tree"""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def apply_theme(self):
        """Apply current theme to treeview"""
        try:
            from ..config.theme_manager import get_theme_manager
            theme = get_theme_manager().get_current_theme()

            # Apply theme colors to tree (using ttk.Style)
            style = ttk.Style()

            # TreeView colors
            style.configure(
                "Treeview",
                background=theme.get('tree_bg'),
                foreground=theme.get('tree_fg'),
                fieldbackground=theme.get('tree_bg')
            )

            # Selection colors
            style.map(
                "Treeview",
                background=[('selected', theme.get('tree_select_bg'))],
                foreground=[('selected', theme.get('tree_select_fg'))]
            )

        except Exception as e:
            # Theme application failed, continue without theme
            import logging
            logging.getLogger(__name__).debug(f"Failed to apply theme to CustomTreeView: {e}")
