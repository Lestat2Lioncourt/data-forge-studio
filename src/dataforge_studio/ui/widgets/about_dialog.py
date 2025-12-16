"""
About Dialog - Shows application information and support options
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QWidget, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QDesktopServices, QColor
from ..window_template.title_bar import TitleBar
from ..core.theme_bridge import ThemeBridge
from ...utils.image_loader import get_pixmap
import logging

logger = logging.getLogger(__name__)


class AboutDialog(QDialog):
    """About dialog showing app information and donation options"""

    # Configuration URLs - To be updated before publication
    DONATION_URLS = {
        "github_sponsors": "https://github.com/sponsors/Lestat2Lioncourt",  # Update when available
        "ko_fi": "https://ko-fi.com/dataforgestudio",  # Update with your account
        "buy_me_coffee": "https://buymeacoffee.com/dataforgestudio",  # Update with your account
        "paypal": "https://paypal.me/dataforgestudio",  # Update with your account
        "liberapay": "https://liberapay.com/DataForgeStudio"  # Update with your account
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set frameless window
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(600, 700)

        # Allow window to be deleted when closed
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Apply theme colors
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()
        window_bg = colors.get('window_bg', '#1e1e1e')
        border_color = colors.get('border_color', '#3d3d3d')

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {window_bg};
                border: 1px solid {border_color};
            }}
        """)

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Custom title bar
        self.title_bar = TitleBar("About DataForge Studio")
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        # No maximize for About dialog
        self.title_bar.maximize_btn.hide()
        layout.addWidget(self.title_bar)

        # Apply theme to title bar
        theme_bridge = ThemeBridge.get_instance()
        colors = theme_bridge.get_theme_colors()
        title_bar_bg = colors.get('main_menu_bar_bg', '#2b2b2b')
        title_bar_fg = colors.get('main_menu_bar_fg', '#ffffff')
        self.title_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {title_bar_bg};
                color: {title_bar_fg};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {title_bar_fg};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QPushButton#closeButton:hover {{
                background-color: #e81123;
            }}
        """)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(15)

        # Header: Logo + Name + Version
        self._create_header(content_layout)

        # Description
        self._create_description(content_layout)

        # Features
        self._create_features(content_layout)

        # GitHub Link
        self._create_github_link(content_layout)

        # Support Section
        self._create_support_section(content_layout)

        # Copyright
        self._create_footer(content_layout)

        # Spacer
        content_layout.addStretch()

        # Close button
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cc1;
            }
        """)
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        close_layout.addStretch()
        content_layout.addLayout(close_layout)

        # Add content widget to main layout
        layout.addWidget(content_widget)

    def _create_header(self, layout: QVBoxLayout):
        """Create header with logo, name, and version"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)

        # Logo
        logo_pixmap = get_pixmap("DataForge Studio", width=80, height=80)
        if logo_pixmap:
            logo_label = QLabel()
            logo_label.setPixmap(logo_pixmap)
            logo_label.setFixedSize(80, 80)
            header_layout.addWidget(logo_label)

        # Name and Version
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)

        name_label = QLabel("DataForge Studio")
        name_font = QFont("Arial", 20, QFont.Weight.Bold)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #ffffff;")
        text_layout.addWidget(name_label)

        version_label = QLabel("Version 0.50.0")
        version_font = QFont("Arial", 12)
        version_label.setFont(version_font)
        version_label.setStyleSheet("color: #808080;")
        text_layout.addWidget(version_label)

        header_layout.addLayout(text_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

    def _create_description(self, layout: QVBoxLayout):
        """Create description section"""
        desc_label = QLabel("Multi-database management tool")
        desc_font = QFont("Arial", 11)
        desc_label.setFont(desc_font)
        desc_label.setStyleSheet("color: #c0c0c0; padding: 10px 0;")
        layout.addWidget(desc_label)

    def _create_features(self, layout: QVBoxLayout):
        """Create features list"""
        features_group = QGroupBox("Fonctionnalités")
        features_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 11pt;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        features_layout = QVBoxLayout(features_group)
        features_layout.setSpacing(8)

        features = [
            "• Support multi-bases (SQL Server, MySQL, Postgres, SQLite)",
            "• Mise en forme automatique des requêtes avec 4 styles",
            "• Éditeur de requêtes avec analyses de distribution",
            "• Navigateur de fichiers + affichage multiformat (csv, json, ...)",
            "• Distribution de fichier d'une racine dans leur dossier Dataset",
            "• Scripts d'importation de fichiers dans des tables avec gestion du polymorphisme",
            "• Définition de jobs pour séquencer des scripts ou d'autres jobs",
            "• Orchestrateur de jobs multi-plateformes",
            "• Gestionnaire de requêtes enregistrées",
            "• Plusieurs thèmes + éditeur de thèmes",
            "• Multilingue + éditeur pour nouvelle traduction"
        ]

        for feature in features:
            feature_label = QLabel(feature)
            feature_label.setStyleSheet("color: #e0e0e0; padding-left: 10px;")
            feature_font = QFont("Arial", 10)
            feature_label.setFont(feature_font)
            features_layout.addWidget(feature_label)

        layout.addWidget(features_group)

    def _create_github_link(self, layout: QVBoxLayout):
        """Create GitHub link section"""
        github_layout = QHBoxLayout()
        github_layout.setSpacing(10)

        github_icon = QLabel("🔗")
        github_icon.setStyleSheet("font-size: 16pt;")
        github_layout.addWidget(github_icon)

        github_link = QLabel('<a href="https://github.com/Lestat2Lioncourt/data-forge-studio" style="color: #0078d4; text-decoration: none;">GitHub: Lestat2Lioncourt/data-forge-studio</a>')
        github_link.setOpenExternalLinks(True)
        github_link.setStyleSheet("font-size: 10pt;")
        github_link.linkActivated.connect(self._open_url)
        github_layout.addWidget(github_link)
        github_layout.addStretch()

        layout.addLayout(github_layout)

    def _create_support_section(self, layout: QVBoxLayout):
        """Create support/donation section"""
        support_group = QGroupBox("Soutenir le projet")
        support_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 11pt;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        support_layout = QVBoxLayout(support_group)
        support_layout.setSpacing(10)

        # Info text
        info_label = QLabel("Les donations volontaires soutiennent le développement du projet ❤️")
        info_label.setStyleSheet("color: #c0c0c0; padding: 5px 10px;")
        info_label.setWordWrap(True)
        info_font = QFont("Arial", 9)
        info_label.setFont(info_font)
        support_layout.addWidget(info_label)

        # Donation buttons grid
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(10)

        # GitHub Sponsors
        github_btn = self._create_donation_button(
            "💜 GitHub Sponsors",
            "#ea4aaa",
            self.DONATION_URLS["github_sponsors"]
        )
        buttons_layout.addWidget(github_btn, 0, 0)

        # Ko-fi
        kofi_btn = self._create_donation_button(
            "☕ Ko-fi",
            "#ff5e5b",
            self.DONATION_URLS["ko_fi"]
        )
        buttons_layout.addWidget(kofi_btn, 0, 1)

        # Buy Me a Coffee
        bmc_btn = self._create_donation_button(
            "☕ Buy Me a Coffee",
            "#ffdd00",
            self.DONATION_URLS["buy_me_coffee"],
            text_color="#000000"
        )
        buttons_layout.addWidget(bmc_btn, 1, 0)

        # PayPal
        paypal_btn = self._create_donation_button(
            "💰 PayPal",
            "#0070ba",
            self.DONATION_URLS["paypal"]
        )
        buttons_layout.addWidget(paypal_btn, 1, 1)

        # Liberapay
        liberapay_btn = self._create_donation_button(
            "💛 Liberapay",
            "#f6c915",
            self.DONATION_URLS["liberapay"],
            text_color="#000000"
        )
        buttons_layout.addWidget(liberapay_btn, 2, 0, 1, 2)  # Span 2 columns

        support_layout.addLayout(buttons_layout)
        layout.addWidget(support_group)

    def _create_donation_button(self, text: str, color: str, url: str, text_color: str = "#ffffff") -> QPushButton:
        """Create a styled donation button"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(40)

        # Store URL in button property
        btn.setProperty("donation_url", url)

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {self._adjust_color_brightness(color, 1.1)};
            }}
            QPushButton:pressed {{
                background-color: {self._adjust_color_brightness(color, 0.9)};
            }}
        """)

        btn.clicked.connect(lambda: self._open_url(url))
        return btn

    def _adjust_color_brightness(self, hex_color: str, factor: float) -> str:
        """Adjust color brightness for hover/press effects"""
        # Remove # if present
        hex_color = hex_color.lstrip('#')

        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Adjust brightness
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_footer(self, layout: QVBoxLayout):
        """Create copyright footer"""
        footer_label = QLabel("© 2024-2025 - MIT License")
        footer_label.setStyleSheet("color: #808080; padding: 15px 0 5px 0;")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_font = QFont("Arial", 9)
        footer_label.setFont(footer_font)
        layout.addWidget(footer_label)

    def _open_url(self, url: str):
        """Open URL in default browser"""
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))
        logger.info(f"Opening URL: {url}")
