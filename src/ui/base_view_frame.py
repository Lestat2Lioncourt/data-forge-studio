"""
BaseViewFrame - Base class for all view frames with consistent layout
Provides standard structure: Toolbar + PanedWindow(Left TreeView, Right Top/Bottom)
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Callable, Optional


class BaseViewFrame(ttk.Frame):
    """
    Base class for all view frames

    Standard layout:
    - Toolbar at top
    - Main horizontal PanedWindow:
      - Left: TreeView frame (parent provides)
      - Right: Vertical PanedWindow:
        - Top: Content frame
        - Bottom: Content frame
    """

    def __init__(self, parent,
                 toolbar_buttons: List[Tuple[str, Callable]] = None,
                 show_left_panel: bool = True,
                 left_weight: int = 1,
                 right_weight: int = 2,
                 top_weight: int = 1,
                 bottom_weight: int = 1):
        """
        Initialize BaseViewFrame

        Args:
            parent: Parent widget
            toolbar_buttons: List of (label, callback) tuples for toolbar buttons
            show_left_panel: Whether to show left panel (TreeView area)
            left_weight: Weight for left panel in horizontal split
            right_weight: Weight for right panel in horizontal split
            top_weight: Weight for top panel in vertical split
            bottom_weight: Weight for bottom panel in vertical split
        """
        super().__init__(parent)

        self.toolbar_buttons = toolbar_buttons or []
        self.show_left_panel = show_left_panel
        self.left_weight = left_weight
        self.right_weight = right_weight
        self.top_weight = top_weight
        self.bottom_weight = bottom_weight

        # References to main components
        self.toolbar_frame = None
        self.main_paned = None
        self.left_frame = None
        self.right_paned = None
        self.top_frame = None
        self.bottom_frame = None

        self._create_base_widgets()

    def _create_base_widgets(self):
        """Create base widget structure"""
        # Toolbar
        if self.toolbar_buttons:
            self.toolbar_frame = ttk.Frame(self, padding="5")
            self.toolbar_frame.pack(fill=tk.X)

            for label, callback in self.toolbar_buttons:
                btn = ttk.Button(self.toolbar_frame, text=label, command=callback)
                btn.pack(side=tk.LEFT, padx=2)

        # Main horizontal PanedWindow
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel (TreeView area)
        if self.show_left_panel:
            self.left_frame = ttk.Frame(self.main_paned, width=350)
            self.main_paned.add(self.left_frame, weight=self.left_weight)

        # Right: Vertical PanedWindow
        self.right_paned = ttk.PanedWindow(self.main_paned, orient=tk.VERTICAL)
        self.main_paned.add(self.right_paned, weight=self.right_weight)

        # Top frame
        self.top_frame = ttk.Frame(self.right_paned)
        self.right_paned.add(self.top_frame, weight=self.top_weight)

        # Bottom frame
        self.bottom_frame = ttk.Frame(self.right_paned)
        self.right_paned.add(self.bottom_frame, weight=self.bottom_weight)

    def create_left_content(self):
        """Override this method to populate left panel (TreeView)"""
        pass

    def create_top_content(self):
        """Override this method to populate top right panel"""
        pass

    def create_bottom_content(self):
        """Override this method to populate bottom right panel"""
        pass

    # ===== Helper Methods for Creating Standard UI Elements =====

    @staticmethod
    def create_panel_title(parent, text: str, font_size: int = 10) -> ttk.Label:
        """
        Create standardized panel title label

        Args:
            parent: Parent widget
            text: Title text
            font_size: Font size (default: 10)

        Returns:
            ttk.Label: Created title label
        """
        label = ttk.Label(parent, text=text, font=("Arial", font_size, "bold"))
        label.pack(pady=5)
        return label

    @staticmethod
    def create_detail_grid(parent, padding: str = "5") -> ttk.Frame:
        """
        Create standardized details grid frame

        This creates a frame suitable for label-value pairs in a grid layout.
        Column 1 is automatically configured to expand.

        Args:
            parent: Parent widget
            padding: Frame padding (default: "5")

        Returns:
            ttk.Frame: Created details frame with column 1 expandable
        """
        frame = ttk.Frame(parent, padding=padding)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        return frame

    @staticmethod
    def add_detail_row(parent_grid: ttk.Frame, row: int, label_text: str, value_widget: tk.Widget = None,
                      label_font: tuple = ("Arial", 9, "bold")) -> Optional[ttk.Label]:
        """
        Add a detail row to a grid (label + value)

        Args:
            parent_grid: Parent grid frame (created with create_detail_grid)
            row: Row number
            label_text: Text for the label
            value_widget: Optional value widget to place in column 1. If None, returns a Label for manual setup.
            label_font: Font for label (default: bold Arial 9)

        Returns:
            ttk.Label or None: Value label if value_widget is None, otherwise None
        """
        # Create label
        ttk.Label(parent_grid, text=label_text, font=label_font).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )

        # If value_widget provided, place it
        if value_widget:
            value_widget.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
            return None
        else:
            # Create and return a value label for manual setup
            value_label = ttk.Label(parent_grid, text="", font=("Arial", 9))
            value_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=5)
            return value_label
