"""
ER Table Item - Draggable QGraphicsItem representing a database table.
"""

from typing import List, Optional, Dict
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject

import logging
logger = logging.getLogger(__name__)


class TableItemSignals(QObject):
    """Signals for ERTableItem (QGraphicsItem can't emit signals directly)."""
    position_changed = Signal(str, float, float)  # table_name, x, y


class ERTableItem(QGraphicsRectItem):
    """
    Draggable table representation in an ER diagram.

    Displays: table name header, columns with types, PK/FK indicators.
    """

    # Layout constants
    HEADER_HEIGHT = 28
    ROW_HEIGHT = 20
    MIN_WIDTH = 180
    H_PADDING = 8
    HEADER_FONT_SIZE = 10
    COLUMN_FONT_SIZE = 9
    TYPE_FONT_SIZE = 8

    def __init__(self, table_name: str, columns: List[Dict], pk_columns: List[str],
                 fk_columns: List[str], schema_name: str = "", is_dark: bool = True):
        """
        Args:
            table_name: Name of the table
            columns: List of {'name': str, 'type': str}
            pk_columns: List of primary key column names
            fk_columns: List of foreign key column names
            schema_name: Schema name (e.g., 'dbo')
            is_dark: Dark theme flag
        """
        super().__init__()
        self.table_name = table_name
        self.schema_name = schema_name
        self.columns = columns
        self.pk_columns = set(pk_columns)
        self.fk_columns = set(fk_columns)
        self.is_dark = is_dark

        # Signals
        self.signals = TableItemSignals()

        # Calculate dimensions
        self._calculate_size()

        # Setup item flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        # Z-value for stacking order
        self.setZValue(1)

    def _calculate_size(self):
        """Calculate table dimensions based on content."""
        font = QFont("Consolas", self.COLUMN_FONT_SIZE)
        fm = QFontMetrics(font)

        # Calculate width based on longest column text
        max_text_width = fm.horizontalAdvance(self.table_name) + 20
        for col in self.columns:
            prefix = "PK " if col['name'] in self.pk_columns else ("FK " if col['name'] in self.fk_columns else "   ")
            text = f"{prefix}{col['name']}  {col['type']}"
            max_text_width = max(max_text_width, fm.horizontalAdvance(text))

        self.width = max(self.MIN_WIDTH, max_text_width + self.H_PADDING * 2 + 10)
        self.height = self.HEADER_HEIGHT + len(self.columns) * self.ROW_HEIGHT + 4

        self.setRect(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        """Draw the table."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Colors
        if self.is_dark:
            bg_color = QColor("#2d2d2d")
            header_color = QColor("#0078d4")
            border_color = QColor("#0078d4") if self.isSelected() else QColor("#555555")
            text_color = QColor("#ffffff")
            col_color = QColor("#cccccc")
            type_color = QColor("#808080")
            pk_color = QColor("#ffd700")
            fk_color = QColor("#00bcd4")
        else:
            bg_color = QColor("#ffffff")
            header_color = QColor("#0078d4")
            border_color = QColor("#0078d4") if self.isSelected() else QColor("#cccccc")
            text_color = QColor("#ffffff")
            col_color = QColor("#333333")
            type_color = QColor("#888888")
            pk_color = QColor("#b8860b")
            fk_color = QColor("#00838f")

        border_width = 2 if self.isSelected() else 1

        # Background
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(0, 0, self.width, self.height, 4, 4)

        # Header
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(header_color))
        painter.drawRoundedRect(0, 0, self.width, self.HEADER_HEIGHT, 4, 4)
        # Square bottom corners of header
        painter.drawRect(0, self.HEADER_HEIGHT - 4, self.width, 4)

        # Table name
        header_font = QFont("Consolas", self.HEADER_FONT_SIZE, QFont.Weight.Bold)
        painter.setFont(header_font)
        painter.setPen(text_color)
        display_name = f"{self.schema_name}.{self.table_name}" if self.schema_name else self.table_name
        painter.drawText(self.H_PADDING, 4, self.width - self.H_PADDING * 2,
                         self.HEADER_HEIGHT - 4, Qt.AlignmentFlag.AlignVCenter, display_name)

        # Columns
        col_font = QFont("Consolas", self.COLUMN_FONT_SIZE)
        type_font = QFont("Consolas", self.TYPE_FONT_SIZE)

        for i, col in enumerate(self.columns):
            cy = self.HEADER_HEIGHT + i * self.ROW_HEIGHT + 2
            col_name = col['name']
            col_type = col['type']

            # PK/FK prefix and color
            if col_name in self.pk_columns:
                prefix = "PK "
                name_color = pk_color
            elif col_name in self.fk_columns:
                prefix = "FK "
                name_color = fk_color
            else:
                prefix = "   "
                name_color = col_color

            # Column name
            painter.setFont(col_font)
            painter.setPen(name_color)
            painter.drawText(self.H_PADDING, cy, self.width * 0.65,
                             self.ROW_HEIGHT, Qt.AlignmentFlag.AlignVCenter,
                             f"{prefix}{col_name}")

            # Column type (right-aligned)
            painter.setFont(type_font)
            painter.setPen(type_color)
            painter.drawText(self.width * 0.55, cy + 1, self.width * 0.4,
                             self.ROW_HEIGHT, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                             col_type)

    def get_connection_point(self, side: str) -> QPointF:
        """Get connection point on a specific side of the table.

        Args:
            side: 'left', 'right', 'top', 'bottom'

        Returns:
            Scene-coordinate point on the specified side
        """
        pos = self.scenePos()
        if side == 'left':
            return QPointF(pos.x(), pos.y() + self.height / 2)
        elif side == 'right':
            return QPointF(pos.x() + self.width, pos.y() + self.height / 2)
        elif side == 'top':
            return QPointF(pos.x() + self.width / 2, pos.y())
        elif side == 'bottom':
            return QPointF(pos.x() + self.width / 2, pos.y() + self.height)
        return pos

    def get_column_connection_point(self, column_name: str, side: str) -> QPointF:
        """Get connection point at a specific column row.

        Args:
            column_name: Name of the column
            side: 'left' or 'right'

        Returns:
            Scene-coordinate point at the column's row
        """
        pos = self.scenePos()
        # Find column index
        for i, col in enumerate(self.columns):
            if col['name'] == column_name:
                cy = self.HEADER_HEIGHT + i * self.ROW_HEIGHT + self.ROW_HEIGHT / 2
                if side == 'left':
                    return QPointF(pos.x(), pos.y() + cy)
                else:
                    return QPointF(pos.x() + self.width, pos.y() + cy)
        # Fallback to center
        return self.get_connection_point(side)

    def itemChange(self, change, value):
        """Handle item changes — notify position changes for FK line updates."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.signals.position_changed.emit(
                self.table_name, value.x(), value.y()
            )
        return super().itemChange(change, value)
