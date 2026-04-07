"""
ER Diagram Manager - Main widget for viewing and managing ER diagrams.

Layout:
- Left: List of saved diagrams
- Right: QGraphicsView displaying the active diagram
"""

from typing import Optional, Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGraphicsView,
    QListWidget, QListWidgetItem, QPushButton, QFileDialog, QLabel,
    QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QWheelEvent

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db
from ...database.models import ERDiagram, ERDiagramTable
from ...database.schema_loaders import SchemaLoaderFactory, ForeignKeyInfo, PrimaryKeyInfo

from .er_diagram.scene import ERDiagramScene
from .er_diagram.dialogs import NewDiagramDialog, TablePickerDialog
from .er_diagram.export import export_to_png, export_to_svg

import logging
logger = logging.getLogger(__name__)


class ZoomableGraphicsView(QGraphicsView):
    """QGraphicsView with mouse wheel zoom."""

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1 / factor, 1 / factor)


class ERDiagramManager(QWidget):
    """
    Main ER Diagram manager widget.

    Layout: toolbar + splitter (diagram list | diagram view)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._database_manager = None
        self._current_diagram: Optional[ERDiagram] = None
        self._scene: Optional[ERDiagramScene] = None
        self._is_dark = True

        self._setup_ui()
        self._load_diagram_list()

    def set_database_manager(self, db_manager):
        """Set reference to DatabaseManager for connections and schema loading."""
        self._database_manager = db_manager

    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button("New Diagram", self._new_diagram, icon="add")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Add Tables", self._add_tables, icon="table")
        toolbar_builder.add_button("Save Positions", self._save_positions, icon="star")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Export PNG", self._export_png, icon="download")
        toolbar_builder.add_button("Export SVG", self._export_svg, icon="download")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Delete", self._delete_diagram, icon="delete")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: diagram list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_layout.addWidget(QLabel("Diagrams"))

        # Connection filter
        self._conn_combo = QComboBox()
        self._conn_combo.addItem("All connections", "")
        self._conn_combo.currentIndexChanged.connect(self._on_connection_filter_changed)
        left_layout.addWidget(self._conn_combo)

        self._diagram_list = QListWidget()
        self._diagram_list.currentItemChanged.connect(self._on_diagram_selected)
        left_layout.addWidget(self._diagram_list)

        self.splitter.addWidget(left_panel)

        # Right: graphics view
        self._view = ZoomableGraphicsView()
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setRenderHint(self._view.renderHints())
        self.splitter.addWidget(self._view)

        self.splitter.setSizes([250, 750])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        layout.addWidget(self.splitter)

    def _load_diagram_list(self):
        """Load saved diagrams into the list."""
        self._diagram_list.clear()
        config_db = get_config_db()

        # Load connection filter
        self._conn_combo.blockSignals(True)
        self._conn_combo.clear()
        self._conn_combo.addItem("All connections", "")
        for conn in config_db.get_all_database_connections():
            self._conn_combo.addItem(conn.name, conn.id)
        self._conn_combo.blockSignals(False)

        # Load diagrams
        conn_filter = self._conn_combo.currentData()
        if conn_filter:
            diagrams = config_db.get_er_diagrams_by_connection(conn_filter)
        else:
            diagrams = config_db.get_all_er_diagrams()

        for diagram in diagrams:
            item = QListWidgetItem(f"{diagram.name} ({len(diagram.tables)} tables)")
            item.setData(Qt.ItemDataRole.UserRole, diagram.id)
            item.setToolTip(diagram.description or diagram.name)
            self._diagram_list.addItem(item)

    def _on_connection_filter_changed(self, index: int):
        """Filter diagrams by connection."""
        self._load_diagram_list()

    def _on_diagram_selected(self, current, previous):
        """Load the selected diagram."""
        if not current:
            return
        diagram_id = current.data(Qt.ItemDataRole.UserRole)
        if diagram_id:
            self._load_diagram(diagram_id)

    def _load_diagram(self, diagram_id: str):
        """Load a diagram and display it."""
        config_db = get_config_db()
        diagram = config_db.get_er_diagram(diagram_id)
        if not diagram:
            return

        self._current_diagram = diagram

        # Get connection and schema loader
        if not self._database_manager:
            DialogHelper.warning("Database Manager not available.", parent=self)
            return

        connection = self._database_manager.connections.get(diagram.connection_id)
        if not connection:
            DialogHelper.warning(
                f"Connection not active. Connect to the database first.",
                parent=self
            )
            return

        db_conn = config_db.get_database_connection(diagram.connection_id)
        if not db_conn:
            return

        # Create schema loader
        try:
            loader = SchemaLoaderFactory.create_loader(
                connection, db_conn.id, diagram.database_name or db_conn.name, db_conn.db_type
            )
        except (ValueError, KeyError) as e:
            DialogHelper.error(f"Cannot create schema loader: {e}", parent=self)
            return

        # Load metadata
        table_names = diagram.get_table_names()
        foreign_keys = loader.load_foreign_keys(table_names, diagram.database_name)
        primary_keys = loader.load_primary_keys(table_names, diagram.database_name)

        # Build PK/FK lookup
        pk_by_table: Dict[str, List[str]] = {}
        for pk in primary_keys:
            pk_by_table.setdefault(pk.table_name, []).append(pk.column_name)

        fk_columns_by_table: Dict[str, List[str]] = {}
        for fk in foreign_keys:
            fk_columns_by_table.setdefault(fk.from_table, []).append(fk.from_column)

        # Create scene
        self._scene = ERDiagramScene(is_dark=self._is_dark)
        self._scene.table_moved.connect(self._on_table_moved)

        # Add tables
        has_positions = any(t.pos_x != 0 or t.pos_y != 0 for t in diagram.tables)

        for dt in diagram.tables:
            # Load columns for this table
            try:
                col_nodes = loader.load_columns(dt.table_name)
                columns = [{'name': c.name, 'type': c.metadata.get('type', '')} for c in col_nodes]
            except Exception:
                columns = [{'name': '(error loading columns)', 'type': ''}]

            self._scene.add_table(
                table_name=dt.table_name,
                columns=columns,
                pk_columns=pk_by_table.get(dt.table_name, []),
                fk_columns=fk_columns_by_table.get(dt.table_name, []),
                schema_name=dt.schema_name,
                pos_x=dt.pos_x, pos_y=dt.pos_y
            )

        # Add FK relationships
        self._scene.add_relationships(foreign_keys)

        # Auto-layout if no saved positions
        if not has_positions:
            self._scene.auto_layout()

        self._view.setScene(self._scene)
        self._view.fitInView(self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50),
                            Qt.AspectRatioMode.KeepAspectRatio)

    def _on_table_moved(self, table_name: str, x: float, y: float):
        """Track table position changes (for save)."""
        if self._current_diagram:
            self._current_diagram.update_table_position(table_name, x, y)

    def _new_diagram(self):
        """Create a new ER diagram."""
        if not self._database_manager:
            DialogHelper.warning("Database Manager not available.", parent=self)
            return

        # Get available tables from active connections
        config_db = get_config_db()
        available_tables = []
        active_conn_id = None

        # Use first active connection
        for conn_id, conn in self._database_manager.connections.items():
            db_conn = config_db.get_database_connection(conn_id)
            if db_conn:
                active_conn_id = conn_id
                try:
                    loader = SchemaLoaderFactory.create_loader(
                        conn, db_conn.id, db_conn.name, db_conn.db_type
                    )
                    tables = loader.load_tables()
                    available_tables = [t.metadata.get('table', t.name) for t in tables]
                except Exception as e:
                    logger.error(f"Error loading tables: {e}")
                break

        if not available_tables:
            DialogHelper.warning("No active connection with tables found.", parent=self)
            return

        dialog = NewDiagramDialog(available_tables, parent=self)
        if dialog.exec() != NewDiagramDialog.DialogCode.Accepted:
            return

        # Create diagram
        diagram = ERDiagram(
            name=dialog.diagram_name,
            connection_id=active_conn_id,
            description=dialog.description,
        )
        for table in dialog.selected_tables:
            diagram.add_table(table)

        # Save
        config_db.save_er_diagram(diagram)

        # Reload list and select
        self._load_diagram_list()
        self._load_diagram(diagram.id)

    def _add_tables(self):
        """Add tables to the current diagram."""
        if not self._current_diagram or not self._database_manager:
            return

        config_db = get_config_db()
        conn = self._database_manager.connections.get(self._current_diagram.connection_id)
        db_conn = config_db.get_database_connection(self._current_diagram.connection_id)
        if not conn or not db_conn:
            return

        try:
            loader = SchemaLoaderFactory.create_loader(
                conn, db_conn.id, db_conn.name, db_conn.db_type
            )
            tables = loader.load_tables()
            available = [t.metadata.get('table', t.name) for t in tables]
        except Exception:
            return

        already = self._current_diagram.get_table_names()
        dialog = TablePickerDialog(available, already, parent=self)
        if dialog.exec() != TablePickerDialog.DialogCode.Accepted:
            return

        for table in dialog.selected_tables:
            self._current_diagram.add_table(table)

        config_db.save_er_diagram(self._current_diagram)
        self._load_diagram(self._current_diagram.id)

    def _save_positions(self):
        """Save current table positions."""
        if not self._current_diagram or not self._scene:
            return

        positions = self._scene.get_table_positions()
        for table_name, (x, y) in positions.items():
            self._current_diagram.update_table_position(table_name, x, y)

        config_db = get_config_db()
        config_db.save_er_diagram(self._current_diagram)
        DialogHelper.info("Positions saved.", parent=self)

    def _export_png(self):
        """Export diagram to PNG."""
        if not self._scene:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "", "PNG Files (*.png)")
        if path:
            if export_to_png(self._scene, path):
                DialogHelper.info(f"Exported to {path}", parent=self)

    def _export_svg(self):
        """Export diagram to SVG."""
        if not self._scene:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export SVG", "", "SVG Files (*.svg)")
        if path:
            if export_to_svg(self._scene, path):
                DialogHelper.info(f"Exported to {path}", parent=self)

    def _delete_diagram(self):
        """Delete the current diagram."""
        if not self._current_diagram:
            return
        if not DialogHelper.confirm(f"Delete diagram '{self._current_diagram.name}'?"):
            return

        config_db = get_config_db()
        config_db.delete_er_diagram(self._current_diagram.id)
        self._current_diagram = None
        self._scene = None
        self._view.setScene(None)
        self._load_diagram_list()

    def refresh(self):
        """Refresh the diagram list."""
        self._load_diagram_list()
