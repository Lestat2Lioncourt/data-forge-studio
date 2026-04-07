"""
ER Relationship Line - Auto-routing FK connector between tables.
"""

from typing import Optional
from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QPolygonF
from PySide6.QtCore import Qt, QPointF

from .table_item import ERTableItem

import logging
logger = logging.getLogger(__name__)


class ERRelationshipLine(QGraphicsPathItem):
    """
    FK relationship line between two ERTableItems.

    Auto-routes with orthogonal segments, choosing the best side
    (left/right/top/bottom) based on relative table positions.
    """

    LINE_COLOR = QColor("#ff9800")
    LINE_COLOR_SELECTED = QColor("#ffcc02")
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

        self.setZValue(0)  # Behind tables
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{from_table.table_name}.{from_column} → {to_table.table_name}.{to_column}")

        # Connect to position changes
        from_table.signals.position_changed.connect(lambda *_: self.update_path())
        to_table.signals.position_changed.connect(lambda *_: self.update_path())

        self.update_path()

    def update_path(self):
        """Recalculate the path based on current table positions."""
        # Determine best sides
        from_side, to_side = self._best_sides()

        from_pt = self.from_table.get_column_connection_point(self.from_column, from_side)
        to_pt = self.to_table.get_column_connection_point(self.to_column, to_side)

        # Build orthogonal path
        path = QPainterPath()
        path.moveTo(from_pt)

        if from_side in ('left', 'right') and to_side in ('left', 'right'):
            # Horizontal routing
            mid_x = (from_pt.x() + to_pt.x()) / 2
            path.lineTo(mid_x, from_pt.y())
            path.lineTo(mid_x, to_pt.y())
            path.lineTo(to_pt.x(), to_pt.y())
        elif from_side in ('top', 'bottom') and to_side in ('top', 'bottom'):
            # Vertical routing
            mid_y = (from_pt.y() + to_pt.y()) / 2
            path.lineTo(from_pt.x(), mid_y)
            path.lineTo(to_pt.x(), mid_y)
            path.lineTo(to_pt.x(), to_pt.y())
        else:
            # Mixed routing (one horizontal, one vertical)
            path.lineTo(from_pt.x(), to_pt.y())
            path.lineTo(to_pt.x(), to_pt.y())

        self.setPath(path)

    def _best_sides(self):
        """Determine the best connection sides based on relative positions."""
        from_pos = self.from_table.scenePos()
        to_pos = self.to_table.scenePos()
        from_w = self.from_table.width
        from_h = self.from_table.height
        to_w = self.to_table.width

        # Centers
        from_cx = from_pos.x() + from_w / 2
        from_cy = from_pos.y() + from_h / 2
        to_cx = to_pos.x() + to_w / 2
        to_cy = to_pos.y() + self.to_table.height / 2

        dx = to_cx - from_cx
        dy = to_cy - from_cy

        # Check for vertical alignment (tables stacked)
        horizontal_overlap = not (from_pos.x() + from_w < to_pos.x() or to_pos.x() + to_w < from_pos.x())

        if horizontal_overlap and abs(dy) > abs(dx):
            # Tables are vertically aligned — connect top/bottom
            if dy > 0:
                return 'bottom', 'top'
            else:
                return 'top', 'bottom'

        # Default: horizontal connection
        if dx > 0:
            return 'right', 'left'
        else:
            return 'left', 'right'

    def paint(self, painter: QPainter, option, widget=None):
        """Draw the relationship line with arrow."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self.LINE_COLOR_SELECTED if self.isSelected() else self.LINE_COLOR
        pen = QPen(color, self.LINE_WIDTH)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # Draw arrow at target end
        path = self.path()
        if path.elementCount() >= 2:
            # Get last two points for arrow direction
            last = QPointF(path.elementAt(path.elementCount() - 1).x,
                          path.elementAt(path.elementCount() - 1).y)
            prev = QPointF(path.elementAt(path.elementCount() - 2).x,
                          path.elementAt(path.elementCount() - 2).y)

            self._draw_arrow(painter, prev, last, color)

    def _draw_arrow(self, painter: QPainter, from_pt: QPointF, to_pt: QPointF, color: QColor):
        """Draw an arrowhead at to_pt pointing from from_pt."""
        import math
        dx = to_pt.x() - from_pt.x()
        dy = to_pt.y() - from_pt.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return

        # Normalize
        dx /= length
        dy /= length

        # Arrow points
        s = self.ARROW_SIZE
        p1 = QPointF(to_pt.x() - s * dx + s * 0.5 * dy,
                     to_pt.y() - s * dy - s * 0.5 * dx)
        p2 = QPointF(to_pt.x() - s * dx - s * 0.5 * dy,
                     to_pt.y() - s * dy + s * 0.5 * dx)

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        arrow = QPolygonF([to_pt, p1, p2])
        painter.drawPolygon(arrow)
