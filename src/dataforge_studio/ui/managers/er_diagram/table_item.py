"""
ER Table Item - Draggable, resizable QGraphicsItem representing a database table.

Uses QGraphicsProxyWidget for real scrollable column list.
"""

from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsProxyWidget,
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QAbstractItemView, QSizePolicy, QFrame
)
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QCursor, QFontMetrics
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject, QSize

import logging
logger = logging.getLogger(__name__)


class TableItemSignals(QObject):
    """Signals for ERTableItem (QGraphicsItem can't emit signals directly)."""
    position_changed = Signal(str, float, float)  # table_name, x, y


class _TableWidget(QFrame):
    """Internal widget rendered inside the QGraphicsProxyWidget."""

    def __init__(self, table_name: str, columns: List[Dict],
                 pk_columns: set, fk_columns: set,
                 schema_name: str = "", is_dark: bool = True):
        super().__init__()
        self.table_name = table_name
        self.setObjectName("ERTableWidget")

        # Colors
        if is_dark:
            bg = "#2d2d2d"
            header_bg = "#0078d4"
            border = "#555555"
            text = "#cccccc"
            pk_color = "#ffd700"
            fk_color = "#00bcd4"
            type_color = "#808080"
        else:
            bg = "#ffffff"
            header_bg = "#0078d4"
            border = "#cccccc"
            text = "#333333"
            pk_color = "#b8860b"
            fk_color = "#00838f"
            type_color = "#888888"

        self.setStyleSheet(f"""
            QFrame#ERTableWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QLabel#tableHeader {{
                background-color: {header_bg};
                color: white;
                font-weight: bold;
                font-family: Consolas;
                font-size: 10px;
                padding: 4px 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QListWidget {{
                background-color: {bg};
                border: none;
                font-family: Consolas;
                font-size: 9px;
                color: {text};
            }}
            QListWidget::item {{
                padding: 1px 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        display_name = f"{schema_name}.{table_name}" if schema_name else table_name
        header = QLabel(display_name)
        header.setObjectName("tableHeader")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFixedHeight(26)
        layout.addWidget(header)

        # Column list (scrollable)
        self.column_list = QListWidget()
        self.column_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.column_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.column_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.column_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for col in columns:
            col_name = col['name']
            col_type = col['type']

            if col_name in pk_columns:
                prefix = "PK "
                color = pk_color
            elif col_name in fk_columns:
                prefix = "FK "
                color = fk_color
            else:
                prefix = "   "
                color = text

            item = QListWidgetItem(f"{prefix}{col_name}  ({col_type})")
            item.setForeground(QColor(color))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.column_list.addItem(item)

        layout.addWidget(self.column_list)

        # Default size
        self._calc_width(columns)
        self.setMinimumSize(160, 80)

    def _calc_width(self, columns):
        """Calculate width based on content."""
        font = QFont("Consolas", 9)
        fm = QFontMetrics(font)
        max_w = fm.horizontalAdvance(self.table_name) + 40
        for col in columns:
            text = f"PK {col['name']}  ({col['type']})"
            max_w = max(max_w, fm.horizontalAdvance(text) + 20)
        self.setFixedWidth(max(180, min(max_w, 350)))


class ERTableItem(QGraphicsRectItem):
    """
    Draggable, resizable table representation in an ER diagram.

    Wraps a _TableWidget inside a QGraphicsProxyWidget.
    Supports resize via a handle in the bottom-right corner.
    """

    DEFAULT_HEIGHT = 200
    MIN_HEIGHT = 80
    RESIZE_MARGIN = 8

    def __init__(self, table_name: str, columns: List[Dict], pk_columns: List[str],
                 fk_columns: List[str], schema_name: str = "", is_dark: bool = True):
        super().__init__()
        self.table_name = table_name
        self.schema_name = schema_name
        self.columns = columns
        self.pk_columns = set(pk_columns)
        self.fk_columns = set(fk_columns)
        self.is_dark = is_dark

        # Signals
        self.signals = TableItemSignals()

        # Create the widget
        self._table_widget = _TableWidget(
            table_name, columns, self.pk_columns, self.fk_columns,
            schema_name, is_dark
        )

        # Determine initial height
        row_count = len(columns)
        natural_height = 26 + row_count * 22 + 10
        initial_height = min(natural_height, self.DEFAULT_HEIGHT)
        initial_height = max(initial_height, self.MIN_HEIGHT)

        self.width = self._table_widget.width()
        self.height = initial_height
        self._table_widget.setFixedHeight(initial_height)

        # Create proxy
        self._proxy = QGraphicsProxyWidget(self)
        self._proxy.setWidget(self._table_widget)
        self._proxy.setPos(0, 0)

        # Make rect match widget exactly — no extra space
        self.setRect(0, 0, self.width, self.height)
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setBrush(Qt.BrushStyle.NoBrush)

        # Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self.setZValue(1)

        # Resize state
        self._resizing = False
        self._resize_start_y = 0
        self._resize_start_height = 0

    def boundingRect(self):
        """Override to match exact widget size — prevents oversized selection."""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        """Draw selection border and resize handle."""
        if self.isSelected():
            painter.setPen(QPen(QColor("#0078d4"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(0, 0, self.width, self.height))

        # Resize handle (bottom-right triangle)
        m = self.RESIZE_MARGIN
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#888888"))
        from PySide6.QtGui import QPolygonF
        handle = QPolygonF([
            QPointF(self.width, self.height - m),
            QPointF(self.width - m, self.height),
            QPointF(self.width, self.height),
        ])
        painter.drawPolygon(handle)

    def hoverMoveEvent(self, event):
        """Change cursor near resize handle."""
        if self._is_near_resize_handle(event.pos()):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """Start resize if clicking on resize handle."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_near_resize_handle(event.pos()):
            self._resizing = True
            self._resize_start_y = event.scenePos().y()
            self._resize_start_height = self.height
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle resize dragging."""
        if self._resizing:
            delta_y = event.scenePos().y() - self._resize_start_y
            new_height = max(self.MIN_HEIGHT, self._resize_start_height + delta_y)
            self.prepareGeometryChange()
            self.height = new_height
            self._table_widget.setFixedHeight(int(new_height))
            self.setRect(0, 0, self.width, new_height)
            self.signals.position_changed.emit(self.table_name, self.pos().x(), self.pos().y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """End resize."""
        if self._resizing:
            self._resizing = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _is_near_resize_handle(self, pos: QPointF) -> bool:
        """Check if position is near the resize handle."""
        r = self.rect()
        m = self.RESIZE_MARGIN * 2
        return (pos.x() > r.right() - m and pos.y() > r.bottom() - m)

    def get_connection_point(self, side: str) -> QPointF:
        """Get connection point on a specific side of the table."""
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
        """Get connection point at a specific column row."""
        pos = self.scenePos()
        # Find column index
        for i, col in enumerate(self.columns):
            if col['name'] == column_name:
                # 26px header + index * ~22px row height + half row
                cy = 26 + i * 22 + 11
                # Clamp to visible area
                cy = min(cy, self.height - 5)
                cy = max(cy, 26)
                if side == 'left':
                    return QPointF(pos.x(), pos.y() + cy)
                else:
                    return QPointF(pos.x() + self.width, pos.y() + cy)
        return self.get_connection_point(side)

    def itemChange(self, change, value):
        """Handle item changes — notify position changes for FK line updates."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.prepareGeometryChange()
            self.signals.position_changed.emit(
                self.table_name, value.x(), value.y()
            )
        return super().itemChange(change, value)
