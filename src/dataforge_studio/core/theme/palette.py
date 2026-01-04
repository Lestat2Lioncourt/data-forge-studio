"""
Theme Palette - Minimal color definition for theme generation.

A palette contains only the essential colors that a user needs to define.
The ThemeGenerator expands this into a complete theme with 90+ properties.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional
import json
from pathlib import Path


@dataclass
class ThemePalette:
    """
    Minimal palette defined by the user.

    Contains 11 core colors that are expanded into a full theme:
    - 4 structure colors: background, surface, border, accent
    - 3 text/icon colors: text, text_secondary, icon
    - 4 semantic colors: info, warning, error, important

    Plus 2 opacity settings for interactive states.

    Optionally, users can provide overrides for specific generated properties.
    """

    # Theme name
    name: str

    # === STRUCTURE COLORS (4) ===
    background: str     # Main panel/frame background
    surface: str        # Data surface (trees, grids, inputs)
    border: str         # Borders and separators
    accent: str         # Accent color (selection, focus, links)

    # === TEXT / ICON COLORS (3) ===
    text: str           # Primary text color
    text_secondary: str # Secondary/muted text color
    icon: str           # Icon color (for themed icons)

    # === SEMANTIC COLORS (4) ===
    info: str           # Information messages
    warning: str        # Warning messages
    error: str          # Error messages
    important: str      # Important messages (e.g., schema changes)

    # === OPACITY SETTINGS (0-100) ===
    hover_opacity: int = 15       # Opacity for hover overlays (default 15%)
    selected_opacity: int = 30    # Opacity for selected overlays (default 30%)

    # === OPTIONAL OVERRIDES ===
    overrides: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert palette to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert palette to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def save(self, path: Path) -> None:
        """Save palette to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict) -> "ThemePalette":
        """Create palette from dictionary."""
        # Default icon color based on text if not specified
        default_icon = data.get("text", "#e0e0e0")
        return cls(
            name=data.get("name", "Unnamed"),
            background=data["background"],
            surface=data["surface"],
            border=data["border"],
            accent=data["accent"],
            text=data["text"],
            text_secondary=data["text_secondary"],
            icon=data.get("icon", default_icon),
            info=data.get("info", "#3498db"),
            warning=data.get("warning", "#f39c12"),
            error=data.get("error", "#e74c3c"),
            important=data.get("important", "#9b59b6"),
            hover_opacity=data.get("hover_opacity", 15),
            selected_opacity=data.get("selected_opacity", 30),
            overrides=data.get("overrides", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ThemePalette":
        """Create palette from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def load(cls, path: Path) -> "ThemePalette":
        """Load palette from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))


# === DEFAULT PALETTES ===

DEFAULT_DARK_PALETTE = ThemePalette(
    name="Default Dark",
    background="#252525",
    surface="#2d2d2d",
    border="#3d3d3d",
    accent="#0078d7",
    text="#e0e0e0",
    text_secondary="#808080",
    icon="#e0e0e0",      # Light icons for dark theme
    info="#3498db",
    warning="#f39c12",
    error="#e74c3c",
    important="#9b59b6",
)

DEFAULT_LIGHT_PALETTE = ThemePalette(
    name="Default Light",
    background="#f5f5f5",
    surface="#ffffff",
    border="#d0d0d0",
    accent="#0078d7",
    text="#1e1e1e",
    text_secondary="#606060",
    icon="#1e1e1e",      # Dark icons for light theme
    info="#0078d7",
    warning="#d68000",
    error="#c42b1c",
    important="#8764b8",
)
