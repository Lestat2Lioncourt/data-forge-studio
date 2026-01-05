"""
Script Format Dialog - Dialog for formatting SQL queries as code variables.

Supports: Python, T-SQL, VB.NET/VBScript, C#, C++

Displays the formatted query with options to customize variable name and copy to clipboard.
Uses custom title bar with red close button and double-click to maximize.
"""

from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QApplication, QFrame, QComboBox, QWidget
)
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QFont, QMouseEvent, QIcon

from ..core.i18n_bridge import tr
from ..core.theme_bridge import ThemeBridge
from ..widgets.dialog_helper import DialogHelper
from ...config.user_preferences import UserPreferences


class ScriptFormatDialog(QDialog):
    """Dialog for displaying formatted query with copy option and language selection."""

    # Language configurations
    LANGUAGES = {
        "python": {"label": "Python", "default_var": "query"},
        "tsql": {"label": "T-SQL", "default_var": "Query"},
        "vb": {"label": "VB", "default_var": "strQuery"},
        "csharp": {"label": "C#", "default_var": "query"},
        "cpp": {"label": "C++", "default_var": "query"}
    }

    def __init__(
        self,
        parent=None,
        query_text: str = ""
    ):
        super().__init__(parent)
        self.query_text = query_text
        self.prefs = UserPreferences.instance()

        # State for window dragging and maximizing
        self._drag_position = QPoint()
        self._is_dragging = False
        self._is_maximized = False
        self._normal_geometry = None

        # Load saved language preference
        self.format_type = self.prefs.get("export_language", "python")
        if self.format_type not in self.LANGUAGES:
            self.format_type = "python"

        # Remove native title bar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Load theme colors
        self._load_theme_colors()

        self._setup_ui()
        self._update_formatted_text()

    def _load_theme_colors(self):
        """Load colors from theme."""
        try:
            theme_bridge = ThemeBridge.get_instance()
            colors = theme_bridge.get_theme_colors()
        except Exception:
            colors = {}

        # Store theme colors with fallbacks
        self._colors = {
            'titlebar_bg': colors.get('main_menu_bar_bg', '#2b2b2b'),
            'titlebar_fg': colors.get('main_menu_bar_fg', '#ffffff'),
            'border': colors.get('border_color', '#3d3d3d'),
            'close_hover': colors.get('selector_close_btn_hover', '#e81123'),
        }

    def _setup_ui(self):
        """Setup dialog UI."""
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        self._setup_title_bar(main_layout)

        # Content area with padding
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top row: Language selector and Variable name
        top_layout = QHBoxLayout()

        # Language selector
        lang_label = QLabel(tr("query_export_language") + ":")
        top_layout.addWidget(lang_label)

        self.lang_combo = QComboBox()
        for key, config in self.LANGUAGES.items():
            self.lang_combo.addItem(config["label"], key)
        # Select current language
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == self.format_type:
                self.lang_combo.setCurrentIndex(i)
                break
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self.lang_combo.setMinimumWidth(100)
        top_layout.addWidget(self.lang_combo)

        top_layout.addSpacing(20)

        # Variable name input
        var_label = QLabel(tr("query_format_variable_name") + ":")
        top_layout.addWidget(var_label)

        self.var_input = QLineEdit()
        self.var_input.setText(self.LANGUAGES[self.format_type]["default_var"])
        self.var_input.textChanged.connect(self._update_formatted_text)
        self.var_input.setMaximumWidth(200)
        top_layout.addWidget(self.var_input)

        top_layout.addStretch()
        layout.addLayout(top_layout)

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

        # Add content widget to main layout
        main_layout.addWidget(content_widget)

    def _setup_title_bar(self, main_layout: QVBoxLayout):
        """Setup custom title bar with close button and drag/maximize support."""
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(32)
        self.title_bar.setObjectName("DialogTitleBar")
        self.title_bar.setStyleSheet(f"""
            #DialogTitleBar {{
                background-color: {self._colors['titlebar_bg']};
                border-bottom: 1px solid {self._colors['border']};
            }}
        """)

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        title_layout.setSpacing(0)

        # Title label
        title_label = QLabel(tr("query_toolbar_export"))
        title_label.setStyleSheet(f"color: {self._colors['titlebar_fg']}; font-weight: bold;")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # Close button (red)
        self.title_close_btn = QPushButton()
        self.title_close_btn.setFixedSize(32, 32)
        self.title_close_btn.clicked.connect(self.accept)
        self.title_close_btn.setToolTip(tr("btn_close"))

        # Load close icon
        icon_path = Path(__file__).parent.parent / "templates" / "window" / "icons" / "btn_close.png"
        if icon_path.exists():
            self.title_close_btn.setIcon(QIcon(str(icon_path)))
            self.title_close_btn.setIconSize(QSize(20, 20))
        else:
            self.title_close_btn.setText("✕")

        self.title_close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {self._colors['titlebar_fg']};
            }}
            QPushButton:hover {{
                background-color: {self._colors['close_hover']};
            }}
        """)
        title_layout.addWidget(self.title_close_btn)

        main_layout.addWidget(self.title_bar)

        # Install event filter for title bar mouse events
        self.title_bar.mousePressEvent = self._title_mouse_press
        self.title_bar.mouseMoveEvent = self._title_mouse_move
        self.title_bar.mouseReleaseEvent = self._title_mouse_release
        self.title_bar.mouseDoubleClickEvent = self._title_double_click

    def _title_mouse_press(self, event: QMouseEvent):
        """Handle mouse press on title bar for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _title_mouse_move(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            if self._is_maximized:
                # Restore from maximized before dragging
                self._toggle_maximize()
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def _title_mouse_release(self, event: QMouseEvent):
        """Handle mouse release to stop dragging."""
        self._is_dragging = False
        event.accept()

    def _title_double_click(self, event: QMouseEvent):
        """Handle double-click on title bar to maximize/restore."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
            event.accept()

    def _toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self._is_maximized:
            # Restore to normal
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            self._is_maximized = False
        else:
            # Save current geometry and maximize
            self._normal_geometry = self.geometry()
            screen = QApplication.primaryScreen().availableGeometry()
            self.setGeometry(screen)
            self._is_maximized = True

    def _on_language_changed(self, index: int):
        """Handle language selection change."""
        self.format_type = self.lang_combo.currentData()
        # Update variable name to default for new language
        self.var_input.setText(self.LANGUAGES[self.format_type]["default_var"])
        # Save preference
        self.prefs.set("export_language", self.format_type)
        self._update_formatted_text()

    def _update_formatted_text(self):
        """Update the formatted text based on current variable name."""
        var_name = self.var_input.text().strip()

        if not var_name:
            var_name = self.LANGUAGES[self.format_type]["default_var"]

        formatters = {
            "python": self._format_python,
            "tsql": self._format_tsql,
            "vb": self._format_vb,
            "csharp": self._format_csharp,
            "cpp": self._format_cpp
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
            # Build line parts first to calculate max length for alignment
            line_parts = []
            for line in lines:
                line_parts.append(f'{var_name} &= "{line}"')

            # Calculate max length for alignment
            max_len = max(len(part) for part in line_parts)

            # Build formatted lines with aligned & vbCrLf
            formatted_lines = [f'Dim {var_name} As String = ""']

            for i, part in enumerate(line_parts):
                if i < len(line_parts) - 1:
                    # Add padding for alignment
                    padded = part.ljust(max_len)
                    formatted_lines.append(f'{padded} & vbCrLf')
                else:
                    # Last line - no vbCrLf
                    formatted_lines.append(part)

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

    def _format_cpp(self, var_name: str) -> str:
        """Format as C++ variable assignment using raw string literals."""
        # Split query into lines
        lines = self.query_text.split('\n')

        if len(lines) == 1:
            # Single line query - escape quotes and backslashes
            escaped_query = self.query_text.replace('\\', '\\\\').replace('"', '\\"')
            return f'std::string {var_name} = "{escaped_query}";'
        else:
            # Multiline query - use raw string literal R"(...)"
            # Raw string literals don't need escaping, but )delimiter" cannot appear in content
            # Using a custom delimiter to be safe: R"sql(...)sql"
            return f'std::string {var_name} = R"sql(\n{self.query_text}\n)sql";'

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
