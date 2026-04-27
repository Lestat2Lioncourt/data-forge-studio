"""
ER Group Item — visual grouping frame around tables.

A translucent pastel-colored rectangle with a title, placed below tables so
relationship lines and table widgets remain fully visible. Dragging a group
moves the tables whose center is inside it at drag start (like a selection).
"""

from typing import Optional
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsItem
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QFont, QCursor
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject


class GroupSignals(QObject):
    """Signals for ERGroupItem (QGraphicsItem can't emit directly)."""
    geometry_changed = Signal(str, float, float, float, float)  # id, x, y, w, h


class ERGroupItem(QGraphicsRectItem):
    """Draggable, resizable pastel frame with title for grouping tables visually."""

    TITLE_HEIGHT = 22
    RESIZE_MARGIN = 10
    BORDER_RADIUS = 6

    # Pastel color presets (hex, alpha applied at paint time)
    PRESETS = [
        "#B3E5FC",  # pastel blue
        "#C8E6C9",  # pastel green
        "#FFF9C4",  # pastel yellow
        "#F8BBD0",  # pastel pink
        "#E1BEE7",  # pastel lavender
        "#FFCCBC",  # pastel peach
        "#D7CCC8",  # pastel taupe
        "#CFD8DC",  # pastel slate
    ]

    def __init__(self, group_id: str, name: str, x: float, y: float,
                 width: float, height: float, color: str = "#B3E5FC"):
        super().__init__(0, 0, width, height)
        self.group_id = group_id
        self.name = name
        self.color = color
        self.width = width
        self.height = height
        self.signals = GroupSignals()

        self.setPos(x, y)
        self.setZValue(-1)  # below tables (z=1) and lines (z=0)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self._resize_mode = None  # None | 'v' | 'h' | 'both'
        self._resize_start_pos = None
        self._resize_start_size = None
        self._drag_start_pos = None  # used to translate inner tables when moving
        self._captured_tables = []  # tables "inside" the group at drag start

    # ------------------------------------------------------------------
    def boundingRect(self):
        m = self.RESIZE_MARGIN
        return QRectF(0, 0, self.width + m, self.height + m)

    def shape(self):
        """Hit-test only the title bar and the resize strips. The body area stays
        paint-visible but transparent to clicks — FK lines/tables underneath can
        therefore be selected/dragged even when the group overlaps them."""
        from PySide6.QtGui import QPainterPath
        m = self.RESIZE_MARGIN
        path = QPainterPath()
        # Title bar (drag handle)
        path.addRect(QRectF(0, 0, self.width, self.TITLE_HEIGHT))
        # Right-edge resize strip (full height + corner overhang)
        path.addRect(QRectF(self.width - m, 0, m * 2, self.height + m))
        # Bottom-edge resize strip (full width + corner overhang)
        path.addRect(QRectF(0, self.height - m, self.width + m, m * 2))
        return path

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Pastel fill with transparency
        fill = QColor(self.color)
        fill.setAlpha(90)
        painter.setBrush(QBrush(fill))
        border = QColor(self.color)
        border.setAlpha(220)
        painter.setPen(QPen(border, 1.5))
        rect = QRectF(0, 0, self.width, self.height)
        painter.drawRoundedRect(rect, self.BORDER_RADIUS, self.BORDER_RADIUS)

        # Title bar (slightly darker top strip)
        title_rect = QRectF(0, 0, self.width, self.TITLE_HEIGHT)
        title_fill = QColor(self.color)
        title_fill.setAlpha(160)
        painter.setBrush(QBrush(title_fill))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(title_rect, self.BORDER_RADIUS, self.BORDER_RADIUS)
        # Fill the lower half so title bar doesn't have the bottom radius
        bottom_half = QRectF(0, self.TITLE_HEIGHT / 2, self.width, self.TITLE_HEIGHT / 2)
        painter.drawRect(bottom_half)

        # Title text — dark color for readability on pastel
        painter.setPen(QColor(50, 50, 50))
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(8, 2, self.width - 16, self.TITLE_HEIGHT - 4),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.name
        )

        # Selection border
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, self.BORDER_RADIUS, self.BORDER_RADIUS)

    # ------------------------------------------------------------------
    def _resize_mode_at(self, pos: QPointF) -> Optional[str]:
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

    def hoverMoveEvent(self, event):
        mode = self._resize_mode_at(event.pos())
        if mode == 'both':
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif mode == 'v':
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif mode == 'h':
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif pos_in_title := (event.pos().y() < self.TITLE_HEIGHT):
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            mode = self._resize_mode_at(event.pos())
            if mode:
                self._resize_mode = mode
                self._resize_start_pos = event.scenePos()
                self._resize_start_size = (self.width, self.height)
                event.accept()
                return
            # Capture tables inside the group for co-movement
            self._drag_start_pos = self.pos()
            self._captured_tables = self._tables_inside()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_mode:
            dx = event.scenePos().x() - self._resize_start_pos.x()
            dy = event.scenePos().y() - self._resize_start_pos.y()
            w0, h0 = self._resize_start_size
            new_w, new_h = w0, h0
            if self._resize_mode in ('h', 'both'):
                new_w = max(100, w0 + dx)
            if self._resize_mode in ('v', 'both'):
                new_h = max(60, h0 + dy)
            self.prepareGeometryChange()
            self.width = new_w
            self.height = new_h
            self.setRect(0, 0, new_w, new_h)
            self.signals.geometry_changed.emit(
                self.group_id, self.pos().x(), self.pos().y(), new_w, new_h
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_mode:
            self._resize_mode = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)
        self._captured_tables = []

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Translate captured tables along with group
            if self._drag_start_pos is not None and self._captured_tables:
                delta = self.pos() - self._drag_start_pos
                self._drag_start_pos = self.pos()
                for (tbl, start_pos) in self._captured_tables:
                    tbl.setPos(tbl.pos() + delta)
            self.signals.geometry_changed.emit(
                self.group_id, self.pos().x(), self.pos().y(), self.width, self.height
            )
        return super().itemChange(change, value)

    def _tables_inside(self):
        """Return tables whose center is within this group's bounding box at this instant."""
        from .table_item import ERTableItem
        result = []
        if not self.scene():
            return result
        my_rect = QRectF(self.pos(), QRectF(0, 0, self.width, self.height).size())
        for item in self.scene().items():
            if isinstance(item, ERTableItem):
                cx = item.pos().x() + item.width / 2
                cy = item.pos().y() + item.height / 2
                if my_rect.contains(QPointF(cx, cy)):
                    result.append((item, item.pos()))
        return result
