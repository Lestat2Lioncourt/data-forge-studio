"""
Splash Screen for DataForge Studio.

Modern vertical layout:
- logo + wordmark + tagline at the top
- thin full-width animated progress bar
- single current-status line
- compact 3-row log of recent steps (newest fades in + slides up)
- version in the bottom-right corner
- rounded corners, soft drop shadow, fade-in / fade-out
- follows the current ThemeBridge palette (dark/light)
"""

import time

from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient,
    QPainterPath, QGuiApplication, QCursor,
)

from ...utils.image_loader import get_pixmap
from ... import __version__


_SPLASH_DEFAULTS_DARK = {
    "bg_from": "#17171c",
    "bg_to": "#0e0e13",
    "border": "#2a2a30",
    "title": "#ffffff",
    "tagline": "#a0a0a8",
    "muted": "#707078",
    "accent": "#0078d4",
    "bar_track": "#2a2a30",
    "log_fg": "#b0b0b8",
    "log_check": "#4ade80",
    "log_time": "#606068",
}

_SPLASH_DEFAULTS_LIGHT = {
    "bg_from": "#fafafa",
    "bg_to": "#eeeef2",
    "border": "#d5d5da",
    "title": "#1a1a1f",
    "tagline": "#505058",
    "muted": "#80808a",
    "accent": "#0078d4",
    "bar_track": "#e2e2e7",
    "log_fg": "#30303a",
    "log_check": "#16a34a",
    "log_time": "#a0a0a8",
}


def _tr(key: str, fallback: str) -> str:
    """Translate with fallback — i18n may not be ready when splash first renders."""
    try:
        from .i18n_bridge import tr
        s = tr(key)
        return s if s and s != key else fallback
    except Exception:
        return fallback


