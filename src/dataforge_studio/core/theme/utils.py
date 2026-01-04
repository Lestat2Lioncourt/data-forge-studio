"""
Theme Utilities - Color manipulation functions.

Provides functions for:
- Color format conversion (hex, rgb, rgba)
- Color blending and mixing
- Luminosity calculations
- Color lightening/darkening
"""

from typing import Tuple


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#FF5500" or "FF5500")

    Returns:
        Tuple of (red, green, blue) values (0-255)
    """
    hex_color = hex_color.lstrip('#')
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """
    Convert RGB values to hex color string.

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        Hex color string (e.g., "#ff5500")
    """
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgba(hex_color: str, opacity: float) -> str:
    """
    Convert hex color to rgba() CSS string.

    Args:
        hex_color: Hex color string
        opacity: Opacity value (0.0 to 1.0)

    Returns:
        RGBA CSS string (e.g., "rgba(255, 85, 0, 0.5)")
    """
    r, g, b = hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {opacity})"


def luminosity(hex_color: str) -> float:
    """
    Calculate the relative luminosity of a color.

    Uses the formula: 0.299*R + 0.587*G + 0.114*B

    Args:
        hex_color: Hex color string

    Returns:
        Luminosity value (0.0 to 1.0)
    """
    r, g, b = hex_to_rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def is_dark(hex_color: str, threshold: float = 0.5) -> bool:
    """
    Determine if a color is dark based on luminosity.

    Args:
        hex_color: Hex color string
        threshold: Luminosity threshold (default 0.5)

    Returns:
        True if the color is dark
    """
    return luminosity(hex_color) < threshold


def lighten(hex_color: str, amount: float) -> str:
    """
    Lighten a color by a given amount.

    Args:
        hex_color: Hex color string
        amount: Amount to lighten (0.0 to 1.0)

    Returns:
        Lightened hex color
    """
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return rgb_to_hex(r, g, b)


def darken(hex_color: str, amount: float) -> str:
    """
    Darken a color by a given amount.

    Args:
        hex_color: Hex color string
        amount: Amount to darken (0.0 to 1.0)

    Returns:
        Darkened hex color
    """
    r, g, b = hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))
    return rgb_to_hex(r, g, b)


def blend(color1: str, color2: str, ratio: float) -> str:
    """
    Blend two colors together.

    Args:
        color1: First hex color (base)
        color2: Second hex color (overlay)
        ratio: Blend ratio (0.0 = all color1, 1.0 = all color2)

    Returns:
        Blended hex color
    """
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)

    return rgb_to_hex(r, g, b)


def fade(hex_color: str, opacity: float) -> str:
    """
    Create a faded (semi-transparent) version of a color.

    Alias for hex_to_rgba for semantic clarity.

    Args:
        hex_color: Hex color string
        opacity: Opacity value (0.0 to 1.0)

    Returns:
        RGBA CSS string
    """
    return hex_to_rgba(hex_color, opacity)


def contrast_color(hex_color: str, light: str = "#ffffff", dark: str = "#000000") -> str:
    """
    Get a contrasting color (light or dark) for text on a background.

    Args:
        hex_color: Background color
        light: Color to use if background is dark
        dark: Color to use if background is light

    Returns:
        Contrasting color (light or dark)
    """
    return light if is_dark(hex_color) else dark


def adjust_for_theme(hex_color: str, is_dark_theme: bool, amount: float = 0.1) -> str:
    """
    Adjust a color for better visibility on dark or light themes.

    For dark themes: slightly lightens the color
    For light themes: slightly darkens the color

    Args:
        hex_color: Hex color string
        is_dark_theme: True if theme is dark
        amount: Adjustment amount (0.0 to 1.0)

    Returns:
        Adjusted hex color
    """
    if is_dark_theme:
        return lighten(hex_color, amount)
    else:
        return darken(hex_color, amount)


def subtle_alternate(hex_color: str, is_dark_theme: bool) -> str:
    """
    Create a subtle alternate row color for tables/trees.

    Args:
        hex_color: Base background color
        is_dark_theme: True if theme is dark

    Returns:
        Slightly different background color
    """
    if is_dark_theme:
        return lighten(hex_color, 0.03)
    else:
        return darken(hex_color, 0.02)
