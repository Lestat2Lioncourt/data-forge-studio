"""
Settings Frame - Application settings and preferences
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox,
                               QPushButton, QGroupBox, QLabel)
from PySide6.QtCore import Qt

from ..core.theme_bridge import ThemeBridge
from ..core.i18n_bridge import I18nBridge, tr


class SettingsFrame(QWidget):
    """Settings and preferences frame."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_bridge = ThemeBridge.get_instance()
        self.i18n_bridge = I18nBridge.instance()
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(tr("menu_preferences"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Theme settings group
        theme_group = QGroupBox(tr("settings_theme"))
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        themes = self.theme_bridge.get_available_themes()
        for theme_id, theme_name in themes.items():
            self.theme_combo.addItem(theme_name, theme_id)

        # Set current theme
        current_theme = self.theme_bridge.current_theme
        index = self.theme_combo.findData(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        theme_layout.addRow(tr("settings_select_theme"), self.theme_combo)
        layout.addWidget(theme_group)

        # Language settings group
        lang_group = QGroupBox(tr("settings_language"))
        lang_layout = QFormLayout(lang_group)

        self.lang_combo = QComboBox()
        languages = self.i18n_bridge.get_available_languages()
        for lang_code, lang_name in languages.items():
            self.lang_combo.addItem(lang_name, lang_code)

        # Set current language
        current_lang = self.i18n_bridge.get_current_language()
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)

        lang_layout.addRow(tr("settings_select_language"), self.lang_combo)
        layout.addWidget(lang_group)

        # Apply button
        apply_btn = QPushButton(tr("btn_apply"))
        apply_btn.clicked.connect(self._apply_settings)
        apply_btn.setMinimumWidth(120)
        layout.addWidget(apply_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: green; padding: 10px;")
        layout.addWidget(self.status_label)

        # Add stretch to push everything to the top
        layout.addStretch()

    def _apply_settings(self):
        """Apply selected settings."""
        # Get window reference from parent hierarchy
        window = self._find_template_window()

        # Apply theme
        theme_id = self.theme_combo.currentData()
        if window:
            self.theme_bridge.apply_theme(window, theme_id)

        # Apply language
        lang_code = self.lang_combo.currentData()
        self.i18n_bridge.set_language(lang_code)

        # Show success message
        self.status_label.setText(tr("settings_applied"))

        # Clear status after 3 seconds
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

    def _find_template_window(self):
        """Find the TemplateWindow in parent hierarchy."""
        parent = self.parent()
        while parent is not None:
            # Look for stacked widget's parent which should have window attribute
            if hasattr(parent, 'window'):
                return parent.window
            parent = parent.parent()
        return None
