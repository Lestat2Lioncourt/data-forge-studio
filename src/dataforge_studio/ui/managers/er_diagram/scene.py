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

    # Signal emitted when a FK line's routing is edited (drag, split, delete,
    # reset) — lets the manager flag the diagram as having unsaved changes
    routing_changed = Signal()

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._group_fks = True  # Default: merge all FKs between same table pair
        self._read_only = False

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

    # ==================================================================
    # Auto-routing — rules R1..R5 are specified in docs/ER_DIAGRAMS_ROUTING.md
    # ==================================================================

    # R3.1 — a straight link is kept only if its anchor stays at least this
    # fraction of the homogeneous step away from both ends of its edge.
    HOMOGENEITY_MIN = 0.5
    # Minimum edge overlap (px) making a straight link geometrically possible.
    STRAIGHT_MIN_OVERLAP = 20
    # R3.2 (interim) — a table carrying at least this many outgoing links
    # spreads them on its lateral sides instead of crowding a single side.
    LATERAL_SPREAD_MIN = 2

    def _compute_line_offsets(self):
        """Route every auto line: choose sides, place anchors, rebuild paths.

        Implements docs/ER_DIAGRAMS_ROUTING.md — R1 straight > L > Z,
        R2 inclusion-constrained anchors, R3 form/side choice, R4 homogeneous
        distribution per sub-segment, R5 crossing-free ordering on an edge.
        """
        auto_lines = [ln for ln in self._relationship_lines if not ln._user_modified]
        if not auto_lines:
            return
        line_sides, pin_coord = self._assign_sides(auto_lines)
        self._place_anchors(auto_lines, line_sides, pin_coord)
        self._rebuild_all(auto_lines, line_sides)

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _span(table, side):
        """(start, end) of an edge along its own axis."""
        p = table.scenePos()
        if side in ('top', 'bottom'):
            return p.x(), p.x() + table.width
        return p.y(), p.y() + table.height

    @staticmethod
    def _shared_coord(a0, a1, b0, b1):
        """R2 — coordinate of a straight link between two overlapping spans.

        When one span is included in the other, the included one imposes its
        middle: it has the least room, and the point is then guaranteed to fall
        inside the wider span. Otherwise the middle of the overlap is used.
        """
        if b0 >= a0 and b1 <= a1:
            return (b0 + b1) / 2
        if a0 >= b0 and a1 <= b1:
            return (a0 + a1) / 2
        return (max(a0, b0) + min(a1, b1)) / 2

    def _straight_candidate(self, ft, tt):
        """Geometric candidate for a 1-segment straight link, or None.

        Returns (from_side, to_side, coord). Only checks feasibility — whether
        the candidate is clean enough to keep is R3.1's job.
        """
        fp, tp = ft.scenePos(), tt.scenePos()
        fx0, fx1 = fp.x(), fp.x() + ft.width
        fy0, fy1 = fp.y(), fp.y() + ft.height
        tx0, tx1 = tp.x(), tp.x() + tt.width
        ty0, ty1 = tp.y(), tp.y() + tt.height

        # Horizontal link needs a vertical overlap
        if min(fy1, ty1) - max(fy0, ty0) >= self.STRAIGHT_MIN_OVERLAP:
            coord = self._shared_coord(fy0, fy1, ty0, ty1)
            if (tx0 + tx1) / 2 > (fx0 + fx1) / 2:
                return 'right', 'left', coord
            return 'left', 'right', coord

        # Vertical link needs a horizontal overlap
        if min(fx1, tx1) - max(fx0, tx0) >= self.STRAIGHT_MIN_OVERLAP:
            coord = self._shared_coord(fx0, fx1, tx0, tx1)
            if (ty0 + ty1) / 2 > (fy0 + fy1) / 2:
                return 'bottom', 'top', coord
            return 'top', 'bottom', coord

        return None

    @staticmethod
    def _l_sides(ft, tt, horizontal_first):
        """R3.2/R3.3 — the two sides of an L path between diagonal tables.

        A diagonal pair admits exactly two orthogonal L paths. Either way the
        target is entered on the side facing the source (R3.3).
        """
        fcx = ft.scenePos().x() + ft.width / 2
        fcy = ft.scenePos().y() + ft.height / 2
        tcx = tt.scenePos().x() + tt.width / 2
        tcy = tt.scenePos().y() + tt.height / 2
        if horizontal_first:
            # leave sideways, arrive on the target's top or bottom
            return ('right' if tcx > fcx else 'left',
                    'top' if tcy > fcy else 'bottom')
        # leave vertically, arrive on the target's left or right
        return ('bottom' if tcy > fcy else 'top',
                'left' if tcx > fcx else 'right')

    def _distribution_ok(self, coord, table, side, n_anchors):
        """R3.1 — is `coord` far enough from both ends of the edge?

        Compares the smallest margin to the homogeneous step L/(n+1). Below
        HOMOGENEITY_MIN the anchor is jammed into a corner and the straight
        link is not worth its cost.
        """
        start, end = self._span(table, side)
        step = (end - start) / (n_anchors + 1)
        if step <= 0:
            return False
        return min(coord - start, end - coord) / step >= self.HOMOGENEITY_MIN

    # ------------------------------------------------------------------
    # R1 / R2 / R3 — side assignment
    # ------------------------------------------------------------------

    def _assign_sides(self, auto_lines):
        """Choose the form and the two sides of every auto line.

        Straight candidates are accepted optimistically, then demoted to an L
        when they would push an anchor into a corner (R3.1). That test needs
        the per-edge anchor count, which itself depends on the chosen sides, so
        the assignment is iterated until it stabilises.

        Returns (line_sides, pin_coord):
          line_sides[id(line)] = (from_side, to_side)
          pin_coord[id(line)]  = imposed coordinate, for straight links only
        """
        from collections import defaultdict

        # Pairs carrying many composite FKs keep the legacy spread across two
        # sides of the target — see _assign_sides_multi_fk.
        pair_lines = defaultdict(list)
        for ln in auto_lines:
            pair_lines[(id(ln.from_table), id(ln.to_table))].append(ln)
        multi_fk_sides = {}
        simple_lines = []
        for lines in pair_lines.values():
            if len(lines) >= 5:
                multi_fk_sides.update(self._assign_sides_multi_fk(lines))
            else:
                simple_lines.extend(lines)

        # Interim R3.2 criterion: a busy source spreads its links sideways
        out_degree = defaultdict(int)
        for ln in auto_lines:
            out_degree[id(ln.from_table)] += 1

        candidate = {id(ln): self._straight_candidate(ln.from_table, ln.to_table)
                     for ln in simple_lines}
        keep_straight = {id(ln): candidate[id(ln)] is not None for ln in simple_lines}

        def build():
            sides, pins = dict(multi_fk_sides), {}
            for ln in simple_lines:
                if keep_straight[id(ln)]:
                    fs, ts, coord = candidate[id(ln)]
                    pins[id(ln)] = coord
                else:
                    horizontal_first = (out_degree[id(ln.from_table)]
                                        >= self.LATERAL_SPREAD_MIN)
                    fs, ts = self._l_sides(ln.from_table, ln.to_table,
                                           horizontal_first)
                sides[id(ln)] = (fs, ts)
                ln._from_side, ln._to_side = fs, ts
            return sides, pins

        def demote(sides, pins):
            """Drop straight links whose anchor would land in a corner."""
            counts = defaultdict(int)
            for ln in auto_lines:
                fs, ts = sides[id(ln)]
                counts[(id(ln.from_table), fs)] += 1
                counts[(id(ln.to_table), ts)] += 1
            changed = False
            for ln in simple_lines:
                if not keep_straight[id(ln)]:
                    continue
                fs, ts = sides[id(ln)]
                coord = pins[id(ln)]
                if not (self._distribution_ok(coord, ln.from_table, fs,
                                              counts[(id(ln.from_table), fs)])
                        and self._distribution_ok(coord, ln.to_table, ts,
                                                  counts[(id(ln.to_table), ts)])):
                    keep_straight[id(ln)] = False
                    changed = True
            return changed

        for _ in range(4):
            line_sides, pin_coord = build()
            if not demote(line_sides, pin_coord):
                break
        else:
            line_sides, pin_coord = build()

        return line_sides, pin_coord

    def _assign_sides_multi_fk(self, lines):
        """Legacy spread for a pair linked by 5+ separate FK lines.

        Splits the anchors between the target's facing side and an adjacent
        perpendicular side, so a dense bundle does not pile up on one edge.
        Kept unchanged: it only triggers with group_fks disabled.
        """
        import math

        base_from, base_to = lines[0]._auto_sides()
        ft = lines[0].from_table
        tt = lines[0].to_table

        base_horiz = base_to in ('left', 'right')
        ft_cy = ft.scenePos().y() + ft.height / 2
        ft_cx = ft.scenePos().x() + ft.width / 2
        tt_cy = tt.scenePos().y() + tt.height / 2
        tt_cx = tt.scenePos().x() + tt.width / 2

        if base_horiz:
            perp = 'top' if ft_cy < tt_cy else 'bottom'
        else:
            perp = 'left' if ft_cx < tt_cx else 'right'

        base_len = tt.width if base_to in ('top', 'bottom') else tt.height
        perp_len = tt.width if perp in ('top', 'bottom') else tt.height
        perp_ratio = (perp_len / (base_len + perp_len)
                      if (base_len + perp_len) > 0 else 0.5)
        n_perp = max(1, min(len(lines) - 1, math.ceil(len(lines) * perp_ratio)))
        n_base = len(lines) - n_perp

        fs_axis_vert = base_from in ('left', 'right')
        ft_columns = [c.get('name') for c in getattr(ft, 'columns', [])]

        def col_index(ln):
            try:
                return ft_columns.index(ln.from_column)
            except (ValueError, AttributeError):
                return 999

        def target_pos_outer(ln):
            t = ln.to_table
            if fs_axis_vert:
                return t.scenePos().y() + t.height / 2
            return t.scenePos().x() + t.width / 2

        lines_sorted = sorted(
            lines, key=lambda ln: (target_pos_outer(ln), col_index(ln),
                                   ln.fk_name or ''))

        if fs_axis_vert:
            perp_at_end = ft.scenePos().y() < tt.scenePos().y()
        else:
            perp_at_end = ft.scenePos().x() < tt.scenePos().x()

        if perp_at_end:
            base_lines = lines_sorted[:n_base]
            perp_lines = lines_sorted[n_base:]
        else:
            perp_lines = lines_sorted[:len(lines_sorted) - n_base]
            base_lines = lines_sorted[len(lines_sorted) - n_base:]

        sides = {}
        for ln in base_lines:
            ln._from_side, ln._to_side = base_from, base_to
            sides[id(ln)] = (base_from, base_to)
        for ln in perp_lines:
            ln._from_side, ln._to_side = base_from, perp
            sides[id(ln)] = (base_from, perp)
        return sides

    # ------------------------------------------------------------------
    # R2 / R4 / R5 — anchor placement
    # ------------------------------------------------------------------

    def _place_anchors(self, auto_lines, line_sides, pin_coord):
        """Place both endpoints of every auto line on their table edges.

        Parallel-sided links (straight / Z) keep the master-slave scheme: the
        busier edge lays its anchors out and the other end matches that
        coordinate. Perpendicular links (L) have their anchors on two different
        axes, so each end is laid out independently on its own edge.
        """
        from collections import defaultdict

        id_to_table = {id(t): t for t in self._table_items.values()}

        parallel = {}
        for ln in auto_lines:
            fs, ts = line_sides[id(ln)]
            parallel[id(ln)] = (fs in ('left', 'right')) == (ts in ('left', 'right'))

        counts = defaultdict(int)
        for ln in auto_lines:
            fs, ts = line_sides[id(ln)]
            counts[(id(ln.from_table), fs)] += 1
            counts[(id(ln.to_table), ts)] += 1

        master_is_from = {}
        for ln in auto_lines:
            if not parallel[id(ln)]:
                continue
            fs, ts = line_sides[id(ln)]
            master_is_from[id(ln)] = (counts[(id(ln.from_table), fs)]
                                      >= counts[(id(ln.to_table), ts)])

        # One entry per anchor that the distribution rule has to place
        edge_entries = defaultdict(list)  # (table_id, side) -> [(line, is_from)]
        for ln in auto_lines:
            fs, ts = line_sides[id(ln)]
            if parallel[id(ln)]:
                if master_is_from[id(ln)]:
                    edge_entries[(id(ln.from_table), fs)].append((ln, True))
                else:
                    edge_entries[(id(ln.to_table), ts)].append((ln, False))
            else:
                edge_entries[(id(ln.from_table), fs)].append((ln, True))
                edge_entries[(id(ln.to_table), ts)].append((ln, False))

        for (tid, side), entries in edge_entries.items():
            table = id_to_table.get(tid)
            if table is not None:
                self._layout_edge(table, side, entries, pin_coord)

        self._place_slaves(auto_lines, line_sides, parallel, master_is_from)

    def _layout_edge(self, table, side, entries, pin_coord):
        """R2 + R4 + R5 — place all the anchors carried by one edge.

        Constrained anchors (straight links, R2) go to their imposed coordinate
        and split the edge into sub-segments; the remaining anchors spread
        homogeneously inside each sub-segment (R4). The ordering along the edge
        follows the direction of the far end, so links sharing an edge do not
        cross (R5).
        """
        from math import atan2
        from PySide6.QtCore import QPointF as _QPointF

        pos = table.scenePos()
        w, h = table.width, table.height
        start, end = self._span(table, side)
        cx, cy = pos.x() + w / 2, pos.y() + h / 2

        def other_end(entry):
            ln, is_from = entry
            return ln.to_table if is_from else ln.from_table

        def angle(entry):
            ot = other_end(entry)
            return atan2(ot.scenePos().y() + ot.height / 2 - cy,
                         ot.scenePos().x() + ot.width / 2 - cx)

        if side == 'top':
            entries.sort(key=lambda e: (angle(e), e[0].fk_name or ''))
        elif side == 'bottom':
            entries.sort(key=lambda e: (-angle(e), e[0].fk_name or ''))
        else:
            entries.sort(key=lambda e: (other_end(e).scenePos().y()
                                        + other_end(e).height / 2,
                                        e[0].fk_name or ''))

        def set_pos(entry, coord):
            ln, is_from = entry
            vidx = 0 if is_from else -1
            if side == 'left':
                ln._vertices[vidx] = _QPointF(pos.x(), coord)
            elif side == 'right':
                ln._vertices[vidx] = _QPointF(pos.x() + w, coord)
            elif side == 'top':
                ln._vertices[vidx] = _QPointF(coord, pos.y())
            else:
                ln._vertices[vidx] = _QPointF(coord, pos.y() + h)

        CORNER_MARGIN = 10
        pinned = {}
        for e in entries:
            c = pin_coord.get(id(e[0]))
            if c is not None and (start + CORNER_MARGIN) < c < (end - CORNER_MARGIN):
                pinned[id(e[0])] = c

        # Sub-segments delimited by the constrained anchors
        segments, seg_start, current = [], start, []
        for e in entries:
            if id(e[0]) in pinned:
                segments.append((seg_start, pinned[id(e[0])], current))
                current, seg_start = [], pinned[id(e[0])]
            else:
                current.append(e)
        segments.append((seg_start, end, current))

        for e in entries:
            if id(e[0]) in pinned:
                set_pos(e, pinned[id(e[0])])

        for s_start, s_end, s_entries in segments:
            m = len(s_entries)
            if m == 0:
                continue
            step = (s_end - s_start) / (m + 1)
            for i, e in enumerate(s_entries):
                set_pos(e, s_start + step * (i + 1))

    def _place_slaves(self, auto_lines, line_sides, parallel, master_is_from):
        """Parallel links only — the non-master end matches its master's
        coordinate, clamped inside its own edge so it never lands on a corner."""
        from PySide6.QtCore import QPointF as _QPointF

        SLAVE_CORNER_MARGIN = 5
        for ln in auto_lines:
            if not parallel[id(ln)]:
                continue
            fs, ts = line_sides[id(ln)]
            if master_is_from[id(ln)]:
                master = ln._vertices[0]
                table, side, vidx = ln.to_table, ts, -1
            else:
                master = ln._vertices[-1]
                table, side, vidx = ln.from_table, fs, 0

            p = table.scenePos()
            w, h = table.width, table.height
            if side in ('top', 'bottom'):
                x = max(p.x() + SLAVE_CORNER_MARGIN,
                        min(p.x() + w - SLAVE_CORNER_MARGIN, master.x()))
                y = p.y() if side == 'top' else p.y() + h
            else:
                y = max(p.y() + SLAVE_CORNER_MARGIN,
                        min(p.y() + h - SLAVE_CORNER_MARGIN, master.y()))
                x = p.x() if side == 'left' else p.x() + w
            ln._vertices[vidx] = _QPointF(x, y)

    # ------------------------------------------------------------------
    # Path regeneration
    # ------------------------------------------------------------------

    def _rebuild_all(self, auto_lines, line_sides):
        """Regenerate intermediate vertices and repaint every auto line.

        Z-paths sharing the same pair and sides get their middle segment
        staggered so they do not overlap.
        """
        from collections import defaultdict

        zpath_groups = defaultdict(list)
        for ln in auto_lines:
            fs, ts = line_sides[id(ln)]
            if (fs in ('left', 'right')) == (ts in ('left', 'right')):
                zpath_groups[(id(ln.from_table), id(ln.to_table), fs, ts)].append(ln)

        mid_ratio = {}
        for group in zpath_groups.values():
            n = len(group)
            fs = line_sides[id(group[0])][0]
            if fs in ('left', 'right'):
                group.sort(key=lambda ln: ln._vertices[0].y())
            else:
                group.sort(key=lambda ln: ln._vertices[0].x())

            if n == 1:
                mid_ratio[id(group[0])] = 0.5
                continue

            ft, tt = group[0].from_table, group[0].to_table
            if fs in ('left', 'right'):
                source_before = ((ft.scenePos().y() + ft.height / 2)
                                 < (tt.scenePos().y() + tt.height / 2))
            else:
                source_before = ((ft.scenePos().x() + ft.width / 2)
                                 < (tt.scenePos().x() + tt.width / 2))

            for i, ln in enumerate(group):
                # 0.2 → mid segment near the source, 0.8 → near the target
                mid_ratio[id(ln)] = (0.8 - i * 0.6 / (n - 1)) if source_before \
                    else (0.2 + i * 0.6 / (n - 1))

        for ln in auto_lines:
            if len(ln._vertices) == 2:
                a, b = ln._vertices[0], ln._vertices[1]
                if abs(a.x() - b.x()) < 1 or abs(a.y() - b.y()) < 1:
                    ln._rebuild_path()
                    continue
            ln.rebuild_intermediates(mid_ratio=mid_ratio.get(id(ln), 0.5))
            ln._rebuild_path()


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
        """Safety reset — ensure all tables are movable (fixes stuck state after drag bug).

        Does nothing on a read-only scene: the view calls this on every mouse
        press, which would otherwise undo set_read_only() on the first click.
        """
        if self._read_only:
            return
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

    def set_read_only(self, read_only: bool):
        """Freeze every item so the diagram can be shown outside the editor
        without pretending to be editable. Hover popups keep working."""
        self._read_only = read_only
        for item in self._table_items.values():
            item.set_read_only(read_only)
        for line in self._relationship_lines:
            line.set_read_only(read_only)
        for group in self._group_items.values():
            group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not read_only)
            group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, not read_only)

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
