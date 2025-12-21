"""
Settings Frame - Unified preferences editor
Language and Theme have the same pattern: dropdown + editor + actions
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Any, Dict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                               QPushButton, QLabel, QGroupBox, QCheckBox,
                               QScrollArea, QTableWidget, QTableWidgetItem,
                               QHeaderView, QSplitter, QInputDialog,
                               QMessageBox, QApplication)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ..managers.base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.theme_preview import ThemePreview
from ..widgets.color_property_row import ColorPropertyRow
from ..widgets.palette_widget import PaletteWidget
from ..core.theme_bridge import ThemeBridge
from ..core.i18n_bridge import I18nBridge, tr
from ...config.i18n import i18n_manager
from ...config.user_preferences import UserPreferences
from .quick_theme_frame import QuickThemeFrame

logger = logging.getLogger(__name__)

# Path to icons
ICONS_PATH = Path(__file__).parent.parent / "assets" / "images"

# Paths to config files
LANGUAGES_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig" / "languages"
THEMES_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig" / "themes"

# Theme palette categories (user-friendly names)
THEME_CATEGORIES = {
    "Barre de titre": ["TopBar_BG", "TopBar_FG"],
    "Menu": ["MenuBar_BG", "MenuBar_FG", "MenuBar_Hover_BG", "MenuBar_Hover_FG",
             "MenuBar_Selected_BG", "MenuBar_Selected_FG"],
    "Sous-menus": ["DD_Menu_BG", "DD_Menu_FG", "DD_Menu_Hover_BG", "DD_Menu_Hover_FG",
                   "DD_Menu_Selected_BG", "DD_Menu_Selected_FG"],
    "Barre d'outils": ["ToolbarBtn_BG", "ToolbarBtn_FG", "ToolbarBtn_Hover_BG",
                       "ToolbarBtn_Hover_FG", "ToolbarBtn_Pressed_BG", "ToolbarBtn_Border"],
    "Boutons (panneaux)": ["Button_BG", "Button_FG", "Button_Hover_BG", "Button_Hover_FG",
                           "Button_Pressed_BG", "Button_Border"],
    "Barre d'état": ["StatusBar_BG", "StatusBar_FG"],
    "Panneaux": ["Frame_BG", "Frame_FG", "Frame_FG_Secondary", "Frame_Border_Radius"],
    "Séparateurs": ["Splitter_BG", "Splitter_Hover_BG"],
    "Grilles": ["Grid_Header_BG", "Grid_Header_FG",
                "Grid_Line1_BG", "Grid_Line1_FG",
                "Grid_Line2_BG", "Grid_Line2_FG",
                "Data_Border"],
    "Arborescence": ["Tree_BG", "Tree_FG",
                     "Tree_Header_BG", "Tree_Header_FG",
                     "Tree_Line1_BG", "Tree_Line1_FG",
                     "Tree_Line2_BG", "Tree_Line2_FG",
                     "Tree_Branch_Color"],
    "Sélection": ["Hover_BG", "Selected_BG", "Selected_FG", "Accent"],
    "Messages (log)": ["Log_BG", "Normal_FG", "Success_FG", "Warning_FG", "Error_FG", "Info_FG"],
    "Onglets": ["Tab_BG", "Tab_FG", "Tab_Selected_BG", "Tab_Selected_FG", "Tab_Hover_BG"],
}


class SettingsFrame(BaseManagerView):
    """Unified settings editor with consistent pattern for Language and Theme."""

    debug_borders_changed = Signal(bool)
    theme_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        self.theme_bridge = ThemeBridge.get_instance()
        self.i18n_bridge = I18nBridge.instance()
        self.user_prefs = UserPreferences.instance()

        # Current editing state
        self._current_lang_data: Dict[str, str] = {}
        self._current_theme_data: Dict[str, str] = {}
        self._theme_color_rows: Dict[str, ColorPropertyRow] = {}
        self._is_lang_modified = False
        self._is_theme_modified = False
        self._selected_category = None  # For theme category filtering

        super().__init__(parent, title="Preferences", enable_details_panel=False)

        self._setup_toolbar()
        self._setup_content()
        self._register_theme_observer()
        self.refresh()

    def _get_tree_columns(self) -> List[str]:
        return ["Preferences"]

    def _setup_toolbar(self):
        """Minimal toolbar."""
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button(tr("btn_refresh"), self.refresh, icon="refresh.png")
        self._replace_toolbar(toolbar_builder)

    def _setup_content(self):
        """Setup the right panel that changes based on selection."""
        # Container for all editors
        self.editors_container = QWidget()
        self.editors_layout = QVBoxLayout(self.editors_container)
        self.editors_layout.setContentsMargins(0, 0, 0, 0)

        # Language editor
        self.language_editor = self._create_language_editor()
        self.editors_layout.addWidget(self.language_editor)
        self.language_editor.hide()

        # Theme editor
        self.theme_editor = self._create_theme_editor()
        self.editors_layout.addWidget(self.theme_editor)
        self.theme_editor.hide()

        # Debug editor
        self.debug_editor = self._create_debug_editor()
        self.editors_layout.addWidget(self.debug_editor)
        self.debug_editor.hide()

        # Quick theme editor
        self.quick_theme_editor = QuickThemeFrame()
        self.quick_theme_editor.theme_applied.connect(self._on_quick_theme_applied)
        self.editors_layout.addWidget(self.quick_theme_editor)
        self.quick_theme_editor.hide()

        # Placeholder when nothing selected
        self.placeholder = QLabel(tr("settings_select_option"))
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: #808080; font-style: italic;")
        self.editors_layout.addWidget(self.placeholder)

        self.content_layout.addWidget(self.editors_container)

    def _create_language_editor(self) -> QWidget:
        """Create language editor: dropdown + translations table + actions."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # === TOP: Dropdown ===
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel(tr("settings_active_language")))

        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(200)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_selected)
        top_layout.addWidget(self.lang_combo)
        top_layout.addStretch()

        # Actions
        self.lang_duplicate_btn = QPushButton(tr("settings_duplicate"))
        self.lang_duplicate_btn.clicked.connect(self._duplicate_language)
        top_layout.addWidget(self.lang_duplicate_btn)

        self.lang_save_btn = QPushButton(tr("btn_save"))
        self.lang_save_btn.clicked.connect(self._save_language)
        top_layout.addWidget(self.lang_save_btn)

        layout.addLayout(top_layout)

        # === MIDDLE: Translations table ===
        self.lang_table = QTableWidget()
        self.lang_table.setColumnCount(2)
        self.lang_table.setHorizontalHeaderLabels(["Cle", "Traduction"])
        self.lang_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.lang_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.lang_table.setAlternatingRowColors(True)
        self.lang_table.cellChanged.connect(self._on_translation_changed)
        layout.addWidget(self.lang_table, 1)

        # Status
        self.lang_status = QLabel("")
        self.lang_status.setStyleSheet("color: #2ecc71;")
        layout.addWidget(self.lang_status)

        return widget

    def _create_theme_editor(self) -> QWidget:
        """Create theme editor: dropdown + categories + colors + palette + preview + actions."""
        widget = QWidget()
        # Store reference for dynamic styling
        self._theme_editor_widget = widget
        # Apply theme-based styling
        self._apply_theme_editor_style()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # === TOP: Dropdown + Actions ===
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel(tr("settings_active_theme")))

        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(200)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selected)
        top_layout.addWidget(self.theme_combo)
        top_layout.addStretch()

        # Actions
        self.theme_duplicate_btn = QPushButton(tr("settings_duplicate"))
        self.theme_duplicate_btn.clicked.connect(self._duplicate_theme)
        top_layout.addWidget(self.theme_duplicate_btn)

        self.theme_save_btn = QPushButton(tr("btn_save"))
        self.theme_save_btn.clicked.connect(self._save_theme)
        top_layout.addWidget(self.theme_save_btn)

        self.theme_apply_btn = QPushButton(tr("btn_apply"))
        self.theme_apply_btn.clicked.connect(self._apply_theme)
        top_layout.addWidget(self.theme_apply_btn)

        layout.addLayout(top_layout)

        # === MIDDLE: Splitter with categories, colors and palette/preview ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Category tree removed - categories are now selected from the left panel tree

        # Middle: Color properties (scrollable)
        colors_scroll = QScrollArea()
        colors_scroll.setWidgetResizable(True)
        colors_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.colors_container = QWidget()
        self.colors_layout = QVBoxLayout(self.colors_container)
        self.colors_layout.setContentsMargins(5, 5, 5, 5)
        self.colors_layout.setSpacing(2)
        colors_scroll.setWidget(self.colors_container)
        splitter.addWidget(colors_scroll)

        # Right: Palette + Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        self.palette_widget = PaletteWidget()
        self.palette_widget.color_selected.connect(self._on_palette_color_selected)
        right_layout.addWidget(self.palette_widget)

        preview_label = QLabel(tr("settings_preview"))
        preview_label.setStyleSheet("font-weight: bold; font-size: 9pt; color: #808080;")
        right_layout.addWidget(preview_label)

        self.theme_preview = ThemePreview()
        self.theme_preview.setMaximumHeight(250)
        right_layout.addWidget(self.theme_preview)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([400, 200])  # Colors, Palette/Preview (category tree removed)

        layout.addWidget(splitter, 1)

        # Status
        self.theme_status = QLabel("")
        self.theme_status.setStyleSheet("color: #2ecc71;")
        layout.addWidget(self.theme_status)

        # Track selected category
        self._selected_category = None

        return widget


    def _update_color_display(self):
        """Update which color rows are visible based on selected category."""
        if not hasattr(self, '_theme_color_rows'):
            return

        # Get keys for selected category (None = show all)
        if self._selected_category is None:
            visible_keys = set(self._theme_color_rows.keys())
        else:
            visible_keys = set(THEME_CATEGORIES.get(self._selected_category, []))

        # Show/hide rows
        for key, row in self._theme_color_rows.items():
            row.setVisible(key in visible_keys)

    def _create_debug_editor(self) -> QWidget:
        """Create debug options editor."""
        colors = self.theme_bridge.get_theme_colors()
        warning_color = colors.get("warning_fg", "#f39c12")

        widget = QGroupBox("Debug")
        widget.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {warning_color};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
        """)
        layout = QVBoxLayout(widget)

        self.objects_borders_cb = QCheckBox("Afficher les contours de debug sur les composants UI")
        current_value = self.user_prefs.get("objects_borders", False)
        self.objects_borders_cb.setChecked(current_value)
        layout.addWidget(self.objects_borders_cb)

        apply_btn = QPushButton(tr("btn_apply"))
        apply_btn.clicked.connect(self._apply_debug)
        apply_btn.setMinimumWidth(120)
        layout.addWidget(apply_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.debug_status = QLabel("")
        self.debug_status.setStyleSheet(f"color: {warning_color};")
        layout.addWidget(self.debug_status)

        layout.addStretch()
        return widget

    def _register_theme_observer(self):
        """Register as observer for theme changes."""
        try:
            self.theme_bridge.register_observer(self._on_theme_changed)
        except AttributeError as e:
            logger.debug(f"Could not register theme observer: {e}")

    def _on_theme_changed(self, theme_colors: Dict[str, str]):
        """Called when theme changes - update editor styling."""
        try:
            self._apply_theme_editor_style()
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Error during theme update: {e}")

    def _apply_theme_editor_style(self):
        """Apply dynamic theme colors to theme editor widget."""
        if not hasattr(self, '_theme_editor_widget'):
            return

        colors = self.theme_bridge.get_theme_colors()

        # Get theme colors with fallbacks
        bg = colors.get('panel_bg', '#2d2d2d')
        fg = colors.get('text_primary', '#e0e0e0')
        data_bg = colors.get('data_bg', '#252525')
        border = colors.get('border_color', '#505050')
        hover = colors.get('hover_bg', '#4d4d4d')
        selected = colors.get('selected_bg', '#0078d7')
        accent = colors.get('accent', '#0078d7')
        # Button colors
        button_bg = colors.get('button_bg', data_bg)
        button_fg = colors.get('button_fg', fg)
        button_border = colors.get('button_border', border)
        button_hover_bg = colors.get('button_hover_bg', hover)
        button_hover_fg = colors.get('button_hover_fg', fg)
        button_pressed_bg = colors.get('button_pressed_bg', selected)

        self._theme_editor_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                color: {fg};
            }}
            QPushButton {{
                background-color: {button_bg};
                color: {button_fg};
                border: 1px solid {button_border};
                padding: 5px 12px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {button_hover_bg};
                color: {button_hover_fg};
            }}
            QPushButton:pressed {{
                background-color: {button_pressed_bg};
            }}
            QComboBox {{
                background-color: {data_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 4px 8px;
                border-radius: 3px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {data_bg};
                color: {fg};
                selection-background-color: {accent};
            }}
            QScrollArea {{
                background-color: {bg};
                border: none;
            }}
            QLineEdit {{
                background-color: {data_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 3px;
                border-radius: 2px;
            }}
        """)

    def _load_items(self):
        """Load preferences tree."""
        category_icon = QIcon(str(ICONS_PATH / "Category.png"))
        option_icon = QIcon(str(ICONS_PATH / "option.png"))

        # Preferences section
        prefs_parent = self.tree_view.add_item(
            parent=None,
            text=["Preferences"],
            data={"type": "category", "name": "preferences"}
        )
        prefs_parent.setIcon(0, category_icon)

        lang_item = self.tree_view.add_item(
            parent=prefs_parent,
            text=["Langue"],
            data={"type": "language"}
        )
        lang_item.setIcon(0, option_icon)

        # Quick theme (simplified Color Patch system)
        quick_theme_item = self.tree_view.add_item(
            parent=prefs_parent,
            text=["Theme rapide"],
            data={"type": "quick_theme"}
        )
        quick_theme_item.setIcon(0, option_icon)

        theme_item = self.tree_view.add_item(
            parent=prefs_parent,
            text=["Theme avance"],
            data={"type": "theme", "category": None}  # None = show all categories
        )
        theme_item.setIcon(0, option_icon)

        # Add theme categories as children
        for category_name in THEME_CATEGORIES.keys():
            cat_item = self.tree_view.add_item(
                parent=theme_item,
                text=[category_name],
                data={"type": "theme", "category": category_name}
            )
            cat_item.setIcon(0, option_icon)

        # Debug section
        debug_parent = self.tree_view.add_item(
            parent=None,
            text=["Debug"],
            data={"type": "category", "name": "debug"}
        )
        debug_parent.setIcon(0, category_icon)

        borders_item = self.tree_view.add_item(
            parent=debug_parent,
            text=["Contours"],
            data={"type": "debug_borders"}
        )
        borders_item.setIcon(0, option_icon)

        self.tree_view.tree.expandAll()

        # Populate dropdowns
        self._populate_lang_combo()
        self._populate_theme_combo()

    def _populate_lang_combo(self):
        """Populate language dropdown."""
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()

        languages = self.i18n_bridge.get_available_languages()
        for lang_code, lang_name in languages.items():
            self.lang_combo.addItem(f"{lang_name} ({lang_code})", lang_code)

        current = self.i18n_bridge.get_current_language()
        idx = self.lang_combo.findData(current)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)

        self.lang_combo.blockSignals(False)
        self._load_language_data(current)

    def _populate_theme_combo(self):
        """Populate theme dropdown."""
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()

        # Built-in themes
        themes = self.theme_bridge.get_available_themes()
        for theme_id, theme_name in themes.items():
            self.theme_combo.addItem(theme_name, theme_id)

        # Custom themes
        if THEMES_PATH.exists():
            for f in THEMES_PATH.glob("*.json"):
                theme_id = f.stem
                if theme_id not in themes:
                    try:
                        with open(f, 'r', encoding='utf-8') as file:
                            data = json.load(file)
                            name = data.get("name", theme_id)
                            self.theme_combo.addItem(f"{name} (perso)", theme_id)
                    except (json.JSONDecodeError, OSError) as e:
                        logger.warning(f"Could not load theme file {f}: {e}")

        current = self.theme_bridge.current_theme
        idx = self.theme_combo.findData(current)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        self.theme_combo.blockSignals(False)
        self._load_theme_data(current)

    def _display_item(self, item_data: Any):
        """Show appropriate editor based on selection."""
        if not isinstance(item_data, dict):
            return

        option_type = item_data.get("type", "")

        # Hide all
        self.language_editor.hide()
        self.theme_editor.hide()
        self.debug_editor.hide()
        self.quick_theme_editor.hide()
        self.placeholder.hide()

        if option_type == "language":
            self.language_editor.show()
        elif option_type == "quick_theme":
            self.quick_theme_editor.show()
        elif option_type == "theme":
            self.theme_editor.show()
            # Apply category filter from tree selection
            category = item_data.get("category")
            self._selected_category = category
            self._update_color_display()
        elif option_type == "debug_borders":
            self.debug_editor.show()
        else:
            self.placeholder.show()

    # === LANGUAGE METHODS ===

    def _on_lang_selected(self, index: int):
        """Handle language selection change."""
        lang_code = self.lang_combo.currentData()
        if lang_code:
            self._load_language_data(lang_code)
            # Apply language
            self.i18n_bridge.set_language(lang_code)

    def _load_language_data(self, lang_code: str):
        """Load language translations into table."""
        # Get translations (try external file first, then built-in)
        translations = {}

        lang_file = LANGUAGES_PATH / f"{lang_code}.json"
        if lang_file.exists():
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load language file {lang_file}: {e}")

        if not translations:
            # Get from i18n manager built-in (core translations)
            translations = dict(i18n_manager._core.get(lang_code, {}))

        self._current_lang_data = translations
        self._is_lang_modified = False
        self._update_lang_save_btn()

        # Populate table
        self.lang_table.blockSignals(True)
        self.lang_table.setRowCount(len(translations))

        for row, (key, value) in enumerate(sorted(translations.items())):
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.lang_table.setItem(row, 0, key_item)

            value_item = QTableWidgetItem(str(value))
            self.lang_table.setItem(row, 1, value_item)

        self.lang_table.blockSignals(False)

    def _on_translation_changed(self, row: int, col: int):
        """Handle translation edit."""
        if col == 1:  # Only value column is editable
            key = self.lang_table.item(row, 0).text()
            value = self.lang_table.item(row, 1).text()
            self._current_lang_data[key] = value
            self._is_lang_modified = True
            self._update_lang_save_btn()

    def _update_lang_save_btn(self):
        """Update save button style."""
        if self._is_lang_modified:
            self.lang_save_btn.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
            self.lang_save_btn.setText(tr("btn_save") + " *")
        else:
            self.lang_save_btn.setStyleSheet("")
            self.lang_save_btn.setText(tr("btn_save"))

    def _duplicate_language(self):
        """Duplicate current language."""
        current = self.lang_combo.currentData()
        name, ok = QInputDialog.getText(self, "Dupliquer la langue",
                                        "Code de la nouvelle langue (ex: es, de):")
        if ok and name:
            name = name.strip().lower()
            if not name.isalpha() or len(name) != 2:
                DialogHelper.error("Le code doit etre 2 lettres (ex: es, de)", parent=self)
                return

            LANGUAGES_PATH.mkdir(parents=True, exist_ok=True)
            new_file = LANGUAGES_PATH / f"{name}.json"

            if new_file.exists():
                DialogHelper.error(f"La langue '{name}' existe deja.", parent=self)
                return

            # Save copy
            with open(new_file, 'w', encoding='utf-8') as f:
                json.dump(self._current_lang_data, f, indent=2, ensure_ascii=False)

            DialogHelper.info(f"Langue '{name}' creee. Rechargez l'application.", parent=self)
            self._populate_lang_combo()

    def _save_language(self):
        """Save current language to file."""
        lang_code = self.lang_combo.currentData()
        LANGUAGES_PATH.mkdir(parents=True, exist_ok=True)

        lang_file = LANGUAGES_PATH / f"{lang_code}.json"
        try:
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(self._current_lang_data, f, indent=2, ensure_ascii=False)

            self._is_lang_modified = False
            self._update_lang_save_btn()
            self.lang_status.setText(tr("settings_saved"))
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self.lang_status.setText(""))
        except Exception as e:
            DialogHelper.error(f"Erreur: {e}", parent=self)

    # === THEME METHODS ===

    def _ensure_palette_keys(self, palette: Dict[str, str]) -> Dict[str, str]:
        """
        Ensure all expected palette keys exist with sensible defaults.

        Args:
            palette: Original palette dict

        Returns:
            Palette with all expected keys
        """
        # Define all expected keys with their default derivation
        # Base keys that should always exist
        required_keys = [
            "TopBar_BG", "TopBar_FG",
            "MenuBar_BG", "MenuBar_FG",
            "MenuBar_Hover_BG", "MenuBar_Hover_FG",
            "MenuBar_Selected_BG", "MenuBar_Selected_FG",
            "StatusBar_BG", "StatusBar_FG",
            "Frame_BG", "Frame_FG", "Frame_FG_Secondary",
            "Data_BG", "Data_FG", "Data_Border",
            "Hover_BG", "Selected_BG", "Selected_FG",
            "Accent",
            "Normal_FG", "Success_FG", "Warning_FG", "Error_FG", "Info_FG"
        ]

        result = dict(palette)

        # Add MenuBar hover/selected defaults if missing
        # Use Hover_BG as default for MenuBar_Hover_BG (visible difference)
        if "MenuBar_Hover_BG" not in result:
            result["MenuBar_Hover_BG"] = result.get("Hover_BG", "#4d4d4d")
        if "MenuBar_Hover_FG" not in result:
            result["MenuBar_Hover_FG"] = result.get("MenuBar_FG", "#ffffff")
        # Use Accent as default for MenuBar_Selected_BG
        if "MenuBar_Selected_BG" not in result:
            result["MenuBar_Selected_BG"] = result.get("Accent", "#0078d7")
        if "MenuBar_Selected_FG" not in result:
            result["MenuBar_Selected_FG"] = "#ffffff"

        # Add Dropdown menu colors if missing
        if "DD_Menu_BG" not in result:
            result["DD_Menu_BG"] = result.get("Data_BG", "#2d2d2d")
        if "DD_Menu_FG" not in result:
            result["DD_Menu_FG"] = result.get("Data_FG", "#e0e0e0")
        if "DD_Menu_Hover_BG" not in result:
            result["DD_Menu_Hover_BG"] = result.get("Hover_BG", "#4d4d4d")
        if "DD_Menu_Hover_FG" not in result:
            result["DD_Menu_Hover_FG"] = result.get("Data_FG", "#e0e0e0")
        if "DD_Menu_Selected_BG" not in result:
            result["DD_Menu_Selected_BG"] = result.get("Selected_BG", "#0078d7")
        if "DD_Menu_Selected_FG" not in result:
            result["DD_Menu_Selected_FG"] = result.get("Selected_FG", "#ffffff")

        # Add Toolbar Button colors if missing (buttons in toolbar at top of managers)
        if "ToolbarBtn_BG" not in result:
            result["ToolbarBtn_BG"] = result.get("Frame_BG", "#3d3d3d")
        if "ToolbarBtn_FG" not in result:
            result["ToolbarBtn_FG"] = result.get("Frame_FG", "#e0e0e0")
        if "ToolbarBtn_Hover_BG" not in result:
            result["ToolbarBtn_Hover_BG"] = result.get("Hover_BG", "#4d4d4d")
        if "ToolbarBtn_Hover_FG" not in result:
            result["ToolbarBtn_Hover_FG"] = result.get("Normal_FG", "#ffffff")
        if "ToolbarBtn_Pressed_BG" not in result:
            result["ToolbarBtn_Pressed_BG"] = result.get("Selected_BG", "#0078d7")
        if "ToolbarBtn_Border" not in result:
            result["ToolbarBtn_Border"] = result.get("Frame_BG", "#3d3d3d")

        # Add Button colors if missing (buttons in panels/dialogs)
        if "Button_BG" not in result:
            result["Button_BG"] = result.get("Data_BG", "#2d2d2d")
        if "Button_FG" not in result:
            result["Button_FG"] = result.get("Normal_FG", "#ffffff")
        if "Button_Hover_BG" not in result:
            result["Button_Hover_BG"] = result.get("Hover_BG", "#4d4d4d")
        if "Button_Hover_FG" not in result:
            result["Button_Hover_FG"] = result.get("Normal_FG", "#ffffff")
        if "Button_Pressed_BG" not in result:
            result["Button_Pressed_BG"] = result.get("Selected_BG", "#0078d7")
        if "Button_Border" not in result:
            result["Button_Border"] = result.get("Data_Border", "#505050")

        # Add Grid colors if missing (alternating rows)
        if "Grid_Header_BG" not in result:
            result["Grid_Header_BG"] = result.get("Frame_BG", "#3d3d3d")
        if "Grid_Header_FG" not in result:
            result["Grid_Header_FG"] = result.get("Normal_FG", "#ffffff")
        if "Grid_Line1_BG" not in result:
            result["Grid_Line1_BG"] = result.get("Data_BG", "#2d2d2d")
        if "Grid_Line1_FG" not in result:
            result["Grid_Line1_FG"] = result.get("Frame_FG", "#e0e0e0")
        if "Grid_Line2_BG" not in result:
            # Slightly different from Line1 for alternating effect
            line1 = result.get("Grid_Line1_BG", result.get("Data_BG", "#2d2d2d"))
            result["Grid_Line2_BG"] = line1  # Will be darkened/lightened by theme_manager
        if "Grid_Line2_FG" not in result:
            result["Grid_Line2_FG"] = result.get("Frame_FG", "#e0e0e0")

        # Add TreeView colors if missing
        if "Tree_BG" not in result:
            result["Tree_BG"] = result.get("Data_BG", "#2d2d2d")
        if "Tree_FG" not in result:
            result["Tree_FG"] = result.get("Frame_FG", "#e0e0e0")
        if "Tree_Header_BG" not in result:
            result["Tree_Header_BG"] = result.get("Frame_BG", "#3d3d3d")
        if "Tree_Header_FG" not in result:
            result["Tree_Header_FG"] = result.get("Normal_FG", "#ffffff")
        if "Tree_Line1_BG" not in result:
            result["Tree_Line1_BG"] = result.get("Data_BG", "#2d2d2d")
        if "Tree_Line1_FG" not in result:
            result["Tree_Line1_FG"] = result.get("Frame_FG", "#e0e0e0")
        if "Tree_Line2_BG" not in result:
            result["Tree_Line2_BG"] = result.get("Tree_Line1_BG", "#2d2d2d")
        if "Tree_Line2_FG" not in result:
            result["Tree_Line2_FG"] = result.get("Frame_FG", "#e0e0e0")
        if "Tree_Branch_Color" not in result:
            result["Tree_Branch_Color"] = result.get("Frame_FG_Secondary", "#808080")

        # Add Frame styling if missing
        if "Frame_Border_Radius" not in result:
            result["Frame_Border_Radius"] = "0"

        # Add Splitter colors if missing (use visible colors by default)
        if "Splitter_BG" not in result:
            result["Splitter_BG"] = "#4d4d4d"  # Visible gray
        if "Splitter_Hover_BG" not in result:
            result["Splitter_Hover_BG"] = result.get("Accent", "#0078d7")

        # Add Log panel colors if missing
        if "Log_BG" not in result:
            result["Log_BG"] = result.get("Data_BG", "#2d2d2d")

        return result

    def _on_theme_selected(self, index: int):
        """Handle theme selection change."""
        theme_id = self.theme_combo.currentData()
        if theme_id:
            self._load_theme_data(theme_id)

    def _load_theme_data(self, theme_id: str):
        """Load theme colors into editor."""
        # Get theme palette
        palette = {}
        theme_name = theme_id

        # Try custom theme first
        theme_file = THEMES_PATH / f"{theme_id}.json"
        if theme_file.exists():
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    palette = data.get("palette", {})
                    theme_name = data.get("name", theme_id)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load theme file {theme_file}: {e}")

        if not palette:
            # Get from theme bridge
            if theme_id in self.theme_bridge.themes:
                theme_data = self.theme_bridge.themes[theme_id]
                palette = dict(theme_data.get("palette", {}))

        # Ensure all expected palette keys exist with defaults
        palette = self._ensure_palette_keys(palette)

        # Register in theme_bridge WITH the ensured keys so apply_theme works
        theme_data_for_bridge = {
            "name": theme_name,
            "type": "minimal",
            "palette": palette
        }
        self.theme_bridge.themes[theme_id] = theme_data_for_bridge
        self.theme_bridge._expanded_cache.pop(theme_id, None)

        self._current_theme_data = palette
        self._is_theme_modified = False
        self._update_theme_save_btn()

        # Clear colors layout
        self._theme_color_rows.clear()
        while self.colors_layout.count():
            item = self.colors_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create color rows
        for key, value in sorted(palette.items()):
            if isinstance(value, str) and value.startswith('#'):
                row = ColorPropertyRow(key, value)
                row.color_changed.connect(self._on_color_changed)
                self.colors_layout.addWidget(row)
                self._theme_color_rows[key] = row

        self.colors_layout.addStretch()

        # Update palette and preview
        self.palette_widget.update_colors(palette)
        self.theme_preview.set_colors(palette)

        # Apply category filter
        self._update_color_display()

    def _on_color_changed(self, key: str, color: str):
        """Handle color change."""
        self._current_theme_data[key] = color
        self._is_theme_modified = True
        self._update_theme_save_btn()
        self.palette_widget.update_colors(self._current_theme_data)
        self.theme_preview.set_colors(self._current_theme_data)

    def _on_palette_color_selected(self, color: str):
        """Handle palette color click - copy to clipboard."""
        QApplication.clipboard().setText(color)
        self.theme_status.setText(f"Couleur {color} copiee!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.theme_status.setText(""))

    def _update_theme_save_btn(self):
        """Update save button style."""
        if self._is_theme_modified:
            self.theme_save_btn.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
            self.theme_save_btn.setText(tr("btn_save") + " *")
        else:
            self.theme_save_btn.setStyleSheet("")
            self.theme_save_btn.setText(tr("btn_save"))

    def _duplicate_theme(self):
        """Duplicate current theme."""
        name, ok = QInputDialog.getText(self, "Dupliquer le theme",
                                        "Nom du nouveau theme:")
        if ok and name:
            name = name.strip()
            theme_id = name.lower().replace(" ", "_").replace("'", "")

            THEMES_PATH.mkdir(parents=True, exist_ok=True)
            new_file = THEMES_PATH / f"{theme_id}.json"

            if new_file.exists():
                DialogHelper.error(f"Le theme '{name}' existe deja.", parent=self)
                return

            # Save copy
            theme_data = {
                "name": name,
                "type": "minimal",
                "palette": self._current_theme_data
            }
            with open(new_file, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)

            # Register in bridge
            self.theme_bridge.themes[theme_id] = theme_data

            DialogHelper.info(f"Theme '{name}' cree!", parent=self)
            self._populate_theme_combo()

            # Select new theme
            idx = self.theme_combo.findData(theme_id)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)

    def _save_theme(self):
        """Save current theme to file."""
        theme_id = self.theme_combo.currentData()

        # Get theme name
        current_idx = self.theme_combo.currentIndex()
        theme_name = self.theme_combo.itemText(current_idx).replace(" (perso)", "")

        THEMES_PATH.mkdir(parents=True, exist_ok=True)

        theme_data = {
            "name": theme_name,
            "type": "minimal",
            "palette": self._current_theme_data
        }

        theme_file = THEMES_PATH / f"{theme_id}.json"
        try:
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)

            # Update bridge and clear cache
            self.theme_bridge.themes[theme_id] = theme_data
            self.theme_bridge.clear_cache(theme_id)

            self._is_theme_modified = False
            self._update_theme_save_btn()
            self.theme_status.setText(tr("settings_theme_saved"))
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self.theme_status.setText(""))
        except Exception as e:
            DialogHelper.error(f"Erreur: {e}", parent=self)

    def _apply_theme(self):
        """Apply selected theme to application."""
        theme_id = self.theme_combo.currentData()

        # If modified, ask to save first
        if self._is_theme_modified:
            reply = QMessageBox.question(self, tr("btn_apply"),
                                         tr("settings_confirm_apply"),
                                         QMessageBox.StandardButton.Yes |
                                         QMessageBox.StandardButton.No |
                                         QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                self._save_theme()

        # Apply theme (clear cache first to ensure fresh colors)
        self.theme_bridge.clear_cache(theme_id)
        global_qss = self.theme_bridge.generate_global_qss(theme_id)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(global_qss)
            self.theme_bridge.current_theme = theme_id
            self.user_prefs.set("theme", theme_id)
            self.theme_changed.emit(theme_id)

            self.theme_status.setText(tr("settings_theme_applied"))
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self.theme_status.setText(""))

    def _on_quick_theme_applied(self, theme_id: str):
        """Handle quick theme application."""
        # Refresh theme combo to include new themes
        self._populate_theme_combo()
        # Emit theme change signal
        self.theme_changed.emit(theme_id)

    # === DEBUG METHODS ===

    def _apply_debug(self):
        """Apply debug options."""
        objects_borders = self.objects_borders_cb.isChecked()
        self.user_prefs.set("objects_borders", objects_borders)
        self.debug_borders_changed.emit(objects_borders)

        self.debug_status.setText(tr("settings_options_applied"))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.debug_status.setText(""))