class SplashScreen(QSplashScreen):
    """Custom splash screen with animated progress bar and fading log history."""

    WIDTH = 560
    HEIGHT = 360
    CORNER_RADIUS = 14
    SHADOW_MARGIN = 20
    LOGO_SIZE = 72

    # Layout (coordinates relative to body rect — body is offset by SHADOW_MARGIN)
    LOGO_Y = 44
    TITLE_Y = 44 + 72 + 14           # under logo
    TAGLINE_Y = TITLE_Y + 32
    BAR_Y = 244
    BAR_HEIGHT = 3
    MESSAGE_Y = BAR_Y + 14
    LOG_TOP_Y = MESSAGE_Y + 28
    LOG_ROW_HEIGHT = 14
    VERSION_Y_OFFSET = 22            # from body bottom

    CONTENT_PAD_X = 40
    MAX_LOG_ROWS = 3

    def __init__(self):
        self._start_time = time.time()
        self._step_start_time = self._start_time
        self._current_message = ""
        self._current_progress = 0
        self._displayed_progress = 0.0   # smoothly animated toward _current_progress
        # each entry: [message, duration_ms, opacity 0→1]
        self._log_history: list = []

        self._palette = self._build_palette()
        self._logo_pixmap = self._load_logo()

        pixmap = self._create_base_pixmap()
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.SplashScreen
        )

        self._center_on_screen()

        # Fade-in
        self.setWindowOpacity(0.0)
        self.show()
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(200)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

        # 60 Hz tick for progress-bar easing + new-entry fade-in
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(16)

    # ------------------------------------------------------------------
    # Palette / logo / canvas setup
    # ------------------------------------------------------------------
    def _build_palette(self) -> dict:
        is_dark = True
        accent = _SPLASH_DEFAULTS_DARK["accent"]
        try:
            from .theme_bridge import ThemeBridge
            colors = ThemeBridge.get_instance().get_theme_colors()
            is_dark = bool(colors.get("is_dark", True))
            accent = colors.get("Accent") or colors.get("accent") or accent
        except Exception:
            pass
        base = dict(_SPLASH_DEFAULTS_DARK if is_dark else _SPLASH_DEFAULTS_LIGHT)
        base["accent"] = accent
        return base

    def _load_logo(self):
        """Load the logo at 2× the target size so it stays crisp on HiDPI."""
        try:
            pm = get_pixmap(
                "DataForge-Studio-logo",
                width=self.LOGO_SIZE * 2,
                height=self.LOGO_SIZE * 2,
            )
            if pm is not None and not pm.isNull():
                pm.setDevicePixelRatio(2.0)
                return pm
        except Exception:
            pass
        return None

    def _create_base_pixmap(self) -> QPixmap:
        """Build the background pixmap: shadow + rounded body + logo + texts.
        Dynamic content (progress bar, status, logs) is painted in drawContents."""
        screen = QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen else 1.0

        total_w = self.WIDTH + 2 * self.SHADOW_MARGIN
        total_h = self.HEIGHT + 2 * self.SHADOW_MARGIN
        pixmap = QPixmap(int(total_w * dpr), int(total_h * dpr))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)

        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        body = QRectF(self.SHADOW_MARGIN, self.SHADOW_MARGIN, self.WIDTH, self.HEIGHT)

        # Soft drop shadow (faked with concentric fading rounded rects)
        for i in range(self.SHADOW_MARGIN, 0, -2):
            alpha = int(60 * (self.SHADOW_MARGIN - i + 2) / (self.SHADOW_MARGIN * 2))
            shadow_rect = body.adjusted(-i, -i + 2, i, i + 2)
            p.setBrush(QColor(0, 0, 0, max(0, alpha)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(shadow_rect, self.CORNER_RADIUS + i / 2,
                              self.CORNER_RADIUS + i / 2)

        # Rounded body with vertical gradient
        path = QPainterPath()
        path.addRoundedRect(body, self.CORNER_RADIUS, self.CORNER_RADIUS)
        grad = QLinearGradient(0, body.top(), 0, body.bottom())
        grad.setColorAt(0.0, QColor(self._palette["bg_from"]))
        grad.setColorAt(1.0, QColor(self._palette["bg_to"]))
        p.setClipPath(path)
        p.fillPath(path, QBrush(grad))
        p.setClipping(False)

        # Thin border
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(self._palette["border"]), 1))
        p.drawRoundedRect(body, self.CORNER_RADIUS, self.CORNER_RADIUS)

        # Logo centered, top area
        if self._logo_pixmap is not None:
            logo_x = body.center().x() - self.LOGO_SIZE / 2
            logo_y = body.top() + self.LOGO_Y
            p.drawPixmap(int(logo_x), int(logo_y),
                         self.LOGO_SIZE, self.LOGO_SIZE, self._logo_pixmap)

        # Wordmark
        title_font = QFont("Segoe UI", 16)
        title_font.setWeight(QFont.Weight.DemiBold)
        p.setFont(title_font)
        p.setPen(QColor(self._palette["title"]))
        p.drawText(QRectF(body.left(), body.top() + self.TITLE_Y, body.width(), 28),
                   Qt.AlignmentFlag.AlignCenter, "DataForge Studio")

        # Tagline
        tag_font = QFont("Segoe UI", 10)
        tag_font.setWeight(QFont.Weight.Light)
        p.setFont(tag_font)
        p.setPen(QColor(self._palette["tagline"]))
        p.drawText(QRectF(body.left(), body.top() + self.TAGLINE_Y, body.width(), 20),
                   Qt.AlignmentFlag.AlignCenter,
                   _tr("splash_tagline", "Multi-Database Management Tool"))

        # Version (bottom-right corner)
        ver_font = QFont("Segoe UI", 8)
        p.setFont(ver_font)
        p.setPen(QColor(self._palette["muted"]))
        p.drawText(
            QRectF(body.left(),
                   body.bottom() - self.VERSION_Y_OFFSET,
                   body.width() - 20, 14),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"v{__version__}",
        )

        p.end()
        return pixmap

    def _center_on_screen(self):
        """Center splash on the screen containing the cursor."""
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        geo = screen.geometry()
        sr = self.geometry()
        self.move(geo.x() + (geo.width() - sr.width()) // 2,
                  geo.y() + (geo.height() - sr.height()) // 2)

    # ------------------------------------------------------------------
    # Dynamic painting
    # ------------------------------------------------------------------
    def drawContents(self, painter: QPainter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        body_left = self.SHADOW_MARGIN
        body_top = self.SHADOW_MARGIN
        body_right = self.SHADOW_MARGIN + self.WIDTH

        bar_x = body_left + self.CONTENT_PAD_X
        bar_w = self.WIDTH - 2 * self.CONTENT_PAD_X
        bar_y = body_top + self.BAR_Y
        radius = self.BAR_HEIGHT / 2

        # Progress track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._palette["bar_track"]))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, self.BAR_HEIGHT),
                                radius, radius)

        # Progress fill (eased)
        filled = bar_w * max(0.0, min(100.0, self._displayed_progress)) / 100.0
        if filled > 1.0:
            painter.setBrush(QColor(self._palette["accent"]))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, filled, self.BAR_HEIGHT),
                                    radius, radius)

        # Current message (centered under bar)
        msg_font = QFont("Segoe UI", 9)
        painter.setFont(msg_font)
        painter.setPen(QColor(self._palette["tagline"]))
        msg = self._current_message or _tr("splash_loading", "Loading...")
        painter.drawText(
            QRectF(body_left, body_top + self.MESSAGE_Y, self.WIDTH, 16),
            Qt.AlignmentFlag.AlignCenter, msg,
        )

        # Log rows (last MAX_LOG_ROWS, newest at the bottom with fade/slide-up)
        log_font = QFont("Segoe UI", 8)
        painter.setFont(log_font)
        visible = self._log_history[-self.MAX_LOG_ROWS:]
        for i, (message, dur_ms, opacity) in enumerate(visible):
            alpha = int(255 * opacity)
            # Slide-up: when opacity is 0, row is 6px below final; ends at 0 offset.
            y_offset = (1.0 - opacity) * 6.0
            row_y = body_top + self.LOG_TOP_Y + i * self.LOG_ROW_HEIGHT + y_offset

            # Checkmark
            check_color = QColor(self._palette["log_check"])
            check_color.setAlpha(alpha)
            painter.setPen(check_color)
            painter.drawText(
                QRectF(bar_x, row_y, 14, self.LOG_ROW_HEIGHT),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "✓",
            )

            # Message (truncate if too long)
            msg_color = QColor(self._palette["log_fg"])
            msg_color.setAlpha(alpha)
            painter.setPen(msg_color)
            display = message if len(message) <= 45 else message[:42] + "…"
            painter.drawText(
                QRectF(bar_x + 18, row_y, bar_w - 74, self.LOG_ROW_HEIGHT),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, display,
            )

            # Duration aligned right
            time_color = QColor(self._palette["log_time"])
            time_color.setAlpha(alpha)
            painter.setPen(time_color)
            painter.drawText(
                QRectF(bar_x + bar_w - 56, row_y, 56, self.LOG_ROW_HEIGHT),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{dur_ms}ms",
            )

    # ------------------------------------------------------------------
    # Animation tick
    # ------------------------------------------------------------------
    def _tick(self):
        """Ease progress bar toward target; fade in the newest log entries."""
        changed = False

        target = float(self._current_progress)
        diff = target - self._displayed_progress
        if abs(diff) > 0.1:
            # ease-out: move 15% of remaining distance per frame
            self._displayed_progress += diff * 0.15
            changed = True
        elif self._displayed_progress != target:
            self._displayed_progress = target
            changed = True

        for i, row in enumerate(self._log_history):
            if row[2] < 1.0:
                self._log_history[i] = (row[0], row[1], min(1.0, row[2] + 0.1))
                changed = True

        if changed:
            self.repaint()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def show_message(self, message: str):
        """Set the current status line without advancing progress."""
        self._current_message = message
        self.repaint()
        QApplication.processEvents()

    def update_progress(self, message: str, progress: int = 0):
        """Push the previous step into the log history and advance to a new one."""
        now = time.time()
        step_ms = int((now - self._step_start_time) * 1000)

        if self._current_message and step_ms > 0:
            self._log_history.append([self._current_message, step_ms, 0.0])
            # keep memory bounded
            if len(self._log_history) > 32:
                self._log_history = self._log_history[-32:]

        self._current_message = message
        self._current_progress = max(0, min(100, progress))
        self._step_start_time = now

        self.repaint()
        QApplication.processEvents()

    def apply_theme(self):
        """Rebuild palette + background after ThemeBridge initializes or changes."""
        self._palette = self._build_palette()
        self.setPixmap(self._create_base_pixmap())
        self.repaint()

    def finish(self, widget):
        """Fade out, then close and transfer focus to the main window."""
        try:
            self._anim_timer.stop()
        except Exception:
            pass
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(200)
        fade.setStartValue(self.windowOpacity())
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InCubic)

        def _done():
            QSplashScreen.finish(self, widget)

        fade.finished.connect(_done)
        fade.start()
        self._fade_out_anim = fade  # keep reference so it isn't GC'd


def show_splash_screen() -> SplashScreen:
    """Create and display the splash screen. Returns the instance for progress updates."""
    splash = SplashScreen()
    splash.show_message(_tr("splash_loading", "Loading..."))
    return splash
