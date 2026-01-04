"""
Theme System Models - Data classes for the new theme architecture.

The new theme system separates concerns into three components:
- Palette: A set of 15 named colors
- Disposition: Vectors that map palette colors to UI properties
- Theme: A combination of Palette + Disposition + optional overrides
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


# Standard palette color names (15 colors)
PALETTE_COLOR_NAMES = [
    "primary",        # Primary brand color
    "secondary",      # Secondary brand color
    "accent",         # Accent color (selection, focus, links)
    "background",     # Main panel/frame background
    "surface",        # Data surface (grids, trees, inputs)
    "border",         # Borders and separators
    "text",           # Primary text color
    "text_secondary", # Secondary/muted text color
    "icon",           # Icon color
    "info",           # Information messages
    "warning",        # Warning messages
    "error",          # Error messages
    "important",      # Important messages
    "highlight",      # Highlight color
    "muted",          # Disabled/muted elements
]


@dataclass
class Palette:
    """
    A palette is a set of 15 named colors.

    Palettes are the foundation of themes. They define the core colors
    that will be mapped to UI elements through dispositions.

    Attributes:
        id: Unique identifier (e.g., "sombre", "clair", "corporate")
        name: Display name (e.g., "Sombre", "Clair", "Corporate")
        colors: Dictionary of color names to hex values
    """
    id: str
    name: str
    colors: Dict[str, str]

    def get(self, color_name: str, default: str = "#ff00ff") -> str:
        """Get a color by name with optional default."""
        return self.colors.get(color_name, default)

    def __getitem__(self, color_name: str) -> str:
        """Get a color by name."""
        return self.colors[color_name]

    def is_valid(self) -> bool:
        """Check if palette has all required colors."""
        return all(name in self.colors for name in PALETTE_COLOR_NAMES)

    def get_missing_colors(self) -> list:
        """Get list of missing color names."""
        return [name for name in PALETTE_COLOR_NAMES if name not in self.colors]

    @classmethod
    def from_dict(cls, palette_id: str, data: dict) -> "Palette":
        """Create a Palette from a dictionary (JSON data)."""
        return cls(
            id=palette_id,
            name=data.get("name", palette_id),
            colors=data.get("colors", {})
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "colors": self.colors
        }


@dataclass
class Disposition:
    """
    A disposition defines how palette colors map to UI properties.

    Dispositions use "vectors" - expressions that reference palette colors
    and can apply transformations like blend, lighten, darken, etc.

    Vector syntax examples:
        - "text"                     -> Use palette color directly
        - "blend(surface, accent, 0.15)" -> Blend two colors
        - "lighten(background, 0.1)"    -> Lighten a color
        - "darken(background, 0.1)"     -> Darken a color
        - "contrast(accent)"            -> Black or white based on luminosity
        - "alternate(surface)"          -> Subtle variation for alternating rows
        - "fade(accent, 0.5)"           -> Add transparency
        - "#ff0000"                     -> Fixed color (rare)

    Attributes:
        id: Unique identifier (e.g., "standard")
        name: Display name (e.g., "Standard")
        description: Description of the disposition style
        vectors: Dictionary of UI property names to vector expressions
    """
    id: str
    name: str
    description: str
    vectors: Dict[str, str]

    def get_vector(self, ui_property: str, default: Optional[str] = None) -> Optional[str]:
        """Get a vector for a UI property."""
        return self.vectors.get(ui_property, default)

    def __getitem__(self, ui_property: str) -> str:
        """Get a vector by UI property name."""
        return self.vectors[ui_property]

    def __contains__(self, ui_property: str) -> bool:
        """Check if a vector exists for a UI property."""
        return ui_property in self.vectors

    @classmethod
    def from_dict(cls, disposition_id: str, data: dict) -> "Disposition":
        """Create a Disposition from a dictionary (JSON data)."""
        return cls(
            id=disposition_id,
            name=data.get("name", disposition_id),
            description=data.get("description", ""),
            vectors=data.get("vectors", {})
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "vectors": self.vectors
        }


@dataclass
class Theme:
    """
    A theme is a combination of Palette + Disposition + optional overrides.

    Attributes:
        id: Unique identifier (e.g., "mon_theme_perso")
        name: Display name (e.g., "Mon Thème Perso")
        palette_id: Reference to the palette
        disposition_id: Reference to the disposition
        overrides: Custom color overrides (UI property -> hex color)
    """
    id: str
    name: str
    disposition_id: str
    palette_id: str = "sombre"
    overrides: Dict[str, str] = field(default_factory=dict)

    def has_overrides(self) -> bool:
        """Check if theme has any custom overrides."""
        return len(self.overrides) > 0

    def get_override(self, ui_property: str) -> Optional[str]:
        """Get an override for a UI property, or None if not overridden."""
        return self.overrides.get(ui_property)

    def set_override(self, ui_property: str, color: str):
        """Set an override for a UI property."""
        self.overrides[ui_property] = color

    def remove_override(self, ui_property: str):
        """Remove an override for a UI property."""
        if ui_property in self.overrides:
            del self.overrides[ui_property]

    def clear_overrides(self):
        """Remove all overrides."""
        self.overrides.clear()

    @classmethod
    def from_dict(cls, theme_id: str, data: dict) -> "Theme":
        """Create a Theme from a dictionary (JSON data)."""
        # Support old formats (palette_dark/palette_light) for backward compatibility
        palette_id = data.get("palette")
        if palette_id is None:
            palette_id = data.get("palette_dark") or data.get("palette_light") or "sombre"

        return cls(
            id=theme_id,
            name=data.get("name", theme_id),
            disposition_id=data.get("disposition", "standard"),
            palette_id=palette_id,
            overrides=data.get("overrides", {})
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "name": self.name,
            "disposition": self.disposition_id,
            "palette": self.palette_id,
        }
        if self.overrides:
            result["overrides"] = self.overrides
        return result


# Built-in palette IDs
BUILTIN_PALETTES = ["clair", "sombre", "modern"]

# Built-in disposition IDs
BUILTIN_DISPOSITIONS = ["standard"]

# Default theme configuration
DEFAULT_THEME_CONFIG = {
    "palette": "sombre",
    "disposition": "standard"
}
