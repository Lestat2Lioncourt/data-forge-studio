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
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QWheelEvent, QKeyEvent, QAction

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
    """QGraphicsView with mouse wheel zoom and delete support."""

    delete_requested = Signal(list)  # list of table_name strings

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15
            if event.angleDelta().y() > 0:
                self.scale(factor, factor)
            else:
                self.scale(1 / factor, 1 / factor)
            event.accept()
        else:
            # Plain wheel → forward to scene (scrolls table columns or pans view)
            super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            from .er_diagram.table_item import ERTableItem
            names = [
                item.table_name for item in self.scene().selectedItems()
                if isinstance(item, ERTableItem)
            ] if self.scene() else []
            if names:
                self.delete_requested.emit(names)
                event.accept()
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """Pan on empty canvas + unfreeze safety net."""
        if self.scene() and hasattr(self.scene(), 'unfreeze_all_tables'):
            self.scene().unfreeze_all_tables()
        # Start pan if clicking on empty canvas (no item under cursor)
        if event.button() == Qt.MouseButton.LeftButton and not self.itemAt(event.pos()):
            self._panning = True
            self._pan_start = event.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_panning', False):
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_panning', False):
            self._panning = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        from .er_diagram.table_item import ERTableItem
        from .er_diagram.relationship_line import ERRelationshipLine, _DragPoint
        from .er_diagram.group_item import ERGroupItem
        item = self.itemAt(event.pos())

        # Right-click on a visual group → rename / change color / delete
        group_hit = item
        while group_hit and not isinstance(group_hit, (ERGroupItem, ERTableItem,
                                                       ERRelationshipLine, _DragPoint)):
            group_hit = group_hit.parentItem()
        if isinstance(group_hit, ERGroupItem):
            menu = QMenu(self)
            rename_action = QAction(tr("er_rename_group"), self)
            rename_action.triggered.connect(lambda: self._rename_group(group_hit))
            menu.addAction(rename_action)
            color_menu = menu.addMenu(tr("er_change_color"))
            for preset in ERGroupItem.PRESETS:
                act = QAction(preset, self)
                act.triggered.connect(lambda _=False, p=preset, g=group_hit: self._change_group_color(g, p))
                color_menu.addAction(act)
            menu.addSeparator()
            del_action = QAction(tr("er_delete_group"), self)
            del_action.triggered.connect(lambda: self._delete_group(group_hit))
            menu.addAction(del_action)
            menu.exec(event.globalPos())
            event.accept()
            return

        # Right-click on drag point → delete / split segment
        if isinstance(item, _DragPoint):
            line = item._parent_line
            seg_idx = item._seg_index
            n_segs = len(line._vertices) - 1
            menu = QMenu(self)
            split_action = QAction(tr("er_split_segment"), self)
            split_action.triggered.connect(lambda: self._split_segment(line, seg_idx))
            menu.addAction(split_action)
            if n_segs > 1:
                del_action = QAction(tr("er_delete_segment"), self)
                del_action.triggered.connect(lambda: self._delete_segment(line, seg_idx))
                menu.addAction(del_action)
            menu.exec(event.globalPos())
            event.accept()
            return

        # Right-click on FK line → delete segment (find closest segment)
        orig = item
        while item and not isinstance(item, (ERTableItem, ERRelationshipLine)):
            item = item.parentItem()
        if isinstance(item, ERRelationshipLine):
            scene_pos = self.mapToScene(event.pos())
            seg_idx = self._find_closest_segment(item, scene_pos)
            n_segs = len(item._vertices) - 1
            menu = QMenu(self)
            split_action = QAction(tr("er_split_segment"), self)
            split_action.triggered.connect(lambda: self._split_segment(item, seg_idx))
            menu.addAction(split_action)
            if n_segs > 1:
                del_action = QAction(tr("er_delete_segment"), self)
                del_action.triggered.connect(lambda: self._delete_segment(item, seg_idx))
                menu.addAction(del_action)
            if item._user_modified:
                menu.addSeparator()
                reset_action = QAction(tr("er_reset_link"), self)
                reset_action.triggered.connect(lambda: self._reset_link(item))
                menu.addAction(reset_action)
            menu.exec(event.globalPos())
            event.accept()
            return

        if isinstance(orig, ERTableItem) or (item and isinstance(item, ERTableItem)):
            tbl = orig if isinstance(orig, ERTableItem) else item
            # Walk up to find ERTableItem
            while tbl and not isinstance(tbl, ERTableItem):
                tbl = tbl.parentItem()
            if isinstance(tbl, ERTableItem):
                menu = QMenu(self)
                action = QAction(tr("er_remove_table"), self)
                action.triggered.connect(lambda: self.delete_requested.emit([tbl.table_name]))
                menu.addAction(action)
                menu.exec(event.globalPos())
                event.accept()
                return
        super().contextMenuEvent(event)

    def _find_closest_segment(self, line, scene_pos):
        """Find the segment index closest to a scene position."""
        import math
        best_idx, best_dist = 0, float('inf')
        for i in range(len(line._vertices) - 1):
            a, b = line._vertices[i], line._vertices[i + 1]
            mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            dist = math.sqrt((mid.x() - scene_pos.x()) ** 2 + (mid.y() - scene_pos.y()) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    def _split_segment(self, line, seg_idx):
        """Divide a segment.

        - Single segment path: insert an L-corner (no side change).
        - Anchor segment (first/last of a multi-segment path): shift the anchor along
          the same edge and insert a jog (2 new vertices). The anchor SIDE is preserved.
        - Intermediate segment: inserts a midpoint vertex (collinear — user then drags).
        """
        verts = line._vertices
        n_segs = len(verts) - 1
        if seg_idx >= n_segs:
            return

        line._user_modified = True
        is_from_anchor = (seg_idx == 0)
        is_to_anchor = (seg_idx == n_segs - 1)

        if n_segs == 1:
            # Single segment (both from + to anchor): insert one L-corner, no side change
            a, b = verts[0], verts[1]
            from_side, _ = line._get_sides()
            if from_side in ('left', 'right'):
                corner = QPointF(b.x(), a.y())
            else:
                corner = QPointF(a.x(), b.y())
            verts.insert(1, corner)
        elif is_from_anchor:
            self._jog_anchor_segment(line, is_from=True)
        elif is_to_anchor:
            self._jog_anchor_segment(line, is_from=False)
        else:
            # Intermediate: midpoint insertion (collinear)
            a, b = verts[seg_idx], verts[seg_idx + 1]
            mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            verts.insert(seg_idx + 1, mid)

        line._rebuild_path()

    def _jog_anchor_segment(self, line, is_from: bool):
        """Divide an anchor segment while preserving the anchor side.

        Shifts the anchor point along its edge and inserts a jog (two new vertices)
        so the path now takes a small detour: anchor' → perpendicular hop → back to
        the original segment axis → continues to the rest of the path.
        """
        verts = line._vertices
        table = line.from_table if is_from else line.to_table
        anchor_idx = 0 if is_from else len(verts) - 1
        next_idx = 1 if is_from else len(verts) - 2

        anchor_pt = verts[anchor_idx]
        next_pt = verts[next_idx]

        # Detect current anchor side from position on table bounds
        tpos = table.scenePos()
        tw, th = table.width, table.height
        if abs(anchor_pt.x() - tpos.x()) < 2:
            side = 'left'
        elif abs(anchor_pt.x() - (tpos.x() + tw)) < 2:
            side = 'right'
        elif abs(anchor_pt.y() - tpos.y()) < 2:
            side = 'top'
        else:
            side = 'bottom'

        SHIFT = 30  # px: jog amplitude along the edge

        if side in ('top', 'bottom'):
            # Anchor slides along X. Original segment is vertical (same X as next_pt).
            # Shift anchor right if there is room; otherwise shift left.
            edge_left = tpos.x() + 4
            edge_right = tpos.x() + tw - 4
            new_x = anchor_pt.x() + SHIFT
            if new_x > edge_right:
                new_x = anchor_pt.x() - SHIFT
            new_x = max(edge_left, min(edge_right, new_x))
            new_anchor = QPointF(new_x, anchor_pt.y())

            # Jog height: halfway between anchor and next_pt along Y
            mid_y = (anchor_pt.y() + next_pt.y()) / 2
            jog1 = QPointF(new_x, mid_y)          # vertical from anchor to jog level
            jog2 = QPointF(next_pt.x(), mid_y)    # horizontal back to original X
        else:
            # side in ('left', 'right') — anchor slides along Y; original segment horizontal
            edge_top = tpos.y() + 4
            edge_bot = tpos.y() + th - 4
            new_y = anchor_pt.y() + SHIFT
            if new_y > edge_bot:
                new_y = anchor_pt.y() - SHIFT
            new_y = max(edge_top, min(edge_bot, new_y))
            new_anchor = QPointF(anchor_pt.x(), new_y)

            mid_x = (anchor_pt.x() + next_pt.x()) / 2
            jog1 = QPointF(mid_x, new_y)
            jog2 = QPointF(mid_x, next_pt.y())

        if is_from:
            verts[0] = new_anchor
            verts.insert(1, jog2)
            verts.insert(1, jog1)
        else:
            verts[-1] = new_anchor
            verts.insert(-1, jog1)
            verts.insert(-1, jog2)

    def _split_anchor(self, line, is_from: bool):
        """Change the anchor side to perpendicular, creating an L-bend."""
        verts = line._vertices
        table = line.from_table if is_from else line.to_table
        anchor_idx = 0 if is_from else len(verts) - 1
        other_idx = 1 if is_from else len(verts) - 2

        anchor_pt = verts[anchor_idx]
        other_pt = verts[other_idx]

        # Detect current side from anchor point position
        tpos = table.scenePos()
        tw, th = table.width, table.height
        if abs(anchor_pt.x() - tpos.x()) < 2:
            current_side = 'left'
        elif abs(anchor_pt.x() - (tpos.x() + tw)) < 2:
            current_side = 'right'
        elif abs(anchor_pt.y() - tpos.y()) < 2:
            current_side = 'top'
        else:
            current_side = 'bottom'

        # Choose a perpendicular side based on other_pt position relative to table center
        cx, cy = tpos.x() + tw / 2, tpos.y() + th / 2
        if current_side in ('left', 'right'):
            new_side = 'top' if other_pt.y() < cy else 'bottom'
        else:
            new_side = 'left' if other_pt.x() < cx else 'right'

        # Compute new anchor point on the new side
        new_anchor = table.get_connection_point(new_side)

        # Single corner: orthogonal bend between new_anchor and other_pt
        if new_side in ('top', 'bottom'):
            corner = QPointF(new_anchor.x(), other_pt.y())
        else:
            corner = QPointF(other_pt.x(), new_anchor.y())

        if is_from:
            line._from_side = new_side
            verts[0] = new_anchor
            verts.insert(1, corner)
        else:
            line._to_side = new_side
            verts[-1] = new_anchor
            verts.insert(-1, corner)

        # Push corner if the resulting segment overlaps any table edge
        self._offset_corner_from_obstacles(line, is_from)

    def _offset_corner_from_obstacles(self, line, is_from: bool):
        """Push the L-bend corner away if any resulting segment overlaps a table's edge zone."""
        verts = line._vertices
        if len(verts) < 4:
            return
        scene = line.scene()
        if not scene or not hasattr(scene, '_table_items'):
            return

        GAP = 25
        # Corner is inserted right after new_anchor (index 1) or right before (index -2)
        corner_idx = 1 if is_from else len(verts) - 2
        # Segments touching the corner: (corner_idx-1, corner_idx) and (corner_idx, corner_idx+1)
        # Skip the stub (corner_idx-1) because it's expected to exit perpendicular to the anchor.

        for _ in range(4):
            if corner_idx >= len(verts) or corner_idx < 0:
                return
            corner = verts[corner_idx]
            prev_pt = verts[corner_idx - 1] if is_from else verts[corner_idx + 1]
            next_pt = verts[corner_idx + 1] if is_from else verts[corner_idx - 1]

            moved = False
            for t in scene._table_items.values():
                tpos = t.scenePos()
                tw, th = t.width, t.height
                left, right = tpos.x() - GAP, tpos.x() + tw + GAP
                top, bottom = tpos.y() - GAP, tpos.y() + th + GAP

                # Check if the segment corner→next_pt overlaps the padded zone
                # Segment is always horizontal or vertical (orthogonal)
                seg_vertical = abs(corner.x() - next_pt.x()) < 1
                if seg_vertical:
                    seg_x = corner.x()
                    seg_y1 = min(corner.y(), next_pt.y())
                    seg_y2 = max(corner.y(), next_pt.y())
                    # Segment vertical at x=seg_x, from y1 to y2
                    if left <= seg_x <= right and not (seg_y2 < top or seg_y1 > bottom):
                        # Push corner horizontally out of the zone
                        dist_left = abs(seg_x - left)
                        dist_right = abs(right - seg_x)
                        if dist_left < dist_right:
                            corner = QPointF(left - 1, corner.y())
                        else:
                            corner = QPointF(right + 1, corner.y())
                        verts[corner_idx] = corner
                        # Adjust prev to keep orthogonal (prev had same Y, corner new X)
                        verts[corner_idx - 1 if is_from else corner_idx + 1] = QPointF(
                            verts[corner_idx - 1 if is_from else corner_idx + 1].x(),
                            corner.y()
                        ) if False else verts[corner_idx - 1 if is_from else corner_idx + 1]
                        # Actually prev segment is horizontal so its Y is corner's Y (unchanged)
                        # and prev X stays at stub X (anchor perpendicular). Rebuild prev point.
                        moved = True
                        break
                else:
                    seg_y = corner.y()
                    seg_x1 = min(corner.x(), next_pt.x())
                    seg_x2 = max(corner.x(), next_pt.x())
                    if top <= seg_y <= bottom and not (seg_x2 < left or seg_x1 > right):
                        dist_top = abs(seg_y - top)
                        dist_bottom = abs(bottom - seg_y)
                        if dist_top < dist_bottom:
                            corner = QPointF(corner.x(), top - 1)
                        else:
                            corner = QPointF(corner.x(), bottom + 1)
                        verts[corner_idx] = corner
                        moved = True
                        break
            if not moved:
                break

    def _reset_link(self, line):
        """Reset one FK line's routing back to auto-layout (clears waypoints + side overrides)."""
        scene = self.scene()
        if scene is None or not hasattr(scene, 'reset_line_routing'):
            return
        scene.reset_line_routing(line)
        # Also drop any saved midpoints for this line in the current diagram model
        mgr = self._find_manager()
        if mgr is not None and mgr._current_diagram is not None:
            ft = line.from_table.table_name
            tt = line.to_table.table_name
            fc = line.from_column
            tc = line.to_column
            mgr._current_diagram.fk_midpoints = [
                mp for mp in mgr._current_diagram.fk_midpoints
                if not (mp.from_table == ft and mp.to_table == tt
                        and mp.from_column == fc and mp.to_column == tc)
            ]

    def _delete_segment(self, line, seg_idx):
        """Delete a segment by removing the shared vertex, merging adjacent segments."""
        line._user_modified = True
        verts = line._vertices
        n = len(verts)
        if n <= 2:
            return  # Can't delete if only 1 segment

        # Remove the vertex at the END of the segment (seg_idx + 1)
        # unless it's the last vertex (to_pt), then remove seg_idx
        if seg_idx + 1 >= n - 1:
            # Last segment — remove vertex before to_pt
            if seg_idx > 0:
                del verts[seg_idx]
        elif seg_idx == 0:
            # First segment — remove vertex after from_pt
            if len(verts) > 2:
                del verts[1]
        else:
            # Middle segment — remove the shared vertex
            del verts[seg_idx + 1]

        line._rebuild_path()

    def _rename_group(self, group_item):
        """Prompt the user for a new title for the group."""
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, tr("er_rename_group"), tr("er_group_name_prompt"),
            text=group_item.name
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        group_item.name = name
        group_item.update()
        # Persist into model
        mgr = self._find_manager()
        if mgr and mgr._current_diagram:
            for g in mgr._current_diagram.groups:
                if g.id == group_item.group_id:
                    g.name = name
                    return

    def _change_group_color(self, group_item, color_hex: str):
        """Change a group's pastel color."""
        group_item.color = color_hex
        group_item.update()
        mgr = self._find_manager()
        if mgr and mgr._current_diagram:
            for g in mgr._current_diagram.groups:
                if g.id == group_item.group_id:
                    g.color = color_hex
                    return

    def _delete_group(self, group_item):
        """Remove the group from the scene and the diagram model."""
        scene = self.scene()
        if scene is None:
            return
        gid = group_item.group_id
        if hasattr(scene, 'remove_group'):
            scene.remove_group(gid)
        mgr = self._find_manager()
        if mgr and mgr._current_diagram:
            mgr._current_diagram.groups = [
                g for g in mgr._current_diagram.groups if g.id != gid
            ]

    def _find_manager(self):
        """Walk up the parent chain to find the ERDiagramManager."""
        w = self.parent()
        while w is not None and not isinstance(w, ERDiagramManager):
            w = w.parent()
        return w

    def resizeEvent(self, event):
        super().resizeEvent(event)
        scene = self.scene()
        if scene is not None:
            rect = scene.itemsBoundingRect()
            if not rect.isEmpty():
                self.fitInView(rect.adjusted(-50, -50, 50, 50),
                               Qt.AspectRatioMode.KeepAspectRatio)


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
        self._show_column_types = True
        self._group_fks = True

        self._setup_ui()
        self._load_diagram_list()

        from ..core.theme_bridge import ThemeBridge
        ThemeBridge.get_instance().register_observer(self._on_theme_changed)

    def _on_theme_changed(self, theme_colors: dict):
        """Reload current diagram + refresh hover overlay to pick up new palette."""
        self._apply_hover_label_style()
        if self._current_diagram:
            self._load_diagram(self._current_diagram.id)

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
        toolbar_builder.add_button("Save Diagram", self._save_positions, icon="star")
        toolbar_builder.add_button("Fit View", self._fit_view, icon="view")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Export PNG", self._export_png, icon="download")
        toolbar_builder.add_button("Export SVG", self._export_svg, icon="download")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("FK Names", self._toggle_fk_names, icon="view")
        toolbar_builder.add_button("Column Types", self._toggle_column_types, icon="view")
        self._group_fks_btn = toolbar_builder.add_button(
            "Group FKs", self._toggle_group_fks, icon="link_grouped", return_button=True
        )
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Add Group", self._add_group, icon="folder")
        toolbar_builder.add_button("Reset Layout", self._reset_layout, icon="refresh")
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
        self._view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._view.setRenderHint(self._view.renderHints())
        self._view.delete_requested.connect(self._remove_tables_from_diagram)
        self.splitter.addWidget(self._view)

        # Hover popup overlay (centered top of view)
        self._hover_label = QLabel(self._view)
        self._apply_hover_label_style()
        self._hover_label.setTextFormat(Qt.TextFormat.RichText)
        self._hover_label.hide()
        self._view.installEventFilter(self)

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

        # Load metadata — retry once if FK query returns empty (cold connection issue)
        table_names = diagram.get_table_names()
        foreign_keys = loader.load_foreign_keys(table_names, diagram.database_name)
        if not foreign_keys and table_names:
            logger.warning("FK query returned empty — retrying after reconnect")
            connection = self._database_manager.reconnect_database(diagram.connection_id)
            if connection:
                try:
                    loader = SchemaLoaderFactory.create(
                        db_conn.db_type, connection, db_conn.id,
                        diagram.database_name or db_conn.name
                    )
                    foreign_keys = loader.load_foreign_keys(table_names, diagram.database_name)
                except Exception as e:
                    logger.error(f"FK retry failed: {e}")
        logger.info(f"FK loaded: {len(foreign_keys)} entries")
        for fk in foreign_keys:
            logger.info(f"  FK: {fk.fk_name} | {fk.from_table}.{fk.from_column} -> {fk.to_table}.{fk.to_column}")
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
        # Restore group_fks BEFORE add_relationships so grouping applies during line creation
        self._group_fks = diagram.group_fks
        self._scene.set_group_fks(self._group_fks)
        self._update_group_fks_icon()
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
                pos_x=dt.pos_x, pos_y=dt.pos_y,
                width=dt.width, height=dt.height,
            )

        # Add FK relationships
        self._scene.add_relationships(foreign_keys)

        # Restore saved FK waypoints (ordered by seq)
        for mp in diagram.fk_midpoints:
            self._scene.set_fk_midpoint(
                mp.from_table, mp.from_column,
                mp.to_table, mp.to_column,
                mp.mid_x, mp.mid_y, seq=mp.seq
            )

        # Restore saved groups
        for g in diagram.groups:
            self._scene.add_group(g.id, g.name, g.x, g.y, g.width, g.height, g.color)
        self._scene.group_geometry_changed.connect(self._on_group_geometry_changed)

        # Auto-layout if no saved positions
        if not has_positions:
            self._scene.auto_layout()

        self._view.setScene(self._scene)
        self._scene.relation_hovered.connect(self._on_relation_hovered)

        # Restore column types toggle
        self._show_column_types = diagram.show_column_types
        if not self._show_column_types:
            self._scene.set_show_column_types(False)

        # Always fit to view at the end of loading — ignore saved zoom level,
        # so a freshly opened diagram is always fully visible.
        rect = self._scene.itemsBoundingRect()
        if not rect.isEmpty():
            self._view.fitInView(rect.adjusted(-50, -50, 50, 50),
                                 Qt.AspectRatioMode.KeepAspectRatio)

    def _apply_hover_label_style(self):
        from ..core.theme_bridge import ThemeBridge
        p = ThemeBridge.get_instance().get_er_diagram_colors()
        self._hover_label.setStyleSheet(
            f"background-color: {p['popup_bg']}; color: {p['popup_fg']};"
            f" padding: 6px 12px; border-radius: 4px; border: 1px solid {p['popup_border']};"
        )

    def _on_relation_hovered(self, html: str):
        """Show/hide hover popup for FK relationship at top-center of the view."""
        if not html:
            self._hover_label.hide()
            return
        self._hover_label.setText(html)
        self._hover_label.adjustSize()
        self._reposition_hover_label()
        self._hover_label.show()
        self._hover_label.raise_()

    def _reposition_hover_label(self):
        """Place the FK popup top- or bottom-centered depending on where the cursor
        is in the view: if the cursor sits in the upper half, show the popup at the
        bottom (so it doesn't cover the link the user is trying to reach)."""
        from PySide6.QtGui import QCursor
        viewport = self._view.viewport()
        view_w = viewport.width()
        view_h = viewport.height()
        label_w = self._hover_label.width()
        label_h = self._hover_label.height()
        x = max(0, (view_w - label_w) // 2)

        cursor_local = viewport.mapFromGlobal(QCursor.pos())
        show_at_bottom = (0 <= cursor_local.y() <= view_h // 2)
        if show_at_bottom:
            y = max(8, view_h - label_h - 8)
        else:
            y = 8
        self._hover_label.move(x, y)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._view and event.type() == QEvent.Type.Resize and self._hover_label.isVisible():
            self._reposition_hover_label()
        return super().eventFilter(obj, event)

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

        # Reload list and select the new diagram
        self._diagram_list.blockSignals(True)
        self._load_diagram_list()
        for i in range(self._diagram_list.count()):
            item = self._diagram_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == diagram.id:
                self._diagram_list.setCurrentItem(item)
                break
        self._diagram_list.blockSignals(False)
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
                db_conn.db_type, conn, db_conn.id, self._current_diagram.database_name or db_conn.name
            )
            target_database = self._current_diagram.database_name or None
            tables = loader.load_tables(target_database) if target_database else loader.load_tables()
            available = [t.metadata.get('table', t.name) for t in tables]
        except Exception as e:
            logger.error(f"Failed to load tables for Add Tables dialog: {e}")
            DialogHelper.error(f"Cannot load tables: {e}", parent=self)
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

        # Save table sizes (resize handles)
        sizes = self._scene.get_table_sizes()
        for table_name, (w, h) in sizes.items():
            self._current_diagram.update_table_size(table_name, w, h)

        # Save FK midpoints
        from ...database.models import ERDiagramFKMidpoint, ERDiagramGroup
        midpoints_data = self._scene.get_fk_midpoints()
        self._current_diagram.fk_midpoints = [
            ERDiagramFKMidpoint(**mp) for mp in midpoints_data
        ]

        # Save groups
        self._current_diagram.groups = [
            ERDiagramGroup(id=gid, name=name, x=x, y=y, width=w, height=h,
                           color=color, diagram_id=self._current_diagram.id)
            for (gid, name, x, y, w, h, color) in self._scene.get_groups()
        ]

        # Save zoom level + column types toggle + group_fks
        transform = self._view.transform()
        self._current_diagram.zoom_level = transform.m11()
        self._current_diagram.show_column_types = self._show_column_types
        self._current_diagram.group_fks = self._group_fks

        config_db = get_config_db()
        config_db.save_er_diagram(self._current_diagram)
        # Status bar notification instead of popup
        try:
            w = self.window()
            while w is not None and not hasattr(w, 'status_bar'):
                w = w.parent()
            if w is not None and hasattr(w, 'status_bar'):
                w.status_bar.set_message(tr("er_diagram_saved"))
        except Exception:
            pass

    def _remove_tables_from_diagram(self, table_names: list):
        """Remove selected tables from the diagram (not from the database)."""
        if not self._current_diagram or not self._scene:
            return
        for name in table_names:
            self._scene.remove_table(name)
            self._current_diagram.remove_table(name)
        config_db = get_config_db()
        config_db.save_er_diagram(self._current_diagram)

    def _fit_view(self):
        """Center and zoom to show all tables within the viewport."""
        if not self._scene:
            return
        rect = self._scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        self._view.fitInView(rect.adjusted(-50, -50, 50, 50),
                             Qt.AspectRatioMode.KeepAspectRatio)

    def _toggle_fk_names(self):
        """Toggle FK name labels on/off."""
        if not self._scene:
            return
        self._show_fk_names = not self._show_fk_names
        self._scene.set_show_fk_names(self._show_fk_names)

    def _toggle_column_types(self):
        """Toggle display of column types in tables (compact vs detailed)."""
        if not self._scene:
            return
        self._show_column_types = not self._show_column_types
        self._scene.set_show_column_types(self._show_column_types)

    def _toggle_group_fks(self):
        """Toggle grouping of multiple FKs between same table pair."""
        self._group_fks = not self._group_fks
        # Persist to DB BEFORE reload so _load_diagram re-reads the correct value
        if self._current_diagram:
            self._current_diagram.group_fks = self._group_fks
            get_config_db().save_er_diagram(self._current_diagram)
        self._update_group_fks_icon()
        if self._current_diagram:
            self._load_diagram(self._current_diagram.id)

    def _reset_layout(self):
        """Clear every manual FK geometry on the current diagram and rerun the
        auto-layout. Display-only: table positions/sizes/groups untouched, NO
        database save — the user decides whether to persist via Save Diagram
        or to drop the result by reloading the diagram."""
        if not self._current_diagram or not self._scene:
            DialogHelper.warning(tr("er_no_diagram_selected"), parent=self)
            return
        if not DialogHelper.confirm(tr("er_reset_layout_confirm")):
            return
        self._scene.reset_all_routing()
        # Clear in-memory midpoints so "Save Diagram" after this truly commits
        # the reset. If the user reloads instead, DB midpoints are still there.
        self._current_diagram.fk_midpoints = []
        try:
            w = self.window()
            while w is not None and not hasattr(w, 'status_bar'):
                w = w.parent()
            if w is not None and hasattr(w, 'status_bar'):
                w.status_bar.set_message(tr("er_layout_reset_done"))
        except Exception:
            pass

    def _add_group(self):
        """Create a new visual group frame centered in the current viewport."""
        if not self._current_diagram or not self._scene:
            DialogHelper.warning(tr("er_no_diagram_selected"), parent=self)
            return

        from PySide6.QtWidgets import QInputDialog
        from ...database.models import ERDiagramGroup

        name, ok = QInputDialog.getText(
            self, tr("er_add_group"), tr("er_group_name_prompt"),
            text=tr("er_group_default_name")
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        # Place the group centered on the current viewport
        view_rect = self._view.mapToScene(self._view.viewport().rect()).boundingRect()
        width, height = 360.0, 240.0
        x = view_rect.center().x() - width / 2
        y = view_rect.center().y() - height / 2

        group = ERDiagramGroup(name=name, x=x, y=y, width=width, height=height)
        self._scene.add_group(group.id, group.name, group.x, group.y,
                              group.width, group.height, group.color)
        self._current_diagram.groups.append(group)

    def _on_group_geometry_changed(self, group_id: str, x: float, y: float,
                                    w: float, h: float):
        """Persist group position/size into the current diagram model."""
        if not self._current_diagram:
            return
        for g in self._current_diagram.groups:
            if g.id == group_id:
                g.x, g.y, g.width, g.height = x, y, w, h
                return

    def _update_group_fks_icon(self):
        """Swap toolbar icon based on current grouping state."""
        if hasattr(self, '_group_fks_btn') and self._group_fks_btn is not None:
            from ...utils.image_loader import get_icon
            name = "link_grouped" if self._group_fks else "link_multi"
            icon = get_icon(name, size=20)
            if icon:
                self._group_fks_btn.setIcon(icon)
            tooltip = tr("er_ungroup_fks") if self._group_fks else tr("er_group_fks")
            self._group_fks_btn.setToolTip(tooltip)

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
