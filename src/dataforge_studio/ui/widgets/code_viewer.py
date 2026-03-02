"""
CodeViewerWidget - Read-only code viewer with syntax highlighting.

Supports multiple languages via custom QSyntaxHighlighter classes.
Falls back to Pygments for unsupported languages (e.g., PowerShell).

Usage:
    viewer = CodeViewerWidget()
    viewer.set_code(code_text, language="python")
"""

from typing import Optional, Dict, Type
import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextDocument
)
from PySide6.QtCore import QRegularExpression

logger = logging.getLogger(__name__)


# =============================================================================
# Base Highlighter
# =============================================================================

class BaseCodeHighlighter(QSyntaxHighlighter):
    """Base class for code syntax highlighters."""

    # Default colors (VS Code dark theme style)
    COLORS = {
        "keyword": "#569cd6",
        "string": "#ce9178",
        "comment": "#6a9955",
        "number": "#b5cea8",
        "function": "#dcdcaa",
        "operator": "#d4d4d4",
        "class": "#4ec9b0",
        "variable": "#9cdcfe",
        "decorator": "#c586c0",
        "builtin": "#4fc1ff",
    }

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._setup_formats()
        self._setup_rules()

    def _setup_formats(self):
        """Setup text formats for code elements."""
        self.formats: Dict[str, QTextCharFormat] = {}

        # Keyword format (bold)
        self.formats["keyword"] = QTextCharFormat()
        self.formats["keyword"].setForeground(QColor(self.COLORS["keyword"]))
        self.formats["keyword"].setFontWeight(QFont.Weight.Bold)

        # String format
        self.formats["string"] = QTextCharFormat()
        self.formats["string"].setForeground(QColor(self.COLORS["string"]))

        # Comment format (italic)
        self.formats["comment"] = QTextCharFormat()
        self.formats["comment"].setForeground(QColor(self.COLORS["comment"]))
        self.formats["comment"].setFontItalic(True)

        # Number format
        self.formats["number"] = QTextCharFormat()
        self.formats["number"].setForeground(QColor(self.COLORS["number"]))

        # Function format
        self.formats["function"] = QTextCharFormat()
        self.formats["function"].setForeground(QColor(self.COLORS["function"]))

        # Operator format
        self.formats["operator"] = QTextCharFormat()
        self.formats["operator"].setForeground(QColor(self.COLORS["operator"]))

        # Class format
        self.formats["class"] = QTextCharFormat()
        self.formats["class"].setForeground(QColor(self.COLORS["class"]))

        # Variable format
        self.formats["variable"] = QTextCharFormat()
        self.formats["variable"].setForeground(QColor(self.COLORS["variable"]))

        # Decorator format
        self.formats["decorator"] = QTextCharFormat()
        self.formats["decorator"].setForeground(QColor(self.COLORS["decorator"]))

        # Builtin format
        self.formats["builtin"] = QTextCharFormat()
        self.formats["builtin"].setForeground(QColor(self.COLORS["builtin"]))

    def _setup_rules(self):
        """Setup highlighting rules - to be overridden by subclasses."""
        self.highlighting_rules = []

    def highlightBlock(self, text: str):
        """Apply syntax highlighting to a block of text."""
        for pattern, format_type in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format_type)


# =============================================================================
# Python Highlighter
# =============================================================================

