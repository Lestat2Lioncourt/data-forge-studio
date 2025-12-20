"""
Quick Theme Frame - Simplified theme creator using Color Patch system.

Allows users to create custom themes by overriding just 5-8 key colors
on top of a base theme (minimal_dark or minimal_light).
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QInputDialog,
    QColorDialog, QApplication, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ..widgets.theme_preview import ThemePreview
from ..widgets.dialog_helper import DialogHelper
from ..core.theme_bridge import ThemeBridge
from ..core.i18n_bridge import tr
from ...config.user_preferences import UserPreferences


# Path to custom themes
CUSTOM_THEMES_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig" / "themes"


# Quick theme color mappings (user-friendly name -> palette key)
QUICK_COLORS = [
    ("Accent", "Accent", "Couleur principale (boutons, liens, focus)"),
    ("Primary_BG", "Frame_BG", "Fond des panneaux"),
    ("Secondary_BG", "Data_BG", "Fond des grilles et arbres"),
    ("Text_Primary", "Normal_FG", "Texte principal"),
    ("Text_Secondary", "Frame_FG_Secondary", "Texte secondaire (grisé)"),
    ("Border", "Data_Border", "Bordures et séparateurs"),
    ("Success", "Success_FG", "Messages de succès"),
    ("Warning", "Warning_FG", "Messages d'avertissement"),
    ("Error", "Error_FG", "Messages d'erreur"),
    ("Info", "Info_FG", "Messages d'information"),
]

# Base themes available for patching
BASE_THEMES = {
    "minimal_dark": "Mode sombre",
    "minimal_light": "Mode clair",
}


class ColorPickerWidget(QWidget):
    """Single color picker row with label and color button."""

    color_changed = Signal(str, str)  # key, color

    def __init__(self, key: str, label: str, description: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.key = key
        self._color: Optional[str] = None
        self._is_overridden = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Color button
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(32, 24)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.clicked.connect(self._pick_color)
        layout.addWidget(self.color_btn)

        # Labels container
        labels_layout = QVBoxLayout()
        labels_layout.setSpacing(0)
        labels_layout.setContentsMargins(0, 0, 0, 0)

        self.name_label = QLabel(label)
        self.name_label.setStyleSheet("font-weight: bold;")
        labels_layout.addWidget(self.name_label)

        self.desc_label = QLabel(description)
        self.desc_label.setStyleSheet("color: #808080; font-size: 11px;")
        labels_layout.addWidget(self.desc_label)

        layout.addLayout(labels_layout, 1)

        # Hex value display
        self.hex_label = QLabel()
        self.hex_label.setFixedWidth(70)
        self.hex_label.setStyleSheet("color: #808080;")
        layout.addWidget(self.hex_label)

        # Reset button (only visible when overridden)
        self.reset_btn = QPushButton("×")
        self.reset_btn.setFixedSize(20, 20)
        self.reset_btn.setToolTip("Réinitialiser (utiliser la couleur de base)")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._reset_color)
        self.reset_btn.hide()
        layout.addWidget(self.reset_btn)

    def set_color(self, color: str, is_override: bool = False):
        """Set the displayed color."""
        self._color = color
        self._is_overridden = is_override
        self._update_display()

    def get_color(self) -> Optional[str]:
        """Get the current color if overridden, None otherwise."""
        return self._color if self._is_overridden else None

    def is_overridden(self) -> bool:
        """Check if this color is overridden."""
        return self._is_overridden

    def _update_display(self):
        """Update visual display."""
        if self._color:
            border_style = "2px solid #0078d7" if self._is_overridden else "1px solid #505050"
            self.color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._color};
                    border: {border_style};
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #0078d7;
                }}
            """)
            self.hex_label.setText(self._color)

        # Show/hide reset button
        self.reset_btn.setVisible(self._is_overridden)

        # Update name label style
        if self._is_overridden:
            self.name_label.setStyleSheet("font-weight: bold; color: #0078d7;")
        else:
            self.name_label.setStyleSheet("font-weight: bold;")

    def _pick_color(self):
        """Open color picker dialog."""
        initial = QColor(self._color) if self._color else QColor("#808080")
        color = QColorDialog.getColor(initial, self, f"Choisir: {self.key}")

        if color.isValid():
            self._color = color.name()
            self._is_overridden = True
            self._update_display()
            self.color_changed.emit(self.key, self._color)

    def _reset_color(self):
        """Reset to base theme color."""
        self._is_overridden = False
        self._update_display()
        self.color_changed.emit(self.key, "")  # Empty = reset


