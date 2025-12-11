"""
CustomDataGridView - Reusable data grid component with integrated toolbar
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List, Dict, Any, Callable
import csv
from pathlib import Path
from ..utils.logger import logger

# Counter for unique style names
_style_counter = 0


class CustomDataGridView(ttk.Frame):
    """
    Reusable DataGrid component with integrated mini-toolbar

    Features:
    - Configurable toolbar buttons
    - Data display in table format (Treeview)
    - Horizontal and vertical scrollbars
    - Column sorting (click header)
    - Export to CSV/Excel
    - Copy selection
    - Fullscreen toggle with animation
    - State preservation (scroll position, sort, selection)
    """

    def __init__(self, parent, show_export=True, show_copy=True,
                 show_raw_toggle=False, on_raw_toggle=None, auto_row_height=True,
                 show_grid_toggle=True, **grid_kwargs):
        """
        Initialize CustomDataGridView

        Args:
            parent: Parent widget
            show_export: Show export button
            show_copy: Show copy button
            show_raw_toggle: Show raw/table toggle button (for CSV)
            on_raw_toggle: Callback for raw/table toggle
            auto_row_height: Automatically adjust row height based on content with line breaks
            show_grid_toggle: Show grid display toggle button (alternating row colors)
            **grid_kwargs: Additional arguments
        """
        super().__init__(parent)

        self.show_export = show_export
        self.show_copy = show_copy
        self.show_raw_toggle = show_raw_toggle
        self.on_raw_toggle_callback = on_raw_toggle
        self.auto_row_height = auto_row_height
        self.show_grid_toggle = show_grid_toggle
        self.grid_display_enabled = False  # Start with grid display off

        # Create unique style name for this instance
        global _style_counter
        self.style_name = f"CustomTreeview{_style_counter}"
        _style_counter += 1

        # State
        self.columns = []
        self.data = []
        self.active_sorts = []  # List of (column_name, direction) tuples for multi-column sort
        self.is_fullscreen = False
        self.saved_state = {}  # Store state before fullscreen
        self.fullscreen_window = None  # Reference to fullscreen Toplevel window
        self.fullscreen_grid = None  # Reference to grid in fullscreen window

        # Callbacks
        self.on_fullscreen_callback: Optional[Callable] = None
        self.on_row_selected_callback: Optional[Callable] = None
        self.on_row_double_click_callback: Optional[Callable] = None

        self._create_widgets()

    def _create_widgets(self):
        """Create toolbar and data grid"""
        # Toolbar frame
        toolbar_frame = ttk.Frame(self, padding="5")
        toolbar_frame.pack(fill=tk.X)

        if self.show_export:
            ttk.Button(toolbar_frame, text="📊 Export", command=self._export_data, width=10).pack(side=tk.LEFT, padx=2)

        if self.show_copy:
            ttk.Button(toolbar_frame, text="📋 Copy", command=self._copy_selection, width=10).pack(side=tk.LEFT, padx=2)

        if self.show_raw_toggle:
            ttk.Button(toolbar_frame, text="🔄 Raw/Table", command=self._toggle_raw_table, width=12).pack(side=tk.LEFT, padx=2)

        if self.show_grid_toggle:
            self.grid_btn = ttk.Button(toolbar_frame, text="⚏ Grid Off", command=self._toggle_grid_display, width=10)
            self.grid_btn.pack(side=tk.LEFT, padx=2)

        # Fullscreen button (always available)
        self.fullscreen_btn = ttk.Button(toolbar_frame, text="⛶ Fullscreen", command=self._toggle_fullscreen, width=12)
        self.fullscreen_btn.pack(side=tk.RIGHT, padx=2)

        # Info label
        self.info_label = ttk.Label(toolbar_frame, text="", foreground="gray", font=("Arial", 8))
        self.info_label.pack(side=tk.LEFT, padx=10)

        # Grid container with scrollbars
        grid_container = ttk.Frame(self)
        grid_container.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(grid_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(grid_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure grid styling with unique style name BEFORE creating the widget
        style = ttk.Style()
        # Copy the layout from the default Treeview style
        style.layout(self.style_name, style.layout("Treeview"))
        # Now configure the style with Consolas monospace font
        style.configure(self.style_name, rowheight=25, font=("Consolas", 9))
        style.configure(f"{self.style_name}.Heading", font=("Consolas", 9, "bold"))

        # Treeview in table mode with unique style
        self.grid = ttk.Treeview(
            grid_container,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            selectmode='extended',
            style=self.style_name
        )
        self.grid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure scrollbars
        v_scrollbar.config(command=self.grid.yview)
        h_scrollbar.config(command=self.grid.xview)

        # Bind events
        self.grid.bind("<Double-Button-1>", self._on_double_click)
        self.grid.bind("<<TreeviewSelect>>", self._on_select)
        self.grid.bind("<Button-1>", self._on_header_click)

    # ==================== Data Management ====================

    def load_data(self, data: List[Dict[str, Any]], columns: Optional[List[str]] = None):
        """
        Load data into grid

        Args:
            data: List of dictionaries (each dict is a row)
            columns: List of column names (if None, use keys from first row)
        """
        # Clear existing data
        self.grid.delete(*self.grid.get_children())

        if not data:
            self.info_label.config(text="No data to display")
            return

        # Determine columns
        if columns is None:
            columns = list(data[0].keys())

        self.columns = columns
        self.data = data

        # Configure columns
        self.grid['columns'] = columns
        self.grid['show'] = 'headings'

        # Set up column headers
        for col in columns:
            self.grid.heading(col, text=col, command=lambda c=col: self._on_column_click(c, False))
            self.grid.column(col, width=100, anchor='w')  # Initial width, will be auto-sized

        # Insert data
        for row_data in data:
            values = [row_data.get(col, '') for col in columns]
            self.grid.insert('', 'end', values=values)

        # Defer autosize to ensure widget is fully rendered (critical for PanedWindows)
        self.after(1, self._autosize_columns)

        # Auto-size row height if enabled
        if self.auto_row_height:
            self.after(1, self._autosize_row_height)

        # Apply grid styling if enabled
        if self.grid_display_enabled:
            self.after(1, self._apply_grid_styling)

        # Update info
        self.info_label.config(text=f"{len(data)} rows × {len(columns)} columns")
        logger.info(f"Loaded {len(data)} rows into CustomDataGridView")

    def load_from_dataframe(self, df):
        """
        Load data from pandas DataFrame

        Args:
            df: pandas DataFrame
        """
        try:
            import pandas as pd
            if not isinstance(df, pd.DataFrame):
                raise ValueError("Input must be a pandas DataFrame")

            # Convert DataFrame to list of dicts
            data = df.to_dict('records')
            columns = list(df.columns)

            self.load_data(data, columns)
        except ImportError:
            logger.error("Pandas not available for DataFrame loading")
            messagebox.showerror("Error", "Pandas library not available")

    def clear(self):
        """Clear all data from grid"""
        self.grid.delete(*self.grid.get_children())
        self.columns = []
        self.data = []
        self.info_label.config(text="")

    def _autosize_columns(self):
        """Auto-size columns based on content"""
        import tkinter.font as tkfont

        # Get font used in treeview (Consolas monospace)
        font = tkfont.Font(family="Consolas", size=9)

        for col in self.columns:
            # Calculate width based on column header
            header_width = font.measure(col) + 20  # Add padding

            # Calculate width based on content (sample first 100 rows for performance)
            max_width = header_width
            for child in list(self.grid.get_children())[:100]:
                values = self.grid.item(child)['values']
                col_index = self.columns.index(col)
                if col_index < len(values):
                    cell_value = str(values[col_index])
                    cell_width = font.measure(cell_value) + 20
                    max_width = max(max_width, cell_width)

            # Set a reasonable max width (500px) and min width (80px)
            max_width = min(max(max_width, 80), 500)

            # CRITICAL: Set stretch=False to force column to respect width
            self.grid.column(col, width=max_width, minwidth=max_width, stretch=False)

        logger.info("Auto-sized columns")

    def _autosize_row_height(self):
        """
        Auto-size row height based on content with line breaks
        Note: All rows will have the same height (Treeview limitation)
        """
        import tkinter.font as tkfont

        # Get font used in treeview (Consolas monospace)
        font = tkfont.Font(family="Consolas", size=9)
        line_height = font.metrics('linespace')

        # Base height with padding
        base_height = 25

        # Find maximum number of lines in any cell (sample first 200 rows for performance)
        max_lines = 1
        for child in list(self.grid.get_children())[:200]:
            values = self.grid.item(child)['values']
            for value in values:
                if value:
                    # Count line breaks in the value
                    value_str = str(value)
                    line_count = value_str.count('\n') + 1
                    max_lines = max(max_lines, line_count)

        # Calculate required height
        # Each line needs line_height, plus some padding
        required_height = max(base_height, (line_height * max_lines) + 10)

        # Cap at reasonable maximum (400px)
        required_height = min(required_height, 400)

        # Apply row height using unique style name for this instance
        style = ttk.Style()
        style.configure(self.style_name, rowheight=required_height)

        logger.info(f"Auto-sized row height to {required_height}px for up to {max_lines} lines (style: {self.style_name})")

    @staticmethod
    def calculate_column_statistics(data: List[Dict[str, Any]], columns: List[str]) -> List[Dict[str, Any]]:
        """
        Calculate column statistics for tabular data

        Args:
            data: List of dictionaries (each dict is a row)
            columns: List of column names

        Returns:
            List of statistics dictionaries with keys:
            - Column: column name
            - Total: total row count
            - Non-Null: count of non-null values (excluding NaN, None, and empty strings)
            - Empty: count of empty values (NaN, None, or empty/whitespace strings)
            - Distinct: count of distinct values
        """
        import math
        stats = []

        for col in columns:
            # Get all values for this column
            values = [row.get(col, None) for row in data]

            # Calculate statistics
            total = len(values)

            # Helper function to check if value is "empty"
            def is_empty(v):
                if v is None:
                    return True
                # Check for pandas NaN (float NaN)
                if isinstance(v, float) and math.isnan(v):
                    return True
                # Check for empty string or whitespace
                if str(v).strip() in ('', 'nan', 'NaN', 'None'):
                    return True
                return False

            # Count empty values
            empty = sum(1 for v in values if is_empty(v))

            # Non-null: total - empty
            non_null = total - empty

            # Distinct: unique non-empty values
            distinct_values = set()
            for v in values:
                if not is_empty(v):
                    distinct_values.add(str(v))
            distinct = len(distinct_values)

            stats.append({
                'Column': col,
                'Total': total,
                'Non-Null': non_null,
                'Empty': empty,
                'Distinct': distinct
            })

        return stats

    # ==================== Sorting ====================

    def _get_column_header_text(self, column_name: str) -> str:
        """Get header text with sort indicator (e.g., '1▲ column_name')"""
        # Find if this column is in active sorts
        for i, (col, direction) in enumerate(self.active_sorts):
            if col == column_name:
                arrow = '▼' if direction == 'DESC' else '▲'
                position = i + 1
                return f"{position}{arrow} {column_name}"

        # Not sorted
        return column_name

    def _on_column_click(self, column_name: str, ctrl_pressed: bool):
        """Handle click on column header for sorting"""
        if ctrl_pressed:
            # Ctrl+click: Add to multi-column sort or toggle existing
            existing_index = None
            for i, (col, direction) in enumerate(self.active_sorts):
                if col == column_name:
                    existing_index = i
                    break

            if existing_index is not None:
                # Toggle direction
                col, current_direction = self.active_sorts[existing_index]
                new_direction = 'DESC' if current_direction == 'ASC' else 'ASC'
                self.active_sorts[existing_index] = (col, new_direction)
            else:
                # Add new column to sort
                self.active_sorts.append((column_name, 'ASC'))
        else:
            # Regular click: Sort only by this column
            # If already sorting by this column only, toggle direction
            if len(self.active_sorts) == 1 and self.active_sorts[0][0] == column_name:
                current_direction = self.active_sorts[0][1]
                new_direction = 'DESC' if current_direction == 'ASC' else 'ASC'
                self.active_sorts = [(column_name, new_direction)]
            else:
                # New sort
                self.active_sorts = [(column_name, 'ASC')]

        # Apply the sort
        self._apply_sort()

    def _apply_sort(self):
        """Apply current sort settings to data and refresh display"""
        if not self.data or not self.active_sorts:
            return

        try:
            # Use Python's stable sort in reverse order of sort columns
            # This is the standard way to do multi-column sorting with mixed ASC/DESC
            # See: https://docs.python.org/3/howto/sorting.html#sort-stability-and-complex-sorts
            for col_name, direction in reversed(self.active_sorts):
                def sort_key(row_dict):
                    val = row_dict.get(col_name, '')
                    # Try to convert to number for proper sorting
                    try:
                        return (0, float(val) if val else 0)  # 0 = numeric type
                    except (ValueError, TypeError):
                        return (1, str(val).lower())  # 1 = string type

                # Sort with reverse flag based on direction
                self.data.sort(key=sort_key, reverse=(direction == 'DESC'))

            # Clear grid and reload data
            self.grid.delete(*self.grid.get_children())
            for row_data in self.data:
                values = [row_data.get(col, '') for col in self.columns]
                self.grid.insert('', 'end', values=values)

            # Re-apply row height if auto-sizing is enabled
            if self.auto_row_height:
                self._autosize_row_height()

            # Apply grid styling if enabled
            if self.grid_display_enabled:
                self._apply_grid_styling()

            # Update headers with visual indicators
            for col in self.columns:
                header_text = self._get_column_header_text(col)
                self.grid.heading(col, text=header_text)

            # Log the sort
            sort_desc = ", ".join(f"{col} {dir}" for col, dir in self.active_sorts)
            logger.info(f"Sorted by: {sort_desc}")

        except Exception as e:
            logger.error(f"Error applying sort: {e}")

    def _on_header_click(self, event):
        """Handle header click for sorting"""
        region = self.grid.identify_region(event.x, event.y)
        if region == "heading":
            column = self.grid.identify_column(event.x)
            col_index = int(column.replace('#', '')) - 1
            if 0 <= col_index < len(self.columns):
                # Check if Ctrl is pressed
                ctrl_pressed = (event.state & 0x0004) != 0
                self._on_column_click(self.columns[col_index], ctrl_pressed)

    def _on_fullscreen_header_click(self, event):
        """Handle header click in fullscreen mode for sorting"""
        if not self.fullscreen_grid:
            return

        region = self.fullscreen_grid.identify_region(event.x, event.y)
        if region == "heading":
            column = self.fullscreen_grid.identify_column(event.x)
            col_index = int(column.replace('#', '')) - 1
            if 0 <= col_index < len(self.columns):
                # Check if Ctrl is pressed
                ctrl_pressed = (event.state & 0x0004) != 0
                # Apply sorting to self.data
                self._on_column_click(self.columns[col_index], ctrl_pressed)
                # Refresh fullscreen display
                self._refresh_fullscreen_display()

    def _refresh_fullscreen_display(self):
        """Refresh fullscreen grid after sorting"""
        if not self.fullscreen_grid or not self.data or not self.columns:
            return

        try:
            # Clear and reload data
            self.fullscreen_grid.delete(*self.fullscreen_grid.get_children())
            for row_data in self.data:
                values = [row_data.get(col, '') for col in self.columns]
                self.fullscreen_grid.insert('', 'end', values=values)

            # Update column headers with sort indicators
            for col in self.columns:
                header_text = self._get_column_header_text(col)
                self.fullscreen_grid.heading(col, text=header_text)

            # Re-apply row height if auto-sizing is enabled
            if self.auto_row_height:
                self._autosize_fullscreen_row_height()

            logger.info("Refreshed fullscreen display after sorting")
        except Exception as e:
            logger.error(f"Error refreshing fullscreen display: {e}")

    # ==================== Export ====================

    def _export_data(self):
        """Export data to CSV or Excel"""
        if not self.data:
            messagebox.showwarning("No Data", "No data to export")
            return

        # Ask user for file path
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        try:
            file_path = Path(file_path)

            if file_path.suffix.lower() == '.csv':
                self._export_to_csv(file_path)
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                self._export_to_excel(file_path)
            else:
                # Default to CSV
                self._export_to_csv(file_path)

            messagebox.showinfo("Success", f"Data exported to {file_path}")
            logger.important(f"Exported data to {file_path}")

        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            messagebox.showerror("Export Error", f"Failed to export data: {e}")

    def _export_to_csv(self, file_path: Path):
        """Export to CSV file"""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(self.data)

    def _export_to_excel(self, file_path: Path):
        """Export to Excel file"""
        try:
            import pandas as pd
            df = pd.DataFrame(self.data, columns=self.columns)
            df.to_excel(file_path, index=False)
        except ImportError:
            messagebox.showerror("Error", "Pandas and openpyxl required for Excel export")
            logger.error("Pandas/openpyxl not available for Excel export")

    # ==================== Copy ====================

    def _copy_selection(self):
        """Copy selected rows to clipboard"""
        selection = self.grid.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select rows to copy")
            return

        # Get selected rows data
        rows = []
        for item in selection:
            values = self.grid.item(item)['values']
            rows.append('\t'.join(str(v) for v in values))

        # Copy to clipboard
        clipboard_text = '\n'.join(rows)
        self.clipboard_clear()
        self.clipboard_append(clipboard_text)

        logger.info(f"Copied {len(selection)} rows to clipboard")
        messagebox.showinfo("Success", f"Copied {len(selection)} rows to clipboard")

    # ==================== Fullscreen ====================

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen

        if self.on_fullscreen_callback:
            # Use custom callback if provided
            self.on_fullscreen_callback(self.is_fullscreen)
        else:
            # Use default implementation
            if self.is_fullscreen:
                self._default_fullscreen_enter()
            else:
                self._default_fullscreen_exit()

        # Update button text
        if self.is_fullscreen:
            self.fullscreen_btn.config(text="⤓ Exit Fullscreen")
        else:
            self.fullscreen_btn.config(text="⛶ Fullscreen")

        logger.info(f"Fullscreen mode: {self.is_fullscreen}")

    def _default_fullscreen_enter(self):
        """Default fullscreen implementation - create Toplevel window with data only"""
        # Create fullscreen window
        self.fullscreen_window = tk.Toplevel(self.winfo_toplevel())
        self.fullscreen_window.title("Data View - Fullscreen")

        # Make it fullscreen
        self.fullscreen_window.attributes('-fullscreen', True)

        # Create container for grid with scrollbars (NO TOOLBAR - data only)
        grid_container = ttk.Frame(self.fullscreen_window)
        grid_container.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(grid_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(grid_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Create Treeview directly (no toolbar)
        self.fullscreen_grid = ttk.Treeview(
            grid_container,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            selectmode='extended',
            style=self.style_name
        )
        self.fullscreen_grid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure scrollbars
        v_scrollbar.config(command=self.fullscreen_grid.yview)
        h_scrollbar.config(command=self.fullscreen_grid.xview)

        # Copy data from original grid to fullscreen grid
        if self.data and self.columns:
            # Configure columns
            self.fullscreen_grid['columns'] = self.columns
            self.fullscreen_grid['show'] = 'headings'

            # Set up column headers with sort indicators and click handlers
            for col in self.columns:
                header_text = self._get_column_header_text(col)
                self.fullscreen_grid.heading(col, text=header_text)
                self.fullscreen_grid.column(col, width=100, anchor='w')

            # Bind click handler for sorting
            self.fullscreen_grid.bind("<Button-1>", self._on_fullscreen_header_click)

            # Insert data (self.data is already sorted by _apply_sort)
            for row_data in self.data:
                values = [row_data.get(col, '') for col in self.columns]
                self.fullscreen_grid.insert('', 'end', values=values)

            # Auto-size columns
            self._autosize_fullscreen_columns()

            # Auto-size row height if enabled
            if self.auto_row_height:
                self._autosize_fullscreen_row_height()

        # Bind Esc to close fullscreen
        self.fullscreen_window.bind("<Escape>", lambda e: self._toggle_fullscreen())

        # Bind window close to exit fullscreen
        self.fullscreen_window.protocol("WM_DELETE_WINDOW", self._default_fullscreen_exit)

        logger.info("Entering fullscreen mode - Data-only view created")

    def _default_fullscreen_exit(self):
        """Exit default fullscreen mode"""
        if self.fullscreen_window:
            self.fullscreen_window.destroy()
            self.fullscreen_window = None
            self.fullscreen_grid = None

            # Reset button state
            self.is_fullscreen = False
            self.fullscreen_btn.config(text="⛶ Fullscreen")

            logger.info("Exited fullscreen mode")

    def _autosize_fullscreen_columns(self):
        """Auto-size columns in fullscreen grid"""
        if not self.fullscreen_grid or not self.columns:
            return

        import tkinter.font as tkfont
        font = tkfont.Font(family="Consolas", size=9)

        for col in self.columns:
            # Calculate width based on column header
            header_width = font.measure(col) + 20

            # Calculate width based on content (sample first 100 rows)
            max_width = header_width
            for child in list(self.fullscreen_grid.get_children())[:100]:
                values = self.fullscreen_grid.item(child)['values']
                col_index = self.columns.index(col)
                if col_index < len(values):
                    cell_value = str(values[col_index])
                    cell_width = font.measure(cell_value) + 20
                    max_width = max(max_width, cell_width)

            # Set reasonable limits
            max_width = min(max(max_width, 80), 500)
            self.fullscreen_grid.column(col, width=max_width)

        logger.info("Auto-sized fullscreen columns")

    def _autosize_fullscreen_row_height(self):
        """Auto-size row height in fullscreen grid"""
        if not self.fullscreen_grid:
            return

        import tkinter.font as tkfont
        font = tkfont.Font(family="Consolas", size=9)
        line_height = font.metrics('linespace')

        base_height = 25
        max_lines = 1

        # Find maximum number of lines (sample first 200 rows)
        for child in list(self.fullscreen_grid.get_children())[:200]:
            values = self.fullscreen_grid.item(child)['values']
            for value in values:
                if value:
                    value_str = str(value)
                    line_count = value_str.count('\n') + 1
                    max_lines = max(max_lines, line_count)

        # Calculate required height
        required_height = max(base_height, (line_height * max_lines) + 10)
        required_height = min(required_height, 400)

        # Apply row height using same style name
        style = ttk.Style()
        style.configure(self.style_name, rowheight=required_height)

        logger.info(f"Auto-sized fullscreen row height to {required_height}px")

    def set_on_fullscreen(self, callback: Callable):
        """Set callback for fullscreen toggle"""
        self.on_fullscreen_callback = callback

    # ==================== Raw/Table Toggle ====================

    def _toggle_raw_table(self):
        """Toggle between raw and table view (for CSV)"""
        if self.on_raw_toggle_callback:
            self.on_raw_toggle_callback()

    # ==================== Grid Display Toggle ====================

    def _toggle_grid_display(self):
        """Toggle grid display (alternating row colors)"""
        self.grid_display_enabled = not self.grid_display_enabled

        # Update button text
        if self.grid_display_enabled:
            self.grid_btn.config(text="⚏ Grid On")
        else:
            self.grid_btn.config(text="⚏ Grid Off")

        # Apply or remove grid styling
        self._apply_grid_styling()

        logger.info(f"Grid display: {'enabled' if self.grid_display_enabled else 'disabled'}")

    def _apply_grid_styling(self):
        """Apply or remove alternating row colors for grid display"""
        # Configure tags for alternating rows FIRST
        self.grid.tag_configure('oddrow', background='#f5f5f5')  # Very light gray
        self.grid.tag_configure('evenrow', background='white')

        # Verify tag configuration
        oddrow_config = self.grid.tag_configure('oddrow')
        evenrow_config = self.grid.tag_configure('evenrow')
        logger.info(f"Tag 'oddrow' config: {oddrow_config}")
        logger.info(f"Tag 'evenrow' config: {evenrow_config}")

        # Apply tags to all rows
        if self.grid_display_enabled:
            children = self.grid.get_children()
            logger.info(f"Applying grid styling to {len(children)} rows")
            for idx, child in enumerate(children):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                self.grid.item(child, tags=(tag,))
                if idx < 5:  # Log first 5 rows for debugging
                    item_info = self.grid.item(child)
                    logger.info(f"Row {idx}: applied tag '{tag}', item info: {item_info}")

            # Force widget update to show changes immediately
            self.grid.update_idletasks()
        else:
            # Remove all tags
            for child in self.grid.get_children():
                self.grid.item(child, tags=())
            logger.info("Removed all grid styling tags")

            # Force widget update
            self.grid.update_idletasks()

    # ==================== Events ====================

    def _on_select(self, event):
        """Handle row selection"""
        if self.on_row_selected_callback:
            selection = self.grid.selection()
            if selection:
                item = selection[0]
                values = self.grid.item(item)['values']
                self.on_row_selected_callback(values)

    def _on_double_click(self, event):
        """Handle double-click on row"""
        if self.on_row_double_click_callback:
            selection = self.grid.selection()
            if selection:
                item = selection[0]
                values = self.grid.item(item)['values']
                self.on_row_double_click_callback(values)

    def set_on_row_selected(self, callback: Callable):
        """Set callback for row selection"""
        self.on_row_selected_callback = callback

    def set_on_row_double_click(self, callback: Callable):
        """Set callback for row double-click"""
        self.on_row_double_click_callback = callback

    # ==================== State Management ====================

    def save_state(self):
        """Save current state (for fullscreen toggle)"""
        # Save scroll position
        self.saved_state['yview'] = self.grid.yview()
        self.saved_state['xview'] = self.grid.xview()
        # Save selection
        self.saved_state['selection'] = self.grid.selection()
        # Save sort
        self.saved_state['active_sorts'] = self.active_sorts.copy()

    def restore_state(self):
        """Restore saved state"""
        if 'yview' in self.saved_state:
            self.grid.yview_moveto(self.saved_state['yview'][0])
        if 'xview' in self.saved_state:
            self.grid.xview_moveto(self.saved_state['xview'][0])
        if 'selection' in self.saved_state:
            for item in self.saved_state['selection']:
                try:
                    self.grid.selection_add(item)
                except:
                    pass

    def apply_theme(self):
        """Apply current theme to data grid"""
        try:
            from ..config.theme_manager import get_theme_manager
            theme = get_theme_manager().get_current_theme()

            # Apply theme colors to treeview grid (using ttk.Style)
            style = ttk.Style()

            # TreeView (grid) colors
            style.configure(
                "Treeview",
                background=theme.get('grid_bg'),
                foreground=theme.get('grid_fg'),
                fieldbackground=theme.get('grid_bg')
            )

            # Headers
            style.configure(
                "Treeview.Heading",
                background=theme.get('grid_header_bg'),
                foreground=theme.get('grid_header_fg')
            )

            # Selection colors
            style.map(
                "Treeview",
                background=[('selected', theme.get('grid_select_bg'))],
                foreground=[('selected', theme.get('grid_select_fg'))]
            )

        except Exception as e:
            # Theme application failed, continue without theme
            import logging
            logging.getLogger(__name__).debug(f"Failed to apply theme to CustomDataGridView: {e}")