class PythonHighlighter(BaseCodeHighlighter):
    """Syntax highlighter for Python code."""

    def _setup_rules(self):
        self.highlighting_rules = []

        # Python keywords
        keywords = [
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'try', 'while', 'with', 'yield'
        ]
        keyword_pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self.highlighting_rules.append((
            QRegularExpression(keyword_pattern),
            self.formats["keyword"]
        ))

        # Python builtins
        builtins = [
            'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'callable', 'chr',
            'classmethod', 'compile', 'complex', 'delattr', 'dict', 'dir',
            'divmod', 'enumerate', 'eval', 'exec', 'filter', 'float', 'format',
            'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex',
            'id', 'input', 'int', 'isinstance', 'issubclass', 'iter', 'len',
            'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next',
            'object', 'oct', 'open', 'ord', 'pow', 'print', 'property', 'range',
            'repr', 'reversed', 'round', 'set', 'setattr', 'slice', 'sorted',
            'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip'
        ]
        builtin_pattern = r'\b(' + '|'.join(builtins) + r')\b'
        self.highlighting_rules.append((
            QRegularExpression(builtin_pattern),
            self.formats["builtin"]
        ))

        # Decorators
        self.highlighting_rules.append((
            QRegularExpression(r'@\w+'),
            self.formats["decorator"]
        ))

        # Function definitions
        self.highlighting_rules.append((
            QRegularExpression(r'\bdef\s+(\w+)'),
            self.formats["function"]
        ))

        # Class definitions
        self.highlighting_rules.append((
            QRegularExpression(r'\bclass\s+(\w+)'),
            self.formats["class"]
        ))

        # Numbers
        self.highlighting_rules.append((
            QRegularExpression(r'\b\d+\.?\d*\b'),
            self.formats["number"]
        ))

        # Single-quoted strings
        self.highlighting_rules.append((
            QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
            self.formats["string"]
        ))

        # Double-quoted strings
        self.highlighting_rules.append((
            QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
            self.formats["string"]
        ))

        # Comments
        self.highlighting_rules.append((
            QRegularExpression(r'#[^\n]*'),
            self.formats["comment"]
        ))


# =============================================================================
# Bash/Shell Highlighter
# =============================================================================

class BashHighlighter(BaseCodeHighlighter):
    """Syntax highlighter for Bash/Shell scripts."""

    def _setup_rules(self):
        self.highlighting_rules = []

        # Bash keywords
        keywords = [
            'if', 'then', 'else', 'elif', 'fi', 'case', 'esac', 'for', 'while',
            'until', 'do', 'done', 'in', 'function', 'select', 'time', 'coproc',
            'return', 'exit', 'break', 'continue', 'declare', 'local', 'export',
            'readonly', 'typeset', 'unset', 'shift', 'source', 'alias', 'unalias'
        ]
        keyword_pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self.highlighting_rules.append((
            QRegularExpression(keyword_pattern),
            self.formats["keyword"]
        ))

        # Common commands
        commands = [
            'echo', 'printf', 'read', 'cd', 'pwd', 'ls', 'cat', 'grep', 'sed',
            'awk', 'find', 'xargs', 'sort', 'uniq', 'wc', 'head', 'tail', 'cut',
            'tr', 'tee', 'mkdir', 'rmdir', 'rm', 'cp', 'mv', 'touch', 'chmod',
            'chown', 'test', 'expr', 'true', 'false', 'set', 'eval', 'exec'
        ]
        command_pattern = r'\b(' + '|'.join(commands) + r')\b'
        self.highlighting_rules.append((
            QRegularExpression(command_pattern),
            self.formats["builtin"]
        ))

        # Variables ($VAR, ${VAR})
        self.highlighting_rules.append((
            QRegularExpression(r'\$\{?\w+\}?'),
            self.formats["variable"]
        ))

        # Numbers
        self.highlighting_rules.append((
            QRegularExpression(r'\b\d+\b'),
            self.formats["number"]
        ))

        # Single-quoted strings
        self.highlighting_rules.append((
            QRegularExpression(r"'[^']*'"),
            self.formats["string"]
        ))

        # Double-quoted strings
        self.highlighting_rules.append((
            QRegularExpression(r'"[^"]*"'),
            self.formats["string"]
        ))

        # Comments
        self.highlighting_rules.append((
            QRegularExpression(r'#[^\n]*'),
            self.formats["comment"]
        ))


# =============================================================================
# Batch/CMD Highlighter
# =============================================================================