class QuickThemeFrame(QWidget):
    """
    Simplified theme creator using Color Patch system.

    User selects a base theme and overrides only the colors they want.
    Saves as a "patch" theme that references the base.
    """

    theme_applied = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.theme_bridge = ThemeBridge.get_instance()
        self.user_prefs = UserPreferences.instance()

        # Current state
        self._base_theme = "minimal_dark"
        self._overrides: Dict[str, str] = {}
        self._theme_name = ""
        self._color_pickers: Dict[str, ColorPickerWidget] = {}

        self._setup_ui()
        self._load_base_palette()

    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # === Header ===
        header_label = QLabel("Créateur de thème rapide")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header_label)

        desc_label = QLabel(
            "Créez un thème personnalisé en modifiant seulement les couleurs essentielles.\n"
            "Les autres couleurs seront dérivées automatiquement."
        )
        desc_label.setStyleSheet("color: #808080;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # === Base Theme Selection ===
        base_group = QGroupBox("Thème de base")
        base_layout = QHBoxLayout(base_group)

        self.base_combo = QComboBox()
        for theme_id, theme_name in BASE_THEMES.items():
            self.base_combo.addItem(theme_name, theme_id)
        self.base_combo.currentIndexChanged.connect(self._on_base_changed)
        base_layout.addWidget(self.base_combo)
        base_layout.addStretch()

        layout.addWidget(base_group)

        # === Color Overrides ===
        colors_group = QGroupBox("Couleurs à personnaliser (optionnel)")
        colors_layout = QVBoxLayout(colors_group)
        colors_layout.setSpacing(2)

        for user_key, palette_key, description in QUICK_COLORS:
            picker = ColorPickerWidget(user_key, user_key.replace("_", " "), description)
            picker.color_changed.connect(self._on_color_changed)
            colors_layout.addWidget(picker)
            self._color_pickers[user_key] = picker

        layout.addWidget(colors_group)

        # === Preview ===
        preview_group = QGroupBox("Aperçu")
        preview_layout = QVBoxLayout(preview_group)

        self.theme_preview = ThemePreview()
        self.theme_preview.setMinimumHeight(150)
        preview_layout.addWidget(self.theme_preview)

        layout.addWidget(preview_group)

        # === Actions ===
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.reset_btn = QPushButton("Réinitialiser tout")
        self.reset_btn.clicked.connect(self._reset_all)
        actions_layout.addWidget(self.reset_btn)

        actions_layout.addStretch()

        self.save_btn = QPushButton("Sauvegarder comme...")
        self.save_btn.clicked.connect(self._save_theme)
        self.save_btn.setMinimumWidth(140)
        actions_layout.addWidget(self.save_btn)

        self.apply_btn = QPushButton("Appliquer")
        self.apply_btn.clicked.connect(self._apply_theme)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1e88e5;
            }
        """)
        actions_layout.addWidget(self.apply_btn)

        layout.addLayout(actions_layout)

        # Spacer
        layout.addStretch()

    def _on_base_changed(self, index: int):
        """Handle base theme change."""
        self._base_theme = self.base_combo.currentData()
        self._load_base_palette()
        self._update_preview()

    def _on_color_changed(self, key: str, color: str):
        """Handle color override change."""
        if color:
            self._overrides[key] = color
        else:
            self._overrides.pop(key, None)
            # Reload base color for this key
            self._load_base_color(key)

        self._update_preview()

    def _load_base_palette(self):
        """Load colors from base theme into pickers."""
        # Get base theme palette
        if self._base_theme in self.theme_bridge.themes:
            theme_data = self.theme_bridge.themes[self._base_theme]
            palette = theme_data.get("palette", {})
        else:
            palette = {}

        # Update all color pickers with base values
        for user_key, palette_key, _ in QUICK_COLORS:
            picker = self._color_pickers.get(user_key)
            if picker:
                base_color = palette.get(palette_key, "#808080")
                # Check if we have an override
                if user_key in self._overrides:
                    picker.set_color(self._overrides[user_key], is_override=True)
                else:
                    picker.set_color(base_color, is_override=False)

        self._update_preview()

    def _load_base_color(self, key: str):
        """Reload a single color from base theme."""
        if self._base_theme in self.theme_bridge.themes:
            theme_data = self.theme_bridge.themes[self._base_theme]
            palette = theme_data.get("palette", {})

            # Find the palette key for this user key
            for user_key, palette_key, _ in QUICK_COLORS:
                if user_key == key:
                    base_color = palette.get(palette_key, "#808080")
                    picker = self._color_pickers.get(key)
                    if picker:
                        picker.set_color(base_color, is_override=False)
                    break

    def _get_effective_palette(self) -> Dict[str, str]:
        """Get the effective palette (base + overrides)."""
        # Start with base theme palette
        if self._base_theme in self.theme_bridge.themes:
            theme_data = self.theme_bridge.themes[self._base_theme]
            palette = dict(theme_data.get("palette", {}))
        else:
            palette = {}

        # Apply overrides (map user keys to palette keys)
        for user_key, palette_key, _ in QUICK_COLORS:
            if user_key in self._overrides:
                palette[palette_key] = self._overrides[user_key]

        return palette

    def _update_preview(self):
        """Update the preview widget."""
        palette = self._get_effective_palette()
        self.theme_preview.set_colors(palette)

    def _reset_all(self):
        """Reset all overrides."""
        self._overrides.clear()
        self._load_base_palette()
        self._update_preview()

    def _save_theme(self):
        """Save the current theme as a patch."""
        # Ask for name
        name, ok = QInputDialog.getText(
            self, "Sauvegarder le thème",
            "Nom du thème:"
        )
        if not ok or not name.strip():
            return

        name = name.strip()
        self._theme_name = name

        # Generate theme ID
        theme_id = name.lower().replace(" ", "_").replace("'", "")
        for char in "éèêë":
            theme_id = theme_id.replace(char, "e")
        for char in "àâä":
            theme_id = theme_id.replace(char, "a")

        # Prepare patch data
        patch_data = {
            "name": name,
            "type": "patch",
            "base": self._base_theme,
            "overrides": {}
        }

        # Map user keys to palette keys for storage
        for user_key, palette_key, _ in QUICK_COLORS:
            if user_key in self._overrides:
                patch_data["overrides"][palette_key] = self._overrides[user_key]

        # Save to file
        CUSTOM_THEMES_PATH.mkdir(parents=True, exist_ok=True)
        theme_path = CUSTOM_THEMES_PATH / f"{theme_id}.json"

        try:
            with open(theme_path, 'w', encoding='utf-8') as f:
                json.dump(patch_data, f, indent=2, ensure_ascii=False)

            # Register in theme bridge
            # For patch themes, we need to expand and store as minimal
            self._register_patch_theme(theme_id, patch_data)

            # Apply the saved theme and save preference
            self._apply_saved_theme(theme_id)

            DialogHelper.info(
                f"Thème '{name}' sauvegardé et appliqué!",
                parent=self
            )

        except Exception as e:
            DialogHelper.error(f"Erreur de sauvegarde: {e}", parent=self)

    def _register_patch_theme(self, theme_id: str, patch_data: Dict):
        """Register a patch theme in the bridge."""
        # Get base palette
        base_id = patch_data.get("base", "minimal_dark")
        if base_id in self.theme_bridge.themes:
            base_palette = dict(self.theme_bridge.themes[base_id].get("palette", {}))
        else:
            base_palette = {}

        # Apply overrides
        for key, value in patch_data.get("overrides", {}).items():
            base_palette[key] = value

        # Register as minimal theme (will be expanded on use)
        self.theme_bridge.themes[theme_id] = {
            "name": patch_data.get("name", theme_id),
            "type": "minimal",
            "palette": base_palette
        }

        # Clear any cached expansion
        self.theme_bridge._expanded_cache.pop(theme_id, None)

    def _apply_saved_theme(self, theme_id: str):
        """Apply a saved theme and persist as user preference."""
        try:
            # Generate and apply QSS
            global_qss = self.theme_bridge.generate_global_qss(theme_id)
            app = QApplication.instance()
            if app:
                app.setStyleSheet(global_qss)
                self.theme_bridge.current_theme = theme_id

                # Save as user preference (persists across restarts)
                self.user_prefs.set("theme", theme_id)

                # Notify observers
                theme_colors = self.theme_bridge.get_theme_colors(theme_id)
                self.theme_bridge._notify_observers(theme_colors)

                # Emit signal for parent to update theme combo
                self.theme_applied.emit(theme_id)

        except Exception as e:
            DialogHelper.error(f"Erreur d'application: {e}", parent=self)

    def _apply_theme(self):
        """Apply the current color patch as a temporary theme."""
        # Generate effective palette
        palette = self._get_effective_palette()

        # Create temporary theme ID
        temp_id = "_quick_preview"

        # Register temporarily
        self.theme_bridge.themes[temp_id] = {
            "name": "Quick Theme Preview",
            "type": "minimal",
            "palette": palette
        }

        # Clear cache
        self.theme_bridge._expanded_cache.pop(temp_id, None)

        # Apply globally
        try:
            global_qss = self.theme_bridge.generate_global_qss(temp_id)
            app = QApplication.instance()
            if app:
                app.setStyleSheet(global_qss)
                self.theme_bridge.current_theme = temp_id

                # Notify observers
                theme_colors = self.theme_bridge.get_theme_colors(temp_id)
                self.theme_bridge._notify_observers(theme_colors)

                self.theme_applied.emit(temp_id)

        except Exception as e:
            DialogHelper.error(f"Erreur d'application: {e}", parent=self)

    def load_patch_theme(self, theme_id: str):
        """Load an existing patch theme for editing."""
        theme_path = CUSTOM_THEMES_PATH / f"{theme_id}.json"
        if not theme_path.exists():
            return False

        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data.get("type") != "patch":
                return False

            # Set base theme
            base = data.get("base", "minimal_dark")
            idx = self.base_combo.findData(base)
            if idx >= 0:
                self.base_combo.setCurrentIndex(idx)
            self._base_theme = base

            # Load overrides (map palette keys back to user keys)
            self._overrides.clear()
            overrides = data.get("overrides", {})

            for user_key, palette_key, _ in QUICK_COLORS:
                if palette_key in overrides:
                    self._overrides[user_key] = overrides[palette_key]

            self._theme_name = data.get("name", theme_id)

            # Update UI
            self._load_base_palette()
            self._update_preview()

            return True

        except Exception:
            return False

    # === Compatibility methods ===

    def set_title(self, title: str):
        """Compatibility method."""
        pass

    def refresh(self):
        """Refresh the view."""
        self._load_base_palette()
        self._update_preview()
