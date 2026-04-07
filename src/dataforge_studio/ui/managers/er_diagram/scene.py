"""
ER Diagram Scene - QGraphicsScene orchestrating tables and relationships.
"""

from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import QGraphicsScene
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

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark

        # Track items
        self._table_items: Dict[str, ERTableItem] = {}  # table_name -> ERTableItem
        self._relationship_lines: List[ERRelationshipLine] = []

        # Background
        bg = QColor("#1e1e1e") if is_dark else QColor("#f5f5f5")
        self.setBackgroundBrush(bg)

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
        """Add FK relationship lines for the given foreign keys."""
        for fk in foreign_keys:
            from_item = self._table_items.get(fk.from_table)
            to_item = self._table_items.get(fk.to_table)

            if from_item and to_item:
                line = ERRelationshipLine(
                    from_table=from_item,
                    from_column=fk.from_column,
                    to_table=to_item,
                    to_column=fk.to_column,
                    fk_name=fk.fk_name,
                    is_dark=self.is_dark
                )
                self.addItem(line)
                self._relationship_lines.append(line)

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

    def clear_all(self):
        """Remove all items from the scene."""
        self._table_items.clear()
        self._relationship_lines.clear()
        self.clear()
