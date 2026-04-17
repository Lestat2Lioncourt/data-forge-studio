"""
ER Diagram Scene - QGraphicsScene orchestrating tables and relationships.
"""

from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, QObject

from .table_item import ERTableItem
from .relationship_line import ERRelationshipLine
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

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark

        # Track items
        self._table_items: Dict[str, ERTableItem] = {}  # table_name -> ERTableItem
        self._relationship_lines: List[ERRelationshipLine] = []

        # Background
        from ...core.theme_bridge import ThemeBridge
        palette = ThemeBridge.get_instance().get_er_diagram_colors()
        self.setBackgroundBrush(QColor(palette["scene_bg"]))

    def add_table(self, table_name: str, columns: List[Dict],
                  pk_columns: List[str], fk_columns: List[str],
                  schema_name: str = "",
                  pos_x: float = 0.0, pos_y: float = 0.0) -> ERTableItem:
        """Add a table to the diagram."""
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
        item.signals.position_changed.connect(self.table_moved.emit)

        self.addItem(item)
        self._table_items[table_name] = item
        return item

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
        """Add FK relationship lines, grouping composite FKs into one line per FK name."""
        # Group by (fk_name, from_table, to_table) to merge composite FKs
        from collections import OrderedDict
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
        """Spread FK lines connecting the same table/side to avoid overlap."""
        from collections import defaultdict
        SPREAD = 12  # pixels between adjacent FK lines

        # Group lines by (table, side) — each line appears twice (from + to)
        table_side_lines: dict = defaultdict(list)
        for line in self._relationship_lines:
            from_side, to_side = line._auto_sides()
            table_side_lines[(id(line.from_table), from_side)].append(('from', line))
            table_side_lines[(id(line.to_table), to_side)].append(('to', line))

        # Assign offsets within each group
        for (_table_id, _side), entries in table_side_lines.items():
            n = len(entries)
            for i, (role, line) in enumerate(entries):
                offset = (i - (n - 1) / 2) * SPREAD
                if role == 'from':
                    line._from_offset = offset
                else:
                    line._to_offset = offset

        # Refresh all paths with new offsets
        for line in self._relationship_lines:
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
        positions = {}
        for name, item in self._table_items.items():
            pos = item.scenePos()
            positions[name] = (pos.x(), pos.y())
        return positions

    def get_table_item(self, table_name: str) -> Optional[ERTableItem]:
        """Get a table item by name."""
        return self._table_items.get(table_name)

    def unfreeze_all_tables(self):
        """Safety reset — ensure all tables are movable (fixes stuck state after drag bug)."""
        for item in self._table_items.values():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def get_fk_midpoints(self) -> list:
        """Get waypoints for all FK lines that have been manually adjusted.

        Returns:
            List of dicts with from_table, from_column, to_table, to_column, mid_x, mid_y.
            For backward compat, saves the middle waypoint (best representative).
        """
        midpoints = []
        for line in self._relationship_lines:
            wps = line.get_waypoints()
            if wps:
                # Save middle waypoint as representative
                mid_wp = wps[len(wps) // 2]
                midpoints.append({
                    'from_table': line.from_table.table_name,
                    'from_column': line.from_column,
                    'to_table': line.to_table.table_name,
                    'to_column': line.to_column,
                    'mid_x': mid_wp.x(),
                    'mid_y': mid_wp.y(),
                })
        return midpoints

    def set_fk_midpoint(self, from_table: str, from_column: str,
                        to_table: str, to_column: str,
                        mid_x: float, mid_y: float):
        """Restore a waypoint for a FK line (backward compat — single midpoint)."""
        for line in self._relationship_lines:
            if (line.from_table.table_name == from_table and
                line.from_column == from_column and
                line.to_table.table_name == to_table and
                line.to_column == to_column):
                # Insert the saved midpoint as a waypoint
                from PySide6.QtCore import QPointF
                line.set_waypoints([QPointF(mid_x, mid_y)])
                return

    def set_show_fk_names(self, show: bool):
        """Show or hide FK names on all relationship lines."""
        for line in self._relationship_lines:
            line.set_show_label(show)

    def set_show_column_types(self, show: bool):
        """Show or hide column types in all tables."""
        for item in self._table_items.values():
            item.set_show_types(show)

    def clear_all(self):
        """Remove all items from the scene."""
        self._table_items.clear()
        self._relationship_lines.clear()
        self.clear()
