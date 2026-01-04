"""
Theme Preview Widget - Mini screen for live theme preview
"""

from typing import Dict, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics


class ThemePreview(QWidget):
    """
    A mini screen widget that displays a live preview of theme colors.

    Shows a simplified representation of:
    - TopBar with title
    - MenuBar with menu items
    - Left panel (TreeView)
    - Right panel (Grid with headers and rows)
    - StatusBar
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(350, 280)
        self.setMaximumHeight(350)

        # Default colors (dark theme) - using snake_case keys
        self._colors = {
            # Window
            "topbar_bg": "#2b2b2b",
            "topbar_fg": "#ffffff",
            "menubar_bg": "#3d3d3d",
            "menubar_fg": "#ffffff",
            "statusbar_bg": "#2b2b2b",
            "statusbar_fg": "#ffffff",
            # Frame
            "panel_bg": "#252525",
            "text_primary": "#e0e0e0",
            "text_secondary": "#808080",
            # Data
            "surface_bg": "#2d2d2d",
            "border_color": "#3d3d3d",
            "window_border": "#3d3d3d",
            # Interactive
            "hover_bg": "#383838",
            "selected_bg": "#0078d7",
            "selected_fg": "#ffffff",
            "accent": "#0078d7",
            # Semantic
            "info": "#3498db",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "important": "#9b59b6",
            # Log panel
            "log_bg": "#2d2d2d",
            "log_fg": "#e0e0e0",
            "log_info": "#3498db",
            "log_warning": "#f39c12",
            "log_error": "#e74c3c",
            "log_important": "#9b59b6",
            # Toolbar buttons
            "toolbar_button_bg": "#3d3d3d",
            "toolbar_button_fg": "#e0e0e0",
            "toolbar_button_border": "#3d3d3d",
            # Buttons
            "button_bg": "#2d2d2d",
            "button_fg": "#ffffff",
            "button_border": "#505050",
            # Splitter
            "splitter_bg": "#4d4d4d",
            "splitter_hover_bg": "#0078d7",
            # Tree
            "tree_header_bg": "#3d3d3d",
            "tree_header_fg": "#ffffff",
            "tree_selected_bg": "#0078d7",
            "tree_selected_fg": "#ffffff",
            # Grid
            "grid_header_bg": "#3d3d3d",
            "grid_header_fg": "#ffffff",
        }

    def set_colors(self, colors: Dict[str, str]):
        """
        Update the preview colors.

        Args:
            colors: Dictionary of color keys to hex values
        """
        self._colors.update(colors)
        self.update()

    def set_color(self, key: str, value: str):
        """
        Update a single color.

        Args:
            key: Color key (e.g., "TopBar_BG")
            value: Hex color value
        """
        self._colors[key] = value
        self.update()

    def get_color(self, key: str, default: str = "#808080") -> str:
        """Get a color value by key."""
        return self._colors.get(key, default)

    def paintEvent(self, event):
        """Paint the mini preview screen."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Calculate zones
        topbar_h = 22
        menubar_h = 20
        toolbar_h = 24
        statusbar_h = 18
        content_y = topbar_h + menubar_h + toolbar_h
        content_h = h - topbar_h - menubar_h - toolbar_h - statusbar_h

        # Left panel (TreeView) - 30% width
        left_w = int(w * 0.30)
        # Right panel - 70% width
        right_w = w - left_w

        # ===== TopBar =====
        self._draw_topbar(painter, QRect(0, 0, w, topbar_h))

        # ===== MenuBar =====
        self._draw_menubar(painter, QRect(0, topbar_h, w, menubar_h))

        # ===== Toolbar =====
        self._draw_toolbar(painter, QRect(0, topbar_h + menubar_h, w, toolbar_h))

        # ===== Left Panel (TreeView) =====
        splitter_w = 4
        self._draw_treeview(painter, QRect(0, content_y, left_w - splitter_w, content_h))

        # ===== Vertical Splitter (between left and right) =====
        self._draw_splitter(painter, QRect(left_w - splitter_w, content_y, splitter_w, content_h), vertical=True)

        # ===== Right Panel (split: grid top, log bottom) =====
        grid_h = int(content_h * 0.55)
        log_h = content_h - grid_h
        splitter_h = 4

        self._draw_grid(painter, QRect(left_w, content_y, right_w, grid_h - splitter_h))

        # ===== Horizontal Splitter (between grid and log) =====
        self._draw_splitter(painter, QRect(left_w, content_y + grid_h - splitter_h, right_w, splitter_h), vertical=False)

        self._draw_log_panel(painter, QRect(left_w, content_y + grid_h, right_w, log_h))

        # ===== StatusBar =====
        self._draw_statusbar(painter, QRect(0, h - statusbar_h, w, statusbar_h))

        # ===== Border around entire preview =====
        painter.setPen(QPen(QColor(self._colors.get("window_border", "#3d3d3d")), 1))
        painter.drawRect(0, 0, w - 1, h - 1)

    def _draw_topbar(self, painter: QPainter, rect: QRect):
        """Draw the TopBar area."""
        # Background
        painter.fillRect(rect, QColor(self._colors.get("topbar_bg", "#2b2b2b")))

        # Title text
        painter.setPen(QColor(self._colors.get("topbar_fg", "#ffffff")))
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "DataForge Studio")

        # Window buttons (simulated)
        btn_size = 12
        btn_y = (rect.height() - btn_size) // 2
        btn_spacing = 20
        btn_start = rect.width() - 70

        # Minimize
        painter.fillRect(btn_start, btn_y, btn_size, btn_size, QColor("#606060"))
        # Maximize
        painter.fillRect(btn_start + btn_spacing, btn_y, btn_size, btn_size, QColor("#606060"))
        # Close
        painter.fillRect(btn_start + 2 * btn_spacing, btn_y, btn_size, btn_size, QColor(self._colors.get("error", "#e74c3c")))

    def _draw_menubar(self, painter: QPainter, rect: QRect):
        """Draw the MenuBar area."""
        # Background
        painter.fillRect(rect, QColor(self._colors.get("menubar_bg", "#3d3d3d")))

        # Menu items
        painter.setPen(QColor(self._colors.get("menubar_fg", "#ffffff")))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        menus = ["Fichier", "Edition", "Outils", "Aide"]
        x = 10
        for menu in menus:
            fm = QFontMetrics(font)
            text_w = fm.horizontalAdvance(menu)
            painter.drawText(x, rect.y(), text_w + 10, rect.height(),
                           Qt.AlignmentFlag.AlignVCenter, menu)
            x += text_w + 20

    def _draw_treeview(self, painter: QPainter, rect: QRect):
        """Draw the TreeView (left panel) area."""
        # Background
        painter.fillRect(rect, QColor(self._colors.get("surface_bg", "#2d2d2d")))

        # Border
        painter.setPen(QPen(QColor(self._colors.get("border_color", "#3d3d3d")), 1))
        painter.drawRect(rect)

        # Header
        header_h = 18
        painter.fillRect(rect.x(), rect.y(), rect.width(), header_h,
                        QColor(self._colors.get("tree_header_bg", "#3d3d3d")))
        painter.setPen(QColor(self._colors.get("tree_header_fg", "#ffffff")))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(rect.x() + 5, rect.y(), rect.width(), header_h,
                        Qt.AlignmentFlag.AlignVCenter, "Items")

        # Tree items
        item_h = 16
        items_y = rect.y() + header_h + 2
        items = [
            ("  Catégorie 1", False),
            ("    Item A", False),
            ("    Item B", True),  # Selected
            ("  Catégorie 2", False),
            ("    Item C", False),
        ]

        font.setPointSize(7)
        painter.setFont(font)

        for i, (text, selected) in enumerate(items):
            item_rect = QRect(rect.x() + 2, items_y + i * item_h, rect.width() - 4, item_h)
            if selected:
                painter.fillRect(item_rect, QColor(self._colors.get("tree_selected_bg", "#0078d7")))
                painter.setPen(QColor(self._colors.get("tree_selected_fg", "#ffffff")))
            else:
                painter.setPen(QColor(self._colors.get("text_primary", "#e0e0e0")))
            painter.drawText(item_rect.adjusted(4, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, text)

    def _draw_grid(self, painter: QPainter, rect: QRect):
        """Draw the Grid (right panel) area."""
        # Background
        painter.fillRect(rect, QColor(self._colors.get("surface_bg", "#2d2d2d")))

        # Border
        painter.setPen(QPen(QColor(self._colors.get("border_color", "#3d3d3d")), 1))
        painter.drawRect(rect)

        # Get alternating row colors from theme or calculate
        line1_bg = self._colors.get("grid_line1_bg", self._colors.get("surface_bg", "#2d2d2d"))
        line2_bg = self._colors.get("grid_line2_bg")
        if not line2_bg:
            # Calculate alternate row color (slightly darker/lighter than line1)
            bg_color = QColor(line1_bg)
            if bg_color.lightness() > 128:  # Light theme
                line2_bg = bg_color.darker(105).name()
            else:  # Dark theme
                line2_bg = bg_color.lighter(110).name()

        # Header
        header_h = 18
        col_w = rect.width() // 3
        headers = ["Nom", "Type", "Valeur"]

        painter.fillRect(rect.x(), rect.y(), rect.width(), header_h,
                        QColor(self._colors.get("grid_header_bg", "#3d3d3d")))
        painter.setPen(QColor(self._colors.get("grid_header_fg", "#ffffff")))
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)

        for i, header in enumerate(headers):
            painter.drawText(rect.x() + i * col_w + 5, rect.y(), col_w, header_h,
                           Qt.AlignmentFlag.AlignVCenter, header)

        # Grid lines for header
        gridline_color = self._colors.get("grid_gridline", self._colors.get("border_color", "#3d3d3d"))
        painter.setPen(QPen(QColor(gridline_color), 1))
        for i in range(1, 3):
            x = rect.x() + i * col_w
            painter.drawLine(x, rect.y(), x, rect.y() + header_h)

        # Data rows
        row_h = 16
        rows_y = rect.y() + header_h
        data_rows = [
            ("query_1", "SELECT", "123"),
            ("script_a", "Python", "OK"),
            ("job_daily", "Job", "Active"),
            ("table_x", "Table", "1024"),
        ]

        font.setBold(False)
        font.setPointSize(7)
        painter.setFont(font)

        for row_idx, row_data in enumerate(data_rows):
            row_rect = QRect(rect.x(), rows_y + row_idx * row_h, rect.width(), row_h)

            # Alternating row colors (Line1/Line2)
            if row_idx % 2 == 0:
                painter.fillRect(row_rect, QColor(line1_bg))
            else:
                painter.fillRect(row_rect, QColor(line2_bg))

            painter.setPen(QColor(self._colors.get("text_primary", "#e0e0e0")))

            for col_idx, cell_value in enumerate(row_data):
                cell_rect = QRect(rect.x() + col_idx * col_w + 5, row_rect.y(),
                                 col_w - 10, row_h)
                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignVCenter, cell_value)

        # Grid lines
        painter.setPen(QPen(QColor(gridline_color), 1))
        # Vertical
        for i in range(1, 3):
            x = rect.x() + i * col_w
            painter.drawLine(x, rect.y() + header_h, x, rect.y() + rect.height())
        # Horizontal
        for i in range(1, len(data_rows) + 1):
            y = rows_y + i * row_h
            painter.drawLine(rect.x(), y, rect.x() + rect.width(), y)

    def _draw_toolbar(self, painter: QPainter, rect: QRect):
        """Draw toolbar with buttons."""
        # Background (same as panel)
        painter.fillRect(rect, QColor(self._colors.get("panel_bg", "#252525")))

        # Draw toolbar buttons
        btn_x = 5
        btn_h = 16
        btn_y = rect.y() + (rect.height() - btn_h) // 2
        btn_bg = self._colors.get("toolbar_button_bg", self._colors.get("panel_bg", "#252525"))
        btn_border = self._colors.get("toolbar_button_border", self._colors.get("border_color", "#3d3d3d"))
        btn_fg = self._colors.get("toolbar_button_fg", self._colors.get("text_primary", "#e0e0e0"))
        accent = self._colors.get("accent", "#0078d7")

        buttons = [("Nouveau", False), ("Ouvrir", False), ("Sauver", True), ("Executer", False)]
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)

        for btn_text, is_accent in buttons:
            fm = QFontMetrics(font)
            btn_w = fm.horizontalAdvance(btn_text) + 12

            # Button background
            if is_accent:
                painter.fillRect(btn_x, btn_y, btn_w, btn_h, QColor(accent))
                painter.setPen(QColor("#ffffff"))
            else:
                painter.fillRect(btn_x, btn_y, btn_w, btn_h, QColor(btn_bg))
                painter.setPen(QPen(QColor(btn_border), 1))
                painter.drawRect(btn_x, btn_y, btn_w, btn_h)
                painter.setPen(QColor(btn_fg))

            painter.drawText(btn_x, btn_y, btn_w, btn_h,
                           Qt.AlignmentFlag.AlignCenter, btn_text)
            btn_x += btn_w + 4

        # Draw an input field on the right
        input_w = 80
        input_x = rect.width() - input_w - 10
        input_bg = self._colors.get("input_bg", self._colors.get("surface_bg", "#2d2d2d"))
        input_border = self._colors.get("input_border", self._colors.get("border_color", "#3d3d3d"))

        painter.fillRect(input_x, btn_y, input_w, btn_h, QColor(input_bg))
        painter.setPen(QPen(QColor(input_border), 1))
        painter.drawRect(input_x, btn_y, input_w, btn_h)
        painter.setPen(QColor(self._colors.get("text_secondary", "#808080")))
        painter.drawText(input_x + 4, btn_y, input_w - 8, btn_h,
                        Qt.AlignmentFlag.AlignVCenter, "Rechercher...")

    def _draw_log_panel(self, painter: QPainter, rect: QRect):
        """Draw log panel with colored messages."""
        # Background
        log_bg = self._colors.get("log_bg", self._colors.get("surface_bg", "#2d2d2d"))
        painter.fillRect(rect, QColor(log_bg))

        # Border
        painter.setPen(QPen(QColor(self._colors.get("border_color", "#3d3d3d")), 1))
        painter.drawRect(rect)

        # Header
        header_h = 14
        painter.fillRect(rect.x(), rect.y(), rect.width(), header_h,
                        QColor(self._colors.get("menubar_bg", "#3d3d3d")))
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(self._colors.get("menubar_fg", "#ffffff")))
        painter.drawText(rect.x() + 5, rect.y(), rect.width(), header_h,
                        Qt.AlignmentFlag.AlignVCenter, "Logs")

        # Log entries
        log_y = rect.y() + header_h + 2
        line_h = 12
        font.setBold(False)
        font.setPointSize(6)
        painter.setFont(font)

        logs = [
            (self._colors.get("log_info", "#3498db"), "[INFO] Application demarree"),
            (self._colors.get("log_fg", "#ffffff"), "[LOG] Chargement des modules..."),
            (self._colors.get("log_important", "#9b59b6"), "[OK] Connexion etablie"),
            (self._colors.get("log_warning", "#f39c12"), "[WARN] Cache expire"),
            (self._colors.get("log_error", "#e74c3c"), "[ERR] Fichier introuvable"),
        ]

        for i, (color, text) in enumerate(logs):
            if log_y + i * line_h > rect.y() + rect.height() - 4:
                break
            painter.setPen(QColor(color))
            painter.drawText(rect.x() + 5, log_y + i * line_h, rect.width() - 10, line_h,
                           Qt.AlignmentFlag.AlignVCenter, text)

    def _draw_statusbar(self, painter: QPainter, rect: QRect):
        """Draw the StatusBar area."""
        # Background
        painter.fillRect(rect, QColor(self._colors.get("statusbar_bg", "#2b2b2b")))

        # Status text
        painter.setPen(QColor(self._colors.get("statusbar_fg", "#ffffff")))
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        painter.drawText(rect.adjusted(8, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter,
                        "Pret | 4 elements")

        # Semantic indicators on the right
        indicators = [
            (self._colors.get("important", "#9b59b6"), "OK"),
            (self._colors.get("warning", "#f39c12"), "!"),
            (self._colors.get("error", "#e74c3c"), "X"),
        ]
        x = rect.width() - 80
        for color, text in indicators:
            painter.setPen(QColor(color))
            painter.drawText(x, rect.y(), 20, rect.height(),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, text)
            x += 25

    def _draw_splitter(self, painter: QPainter, rect: QRect, vertical: bool = True):
        """Draw a splitter bar."""
        splitter_bg = self._colors.get("splitter_bg", self._colors.get("border_color", "#4d4d4d"))
        painter.fillRect(rect, QColor(splitter_bg))
