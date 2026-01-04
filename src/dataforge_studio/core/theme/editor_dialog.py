"""
Theme Editor Dialog - Visual editor for theme palettes.

Provides a dialog for editing theme palettes with live preview.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QGroupBox, QColorDialog, QMessageBox,
    QFrame, QSizePolicy, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .palette import ThemePalette, DEFAULT_DARK_PALETTE, DEFAULT_LIGHT_PALETTE
from .generator import ThemeGenerator, GeneratedTheme
from .preview_widget import ThemePreviewWidget


class ColorButton(QPushButton):
    """Button that displays and allows editing a color."""

    color_changed = Signal(str)

    def __init__(self, color: str = "#000000", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(60, 24)
        self._update_style()
        self.clicked.connect(self._pick_color)

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str):
        self._color = value
        self._update_style()

    def _update_style(self):
        """Update button appearance to show current color."""
        # Calculate contrasting text color
        qcolor = QColor(self._color)
        luminance = (0.299 * qcolor.red() + 0.587 * qcolor.green() + 0.114 * qcolor.blue()) / 255
        text_color = "#000000" if luminance > 0.5 else "#ffffff"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                color: {text_color};
                border: 1px solid #555;
                border-radius: 3px;
                font-size: 8pt;
            }}
            QPushButton:hover {{
                border: 2px solid #888;
            }}
        """)
        self.setText(self._color.upper())

    def _pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(QColor(self._color), self, "Select Color")
        if color.isValid():
            self._color = color.name()
            self._update_style()
            self.color_changed.emit(self._color)


class ThemeEditorDialog(QDialog):
    """
    Dialog for editing theme palettes with live preview.

    Usage:
        dialog = ThemeEditorDialog(parent)
        dialog.set_palette(current_palette)
        if dialog.exec() == QDialog.Accepted:
            new_palette = dialog.get_palette()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Editor")
        self.setMinimumSize(700, 500)

        self._generator = ThemeGenerator()
        self._palette: Optional[ThemePalette] = None

        self._setup_ui()
        self._connect_signals()

        # Start with default dark palette
        self.set_palette(DEFAULT_DARK_PALETTE)

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QHBoxLayout(self)

        # Left side: Color editors
        left_panel = QScrollArea()
        left_panel.setWidgetResizable(True)
        left_panel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_panel.setMinimumWidth(320)
        left_panel.setMaximumWidth(400)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Theme name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Theme Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        left_layout.addLayout(name_layout)

        # Structure colors group
        structure_group = QGroupBox("Structure Colors")
        structure_form = QFormLayout(structure_group)

        self.bg_btn = ColorButton()
        structure_form.addRow("Background:", self.bg_btn)

        self.surface_btn = ColorButton()
        structure_form.addRow("Surface:", self.surface_btn)

        self.border_btn = ColorButton()
        structure_form.addRow("Border:", self.border_btn)

        self.accent_btn = ColorButton()
        structure_form.addRow("Accent:", self.accent_btn)

        left_layout.addWidget(structure_group)

        # Text / Icon colors group
        text_group = QGroupBox("Text / Icon Colors")
        text_form = QFormLayout(text_group)

        self.text_btn = ColorButton()
        text_form.addRow("Primary:", self.text_btn)

        self.text_secondary_btn = ColorButton()
        text_form.addRow("Secondary:", self.text_secondary_btn)

        self.icon_btn = ColorButton()
        text_form.addRow("Icon:", self.icon_btn)

        left_layout.addWidget(text_group)

        # Semantic colors group
        semantic_group = QGroupBox("Semantic Colors")
        semantic_form = QFormLayout(semantic_group)

        self.info_btn = ColorButton()
        semantic_form.addRow("Info:", self.info_btn)

        self.warning_btn = ColorButton()
        semantic_form.addRow("Warning:", self.warning_btn)

        self.error_btn = ColorButton()
        semantic_form.addRow("Error:", self.error_btn)

        self.important_btn = ColorButton()
        semantic_form.addRow("Important:", self.important_btn)

        left_layout.addWidget(semantic_group)

        # Preset buttons
        preset_group = QGroupBox("Presets")
        preset_layout = QHBoxLayout(preset_group)

        dark_btn = QPushButton("Default Dark")
        dark_btn.clicked.connect(lambda: self.set_palette(DEFAULT_DARK_PALETTE))
        preset_layout.addWidget(dark_btn)

        light_btn = QPushButton("Default Light")
        light_btn.clicked.connect(lambda: self.set_palette(DEFAULT_LIGHT_PALETTE))
        preset_layout.addWidget(light_btn)

        left_layout.addWidget(preset_group)

        left_layout.addStretch()

        left_panel.setWidget(left_widget)
        layout.addWidget(left_panel)

        # Right side: Preview
        right_panel = QVBoxLayout()

        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        right_panel.addWidget(preview_label)

        self.preview = ThemePreviewWidget()
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_panel.addWidget(self.preview)

        # Theme info
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #888; font-size: 8pt;")
        right_panel.addWidget(self.info_label)

        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.accept)
        button_layout.addWidget(apply_btn)

        right_panel.addLayout(button_layout)

        layout.addLayout(right_panel)

    def _connect_signals(self):
        """Connect color change signals to update preview."""
        self.name_edit.textChanged.connect(self._on_palette_changed)

        for btn in [self.bg_btn, self.surface_btn, self.border_btn, self.accent_btn,
                    self.text_btn, self.text_secondary_btn, self.icon_btn,
                    self.info_btn, self.warning_btn, self.error_btn, self.important_btn]:
            btn.color_changed.connect(self._on_palette_changed)

    def _on_palette_changed(self):
        """Called when any palette value changes."""
        palette = self._build_palette()
        theme = self._generator.generate(palette)
        self.preview.update_theme(theme)

        # Update info label
        mode = "Dark" if theme.is_dark else "Light"
        self.info_label.setText(f"Mode: {mode} (auto-detected from background luminosity)")

    def _build_palette(self) -> ThemePalette:
        """Build a palette from current UI values."""
        return ThemePalette(
            name=self.name_edit.text() or "Untitled",
            background=self.bg_btn.color,
            surface=self.surface_btn.color,
            border=self.border_btn.color,
            accent=self.accent_btn.color,
            text=self.text_btn.color,
            text_secondary=self.text_secondary_btn.color,
            icon=self.icon_btn.color,
            info=self.info_btn.color,
            warning=self.warning_btn.color,
            error=self.error_btn.color,
            important=self.important_btn.color,
        )

    def set_palette(self, palette: ThemePalette):
        """
        Set the palette to edit.

        Args:
            palette: ThemePalette to load into the editor
        """
        self._palette = palette

        # Update UI
        self.name_edit.setText(palette.name)
        self.bg_btn.color = palette.background
        self.surface_btn.color = palette.surface
        self.border_btn.color = palette.border
        self.accent_btn.color = palette.accent
        self.text_btn.color = palette.text
        self.text_secondary_btn.color = palette.text_secondary
        self.icon_btn.color = palette.icon
        self.info_btn.color = palette.info
        self.warning_btn.color = palette.warning
        self.error_btn.color = palette.error
        self.important_btn.color = palette.important

        # Update preview
        self._on_palette_changed()

    def get_palette(self) -> ThemePalette:
        """
        Get the edited palette.

        Returns:
            ThemePalette with current editor values
        """
        return self._build_palette()
