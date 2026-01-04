"""
QSS Builder - Generates Qt Style Sheets from GeneratedTheme.

Takes a GeneratedTheme with 90+ color properties and produces
a complete QSS stylesheet for the application.
"""

from .generator import GeneratedTheme


class QSSBuilder:
    """
    Builds QSS stylesheets from a GeneratedTheme.

    The builder creates styles for all standard Qt widgets,
    using the theme's color properties for consistency.
    """

    def build(self, theme: GeneratedTheme) -> str:
        """
        Build a complete QSS stylesheet from a theme.

        Args:
            theme: The generated theme with color properties

        Returns:
            Complete QSS stylesheet string
        """
        c = theme.colors  # Shorthand for cleaner templates

        sections = [
            self._build_global(c),
            self._build_menu(c),
            self._build_buttons(c),
            self._build_inputs(c),
            self._build_combobox(c),
            self._build_checkbox_radio(c),
            self._build_tree(c),
            self._build_table(c),
            self._build_tabs(c),
            self._build_scrollbar(c),
            self._build_splitter(c),
            self._build_groupbox(c),
            self._build_tooltip(c),
            self._build_progressbar(c),
            self._build_statusbar(c),
            self._build_toolbar(c),
        ]

        return "\n\n".join(sections)

    def _build_global(self, c: dict) -> str:
        """Build global widget styles."""
        return f"""
/* === GLOBAL === */
QWidget {{
    background-color: {c["panel_bg"]};
    color: {c["text_primary"]};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 9pt;
}}

QMainWindow {{
    background-color: {c["window_bg"]};
}}

QDialog {{
    background-color: {c["dialog_bg"]};
    color: {c["dialog_fg"]};
}}

QFrame {{
    border: none;
}}

QLabel {{
    background-color: transparent;
    color: {c["text_primary"]};
}}

QLabel:disabled {{
    color: {c["text_disabled"]};
}}
""".strip()

    def _build_menu(self, c: dict) -> str:
        """Build menu bar and dropdown menu styles."""
        return f"""
/* === MENU BAR === */
QMenuBar {{
    background-color: {c["menubar_bg"]};
    color: {c["menubar_fg"]};
    border: none;
    padding: 2px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 4px 8px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {c["menubar_hover_bg"]};
    color: {c["menubar_hover_fg"]};
}}

QMenuBar::item:pressed {{
    background-color: {c["menubar_selected_bg"]};
    color: {c["menubar_selected_fg"]};
}}

/* === DROPDOWN MENUS === */
QMenu {{
    background-color: {c["menu_bg"]};
    color: {c["menu_fg"]};
    border: 1px solid {c["border_color"]};
    border-radius: 4px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 3px;
}}

QMenu::item:selected {{
    background-color: {c["menu_hover_bg"]};
    color: {c["menu_hover_fg"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {c["menu_separator"]};
    margin: 4px 8px;
}}

QMenu::indicator {{
    width: 16px;
    height: 16px;
    margin-left: 4px;
}}
""".strip()

    def _build_buttons(self, c: dict) -> str:
        """Build button styles."""
        return f"""
/* === BUTTONS === */
QPushButton {{
    background-color: {c["button_bg"]};
    color: {c["button_fg"]};
    border: 1px solid {c["button_border"]};
    border-radius: 4px;
    padding: 6px 16px;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {c["button_hover_bg"]};
    color: {c["button_hover_fg"]};
}}

QPushButton:pressed {{
    background-color: {c["button_pressed_bg"]};
}}

QPushButton:disabled {{
    background-color: {c["button_disabled_bg"]};
    color: {c["button_disabled_fg"]};
    border-color: {c["border_color"]};
}}

QPushButton:focus {{
    border: 1px solid {c["focus_border"]};
}}

/* Primary/Default button style */
QPushButton[default="true"], QPushButton:default {{
    background-color: {c["accent"]};
    color: {c["selected_fg"]};
    border-color: {c["accent"]};
}}

QPushButton[default="true"]:hover, QPushButton:default:hover {{
    background-color: {c["pressed_bg"]};
}}
""".strip()

    def _build_inputs(self, c: dict) -> str:
        """Build input field styles."""
        return f"""
/* === INPUT FIELDS === */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {c["input_bg"]};
    color: {c["input_fg"]};
    border: 1px solid {c["input_border"]};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {c["selected_bg"]};
    selection-color: {c["selected_fg"]};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {c["input_focus_border"]};
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {c["input_disabled_bg"]};
    color: {c["input_disabled_fg"]};
}}

QLineEdit::placeholder {{
    color: {c["input_placeholder"]};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px;
    border-left: 1px solid {c["border_color"]};
    border-radius: 0;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px;
    border-left: 1px solid {c["border_color"]};
    border-radius: 0;
}}
""".strip()

    def _build_combobox(self, c: dict) -> str:
        """Build combobox styles."""
        return f"""
/* === COMBOBOX === */
QComboBox {{
    background-color: {c["combo_bg"]};
    color: {c["combo_fg"]};
    border: 1px solid {c["combo_border"]};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 20px;
}}

QComboBox:hover {{
    border-color: {c["accent"]};
}}

QComboBox:focus {{
    border-color: {c["focus_border"]};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 20px;
    border: none;
}}

QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {c["menu_bg"]};
    color: {c["menu_fg"]};
    border: 1px solid {c["border_color"]};
    selection-background-color: {c["menu_hover_bg"]};
    selection-color: {c["menu_hover_fg"]};
    outline: none;
}}
""".strip()

    def _build_checkbox_radio(self, c: dict) -> str:
        """Build checkbox and radio button styles."""
        return f"""
/* === CHECKBOX === */
QCheckBox {{
    spacing: 8px;
    color: {c["text_primary"]};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c["checkbox_border"]};
    border-radius: 3px;
    background-color: {c["checkbox_bg"]};
}}

QCheckBox::indicator:hover {{
    border-color: {c["accent"]};
}}

QCheckBox::indicator:checked {{
    background-color: {c["checkbox_checked_bg"]};
    border-color: {c["checkbox_checked_border"]};
}}

QCheckBox:disabled {{
    color: {c["text_disabled"]};
}}

/* === RADIO BUTTON === */
QRadioButton {{
    spacing: 8px;
    color: {c["text_primary"]};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c["checkbox_border"]};
    border-radius: 8px;
    background-color: {c["checkbox_bg"]};
}}

QRadioButton::indicator:hover {{
    border-color: {c["accent"]};
}}

QRadioButton::indicator:checked {{
    background-color: {c["checkbox_checked_bg"]};
    border-color: {c["checkbox_checked_border"]};
}}

QRadioButton:disabled {{
    color: {c["text_disabled"]};
}}
""".strip()

    def _build_tree(self, c: dict) -> str:
        """Build tree widget styles."""
        return f"""
/* === TREE WIDGET === */
QTreeView, QTreeWidget {{
    background-color: {c["tree_bg"]};
    color: {c["tree_fg"]};
    border: 1px solid {c["border_color"]};
    border-radius: 4px;
    outline: none;
    alternate-background-color: {c["tree_line2_bg"]};
}}

QTreeView::item, QTreeWidget::item {{
    padding: 4px;
    border: none;
}}

QTreeView::item:hover, QTreeWidget::item:hover {{
    background-color: {c["tree_hover_bg"]};
}}

QTreeView::item:selected, QTreeWidget::item:selected {{
    background-color: {c["tree_selected_bg"]};
    color: {c["tree_selected_fg"]};
}}

QTreeView::branch {{
    background-color: transparent;
}}

QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {{
    border-image: none;
}}

QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {{
    border-image: none;
}}

QHeaderView::section {{
    background-color: {c["tree_header_bg"]};
    color: {c["tree_header_fg"]};
    padding: 6px;
    border: none;
    border-right: 1px solid {c["border_color"]};
    border-bottom: 1px solid {c["border_color"]};
}}
""".strip()

    def _build_table(self, c: dict) -> str:
        """Build table widget styles."""
        return f"""
/* === TABLE WIDGET === */
QTableView, QTableWidget {{
    background-color: {c["grid_bg"]};
    color: {c["grid_fg"]};
    border: 1px solid {c["border_color"]};
    border-radius: 4px;
    gridline-color: {c["grid_gridline"]};
    outline: none;
    alternate-background-color: {c["grid_line2_bg"]};
}}

QTableView::item, QTableWidget::item {{
    padding: 4px;
    border: none;
}}

QTableView::item:hover, QTableWidget::item:hover {{
    background-color: {c["grid_hover_bg"]};
}}

QTableView::item:selected, QTableWidget::item:selected {{
    background-color: {c["grid_selected_bg"]};
    color: {c["grid_selected_fg"]};
}}

QTableView QHeaderView::section, QTableWidget QHeaderView::section {{
    background-color: {c["grid_header_bg"]};
    color: {c["grid_header_fg"]};
    padding: 6px;
    border: none;
    border-right: 1px solid {c["border_color"]};
    border-bottom: 1px solid {c["border_color"]};
}}

QTableCornerButton::section {{
    background-color: {c["grid_header_bg"]};
    border: none;
    border-right: 1px solid {c["border_color"]};
    border-bottom: 1px solid {c["border_color"]};
}}
""".strip()

    def _build_tabs(self, c: dict) -> str:
        """Build tab widget styles."""
        return f"""
/* === TAB WIDGET === */
QTabWidget::pane {{
    background-color: {c["surface_bg"]};
    border: 1px solid {c["border_color"]};
    border-radius: 4px;
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {c["tab_bg"]};
    color: {c["tab_fg"]};
    padding: 8px 16px;
    border: 1px solid {c["border_color"]};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}}

QTabBar::tab:hover {{
    background-color: {c["tab_hover_bg"]};
}}

QTabBar::tab:selected {{
    background-color: {c["tab_selected_bg"]};
    color: {c["tab_selected_fg"]};
    border-bottom: 1px solid {c["tab_selected_bg"]};
}}

QTabBar::close-button {{
    subcontrol-position: right;
    padding: 2px;
}}

QTabBar::close-button:hover {{
    background-color: {c["hover_bg"]};
    border-radius: 2px;
}}
""".strip()

    def _build_scrollbar(self, c: dict) -> str:
        """Build scrollbar styles."""
        return f"""
/* === SCROLLBAR === */
QScrollBar:vertical {{
    background-color: {c["scrollbar_bg"]};
    width: 12px;
    margin: 0;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {c["scrollbar_handle"]};
    min-height: 30px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c["scrollbar_handle_hover"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {c["scrollbar_bg"]};
    height: 12px;
    margin: 0;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {c["scrollbar_handle"]};
    min-width: 30px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {c["scrollbar_handle_hover"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
""".strip()

    def _build_splitter(self, c: dict) -> str:
        """Build splitter styles."""
        return f"""
/* === SPLITTER === */
QSplitter::handle {{
    background-color: {c["splitter_bg"]};
}}

QSplitter::handle:horizontal {{
    width: 4px;
}}

QSplitter::handle:vertical {{
    height: 4px;
}}

QSplitter::handle:hover {{
    background-color: {c["splitter_hover_bg"]};
}}
""".strip()

    def _build_groupbox(self, c: dict) -> str:
        """Build group box styles."""
        return f"""
/* === GROUPBOX === */
QGroupBox {{
    border: 1px solid {c["groupbox_border"]};
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: {c["groupbox_title"]};
    background-color: {c["panel_bg"]};
}}
""".strip()

    def _build_tooltip(self, c: dict) -> str:
        """Build tooltip styles."""
        return f"""
/* === TOOLTIP === */
QToolTip {{
    background-color: {c["tooltip_bg"]};
    color: {c["tooltip_fg"]};
    border: 1px solid {c["tooltip_border"]};
    border-radius: 4px;
    padding: 4px 8px;
}}
""".strip()

    def _build_progressbar(self, c: dict) -> str:
        """Build progress bar styles."""
        return f"""
/* === PROGRESS BAR === */
QProgressBar {{
    background-color: {c["progress_bg"]};
    border: 1px solid {c["border_color"]};
    border-radius: 4px;
    text-align: center;
    color: {c["progress_text"]};
}}

QProgressBar::chunk {{
    background-color: {c["progress_fg"]};
    border-radius: 3px;
}}
""".strip()

    def _build_statusbar(self, c: dict) -> str:
        """Build status bar styles."""
        return f"""
/* === STATUS BAR === */
QStatusBar {{
    background-color: {c["statusbar_bg"]};
    color: {c["statusbar_fg"]};
    border-top: 1px solid {c["border_color"]};
}}

QStatusBar::item {{
    border: none;
}}

QStatusBar QLabel {{
    padding: 2px 4px;
}}
""".strip()

    def _build_toolbar(self, c: dict) -> str:
        """Build toolbar styles."""
        return f"""
/* === TOOLBAR === */
QToolBar {{
    background-color: {c["toolbar_bg"]};
    border: none;
    spacing: 4px;
    padding: 4px;
}}

QToolBar::separator {{
    background-color: {c["border_color"]};
    width: 1px;
    margin: 4px 8px;
}}

QToolButton {{
    background-color: {c["toolbar_button_bg"]};
    color: {c["toolbar_button_fg"]};
    border: 1px solid {c["toolbar_button_border"]};
    border-radius: 4px;
    padding: 4px;
}}

QToolButton:hover {{
    background-color: {c["toolbar_button_hover_bg"]};
    color: {c["toolbar_button_hover_fg"]};
}}

QToolButton:pressed {{
    background-color: {c["toolbar_button_pressed_bg"]};
}}

QToolButton:checked {{
    background-color: {c["selected_bg"]};
}}
""".strip()
