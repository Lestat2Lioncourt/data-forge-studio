"""
Splash Screen for DataForge Studio
Displays during application startup with progress updates
"""

from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QImage, QPen
from pathlib import Path
from ...utils.image_loader import get_pixmap


class SplashScreen(QSplashScreen):
    """Custom splash screen with progress bar and status updates"""

    def __init__(self):
        import time
        self._start_time = time.time()
        self._step_start_time = self._start_time

        # Load DataForge Studio splash image
        logo_pixmap = get_pixmap("DataForge Studio", width=350, height=280)

        # Create splash with logo
        if logo_pixmap is not None:
            pixmap = self._create_splash_with_logo(logo_pixmap)
        else:
            # Fallback to generated pixmap if image not found
            pixmap = self._create_splash_pixmap()

        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SplashScreen
        )

        # Store current message and log history
        self._current_message = "Initializing..."
        self._current_progress = 0
        self._log_history = []  # List of (message, duration_ms)

        # Center on screen
        self._center_on_screen()

        # Show the splash screen
        self.show()

    def _create_splash_with_logo(self, logo_pixmap: QPixmap) -> QPixmap:
        """Create splash screen with logo on left and progress area on right"""
        width = 800
        height = 450

        # Create base pixmap with transparent background
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent background (67% opacity black)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        background_color = QColor(0, 0, 0, 171)  # Black with 67% opacity (171/255)
        painter.fillRect(0, 0, width, height, background_color)

        # Draw border
        painter.setPen(QPen(QColor("#0078d4"), 2))
        painter.drawRect(1, 1, width - 2, height - 2)

        # Left side: Logo (400px wide)
        logo_area_width = 400
        logo_x = (logo_area_width - logo_pixmap.width()) // 2 + 20
        logo_y = (height - logo_pixmap.height()) // 2
        painter.drawPixmap(logo_x, logo_y, logo_pixmap)

        # Draw vertical separator
        separator_x = logo_area_width
        painter.setPen(QPen(QColor("#3d3d3d"), 1))
        painter.drawLine(separator_x, 20, separator_x, height - 20)

        # Right side: Progress area (400px wide)
        right_area_x = logo_area_width + 30
        right_area_width = width - logo_area_width - 60

        # Title
        title_font = QFont("Arial", 18, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(right_area_x, 80, right_area_width, 40,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                        "DataForge Studio")

        # Version
        version_font = QFont("Arial", 11)
        painter.setFont(version_font)
        painter.setPen(QColor("#808080"))
        painter.drawText(right_area_x, 115, right_area_width, 30,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                        "Version 0.50")

        # Subtitle
        subtitle_font = QFont("Arial", 10)
        painter.setFont(subtitle_font)
        painter.setPen(QColor("#a0a0a0"))
        painter.drawText(right_area_x, 145, right_area_width, 30,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                        "Multi-Database Management Tool")

        # Progress area background
        progress_area_y = 200
        progress_area_height = 180
        painter.fillRect(right_area_x - 10, progress_area_y, right_area_width + 10, progress_area_height,
                        QColor(30, 30, 30, 100))

        # Progress area title
        progress_title_font = QFont("Arial", 11, QFont.Weight.Bold)
        painter.setFont(progress_title_font)
        painter.setPen(QColor("#0078d4"))
        painter.drawText(right_area_x, progress_area_y + 15, right_area_width, 30,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                        "Loading...")

        painter.end()
        return pixmap

    def _create_splash_pixmap(self) -> QPixmap:
        """Create a custom splash screen pixmap (fallback without logo)"""
        width = 800
        height = 450

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#1e1e1e"))  # Dark background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw border
        border_color = QColor("#0078d4")
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(1, 1, width - 2, height - 2)

        # Draw title (centered)
        title_font = QFont("Arial", 32, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(pixmap.rect().adjusted(0, -80, 0, 0), Qt.AlignmentFlag.AlignCenter, "DataForge Studio")

        # Draw version
        version_font = QFont("Arial", 14)
        painter.setFont(version_font)
        painter.setPen(QColor("#808080"))
        version_rect = pixmap.rect().adjusted(0, -20, 0, 0)
        painter.drawText(version_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "Version 0.50")

        # Draw subtitle
        subtitle_font = QFont("Arial", 12)
        painter.setFont(subtitle_font)
        painter.setPen(QColor("#a0a0a0"))
        subtitle_rect = pixmap.rect().adjusted(0, 40, 0, 0)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                        "Multi-Database Management Tool")

        painter.end()
        return pixmap

    def _center_on_screen(self):
        """Center the splash screen on the primary screen"""
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        splash_rect = self.geometry()
        x = (screen.width() - splash_rect.width()) // 2
        y = (screen.height() - splash_rect.height()) // 2
        self.move(x, y)

    def drawContents(self, painter: QPainter):
        """Override to draw custom progress messages"""
        super().drawContents(painter)

        # Draw messages in the right progress area
        right_area_x = 430
        progress_area_y = 235
        right_area_width = 340

        # Draw progress bar
        bar_y = progress_area_y
        bar_width = right_area_width - 20
        bar_height = 8

        # Background
        painter.fillRect(right_area_x, bar_y, bar_width, bar_height, QColor("#1e1e1e"))
        # Progress
        progress_width = int(bar_width * self._current_progress / 100)
        painter.fillRect(right_area_x, bar_y, progress_width, bar_height, QColor("#0078d4"))
        # Border
        painter.setPen(QPen(QColor("#3d3d3d"), 1))
        painter.drawRect(right_area_x, bar_y, bar_width, bar_height)

        # Percentage text
        pct_font = QFont("Consolas", 8)
        painter.setFont(pct_font)
        painter.setPen(QColor("#808080"))
        painter.drawText(right_area_x + bar_width + 5, bar_y, 40, bar_height + 4,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        f"{self._current_progress}%")

        # Current action (larger, highlighted)
        action_y = bar_y + 20
        action_font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(action_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(right_area_x, action_y, right_area_width, 20,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                        f"► {self._current_message}")

        # Log history (smaller, with timing)
        log_y = action_y + 28
        log_font = QFont("Consolas", 8)
        painter.setFont(log_font)

        # Show last 6 log entries
        visible_logs = self._log_history[-6:]
        for i, (msg, duration_ms) in enumerate(visible_logs):
            # Checkmark and message
            painter.setPen(QColor("#2ecc71"))  # Green checkmark
            painter.drawText(right_area_x, log_y + i * 16, 15, 16,
                           Qt.AlignmentFlag.AlignLeft, "✓")

            painter.setPen(QColor("#808080"))
            # Truncate long messages
            display_msg = msg[:35] + "..." if len(msg) > 38 else msg
            painter.drawText(right_area_x + 18, log_y + i * 16, right_area_width - 70, 16,
                           Qt.AlignmentFlag.AlignLeft, display_msg)

            # Duration on the right
            painter.setPen(QColor("#606060"))
            painter.drawText(right_area_x + right_area_width - 55, log_y + i * 16, 50, 16,
                           Qt.AlignmentFlag.AlignRight, f"{duration_ms}ms")

        # Total elapsed time at bottom
        import time
        elapsed = int((time.time() - self._start_time) * 1000)
        elapsed_y = progress_area_y + 160
        elapsed_font = QFont("Arial", 8)
        painter.setFont(elapsed_font)
        painter.setPen(QColor("#606060"))
        painter.drawText(right_area_x, elapsed_y, right_area_width, 16,
                        Qt.AlignmentFlag.AlignLeft,
                        f"Temps total: {elapsed}ms")

    def show_message(self, message: str):
        """
        Display a status message on the splash screen.

        Args:
            message: Status message to display
        """
        self._current_message = message
        # Force repaint
        self.repaint()
        # Process events to update the display
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def update_progress(self, message: str, progress: int = 0):
        """
        Update splash screen with progress.

        Args:
            message: Status message
            progress: Progress percentage (0-100)
        """
        import time

        # Calculate duration of previous step
        now = time.time()
        step_duration_ms = int((now - self._step_start_time) * 1000)

        # Add previous message to log (if there was one and it took > 0ms)
        if self._current_message and self._current_message != "Initializing..." and step_duration_ms > 0:
            self._log_history.append((self._current_message, step_duration_ms))

        # Update current state
        self._current_message = message
        self._current_progress = progress
        self._step_start_time = now

        # Force repaint
        self.repaint()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()


def show_splash_screen():
    """
    Create and show splash screen.

    Returns:
        SplashScreen instance
    """
    splash = SplashScreen()
    splash.show_message("Initializing...")
    return splash
