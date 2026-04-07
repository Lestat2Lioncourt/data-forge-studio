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
        self._show_fk_names = False

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
        toolbar_builder.add_button("FK Names", self._toggle_fk_names, icon="view")
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

        # Get connection (auto-connect if needed)
        if not self._database_manager:
            DialogHelper.warning("Database Manager not available.", parent=self)
            return

        db_conn = config_db.get_database_connection(diagram.connection_id)
        if not db_conn:
            DialogHelper.warning("Connection configuration not found.", parent=self)
            return

        connection = self._database_manager.connections.get(diagram.connection_id)
        if not connection:
            connection = self._database_manager.reconnect_database(diagram.connection_id)
        if not connection:
            DialogHelper.warning(
                f"Cannot connect to '{db_conn.name}'.\n"
                "Connect to the database in the Database Manager first.",
                parent=self
            )
            return

        # Create schema loader
        try:
            loader = SchemaLoaderFactory.create(
                db_conn.db_type, connection, db_conn.id, diagram.database_name or db_conn.name
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

        # Restore saved FK midpoints
        for mp in diagram.fk_midpoints:
            self._scene.set_fk_midpoint(
                mp.from_table, mp.from_column,
                mp.to_table, mp.to_column,
                mp.mid_x, mp.mid_y
            )

        # Auto-layout if no saved positions
        if not has_positions:
            self._scene.auto_layout()

        self._view.setScene(self._scene)

        # Restore zoom level or fit to view
        if diagram.zoom_level and diagram.zoom_level != 1.0 and has_positions:
            self._view.resetTransform()
            self._view.scale(diagram.zoom_level, diagram.zoom_level)
        else:
            self._view.fitInView(self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50),
                                Qt.AspectRatioMode.KeepAspectRatio)

    def _on_table_moved(self, table_name: str, x: float, y: float):
        """Track table position changes (for save)."""
        if self._current_diagram:
            self._current_diagram.update_table_position(table_name, x, y)

    def _get_active_connection(self):
        """Get the currently selected connection from the combo, auto-connecting if needed.

        Returns (connection, db_conn) or (None, None) if unavailable.
        """
        config_db = get_config_db()
        conn_filter = self._conn_combo.currentData()

        if conn_filter:
            # Specific connection selected
            db_conn = config_db.get_database_connection(conn_filter)
            if not db_conn:
                return None, None
            connection = self._database_manager.connections.get(conn_filter) if self._database_manager else None
            if not connection and self._database_manager:
                # Try to auto-connect
                connection = self._database_manager.reconnect_database(conn_filter)
            return connection, db_conn

        # No filter — use first active, or first configured
        if self._database_manager:
            for conn_id, conn in self._database_manager.connections.items():
                db_conn = config_db.get_database_connection(conn_id)
                if db_conn:
                    return conn, db_conn

        # Try first configured connection
        all_conns = config_db.get_business_database_connections()
        if all_conns and self._database_manager:
            first = all_conns[0]
            connection = self._database_manager.reconnect_database(first.id)
            if connection:
                return connection, first

        return None, None

    def _new_diagram(self):
        """Create a new ER diagram."""
        if not self._database_manager:
            DialogHelper.warning("Database Manager not available.", parent=self)
            return

        connection, db_conn = self._get_active_connection()
        if not connection or not db_conn:
            DialogHelper.warning(
                "No active connection found.\n"
                "Connect to a database in the Database Manager first, "
                "or select a connection in the filter above.",
                parent=self
            )
            return

        config_db = get_config_db()

        # For multi-database servers (SQL Server), ask which database
        loader = SchemaLoaderFactory.create(
            db_conn.db_type, connection, db_conn.id, db_conn.name or ""
        )
        if not loader:
            DialogHelper.error("Cannot create schema loader.", parent=self)
            return

        target_database = ""
        databases = loader.get_databases()
        if databases:
            from PySide6.QtWidgets import QInputDialog
            db_name, ok = QInputDialog.getItem(
                self, "Select Database",
                "Which database?",
                databases, 0, False
            )
            if not ok:
                return
            target_database = db_name

        available_tables = []
        try:
            if target_database:
                tables = loader.load_tables(target_database)
            else:
                tables = loader.load_tables()
            available_tables = [t.metadata.get('table', t.name) for t in tables]
        except Exception as e:
            logger.error(f"Error loading tables: {e}")
            DialogHelper.error(f"Error loading tables: {e}", parent=self)
            return

        if not available_tables:
            DialogHelper.warning("No tables found.", parent=self)
            return

        dialog = NewDiagramDialog(available_tables, parent=self)
        if dialog.exec() != NewDiagramDialog.DialogCode.Accepted:
            return

        # Create diagram
        diagram = ERDiagram(
            name=dialog.diagram_name,
            connection_id=db_conn.id,
            database_name=target_database,
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
            loader = SchemaLoaderFactory.create(
                db_conn.db_type, conn, db_conn.id, db_conn.name
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
        """Save current table positions, FK midpoints, and zoom level."""
        if not self._current_diagram or not self._scene:
            return

        positions = self._scene.get_table_positions()
        for table_name, (x, y) in positions.items():
            self._current_diagram.update_table_position(table_name, x, y)

        # Save FK midpoints
        from ...database.models import ERDiagramFKMidpoint
        midpoints_data = self._scene.get_fk_midpoints()
        self._current_diagram.fk_midpoints = [
            ERDiagramFKMidpoint(**mp) for mp in midpoints_data
        ]

        # Save zoom level
        transform = self._view.transform()
        self._current_diagram.zoom_level = transform.m11()

        config_db = get_config_db()
        config_db.save_er_diagram(self._current_diagram)
        DialogHelper.info("Diagram saved.", parent=self)

    def _toggle_fk_names(self):
        """Toggle FK name labels on/off."""
        if not self._scene:
            return
        self._show_fk_names = not self._show_fk_names
        self._scene.set_show_fk_names(self._show_fk_names)

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
