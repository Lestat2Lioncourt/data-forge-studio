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
                               QMessageBox, QApplication, QLineEdit,
                               QFormLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ..managers.base_manager_view import BaseManagerView
from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.theme_preview import ThemePreview
from ..widgets.color_property_row import ColorPropertyRow
from ..widgets.opacity_property_row import OpacityPropertyRow
from ..widgets.palette_widget import PaletteWidget
from ..core.theme_bridge import ThemeBridge
from ..core.i18n_bridge import I18nBridge, tr
from ...config.i18n import i18n_manager
from ...config.user_preferences import UserPreferences
from ...core.theme.models import Palette, PALETTE_COLOR_NAMES

logger = logging.getLogger(__name__)

# Path to icons
ICONS_PATH = Path(__file__).parent.parent / "assets" / "images"

# General preferences definitions (data-driven)
# Each entry generates a tree node and an editor panel automatically.
# Supported types: "text", "bool", "choice"
GENERAL_PREFERENCES = [
    {
        "key": "query_column_names",
        "label": "Noms de colonnes (Edit Query)",
        "type": "text",
        "group": "Edit Query - Noms de colonnes",
        "description": (
            "Liste des noms de colonnes (séparés par des virgules) pour lesquels "
            "l'option \"Edit Query\" est disponible dans le menu contextuel des "
            "grilles de résultats.\nLa comparaison est insensible à la casse."
        ),
        "placeholder": "query, requête, sql, sql_text, ...",
        "default": "query, requête",
    },
]

# Paths to config files
LANGUAGES_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig" / "languages"
THEMES_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig" / "themes"
PALETTES_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig" / "palettes"

