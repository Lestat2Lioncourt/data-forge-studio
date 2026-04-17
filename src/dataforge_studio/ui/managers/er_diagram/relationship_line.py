"""
ER Relationship Line — Orthogonal FK connector with per-segment drag points.

Path model: a list of vertices [from_pt, wp0, wp1, ..., to_pt].
- from_pt/to_pt are on table edges (recomputed when tables move)
- Waypoints (wp*) are user-adjustable via drag points
- On drag release: collinear segments merge, out-of-bounds anchors split
"""

from typing import Optional, List
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QPolygonF, QBrush, QCursor, QFont
from PySide6.QtCore import Qt, QPointF

from .table_item import ERTableItem

import logging
import math

logger = logging.getLogger(__name__)

MERGE_THRESHOLD = 5  # pixels — segments closer than this are considered collinear
GAP = 25  # stub length (pixels out from table edge)


class _DragPoint(QGraphicsEllipseItem):
    """Draggable control point on a relationship line segment."""

    SIZE = 10

    def __init__(self, parent_line):
        super().__init__(-self.SIZE / 2, -self.SIZE / 2, self.SIZE, self.SIZE)
        self._parent_line = parent_line
        self._seg_index = 0
        self._drag_start_pos = None
        from ...core.theme_bridge import ThemeBridge
        palette = ThemeBridge.get_instance().get_er_diagram_colors()
        self.setBrush(QBrush(QColor(palette["line"])))
        self.setPen(QPen(QColor(palette["header_fg"]), 1.5))
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setZValue(10)
        self.setVisible(False)

    def _freeze_tables(self):
        self._frozen_items = []
        if self.scene():
            for item in self.scene().items():
                if hasattr(item, 'table_name') and item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable:
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                    self._frozen_items.append(item)

    def _unfreeze_tables(self):
        for item in getattr(self, '_frozen_items', []):
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self._frozen_items = []

    def mousePressEvent(self, event):
        self._freeze_tables()
        self._drag_start_pos = self.pos()
        event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._unfreeze_tables()
        self._parent_line._on_drag_release()
        super().mouseReleaseEvent(event)

    def ungrabMouse(self):
        self._unfreeze_tables()
        super().ungrabMouse()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if not self._parent_line._repositioning:
                self._parent_line._on_segment_dragged(self._seg_index, self.pos())
        return super().itemChange(change, value)


