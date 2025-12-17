"""
Theme Editor Frame - Edit and create custom themes with live preview
Simplified version with intuitive UX
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QLineEdit, QPushButton, QGroupBox, QInputDialog,
                                QMessageBox, QScrollArea, QSizePolicy,
                                QColorDialog, QApplication, QSplitter)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QColor

from ..managers.base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.theme_preview import ThemePreview
from ..widgets.dialog_helper import DialogHelper
from ..core.theme_bridge import ThemeBridge
from ..core.i18n_bridge import tr
from ...config.user_preferences import UserPreferences

# Path to icons
ICONS_PATH = Path(__file__).parent.parent / "assets" / "images"

# Path to custom themes
CUSTOM_THEMES_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig" / "themes"


# Palette structure with categories - simplified labels
PALETTE_CATEGORIES = {
    "window": {
        "name": "Fenetre",
        "properties": [
            ("TopBar_BG", "Barre titre - Fond"),
            ("TopBar_FG", "Barre titre - Texte"),
            ("MenuBar_BG", "Menu - Fond"),
            ("MenuBar_FG", "Menu - Texte"),
            ("StatusBar_BG", "Barre statut - Fond"),
            ("StatusBar_FG", "Barre statut - Texte"),
        ]
    },
    "frames": {
        "name": "Panneaux",
        "properties": [
            ("Frame_BG", "Fond"),
            ("Frame_FG", "Texte"),
            ("Frame_FG_Secondary", "Texte secondaire"),
        ]
    },
    "data": {
        "name": "Donnees",
        "properties": [
            ("Data_BG", "Fond"),
            ("Data_FG", "Texte"),
            ("Data_Border", "Bordure"),
        ]
    },
    "interactive": {
        "name": "Interactif",
        "properties": [
            ("Hover_BG", "Survol"),
            ("Selected_BG", "Selection - Fond"),
            ("Selected_FG", "Selection - Texte"),
            ("Accent", "Couleur accent"),
        ]
    },
    "semantic": {
        "name": "Messages",
        "properties": [
            ("Normal_FG", "Normal"),
            ("Success_FG", "Succes"),
            ("Warning_FG", "Avertissement"),
            ("Error_FG", "Erreur"),
            ("Info_FG", "Information"),
        ]
    },
    "tabs": {
        "name": "Onglets",
        "properties": [
            ("Tab_BG", "Fond"),
            ("Tab_FG", "Texte"),
            ("Tab_Selected_BG", "Selection - Fond"),
            ("Tab_Selected_FG", "Selection - Texte"),
            ("Tab_Hover_BG", "Survol"),
        ]
    },
}

# Default dark palette
DEFAULT_DARK_PALETTE = {
    "is_dark": True,
    "TopBar_BG": "#2b2b2b",
    "TopBar_FG": "#ffffff",
    "MenuBar_BG": "#3d3d3d",
    "MenuBar_FG": "#ffffff",
    "StatusBar_BG": "#2b2b2b",
    "StatusBar_FG": "#ffffff",
    "Frame_BG": "#252525",
    "Frame_FG": "#e0e0e0",
    "Frame_FG_Secondary": "#808080",
    "Data_BG": "#2d2d2d",
    "Data_FG": "#e0e0e0",
    "Data_Border": "#3d3d3d",
    "Hover_BG": "#383838",
    "Selected_BG": "#0078d7",
    "Selected_FG": "#ffffff",
    "Accent": "#0078d7",
    "Normal_FG": "#ffffff",
    "Success_FG": "#2ecc71",
    "Warning_FG": "#f39c12",
    "Error_FG": "#e74c3c",
    "Info_FG": "#3498db",
    "Tab_BG": "#252525",
    "Tab_FG": "#b0b0b0",
    "Tab_Selected_BG": "#2d2d2d",
    "Tab_Selected_FG": "#ffffff",
    "Tab_Hover_BG": "#383838",
}


class ColorPropertyEditor(QWidget):
    """Widget to edit a single color property - click to pick color."""

    color_changed = Signal(str, str)  # property_key, new_color

    def __init__(self, prop_key: str, prop_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.prop_key = prop_key
        self._color = "#808080"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(8)

        # Color box button - click to pick
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(24, 20)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.clicked.connect(self._pick_color)
        self.color_btn.setToolTip("Cliquez pour choisir une couleur")
        layout.addWidget(self.color_btn)

        # Label
        self.label = QLabel(prop_label)
        self.label.setMinimumWidth(140)
        layout.addWidget(self.label)

        # Hex display (read-only, clickable to copy)
        self.hex_label = QLabel()
        self.hex_label.setFixedWidth(70)
        self.hex_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hex_label.setToolTip("Cliquez pour copier")
        self.hex_label.mousePressEvent = self._copy_color
        self.hex_label.setStyleSheet("color: #808080;")
        layout.addWidget(self.hex_label)

        layout.addStretch()

    def set_color(self, color: str):
        """Set the color value."""
        self._color = color
        self._update_display()

    def get_color(self) -> str:
        """Get the current color value."""
        return self._color

    def _update_display(self):
        """Update the visual display of the color."""
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 1px solid #505050;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border: 2px solid #0078d7;
            }}
        """)
        self.hex_label.setText(self._color)

    def _pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(
            QColor(self._color), self,
            f"Couleur: {self.prop_key}"
        )
        if color.isValid():
            self._color = color.name()
            self._update_display()
            self.color_changed.emit(self.prop_key, self._color)

    def _copy_color(self, event):
        """Copy color hex code to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self._color)
        # Brief visual feedback
        self.hex_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self.hex_label.setStyleSheet("color: #808080;"))


class ThemeEditorFrame(QWidget):
    """
    Simplified theme editor with live preview.

    Layout:
    - Top: Theme name + Save button
    - Middle: Color properties (scrollable) | Preview
    - No confusing palette or mode options
    """

    theme_applied = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.theme_bridge = ThemeBridge.get_instance()
        self.user_prefs = UserPreferences.instance()

        # Current editing state
        self._current_palette: Dict[str, str] = dict(DEFAULT_DARK_PALETTE)
        self._current_theme_name = ""
        self._is_modified = False
        self._property_editors: Dict[str, ColorPropertyEditor] = {}

        self._setup_ui()
        self._create_property_editors()
        self._update_preview()

    def _setup_ui(self):
        """Setup the simplified UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === TOP: Theme name + Actions ===
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # Theme name
        name_label = QLabel("Nom du theme:")
        top_layout.addWidget(name_label)

        self.theme_name_input = QLineEdit()
        self.theme_name_input.setPlaceholderText("Entrez un nom pour votre theme...")
        self.theme_name_input.setMinimumWidth(200)
        self.theme_name_input.textChanged.connect(self._on_name_changed)
        top_layout.addWidget(self.theme_name_input)

        top_layout.addStretch()

        # Action buttons
        self.new_btn = QPushButton("Nouveau")
        self.new_btn.clicked.connect(self._new_theme)
        top_layout.addWidget(self.new_btn)

        self.open_btn = QPushButton("Ouvrir...")
        self.open_btn.clicked.connect(self._open_theme)
        top_layout.addWidget(self.open_btn)

        # Save button - prominent
        self.save_btn = QPushButton("Sauvegarder")
        self.save_btn.clicked.connect(self._save_theme)
        self.save_btn.setMinimumWidth(120)
        top_layout.addWidget(self.save_btn)

        # Apply button
        self.apply_btn = QPushButton("Appliquer")
        self.apply_btn.clicked.connect(self._apply_theme)
        self.apply_btn.setToolTip("Appliquer ce theme a l'application")
        top_layout.addWidget(self.apply_btn)

        main_layout.addLayout(top_layout)

        # === MIDDLE: Splitter with Properties and Preview ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Scrollable property editors
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setMinimumWidth(320)

        scroll_content = QWidget()
        self.editors_layout = QVBoxLayout(scroll_content)
        self.editors_layout.setContentsMargins(5, 5, 5, 5)
        self.editors_layout.setSpacing(8)

        scroll_area.setWidget(scroll_content)
        splitter.addWidget(scroll_area)

        # Right: Preview
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        preview_label = QLabel("Apercu en direct")
        preview_label.setStyleSheet("font-weight: bold; color: #808080;")
        preview_layout.addWidget(preview_label)

        self.theme_preview = ThemePreview()
        preview_layout.addWidget(self.theme_preview)
        preview_layout.addStretch()

        splitter.addWidget(preview_container)

        # Set splitter proportions (60% properties, 40% preview)
        splitter.setSizes([400, 300])

        main_layout.addWidget(splitter, 1)

        # Initial button states
        self._update_button_states()

    def _create_property_editors(self):
        """Create property editors for all palette properties."""
        # Clear existing
        for editor in self._property_editors.values():
            editor.setParent(None)
        self._property_editors.clear()

        # Clear layout
        while self.editors_layout.count():
            item = self.editors_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Create editors grouped by category
        for cat_key, cat_data in PALETTE_CATEGORIES.items():
            group = QGroupBox(cat_data["name"])
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(5, 8, 5, 5)
            group_layout.setSpacing(1)

            for prop_key, prop_label in cat_data["properties"]:
                editor = ColorPropertyEditor(prop_key, prop_label)
                editor.color_changed.connect(self._on_property_changed)

                # Set initial color
                if prop_key in self._current_palette:
                    editor.set_color(self._current_palette[prop_key])

                group_layout.addWidget(editor)
                self._property_editors[prop_key] = editor

            self.editors_layout.addWidget(group)

        self.editors_layout.addStretch()

    def _update_button_states(self):
        """Update button appearance based on state."""
        if self._is_modified:
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    font-weight: bold;
                    border: none;
                    padding: 6px 16px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1e88e5;
                }
            """)
            self.save_btn.setText("Sauvegarder *")
        else:
            self.save_btn.setStyleSheet("")
            self.save_btn.setText("Sauvegarder")

        # Disable save if no name
        has_name = bool(self.theme_name_input.text().strip())
        self.save_btn.setEnabled(has_name or self._is_modified)

    def _on_name_changed(self, text: str):
        """Handle theme name change."""
        self._current_theme_name = text.strip()
        self._set_modified(True)

    def _on_property_changed(self, prop_key: str, color: str):
        """Handle property color change."""
        self._current_palette[prop_key] = color
        self._set_modified(True)
        self._update_preview()

    def _set_modified(self, modified: bool):
        """Set modification state and update UI."""
        self._is_modified = modified
        self._update_button_states()

    def _update_preview(self):
        """Update the preview widget with current palette."""
        self.theme_preview.set_colors(self._current_palette)

    def _new_theme(self):
        """Create a new theme based on default."""
        if self._is_modified:
            reply = QMessageBox.question(
                self, "Nouveau theme",
                "Les modifications actuelles seront perdues. Continuer?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Reset to default
        self._current_palette = dict(DEFAULT_DARK_PALETTE)
        self._current_theme_name = ""
        self._set_modified(False)

        # Update UI
        self.theme_name_input.setText("")
        self.theme_name_input.setFocus()

        # Update editors
        for prop_key, editor in self._property_editors.items():
            if prop_key in self._current_palette:
                editor.set_color(self._current_palette[prop_key])

        self._update_preview()

    def _open_theme(self):
        """Open an existing theme for editing."""
        # Get available themes
        themes = {}

        # Built-in themes
        for theme_id, theme_data in self.theme_bridge.themes.items():
            if self.theme_bridge.is_minimal_theme(theme_id):
                themes[theme_id] = theme_data.get("name", theme_id)

        # Custom themes
        custom_themes = self._get_custom_themes()
        for theme_id, theme_name in custom_themes.items():
            themes[theme_id] = theme_name

        if not themes:
            DialogHelper.info("Aucun theme disponible.", parent=self)
            return

        # Show selection dialog
        theme_name, ok = QInputDialog.getItem(
            self, "Ouvrir un theme",
            "Selectionner un theme:",
            list(themes.values()),
            editable=False
        )

        if ok and theme_name:
            # Find theme key from name
            theme_key = None
            for key, name in themes.items():
                if name == theme_name:
                    theme_key = key
                    break

            if theme_key:
                self._load_theme(theme_key, theme_name)

    def _load_theme(self, theme_key: str, theme_name: str):
        """Load a theme into the editor."""
        # Check if it's a built-in minimal theme
        if theme_key in self.theme_bridge.themes:
            theme_data = self.theme_bridge.themes[theme_key]
            if "palette" in theme_data:
                self._current_palette = dict(theme_data["palette"])
            self._current_theme_name = theme_name
        else:
            # Try to load custom theme
            custom_path = CUSTOM_THEMES_PATH / f"{theme_key}.json"
            if custom_path.exists():
                try:
                    with open(custom_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._current_palette = dict(data.get("palette", {}))
                        self._current_theme_name = data.get("name", theme_key)
                except Exception as e:
                    DialogHelper.error(f"Erreur de chargement: {e}", parent=self)
                    return
            else:
                DialogHelper.error("Theme non trouve.", parent=self)
                return

        self._set_modified(False)

        # Update UI
        self.theme_name_input.setText(self._current_theme_name)

        # Update editors
        for prop_key, editor in self._property_editors.items():
            if prop_key in self._current_palette:
                editor.set_color(self._current_palette[prop_key])

        self._update_preview()

    def _save_theme(self):
        """Save the current theme."""
        name = self.theme_name_input.text().strip()

        if not name:
            # Prompt for name
            name, ok = QInputDialog.getText(
                self, "Nom du theme",
                "Entrez un nom pour ce theme:"
            )
            if not ok or not name.strip():
                return
            name = name.strip()
            self.theme_name_input.setText(name)
            self._current_theme_name = name

        # Create themes directory if needed
        CUSTOM_THEMES_PATH.mkdir(parents=True, exist_ok=True)

        # Generate theme ID from name
        theme_id = name.lower().replace(" ", "_").replace("'", "").replace("é", "e").replace("è", "e")

        # Save theme data
        theme_data = {
            "name": name,
            "type": "minimal",
            "palette": self._current_palette
        }

        theme_path = CUSTOM_THEMES_PATH / f"{theme_id}.json"
        try:
            with open(theme_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)

            self._set_modified(False)

            # Register the theme in the bridge
            self.theme_bridge.themes[theme_id] = theme_data
            self.theme_bridge._expanded_cache.pop(theme_id, None)

            DialogHelper.info(f"Theme sauvegarde!\n\nFichier: {theme_path.name}", parent=self)

        except Exception as e:
            DialogHelper.error(f"Erreur de sauvegarde: {e}", parent=self)

    def _apply_theme(self):
        """Apply the current theme to the application."""
        # Save first if modified
        if self._is_modified:
            reply = QMessageBox.question(
                self, "Appliquer le theme",
                "Sauvegarder les modifications avant d'appliquer?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                self._save_theme()
                if self._is_modified:  # Save failed
                    return

        name = self.theme_name_input.text().strip()
        if not name:
            DialogHelper.warning("Veuillez d'abord nommer et sauvegarder le theme.", parent=self)
            return

        # Generate theme ID
        theme_id = name.lower().replace(" ", "_").replace("'", "").replace("é", "e").replace("è", "e")

        # Ensure theme is registered
        if theme_id not in self.theme_bridge.themes:
            self.theme_bridge.themes[theme_id] = {
                "name": name,
                "type": "minimal",
                "palette": self._current_palette
            }

        # Clear cache to force regeneration
        self.theme_bridge._expanded_cache.pop(theme_id, None)

        # Apply globally
        global_qss = self.theme_bridge.generate_global_qss(theme_id)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(global_qss)
            self.theme_bridge.current_theme = theme_id

            # Save preference
            self.user_prefs.set("theme", theme_id)

            # Emit signal
            self.theme_applied.emit(theme_id)

            DialogHelper.info("Theme applique!", parent=self)

    def _get_custom_themes(self) -> Dict[str, str]:
        """Get list of custom themes from _AppConfig/themes/."""
        custom_themes = {}

        if CUSTOM_THEMES_PATH.exists():
            for theme_file in CUSTOM_THEMES_PATH.glob("*.json"):
                try:
                    with open(theme_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        theme_id = theme_file.stem
                        theme_name = data.get("name", theme_id)
                        custom_themes[theme_id] = f"{theme_name} (perso)"
                except Exception:
                    pass

        return custom_themes

    # === Methods expected by main_window ===

    def set_title(self, title: str):
        """Compatibility method."""
        pass

    def refresh(self):
        """Refresh the view."""
        self._update_preview()
