"""
CustomLogPanel - Reusable log panel with syntax highlighting
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from typing import Optional


class CustomLogPanel(ttk.Frame):
    """
    Standardized log panel component with colored output

    Features:
    - Title label
    - Scrollable text area with dark theme
    - Color-coded log levels (info, warning, error, success)
    - Automatic timestamps
    - Auto-scroll to bottom
    - Clear method

    Usage:
        log_panel = CustomLogPanel(parent, title="Execution Log")
        log_panel.pack(fill=tk.BOTH, expand=True)

        log_panel.log_message("Processing started...", "info")
        log_panel.log_message("Warning detected", "warning")
        log_panel.log_message("Operation completed", "success")
        log_panel.clear()
    """

    def __init__(self, parent, title: str = "Execution Log", initial_message: Optional[str] = None):
        """
        Initialize CustomLogPanel

        Args:
            parent: Parent widget
            title: Title text for the log panel
            initial_message: Optional initial message to display
        """
        super().__init__(parent)

        self.title = title
        self.log_text = None
        self._tags_configured = False

        self._create_widgets(initial_message)

    def _create_widgets(self, initial_message: Optional[str]):
        """Create panel widgets"""
        # Title label
        ttk.Label(
            self,
            text=self.title,
            font=("Arial", 10, "bold")
        ).pack(pady=5)

        # Log text area frame
        log_frame = ttk.Frame(self, padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable text widget with dark theme
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure color tags
        self._configure_tags()

        # Add initial message if provided
        if initial_message:
            self.log_message(initial_message)

    def _configure_tags(self):
        """Configure color tags for different log levels"""
        if self._tags_configured:
            return

        self.log_text.tag_config("error", foreground="#f48771")
        self.log_text.tag_config("warning", foreground="#dcdcaa")
        self.log_text.tag_config("success", foreground="#4ec9b0")
        self.log_text.tag_config("info", foreground="#d4d4d4")

        self._tags_configured = True

    def log_message(self, message: str, level: str = "info"):
        """
        Add message to execution log with timestamp and color

        Args:
            message: Message to log
            level: Log level - one of: "info", "warning", "error", "success"
        """
        self.log_text.config(state=tk.NORMAL)

        # Ensure tags are configured
        if not self._tags_configured:
            self._configure_tags()

        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Insert message with appropriate tag
        tag = level if level in ["error", "warning", "success", "info"] else "info"
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)

        # Auto-scroll to bottom
        self.log_text.see(tk.END)

        self.log_text.config(state=tk.DISABLED)

    def clear(self):
        """Clear all log content"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def get_content(self) -> str:
        """
        Get all log content as string

        Returns:
            str: All text content from the log
        """
        return self.log_text.get(1.0, tk.END)

    def set_state(self, state: str):
        """
        Set text widget state

        Args:
            state: Either "normal" or "disabled"
        """
        self.log_text.config(state=state)
