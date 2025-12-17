"""
Help Frame - Help and documentation view
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtCore import Qt

from ..core.i18n_bridge import tr


class HelpFrame(QWidget):
    """Help and documentation frame."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # Rich text browser for help content
        self.help_browser = QTextEdit()
        self.help_browser.setReadOnly(True)

        # Load help content
        help_html = self._get_help_content()
        self.help_browser.setHtml(help_html)

        layout.addWidget(self.help_browser)

    def _get_help_content(self) -> str:
        """Generate help content HTML."""
        return """
        <h1>DataForge Studio v0.50</h1>

        <h2>Welcome to DataForge Studio</h2>
        <p>DataForge Studio is a multi-database management tool with a modern PySide6 interface.</p>

        <h2>What's New in v0.50</h2>
        <ul>
            <li><strong>Complete UI Overhaul</strong>: Migrated from TKinter to PySide6</li>
            <li><strong>Modern Frameless Window</strong>: Custom title bar, menu bar, and status bar</li>
            <li><strong>Improved Architecture</strong>: Reduced code by ~60% through refactoring</li>
            <li><strong>Reusable Components</strong>: New widget library for consistent UI</li>
            <li><strong>Better Performance</strong>: Faster rendering and responsiveness</li>
        </ul>

        <h2>Navigation</h2>
        <p>Use the <strong>View</strong> menu to navigate between different sections:</p>
        <ul>
            <li><strong>Data Lake</strong>: Manage data operations</li>
            <li><strong>Database</strong>: Connect and query databases</li>
            <li><strong>Queries</strong>: Save and manage SQL queries</li>
            <li><strong>Scripts</strong>: Create and execute Python scripts</li>
            <li><strong>Jobs</strong>: Schedule and manage jobs</li>
        </ul>

        <h2>Settings</h2>
        <p>Go to <strong>Settings → Preferences</strong> to customize:</p>
        <ul>
            <li>Theme (Dark Mode / Light Mode)</li>
            <li>Language (English / Français)</li>
        </ul>

        <h2>Keyboard Shortcuts</h2>
        <table border="1" style="border-collapse: collapse; margin-top: 10px;">
            <tr>
                <th style="padding: 5px; background-color: #3d3d3d;">Shortcut</th>
                <th style="padding: 5px; background-color: #3d3d3d;">Action</th>
            </tr>
            <tr>
                <td style="padding: 5px;">Ctrl+Q</td>
                <td style="padding: 5px;">Quit application</td>
            </tr>
            <tr>
                <td style="padding: 5px;">F1</td>
                <td style="padding: 5px;">Show help (this page)</td>
            </tr>
        </table>

        <h2>About</h2>
        <p><strong>Version:</strong> 0.50.0<br>
        <strong>License:</strong> MIT<br>
        <strong>Author:</strong> Lestat2Lioncourt</p>

        <hr>
        <p style="text-align: center; opacity: 0.7;">
            For more information, visit the
            <a href="https://github.com/Lestat2Lioncourt/data-forge-studio">GitHub Repository</a>
        </p>
        """
