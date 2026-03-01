"""
About Dialog - Shows application information and support options
"""

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QWidget, QGroupBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QDesktopServices, QCursor
from ..templates.dialog import SelectorDialog
from ..core.theme_bridge import ThemeBridge
from ...utils.image_loader import get_pixmap
from ... import __version__
import logging

logger = logging.getLogger(__name__)


class _ClickableIcon(QLabel):
    """A QLabel displaying a pixmap that opens a URL on click."""

    def __init__(self, pixmap: QPixmap, url: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(tooltip)
        self._url = url

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(self._url))


class AboutDialog(SelectorDialog):
    """About dialog showing app information and support options.

    Inherits from SelectorDialog for consistent styling with custom title bar.
    """

    DONATION_LINKS = [
        ("github-sponsors.png", "GitHub Sponsors", "https://github.com/sponsors/Lestat2Lioncourt"),
        ("ko-fi.png",           "Ko-fi",           "https://ko-fi.com/dataforgestudio"),
        ("buy-me-a-coffee.png", "Buy Me a Coffee", "https://buymeacoffee.com/dataforgestudio"),
        ("paypal.png",          "PayPal",          "https://paypal.me/dataforgestudio"),
        ("liberapay.png",       "Liberapay",       "https://liberapay.com/DataForgeStudio"),
    ]

    def __init__(self, parent=None):
        super().__init__(
            title="About DataForge Studio",
            parent=parent,
            width=560,
            height=650
        )

        self._load_theme_colors()
        self._setup_content()

    def _load_theme_colors(self):
        """Load colors from theme."""
        try:
            theme_bridge = ThemeBridge.get_instance()
            colors = theme_bridge.get_theme_colors()
        except Exception:
            colors = {}

        self._colors = {
            'text_primary': colors.get('main_menu_bar_fg', '#ffffff'),
            'text_secondary': colors.get('text_secondary', '#808080'),
            'text_muted': colors.get('text_muted', '#c0c0c0'),
            'border': colors.get('border_color', '#3d3d3d'),
            'accent': colors.get('accent_color', '#0078d4'),
        }

    def _setup_content(self):
        """Setup the dialog content inside self.content_widget."""
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(12)

        self._create_header(content_layout)
        self._create_description(content_layout)
        self._create_features(content_layout)
        self._create_github_link(content_layout)
        self._create_discussions_link(content_layout)
        self._create_support_section(content_layout)
        self._create_footer(content_layout)

        content_layout.addStretch()

    def _create_header(self, layout: QVBoxLayout):
        """Create header with logo, name, and version."""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)

        logo_pixmap = get_pixmap("DataForge Studio", width=80, height=80)
        if logo_pixmap:
            logo_label = QLabel()
            logo_label.setPixmap(logo_pixmap)
            logo_label.setFixedSize(80, 80)
            header_layout.addWidget(logo_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)

        name_label = QLabel("DataForge Studio")
        name_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {self._colors['text_primary']};")
        text_layout.addWidget(name_label)

        version_label = QLabel(f"Version {__version__}")
        version_label.setFont(QFont("Arial", 12))
        version_label.setStyleSheet(f"color: {self._colors['text_secondary']};")
        text_layout.addWidget(version_label)

        header_layout.addLayout(text_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

    def _create_description(self, layout: QVBoxLayout):
        """Create description section."""
        desc_label = QLabel("Multi-database management tool")
        desc_label.setFont(QFont("Arial", 11))
        desc_label.setStyleSheet(f"color: {self._colors['text_muted']}; padding: 10px 0;")
        layout.addWidget(desc_label)

    def _create_features(self, layout: QVBoxLayout):
        """Create features list."""
        features_group = QGroupBox("Fonctionnalites")
        features_group.setStyleSheet(f"""
            QGroupBox {{
                color: {self._colors['text_primary']};
                border: 1px solid {self._colors['border']};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 11pt;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)

        features_layout = QVBoxLayout(features_group)
        features_layout.setSpacing(8)

        features = [
            "  Support multi-bases (SQL Server, MySQL, Postgres, SQLite)",
            "  Mise en forme automatique des requetes avec 4 styles",
            "  Editeur de requetes avec analyses de distribution",
            "  Navigateur de fichiers + affichage multiformat (csv, json, ...)",
            "  Distribution de fichier d'une racine dans leur dossier Dataset",
            "  Scripts d'importation de fichiers dans des tables avec gestion du polymorphisme",
            "  Definition de jobs pour sequencer des scripts ou d'autres jobs",
            "  Orchestrateur de jobs multi-plateformes",
            "  Gestionnaire de requetes enregistrees",
            "  Plusieurs themes + editeur de themes",
            "  Multilingue + editeur pour nouvelle traduction",
        ]

        for feature in features:
            lbl = QLabel(feature)
            lbl.setStyleSheet(f"color: {self._colors['text_muted']}; padding-left: 10px;")
            lbl.setFont(QFont("Arial", 10))
            features_layout.addWidget(lbl)

        layout.addWidget(features_group)

    def _create_github_link(self, layout: QVBoxLayout):
        """Create GitHub link section."""
        github_layout = QHBoxLayout()
        github_layout.setSpacing(10)

        github_icon = QLabel("link")
        github_icon.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        github_icon.setStyleSheet(f"color: {self._colors['text_primary']};")
        github_layout.addWidget(github_icon)

        accent = self._colors['accent']
        github_link = QLabel(
            f'<a href="https://github.com/Lestat2Lioncourt/data-forge-studio" '
            f'style="color: {accent}; text-decoration: none;">'
            f'GitHub: Lestat2Lioncourt/data-forge-studio</a>'
        )
        github_link.setOpenExternalLinks(True)
        github_link.setStyleSheet("font-size: 10pt;")
        github_layout.addWidget(github_link)
        github_layout.addStretch()

        layout.addLayout(github_layout)

    def _create_discussions_link(self, layout: QVBoxLayout):
        """Create Discussions link with icon."""
        discussions_layout = QHBoxLayout()
        discussions_layout.setSpacing(10)

        # Discussion icon (themed from icons/base/)
        icon_size = 20
        disc_pixmap = get_pixmap("discussion.png", width=icon_size, height=icon_size)
        if disc_pixmap:
            icon_label = QLabel()
            icon_label.setPixmap(disc_pixmap)
            icon_label.setFixedSize(icon_size, icon_size)
            discussions_layout.addWidget(icon_label)

        accent = self._colors['accent']
        disc_link = QLabel(
            f'<a href="https://github.com/Lestat2Lioncourt/data-forge-studio/discussions" '
            f'style="color: {accent}; text-decoration: none;">'
            f'Discussions &amp; Feedback</a>'
        )
        disc_link.setOpenExternalLinks(True)
        disc_link.setStyleSheet("font-size: 10pt;")
        discussions_layout.addWidget(disc_link)
        discussions_layout.addStretch()

        layout.addLayout(discussions_layout)

    def _create_support_section(self, layout: QVBoxLayout):
        """Create compact support section with a row of clickable logo icons."""
        # Separator
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {self._colors['border']};")
        layout.addWidget(separator)

        # Title
        title_label = QLabel("Soutenir le projet")
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self._colors['text_primary']};")
        layout.addWidget(title_label)

        # Row of logo icons
        icons_layout = QHBoxLayout()
        icons_layout.setSpacing(16)
        icons_layout.setContentsMargins(0, 4, 0, 0)

        icon_size = 32
        for filename, tooltip, url in self.DONATION_LINKS:
            pixmap = get_pixmap(filename, width=icon_size, height=icon_size)
            if not pixmap:
                logger.debug(f"Donation icon not found: {filename}")
                continue

            icon_label = _ClickableIcon(pixmap, url, tooltip, parent=self)
            icons_layout.addWidget(icon_label)

        icons_layout.addStretch()
        layout.addLayout(icons_layout)

    def _create_footer(self, layout: QVBoxLayout):
        """Create copyright footer."""
        footer_label = QLabel("2024-2025 - MIT License")
        footer_label.setStyleSheet(f"color: {self._colors['text_secondary']}; padding: 15px 0 5px 0;")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setFont(QFont("Arial", 9))
        layout.addWidget(footer_label)

    def _open_url(self, url: str):
        """Open URL in default browser."""
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))
        logger.info(f"Opening URL: {url}")
