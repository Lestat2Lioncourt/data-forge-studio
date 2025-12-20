"""Transparent wrapper window for easy resizing."""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QRect, QPoint, QEvent
from PySide6.QtGui import QMouseEvent, QPainter, QColor, QPen


class ResizeWrapper(QWidget):
    """
    Transparent wrapper that adds a resize margin around the main window.

    This creates an invisible border around the window that makes resizing
    much easier by providing a larger grab area.
    """

    # Resize margin in pixels (invisible grab area around the window)
    RESIZE_MARGIN = 4

    # Resize priority zone in pixels (from window edge, resize takes priority over drag)
    RESIZE_PRIORITY_ZONE = 12

    def __init__(self, wrapped_widget: QWidget, parent=None):
        super().__init__(parent)
        self.wrapped_widget = wrapped_widget

        # Make wrapper frameless
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_QuitOnClose)  # Quit application when wrapper closes
        self.setMouseTracking(True)

        # Don't use WA_TranslucentBackground - it prevents mouse events
        # We'll paint transparency manually in paintEvent

        # Resize state
        self._resize_direction = None
        self._resize_start_pos = QPoint()
        self._resize_start_geometry = QRect()
        self._is_maximized = False
        self._debug_visible = False
        self._wrapper_bg_color = "#1e1e1e"  # Default background color

        self._setup_ui()

        # Install event filter recursively on all widgets
        self._install_event_filter_recursive(self.wrapped_widget)

    def _install_event_filter_recursive(self, widget):
        """Install event filter on widget and all its children recursively."""
        widget.installEventFilter(self)
        widget.setMouseTracking(True)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)
            child.setMouseTracking(True)

    def _setup_ui(self):
        """Setup the wrapper layout."""
        layout = QVBoxLayout(self)
        # Set margins to create the invisible resize area
        layout.setContentsMargins(
            self.RESIZE_MARGIN,
            self.RESIZE_MARGIN,
            self.RESIZE_MARGIN,
            self.RESIZE_MARGIN
        )
        layout.setSpacing(0)
        layout.addWidget(self.wrapped_widget)

    @property
    def window(self):
        """Access the wrapped TemplateWindow."""
        return self.wrapped_widget

    def _get_resize_direction(self, pos: QPoint) -> str:
        """
        Determine resize direction based on mouse position.

        Uses RESIZE_PRIORITY_ZONE: within this distance from window edge,
        resize takes priority even if over title bar.

        Returns:
            Direction string or None if not in resize area
        """
        rect = self.rect()
        x, y = pos.x(), pos.y()
        priority_zone = self.RESIZE_PRIORITY_ZONE

        # Check if in priority resize zones (within X pixels from edges)
        on_left = x <= priority_zone
        on_right = x >= rect.width() - priority_zone
        on_top = y <= priority_zone
        on_bottom = y >= rect.height() - priority_zone

        # Determine direction (corners first, then edges)
        if on_top and on_left:
            return 'top-left'
        elif on_top and on_right:
            return 'top-right'
        elif on_bottom and on_left:
            return 'bottom-left'
        elif on_bottom and on_right:
            return 'bottom-right'
        elif on_left:
            return 'left'
        elif on_right:
            return 'right'
        elif on_top:
            return 'top'
        elif on_bottom:
            return 'bottom'

        return None

    def _update_cursor(self, direction: str):
        """Update cursor based on resize direction."""
        cursor_map = {
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
            'top-left': Qt.SizeFDiagCursor,
            'bottom-right': Qt.SizeFDiagCursor,
            'top-right': Qt.SizeBDiagCursor,
            'bottom-left': Qt.SizeBDiagCursor,
        }

        if direction in cursor_map:
            self.setCursor(cursor_map[direction])
        else:
            # Force reset to normal arrow cursor
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for resizing."""
        if event.button() == Qt.LeftButton and not self._is_maximized:
            self._resize_direction = self._get_resize_direction(event.pos())
            if self._resize_direction:
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geometry = self.geometry()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for cursor and resizing."""
        if not self._is_maximized:
            if self._resize_direction:
                # Currently resizing
                self._handle_resize(event.globalPosition().toPoint())
                event.accept()
                return
            else:
                # Not resizing - check if cursor should change
                direction = self._get_resize_direction(event.pos())
                self._update_cursor(direction)
                event.accept()
                return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop resizing."""
        if event.button() == Qt.LeftButton:
            self._resize_direction = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _handle_resize(self, global_pos: QPoint):
        """Perform window resizing."""
        delta = global_pos - self._resize_start_pos
        geo = QRect(self._resize_start_geometry)

        if 'left' in self._resize_direction:
            geo.setLeft(geo.left() + delta.x())
        if 'right' in self._resize_direction:
            geo.setRight(geo.right() + delta.x())
        if 'top' in self._resize_direction:
            geo.setTop(geo.top() + delta.y())
        if 'bottom' in self._resize_direction:
            geo.setBottom(geo.bottom() + delta.y())

        # Enforce minimum size (account for margins)
        min_width = self.wrapped_widget.minimumWidth() + (self.RESIZE_MARGIN * 2)
        min_height = self.wrapped_widget.minimumHeight() + (self.RESIZE_MARGIN * 2)

        if geo.width() >= min_width and geo.height() >= min_height:
            self.setGeometry(geo)

    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        layout = self.layout()

        if self._is_maximized:
            # Restore to normal size
            self.setGeometry(self._resize_start_geometry)
            self._is_maximized = False

            # Restore resize margins
            if layout:
                layout.setContentsMargins(
                    self.RESIZE_MARGIN,
                    self.RESIZE_MARGIN,
                    self.RESIZE_MARGIN,
                    self.RESIZE_MARGIN
                )
        else:
            # Save current geometry
            self._resize_start_geometry = self.geometry()
            # Maximize to available screen geometry
            screen = self.screen()
            if screen:
                self.setGeometry(screen.availableGeometry())
            self._is_maximized = True

            # Remove resize margins in fullscreen
            if layout:
                layout.setContentsMargins(0, 0, 0, 0)

        # Update the maximize button icon
        if hasattr(self.wrapped_widget, 'title_bar'):
            self.wrapped_widget.title_bar.update_maximize_button(self._is_maximized)

    def set_maximized(self, maximized: bool):
        """Update maximized state (called by wrapped widget)."""
        self._is_maximized = maximized

    def set_background_color(self, color: str):
        """
        Set the background color of the wrapper.

        Args:
            color: Hex color string (e.g., "#1e1e1e")
        """
        self._wrapper_bg_color = color
        self.update()  # Force repaint

    def eventFilter(self, obj, event):
        """Filter events to handle resize priority and cursor updates."""
        if not self._is_maximized:
            # Get title bar reference
            title_bar = getattr(self.wrapped_widget, 'title_bar', None)

            # Handle MouseMove for ALL child widgets to update cursor properly
            if event.type() == QEvent.MouseMove and hasattr(event, 'pos'):
                # Convert to wrapper coordinates regardless of which widget sent the event
                global_pos = obj.mapToGlobal(event.pos())
                local_pos = self.mapFromGlobal(global_pos)
                direction = self._get_resize_direction(local_pos)

                # Check if mouse is over a control button
                if title_bar and obj == title_bar:
                    widget_at_pos = title_bar.childAt(event.pos())
                    if widget_at_pos in [
                        getattr(title_bar, 'close_btn', None),
                        getattr(title_bar, 'minimize_btn', None),
                        getattr(title_bar, 'maximize_btn', None),
                        getattr(title_bar, 'special_btn', None)
                    ]:
                        # Force normal cursor on control buttons
                        self.setCursor(Qt.ArrowCursor)
                        return super().eventFilter(obj, event)

                # If currently resizing, continue
                if self._resize_direction:
                    if obj == title_bar:
                        self._handle_resize(global_pos)
                        return True
                else:
                    # Update cursor based on position
                    self._update_cursor(direction)

                    # If on title bar in resize zone, prepare to intercept
                    if obj == title_bar and direction:
                        # Just update cursor, actual resize starts on mouse press
                        pass

            # Handle mouse press on title bar in resize zone
            elif event.type() == QEvent.MouseButtonPress and obj == title_bar:
                if hasattr(event, 'pos'):
                    global_pos = obj.mapToGlobal(event.pos())
                    local_pos = self.mapFromGlobal(global_pos)
                    direction = self._get_resize_direction(local_pos)

                    if direction:
                        # Start resize instead of drag
                        self._resize_direction = direction
                        self._resize_start_pos = global_pos
                        self._resize_start_geometry = self.geometry()
                        self._update_cursor(direction)
                        return True  # Block title bar from handling this

            # Handle mouse release
            elif event.type() == QEvent.MouseButtonRelease:
                if self._resize_direction:
                    self._resize_direction = None
                    # Update cursor based on current position
                    if hasattr(event, 'pos'):
                        global_pos = obj.mapToGlobal(event.pos())
                        local_pos = self.mapFromGlobal(global_pos)
                        direction = self._get_resize_direction(local_pos)
                        self._update_cursor(direction)
                    return True

            # Reset cursor when leaving any widget
            elif event.type() == QEvent.Leave:
                if not self._resize_direction:
                    # Check if mouse is still inside wrapper bounds
                    cursor_pos = self.mapFromGlobal(self.cursor().pos())
                    if not self.rect().contains(cursor_pos):
                        self.setCursor(Qt.ArrowCursor)

        return super().eventFilter(obj, event)

    def leaveEvent(self, event):
        """Reset cursor when mouse leaves the wrapper completely."""
        if not self._resize_direction:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def set_debug_visible(self, visible: bool = True):
        """
        Toggle visibility of the resize wrapper border for debugging.

        Args:
            visible: If True, shows a red border around the resize margin.
                     If False, makes it almost invisible (normal mode).
        """
        self._debug_visible = visible

        # Debug mode enables visual feedback for troubleshooting

        # Force repaint
        self.update()

    def toggle_debug_visible(self):
        """Toggle the debug visibility on/off."""
        self.set_debug_visible(not self._debug_visible)

    def paintEvent(self, event):
        """Paint event to draw the wrapper (transparent or debug mode)."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._debug_visible:
            # Debug mode: Draw red semi-transparent background for the margin area
            margin_color = QColor(255, 0, 0, 80)  # Red with alpha
            painter.fillRect(self.rect(), margin_color)

            # Draw the inner window area in green to show the contrast
            inner_rect = self.wrapped_widget.geometry()
            inner_color = QColor(0, 255, 0, 50)  # Green with alpha
            painter.fillRect(inner_rect, inner_color)

            # Draw red border outline
            pen = QPen(QColor(255, 0, 0, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

            # Draw inner border to show wrapped widget boundary
            pen.setColor(QColor(0, 255, 0, 255))
            painter.setPen(pen)
            painter.drawRect(inner_rect)
        else:
            # Normal mode: Paint with the same color as the inner window background
            # This ensures no visible border while still capturing mouse events
            bg_color = QColor(self._wrapper_bg_color)
            painter.fillRect(self.rect(), bg_color)

        painter.end()
        super().paintEvent(event)
