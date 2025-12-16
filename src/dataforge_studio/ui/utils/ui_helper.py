"""
UIHelper - Common UI utility functions

Centralizes repeated UI patterns to avoid code duplication.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QFont


class UIHelper:
    """Collection of common UI utility functions."""

    # Default monospace fonts in order of preference
    MONOSPACE_FONTS = ["Consolas", "Monaco", "Courier New", "monospace"]

    @staticmethod
    def apply_monospace_font(widget: QWidget, size: int = 10, font_family: Optional[str] = None) -> QFont:
        """
        Apply monospace font to a widget.

        Replaces the repeated pattern:
            font = QFont("Consolas", 10)
            font.setStyleHint(QFont.StyleHint.Monospace)
            widget.setFont(font)

        Args:
            widget: Widget to apply font to
            size: Font size in points
            font_family: Specific font family (default: Consolas)

        Returns:
            The created QFont instance
        """
        family = font_family or UIHelper.MONOSPACE_FONTS[0]
        font = QFont(family, size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        widget.setFont(font)
        return font

    @staticmethod
    def create_monospace_font(size: int = 10, font_family: Optional[str] = None) -> QFont:
        """
        Create a monospace font without applying to widget.

        Args:
            size: Font size in points
            font_family: Specific font family (default: Consolas)

        Returns:
            QFont configured for monospace
        """
        family = font_family or UIHelper.MONOSPACE_FONTS[0]
        font = QFont(family, size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