# Theme color categories for filtering
THEME_CATEGORIES = {
    "Barre de titre": ["topbar_bg", "topbar_fg"],
    "Barre de menu": ["menubar_bg", "menubar_fg", "menubar_hover_bg", "menubar_hover_fg",
                      "menubar_selected_bg", "menubar_selected_fg"],
    "Menus déroulants": ["menu_bg", "menu_fg", "menu_hover_bg", "menu_hover_fg",
                         "menu_selected_bg", "menu_selected_fg", "menu_separator"],
    "Barre d'outils": ["toolbar_bg", "toolbar_button_bg", "toolbar_button_fg", "toolbar_button_hover_bg",
                       "toolbar_button_hover_fg", "toolbar_button_pressed_bg", "toolbar_button_border"],
    "Boutons": ["button_bg", "button_fg", "button_hover_bg", "button_hover_fg",
                "button_pressed_bg", "button_border", "button_disabled_bg", "button_disabled_fg"],
    "Barre d'état": ["statusbar_bg", "statusbar_fg"],
    "Barre d'icônes": ["iconsidebar_bg", "iconsidebar_selected_bg", "iconsidebar_hover_bg",
                       "iconsidebar_pressed_bg", "icon_color"],
    "Panneaux": ["panel_bg", "surface_bg", "window_bg", "border_color", "window_border"],
    "Sélection": ["hover_bg", "selected_bg", "selected_fg", "pressed_bg", "focus_border"],
    "Grilles": ["grid_bg", "grid_fg", "grid_header_bg", "grid_header_fg",
                "grid_line1_bg", "grid_line1_fg", "grid_line2_bg", "grid_line2_fg",
                "grid_selected_bg", "grid_selected_fg", "grid_hover_bg", "grid_gridline"],
    "Arborescence": ["tree_bg", "tree_fg", "tree_header_bg", "tree_header_fg",
                     "tree_line1_bg", "tree_line1_fg", "tree_line2_bg", "tree_line2_fg",
                     "tree_selected_bg", "tree_selected_fg", "tree_hover_bg", "tree_branch_color",
                     "tree_icon_color"],
    "Onglets": ["tab_bg", "tab_fg", "tab_selected_bg", "tab_selected_fg", "tab_hover_bg"],
    "Champs de saisie": ["input_bg", "input_fg", "input_border", "input_focus_border",
                         "input_placeholder", "input_disabled_bg", "input_disabled_fg"],
    "Éditeur SQL": ["editor_bg", "editor_fg", "editor_selection_bg", "editor_selection_fg",
                    "editor_current_line_bg", "editor_line_number_bg", "editor_line_number_fg",
                    "sql_keyword", "sql_string", "sql_comment", "sql_number",
                    "sql_function", "sql_operator", "sql_identifier"],
    "Messages (log)": ["log_bg", "log_fg", "log_info", "log_warning", "log_error", "log_important", "log_debug"],
    "Barres de défilement": ["scrollbar_bg", "scrollbar_handle", "scrollbar_handle_hover"],
    "Infobulles": ["tooltip_bg", "tooltip_fg", "tooltip_border"],
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
        self._is_lang_modified = False

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

        # General editor
        self.general_editor = self._create_general_editor()
        self.editors_layout.addWidget(self.general_editor)
        self.general_editor.hide()

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

        # Placeholder when nothing selected
        self.placeholder = QLabel(tr("settings_select_option"))
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: #808080; font-style: italic;")
        self.editors_layout.addWidget(self.placeholder)

        self.content_layout.addWidget(self.editors_container)

    def _create_general_editor(self) -> QWidget:
        """Create dynamic general preferences editor.

        Content is rebuilt by _load_general_pref() each time a preference
        node is selected in the tree.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Dynamic content area (rebuilt per preference)
        self._general_content = QWidget()
        self._general_content_layout = QVBoxLayout(self._general_content)
        self._general_content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._general_content)

        # Apply button
        btn_layout = QHBoxLayout()
        general_apply_btn = QPushButton(tr("btn_apply"))
        general_apply_btn.clicked.connect(self._apply_general)
        general_apply_btn.setMinimumWidth(120)
        btn_layout.addWidget(general_apply_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Status
        self.general_status = QLabel("")
        self.general_status.setStyleSheet("color: #2ecc71;")
        layout.addWidget(self.general_status)

        layout.addStretch()

        # Track current pref key + its input widget
        self._general_current_key: Optional[str] = None
        self._general_input_widget: Optional[QWidget] = None

        return widget

    def _load_general_pref(self, pref_key: str):
        """Load a specific general preference into the editor."""
        # Find definition
        pref_def = None
        for p in GENERAL_PREFERENCES:
            if p["key"] == pref_key:
                pref_def = p
                break
        if not pref_def:
            return

        self._general_current_key = pref_key

        # Clear previous content
        while self._general_content_layout.count():
            item = self._general_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Group box
        group = QGroupBox(pref_def.get("group", pref_def["label"]))
        group_layout = QVBoxLayout(group)

        # Description
        desc = pref_def.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #808080; font-style: italic;")
            group_layout.addWidget(desc_label)

        # Input widget based on type
        pref_type = pref_def.get("type", "text")
        current_value = self.user_prefs.get(pref_key, pref_def.get("default", ""))

        if pref_type == "text":
            input_layout = QHBoxLayout()
            input_layout.addWidget(QLabel(pref_def["label"] + " :"))
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(pref_def.get("placeholder", ""))
            line_edit.setText(str(current_value))
            input_layout.addWidget(line_edit)
            group_layout.addLayout(input_layout)
            self._general_input_widget = line_edit

        elif pref_type == "bool":
            cb = QCheckBox(pref_def["label"])
            cb.setChecked(bool(current_value))
            group_layout.addWidget(cb)
            self._general_input_widget = cb

        elif pref_type == "choice":
            input_layout = QHBoxLayout()
            input_layout.addWidget(QLabel(pref_def["label"] + " :"))
            combo = QComboBox()
            for choice in pref_def.get("choices", []):
                combo.addItem(choice)
            idx = combo.findText(str(current_value))
            if idx >= 0:
                combo.setCurrentIndex(idx)
            input_layout.addWidget(combo)
            input_layout.addStretch()
            group_layout.addLayout(input_layout)
            self._general_input_widget = combo

        self._general_content_layout.addWidget(group)

    def _apply_general(self):
        """Apply the currently displayed general preference."""
        if not self._general_current_key or not self._general_input_widget:
            return

        pref_def = None
        for p in GENERAL_PREFERENCES:
            if p["key"] == self._general_current_key:
                pref_def = p
                break
        if not pref_def:
            return

        pref_type = pref_def.get("type", "text")

        if pref_type == "text":
            value = self._general_input_widget.text().strip()
        elif pref_type == "bool":
            value = self._general_input_widget.isChecked()
        elif pref_type == "choice":
            value = self._general_input_widget.currentText()
        else:
            return

        if value or pref_type == "bool":
            self.user_prefs.set(self._general_current_key, value)

        self.general_status.setText(tr("settings_options_applied"))
        self.general_status.setStyleSheet("color: #2ecc71;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.general_status.setText(""))

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
        """Create theme editor with v2 system: palette + disposition + apply."""
        widget = QWidget()
        self._theme_editor_widget = widget
        self._apply_theme_editor_style()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # === ROW 1: Palette + Disposition + Apply ===
        top_layout = QHBoxLayout()

        # Palette selector
        top_layout.addWidget(QLabel("Palette:"))
        self.palette_combo = QComboBox()
        self.palette_combo.setMinimumWidth(150)
        self.palette_combo.currentIndexChanged.connect(self._on_palette_changed)
        top_layout.addWidget(self.palette_combo)

        top_layout.addSpacing(20)

        # Disposition selector
        top_layout.addWidget(QLabel("Disposition:"))
        self.disposition_combo = QComboBox()
        self.disposition_combo.setMinimumWidth(150)
        self.disposition_combo.currentIndexChanged.connect(self._on_disposition_changed)
        top_layout.addWidget(self.disposition_combo)

        top_layout.addSpacing(20)

        # Category filter
        top_layout.addWidget(QLabel("Catégorie:"))
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(150)
        self.category_combo.addItem("Toutes", None)
        for category_name in THEME_CATEGORIES.keys():
            self.category_combo.addItem(category_name, category_name)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        top_layout.addWidget(self.category_combo)

        top_layout.addStretch()

        # Apply button
        self.theme_apply_btn = QPushButton(tr("btn_apply"))
        self.theme_apply_btn.clicked.connect(self._apply_theme)
        self.theme_apply_btn.setStyleSheet("font-weight: bold; padding: 8px 20px;")
        top_layout.addWidget(self.theme_apply_btn)

        layout.addLayout(top_layout)

        # === MIDDLE: Splitter with palette colors, generated colors and preview ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Palette colors (editable - modifies palette)
        palette_group = QGroupBox("Palette (15 couleurs)")
        palette_group_layout = QVBoxLayout(palette_group)

        palette_scroll = QScrollArea()
        palette_scroll.setWidgetResizable(True)
        palette_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.palette_colors_container = QWidget()
        self.palette_colors_layout = QVBoxLayout(self.palette_colors_container)
        self.palette_colors_layout.setContentsMargins(5, 5, 5, 5)
        self.palette_colors_layout.setSpacing(2)
        palette_scroll.setWidget(self.palette_colors_container)
        palette_group_layout.addWidget(palette_scroll)

        splitter.addWidget(palette_group)

        # Middle: Generated colors (editable - stored as overrides)
        generated_group = QGroupBox("Couleurs générées (modifiable = override)")
        generated_group_layout = QVBoxLayout(generated_group)

        generated_scroll = QScrollArea()
        generated_scroll.setWidgetResizable(True)
        generated_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.generated_colors_container = QWidget()
        self.generated_colors_layout = QVBoxLayout(self.generated_colors_container)
        self.generated_colors_layout.setContentsMargins(5, 5, 5, 5)
        self.generated_colors_layout.setSpacing(2)
        generated_scroll.setWidget(self.generated_colors_container)
        generated_group_layout.addWidget(generated_scroll)

        splitter.addWidget(generated_group)

        # Right: Preview
        preview_group = QGroupBox("Aperçu")
        preview_layout = QVBoxLayout(preview_group)

        self.theme_preview = ThemePreview()
        preview_layout.addWidget(self.theme_preview)

        splitter.addWidget(preview_group)
        splitter.setSizes([200, 350, 250])

        layout.addWidget(splitter, 1)

        # Status
        self.theme_status = QLabel("")
        self.theme_status.setStyleSheet("color: #2ecc71;")
        layout.addWidget(self.theme_status)

        # Internal state
        self._current_palette_data: Dict[str, str] = {}
        self._current_overrides: Dict[str, str] = {}  # User overrides for generated colors
        self._palette_color_rows: Dict[str, ColorPropertyRow] = {}
        self._generated_color_rows: Dict[str, ColorPropertyRow] = {}
        self._loaded_color: Optional[str] = None  # Color loaded for paste mode

        return widget

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

        # General section with individual preferences as children
        general_parent = self.tree_view.add_item(
            parent=prefs_parent,
            text=["Général"],
            data={"type": "category", "name": "general"}
        )
        general_parent.setIcon(0, category_icon)

        for pref_def in GENERAL_PREFERENCES:
            pref_item = self.tree_view.add_item(
                parent=general_parent,
                text=[pref_def["label"]],
                data={"type": "general_pref", "key": pref_def["key"]}
            )
            pref_item.setIcon(0, option_icon)

        lang_item = self.tree_view.add_item(
            parent=prefs_parent,
            text=["Langue"],
            data={"type": "language"}
        )
        lang_item.setIcon(0, option_icon)

        # Themes section with individual themes as children
        themes_parent = self.tree_view.add_item(
            parent=prefs_parent,
            text=["Thèmes"],
            data={"type": "category", "name": "themes"}
        )
        themes_parent.setIcon(0, category_icon)

        # Add each theme as a child
        themes = self.theme_bridge.get_themes_v2()
        for theme_id, theme in sorted(themes.items()):
            theme_item = self.tree_view.add_item(
                parent=themes_parent,
                text=[theme.name],
                data={"type": "theme", "theme_id": theme_id}
            )
            theme_item.setIcon(0, option_icon)

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
        self._populate_palette_combo()
        self._populate_disposition_combo()
        self._load_current_palette()

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

    def _populate_palette_combo(self):
        """Populate palette dropdown with v2 palettes."""
        self.palette_combo.blockSignals(True)
        self.palette_combo.clear()

        # Get palettes from theme bridge
        palettes = self.theme_bridge.get_palettes()
        for palette_id, palette in sorted(palettes.items()):
            # Skip internal palettes (starting with _)
            if not palette_id.startswith('_'):
                self.palette_combo.addItem(palette.name, palette_id)

        # Select "sombre" by default if available
        idx = self.palette_combo.findData("sombre")
        if idx >= 0:
            self.palette_combo.setCurrentIndex(idx)
        elif self.palette_combo.count() > 0:
            self.palette_combo.setCurrentIndex(0)

        self.palette_combo.blockSignals(False)

    def _populate_disposition_combo(self):
        """Populate disposition dropdown."""
        self.disposition_combo.blockSignals(True)
        self.disposition_combo.clear()

        # Get dispositions from theme bridge
        dispositions = self.theme_bridge.get_dispositions()
        for disp_id, disp in sorted(dispositions.items()):
            self.disposition_combo.addItem(disp.name, disp_id)

        # Select "standard" by default if available
        idx = self.disposition_combo.findData("standard")
        if idx >= 0:
            self.disposition_combo.setCurrentIndex(idx)
        elif self.disposition_combo.count() > 0:
            self.disposition_combo.setCurrentIndex(0)

        self.disposition_combo.blockSignals(False)

    def _load_current_palette(self):
        """Load the currently selected palette into the editor."""
        palette_id = self.palette_combo.currentData()
        if not palette_id:
            return

        palette = self.theme_bridge.get_palette(palette_id)
        if not palette:
            return

        self._current_palette_data = dict(palette.colors)
        self._rebuild_palette_color_rows()
        self._update_preview()

    def _rebuild_palette_color_rows(self):
        """Rebuild the palette color rows from current palette data."""
        # Clear existing rows
        self._palette_color_rows.clear()
        while self.palette_colors_layout.count():
            item = self.palette_colors_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create color rows for each palette color
        for color_name in PALETTE_COLOR_NAMES:
            color_value = self._current_palette_data.get(color_name, "#ff00ff")
            row = ColorPropertyRow(color_name, color_value)
            row.color_changed.connect(self._on_palette_color_changed)
            row.color_clicked.connect(self._on_palette_color_clicked)
            self.palette_colors_layout.addWidget(row)
            self._palette_color_rows[color_name] = row

        self.palette_colors_layout.addStretch()

    def _update_preview(self):
        """Update the theme preview and generated colors with current palette + disposition."""
        palette_id = self.palette_combo.currentData()
        disposition_id = self.disposition_combo.currentData()

        if not palette_id or not disposition_id:
            return

        # Create a temporary palette with current edits
        from ...core.theme.models import Palette
        temp_palette = Palette(
            id="temp",
            name="Temp",
            colors=self._current_palette_data
        )

        # Get disposition
        disposition = self.theme_bridge.get_disposition(disposition_id)
        if not disposition:
            return

        # Generate colors using the engine
        generated_colors = self.theme_bridge._engine.apply(temp_palette, disposition)

        # Apply overrides on top
        final_colors = dict(generated_colors)
        final_colors.update(self._current_overrides)

        # Update preview
        self.theme_preview.set_colors(final_colors)

        # Rebuild generated colors rows
        self._rebuild_generated_color_rows(generated_colors)

    def _rebuild_generated_color_rows(self, generated_colors: Dict[str, str]):
        """Rebuild the generated colors rows."""
        # Clear existing rows
        self._generated_color_rows.clear()
        while self.generated_colors_layout.count():
            item = self.generated_colors_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get disposition vectors for source display
        disposition_vectors = {}
        disposition_id = self.disposition_combo.currentData()
        if disposition_id:
            disposition = self.theme_bridge.get_disposition(disposition_id)
            if disposition:
                disposition_vectors = disposition.vectors

        # Skip palette colors (they're in the palette section)
        palette_keys = set(PALETTE_COLOR_NAMES)

        # Create color rows for generated colors (excluding palette colors)
        for key in sorted(generated_colors.keys()):
            if key in palette_keys or key == "is_dark":
                continue

            # Check if there's an override
            if key in self._current_overrides:
                color_value = self._current_overrides[key]
                is_override = True
            else:
                color_value = generated_colors[key]
                is_override = False

            if isinstance(color_value, str) and color_value.startswith('#'):
                # Get source vector from disposition
                source = disposition_vectors.get(key)

                row = ColorPropertyRow(key, color_value, source=source)
                row.color_changed.connect(self._on_generated_color_changed)
                row.color_pasted.connect(self._on_generated_color_pasted)

                # Mark overridden colors visually
                if is_override:
                    row.setStyleSheet("background-color: rgba(0, 120, 215, 0.1);")

                # Restore paste mode if a color was loaded
                if self._loaded_color:
                    row.set_paste_mode(self._loaded_color)

                self.generated_colors_layout.addWidget(row)
                self._generated_color_rows[key] = row

        self.generated_colors_layout.addStretch()

    def _on_generated_color_changed(self, key: str, color: str):
        """Handle generated color change - store as override."""
        self._current_overrides[key] = color

        # Update the row styling to show it's an override
        if key in self._generated_color_rows:
            self._generated_color_rows[key].setStyleSheet("background-color: rgba(0, 120, 215, 0.1);")

        # Update preview
        self._update_preview_only()

        self.theme_status.setText(f"Override: '{key}' = {color}")
        self.theme_status.setStyleSheet("color: #f39c12;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.theme_status.setText(""))

    def _on_generated_color_pasted(self, key: str, color: str):
        """Handle color pasted from palette - show feedback then restore paste mode status."""
        self.theme_status.setText(f"Couleur {color} appliquée à '{key}'")
        self.theme_status.setStyleSheet("color: #2ecc71;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, self._restore_paste_mode_status)

    def _restore_paste_mode_status(self):
        """Restore the paste mode status message if a color is still loaded."""
        if self._loaded_color:
            self.theme_status.setText(f"Couleur {self._loaded_color} chargée - cliquer sur une couleur générée pour appliquer")
            self.theme_status.setStyleSheet("color: #2ecc71; font-weight: bold;")
        else:
            self.theme_status.setText("")
            self.theme_status.setStyleSheet("")

    def _update_preview_only(self):
        """Update just the preview without rebuilding color rows."""
        palette_id = self.palette_combo.currentData()
        disposition_id = self.disposition_combo.currentData()

        if not palette_id or not disposition_id:
            return

        from ...core.theme.models import Palette
        temp_palette = Palette(
            id="temp",
            name="Temp",
            colors=self._current_palette_data
        )

        disposition = self.theme_bridge.get_disposition(disposition_id)
        if not disposition:
            return

        generated_colors = self.theme_bridge._engine.apply(temp_palette, disposition)
        final_colors = dict(generated_colors)
        final_colors.update(self._current_overrides)
        self.theme_preview.set_colors(final_colors)

    def _on_palette_changed(self, index: int):
        """Handle palette selection change."""
        # Clear overrides when changing palette (they may no longer make sense)
        self._current_overrides.clear()
        self._load_current_palette()

    def _on_disposition_changed(self, index: int):
        """Handle disposition selection change."""
        # Clear overrides when changing disposition (different vectors = different keys)
        self._current_overrides.clear()
        self._update_preview()

    def _on_category_changed(self, index: int):
        """Handle category filter change."""
        category = self.category_combo.currentData()
        self._filter_generated_colors(category)


    def _on_palette_color_changed(self, key: str, color: str):
        """Handle palette color change from color row."""
        self._current_palette_data[key] = color
        self._update_preview()

        self.theme_status.setText(f"Couleur '{key}' modifiée")
        self.theme_status.setStyleSheet("color: #3498db;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.theme_status.setText(""))

    def _on_palette_color_clicked(self, key: str, color: str):
        """Handle palette color click - load color for paste mode."""
        # If same color clicked again, clear paste mode
        if self._loaded_color == color:
            self._clear_paste_mode()
            return

        # Load this color for paste mode
        self._loaded_color = color

        # Enable paste mode on all generated color rows
        for row in self._generated_color_rows.values():
            row.set_paste_mode(color)

        self.theme_status.setText(f"Couleur {color} chargée - cliquer sur une couleur générée pour appliquer")
        self.theme_status.setStyleSheet("color: #2ecc71; font-weight: bold;")

    def _clear_paste_mode(self):
        """Clear paste mode on all generated color rows."""
        self._loaded_color = None
        for row in self._generated_color_rows.values():
            row.clear_paste_mode()
        self.theme_status.setText("")
        self.theme_status.setStyleSheet("")

    def _save_palette(self):
        """Save current palette colors to a new palette file."""
        from PySide6.QtWidgets import QInputDialog

        # Get palette name
        name, ok = QInputDialog.getText(
            self, "Sauvegarder la palette",
            "Nom de la palette:"
        )
        if not ok or not name.strip():
            return

        name = name.strip()

        # Generate palette ID from name
        palette_id = name.lower().replace(" ", "_").replace("'", "")
        for char in "éèêë":
            palette_id = palette_id.replace(char, "e")
        for char in "àâä":
            palette_id = palette_id.replace(char, "a")

        # Build palette data from current theme
        palette_data = {
            "name": name,
            "background": self._current_theme_data.get("background", "#252525"),
            "surface": self._current_theme_data.get("surface", "#2d2d2d"),
            "border": self._current_theme_data.get("border", "#3d3d3d"),
            "accent": self._current_theme_data.get("accent", "#0078d7"),
            "text": self._current_theme_data.get("text", "#e0e0e0"),
            "text_secondary": self._current_theme_data.get("text_secondary", "#808080"),
            "icon": self._current_theme_data.get("icon", "#e0e0e0"),
            "info": self._current_theme_data.get("info", "#3498db"),
            "warning": self._current_theme_data.get("warning", "#f39c12"),
            "error": self._current_theme_data.get("error", "#e74c3c"),
            "important": self._current_theme_data.get("important", "#9b59b6"),
            "hover_opacity": self._current_theme_data.get("hover_opacity", 15),
            "selected_opacity": self._current_theme_data.get("selected_opacity", 30),
        }

        # Save to file
        PALETTES_PATH.mkdir(parents=True, exist_ok=True)
        palette_file = PALETTES_PATH / f"{palette_id}.json"

        try:
            with open(palette_file, 'w', encoding='utf-8') as f:
                json.dump(palette_data, f, indent=2, ensure_ascii=False)

            # Refresh palette combo
            self._populate_palette_combo()

            # Select the new palette
            idx = self.palette_combo.findData(palette_id)
            if idx >= 0:
                self.palette_combo.setCurrentIndex(idx)

            self.theme_status.setText(f"Palette '{name}' sauvegardée")
            self.theme_status.setStyleSheet("color: #2ecc71;")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.theme_status.setText(""))

        except Exception as e:
            logger.error(f"Error saving palette: {e}")
            from ..widgets.dialog_helper import DialogHelper
            DialogHelper.error(f"Erreur de sauvegarde: {e}", parent=self)

    def _display_item(self, item_data: Any):
        """Show appropriate editor based on selection."""
        if not isinstance(item_data, dict):
            return

        option_type = item_data.get("type", "")

        # Hide all
        self.general_editor.hide()
        self.language_editor.hide()
        self.theme_editor.hide()
        self.debug_editor.hide()
        self.placeholder.hide()

        if option_type == "general_pref":
            pref_key = item_data.get("key")
            if pref_key:
                self.general_editor.show()
                self._load_general_pref(pref_key)
        elif option_type == "category" and item_data.get("name") == "general":
            # Clicked on "Général" parent - show first preference
            if GENERAL_PREFERENCES:
                self.general_editor.show()
                self._load_general_pref(GENERAL_PREFERENCES[0]["key"])
        elif option_type == "language":
            self.language_editor.show()
        elif option_type == "theme":
            self.theme_editor.show()
            # Load theme if theme_id is specified
            theme_id = item_data.get("theme_id")
            if theme_id:
                self._load_theme_into_editor(theme_id)
        elif option_type == "category" and item_data.get("name") == "themes":
            # Clicked on "Thèmes" parent - show editor with current active theme
            self.theme_editor.show()
            current_theme = self.theme_bridge.current_theme
            if current_theme:
                self._load_theme_into_editor(current_theme)
                self._select_theme_in_tree(current_theme)
        elif option_type == "debug_borders":
            self.debug_editor.show()
        else:
            self.placeholder.show()

    def _select_theme_in_tree(self, theme_id: str):
        """Select a theme in the tree view."""
        # Find and select the theme item in the tree
        root = self.tree_view.tree.invisibleRootItem()
        self._find_and_select_theme(root, theme_id)

    def _find_and_select_theme(self, parent, theme_id: str) -> bool:
        """Recursively find and select theme in tree."""
        for i in range(parent.childCount()):
            item = parent.child(i)
            data = self.tree_view.tree.itemWidget(item, 0)
            # Get item data from the tree
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(item_data, dict):
                if item_data.get("type") == "theme" and item_data.get("theme_id") == theme_id:
                    self.tree_view.tree.blockSignals(True)
                    self.tree_view.tree.setCurrentItem(item)
                    self.tree_view.tree.blockSignals(False)
                    return True
            # Recurse into children
            if self._find_and_select_theme(item, theme_id):
                return True
        return False

    def _load_theme_into_editor(self, theme_id: str):
        """Load a theme into the editor by selecting its palette and disposition."""
        theme = self.theme_bridge.get_theme_v2(theme_id)
        if not theme:
            return

        # Select palette
        palette_id = theme.palette_id
        idx = self.palette_combo.findData(palette_id)
        if idx >= 0:
            self.palette_combo.blockSignals(True)
            self.palette_combo.setCurrentIndex(idx)
            self.palette_combo.blockSignals(False)

        # Select disposition
        idx = self.disposition_combo.findData(theme.disposition_id)
        if idx >= 0:
            self.disposition_combo.blockSignals(True)
            self.disposition_combo.setCurrentIndex(idx)
            self.disposition_combo.blockSignals(False)

        # Load overrides if any
        self._current_overrides = dict(theme.overrides) if theme.overrides else {}

        # Reload palette and update preview
        self._load_current_palette()

        # Re-apply current category filter
        current_category = self.category_combo.currentData()
        self._filter_generated_colors(current_category)

    def _filter_generated_colors(self, category: Optional[str]):
        """Filter generated color rows by category."""
        if category is None:
            # Show all
            for row in self._generated_color_rows.values():
                row.setVisible(True)
        else:
            # Show only colors in this category
            visible_keys = set(THEME_CATEGORIES.get(category, []))
            for key, row in self._generated_color_rows.items():
                row.setVisible(key in visible_keys)

    # === LANGUAGE METHODS ===

    def _on_lang_selected(self, index: int):
        """Handle language selection change."""
        lang_code = self.lang_combo.currentData()
        if lang_code:
            self._load_language_data(lang_code)
            # Apply language and persist preference
            self.i18n_bridge.set_language(lang_code)
            self.user_prefs.set("language", lang_code)

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
        Expand a minimal palette to full theme colors using ThemeGenerator.

        Custom overrides in the original palette are preserved - they will
        override the generated values.

        Args:
            palette: Original palette dict (can be legacy or new format)

        Returns:
            Full theme colors dict with all keys in snake_case
        """
        # Convert legacy palette to new ThemePalette format
        try:
            theme_palette = legacy_to_palette(palette, name="Editing")
        except (KeyError, TypeError):
            # If conversion fails, create a default palette
            from ...core.theme import DEFAULT_DARK_PALETTE
            theme_palette = DEFAULT_DARK_PALETTE

        # Generate full theme using ThemeGenerator
        generator = ThemeGenerator()
        generated = generator.generate(theme_palette)

        # Start with generated colors
        result = dict(generated.colors)

        # Overlay original palette values to preserve custom overrides
        # (e.g., user-edited menubar_hover_bg, menubar_selected_bg, etc.)
        for key, value in palette.items():
            if key not in PALETTE_SOURCE_KEYS and key in result:
                # This is a derived color that was customized - preserve it
                result[key] = value

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
        self._opacity_rows.clear()
        while self.colors_layout.count():
            item = self.colors_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create color rows
        for key, value in sorted(palette.items()):
            if isinstance(value, str) and value.startswith('#'):
                row = ColorPropertyRow(key, value)
                row.color_changed.connect(self._on_color_changed)
                row.color_pasted.connect(self._on_color_pasted)
                self.colors_layout.addWidget(row)
                self._theme_color_rows[key] = row

        # Create opacity rows (at the end, after all colors)
        for key, label in OPACITY_SETTINGS.items():
            value = palette.get(key, 15 if 'hover' in key else 30)
            if isinstance(value, int):
                row = OpacityPropertyRow(key, value, label)
                row.value_changed.connect(self._on_opacity_changed)
                self.colors_layout.addWidget(row)
                self._opacity_rows[key] = row

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

        # If a palette source color was changed, regenerate all derived colors
        if key in PALETTE_SOURCE_KEYS:
            self._regenerate_from_palette()
        else:
            self.palette_widget.update_colors(self._current_theme_data)
            self.theme_preview.set_colors(self._current_theme_data)

    def _on_opacity_changed(self, key: str, value: int):
        """Handle opacity value change - regenerate affected colors."""
        self._current_theme_data[key] = value
        self._is_theme_modified = True
        self._update_theme_save_btn()

        # Regenerate the theme with new opacity values to update derived colors
        self._regenerate_derived_colors()

    def _regenerate_from_palette(self):
        """Regenerate derived colors from the current palette source colors.

        When regenerating, ALL derived colors are updated based on the new
        source colors. If the user wants to customize a derived color, they
        should do it AFTER modifying source colors.
        """
        # Build a ThemePalette from current source colors
        palette = ThemePalette(
            name="Editing",
            background=self._current_theme_data.get("background", "#252525"),
            surface=self._current_theme_data.get("surface", "#2d2d2d"),
            border=self._current_theme_data.get("border", "#3d3d3d"),
            accent=self._current_theme_data.get("accent", "#0078d7"),
            text=self._current_theme_data.get("text", "#e0e0e0"),
            text_secondary=self._current_theme_data.get("text_secondary", "#808080"),
            icon=self._current_theme_data.get("icon", "#e0e0e0"),
            info=self._current_theme_data.get("info", "#3498db"),
            warning=self._current_theme_data.get("warning", "#f39c12"),
            error=self._current_theme_data.get("error", "#e74c3c"),
            important=self._current_theme_data.get("important", "#9b59b6"),
            hover_opacity=self._current_theme_data.get("hover_opacity", 15),
            selected_opacity=self._current_theme_data.get("selected_opacity", 30),
        )

        # Generate full theme
        generator = ThemeGenerator()
        generated = generator.generate(palette)

        # Update current theme data with regenerated colors
        self._current_theme_data.update(generated.colors)

        # Update all color rows with new values
        for key, row in self._theme_color_rows.items():
            if key in self._current_theme_data:
                new_color = self._current_theme_data[key]
                if isinstance(new_color, str) and new_color.startswith('#'):
                    row.set_color(new_color)

        # Update palette widget and preview
        self.palette_widget.update_colors(self._current_theme_data)
        self.theme_preview.set_colors(self._current_theme_data)

        # Show feedback
        self.theme_status.setText("Couleurs régénérées depuis la palette")
        self.theme_status.setStyleSheet("color: #3498db;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.theme_status.setText(""))

    def _regenerate_derived_colors(self):
        """Regenerate colors that depend on opacity settings."""
        # Use the full regeneration since opacity affects all derived colors
        self._regenerate_from_palette()

    def _on_palette_color_selected(self, color: str):
        """Handle palette color click - enable paste mode on all color rows."""
        # Enable paste mode on all visible color rows
        for row in self._theme_color_rows.values():
            if row.isVisible():
                row.set_paste_mode(color)

        self.theme_status.setText(f"Couleur {color} chargee - cliquer sur une propriete pour appliquer")
        self.theme_status.setStyleSheet("color: #2ecc71; font-weight: bold;")

    def _on_palette_color_cleared(self):
        """Handle palette color cleared - disable paste mode on all color rows."""
        for row in self._theme_color_rows.values():
            row.clear_paste_mode()

        self.theme_status.setText("")
        self.theme_status.setStyleSheet("")

    def _on_color_pasted(self, key: str, color: str):
        """Handle color pasted from palette - clear paste mode but keep color loaded for more pastes."""
        # Show feedback
        self.theme_status.setText(f"Couleur {color} appliquee a {key}")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self._restore_paste_mode_status())

    def _restore_paste_mode_status(self):
        """Restore the paste mode status message if a color is still loaded."""
        if self._loaded_color:
            self.theme_status.setText(f"Couleur {self._loaded_color} chargée - cliquer sur une couleur générée pour appliquer")
            self.theme_status.setStyleSheet("color: #2ecc71; font-weight: bold;")
        else:
            self.theme_status.setText("")
            self.theme_status.setStyleSheet("")

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
        """Apply current palette + disposition + overrides as theme. Saves everything."""
        palette_id = self.palette_combo.currentData()
        disposition_id = self.disposition_combo.currentData()

        if not palette_id or not disposition_id:
            return

        # 1. Save palette modifications to file
        self._save_current_palette(palette_id)

        # 1b. Reload palette in theme bridge
        self.theme_bridge.reload_palette(palette_id)

        # 2. Build theme ID from disposition + palette
        theme_id = f"{disposition_id}_{palette_id}"

        # 3. Create/update the theme with the selected palette
        from ...core.theme.models import Theme
        theme = Theme(
            id=theme_id,
            name=f"{self.disposition_combo.currentText()} {self.palette_combo.currentText()}",
            disposition_id=disposition_id,
            palette_id=palette_id,
            overrides=dict(self._current_overrides)
        )

        # Register in theme bridge
        self.theme_bridge._themes_v2[theme_id] = theme

        # Save theme to file
        THEMES_PATH.mkdir(parents=True, exist_ok=True)
        theme_file = THEMES_PATH / f"{theme_id}.json"
        with open(theme_file, 'w', encoding='utf-8') as f:
            json.dump(theme.to_dict(), f, indent=2, ensure_ascii=False)

        # 4. Clear cache and apply
        self.theme_bridge.clear_cache(theme_id)
        global_qss = self.theme_bridge.generate_global_qss(theme_id)

        app = QApplication.instance()
        if app:
            app.setStyleSheet(global_qss)
            self.theme_bridge.current_theme = theme_id
            self.user_prefs.set("theme", theme_id)
            self.theme_changed.emit(theme_id)

            # Status message
            msg = f"Thème '{theme_id}' sauvegardé et appliqué"
            if self._current_overrides:
                msg += f" ({len(self._current_overrides)} override(s))"
            self.theme_status.setText(msg)
            self.theme_status.setStyleSheet("color: #2ecc71;")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self.theme_status.setText(""))

    def _save_current_palette(self, palette_id: str):
        """Save current palette modifications to file."""
        if not self._current_palette_data:
            return

        # Get current palette name
        palette = self.theme_bridge.get_palette(palette_id)
        palette_name = palette.name if palette else palette_id

        # Build palette data
        palette_data = {
            "name": palette_name,
            "colors": dict(self._current_palette_data)
        }

        # Save to file
        PALETTES_PATH.mkdir(parents=True, exist_ok=True)
        palette_file = PALETTES_PATH / f"{palette_id}.json"
        with open(palette_file, 'w', encoding='utf-8') as f:
            json.dump(palette_data, f, indent=2, ensure_ascii=False)

        # Update in theme bridge
        from ...core.theme.models import Palette
        updated_palette = Palette(
            id=palette_id,
            name=palette_name,
            colors=dict(self._current_palette_data)
        )
        self.theme_bridge._palettes[palette_id] = updated_palette

    # === DEBUG METHODS ===

    def _apply_debug(self):
        """Apply debug options."""
        objects_borders = self.objects_borders_cb.isChecked()
        self.user_prefs.set("objects_borders", objects_borders)
        self.debug_borders_changed.emit(objects_borders)

        self.debug_status.setText(tr("settings_options_applied"))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self.debug_status.setText(""))

    def cleanup(self):
        """Unregister theme observer and release held references."""
        try:
            self.theme_bridge.unregister_observer(self._on_theme_changed)
        except Exception:
            pass
        if hasattr(self, '_current_lang_data'):
            self._current_lang_data.clear()
        if hasattr(self, '_current_overrides'):
            self._current_overrides.clear()
        if hasattr(self, '_palette_color_rows'):
            self._palette_color_rows.clear()
        if hasattr(self, '_generated_color_rows'):
            self._generated_color_rows.clear()
