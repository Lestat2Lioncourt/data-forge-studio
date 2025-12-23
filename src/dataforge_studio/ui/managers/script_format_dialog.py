"""
Script Format Dialog - Dialog for formatting SQL queries as code variables.

Supports: Python, T-SQL, VB.NET/VBScript, C#

Displays the formatted query with options to customize variable name and copy to clipboard.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QApplication, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..core.i18n_bridge import tr
from ..widgets.dialog_helper import DialogHelper


class ScriptFormatDialog(QDialog):
    """Dialog for displaying formatted query with copy option."""

    def __init__(
        self,
        parent=None,
        query_text: str = "",
        format_type: str = "python"  # "python", "tsql", "vb", "csharp"
    ):
        super().__init__(parent)
        self.query_text = query_text
        self.format_type = format_type

        # Default variable names per language
        default_names = {
            "python": "query",
            "tsql": "Query",
            "vb": "strQuery",
            "csharp": "query"
        }
        self.default_var_name = default_names.get(format_type, "query")

        self._setup_ui()
        self._update_formatted_text()

    def _setup_ui(self):
        """Setup dialog UI."""
        titles = {
            "python": tr("query_format_python_title"),
            "tsql": tr("query_format_tsql_title"),
            "vb": tr("query_format_vb_title"),
            "csharp": tr("query_format_csharp_title")
        }
        self.setWindowTitle(titles.get(self.format_type, "Export Query"))

        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Variable name input
        var_layout = QHBoxLayout()
        var_label = QLabel(tr("query_format_variable_name") + ":")
        var_layout.addWidget(var_label)

        self.var_input = QLineEdit()
        self.var_input.setText(self.default_var_name)
        self.var_input.textChanged.connect(self._update_formatted_text)
        self.var_input.setMaximumWidth(200)
        var_layout.addWidget(self.var_input)

        var_layout.addStretch()
        layout.addLayout(var_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Formatted query display
        result_label = QLabel(tr("query_format_result") + ":")
        layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_text)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.copy_btn = QPushButton(tr("query_format_copy_clipboard"))
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        button_layout.addWidget(self.copy_btn)

        self.close_btn = QPushButton(tr("btn_close"))
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _update_formatted_text(self):
        """Update the formatted text based on current variable name."""
        var_name = self.var_input.text().strip()

        if not var_name:
            var_name = self.default_var_name

        formatters = {
            "python": self._format_python,
            "tsql": self._format_tsql,
            "vb": self._format_vb,
            "csharp": self._format_csharp
        }
        formatter = formatters.get(self.format_type, self._format_python)
        formatted = formatter(var_name)

        self.result_text.setPlainText(formatted)

    def _format_python(self, var_name: str) -> str:
        """Format as Python variable assignment."""
        # Validate Python variable name
        if not var_name.isidentifier():
            return f"# Invalid variable name: {var_name}\n# Please use a valid Python identifier"

        # Format as Python multiline string with triple quotes
        return f'{var_name} = """\n{self.query_text}\n"""'

    def _format_tsql(self, var_name: str) -> str:
        """Format as T-SQL variable assignment using SET."""
        # Remove @ if user added it (we'll add it ourselves)
        if var_name.startswith("@"):
            var_name = var_name[1:]

        # Escape single quotes in query (double them for T-SQL)
        escaped_query = self.query_text.replace("'", "''")

        # Split query into lines for better formatting
        lines = escaped_query.split('\n')

        if len(lines) == 1:
            # Single line query - no need for @CrLf
            return f"SET @{var_name} = N'{escaped_query}';"
        else:
            # Multiline query - use @CrLf variable for line breaks
            # First, find the max line length to align @CrLf
            line_parts = []
            for i, line in enumerate(lines):
                if i < len(lines) - 1:
                    line_parts.append(f"    + N'{line}'")
                else:
                    line_parts.append(f"    + N'{line}'")

            # Calculate max length for alignment
            max_len = max(len(part) for part in line_parts)

            # Build formatted lines with aligned @CrLf
            formatted_lines = [
                "DECLARE @CrLf VARCHAR(4) = CHAR(13) + CHAR(10);",
                "",
                f"SET @{var_name} = N''"
            ]

            for i, part in enumerate(line_parts):
                if i < len(line_parts) - 1:
                    # Add padding for alignment
                    padded = part.ljust(max_len)
                    formatted_lines.append(f"{padded} + @CrLf")
                else:
                    # Last line - no @CrLf, just semicolon
                    formatted_lines.append(f"{part};")

            return '\n'.join(formatted_lines)

    def _format_vb(self, var_name: str) -> str:
        """Format as VB.NET/VBScript variable assignment."""
        # Escape double quotes in query (double them for VB)
        escaped_query = self.query_text.replace('"', '""')

        # Split query into lines
        lines = escaped_query.split('\n')

        if len(lines) == 1:
            # Single line query
            return f'Dim {var_name} As String = "{escaped_query}"'
        else:
            # Multiline query - use string concatenation with vbCrLf
            formatted_lines = [f'Dim {var_name} As String = ""']

            for i, line in enumerate(lines):
                if i < len(lines) - 1:
                    formatted_lines.append(f'{var_name} &= "{line}" & vbCrLf')
                else:
                    formatted_lines.append(f'{var_name} &= "{line}"')

            return '\n'.join(formatted_lines)

    def _format_csharp(self, var_name: str) -> str:
        """Format as C# variable assignment."""
        # Escape double quotes and backslashes for C#
        escaped_query = self.query_text.replace('\\', '\\\\').replace('"', '\\"')

        # Split query into lines
        lines = escaped_query.split('\n')

        if len(lines) == 1:
            # Single line query
            return f'string {var_name} = "{escaped_query}";'
        else:
            # Multiline query - use verbatim string (@"") or string concatenation
            # Using verbatim string (simpler, quotes are doubled)
            verbatim_query = self.query_text.replace('"', '""')
            return f'string {var_name} = @"\n{verbatim_query}";'

    def _copy_to_clipboard(self):
        """Copy formatted text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.result_text.toPlainText())

        # Visual feedback
        original_text = self.copy_btn.text()
        self.copy_btn.setText(tr("query_format_copied") + " ✓")
        self.copy_btn.setEnabled(False)

        # Reset button after 1.5 seconds
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self._reset_copy_button(original_text))

    def _reset_copy_button(self, original_text: str):
        """Reset copy button to original state."""
        self.copy_btn.setText(original_text)
        self.copy_btn.setEnabled(True)
