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

    ROW_HEIGHT = 17

    def __init__(self, table_name: str, columns: List[Dict],
                 pk_columns: set, fk_columns: set,
                 schema_name: str = "", is_dark: bool = True):
        super().__init__()
        self.table_name = table_name
        self.setObjectName("ERTableWidget")

        from ...core.theme_bridge import ThemeBridge
        palette = ThemeBridge.get_instance().get_er_diagram_colors()
        bg = palette["bg"]
        header_bg = palette["header_bg"]
        header_fg = palette["header_fg"]
        border = palette["border"]
        text = palette["text"]
        pk_color = palette["pk"]
        fk_color = palette["fk"]
        type_color = palette["type"]

        self.setStyleSheet(f"""
            QFrame#ERTableWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QLabel#tableHeader {{
                background-color: {header_bg};
                color: {header_fg};
                font-weight: 600;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 11px;
                padding: 4px 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QListWidget {{
                background-color: {bg};
                border: none;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 10px;
                color: {text};
            }}
            QListWidget::item {{
                padding: 1px 6px;
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
        header.setCursor(Qt.CursorShape.OpenHandCursor)
        layout.addWidget(header)

        # Column list (scrollable)
        self.column_list = QListWidget()
        self.column_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.column_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.column_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.column_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Store for rebuild on toggle
        self._columns = columns
        self._pk_columns = pk_columns
        self._fk_columns = fk_columns
        self._pk_color = pk_color
        self._fk_color = fk_color
        self._text_color = text
        self._show_types = True

        self._populate_column_list()

        layout.addWidget(self.column_list)

        # Default size
        self._calc_width()
        self.setMinimumSize(160, 80)

    def _populate_column_list(self):
        self.column_list.clear()
        for col in self._columns:
            col_name = col['name']
            col_type = col['type']

            if col_name in self._pk_columns:
                prefix = "PK "
                color = self._pk_color
            elif col_name in self._fk_columns:
                prefix = "FK "
                color = self._fk_color
            else:
                prefix = "   "
                color = self._text_color

            text = f"{prefix}{col_name}  ({col_type})" if self._show_types else f"{prefix}{col_name}"
            item = QListWidgetItem(text)
            item.setForeground(QColor(color))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setSizeHint(QSize(0, self.ROW_HEIGHT))
            self.column_list.addItem(item)

    def set_show_types(self, show: bool):
        """Toggle display of column types (e.g. '(NVARCHAR(50))')."""
        if show == self._show_types:
            return
        self._show_types = show
        self._populate_column_list()
        self._calc_width()

    def _calc_width(self) -> int:
        """Calculate width based on content and current display mode. Returns the final width."""
        font = QFont("Segoe UI", 9)
        fm = QFontMetrics(font)
        max_w = fm.horizontalAdvance(self.table_name) + 24
        for col in self._columns:
            text = f"PK {col['name']}  ({col['type']})" if self._show_types else f"PK {col['name']}"
            max_w = max(max_w, fm.horizontalAdvance(text) + 12)
        target = max(160, max_w)
        self.setFixedWidth(target)
        self._target_width = target
        return target


class ERTableItem(QGraphicsRectItem):
    """
    Draggable, resizable table representation in an ER diagram.

    Wraps a _TableWidget inside a QGraphicsProxyWidget.
    Supports resize via a handle in the bottom-right corner.
    """

    DEFAULT_HEIGHT = 200
    MIN_HEIGHT = 80
    MIN_WIDTH = 140
    RESIZE_MARGIN = 10

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
        natural_height = 26 + row_count * _TableWidget.ROW_HEIGHT + 10
        initial_height = min(natural_height, self.DEFAULT_HEIGHT)
        initial_height = max(initial_height, self.MIN_HEIGHT)

        # Use the computed target width (minimumWidth() gets clobbered by setMinimumSize)
        self.width = self._table_widget._target_width
        self.height = initial_height
        self._table_widget.setFixedHeight(initial_height)

        # Force widget to apply its fixed size before wrapping in proxy,
        # otherwise proxy caches the default QWidget size (~640) and renders too wide.
        self._table_widget.resize(self.width, initial_height)

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
        self._resize_mode = None  # None | 'v' | 'h' | 'both'
        self._resize_start_pos = None
        self._resize_start_size = None

    def set_size(self, width: float, height: float):
        """Apply a specific width/height (used when restoring persisted size)."""
        width = max(self.MIN_WIDTH, float(width))
        height = max(self.MIN_HEIGHT, float(height))
        self.prepareGeometryChange()
        self.width = width
        self.height = height
        self._table_widget.setMinimumSize(0, 0)
        self._table_widget.setMaximumSize(16777215, 16777215)
        self._table_widget.setFixedSize(int(width), int(height))
        self._table_widget._target_width = int(width)
        self._proxy.resize(int(width), int(height))
        self.setRect(0, 0, width, height)

    def set_show_types(self, show: bool):
        """Toggle column type display and resize to match new content width."""
        self._table_widget.set_show_types(show)
        new_width = self._table_widget._target_width
        if new_width != self.width:
            self.prepareGeometryChange()
            self.width = new_width
            self._table_widget.resize(new_width, self.height)
            self.setRect(0, 0, new_width, self.height)
            self.signals.position_changed.emit(self.table_name, self.pos().x(), self.pos().y())

    def boundingRect(self):
        """Include a small margin for resize grip areas (bottom + right)."""
        m = self.RESIZE_MARGIN
        return QRectF(0, 0, self.width + m, self.height + m)

    def shape(self):
        """Shape covers the widget area + resize grip strips so clicks hit the item."""
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRect(QRectF(0, 0, self.width + self.RESIZE_MARGIN, self.height + self.RESIZE_MARGIN))
        return path

    def paint(self, painter, option, widget=None):
        """Draw selection border and resize handle."""
        from ...core.theme_bridge import ThemeBridge
        palette = ThemeBridge.get_instance().get_er_diagram_colors()

        if self.isSelected():
            painter.setPen(QPen(QColor(palette["header_bg"]), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(0, 0, self.width, self.height))

        # Resize handle (bottom-right triangle)
        m = self.RESIZE_MARGIN
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette["popup_dim"]))
        from PySide6.QtGui import QPolygonF
        handle = QPolygonF([
            QPointF(self.width, self.height - m),
            QPointF(self.width - m, self.height),
            QPointF(self.width, self.height),
        ])
        painter.drawPolygon(handle)

    def hoverMoveEvent(self, event):
        """Change cursor near resize edges (bottom, right, corner)."""
        mode = self._resize_mode_at(event.pos())
        if mode == 'both':
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif mode == 'v':
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif mode == 'h':
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        """Start resize if clicking on the bottom, right, or corner grip area."""
        if event.button() == Qt.MouseButton.LeftButton:
            mode = self._resize_mode_at(event.pos())
            if mode:
                self._resize_mode = mode
                self._resize_start_pos = event.scenePos()
                self._resize_start_size = (self.width, self.height)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle resize dragging."""
        if self._resize_mode:
            dx = event.scenePos().x() - self._resize_start_pos.x()
            dy = event.scenePos().y() - self._resize_start_pos.y()
            w0, h0 = self._resize_start_size
            new_w, new_h = w0, h0
            if self._resize_mode in ('h', 'both'):
                new_w = max(self.MIN_WIDTH, w0 + dx)
            if self._resize_mode in ('v', 'both'):
                new_h = max(self.MIN_HEIGHT, h0 + dy)
            self.prepareGeometryChange()
            self.width = new_w
            self.height = new_h
            # Update the inner widget + proxy so the visible frame follows
            self._table_widget.setMinimumSize(0, 0)  # release previous fixed constraints
            self._table_widget.setMaximumSize(16777215, 16777215)
            self._table_widget.setFixedSize(int(new_w), int(new_h))
            self._table_widget._target_width = int(new_w)
            self._proxy.resize(int(new_w), int(new_h))
            self.setRect(0, 0, new_w, new_h)
            self.signals.position_changed.emit(self.table_name, self.pos().x(), self.pos().y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """End resize + force full viewport repaint to clear paint artifacts."""
        if self._resize_mode:
            self._resize_mode = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)
        if self.scene():
            for view in self.scene().views():
                view.viewport().update()

    def _resize_mode_at(self, pos: QPointF) -> Optional[str]:
        """Return 'both', 'v', 'h', or None based on grip zone under pos."""
        m = self.RESIZE_MARGIN
        near_right = (self.width - m) < pos.x() <= self.width + m
        near_bottom = (self.height - m) < pos.y() <= self.height + m
        if near_right and near_bottom:
            return 'both'
        if near_bottom and 0 <= pos.x() <= self.width + m:
            return 'v'
        if near_right and 0 <= pos.y() <= self.height + m:
            return 'h'
        return None

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
                rh = _TableWidget.ROW_HEIGHT
                cy = 26 + i * rh + rh // 2
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
