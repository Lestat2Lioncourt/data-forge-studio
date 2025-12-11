"""
Theme Editor Dialog - Create and edit custom themes
"""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import logging
from ..config.theme_manager import get_theme_manager
from ..config.i18n import get_i18n

logger = logging.getLogger(__name__)


class ThemeEditorDialog(tk.Toplevel):
    """
    Theme editor dialog window

    Allows users to:
    - Create new themes by duplicating existing ones
    - Edit custom theme colors
    - Preview theme changes
    """

    def __init__(self, parent, theme_name=None):
        """
        Initialize theme editor dialog

        Args:
            parent: Parent window
            theme_name: Name of theme to edit, or None to create new
        """
        super().__init__(parent)

        self.theme_manager = get_theme_manager()
        self.i18n = get_i18n()

        # Determine if creating new or editing existing
        self.is_new = theme_name is None

        if self.is_new:
            # Duplicate current theme
            current_theme_name = self.theme_manager.get_current_theme_name()
            current_theme = self.theme_manager.get_current_theme()
            self.theme_name = f"{current_theme_name}_copy"
            self.theme_colors = dict(current_theme.colors)
        else:
            self.theme_name = theme_name
            theme = self.theme_manager.THEMES.get(theme_name)
            if theme:
                self.theme_colors = dict(theme.colors)
            else:
                # Try to load custom theme
                loaded_theme = self.theme_manager.load_custom_theme(theme_name)
                if loaded_theme:
                    self.theme_colors = dict(loaded_theme)
                else:
                    # Fallback: use current theme if loading failed
                    logger.warning(f"Failed to load theme '{theme_name}', using current theme as fallback")
                    current_theme = self.theme_manager.get_current_theme()
                    self.theme_colors = dict(current_theme.colors)

        self.theme_name_var = tk.StringVar(value=self.theme_name)
        self.color_entries = {}

        self._create_ui()
        self._center_window()

        logger.info(f"Theme editor opened: {'new' if self.is_new else theme_name}")

    def _create_ui(self):
        """Create the dialog UI"""
        title = "Create New Theme" if self.is_new else f"Edit Theme: {self.theme_name}"
        self.title(title)
        self.geometry("800x600")

        # Make dialog modal
        self.transient(self.master)
        self.grab_set()

        # Main container
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Theme name section
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(name_frame, text="Theme Name:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        name_entry = ttk.Entry(name_frame, textvariable=self.theme_name_var, width=30)
        name_entry.pack(side=tk.LEFT)

        # Color selection area with scrollable canvas
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Create canvas with scrollbar
        canvas = tk.Canvas(canvas_frame, bg='white')
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        # Bind mouse wheel events
        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows/Mac
        canvas.bind_all("<Button-4>", _on_mousewheel_linux)  # Linux scroll up
        canvas.bind_all("<Button-5>", _on_mousewheel_linux)  # Linux scroll down

        # Store canvas for cleanup
        self.canvas = canvas

        # Group colors by window/function (user-friendly organization)
        color_categories = {
            "Global / Application": [
                "bg", "fg",  # Base colors
                "panel_bg", "frame_bg",
                "button_bg", "button_fg", "button_active_bg", "button_active_fg",
                "scrollbar_bg", "scrollbar_fg",
                "paned_sash_bg", "paned_sash_hover_bg",  # Resize bars
                "accent", "accent_light", "accent_dark"
            ],
            "Data Explorer (folders tree)": [
                "tree_bg", "tree_fg",  # Background and text of folders
                "tree_select_bg", "tree_select_fg",  # Selected folder
                "tree_alt_row",  # Alternating row color
                "data_explorer_frame_bg", "data_explorer_frame_fg"
            ],
            "Databases (databases list)": [
                "tree_bg", "tree_fg",  # Uses same tree as Data Explorer
                "tree_select_bg", "tree_select_fg",
                "databases_frame_bg", "databases_frame_fg"
            ],
            "Query Results / Data Tables": [
                "grid_bg", "grid_fg",  # Data cells
                "grid_header_bg", "grid_header_fg",  # Column headers
                "grid_select_bg", "grid_select_fg",  # Selected row
                "grid_alt_row", "grid_border"  # Alternating rows and borders
            ],
            "Scripts Window": [
                "scripts_frame_bg", "scripts_frame_fg"
            ],
            "Jobs Window": [
                "jobs_frame_bg", "jobs_frame_fg"
            ],
            "Headers & Toolbars": [
                "header_bg", "header_fg",
                "toolbar_bg"
            ],
            "Dialogs & Inputs": [
                "dialog_bg", "dialog_fg",
                "input_bg", "input_fg", "input_border",
                "select_bg", "select_fg"  # General selection
            ],
            "Status & Notifications": [
                "status_bg", "status_fg",
                "info_bg", "info_fg",
                "tooltip_bg", "tooltip_fg",
                "error_bg", "error_fg",
                "warning_bg", "warning_fg",
                "success_bg", "success_fg"
            ],
            "Other Components": [
                "sidebar_bg", "sidebar_fg",
                "content_frame_bg", "content_frame_fg",
                "hover_bg", "hover_fg",
                "disabled_bg", "disabled_fg"
            ]
        }

        row = 0
        for category, color_keys in color_categories.items():
            # Category header
            ttk.Label(scrollable_frame, text=category, font=("Arial", 10, "bold")).grid(
                row=row, column=0, columnspan=3, sticky=tk.W, pady=(10, 5), padx=5
            )
            row += 1

            # Color entries for this category
            for key in color_keys:
                if key not in self.theme_colors:
                    continue

                # Label
                ttk.Label(scrollable_frame, text=key).grid(
                    row=row, column=0, sticky=tk.W, padx=(20, 5), pady=2
                )

                # Color display box
                color_box = tk.Frame(scrollable_frame, width=30, height=20,
                                    bg=self.theme_colors[key], relief=tk.SOLID, borderwidth=1)
                color_box.grid(row=row, column=1, padx=5, pady=2)
                color_box.grid_propagate(False)  # Force the frame to keep its size

                # Color value entry
                entry = ttk.Entry(scrollable_frame, width=10)
                entry.insert(0, self.theme_colors[key])
                entry.grid(row=row, column=2, padx=5, pady=2)

                # Pick color button
                btn = ttk.Button(scrollable_frame, text="Pick", width=6,
                               command=lambda k=key, e=entry, cb=color_box: self._pick_color(k, e, cb))
                btn.grid(row=row, column=3, padx=5, pady=2)

                self.color_entries[key] = (entry, color_box)
                row += 1

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Preview button
        preview_btn = ttk.Button(
            button_frame,
            text="Preview Theme",
            command=self._preview_theme
        )
        preview_btn.pack(side=tk.LEFT)

        # Right side buttons
        save_btn = ttk.Button(
            button_frame,
            text="Save Theme",
            command=self._save_theme,
            width=12
        )
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_close,
            width=12
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Bind escape key to cancel
        self.bind('<Escape>', lambda e: self._on_close())

        # Cleanup bindings on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Clean up mouse wheel bindings before closing"""
        try:
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
        except:
            pass
        self.destroy()

    def _center_window(self):
        """Center the dialog on the parent window"""
        self.update_idletasks()

        # Get parent window position and size
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        # Get dialog size
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"+{x}+{y}")

    def _pick_color(self, key, entry, color_box):
        """Open color picker dialog"""
        current_color = entry.get()
        color = colorchooser.askcolor(current_color, title=f"Choose color for {key}")

        if color[1]:  # color[1] is hex value
            entry.delete(0, tk.END)
            entry.insert(0, color[1])
            color_box.configure(bg=color[1])
            self.theme_colors[key] = color[1]

    def _preview_theme(self):
        """Preview the theme by temporarily applying it"""
        # Update colors from entries
        for key, (entry, color_box) in self.color_entries.items():
            color = entry.get()
            if color.startswith('#') and len(color) == 7:
                self.theme_colors[key] = color
                color_box.configure(bg=color)

        # Create temporary theme and apply it
        theme_name = self.theme_name_var.get()
        self.theme_manager.create_theme(theme_name, self.theme_colors, apply_now=True)

        logger.info(f"Previewing theme: {theme_name}")

    def _save_theme(self):
        """Save the theme"""
        theme_name = self.theme_name_var.get().strip()

        if not theme_name:
            messagebox.showerror("Error", "Theme name cannot be empty")
            return

        # Validate theme name
        if not theme_name.replace('_', '').isalnum():
            messagebox.showerror("Error", "Theme name can only contain letters, numbers, and underscores")
            return

        # Check if overwriting built-in theme
        if theme_name in ['classic_light', 'dark_professional', 'azure_blue']:
            if not messagebox.askyesno("Warning",
                f"'{theme_name}' is a built-in theme. This will create a custom version. Continue?"):
                return

        # Update colors from entries
        for key, (entry, color_box) in self.color_entries.items():
            color = entry.get()
            if color.startswith('#') and len(color) == 7:
                self.theme_colors[key] = color

        # Save theme
        try:
            self.theme_manager.save_theme(theme_name, self.theme_colors)
            self.theme_manager.create_theme(theme_name, self.theme_colors, apply_now=True)

            messagebox.showinfo("Success", f"Theme '{theme_name}' saved successfully!")
            logger.info(f"Theme saved: {theme_name}")
            self.destroy()

        except Exception as e:
            logger.error(f"Error saving theme: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to save theme: {str(e)}")
