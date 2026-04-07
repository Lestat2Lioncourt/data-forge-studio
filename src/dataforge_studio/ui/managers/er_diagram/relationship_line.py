"""
ER Relationship Line - Auto-routing FK connector with draggable midpoint.
"""

from typing import Optional
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QPolygonF, QBrush, QCursor, QFont
from PySide6.QtCore import Qt, QPointF

from .table_item import ERTableItem

import logging
logger = logging.getLogger(__name__)


class _DragPoint(QGraphicsEllipseItem):
    """Draggable control point on a relationship line."""

    SIZE = 10

    def __init__(self, parent_line):
        super().__init__(-self.SIZE/2, -self.SIZE/2, self.SIZE, self.SIZE)
        self._parent_line = parent_line
        self.setBrush(QBrush(QColor("#ff9800")))
        self.setPen(QPen(QColor("#ffffff"), 1.5))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        self.setZValue(10)  # Well above tables (z=1) and lines (z=0)
        self.setVisible(False)

    def mousePressEvent(self, event):
        """Intercept press — freeze all tables to prevent co-dragging."""
        # Disable movable on all tables while we drag
        self._frozen_items = []
        if self.scene():
            for item in self.scene().items():
                if hasattr(item, 'table_name') and item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable:
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                    self._frozen_items.append(item)
        event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Restore movable on all tables after drag."""
        for item in getattr(self, '_frozen_items', []):
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self._frozen_items = []
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._parent_line.update_path_from_drag()
        return super().itemChange(change, value)


class ERRelationshipLine(QGraphicsPathItem):
    """
    FK relationship line between two ERTableItems.

    Auto-routes with orthogonal segments. Has a draggable midpoint
    for manual adjustment.
    """

    LINE_COLOR = QColor("#ff9800")
    LINE_COLOR_HOVER = QColor("#ffcc02")
    LINE_WIDTH = 2
    ARROW_SIZE = 8

    def __init__(self, from_table: ERTableItem, from_column: str,
                 to_table: ERTableItem, to_column: str,
                 fk_name: str = "", is_dark: bool = True):
        super().__init__()
        self.from_table = from_table
        self.from_column = from_column
        self.to_table = to_table
        self.to_column = to_column
        self.fk_name = fk_name
        self.is_dark = is_dark
        self._hovered = False
        self._drag_point: Optional[_DragPoint] = None
        self._custom_mid: Optional[QPointF] = None  # User-dragged midpoint
        self._label: Optional[QGraphicsTextItem] = None  # FK name label
        self._show_label = False

        self.setZValue(0)
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{from_table.table_name}.{from_column} → {to_table.table_name}.{to_column}")

        # Connect to position changes — reset custom midpoint when tables move
        from_table.signals.position_changed.connect(lambda *_: self._on_table_moved())
        to_table.signals.position_changed.connect(lambda *_: self._on_table_moved())

        self.update_path()

    def set_show_label(self, show: bool):
        """Show or hide the FK name label on the line."""
        self._show_label = show
        if show:
            self._ensure_label()
            if self._label:
                self._label.setVisible(True)
                self._update_label_position()
        elif self._label:
            self._label.setVisible(False)

    def _ensure_label(self):
        """Create the FK name label if not yet created."""
        if self._label is None and self.scene() and self.fk_name:
            self._label = QGraphicsTextItem()
            self._label.setPlainText(self.fk_name)
            font = QFont("Consolas", 7)
            self._label.setFont(font)
            color = QColor("#aaaaaa") if self.is_dark else QColor("#666666")
            self._label.setDefaultTextColor(color)
            self._label.setZValue(0.5)  # Between lines (0) and tables (1)
            self.scene().addItem(self._label)

    def _update_label_position(self):
        """Position the label at the center of the middle segment."""
        if self._label and hasattr(self, '_mid_seg_center'):
            # Offset slightly so it doesn't overlap the line
            self._label.setPos(
                self._mid_seg_center.x() + 4,
                self._mid_seg_center.y() - 12
            )

    def _on_table_moved(self):
        """Called when a connected table moves — reset custom midpoint and update."""
        self._custom_mid = None
        self.update_path()

    def _ensure_drag_point(self):
        """Create the drag point if not yet created."""
        if self._drag_point is None and self.scene():
            self._drag_point = _DragPoint(self)
            self.scene().addItem(self._drag_point)
            # Position at mid segment
            self._update_drag_point_position()

    def update_path(self):
        """Recalculate the path based on current table positions."""
        from_side, to_side = self._best_sides()

        from_pt = self.from_table.get_column_connection_point(self.from_column, from_side)
        to_pt = self.to_table.get_column_connection_point(self.to_column, to_side)

        # Build orthogonal path and track the middle segment for drag point
        path = QPainterPath()
        path.moveTo(from_pt)
        mid_seg_center = QPointF((from_pt.x() + to_pt.x()) / 2,
                                  (from_pt.y() + to_pt.y()) / 2)

        if self._custom_mid:
            mid = self._custom_mid
            path.lineTo(mid.x(), from_pt.y())
            path.lineTo(mid.x(), to_pt.y())
            path.lineTo(to_pt.x(), to_pt.y())
        elif from_side in ('left', 'right') and to_side in ('left', 'right'):
            mid_x = (from_pt.x() + to_pt.x()) / 2
            seg_start = QPointF(mid_x, from_pt.y())
            seg_end = QPointF(mid_x, to_pt.y())
            path.lineTo(seg_start)
            path.lineTo(seg_end)
            path.lineTo(to_pt.x(), to_pt.y())
            mid_seg_center = QPointF(mid_x, (from_pt.y() + to_pt.y()) / 2)
        elif from_side in ('top', 'bottom') and to_side in ('top', 'bottom'):
            mid_y = (from_pt.y() + to_pt.y()) / 2
            seg_start = QPointF(from_pt.x(), mid_y)
            seg_end = QPointF(to_pt.x(), mid_y)
            path.lineTo(seg_start)
            path.lineTo(seg_end)
            path.lineTo(to_pt.x(), to_pt.y())
            mid_seg_center = QPointF((from_pt.x() + to_pt.x()) / 2, mid_y)
        else:
            path.lineTo(from_pt.x(), to_pt.y())
            path.lineTo(to_pt.x(), to_pt.y())
            mid_seg_center = QPointF(from_pt.x(), to_pt.y())

        self.prepareGeometryChange()
        self.setPath(path)
        self._mid_seg_center = mid_seg_center

        # Update drag point at the center of the middle segment
        self._update_drag_point_position()

    def _update_drag_point_position(self):
        """Move the drag point to the center of the middle segment."""
        if self._drag_point and not self._custom_mid and hasattr(self, '_mid_seg_center'):
            self._drag_point.setPos(self._mid_seg_center)
        # Also update label position
        if self._show_label:
            self._update_label_position()

    def update_path_from_drag(self):
        """Called when the drag point is moved by the user."""
        if self._drag_point:
            self._custom_mid = self._drag_point.pos()
            self.update_path()

    def _best_sides(self):
        """Determine the best connection sides based on relative positions."""
        from_pos = self.from_table.scenePos()
        to_pos = self.to_table.scenePos()
        from_w = self.from_table.width
        from_h = self.from_table.height
        to_w = self.to_table.width

        from_cx = from_pos.x() + from_w / 2
        from_cy = from_pos.y() + from_h / 2
        to_cx = to_pos.x() + to_w / 2
        to_cy = to_pos.y() + self.to_table.height / 2

        dx = to_cx - from_cx
        dy = to_cy - from_cy

        horizontal_overlap = not (from_pos.x() + from_w < to_pos.x() or to_pos.x() + to_w < from_pos.x())

        if horizontal_overlap and abs(dy) > abs(dx):
            if dy > 0:
                return 'bottom', 'top'
            else:
                return 'top', 'bottom'

        if dx > 0:
            return 'right', 'left'
        else:
            return 'left', 'right'

    def hoverEnterEvent(self, event):
        """Show drag point on hover."""
        self._hovered = True
        if self.scene():
            self._ensure_drag_point()
            if self._drag_point:
                self._drag_point.setVisible(True)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Hide drag point when not hovering (unless it's being dragged)."""
        self._hovered = False
        if self._drag_point and not self._drag_point.isUnderMouse():
            self._drag_point.setVisible(False)
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        """Draw the relationship line with arrow."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self.LINE_COLOR_HOVER if self._hovered else self.LINE_COLOR
        pen = QPen(color, self.LINE_WIDTH)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # Arrow at target end
        path = self.path()
        if path.elementCount() >= 2:
            last = QPointF(path.elementAt(path.elementCount() - 1).x,
                          path.elementAt(path.elementCount() - 1).y)
            prev = QPointF(path.elementAt(path.elementCount() - 2).x,
                          path.elementAt(path.elementCount() - 2).y)
            self._draw_arrow(painter, prev, last, color)

    def _draw_arrow(self, painter: QPainter, from_pt: QPointF, to_pt: QPointF, color: QColor):
        """Draw an arrowhead at to_pt."""
        import math
        dx = to_pt.x() - from_pt.x()
        dy = to_pt.y() - from_pt.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return

        dx /= length
        dy /= length
        s = self.ARROW_SIZE

        p1 = QPointF(to_pt.x() - s * dx + s * 0.5 * dy,
                     to_pt.y() - s * dy - s * 0.5 * dx)
        p2 = QPointF(to_pt.x() - s * dx - s * 0.5 * dy,
                     to_pt.y() - s * dy + s * 0.5 * dx)

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([to_pt, p1, p2]))
