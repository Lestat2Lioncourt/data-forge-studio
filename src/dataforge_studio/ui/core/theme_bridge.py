"""
Theme Bridge - Extends window-template ThemeManager with Observer pattern
Fusion of window-template theme system and DataForge Studio theme management
"""

import json
import logging
from pathlib import Path
from typing import List, Callable, Dict
from ..templates.window.theme_manager import ThemeManager as BaseThemeManager

logger = logging.getLogger(__name__)
from .theme_image_generator import generate_dropdown_arrow, generate_branch_images

# Path to custom themes
CUSTOM_THEMES_PATH = Path(__file__).parent.parent.parent.parent.parent / "_AppConfig" / "themes"


class ThemeBridge(BaseThemeManager):
    """
    Extended theme manager with Observer pattern for DataForge Studio.

    This class bridges the window-template theme system with DataForge Studio's
    needs, adding:
    - Observer pattern for notifying widgets of theme changes
    - Additional QSS generation methods for custom widgets
    - Support for DataForge-specific color keys
    - Auto-loading of custom themes from _AppConfig/themes/
    """

    _instance = None

    def __init__(self, theme_file=None):
        super().__init__(theme_file)
        self._observers: List[Callable] = []
        self._load_custom_themes()

    def _load_custom_themes(self):
        """Load all custom themes from _AppConfig/themes/ directory."""
        if not CUSTOM_THEMES_PATH.exists():
            return

        for theme_file in CUSTOM_THEMES_PATH.glob("*.json"):
            theme_id = theme_file.stem
            if theme_id not in self.themes:
                try:
                    with open(theme_file, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)

                        # Handle "patch" type themes - expand to minimal
                        if theme_data.get("type") == "patch":
                            theme_data = self._expand_patch_theme(theme_data)

                        self.themes[theme_id] = theme_data
                except Exception as e:
                    logger.warning(f"Failed to load custom theme '{theme_id}': {e}")

    def _expand_patch_theme(self, patch_data: Dict) -> Dict:
        """
        Expand a patch theme to a minimal theme.

        Patch themes reference a base theme and override specific colors.

        Args:
            patch_data: Theme data with type="patch", base, and overrides

        Returns:
            Theme data as type="minimal" with merged palette
        """
        base_id = patch_data.get("base", "minimal_dark")
        overrides = patch_data.get("overrides", {})

        # Get base theme palette
        if base_id in self.themes:
            base_theme = self.themes[base_id]
            base_palette = dict(base_theme.get("palette", {}))
        else:
            # Fallback to minimal_dark defaults
            base_palette = {
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
            }

        # Apply overrides
        for key, value in overrides.items():
            base_palette[key] = value
            # Accent also affects Selected_BG for selection colors
            if key == "Accent":
                base_palette["Selected_BG"] = value

        # Return as minimal theme
        return {
            "name": patch_data.get("name", "Custom Theme"),
            "type": "minimal",
            "palette": base_palette
        }

    @classmethod
    def get_instance(cls):
        """Get singleton instance of ThemeBridge"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_observer(self, callback: Callable):
        """
        Register a callback to be notified of theme changes.

        Args:
            callback: Function to call when theme changes.
                     Will receive theme_colors dict as argument.
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def unregister_observer(self, callback: Callable):
        """
        Unregister a callback.

        Args:
            callback: Previously registered callback
        """
        if callback in self._observers:
            self._observers.remove(callback)

    def apply_theme(self, window, theme_name: str):
        """
        Apply theme and notify observers.

        Args:
            window: TemplateWindow instance
            theme_name: Theme identifier (e.g., "dark_mode")
        """
        # Apply base theme to window-template components
        super().apply_theme(window, theme_name)

        # Notify all observers
        theme_colors = self.get_theme_colors(theme_name)
        self._notify_observers(theme_colors)

    def _notify_observers(self, theme_colors: Dict[str, str]):
        """Notify all registered observers of theme change"""
        for observer in self._observers:
            try:
                observer(theme_colors)
            except Exception as e:
                logger.error(f"Error notifying theme observer: {e}")

    def get_qss_for_widget(self, widget_type: str, theme_name: str = None) -> str:
        """
        Generate QSS stylesheet for specific widget type.

        Args:
            widget_type: Type of widget ("QTreeWidget", "QTableWidget", etc.)
            theme_name: Theme to use (uses current if None)

        Returns:
            QSS stylesheet string
        """
        if theme_name is None:
            theme_name = self.current_theme

        colors = self.get_theme_colors(theme_name)

        if widget_type == "QTreeWidget":
            return f"""
                QTreeWidget {{
                    background-color: {colors['tree_line1_bg']};
                    color: {colors['tree_line1_fg']};
                    border: 1px solid {colors['border_color']};
                    alternate-background-color: {colors['tree_line2_bg']};
                }}
                QTreeWidget::item {{
                    color: {colors['tree_line1_fg']};
                }}
                QTreeWidget::item:alternate {{
                    background-color: {colors['tree_line2_bg']};
                    color: {colors['tree_line2_fg']};
                }}
                QTreeWidget::item:selected {{
                    background-color: {colors['tree_selected_bg']};
                    color: {colors['tree_selected_fg']};
                }}
                QTreeWidget::item:hover {{
                    background-color: {colors['tree_hover_bg']};
                }}
                QTreeWidget::branch {{
                    background: {colors['tree_line1_bg']};
                }}
                QTreeWidget::branch:has-siblings:!adjoins-item {{
                    background: url({str(ASSETS_PATH / 'branch-vline.png').replace(chr(92), '/')}) center center no-repeat;
                }}
                QTreeWidget::branch:has-siblings:adjoins-item {{
                    background: url({str(ASSETS_PATH / 'branch-more.png').replace(chr(92), '/')}) center center no-repeat;
                }}
                QTreeWidget::branch:!has-siblings:adjoins-item {{
                    background: url({str(ASSETS_PATH / 'branch-end.png').replace(chr(92), '/')}) center center no-repeat;
                }}
                QHeaderView::section {{
                    background-color: {colors['tree_heading_bg']};
                    color: {colors['tree_heading_fg']};
                    padding: 4px;
                    border: 1px solid {colors['border_color']};
                }}
            """
        elif widget_type == "QTableWidget":
            return f"""
                QTableWidget {{
                    background-color: {colors['grid_line1_bg']};
                    color: {colors['grid_line1_fg']};
                    gridline-color: {colors['grid_gridline']};
                    border: 1px solid {colors['border_color']};
                    alternate-background-color: {colors['grid_line2_bg']};
                }}
                QTableWidget::item {{
                    color: {colors['grid_line1_fg']};
                }}
                QTableWidget::item:alternate {{
                    background-color: {colors['grid_line2_bg']};
                    color: {colors['grid_line2_fg']};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors['grid_selected_bg']};
                    color: {colors['grid_selected_fg']};
                }}
                QTableWidget::item:hover {{
                    background-color: {colors['grid_hover_bg']};
                }}
                QHeaderView::section {{
                    background-color: {colors['grid_header_bg']};
                    color: {colors['grid_header_fg']};
                    padding: 4px;
                    border: 1px solid {colors['border_color']};
                }}
            """
        elif widget_type == "QTextEdit":
            return f"""
                QTextEdit {{
                    background-color: {colors['input_bg']};
                    color: {colors['input_fg']};
                    border: 1px solid {colors['input_border']};
                    padding: 4px;
                }}
                QTextEdit:focus {{
                    border: 2px solid {colors['input_focus_border']};
                }}
            """
        elif widget_type == "QLineEdit":
            return f"""
                QLineEdit {{
                    background-color: {colors['input_bg']};
                    color: {colors['input_fg']};
                    border: 1px solid {colors['input_border']};
                    padding: 4px;
                    border-radius: 2px;
                }}
                QLineEdit:focus {{
                    border: 2px solid {colors['input_focus_border']};
                }}
            """
        elif widget_type == "QComboBox":
            return f"""
                QComboBox {{
                    background-color: {colors['input_bg']};
                    color: {colors['input_fg']};
                    border: 1px solid {colors['input_border']};
                    padding: 4px;
                    border-radius: 2px;
                }}
                QComboBox:focus {{
                    border: 2px solid {colors['input_focus_border']};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox::down-arrow {{
                    /* Arrow image set by global QSS */
                    width: 10px;
                    height: 10px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {colors['dd_menu_bg']};
                    color: {colors['dd_menu_fg']};
                    selection-background-color: {colors['dd_menu_hover_bg']};
                    border: 1px solid {colors['border_color']};
                }}
            """
        elif widget_type == "QPushButton":
            return f"""
                QPushButton {{
                    background-color: {colors['panel_bg']};
                    color: {colors['normal_fg']};
                    border: 1px solid {colors['border_color']};
                    padding: 5px 15px;
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    background-color: {colors['button_hover_bg']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['button_pressed_bg']};
                }}
                QPushButton:disabled {{
                    background-color: {colors['border_color']};
                    color: {colors['border_color']};
                }}
            """
        elif widget_type == "QCheckBox":
            return f"""
                QCheckBox {{
                    color: {colors['normal_fg']};
                    spacing: 5px;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 1px solid {colors['border_color']};
                    background-color: {colors['input_bg']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {colors['tree_selected_bg']};
                    border: 1px solid {colors['tree_selected_bg']};
                }}
                QCheckBox::indicator:hover {{
                    border: 1px solid {colors['input_focus_border']};
                }}
            """
        elif widget_type == "QGroupBox":
            return f"""
                QGroupBox {{
                    color: {colors['normal_fg']};
                    border: 1px solid {colors['border_color']};
                    border-radius: 4px;
                    margin-top: 10px;
                    padding-top: 10px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }}
            """
        elif widget_type == "QLabel":
            return f"""
                QLabel {{
                    color: {colors['normal_fg']};
                    background-color: transparent;
                }}
            """
        else:
            # Default widget styling
            return f"""
                QWidget {{
                    background-color: {colors['window_bg']};
                    color: {colors['normal_fg']};
                }}
            """

    def generate_global_qss(self, theme_name: str = None) -> str:
        """
        Generate complete global QSS stylesheet for the entire application.

        This creates a comprehensive stylesheet that can be applied to QApplication
        to theme all widgets consistently.

        Args:
            theme_name: Theme to use (uses current if None)

        Returns:
            Complete QSS stylesheet string
        """
        if theme_name is None:
            theme_name = self.current_theme
        else:
            # Update current_theme when explicitly specified
            self.current_theme = theme_name

        colors = self.get_theme_colors(theme_name)

        # Get border radius (default to 0 if not specified)
        border_radius = colors.get('frame_border_radius', '0')
        # Ensure it's a number with 'px' suffix
        if isinstance(border_radius, str) and not border_radius.endswith('px'):
            border_radius = f"{border_radius}px"

        # Get tree branch color and generate/use cached images
        branch_color = colors.get('tree_branch_color', '#E6E6E6')
        theme_assets_dir = CUSTOM_THEMES_PATH / theme_name / "assets"

        # Check if color matches cached version (stored in color.txt)
        color_file = theme_assets_dir / "branch_color.txt"
        cached_color = None
        if color_file.exists():
            try:
                cached_color = color_file.read_text().strip()
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Could not read branch color cache: {e}")

        # Generate images if custom color and (no cache or color changed)
        if branch_color.upper() != '#E6E6E6':
            if cached_color != branch_color or not (theme_assets_dir / "branch-vline.png").exists():
                # Generate images with custom color
                branch_images = generate_branch_images(branch_color, theme_assets_dir)
                # Save color for cache check
                try:
                    color_file.write_text(branch_color)
                except OSError as e:
                    logger.debug(f"Could not write branch color cache: {e}")
            else:
                # Use cached custom images
                branch_images = {
                    "vline": str(theme_assets_dir / "branch-vline.png"),
                    "more": str(theme_assets_dir / "branch-more.png"),
                    "end": str(theme_assets_dir / "branch-end.png"),
                    "arrow_closed": str(theme_assets_dir / "branch-closed.png"),
                    "arrow_open": str(theme_assets_dir / "branch-open.png"),
                }
        else:
            # Use default images
            branch_images = {
                "vline": str(ASSETS_PATH / "branch-vline.png"),
                "more": str(ASSETS_PATH / "branch-more.png"),
                "end": str(ASSETS_PATH / "branch-end.png"),
                "arrow_closed": str(ASSETS_PATH / "branch-closed.png"),
                "arrow_open": str(ASSETS_PATH / "branch-open.png"),
            }

        # Generate dropdown arrow for ComboBox
        combo_fg = colors.get('combo_fg', colors.get('text_primary', '#E6E6E6'))
        dropdown_arrow_color_file = theme_assets_dir / "dropdown_arrow_color.txt"
        cached_dropdown_color = None
        if dropdown_arrow_color_file.exists():
            try:
                cached_dropdown_color = dropdown_arrow_color_file.read_text().strip()
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Could not read dropdown arrow cache: {e}")

        # Generate dropdown arrow if color changed or not exists
        dropdown_arrow_path = theme_assets_dir / "dropdown-arrow.png"
        if cached_dropdown_color != combo_fg or not dropdown_arrow_path.exists():
            dropdown_arrow = generate_dropdown_arrow(combo_fg, theme_assets_dir)
            try:
                dropdown_arrow_color_file.write_text(combo_fg)
            except OSError as e:
                logger.debug(f"Could not write dropdown arrow cache: {e}")
        else:
            dropdown_arrow = str(dropdown_arrow_path)

        # Convert to CSS-friendly paths
        branch_vline = branch_images["vline"].replace("\\", "/")
        branch_more = branch_images["more"].replace("\\", "/")
        branch_end = branch_images["end"].replace("\\", "/")
        arrow_closed = branch_images["arrow_closed"].replace("\\", "/")
        arrow_open = branch_images["arrow_open"].replace("\\", "/")
        dropdown_arrow_css = dropdown_arrow.replace("\\", "/") if dropdown_arrow else ""

        # Build comprehensive QSS
        qss = f"""
        /* ========== BASE WIDGET ========== */
        QWidget {{
            background-color: {colors['window_bg']};
            color: {colors['text_primary']};
            font-size: 9pt;
        }}

        /* ========== MAIN WINDOW CONTAINER ========== */
        #CentralWidget {{
            border-radius: {border_radius};
        }}

        /* ========== FRAMES/PANELS ========== */
        QFrame {{
            border-radius: {border_radius};
        }}
        QGroupBox {{
            border: 1px solid {colors['border_color']};
            border-radius: {border_radius};
            margin-top: 8px;
            padding-top: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: {colors['text_primary']};
        }}

        /* ========== LABELS ========== */
        QLabel {{
            color: {colors['text_primary']};
            background-color: transparent;
        }}

        /* ========== BUTTONS (panels/dialogs) ========== */
        QPushButton {{
            background-color: {colors['button_bg']};
            color: {colors['button_fg']};
            border: 1px solid {colors['button_border']};
            padding: 5px 15px;
            border-radius: 2px;
        }}
        QPushButton:hover {{
            background-color: {colors['button_hover_bg']};
            color: {colors['button_hover_fg']};
        }}
        QPushButton:pressed {{
            background-color: {colors['button_pressed_bg']};
        }}
        QPushButton:disabled {{
            background-color: {colors['panel_bg']};
            color: {colors['text_disabled']};
        }}

        /* ========== TOOLBAR BUTTONS ========== */
        #ToolbarWidget QPushButton {{
            background-color: {colors.get('toolbarbtn_bg', colors['panel_bg'])};
            color: {colors.get('toolbarbtn_fg', colors['text_primary'])};
            border: 1px solid {colors.get('toolbarbtn_border', colors['panel_bg'])};
            padding: 4px 10px;
            border-radius: 2px;
        }}
        #ToolbarWidget QPushButton:hover {{
            background-color: {colors.get('toolbarbtn_hover_bg', colors['hover_bg'])};
            color: {colors.get('toolbarbtn_hover_fg', colors['text_primary'])};
        }}
        #ToolbarWidget QPushButton:pressed {{
            background-color: {colors.get('toolbarbtn_pressed_bg', colors['selected_bg'])};
        }}
        #ToolbarWidget QPushButton:disabled {{
            background-color: {colors['panel_bg']};
            color: {colors['text_disabled']};
        }}

        /* ========== INPUT FIELDS ========== */
        QLineEdit {{
            background-color: {colors['input_bg']};
            color: {colors['input_fg']};
            border: 1px solid {colors['input_border']};
            padding: 4px;
            border-radius: 2px;
        }}
        QLineEdit:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}
        QLineEdit:disabled {{
            background-color: {colors['panel_bg']};
            color: {colors['text_disabled']};
        }}

        QTextEdit {{
            background-color: {colors['editor_bg']};
            color: {colors['editor_fg']};
            border: 1px solid {colors['input_border']};
            padding: 4px;
        }}
        QTextEdit:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}

        QPlainTextEdit {{
            background-color: {colors['editor_bg']};
            color: {colors['editor_fg']};
            border: 1px solid {colors['input_border']};
            padding: 4px;
        }}
        QPlainTextEdit:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}

        /* ========== COMBOBOX ========== */
        QComboBox {{
            background-color: {colors['combo_bg']};
            color: {colors['combo_fg']};
            border: 1px solid {colors['input_border']};
            padding: 4px;
            border-radius: 2px;
        }}
        QComboBox:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: url({dropdown_arrow_css});
            width: 10px;
            height: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors['dd_menu_bg']};
            color: {colors['dd_menu_fg']};
            selection-background-color: {colors['dd_menu_hover_bg']};
            border: 1px solid {colors['border_color']};
            outline: none;
        }}

        /* ========== TREE WIDGET ========== */
        QTreeWidget {{
            background-color: {colors['tree_line1_bg']};
            color: {colors['tree_line1_fg']};
            border: 1px solid {colors['border_color']};
            border-radius: {border_radius};
            alternate-background-color: {colors['tree_line2_bg']};
            outline: none;
        }}
        QTreeWidget::item {{
            padding: 0px;
            color: {colors['tree_line1_fg']};
        }}
        QTreeWidget::item:alternate {{
            background-color: {colors['tree_line2_bg']};
            color: {colors['tree_line2_fg']};
        }}
        QTreeWidget::item:selected {{
            background-color: {colors['tree_selected_bg']};
            color: {colors['tree_selected_fg']};
        }}
        QTreeWidget::item:hover {{
            background-color: {colors['tree_hover_bg']};
        }}
        /* Tree branch lines using centered SVG images */
        QTreeWidget::branch {{
            background: {colors['tree_line1_bg']};
        }}
        /* Vertical line continuation (│) */
        QTreeWidget::branch:has-siblings:!adjoins-item {{
            background: url({branch_vline}) center center no-repeat;
        }}
        /* Intermediate children (├) */
        QTreeWidget::branch:has-siblings:adjoins-item {{
            background: url({branch_more}) center center no-repeat;
        }}
        /* Last child (└) */
        QTreeWidget::branch:!has-siblings:adjoins-item {{
            background: url({branch_end}) center center no-repeat;
        }}
        /* Expand/collapse arrows */
        /* Override background to transparent so arrows are visible */
        QTreeWidget::branch:has-children:closed {{
            background: {colors['tree_line1_bg']};
            image: url({arrow_closed});
        }}
        QTreeWidget::branch:has-children:open {{
            background: {colors['tree_line1_bg']};
            image: url({arrow_open});
        }}

        /* ========== TABLE WIDGET ========== */
        QTableWidget {{
            background-color: {colors['grid_line1_bg']};
            color: {colors['grid_line1_fg']};
            border: 1px solid {colors['border_color']};
            border-radius: {border_radius};
            alternate-background-color: {colors['grid_line2_bg']};
            outline: none;
            font-family: Consolas;
            font-size: 9pt;
            gridline-color: transparent;
        }}
        QTableWidget::item {{
            padding: 0px;
            margin: 0px;
            border: none;
            color: {colors['grid_line1_fg']};
        }}
        QTableWidget::item:alternate {{
            background-color: {colors['grid_line2_bg']};
            color: {colors['grid_line2_fg']};
        }}
        QTableWidget::item:selected {{
            background-color: {colors['grid_selected_bg']};
            color: {colors['grid_selected_fg']};
        }}
        QTableWidget::item:hover {{
            background-color: {colors['grid_hover_bg']};
        }}

        /* ========== HEADER VIEWS ========== */
        /* Default header style (used by tables) */
        QHeaderView::section {{
            background-color: {colors['grid_header_bg']};
            color: {colors['grid_header_fg']};
            padding: 4px;
            border: 1px solid {colors['border_color']};
            border-top: none;
            border-left: none;
        }}
        QHeaderView::section:hover {{
            background-color: {colors['hover_bg']};
        }}
        /* TreeWidget specific header */
        QTreeWidget QHeaderView::section {{
            background-color: {colors['tree_heading_bg']};
            color: {colors['tree_heading_fg']};
        }}

        /* ========== TABS ========== */
        QTabWidget::pane {{
            border: 1px solid {colors['border_color']};
            background-color: {colors['window_bg']};
        }}
        QTabBar::tab {{
            background-color: {colors['tab_bg']};
            color: {colors['tab_fg']};
            border: 1px solid {colors['border_color']};
            padding: 6px 12px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {colors['tab_selected_bg']};
            color: {colors['tab_selected_fg']};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {colors['tab_hover_bg']};
        }}

        /* ========== SCROLLBARS ========== */
        QScrollBar:vertical {{
            background-color: {colors['scrollbar_bg']};
            width: 14px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background-color: {colors['scrollbar_handle_bg']};
            min-height: 20px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['scrollbar_handle_hover_bg']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QScrollBar:horizontal {{
            background-color: {colors['scrollbar_bg']};
            height: 14px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {colors['scrollbar_handle_bg']};
            min-width: 20px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['scrollbar_handle_hover_bg']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        /* ========== SPLITTER ========== */
        QSplitter::handle {{
            background-color: {colors.get('splitter_bg', '#5a5a5a')};
        }}
        QSplitter::handle:hover {{
            background-color: {colors.get('splitter_hover_bg', colors['focus_border'])};
        }}
        QSplitter::handle:horizontal {{
            width: 4px;
        }}
        QSplitter::handle:vertical {{
            height: 4px;
        }}

        /* ========== GROUPBOX ========== */
        QGroupBox {{
            color: {colors['groupbox_title_fg']};
            border: 1px solid {colors['groupbox_border']};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }}

        /* ========== CHECKBOX ========== */
        QCheckBox {{
            color: {colors['checkbox_fg']};
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors['checkbox_border']};
            background-color: {colors['checkbox_bg']};
            border-radius: 2px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors['checkbox_checked_bg']};
            border: 1px solid {colors['checkbox_checked_bg']};
        }}
        QCheckBox::indicator:hover {{
            border: 1px solid {colors['focus_border']};
        }}

        /* ========== RADIO BUTTON ========== */
        QRadioButton {{
            color: {colors['checkbox_fg']};
            spacing: 5px;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors['checkbox_border']};
            background-color: {colors['checkbox_bg']};
            border-radius: 8px;
        }}
        QRadioButton::indicator:checked {{
            background-color: {colors['checkbox_checked_bg']};
            border: 1px solid {colors['checkbox_checked_bg']};
        }}

        /* ========== TOOLTIP ========== */
        QToolTip {{
            background-color: {colors['tooltip_bg']};
            color: {colors['tooltip_fg']};
            border: 1px solid {colors['tooltip_border']};
            padding: 4px;
        }}

        /* ========== PROGRESS BAR ========== */
        QProgressBar {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            border-radius: 2px;
            text-align: center;
            color: {colors['text_primary']};
        }}
        QProgressBar::chunk {{
            background-color: {colors['selected_bg']};
        }}

        /* ========== MENU BAR (custom from window-template) ========== */
        /* Handled by window-template, but ensure consistency */

        /* ========== MESSAGE BOX / DIALOG ========== */
        QDialog {{
            background-color: {colors['window_bg']};
            color: {colors['text_primary']};
        }}
        QMessageBox {{
            background-color: {colors['window_bg']};
        }}
        """

        return qss


# Convenience function for global access
def get_theme_bridge():
    """Get the global ThemeBridge instance"""
    return ThemeBridge.get_instance()