class ERRelationshipLine(QGraphicsPathItem):
    """
    FK relationship line between two ERTableItems.

    Path = list of vertices. First vertex on from_table edge, last on to_table edge.
    Intermediate vertices (waypoints) are user-adjustable.
    """

    LINE_WIDTH = 2
    ARROW_SIZE = 8

    @staticmethod
    def _palette():
        from ...core.theme_bridge import ThemeBridge
        return ThemeBridge.get_instance().get_er_diagram_colors()

    def __init__(self, from_table: ERTableItem, from_column: str,
                 to_table: ERTableItem, to_column: str,
                 fk_name: str = "", is_dark: bool = True,
                 column_pairs: list = None):
        super().__init__()
        self.from_table = from_table
        self.to_table = to_table
        self.from_column = from_column
        self.to_column = to_column
        self.fk_name = fk_name
        self.is_dark = is_dark
        self.column_pairs = column_pairs or [(from_column, to_column)]

        self._vertices: List[QPointF] = []  # Full path: [from_pt, wp..., to_pt]
        self._drag_points: list = []
        self._repositioning = False
        self._hovered = False
        self._label: Optional[QGraphicsTextItem] = None
        self._show_label = False

        self.setZValue(0)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        from_table.signals.position_changed.connect(lambda *_: self._on_table_moved())
        to_table.signals.position_changed.connect(lambda *_: self._on_table_moved())

        self._init_vertices()
        self._rebuild_path()

    # =====================================================================
    # Vertex model
    # =====================================================================

    def _auto_sides(self):
        """Auto-compute best connection sides based on relative table positions."""
        fp = self.from_table.scenePos()
        tp = self.to_table.scenePos()
        fw, fh = self.from_table.width, self.from_table.height
        tw = self.to_table.width

        dx = (tp.x() + tw / 2) - (fp.x() + fw / 2)
        dy = (tp.y() + self.to_table.height / 2) - (fp.y() + fh / 2)

        h_overlap = not (fp.x() + fw < tp.x() or tp.x() + tw < fp.x())
        if h_overlap and abs(dy) > abs(dx):
            return ('bottom', 'top') if dy > 0 else ('top', 'bottom')
        return ('right', 'left') if dx > 0 else ('left', 'right')

    def _exit_vector(self, side):
        vecs = {'left': (-GAP, 0), 'right': (GAP, 0), 'top': (0, -GAP), 'bottom': (0, GAP)}
        return vecs[side]

    def _init_vertices(self):
        """Generate initial vertices for auto-routing."""
        from_side, to_side = self._auto_sides()
        fp = self.from_table.get_connection_point(from_side)
        tp = self.to_table.get_connection_point(to_side)

        dx_f, dy_f = self._exit_vector(from_side)
        dx_t, dy_t = self._exit_vector(to_side)
        stub_f = QPointF(fp.x() + dx_f, fp.y() + dy_f)
        stub_t = QPointF(tp.x() + dx_t, tp.y() + dy_t)

        f_horiz = from_side in ('left', 'right')
        t_horiz = to_side in ('left', 'right')

        if f_horiz and t_horiz:
            mid_x = (stub_f.x() + stub_t.x()) / 2
            self._vertices = [fp, stub_f,
                              QPointF(mid_x, stub_f.y()),
                              QPointF(mid_x, stub_t.y()),
                              stub_t, tp]
        elif not f_horiz and not t_horiz:
            mid_y = (stub_f.y() + stub_t.y()) / 2
            self._vertices = [fp, stub_f,
                              QPointF(stub_f.x(), mid_y),
                              QPointF(stub_t.x(), mid_y),
                              stub_t, tp]
        else:
            if f_horiz:
                self._vertices = [fp, stub_f,
                                  QPointF(stub_t.x(), stub_f.y()),
                                  stub_t, tp]
            else:
                self._vertices = [fp, stub_f,
                                  QPointF(stub_f.x(), stub_t.y()),
                                  stub_t, tp]

    def set_waypoints(self, waypoints: List[QPointF]):
        """Restore waypoints (loaded from DB). Replaces intermediate vertices."""
        if not waypoints:
            return
        from_side, to_side = self._auto_sides()
        fp = self.from_table.get_connection_point(from_side)
        tp = self.to_table.get_connection_point(to_side)
        self._vertices = [fp] + waypoints + [tp]
        self._rebuild_path()

    def get_waypoints(self) -> List[QPointF]:
        """Return intermediate waypoints (for save). Excludes from_pt/to_pt."""
        if len(self._vertices) <= 2:
            return []
        return list(self._vertices[1:-1])

    # =====================================================================
    # Path rendering
    # =====================================================================

    def _rebuild_path(self):
        """Rebuild the QPainterPath from current vertices."""
        if len(self._vertices) < 2:
            return
        path = QPainterPath()
        path.moveTo(self._vertices[0])
        for v in self._vertices[1:]:
            path.lineTo(v)

        self.prepareGeometryChange()
        self.setPath(path)
        self._mid_seg_center = path.pointAtPercent(0.5)

        if self._drag_points:
            self._sync_drag_points()
        if self._show_label:
            self._update_label_position()

    # =====================================================================
    # Drag points
    # =====================================================================

    def _sync_drag_points(self):
        """Create/update one drag point per segment (skip very short ones)."""
        if not self.scene():
            return
        n_segs = len(self._vertices) - 1
        centers = []
        for i in range(n_segs):
            a, b = self._vertices[i], self._vertices[i + 1]
            length = math.sqrt((b.x() - a.x()) ** 2 + (b.y() - a.y()) ** 2)
            if length >= 10:
                centers.append((i, QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)))

        # Adjust pool size
        while len(self._drag_points) < len(centers):
            dp = _DragPoint(self)
            dp.setVisible(False)
            self.scene().addItem(dp)
            self._drag_points.append(dp)
        while len(self._drag_points) > len(centers):
            dp = self._drag_points.pop()
            if dp.scene():
                dp.scene().removeItem(dp)

        self._repositioning = True
        for dp, (seg_idx, center) in zip(self._drag_points, centers):
            dp._seg_index = seg_idx
            dp.setPos(center)
        self._repositioning = False

    # =====================================================================
    # Drag handling
    # =====================================================================

    def _is_horizontal(self, seg_index: int) -> bool:
        a, b = self._vertices[seg_index], self._vertices[seg_index + 1]
        return abs(b.y() - a.y()) < abs(b.x() - a.x())

    def _on_segment_dragged(self, seg_index: int, new_center: QPointF):
        """Called during drag — move the segment's two vertices."""
        if seg_index >= len(self._vertices) - 1:
            return
        a = self._vertices[seg_index]
        b = self._vertices[seg_index + 1]
        horiz = self._is_horizontal(seg_index)

        if horiz:
            # Horizontal segment: user drags vertically → change Y of both vertices
            new_y = new_center.y()
            # Clamp vertex 0 (from_pt) to table edge
            if seg_index == 0:
                new_y = self._clamp_to_table(self.from_table, 'y', new_y)
            self._vertices[seg_index] = QPointF(a.x(), new_y)
            # Clamp last vertex (to_pt)
            if seg_index + 1 == len(self._vertices) - 1:
                new_y = self._clamp_to_table(self.to_table, 'y', new_y)
            self._vertices[seg_index + 1] = QPointF(b.x(), new_y)
        else:
            # Vertical segment: user drags horizontally → change X of both vertices
            new_x = new_center.x()
            if seg_index == 0:
                new_x = self._clamp_to_table(self.from_table, 'x', new_x)
            self._vertices[seg_index] = QPointF(new_x, a.y())
            if seg_index + 1 == len(self._vertices) - 1:
                new_x = self._clamp_to_table(self.to_table, 'x', new_x)
            self._vertices[seg_index + 1] = QPointF(new_x, b.y())

        self._rebuild_path()

    def _clamp_to_table(self, table, axis: str, value: float) -> float:
        """Clamp a coordinate to the table's bounding box."""
        pos = table.scenePos()
        if axis == 'y':
            return max(pos.y() + 5, min(value, pos.y() + table.height - 5))
        else:
            return max(pos.x() + 5, min(value, pos.x() + table.width - 5))

    def _on_drag_release(self):
        """Called on mouseRelease — merge collinear segments, rebuild points."""
        self._merge_collinear()
        self._rebuild_path()

    def _merge_collinear(self):
        """Remove intermediate vertices where adjacent segments are collinear."""
        if len(self._vertices) <= 3:
            return  # Need at least from + 2 wp + to to have something to merge
        merged = [self._vertices[0]]
        for i in range(1, len(self._vertices) - 1):
            prev = merged[-1]
            curr = self._vertices[i]
            nxt = self._vertices[i + 1]
            # Check if prev→curr→nxt are collinear (all same X or all same Y within threshold)
            same_x = abs(prev.x() - curr.x()) < MERGE_THRESHOLD and abs(curr.x() - nxt.x()) < MERGE_THRESHOLD
            same_y = abs(prev.y() - curr.y()) < MERGE_THRESHOLD and abs(curr.y() - nxt.y()) < MERGE_THRESHOLD
            if not (same_x or same_y):
                merged.append(curr)
        merged.append(self._vertices[-1])
        self._vertices = merged

    # =====================================================================
    # Table movement
    # =====================================================================

    def _on_table_moved(self):
        """Recompute from_pt / to_pt when tables move; keep waypoints."""
        if len(self._vertices) < 2:
            return
        from_side, to_side = self._auto_sides()
        self._vertices[0] = self.from_table.get_connection_point(from_side)
        self._vertices[-1] = self.to_table.get_connection_point(to_side)
        self._rebuild_path()

    # =====================================================================
    # Labels
    # =====================================================================

    def set_show_label(self, show: bool):
        self._show_label = show
        if show:
            self._ensure_label()
            if self._label:
                self._label.setVisible(True)
                self._update_label_position()
        elif self._label:
            self._label.setVisible(False)

    def _ensure_label(self):
        if self._label is None and self.scene() and self.fk_name:
            self._label = QGraphicsTextItem()
            self._label.setPlainText(self.fk_name)
            self._label.setFont(QFont("Consolas", 7))
            self._label.setDefaultTextColor(QColor(self._palette()["popup_dim"]))
            self._label.setZValue(0.5)
            self.scene().addItem(self._label)

    def _update_label_position(self):
        if self._label and hasattr(self, '_mid_seg_center'):
            self._label.setPos(self._mid_seg_center.x() + 4, self._mid_seg_center.y() - 12)

    # =====================================================================
    # Hover
    # =====================================================================

    def hoverEnterEvent(self, event):
        self._hovered = True
        if self.scene():
            self._sync_drag_points()
            for dp in self._drag_points:
                dp.setVisible(True)
            palette = self._palette()
            fk_color, pk_color, dim = palette["fk"], palette["pk"], palette["popup_dim"]
            fk_header = f"<span style='color:{dim}'>{self.fk_name}</span><br>" if self.fk_name else ""
            pairs_html = [
                f"&nbsp;&nbsp;&nbsp;&nbsp;"
                f"<span style='color:{fk_color}'><b>{self.from_table.table_name}.{fc}</b></span>"
                f" <span style='color:{dim}'>&rarr;</span> "
                f"<span style='color:{pk_color}'><b>{self.to_table.table_name}.{tc}</b></span>"
                for fc, tc in self.column_pairs
            ]
            self.scene().relation_hovered.emit(fk_header + "<br>".join(pairs_html))
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        for dp in self._drag_points:
            if not dp.isUnderMouse():
                dp.setVisible(False)
        if self.scene():
            self.scene().relation_hovered.emit("")
        self.update()
        super().hoverLeaveEvent(event)

    # =====================================================================
    # Paint
    # =====================================================================

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self._palette()
        color = QColor(palette["line_hover"] if self._hovered else palette["line"])

        pen = QPen(color, self.LINE_WIDTH)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        path = self.path()
        if path.elementCount() >= 2:
            # Circle at source (FK origin)
            first = QPointF(path.elementAt(0).x, path.elementAt(0).y)
            r = self.ARROW_SIZE * 0.4
            painter.setPen(QPen(color, self.LINE_WIDTH))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(first, r, r)

            # Arrow at target (PK destination)
            last = QPointF(path.elementAt(path.elementCount() - 1).x,
                           path.elementAt(path.elementCount() - 1).y)
            prev = QPointF(path.elementAt(path.elementCount() - 2).x,
                           path.elementAt(path.elementCount() - 2).y)
            self._draw_arrow(painter, prev, last, color)

    def _draw_arrow(self, painter: QPainter, from_pt: QPointF, to_pt: QPointF, color: QColor):
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
