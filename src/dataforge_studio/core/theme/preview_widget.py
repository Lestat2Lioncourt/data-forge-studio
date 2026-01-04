"""
Theme Preview Widget - Visual preview of theme colors.

Displays a miniature preview of how a theme will look, including:
- Menu bar simulation
- Icon sidebar simulation
- Tree view simulation
- Grid/table simulation
- Log panel simulation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .generator import GeneratedTheme


class ThemePreviewWidget(QWidget):
    """
    Widget that shows a visual preview of a theme.

    Usage:
        preview = ThemePreviewWidget()
        preview.update_theme(generated_theme)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the preview UI structure."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main container with border
        self.container = QFrame()
        self.container.setFrameStyle(QFrame.Shape.StyledPanel)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Top bar (simulates menu/title bar)
        self.topbar = QFrame()
        self.topbar.setFixedHeight(28)
        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(8, 0, 8, 0)

        self.topbar_label = QLabel("Menu  File  Edit  View")
        self.topbar_label.setFont(QFont("Segoe UI", 8))
        topbar_layout.addWidget(self.topbar_label)
        topbar_layout.addStretch()

        container_layout.addWidget(self.topbar)

        # Main content area (icon sidebar + panels)
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        # Icon sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(36)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(4, 8, 4, 8)
        sidebar_layout.setSpacing(4)

        # Simulated icon buttons
        for i in range(4):
            icon_btn = QFrame()
            icon_btn.setFixedSize(28, 28)
            sidebar_layout.addWidget(icon_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            if i == 0:
                self.icon_selected = icon_btn
            else:
                setattr(self, f"icon_{i}", icon_btn)

        sidebar_layout.addStretch()
        content.addWidget(self.sidebar)

        # Panel area
        panels = QVBoxLayout()
        panels.setContentsMargins(4, 4, 4, 4)
        panels.setSpacing(4)

        # Top row: Tree + Grid
        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        # Tree preview
        self.tree_frame = QFrame()
        self.tree_frame.setMinimumWidth(100)
        tree_layout = QVBoxLayout(self.tree_frame)
        tree_layout.setContentsMargins(4, 4, 4, 4)
        tree_layout.setSpacing(2)

        self.tree_header = QLabel("Tree View")
        self.tree_header.setFont(QFont("Segoe UI", 7))
        tree_layout.addWidget(self.tree_header)

        for i in range(4):
            row = QLabel(f"  {'  ' if i > 0 else ''} Item {i + 1}")
            row.setFont(QFont("Consolas", 7))
            tree_layout.addWidget(row)
            setattr(self, f"tree_row_{i}", row)

        tree_layout.addStretch()
        top_row.addWidget(self.tree_frame)

        # Grid preview
        self.grid_frame = QFrame()
        self.grid_frame.setMinimumWidth(120)
        grid_layout = QVBoxLayout(self.grid_frame)
        grid_layout.setContentsMargins(4, 4, 4, 4)
        grid_layout.setSpacing(1)

        self.grid_header = QLabel("Col A    Col B    Col C")
        self.grid_header.setFont(QFont("Consolas", 7))
        grid_layout.addWidget(self.grid_header)

        for i in range(3):
            row = QLabel(f"val{i}1    val{i}2    val{i}3")
            row.setFont(QFont("Consolas", 7))
            grid_layout.addWidget(row)
            setattr(self, f"grid_row_{i}", row)

        grid_layout.addStretch()
        top_row.addWidget(self.grid_frame)

        panels.addLayout(top_row)

        # Bottom: Log preview
        self.log_frame = QFrame()
        self.log_frame.setFixedHeight(60)
        log_layout = QVBoxLayout(self.log_frame)
        log_layout.setContentsMargins(4, 4, 4, 4)
        log_layout.setSpacing(1)

        self.log_info = QLabel("[INFO] Connected to database")
        self.log_info.setFont(QFont("Consolas", 7))

        self.log_warning = QLabel("[WARNING] Slow query detected")
        self.log_warning.setFont(QFont("Consolas", 7))

        self.log_error = QLabel("[ERROR] Connection timeout")
        self.log_error.setFont(QFont("Consolas", 7))

        self.log_important = QLabel("[IMPORTANT] Schema changed")
        self.log_important.setFont(QFont("Consolas", 7))

        log_layout.addWidget(self.log_info)
        log_layout.addWidget(self.log_warning)
        log_layout.addWidget(self.log_error)
        log_layout.addWidget(self.log_important)
        log_layout.addStretch()

        panels.addWidget(self.log_frame)
        content.addLayout(panels)

        container_layout.addLayout(content)

        # Status bar
        self.statusbar = QFrame()
        self.statusbar.setFixedHeight(20)
        statusbar_layout = QHBoxLayout(self.statusbar)
        statusbar_layout.setContentsMargins(8, 0, 8, 0)

        self.statusbar_label = QLabel("Ready")
        self.statusbar_label.setFont(QFont("Segoe UI", 7))
        statusbar_layout.addWidget(self.statusbar_label)
        statusbar_layout.addStretch()

        container_layout.addWidget(self.statusbar)

        layout.addWidget(self.container)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 200)

    def update_theme(self, theme: GeneratedTheme):
        """
        Update the preview with colors from a theme.

        Args:
            theme: GeneratedTheme to preview
        """
        c = theme.colors

        # Container
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {c['panel_bg']};
                border: 1px solid {c['border_color']};
                border-radius: 4px;
            }}
        """)

        # Top bar
        self.topbar.setStyleSheet(f"""
            QFrame {{
                background-color: {c['topbar_bg']};
                border: none;
                border-bottom: 1px solid {c['border_color']};
            }}
        """)
        self.topbar_label.setStyleSheet(f"color: {c['topbar_fg']}; background: transparent;")

        # Sidebar
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {c['iconsidebar_bg']};
                border: none;
                border-right: 1px solid {c['border_color']};
            }}
        """)

        # Icon buttons
        self.icon_selected.setStyleSheet(f"""
            QFrame {{
                background-color: {c['iconsidebar_selected_bg']};
                border-radius: 4px;
            }}
        """)
        for i in range(1, 4):
            btn = getattr(self, f"icon_{i}", None)
            if btn:
                btn.setStyleSheet(f"""
                    QFrame {{
                        background-color: transparent;
                        border-radius: 4px;
                    }}
                    QFrame:hover {{
                        background-color: {c['iconsidebar_hover_bg']};
                    }}
                """)

        # Tree frame
        self.tree_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c['tree_bg']};
                border: 1px solid {c['border_color']};
                border-radius: 2px;
            }}
        """)
        self.tree_header.setStyleSheet(f"""
            color: {c['tree_header_fg']};
            background-color: {c['tree_header_bg']};
            padding: 2px;
        """)

        # Tree rows with alternating colors
        for i in range(4):
            row = getattr(self, f"tree_row_{i}", None)
            if row:
                bg = c['tree_line1_bg'] if i % 2 == 0 else c['tree_line2_bg']
                fg = c['tree_line1_fg'] if i % 2 == 0 else c['tree_line2_fg']
                # Highlight row 1 as selected
                if i == 1:
                    bg = c['tree_selected_bg']
                    fg = c['tree_selected_fg']
                row.setStyleSheet(f"color: {fg}; background-color: {bg}; padding: 1px;")

        # Grid frame
        self.grid_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c['grid_bg']};
                border: 1px solid {c['border_color']};
                border-radius: 2px;
            }}
        """)
        self.grid_header.setStyleSheet(f"""
            color: {c['grid_header_fg']};
            background-color: {c['grid_header_bg']};
            padding: 2px;
        """)

        # Grid rows with alternating colors
        for i in range(3):
            row = getattr(self, f"grid_row_{i}", None)
            if row:
                bg = c['grid_line1_bg'] if i % 2 == 0 else c['grid_line2_bg']
                fg = c['grid_line1_fg'] if i % 2 == 0 else c['grid_line2_fg']
                row.setStyleSheet(f"color: {fg}; background-color: {bg}; padding: 1px;")

        # Log frame
        self.log_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c['log_bg']};
                border: 1px solid {c['border_color']};
                border-radius: 2px;
            }}
        """)

        # Log messages with semantic colors
        self.log_info.setStyleSheet(f"color: {c['log_info']}; background: transparent;")
        self.log_warning.setStyleSheet(f"color: {c['log_warning']}; background: transparent;")
        self.log_error.setStyleSheet(f"color: {c['log_error']}; background: transparent;")
        self.log_important.setStyleSheet(f"color: {c['log_important']}; background: transparent;")

        # Status bar
        self.statusbar.setStyleSheet(f"""
            QFrame {{
                background-color: {c['statusbar_bg']};
                border: none;
                border-top: 1px solid {c['border_color']};
            }}
        """)
        self.statusbar_label.setStyleSheet(f"color: {c['statusbar_fg']}; background: transparent;")
