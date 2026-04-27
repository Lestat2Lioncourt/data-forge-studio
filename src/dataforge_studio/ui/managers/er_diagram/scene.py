"""
ER Diagram Scene - QGraphicsScene orchestrating tables and relationships.
"""

from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, QObject

from .table_item import ERTableItem
from .relationship_line import ERRelationshipLine
from .group_item import ERGroupItem
from ....database.schema_loaders.base import ForeignKeyInfo, PrimaryKeyInfo

import logging
logger = logging.getLogger(__name__)


class ERDiagramScene(QGraphicsScene):
    """
    Scene containing ERTableItems and ERRelationshipLines.

    Manages:
    - Adding/removing tables
    - Auto-detecting FK relationships
    - Auto-layout for initial placement
    - Position tracking for save
    """

    # Signal emitted when a table position changes (for auto-save)
    table_moved = Signal(str, float, float)  # table_name, x, y

    # Signal emitted when a relationship is hovered (HTML text, "" to hide)
    relation_hovered = Signal(str)

    # Signal emitted when a group's geometry changes (id, x, y, w, h)
    group_geometry_changed = Signal(str, float, float, float, float)

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._group_fks = True  # Default: merge all FKs between same table pair

        # Track items
        self._table_items: Dict[str, ERTableItem] = {}  # table_name -> ERTableItem
        self._relationship_lines: List[ERRelationshipLine] = []
        self._group_items: Dict[str, ERGroupItem] = {}  # group_id -> ERGroupItem

        # Background
        from ...core.theme_bridge import ThemeBridge
        palette = ThemeBridge.get_instance().get_er_diagram_colors()
        self.setBackgroundBrush(QColor(palette["scene_bg"]))

    def add_table(self, table_name: str, columns: List[Dict],
                  pk_columns: List[str], fk_columns: List[str],
                  schema_name: str = "",
                  pos_x: float = 0.0, pos_y: float = 0.0,
                  width: float = 0.0, height: float = 0.0) -> ERTableItem:
        """Add a table to the diagram. width/height=0 means "keep natural size"."""
        if table_name in self._table_items:
            return self._table_items[table_name]

        item = ERTableItem(
            table_name=table_name,
            columns=columns,
            pk_columns=pk_columns,
            fk_columns=fk_columns,
            schema_name=schema_name,
            is_dark=self.is_dark
        )
        item.setPos(pos_x, pos_y)
        if width > 0 and height > 0:
            item.set_size(width, height)
        item.signals.position_changed.connect(self.table_moved.emit)

        self.addItem(item)
        self._table_items[table_name] = item
        return item

    def get_table_sizes(self) -> Dict[str, tuple]:
        """Return current width/height per table: {name: (w, h)}."""
        return {
            name: (item.width, item.height)
            for name, item in self._table_items.items()
        }

    def remove_table(self, table_name: str):
        """Remove a table and its relationships from the diagram."""
        if table_name not in self._table_items:
            return

        item = self._table_items.pop(table_name)

        # Remove related FK lines
        lines_to_remove = [
            line for line in self._relationship_lines
            if line.from_table is item or line.to_table is item
        ]
        for line in lines_to_remove:
            self.removeItem(line)
            self._relationship_lines.remove(line)

        self.removeItem(item)

    def add_relationships(self, foreign_keys: List[ForeignKeyInfo]):
        """Add FK relationship lines. When group_fks is True (default), merges ALL FKs
        between a same pair of tables into a single wider line. Otherwise groups only
        composite FKs (by fk_name)."""
        from collections import OrderedDict

        if self._group_fks:
            # Group by (from_table, to_table) — merge ALL FKs between same pair
            pair_groups: OrderedDict = OrderedDict()
            pair_names: dict = {}  # (from, to) -> list of fk_names
            for fk in foreign_keys:
                key = (fk.from_table, fk.to_table)
                if key not in pair_groups:
                    pair_groups[key] = []
                    pair_names[key] = []
                pair = (fk.from_column, fk.to_column)
                if pair not in pair_groups[key]:
                    pair_groups[key].append(pair)
                if fk.fk_name and fk.fk_name not in pair_names[key]:
                    pair_names[key].append(fk.fk_name)

            for (from_tbl, to_tbl), pairs in pair_groups.items():
                from_item = self._table_items.get(from_tbl)
                to_item = self._table_items.get(to_tbl)
                if from_item and to_item:
                    names = pair_names[(from_tbl, to_tbl)]
                    display_name = " / ".join(names) if len(names) <= 2 else f"{len(names)} FK"
                    line = ERRelationshipLine(
                        from_table=from_item,
                        from_column=pairs[0][0],
                        to_table=to_item,
                        to_column=pairs[0][1],
                        fk_name=display_name,
                        is_dark=self.is_dark,
                        column_pairs=pairs,
                    )
                    self.addItem(line)
                    self._relationship_lines.append(line)
        else:
            # Group by fk_name only (composite FKs combined, separate FKs stay separate)
            groups: OrderedDict = OrderedDict()
            for fk in foreign_keys:
                key = (fk.fk_name or f"{fk.from_table}.{fk.from_column}", fk.from_table, fk.to_table)
                if key not in groups:
                    groups[key] = []
                pair = (fk.from_column, fk.to_column)
                if pair not in groups[key]:
                    groups[key].append(pair)

            for (fk_name, from_tbl, to_tbl), pairs in groups.items():
                from_item = self._table_items.get(from_tbl)
                to_item = self._table_items.get(to_tbl)
                if from_item and to_item:
                    line = ERRelationshipLine(
                        from_table=from_item,
                        from_column=pairs[0][0],
                        to_table=to_item,
                        to_column=pairs[0][1],
                        fk_name=fk_name,
                        is_dark=self.is_dark,
                        column_pairs=pairs
                    )
                    self.addItem(line)
                    self._relationship_lines.append(line)

        self._compute_line_offsets()

    def _compute_line_offsets(self):
        """Distribute FK anchors along shared sides to avoid overlap and minimize crossings.

        Two-pass:
        1. FROM side: sort by other_table position, assign evenly spaced positions.
        2. TO side: sort by counterpart from_anchor position (just assigned).
           If sides axes are perpendicular, reverse to avoid crossings.
        Pair-alone case: single line between two tables on parallel sides with range overlap
        becomes a single straight segment.
        """
        from collections import defaultdict
        from PySide6.QtCore import QPointF as _QPointF

        auto_lines = [ln for ln in self._relationship_lines if not ln._user_modified]
        if not auto_lines:
            return

        id_to_table = {id(t): t for t in self._table_items.values()}

        def edge_pt(table, side, i, n):
            tpos = table.scenePos()
            tw, th = table.width, table.height
            if side == 'left':
                return _QPointF(tpos.x(), tpos.y() + th * (i + 1) / (n + 1))
            if side == 'right':
                return _QPointF(tpos.x() + tw, tpos.y() + th * (i + 1) / (n + 1))
            if side == 'top':
                return _QPointF(tpos.x() + tw * (i + 1) / (n + 1), tpos.y())
            return _QPointF(tpos.x() + tw * (i + 1) / (n + 1), tpos.y() + th)

        # Determine sides per line. For multi-FK pairs (≥5 lines), spread across
        # perpendicular sides of the target to avoid dense clustering on one side.
        pair_lines: dict = defaultdict(list)
        for line in auto_lines:
            pair_lines[(id(line.from_table), id(line.to_table))].append(line)

        line_sides = {}
        for (_ft_id, _tt_id), lines in pair_lines.items():
            if not lines:
                continue
            base_from, base_to = lines[0]._auto_sides()
            ft = lines[0].from_table
            tt = lines[0].to_table

            # Single line or small group: position-aware side decision.
            # If target's center is outside source's Y (or X) range, attach on source's
            # perpendicular side (top/bottom or left/right). Otherwise use auto base sides.
            if len(lines) < 5:
                ft_top = ft.scenePos().y()
                ft_bot = ft.scenePos().y() + ft.height
                ft_lef = ft.scenePos().x()
                ft_rig = ft.scenePos().x() + ft.width
                tt_cx = tt.scenePos().x() + tt.width / 2
                tt_cy = tt.scenePos().y() + tt.height / 2

                if tt_cy < ft_top:
                    fs_auto, ts_auto = 'top', 'bottom'
                elif tt_cy > ft_bot:
                    fs_auto, ts_auto = 'bottom', 'top'
                elif tt_cx < ft_lef:
                    fs_auto, ts_auto = 'left', 'right'
                elif tt_cx > ft_rig:
                    fs_auto, ts_auto = 'right', 'left'
                else:
                    fs_auto, ts_auto = base_from, base_to

                for line in lines:
                    if line._user_modified:
                        fs = line._from_side or fs_auto
                        ts = line._to_side or ts_auto
                    else:
                        fs = fs_auto
                        ts = ts_auto
                        old_fs, old_ts = line._from_side, line._to_side
                        line._from_side = fs
                        line._to_side = ts
                        if old_fs != fs or old_ts != ts:
                            line._init_vertices()
                    line_sides[id(line)] = (fs, ts)
                continue

            # Multi-FK: check if target has an adjacent side that also faces source
            # perpendicular_side = perpendicular to base_to that still faces source
            base_horiz = base_to in ('left', 'right')
            ft_cy = ft.scenePos().y() + ft.height / 2
            ft_cx = ft.scenePos().x() + ft.width / 2
            tt_cy = tt.scenePos().y() + tt.height / 2
            tt_cx = tt.scenePos().x() + tt.width / 2

            if base_horiz:
                # Primary side is left/right; perpendicular is top or bottom
                perp = 'top' if ft_cy < tt_cy else 'bottom'
            else:
                perp = 'left' if ft_cx < tt_cx else 'right'

            # Split ratio based on ratio of base side length vs perp side length
            tt = lines[0].to_table
            if base_to in ('top', 'bottom'):
                base_len = tt.width
            else:
                base_len = tt.height
            if perp in ('top', 'bottom'):
                perp_len = tt.width
            else:
                perp_len = tt.height
            # Use ceil on the perp side so perpendicular sides get their "fair share"
            import math
            if (base_len + perp_len) > 0:
                perp_ratio = perp_len / (base_len + perp_len)
            else:
                perp_ratio = 0.5
            n_perp = max(1, min(len(lines) - 1, math.ceil(len(lines) * perp_ratio)))
            n_base = len(lines) - n_perp

            # Sort lines by TARGET position along source edge axis, then by column index.
            # This places anchors where they naturally want to go (above targets at top, below at bottom).
            fs_axis_vert = base_from in ('left', 'right')
            ft_columns = [c.get('name') for c in getattr(ft, 'columns', [])]

            def col_index(ln):
                try:
                    return ft_columns.index(ln.from_column)
                except (ValueError, AttributeError):
                    return 999
            def target_pos_outer(ln):
                tt = ln.to_table
                if fs_axis_vert:
                    return tt.scenePos().y() + tt.height / 2
                else:
                    return tt.scenePos().x() + tt.width / 2
            lines_sorted = sorted(lines, key=lambda ln: (target_pos_outer(ln), col_index(ln), ln.fk_name or ''))

            # Determine which END of fact's edge should host perp lines.
            # Perp lines go to the side of fact CLOSEST to Calendar's perp edge.
            # This matches the Y/X overlap zone used in distribution.
            ft = lines[0].from_table
            if fs_axis_vert:
                # Source edge varies along Y; check if Calendar is above or below fact
                perp_at_bottom = ft.scenePos().y() < tt.scenePos().y()  # fact above → perp zone at bottom of fact
            else:
                perp_at_bottom = ft.scenePos().x() < tt.scenePos().x()  # fact left → perp zone at right

            # Assign: perp gets lines at the "close to Calendar" end of fact's edge
            if perp_at_bottom:
                # Perp lines are at the END of the sorted list (bottommost/rightmost on fact edge)
                base_lines = lines_sorted[:n_base]
                perp_lines = lines_sorted[n_base:]
            else:
                # Perp lines are at the START of the sorted list (topmost/leftmost on fact edge)
                perp_lines = lines_sorted[:len(lines_sorted) - n_base]
                base_lines = lines_sorted[len(lines_sorted) - n_base:]

            for line in base_lines:
                if line._user_modified:
                    fs = line._from_side or base_from
                    ts = line._to_side or base_to
                else:
                    fs = base_from
                    ts = base_to
                line_sides[id(line)] = (fs, ts)
                if not line._user_modified:
                    old_fs, old_ts = line._from_side, line._to_side
                    line._from_side = fs
                    line._to_side = ts
                    if old_fs != fs or old_ts != ts:
                        line._init_vertices()
            for line in perp_lines:
                if line._user_modified:
                    fs = line._from_side or base_from
                    ts = line._to_side or perp
                else:
                    fs = base_from
                    ts = perp
                line_sides[id(line)] = (fs, ts)
                if not line._user_modified:
                    old_fs, old_ts = line._from_side, line._to_side
                    line._from_side = fs
                    line._to_side = ts
                    if old_fs != fs or old_ts != ts:
                        line._init_vertices()

        # --- Master / Slave anchor placement ---
        # For each edge (table, side), count how many lines attach to it. Per line,
        # the MASTER side is the one with the higher anchor count (tie → from-side).
        # The master lays out its anchors by its own distribution rule (angle-based
        # sort + uniform L/(n+1) spacing). The SLAVE then places its anchor at the
        # master's coordinate along the edge axis — clamped to the slave's edge range
        # — which produces a straight 1-segment line when geometrically possible,
        # and only bends (Z-path) otherwise.
        from math import atan2

        edge_anchor_count: dict = defaultdict(int)
        for line in auto_lines:
            fs, ts = line_sides[id(line)]
            edge_anchor_count[(id(line.from_table), fs)] += 1
            edge_anchor_count[(id(line.to_table), ts)] += 1

        line_master_is_from: dict = {}
        for line in auto_lines:
            fs, ts = line_sides[id(line)]
            nf = edge_anchor_count[(id(line.from_table), fs)]
            nt = edge_anchor_count[(id(line.to_table), ts)]
            line_master_is_from[id(line)] = (nf >= nt)

        # PASS M — master anchors: distribute uniformly on each master edge
        master_edge_lines: dict = defaultdict(list)
        for line in auto_lines:
            if line_master_is_from[id(line)]:
                master_edge_lines[(id(line.from_table), line_sides[id(line)][0])].append(line)
            else:
                master_edge_lines[(id(line.to_table), line_sides[id(line)][1])].append(line)

        for (mtable_id, mside), mlines in master_edge_lines.items():
            mtable = id_to_table.get(mtable_id)
            if not mtable:
                continue
            mpos = mtable.scenePos()
            mw, mh = mtable.width, mtable.height
            mcx = mpos.x() + mw / 2
            mcy = mpos.y() + mh / 2

            def _other_end(ln, _mid=mtable_id):
                return ln.to_table if id(ln.from_table) == _mid else ln.from_table

            def _angle_from_master(ln, _cx=mcx, _cy=mcy):
                ot = _other_end(ln)
                return atan2(ot.scenePos().y() + ot.height / 2 - _cy,
                             ot.scenePos().x() + ot.width / 2 - _cx)

            # Sort lines along the edge axis: angle for horizontal edges (avoids
            # deeper-over-shallower crossings), Y for vertical edges.
            if mside == 'top':
                mlines.sort(key=lambda ln: (_angle_from_master(ln), ln.fk_name or ''))
                edge_start, edge_end = mpos.x(), mpos.x() + mw
            elif mside == 'bottom':
                mlines.sort(key=lambda ln: (-_angle_from_master(ln), ln.fk_name or ''))
                edge_start, edge_end = mpos.x(), mpos.x() + mw
            else:  # left / right
                mlines.sort(key=lambda ln: (
                    _other_end(ln).scenePos().y() + _other_end(ln).height / 2,
                    ln.fk_name or ''))
                edge_start, edge_end = mpos.y(), mpos.y() + mh

            def _set_master_pos(ln, pos):
                vidx = 0 if line_master_is_from[id(ln)] else -1
                if mside == 'left':
                    ln._vertices[vidx] = _QPointF(mpos.x(), pos)
                elif mside == 'right':
                    ln._vertices[vidx] = _QPointF(mpos.x() + mw, pos)
                elif mside == 'top':
                    ln._vertices[vidx] = _QPointF(pos, mpos.y())
                else:
                    ln._vertices[vidx] = _QPointF(pos, mpos.y() + mh)

            # A line is PINNABLE on the master edge if its slave's center along
            # the master-edge axis falls inside the master edge range (minus a
            # small corner margin). Pinnable lines are placed at the slave's
            # own center → a 1-segment straight line. Other lines distribute
            # uniformly within the sub-segments between pins.
            CORNER_MARGIN = 10
            pinned: dict = {}
            for ln in mlines:
                ot = _other_end(ln)
                if mside in ('top', 'bottom'):
                    tcp = ot.scenePos().x() + ot.width / 2
                else:
                    tcp = ot.scenePos().y() + ot.height / 2
                if (edge_start + CORNER_MARGIN) < tcp < (edge_end - CORNER_MARGIN):
                    pinned[id(ln)] = tcp

            # Walk the sorted lines and build the sub-segments bounded by pins
            segments_to_fill = []  # (seg_start, seg_end, [lines])
            seg_start = edge_start
            current: list = []
            for ln in mlines:
                if id(ln) in pinned:
                    segments_to_fill.append((seg_start, pinned[id(ln)], current))
                    current = []
                    seg_start = pinned[id(ln)]
                else:
                    current.append(ln)
            segments_to_fill.append((seg_start, edge_end, current))

            # Place pinned lines at their own pin position
            for ln in mlines:
                if id(ln) in pinned:
                    _set_master_pos(ln, pinned[id(ln)])

            # Distribute non-pinned lines uniformly within each sub-segment
            for s_start, s_end, s_lines in segments_to_fill:
                m = len(s_lines)
                if m == 0:
                    continue
                sub_step = (s_end - s_start) / (m + 1)
                for i, ln in enumerate(s_lines):
                    _set_master_pos(ln, s_start + sub_step * (i + 1))

        # PASS S — slave anchors: match master's coord along the edge axis,
        # clamped to the slave's edge range (minus a small corner margin so the
        # anchor doesn't land exactly on a corner).
        SLAVE_CORNER_MARGIN = 5
        for line in auto_lines:
            fs, ts = line_sides[id(line)]
            is_from_master = line_master_is_from[id(line)]
            if is_from_master:
                master_anchor = line._vertices[0]
                slave_table = line.to_table
                slave_side = ts
                slave_vidx = -1
            else:
                master_anchor = line._vertices[-1]
                slave_table = line.from_table
                slave_side = fs
                slave_vidx = 0

            spos = slave_table.scenePos()
            sw, sh = slave_table.width, slave_table.height
            if slave_side in ('top', 'bottom'):
                x_min = spos.x() + SLAVE_CORNER_MARGIN
                x_max = spos.x() + sw - SLAVE_CORNER_MARGIN
                x = max(x_min, min(x_max, master_anchor.x()))
                y = spos.y() if slave_side == 'top' else spos.y() + sh
            else:  # left / right
                y_min = spos.y() + SLAVE_CORNER_MARGIN
                y_max = spos.y() + sh - SLAVE_CORNER_MARGIN
                y = max(y_min, min(y_max, master_anchor.y()))
                x = spos.x() if slave_side == 'left' else spos.x() + sw
            line._vertices[slave_vidx] = _QPointF(x, y)

        # Compute per-line mid_ratio to stagger Z-path middle segments
        # Group lines by (from_table, to_table, from_side, to_side)
        zpath_groups: dict = defaultdict(list)
        for line in auto_lines:
            fs, ts = line_sides[id(line)]
            f_vert = fs in ('left', 'right')
            t_vert = ts in ('left', 'right')
            if f_vert == t_vert:  # parallel sides → Z-path
                zpath_groups[(id(line.from_table), id(line.to_table), fs, ts)].append(line)

        line_mid_ratio = {}
        for group_key, group_lines in zpath_groups.items():
            n = len(group_lines)
            # Sort by source anchor position (top-to-bottom for vertical sides)
            fs = line_sides[id(group_lines[0])][0]
            if fs in ('left', 'right'):
                group_lines.sort(key=lambda ln: ln._vertices[0].y())
            else:
                group_lines.sort(key=lambda ln: ln._vertices[0].x())

            if n == 1:
                line_mid_ratio[id(group_lines[0])] = 0.5
                continue

            # Determine direction: is source "before" target in the relevant axis?
            ft = group_lines[0].from_table
            tt = group_lines[0].to_table
            if fs in ('left', 'right'):
                # Vertical sides (right/left) → staggering along X axis (stub length)
                # If source is ABOVE target: first line (topmost) has LONGEST stub (ratio high)
                # If source is BELOW target: first line has SHORTEST stub (ratio low)
                source_before = (ft.scenePos().y() + ft.height / 2) < (tt.scenePos().y() + tt.height / 2)
            else:
                # Horizontal sides (top/bottom) → staggering along Y axis
                source_before = (ft.scenePos().x() + ft.width / 2) < (tt.scenePos().x() + tt.width / 2)

            for i, line in enumerate(group_lines):
                # ratio 0.2 → near source, 0.8 → near target
                if source_before:
                    # First line gets longest stub (ratio close to 1)
                    ratio = 0.8 - (i * 0.6 / (n - 1))
                else:
                    # First line gets shortest stub (ratio close to 0)
                    ratio = 0.2 + (i * 0.6 / (n - 1))
                line_mid_ratio[id(line)] = ratio

        # Regenerate intermediate vertices using proper Z/L pattern with new endpoints
        for line in auto_lines:
            if len(line._vertices) == 2:
                a, b = line._vertices[0], line._vertices[1]
                if abs(a.x() - b.x()) < 1 or abs(a.y() - b.y()) < 1:
                    line._rebuild_path()
                    continue
            ratio = line_mid_ratio.get(id(line), 0.5)
            line.rebuild_intermediates(mid_ratio=ratio)
            line._rebuild_path()

    def auto_layout(self):
        """Arrange tables in a grid layout."""
        tables = list(self._table_items.values())
        if not tables:
            return

        # Simple grid layout
        cols = max(1, int(len(tables) ** 0.5))
        spacing_x = 300
        spacing_y = 350

        for i, item in enumerate(tables):
            row = i // cols
            col = i % cols
            item.setPos(col * spacing_x + 50, row * spacing_y + 50)

    def get_table_positions(self) -> Dict[str, tuple]:
        """Get current positions of all tables.

        Returns:
            Dict mapping table_name -> (x, y)
        """
        return {
            name: (item.scenePos().x(), item.scenePos().y())
            for name, item in self._table_items.items()
        }

    def get_table_item(self, table_name: str) -> Optional[ERTableItem]:
        """Get a table item by name."""
        return self._table_items.get(table_name)

    def unfreeze_all_tables(self):
        """Safety reset — ensure all tables are movable (fixes stuck state after drag bug)."""
        for item in self._table_items.values():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def get_fk_midpoints(self) -> list:
        """Get all waypoints for all FK lines that have been manually adjusted.

        Returns:
            List of dicts (one per waypoint, with seq for ordering).
        """
        midpoints = []
        for line in self._relationship_lines:
            wps = line.get_waypoints()
            for i, wp in enumerate(wps):
                midpoints.append({
                    'from_table': line.from_table.table_name,
                    'from_column': line.from_column,
                    'to_table': line.to_table.table_name,
                    'to_column': line.to_column,
                    'mid_x': wp.x(),
                    'mid_y': wp.y(),
                    'seq': i,
                })
        return midpoints

    def set_fk_midpoint(self, from_table: str, from_column: str,
                        to_table: str, to_column: str,
                        mid_x: float, mid_y: float, seq: int = 0):
        """Append a waypoint (at position seq) to a FK line."""
        from PySide6.QtCore import QPointF
        for line in self._relationship_lines:
            if (line.from_table.table_name == from_table and
                line.from_column == from_column and
                line.to_table.table_name == to_table and
                line.to_column == to_column):
                if not hasattr(line, '_pending_waypoints'):
                    line._pending_waypoints = []
                while len(line._pending_waypoints) <= seq:
                    line._pending_waypoints.append(None)
                line._pending_waypoints[seq] = QPointF(mid_x, mid_y)
                applied = [p for p in line._pending_waypoints if p is not None]
                line.set_waypoints(applied)
                return

    def reset_line_routing(self, line):
        """Clear manual geometry/overrides for one FK line and let auto-layout redo it."""
        line._user_modified = False
        line._from_side = None
        line._to_side = None
        if hasattr(line, '_pending_waypoints'):
            line._pending_waypoints = []
        line._init_vertices()
        self._compute_line_offsets()
        for ln in self._relationship_lines:
            ln._rebuild_path()

    def reset_all_routing(self):
        """Clear manual geometry/overrides on EVERY FK line and rerun the full
        auto-layout. Table positions, sizes and visual groups are untouched."""
        for line in self._relationship_lines:
            line._user_modified = False
            line._from_side = None
            line._to_side = None
            if hasattr(line, '_pending_waypoints'):
                line._pending_waypoints = []
            line._init_vertices()
        self._compute_line_offsets()
        for line in self._relationship_lines:
            line._rebuild_path()

    def set_show_fk_names(self, show: bool):
        """Show or hide FK names on all relationship lines."""
        for line in self._relationship_lines:
            line.set_show_label(show)

    def set_group_fks(self, group: bool):
        """Toggle grouping of multiple FKs between same pair of tables."""
        self._group_fks = group

    def set_show_column_types(self, show: bool):
        """Show or hide column types in all tables."""
        for item in self._table_items.values():
            item.set_show_types(show)

    def clear_all(self):
        """Remove all items from the scene."""
        self._table_items.clear()
        self._relationship_lines.clear()
        self._group_items.clear()
        self.clear()

    # ------------------------------------------------------------------
    # Groups (visual frames around tables)
    # ------------------------------------------------------------------
    def add_group(self, group_id: str, name: str, x: float, y: float,
                  width: float, height: float, color: str = "#B3E5FC") -> ERGroupItem:
        """Add a visual group frame to the scene."""
        if group_id in self._group_items:
            return self._group_items[group_id]
        item = ERGroupItem(group_id, name, x, y, width, height, color)
        item.signals.geometry_changed.connect(self.group_geometry_changed.emit)
        self.addItem(item)
        self._group_items[group_id] = item
        return item

    def remove_group(self, group_id: str):
        """Remove a visual group (tables inside stay in place)."""
        item = self._group_items.pop(group_id, None)
        if item is not None:
            self.removeItem(item)

    def get_groups(self) -> list:
        """Return list of (id, name, x, y, w, h, color) tuples for all groups."""
        result = []
        for gid, item in self._group_items.items():
            result.append((gid, item.name, item.pos().x(), item.pos().y(),
                           item.width, item.height, item.color))
        return result

    def get_group_item(self, group_id: str) -> Optional[ERGroupItem]:
        return self._group_items.get(group_id)

    def update_group(self, group_id: str, name: Optional[str] = None,
                     color: Optional[str] = None):
        """Update a group's name and/or color in place."""
        item = self._group_items.get(group_id)
        if item is None:
            return
        if name is not None:
            item.name = name
        if color is not None:
            item.color = color
        item.update()
