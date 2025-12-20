"""
SQL Syntax Highlighter for PySide6
Provides syntax highlighting for SQL queries in QTextEdit
"""

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression


class SQLHighlighter(QSyntaxHighlighter):
    """
    SQL syntax highlighter for QTextEdit/QPlainTextEdit.

    Highlights SQL keywords, strings, comments, numbers, and functions.
    Colors are loaded from the active theme.
    """

    # Default colors for dark mode (VS Code style)
    DARK_COLORS = {
        "keyword": "#569cd6",
        "string": "#ce9178",
        "comment": "#6a9955",
        "number": "#b5cea8",
        "function": "#dcdcaa",
        "operator": "#d4d4d4",
        "identifier": "#9cdcfe",
    }

    # Default colors for light mode (SSMS style)
    LIGHT_COLORS = {
        "keyword": "#0000ff",
        "string": "#a31515",
        "comment": "#008000",
        "number": "#09885a",
        "function": "#795e26",
        "operator": "#000000",
        "identifier": "#001080",
    }

    def __init__(self, document, theme_colors=None):
        """
        Initialize SQL highlighter.

        Args:
            document: QTextDocument to apply highlighting to
            theme_colors: Optional dict of theme colors. If None, will load from ThemeBridge.
        """
        super().__init__(document)
        self.theme_colors = theme_colors
        self._is_dark = True  # Default to dark mode
        self._load_theme_colors()
        self._setup_formats()
        self._setup_rules()

    def _load_theme_colors(self):
        """Load colors from the active theme."""
        try:
            from ..ui.core.theme_bridge import ThemeBridge
            bridge = ThemeBridge.get_instance()
            current_theme = bridge.current_theme

            if current_theme:
                # Check if dark theme
                theme_data = bridge.themes.get(current_theme, {})
                palette = theme_data.get("palette", {})
                self._is_dark = palette.get("is_dark", True)

                # Try to get theme-specific SQL colors from full theme
                colors = bridge.get_theme_colors(current_theme)
                if colors:
                    if "sql_keyword" in colors:
                        self.theme_colors = {
                            "keyword": colors.get("sql_keyword"),
                            "string": colors.get("sql_string"),
                            "comment": colors.get("sql_comment"),
                            "number": colors.get("sql_number"),
                            "function": colors.get("sql_function"),
                            "operator": colors.get("sql_operator"),
                            "identifier": colors.get("sql_identifier"),
                        }
                        return

        except Exception:
            pass

        # Fallback to default colors based on theme darkness
        self.theme_colors = self.DARK_COLORS if self._is_dark else self.LIGHT_COLORS

    def _setup_formats(self):
        """Setup text formats for SQL elements based on theme."""
        colors = self.theme_colors or (self.DARK_COLORS if self._is_dark else self.LIGHT_COLORS)

        # Keyword format (bold)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(colors["keyword"]))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        # String format
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(colors["string"]))

        # Comment format (italic)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(colors["comment"]))
        self.comment_format.setFontItalic(True)

        # Number format
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(colors["number"]))

        # Function format
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor(colors["function"]))

        # Operator format
        self.operator_format = QTextCharFormat()
        self.operator_format.setForeground(QColor(colors["operator"]))

    def _setup_rules(self):
        """Setup highlighting rules with regular expressions."""
        self.highlighting_rules = []

        # SQL Keywords
        keywords = [
            # DML
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE',
            'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
            'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE',
            'IS', 'NULL', 'AS', 'ORDER', 'BY', 'GROUP', 'HAVING',
            'DISTINCT', 'TOP', 'LIMIT', 'OFFSET',

            # DDL
            'CREATE', 'ALTER', 'DROP', 'TRUNCATE',
            'TABLE', 'VIEW', 'INDEX', 'DATABASE', 'SCHEMA',
            'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'UNIQUE',
            'CONSTRAINT', 'CHECK', 'DEFAULT',

            # Data types
            'INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT',
            'VARCHAR', 'CHAR', 'TEXT', 'NVARCHAR', 'NCHAR',
            'DECIMAL', 'NUMERIC', 'FLOAT', 'REAL', 'DOUBLE',
            'DATE', 'DATETIME', 'TIMESTAMP', 'TIME',
            'BOOLEAN', 'BOOL', 'BIT',
            'BLOB', 'CLOB',

            # Other
            'BEGIN', 'END', 'TRANSACTION', 'COMMIT', 'ROLLBACK',
            'GRANT', 'REVOKE', 'WITH', 'CASE', 'WHEN', 'THEN', 'ELSE',
            'UNION', 'INTERSECT', 'EXCEPT', 'ALL',
            'SET', 'INTO', 'VALUES', 'RETURNING',
            'CASCADE', 'RESTRICT', 'NO', 'ACTION'
        ]

        # Create pattern for keywords (word boundaries)
        keyword_pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self.highlighting_rules.append((
            QRegularExpression(keyword_pattern, QRegularExpression.PatternOption.CaseInsensitiveOption),
            self.keyword_format
        ))

        # SQL Functions
        functions = [
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
            'UPPER', 'LOWER', 'TRIM', 'LTRIM', 'RTRIM',
            'SUBSTRING', 'LENGTH', 'CONCAT', 'COALESCE',
            'CAST', 'CONVERT', 'DATEPART', 'DATEDIFF',
            'NOW', 'GETDATE', 'CURRENT_TIMESTAMP',
            'ROW_NUMBER', 'RANK', 'DENSE_RANK',
            'LAG', 'LEAD', 'FIRST_VALUE', 'LAST_VALUE'
        ]

        function_pattern = r'\b(' + '|'.join(functions) + r')\s*\('
        self.highlighting_rules.append((
            QRegularExpression(function_pattern, QRegularExpression.PatternOption.CaseInsensitiveOption),
            self.function_format
        ))

        # Numbers (integers and decimals)
        self.highlighting_rules.append((
            QRegularExpression(r'\b\d+\.?\d*\b'),
            self.number_format
        ))

        # Operators
        operators = [r'\+', r'-', r'\*', r'/', r'=', r'<', r'>', r'<=', r'>=', r'<>', r'!=']
        for op in operators:
            self.highlighting_rules.append((
                QRegularExpression(op),
                self.operator_format
            ))

        # Single-quoted strings
        self.highlighting_rules.append((
            QRegularExpression(r"'[^']*'"),
            self.string_format
        ))

        # Double-quoted identifiers
        self.highlighting_rules.append((
            QRegularExpression(r'"[^"]*"'),
            self.string_format
        ))

        # Single-line comments (-- style)
        self.highlighting_rules.append((
            QRegularExpression(r'--[^\n]*'),
            self.comment_format
        ))

    def highlightBlock(self, text):
        """
        Apply syntax highlighting to a block of text.

        Args:
            text: Text block to highlight
        """
        # Apply all single-line rules
        for pattern, format_type in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format_type)

        # Handle multi-line comments (/* ... */)
        self.setCurrentBlockState(0)

        start_expression = QRegularExpression(r'/\*')
        end_expression = QRegularExpression(r'\*/')

        start_index = 0
        if self.previousBlockState() != 1:
            match = start_expression.match(text)
            start_index = match.capturedStart() if match.hasMatch() else -1

        while start_index >= 0:
            match = end_expression.match(text, start_index)
            end_index = match.capturedStart() if match.hasMatch() else -1

            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + match.capturedLength()

            self.setFormat(start_index, comment_length, self.comment_format)

            match = start_expression.match(text, start_index + comment_length)
            start_index = match.capturedStart() if match.hasMatch() else -1


def format_sql(sql_text: str, indent_width: int = 2) -> str:
    """
    Format SQL text with basic indentation.

    This is a simple formatter. For production use, consider using sqlparse library.

    Args:
        sql_text: SQL text to format
        indent_width: Number of spaces for indentation

    Returns:
        Formatted SQL text
    """
    try:
        import sqlparse
        return sqlparse.format(
            sql_text,
            reindent=True,
            keyword_case='upper',
            indent_width=indent_width
        )
    except ImportError:
        # Fallback: basic formatting without sqlparse
        lines = []
        indent_level = 0
        indent = ' ' * indent_width

        # Keywords that increase indent
        indent_increase = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN',
                          'INNER JOIN', 'OUTER JOIN', 'GROUP BY', 'ORDER BY', 'HAVING']

        # Keywords that decrease indent
        indent_decrease = []

        for line in sql_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Check for indent decrease
            line_upper = line.upper()
            for keyword in indent_decrease:
                if line_upper.startswith(keyword):
                    indent_level = max(0, indent_level - 1)
                    break

            # Add indented line
            lines.append(indent * indent_level + line)

            # Check for indent increase
            for keyword in indent_increase:
                if keyword in line_upper:
                    indent_level += 1
                    break

        return '\n'.join(lines)
