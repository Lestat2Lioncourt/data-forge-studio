"""
FK hover overlay — the popup listing a relationship's column pairs.

Attaches to any QGraphicsView showing an ERDiagramScene, so the editing view and
read-only previews rendered in another container share the same behaviour.
"""

from PySide6.QtWidgets import QLabel, QGraphicsView
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QCursor


class FKHoverOverlay(QObject):
    """Floating popup showing the columns of the hovered FK relationship.

    Lives as a child of the view's viewport and re-centres itself on resize.
    Connect it to a scene's `relation_hovered` signal.
    """

    MARGIN = 8

    def __init__(self, view: QGraphicsView):
        super().__init__(view)
        self._view = view
        self._label = QLabel(view)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.hide()
        self.apply_theme()
        view.installEventFilter(self)

    def attach(self, scene):
        """Connect to a scene's relation_hovered signal."""
        if scene is not None and hasattr(scene, 'relation_hovered'):
            scene.relation_hovered.connect(self.show_html)

    def apply_theme(self):
        """Re-read the palette (call this on a theme change)."""
        from ...core.theme_bridge import ThemeBridge
        p = ThemeBridge.get_instance().get_er_diagram_colors()
        self._label.setStyleSheet(
            f"background-color: {p['popup_bg']}; color: {p['popup_fg']};"
            f" padding: 6px 12px; border-radius: 4px;"
            f" border: 1px solid {p['popup_border']};"
        )

    def show_html(self, html: str):
        """Show the popup, or hide it when `html` is empty."""
        if not html:
            self._label.hide()
            return
        self._label.setText(html)
        self._label.adjustSize()
        self._reposition()
        self._label.show()
        self._label.raise_()

    def _reposition(self):
        """Top- or bottom-centred depending on the cursor: when it sits in the
        upper half, the popup goes to the bottom so it does not cover the link
        the user is reaching for."""
        viewport = self._view.viewport()
        view_w, view_h = viewport.width(), viewport.height()
        label_w, label_h = self._label.width(), self._label.height()

        x = max(0, (view_w - label_w) // 2)
        cursor_local = viewport.mapFromGlobal(QCursor.pos())
        if 0 <= cursor_local.y() <= view_h // 2:
            y = max(self.MARGIN, view_h - label_h - self.MARGIN)
        else:
            y = self.MARGIN
        self._label.move(x, y)

    def eventFilter(self, obj, event):
        if (obj is self._view and event.type() == QEvent.Type.Resize
                and self._label.isVisible()):
            self._reposition()
        return super().eventFilter(obj, event)
