"""
Help Frame - Help and documentation view with navigation and detachable window.
"""

import re
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTextBrowser, QLineEdit, QPushButton, QLabel, QMainWindow, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ..core.i18n_bridge import tr
from ..widgets.pinnable_panel import PinnablePanel
from ...utils.documentation_loader import get_documentation_loader, DocEntry, DocCategory
from ...utils.image_loader import get_icon
from ... import __version__


class MarkdownRenderer:
    """Simple markdown to HTML converter."""

    @staticmethod
    def to_html(markdown: str) -> str:
        """Convert markdown to HTML."""
        html = markdown

        # Escape HTML special chars (except in code blocks)
        # We'll handle this more carefully

        # Code blocks (``` ... ```)
        html = re.sub(
            r'```(\w*)\n(.*?)```',
            r'<pre style="background-color: #2d2d2d; padding: 10px; border-radius: 4px; overflow-x: auto;"><code>\2</code></pre>',
            html,
            flags=re.DOTALL
        )

        # Inline code (`...`)
        html = re.sub(r'`([^`]+)`', r'<code style="background-color: #3d3d3d; padding: 2px 5px; border-radius: 3px;">\1</code>', html)

        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

        # Unordered lists
        html = re.sub(r'^\s*[-*]\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'((?:<li>.*</li>\n?)+)', r'<ul>\1</ul>', html)

        # Ordered lists
        html = re.sub(r'^\s*\d+\.\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # Horizontal rules
        html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)

        # Paragraphs (double newlines)
        html = re.sub(r'\n\n+', r'</p><p>', html)

        # Wrap in paragraph tags
        html = f'<p>{html}</p>'

        # Clean up empty paragraphs
        html = re.sub(r'<p>\s*</p>', '', html)

        return html


class HelpContentWidget(QTextBrowser):
    """Widget for displaying help content with markdown support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self._apply_style()

    def _apply_style(self):
        """Apply styling to the help content."""
        self.setStyleSheet("""
            QTextBrowser {
                font-size: 11pt;
                line-height: 1.6;
            }
        """)

    def set_markdown(self, markdown: str):
        """Set content from markdown string."""
        html = MarkdownRenderer.to_html(markdown)
        self.setHtml(self._wrap_html(html))

    def set_welcome(self):
        """Show welcome content."""
        html = f"""
        <h1>DataForge Studio v{__version__}</h1>
        <p>{tr("help_welcome_text")}</p>

        <h2>{tr("help_quick_start")}</h2>
        <ul>
            <li><strong>{tr("menu_databases")}</strong>: {tr("help_databases_desc")}</li>
            <li><strong>{tr("menu_queries")}</strong>: {tr("help_queries_desc")}</li>
            <li><strong>{tr("menu_datalake")}</strong>: {tr("help_datalake_desc")}</li>
            <li><strong>{tr("menu_scripts")}</strong>: {tr("help_scripts_desc")}</li>
        </ul>

        <h2>{tr("help_select_topic")}</h2>
        <p>{tr("help_select_topic_desc")}</p>

        <hr>
        <p style="text-align: center; opacity: 0.7;">
            Version {__version__} |
            <a href="https://github.com/Lestat2Lioncourt/data-forge-studio">GitHub</a>
        </p>
        """
        self.setHtml(self._wrap_html(html))

    def _wrap_html(self, content: str) -> str:
        """Wrap content in HTML with styling."""
        return f"""
        <html>
        <head>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                padding: 15px;
            }}
            h1 {{ color: #4a9eff; margin-bottom: 10px; }}
            h2 {{ color: #6ab7ff; margin-top: 20px; border-bottom: 1px solid #444; padding-bottom: 5px; }}
            h3 {{ color: #8ecaff; margin-top: 15px; }}
            a {{ color: #4a9eff; }}
            code {{
                background-color: #3d3d3d;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: 'Consolas', 'Courier New', monospace;
            }}
            pre {{
                background-color: #2d2d2d;
                padding: 10px;
                border-radius: 4px;
                overflow-x: auto;
            }}
            ul, ol {{ margin-left: 20px; }}
            li {{ margin: 5px 0; }}
            hr {{ border: none; border-top: 1px solid #444; margin: 20px 0; }}
            table {{ border-collapse: collapse; margin: 10px 0; }}
            th, td {{ padding: 8px; border: 1px solid #444; }}
            th {{ background-color: #3d3d3d; }}
        </style>
        </head>
        <body>
        {content}
        </body>
        </html>
        """


class HelpWindow(QMainWindow):
    """Detachable help window."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"DataForge Studio - {tr('menu_documentation')}")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

        # Create help frame as central widget
        self.help_frame = HelpFrame(embedded=False)
        self.setCentralWidget(self.help_frame)

        # Set window icon
        icon = get_icon("help.png")
        if icon:
            self.setWindowIcon(icon)

    def closeEvent(self, event):
        """Emit closed signal when window closes."""
        self.closed.emit()
        super().closeEvent(event)

    def navigate_to(self, doc_id: str):
        """Navigate to a specific documentation entry."""
        self.help_frame.navigate_to(doc_id)


class HelpFrame(QWidget):
    """
    Help and documentation frame with sidebar navigation.

    Features:
    - Left sidebar with documentation tree
    - Right content area with markdown rendering
    - Search functionality
    - Detach button to open in separate window
    """

    # Signal emitted when detach is requested
    detach_requested = Signal()

    def __init__(self, parent=None, embedded: bool = True):
        super().__init__(parent)
        self._embedded = embedded
        self._doc_loader = get_documentation_loader()
        self._help_window: Optional[HelpWindow] = None
        self._setup_ui()
        self._load_documentation()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Top bar with search and detach button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(5, 5, 5, 5)

        # Search field
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText(tr("help_search_placeholder"))
        self.search_field.setClearButtonEnabled(True)
        self.search_field.textChanged.connect(self._on_search)
        top_bar.addWidget(self.search_field)

        # Detach button (only in embedded mode)
        if self._embedded:
            self.detach_btn = QPushButton()
            # Use view.png as fallback for detach icon
            detach_icon = get_icon("external.png") or get_icon("view.png") or get_icon("open.png")
            if detach_icon:
                self.detach_btn.setIcon(detach_icon)
            else:
                self.detach_btn.setText("⧉")  # Unicode window icon
            self.detach_btn.setToolTip(tr("help_detach_tooltip"))
            self.detach_btn.setFixedSize(28, 28)
            self.detach_btn.clicked.connect(self._on_detach)
            top_bar.addWidget(self.detach_btn)

        layout.addLayout(top_bar)

        # Main splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)

        # Left panel: Documentation tree
        self.left_panel = PinnablePanel(
            title=tr("help_topics"),
            icon_name="file.png"  # Using file.png as help.png doesn't exist
        )
        self.left_panel.set_normal_width(250)

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self.doc_tree = QTreeWidget()
        self.doc_tree.setHeaderHidden(True)
        self.doc_tree.setIndentation(15)
        self.doc_tree.itemClicked.connect(self._on_tree_click)
        tree_layout.addWidget(self.doc_tree)

        self.left_panel.set_content(tree_container)
        self.splitter.addWidget(self.left_panel)

        # Right panel: Content viewer
        self.content_viewer = HelpContentWidget()
        self.splitter.addWidget(self.content_viewer)

        # Set splitter proportions
        self.splitter.setSizes([250, 650])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        layout.addWidget(self.splitter)

        # Show welcome content initially
        self.content_viewer.set_welcome()

    def _load_documentation(self):
        """Load documentation entries into the tree."""
        self.doc_tree.clear()

        categories = self._doc_loader.get_categories()

        for category in categories:
            # Create category item
            cat_item = QTreeWidgetItem(self.doc_tree)
            cat_item.setText(0, category.name)
            cat_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
            cat_item.setExpanded(True)

            # Set category icon from manifest
            cat_icon = get_icon(category.icon, size=16)
            if cat_icon:
                cat_item.setIcon(0, cat_icon)

            # Add entries
            for entry in category.entries:
                entry_item = QTreeWidgetItem(cat_item)
                entry_item.setText(0, entry.title)
                entry_item.setData(0, Qt.ItemDataRole.UserRole, entry.id)

                # Use same icon as category for entries
                if cat_icon:
                    entry_item.setIcon(0, cat_icon)

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click."""
        doc_id = item.data(0, Qt.ItemDataRole.UserRole)
        if doc_id:
            self.navigate_to(doc_id)

    def _on_search(self, query: str):
        """Handle search input."""
        if len(query) < 2:
            # Reset tree to show all items
            self._show_all_items()
            return

        # Search documentation
        results = self._doc_loader.search(query)
        result_ids = {entry.id for entry, _ in results}

        # Filter tree to show only matching items
        self._filter_tree(result_ids)

    def _show_all_items(self):
        """Show all items in the tree."""
        for i in range(self.doc_tree.topLevelItemCount()):
            cat_item = self.doc_tree.topLevelItem(i)
            cat_item.setHidden(False)
            for j in range(cat_item.childCount()):
                cat_item.child(j).setHidden(False)

    def _filter_tree(self, visible_ids: set):
        """Filter tree to show only items with IDs in visible_ids."""
        for i in range(self.doc_tree.topLevelItemCount()):
            cat_item = self.doc_tree.topLevelItem(i)
            has_visible_child = False

            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                doc_id = child.data(0, Qt.ItemDataRole.UserRole)
                is_visible = doc_id in visible_ids
                child.setHidden(not is_visible)
                if is_visible:
                    has_visible_child = True

            cat_item.setHidden(not has_visible_child)

    def _on_detach(self):
        """Handle detach button click."""
        if self._help_window is None:
            self._help_window = HelpWindow()
            self._help_window.closed.connect(self._on_help_window_closed)

        self._help_window.show()
        self._help_window.raise_()
        self._help_window.activateWindow()

    def _on_help_window_closed(self):
        """Handle help window closed."""
        self._help_window = None

    def navigate_to(self, doc_id: str):
        """Navigate to a specific documentation entry."""
        content = self._doc_loader.get_content(doc_id)
        if content:
            self.content_viewer.set_markdown(content)

            # Select item in tree
            self._select_tree_item(doc_id)
        else:
            self.content_viewer.set_welcome()

    def _select_tree_item(self, doc_id: str):
        """Select tree item by doc_id."""
        for i in range(self.doc_tree.topLevelItemCount()):
            cat_item = self.doc_tree.topLevelItem(i)
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                if child.data(0, Qt.ItemDataRole.UserRole) == doc_id:
                    self.doc_tree.setCurrentItem(child)
                    return

    def show_contextual_help(self, topic: str):
        """
        Show help for a specific topic.

        Args:
            topic: Topic identifier (e.g., "database", "queries", "scripts")
        """
        # Map topics to documentation IDs
        topic_map = {
            "database": "summary-all-features",
            "databases": "summary-all-features",
            "queries": "save-queries-guide",
            "datalake": "summary-all-features",
            "rootfolders": "summary-all-features",
            "scripts": "summary-all-features",
            "jobs": "summary-all-features",
            "workspaces": "projects-feature",
            "settings": "sql-format-styles-guide",
            "sqlite": "sqlite-native-support",
            "context-menu": "right-click-menu",
        }

        doc_id = topic_map.get(topic.lower(), "summary-all-features")
        self.navigate_to(doc_id)

        # If window exists, show it
        if self._help_window:
            self._help_window.navigate_to(doc_id)
            self._help_window.show()
            self._help_window.raise_()
