"""
ER Diagram Repository - CRUD operations for ER diagrams and their tables.
"""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import ERDiagram, ERDiagramTable, ERDiagramFKMidpoint

import logging
logger = logging.getLogger(__name__)


class ERDiagramRepository(BaseRepository[ERDiagram]):
    """Repository for ERDiagram entities with nested table positions."""

    @property
    def table_name(self) -> str:
        return "er_diagrams"

    def _row_to_model(self, row: sqlite3.Row) -> ERDiagram:
        data = dict(row)
        # Tables and midpoints are loaded separately
        data['tables'] = []
        data['fk_midpoints'] = []
        data['show_column_types'] = bool(data.get('show_column_types', 1))
        return ERDiagram(**data)

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO er_diagrams
            (id, name, connection_id, database_name, description, zoom_level, show_column_types, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE er_diagrams
            SET name = ?, connection_id = ?, database_name = ?,
                description = ?, zoom_level = ?, show_column_types = ?, updated_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: ERDiagram) -> tuple:
        return (model.id, model.name, model.connection_id, model.database_name,
                model.description, model.zoom_level, int(model.show_column_types),
                model.created_at, model.updated_at)

    def _model_to_update_tuple(self, model: ERDiagram) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.connection_id, model.database_name,
                model.description, model.zoom_level, int(model.show_column_types),
                model.updated_at, model.id)

    def _load_tables(self, diagram_id: str) -> List[ERDiagramTable]:
        """Load tables for a diagram."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT table_name, schema_name, pos_x, pos_y "
                "FROM er_diagram_tables WHERE diagram_id = ? ORDER BY table_name",
                (diagram_id,)
            )
            return [
                ERDiagramTable(
                    table_name=row['table_name'],
                    schema_name=row['schema_name'],
                    pos_x=row['pos_x'],
                    pos_y=row['pos_y']
                )
                for row in cursor.fetchall()
            ]

    def _save_tables(self, diagram_id: str, tables: List[ERDiagramTable]):
        """Save tables for a diagram (replace all)."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM er_diagram_tables WHERE diagram_id = ?", (diagram_id,))
            now = datetime.now().isoformat()
            for t in tables:
                cursor.execute(
                    "INSERT INTO er_diagram_tables "
                    "(diagram_id, table_name, schema_name, pos_x, pos_y, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (diagram_id, t.table_name, t.schema_name, t.pos_x, t.pos_y, now)
                )
            conn.commit()

    def _load_fk_midpoints(self, diagram_id: str) -> List[ERDiagramFKMidpoint]:
        """Load FK midpoints for a diagram."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT from_table, from_column, to_table, to_column, mid_x, mid_y "
                "FROM er_diagram_fk_midpoints WHERE diagram_id = ?",
                (diagram_id,)
            )
            return [
                ERDiagramFKMidpoint(
                    from_table=row[0], from_column=row[1],
                    to_table=row[2], to_column=row[3],
                    mid_x=row[4], mid_y=row[5]
                )
                for row in cursor.fetchall()
            ]

    def _save_fk_midpoints(self, diagram_id: str, midpoints: List[ERDiagramFKMidpoint]):
        """Save FK midpoints for a diagram (replace all)."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM er_diagram_fk_midpoints WHERE diagram_id = ?", (diagram_id,))
            for mp in midpoints:
                cursor.execute(
                    "INSERT INTO er_diagram_fk_midpoints "
                    "(diagram_id, from_table, from_column, to_table, to_column, mid_x, mid_y) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (diagram_id, mp.from_table, mp.from_column,
                     mp.to_table, mp.to_column, mp.mid_x, mp.mid_y)
                )
            conn.commit()

    def _load_full(self, diagram: ERDiagram):
        """Load tables and FK midpoints for a diagram."""
        diagram.tables = self._load_tables(diagram.id)
        diagram.fk_midpoints = self._load_fk_midpoints(diagram.id)

    def get_with_tables(self, diagram_id: str) -> Optional[ERDiagram]:
        """Get a diagram with its tables and FK midpoints loaded."""
        diagram = self.get_by_id(diagram_id)
        if diagram:
            self._load_full(diagram)
        return diagram

    def save(self, diagram: ERDiagram) -> ERDiagram:
        """Save a diagram (insert or update) with its tables and FK midpoints."""
        existing = self.get_by_id(diagram.id)
        if existing:
            self.update(diagram)
        else:
            self.add(diagram)
        self._save_tables(diagram.id, diagram.tables)
        self._save_fk_midpoints(diagram.id, diagram.fk_midpoints)
        return diagram

    def get_by_connection(self, connection_id: str) -> List[ERDiagram]:
        """Get all diagrams for a connection, with tables and midpoints loaded."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM er_diagrams WHERE connection_id = ? ORDER BY name",
                (connection_id,)
            )
            diagrams = [self._row_to_model(row) for row in cursor.fetchall()]
        for d in diagrams:
            self._load_full(d)
        return diagrams

    def get_all_diagrams(self) -> List[ERDiagram]:
        """Get all diagrams with tables and midpoints loaded."""
        diagrams = self.get_all(order_by="name")
        for d in diagrams:
            self._load_full(d)
        return diagrams

    def delete_diagram(self, diagram_id: str):
        """Delete a diagram and its tables (cascade)."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM er_diagram_tables WHERE diagram_id = ?", (diagram_id,))
            cursor.execute("DELETE FROM er_diagrams WHERE id = ?", (diagram_id,))
            conn.commit()

    def update_table_position(self, diagram_id: str, table_name: str,
                               pos_x: float, pos_y: float, schema_name: str = ""):
        """Update position of a single table in a diagram."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE er_diagram_tables SET pos_x = ?, pos_y = ? "
                "WHERE diagram_id = ? AND table_name = ? AND schema_name = ?",
                (pos_x, pos_y, diagram_id, table_name, schema_name)
            )
            # Update diagram updated_at
            cursor.execute(
                "UPDATE er_diagrams SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), diagram_id)
            )
            conn.commit()
