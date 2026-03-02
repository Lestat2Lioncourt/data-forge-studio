"""
Disposition Engine - Resolves vectors to colors.

The engine applies disposition vectors to palette colors, generating
the full set of UI colors for a theme.

Vector syntax:
    - "text"                         -> Direct palette color reference
    - "blend(surface, accent, 0.15)" -> Blend two palette colors
    - "lighten(background, 0.1)"     -> Lighten a palette color
    - "darken(background, 0.1)"      -> Darken a palette color
    - "contrast(accent)"             -> Black or white based on luminosity
    - "alternate(surface)"           -> Subtle variation for alternating rows
    - "fade(accent, 0.5)"            -> Add transparency (rgba)
    - "#ff0000"                      -> Fixed hex color
"""

import re
import logging
from typing import Dict, Optional

from .models import Palette, Disposition
from .utils import (
    blend, lighten, darken, fade,
    contrast_color, is_dark, subtle_alternate
)

logger = logging.getLogger(__name__)


class DispositionEngine:
    """
    Engine that applies disposition vectors to palette colors.

    The engine parses vector expressions and resolves them to actual
    hex color values using the palette colors and transformation functions.
    """

    # Regex patterns for parsing vector expressions
    FUNCTION_PATTERN = re.compile(
        r'^(\w+)\s*\(\s*([^)]+)\s*\)$'
    )
    HEX_PATTERN = re.compile(r'^#[0-9a-fA-F]{6}$')

    def __init__(self):
        """Initialize the disposition engine."""
        # Cache for resolved colors within a single apply() call
        self._cache: Dict[str, str] = {}
        self._palette: Optional[Palette] = None
        self._is_dark_theme: bool = True

    def apply(self, palette: Palette, disposition: Disposition) -> Dict[str, str]:
        """
        Apply a disposition to a palette, generating all UI colors.

        Args:
            palette: The source palette with 15 colors
            disposition: The disposition with vector mappings

        Returns:
            Dictionary of UI property names to resolved hex colors
        """
        # Reset cache for this run
        self._cache = {}
        self._palette = palette

        # Determine if this is a dark or light theme
        self._is_dark_theme = is_dark(palette.get("background", "#252525"))

        # Start with palette colors as base (so they're available in the result)
        result = dict(palette.colors)

        # Add is_dark flag
        result["is_dark"] = self._is_dark_theme

        # Resolve each vector in the disposition
        for ui_property, vector in disposition.vectors.items():
            try:
                color = self._resolve_vector(vector)
                if color:
                    result[ui_property] = color
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to resolve vector '{vector}' for '{ui_property}': {e}")
                # Use fallback color
                result[ui_property] = "#ff00ff"  # Magenta for debugging

        return result

    def _resolve_vector(self, vector: str) -> Optional[str]:
        """
        Resolve a vector expression to a hex color.

        Args:
            vector: The vector expression to resolve

        Returns:
            Resolved hex color, or None if resolution fails
        """
        vector = vector.strip()

        # Check cache first
        if vector in self._cache:
            return self._cache[vector]

        result = None

        # Fixed hex color
        if self.HEX_PATTERN.match(vector):
            result = vector

        # Function call (e.g., blend(surface, accent, 0.15))
        elif match := self.FUNCTION_PATTERN.match(vector):
            func_name = match.group(1).lower()
            args_str = match.group(2)
            result = self._resolve_function(func_name, args_str)

        # Direct palette color reference
        elif self._palette and vector in self._palette.colors:
            result = self._palette.colors[vector]

        # Unknown vector - try as palette color anyway
        elif self._palette:
            result = self._palette.colors.get(vector)

        # Cache the result
        if result:
            self._cache[vector] = result

        return result

    def _resolve_function(self, func_name: str, args_str: str) -> Optional[str]:
        """
        Resolve a function call vector.

        Args:
            func_name: Name of the function (blend, lighten, etc.)
            args_str: Raw arguments string

        Returns:
            Resolved hex color, or None if resolution fails
        """
        # Parse arguments
        args = [arg.strip() for arg in args_str.split(',')]

        if func_name == "blend":
            return self._func_blend(args)
        elif func_name == "lighten":
            return self._func_lighten(args)
        elif func_name == "darken":
            return self._func_darken(args)
        elif func_name == "contrast":
            return self._func_contrast(args)
        elif func_name == "alternate":
            return self._func_alternate(args)
        elif func_name == "fade":
            return self._func_fade(args)
        else:
            logger.warning(f"Unknown function: {func_name}")
            return None

    def _resolve_color_arg(self, arg: str) -> Optional[str]:
        """
        Resolve a color argument (can be palette name, hex, or nested function).

        Args:
            arg: The argument to resolve

        Returns:
            Resolved hex color
        """
        arg = arg.strip()

        # Hex color
        if self.HEX_PATTERN.match(arg):
            return arg

        # Palette color reference
        if self._palette and arg in self._palette.colors:
            return self._palette.colors[arg]

        # Nested function (recursive)
        if '(' in arg:
            return self._resolve_vector(arg)

        return None

    def _func_blend(self, args: list) -> Optional[str]:
        """
        blend(color1, color2, ratio)
        Blend two colors together.
        """
        if len(args) < 3:
            logger.warning(f"blend() requires 3 arguments, got {len(args)}")
            return None

        color1 = self._resolve_color_arg(args[0])
        color2 = self._resolve_color_arg(args[1])
        try:
            ratio = float(args[2])
        except ValueError:
            logger.warning(f"Invalid ratio for blend(): {args[2]}")
            return None

        if color1 and color2:
            return blend(color1, color2, ratio)
        return None

    def _func_lighten(self, args: list) -> Optional[str]:
        """
        lighten(color, amount)
        Lighten a color by the given amount.
        """
        if len(args) < 2:
            logger.warning(f"lighten() requires 2 arguments, got {len(args)}")
            return None

        color = self._resolve_color_arg(args[0])
        try:
            amount = float(args[1])
        except ValueError:
            logger.warning(f"Invalid amount for lighten(): {args[1]}")
            return None

        if color:
            return lighten(color, amount)
        return None

    def _func_darken(self, args: list) -> Optional[str]:
        """
        darken(color, amount)
        Darken a color by the given amount.
        """
        if len(args) < 2:
            logger.warning(f"darken() requires 2 arguments, got {len(args)}")
            return None

        color = self._resolve_color_arg(args[0])
        try:
            amount = float(args[1])
        except ValueError:
            logger.warning(f"Invalid amount for darken(): {args[1]}")
            return None

        if color:
            return darken(color, amount)
        return None

    def _func_contrast(self, args: list) -> Optional[str]:
        """
        contrast(color)
        Return black or white based on the color's luminosity.
        """
        if len(args) < 1:
            logger.warning("contrast() requires 1 argument")
            return None

        color = self._resolve_color_arg(args[0])
        if color:
            return contrast_color(color)
        return None

    def _func_alternate(self, args: list) -> Optional[str]:
        """
        alternate(color)
        Create a subtle alternate row color.
        """
        if len(args) < 1:
            logger.warning("alternate() requires 1 argument")
            return None

        color = self._resolve_color_arg(args[0])
        if color:
            return subtle_alternate(color, self._is_dark_theme)
        return None

    def _func_fade(self, args: list) -> Optional[str]:
        """
        fade(color, opacity)
        Create an rgba color with transparency.
        Note: Returns rgba() string, not hex.
        """
        if len(args) < 2:
            logger.warning(f"fade() requires 2 arguments, got {len(args)}")
            return None

        color = self._resolve_color_arg(args[0])
        try:
            opacity = float(args[1])
        except ValueError:
            logger.warning(f"Invalid opacity for fade(): {args[1]}")
            return None

        if color:
            return fade(color, opacity)
        return None


# Singleton instance
_engine: Optional[DispositionEngine] = None


def get_disposition_engine() -> DispositionEngine:
    """Get the singleton disposition engine instance."""
    global _engine
    if _engine is None:
        _engine = DispositionEngine()
    return _engine