class BatchHighlighter(BaseCodeHighlighter):
    """Syntax highlighter for Windows Batch/CMD scripts."""

    def _setup_rules(self):
        self.highlighting_rules = []

        # Batch keywords (case-insensitive)
        keywords = [
            'if', 'else', 'for', 'in', 'do', 'goto', 'call', 'exit', 'set',
            'setlocal', 'endlocal', 'echo', 'rem', 'pause', 'cls', 'title',
            'color', 'prompt', 'path', 'pushd', 'popd', 'shift', 'errorlevel',
            'exist', 'not', 'equ', 'neq', 'lss', 'leq', 'gtr', 'geq', 'defined',
            'enabledelayedexpansion', 'disabledelayedexpansion'
        ]
        keyword_pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self.highlighting_rules.append((
            QRegularExpression(keyword_pattern, QRegularExpression.PatternOption.CaseInsensitiveOption),
            self.formats["keyword"]
        ))

        # Variables (%VAR%, !VAR!)
        self.highlighting_rules.append((
            QRegularExpression(r'%\w+%|!\w+!'),
            self.formats["variable"]
        ))

        # Labels (:label)
        self.highlighting_rules.append((
            QRegularExpression(r'^:\w+', QRegularExpression.PatternOption.MultilineOption),
            self.formats["function"]
        ))

        # Numbers
        self.highlighting_rules.append((
            QRegularExpression(r'\b\d+\b'),
            self.formats["number"]
        ))

        # Strings
        self.highlighting_rules.append((
            QRegularExpression(r'"[^"]*"'),
            self.formats["string"]
        ))

        # Comments (REM and ::)
        self.highlighting_rules.append((
            QRegularExpression(r'(?:^|\s)(?:REM|::)[^\n]*', QRegularExpression.PatternOption.CaseInsensitiveOption),
            self.formats["comment"]
        ))


# =============================================================================
# JavaScript Highlighter
# =============================================================================

class JavaScriptHighlighter(BaseCodeHighlighter):
    """Syntax highlighter for JavaScript code."""

    def _setup_rules(self):
        self.highlighting_rules = []

        # JavaScript keywords
        keywords = [
            'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
            'default', 'delete', 'do', 'else', 'export', 'extends', 'finally',
            'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new',
            'return', 'static', 'super', 'switch', 'this', 'throw', 'try',
            'typeof', 'var', 'void', 'while', 'with', 'yield', 'async', 'await',
            'null', 'undefined', 'true', 'false', 'of'
        ]
        keyword_pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self.highlighting_rules.append((
            QRegularExpression(keyword_pattern),
            self.formats["keyword"]
        ))

        # Builtins
        builtins = [
            'console', 'window', 'document', 'Array', 'Object', 'String',
            'Number', 'Boolean', 'Function', 'Symbol', 'Error', 'Promise',
            'Map', 'Set', 'WeakMap', 'WeakSet', 'JSON', 'Math', 'Date', 'RegExp'
        ]
        builtin_pattern = r'\b(' + '|'.join(builtins) + r')\b'
        self.highlighting_rules.append((
            QRegularExpression(builtin_pattern),
            self.formats["builtin"]
        ))

        # Function definitions
        self.highlighting_rules.append((
            QRegularExpression(r'\bfunction\s+(\w+)'),
            self.formats["function"]
        ))

        # Numbers
        self.highlighting_rules.append((
            QRegularExpression(r'\b\d+\.?\d*\b'),
            self.formats["number"]
        ))

        # Single-quoted strings
        self.highlighting_rules.append((
            QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
            self.formats["string"]
        ))

        # Double-quoted strings
        self.highlighting_rules.append((
            QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
            self.formats["string"]
        ))

        # Template strings
        self.highlighting_rules.append((
            QRegularExpression(r'`[^`]*`'),
            self.formats["string"]
        ))

        # Single-line comments
        self.highlighting_rules.append((
            QRegularExpression(r'//[^\n]*'),
            self.formats["comment"]
        ))


# =============================================================================
# Pygments Fallback Highlighter
# =============================================================================

class PygmentsHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter using Pygments library.
    Used for languages without native highlighter (e.g., PowerShell).
    """

    def __init__(self, document: QTextDocument, language: str):
        super().__init__(document)
        self.language = language
        self._lexer = None
        self._styles: Dict[str, QTextCharFormat] = {}
        self._setup_lexer()

    def _setup_lexer(self):
        """Setup Pygments lexer for the language."""
        try:
            from pygments import lexers
            from pygments.token import Token

            # Map language names to Pygments lexer names
            lexer_map = {
                "powershell": "powershell",
                "ps1": "powershell",
                "ruby": "ruby",
                "perl": "perl",
                "go": "go",
                "rust": "rust",
                "kotlin": "kotlin",
                "swift": "swift",
                "typescript": "typescript",
                "ts": "typescript",
                "yaml": "yaml",
                "yml": "yaml",
                "toml": "toml",
                "ini": "ini",
                "xml": "xml",
                "html": "html",
                "css": "css",
                "json": "json",
            }

            lexer_name = lexer_map.get(self.language.lower(), self.language.lower())
            self._lexer = lexers.get_lexer_by_name(lexer_name)

            # Setup token styles
            self._setup_styles()

        except (ImportError, ValueError) as e:
            logger.warning(f"Could not setup Pygments lexer for {self.language}: {e}")
            self._lexer = None

    def _setup_styles(self):
        """Setup text formats for Pygments tokens."""
        from pygments.token import Token

        # Map Pygments tokens to colors
        token_colors = {
            Token.Keyword: "#569cd6",
            Token.Keyword.Constant: "#569cd6",
            Token.Keyword.Declaration: "#569cd6",
            Token.Keyword.Namespace: "#c586c0",
            Token.Keyword.Type: "#4ec9b0",
            Token.Name.Function: "#dcdcaa",
            Token.Name.Class: "#4ec9b0",
            Token.Name.Builtin: "#4fc1ff",
            Token.Name.Variable: "#9cdcfe",
            Token.String: "#ce9178",
            Token.String.Doc: "#6a9955",
            Token.Number: "#b5cea8",
            Token.Comment: "#6a9955",
            Token.Operator: "#d4d4d4",
        }

        for token_type, color in token_colors.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if token_type in (Token.Keyword, Token.Keyword.Constant, Token.Keyword.Declaration):
                fmt.setFontWeight(QFont.Weight.Bold)
            if token_type in (Token.Comment, Token.String.Doc):
                fmt.setFontItalic(True)
            self._styles[str(token_type)] = fmt

    def highlightBlock(self, text: str):
        """Apply Pygments syntax highlighting."""
        if not self._lexer:
            return

        try:
            from pygments import lex
            from pygments.token import Token

            tokens = list(lex(text, self._lexer))
            position = 0

            for token_type, token_value in tokens:
                length = len(token_value)

                # Find the best matching style
                fmt = None
                token = token_type
                while token and fmt is None:
                    fmt = self._styles.get(str(token))
                    token = token.parent

                if fmt:
                    self.setFormat(position, length, fmt)

                position += length

        except Exception as e:
            logger.debug(f"Error highlighting with Pygments: {e}")


# =============================================================================
# Highlighter Registry
# =============================================================================

HIGHLIGHTER_REGISTRY: Dict[str, Type[BaseCodeHighlighter]] = {
    "python": PythonHighlighter,
    "py": PythonHighlighter,
    "bash": BashHighlighter,
    "sh": BashHighlighter,
    "zsh": BashHighlighter,
    "shell": BashHighlighter,
    "batch": BatchHighlighter,
    "bat": BatchHighlighter,
    "cmd": BatchHighlighter,
    "javascript": JavaScriptHighlighter,
    "js": JavaScriptHighlighter,
}

# Languages that should use Pygments
PYGMENTS_LANGUAGES = {
    "powershell", "ps1", "psm1", "psd1",
    "ruby", "rb",
    "perl", "pl",
    "go", "golang",
    "rust", "rs",
    "kotlin", "kt",
    "swift",
    "typescript", "ts",
    "yaml", "yml",
    "toml",
    "ini", "cfg",
    "xml",
    "html", "htm",
    "css",
    "json",
}


def get_highlighter(document: QTextDocument, language: str) -> Optional[QSyntaxHighlighter]:
    """
    Get the appropriate syntax highlighter for a language.

    Args:
        document: QTextDocument to attach highlighter to
        language: Language name or file extension

    Returns:
        QSyntaxHighlighter instance or None
    """
    lang_lower = language.lower().lstrip(".")

    # Check native highlighters first
    if lang_lower in HIGHLIGHTER_REGISTRY:
        return HIGHLIGHTER_REGISTRY[lang_lower](document)

    # Try SQL highlighter from existing module
    if lang_lower == "sql":
        try:
            from ...utils.sql_highlighter import SQLHighlighter
            return SQLHighlighter(document)
        except (ImportError, ValueError):
            pass

    # Try Pygments for other languages
    if lang_lower in PYGMENTS_LANGUAGES:
        return PygmentsHighlighter(document, lang_lower)

    # No highlighter available
    return None


# =============================================================================
# CodeViewerWidget
# =============================================================================

class CodeViewerWidget(QWidget):
    """
    Read-only code viewer with syntax highlighting.

    Features:
    - Automatic language detection from file extension or script_type
    - Native highlighters for Python, Bash, Batch, JavaScript, SQL
    - Pygments fallback for PowerShell, Ruby, Go, etc.
    - Theme-aware styling
    """

    # Map script_type to language
    SCRIPT_TYPE_TO_LANGUAGE = {
        "python": "python",
        "bash": "bash",
        "shell": "bash",
        "batch": "batch",
        "powershell": "powershell",
        "javascript": "javascript",
        "sql": "sql",
    }

    def __init__(self, parent: Optional[QWidget] = None, show_header: bool = True):
        """
        Initialize code viewer.

        Args:
            parent: Parent widget
            show_header: Whether to show the language header
        """
        super().__init__(parent)
        self._current_highlighter: Optional[QSyntaxHighlighter] = None
        self._current_language: str = ""
        self._show_header = show_header
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header with language info
        if self._show_header:
            header_layout = QHBoxLayout()
            header_layout.setContentsMargins(5, 2, 5, 2)

            self._language_label = QLabel("Code")
            self._language_label.setStyleSheet("font-weight: bold; color: #888;")
            header_layout.addWidget(self._language_label)
            header_layout.addStretch()

            layout.addLayout(header_layout)

        # Code text editor (read-only)
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 10))
        self._text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Apply dark theme styling
        self._apply_theme()

        layout.addWidget(self._text_edit)

    def _apply_theme(self):
        """Apply theme colors to the text editor."""
        try:
            from ..core.theme_bridge import ThemeBridge
            theme = ThemeBridge.get_instance()
            colors = theme.get_theme_colors()

            bg_color = colors.get("editor_bg", "#1e1e1e")
            fg_color = colors.get("editor_fg", "#d4d4d4")
        except (AttributeError, KeyError):
            bg_color = "#1e1e1e"
            fg_color = "#d4d4d4"

        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                background-color: {bg_color};
                color: {fg_color};
                border: 1px solid #3c3c3c;
                padding: 5px;
            }}
        """)

    def set_code(self, code: str, language: str = ""):
        """
        Set the code to display with syntax highlighting.

        Args:
            code: The code text to display
            language: Language name or file extension (e.g., "python", "ps1", "bash")
        """
        self._current_language = language

        # Update header
        if self._show_header and hasattr(self, '_language_label'):
            display_lang = language.upper() if language else "Code"
            self._language_label.setText(display_lang)

        # Remove old highlighter
        if self._current_highlighter:
            self._current_highlighter.setDocument(None)
            self._current_highlighter = None

        # Set the text first
        self._text_edit.setPlainText(code)

        # Apply highlighter
        if language:
            self._current_highlighter = get_highlighter(
                self._text_edit.document(),
                language
            )

    def set_code_from_script_type(self, code: str, script_type: str):
        """
        Set code with language detected from script_type.

        Args:
            code: The code text to display
            script_type: Script type (e.g., "python", "bash", "powershell")
        """
        language = self.SCRIPT_TYPE_TO_LANGUAGE.get(script_type.lower(), script_type)
        self.set_code(code, language)

    def clear(self):
        """Clear the code viewer."""
        if self._current_highlighter:
            self._current_highlighter.setDocument(None)
            self._current_highlighter = None
        self._text_edit.clear()
        if self._show_header and hasattr(self, '_language_label'):
            self._language_label.setText("Code")

    def get_code(self) -> str:
        """Get the current code text."""
        return self._text_edit.toPlainText()
