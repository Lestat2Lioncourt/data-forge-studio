"""
ER Diagram Export - PNG and SVG export utilities.
"""

from pathlib import Path
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtGui import QPainter, QImage, QColor
from PySide6.QtCore import QRectF, QMarginsF

import logging
logger = logging.getLogger(__name__)


def export_to_png(scene: QGraphicsScene, file_path: str, margin: int = 20) -> bool:
    """Export the scene to a PNG file."""
    try:
        rect = scene.itemsBoundingRect().marginsAdded(
            QMarginsF(margin, margin, margin, margin)
        )
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
        image.fill(scene.backgroundBrush().color())

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(painter, QRectF(image.rect()), rect)
        painter.end()

        image.save(file_path)
        logger.info(f"Exported ER diagram to PNG: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export PNG: {e}")
        return False


def export_to_svg(scene: QGraphicsScene, file_path: str, margin: int = 20) -> bool:
    """Export the scene to an SVG file."""
    try:
        from PySide6.QtSvg import QSvgGenerator

        rect = scene.itemsBoundingRect().marginsAdded(
            QMarginsF(margin, margin, margin, margin)
        )

        generator = QSvgGenerator()
        generator.setFileName(file_path)
        generator.setSize(rect.size().toSize())
        generator.setViewBox(QRectF(0, 0, rect.width(), rect.height()))
        generator.setTitle("ER Diagram")

        painter = QPainter(generator)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)
        painter.end()

        logger.info(f"Exported ER diagram to SVG: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export SVG: {e}")
        return False
