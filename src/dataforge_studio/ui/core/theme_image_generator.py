"""
Theme Image Generator - Dynamic PNG generation for theme-colored UI elements

Generates images at runtime with theme-specific colors:
- Dropdown arrows for combo boxes
- Tree branch lines and expand/collapse arrows
- Themed icons (recolored from black base icons)
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Path to assets
ASSETS_PATH = Path(__file__).parent.parent / "assets" / "images"
ICONS_PATH = Path(__file__).parent.parent / "assets" / "icons"


def generate_dropdown_arrow(color: str, output_dir: Path, size: int = 12) -> str:
    """
    Generate a dropdown arrow PNG image with the specified color.

    Args:
        color: Hex color string (e.g., "#E6E6E6")
        output_dir: Directory to save the image
        size: Size of the image (default 12x12)

    Returns:
        Path to the generated image as string
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return ""

    output_dir.mkdir(parents=True, exist_ok=True)

    # Create down-pointing triangle
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Triangle pointing down - centered
    margin = 2
    draw.polygon([
        (margin, margin + 2),           # Top-left
        (size - margin, margin + 2),    # Top-right
        (size // 2, size - margin)      # Bottom-center
    ], fill=color)

    arrow_path = output_dir / "dropdown-arrow.png"
    img.save(arrow_path)

    return str(arrow_path)


def generate_branch_images(color: str, output_dir: Path) -> dict:
    """
    Generate tree branch PNG images with the specified color.

    Creates 5 images for QTreeWidget branch indicators:
    - branch-vline.png: Vertical line (│)
    - branch-more.png: T-junction (├)
    - branch-end.png: L-corner (└)
    - branch-closed.png: Right arrow (►) for collapsed items
    - branch-open.png: Down arrow (▼) for expanded items

    Args:
        color: Hex color string (e.g., "#E6E6E6")
        output_dir: Directory to save the images

    Returns:
        Dict with paths to generated images:
        {"vline", "more", "end", "arrow_closed", "arrow_open"}
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # Fallback to default images if PIL not available
        return {
            "vline": str(ASSETS_PATH / "branch-vline.png"),
            "more": str(ASSETS_PATH / "branch-more.png"),
            "end": str(ASSETS_PATH / "branch-end.png"),
            "arrow_closed": str(ASSETS_PATH / "branch-closed.png"),
            "arrow_open": str(ASSETS_PATH / "branch-open.png"),
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    size = 20

    # branch-vline.png - vertical line centered (│)
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.line([(10, 0), (10, 20)], fill=color, width=1)
    vline_path = output_dir / "branch-vline.png"
    img.save(vline_path)

    # branch-more.png - T-junction (├)
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.line([(10, 0), (10, 20)], fill=color, width=1)
    draw.line([(10, 10), (20, 10)], fill=color, width=1)
    more_path = output_dir / "branch-more.png"
    img.save(more_path)

    # branch-end.png - L-corner (└)
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.line([(10, 0), (10, 10)], fill=color, width=1)
    draw.line([(10, 10), (20, 10)], fill=color, width=1)
    end_path = output_dir / "branch-end.png"
    img.save(end_path)

    # branch-closed.png - Right arrow (►) for collapsed items - smaller
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Smaller triangle pointing right (centered)
    draw.polygon([(7, 6), (13, 10), (7, 14)], fill=color)
    closed_path = output_dir / "branch-closed.png"
    img.save(closed_path)

    # branch-open.png - Down arrow (▼) for expanded items - smaller
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Smaller triangle pointing down (centered)
    draw.polygon([(6, 7), (14, 7), (10, 13)], fill=color)
    open_path = output_dir / "branch-open.png"
    img.save(open_path)

    return {
        "vline": str(vline_path),
        "more": str(more_path),
        "end": str(end_path),
        "arrow_closed": str(closed_path),
        "arrow_open": str(open_path),
    }


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def recolor_icon(icon_name: str, target_color: str, theme_variant: str) -> Optional[str]:
    """
    Recolor a base icon (black) to the target color.

    Base icons are black (#000000) with transparency.
    This function replaces black pixels with the target color.

    Args:
        icon_name: Name of the icon file (e.g., "database.png")
        target_color: Hex color string (e.g., "#E0E0E0")
        theme_variant: "light" or "dark"

    Returns:
        Path to the recolored icon, or None if failed
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("PIL not available for icon recoloring")
        return None

    # Ensure .png extension
    if not icon_name.endswith('.png'):
        icon_name = f"{icon_name}.png"

    base_path = ICONS_PATH / "base" / icon_name
    if not base_path.exists():
        return None

    output_dir = ICONS_PATH / theme_variant
    output_path = output_dir / icon_name

    # Check folder-level color cache (one file for all icons in the folder)
    color_cache_file = output_dir / "_color.txt"
    cached_color = None
    if color_cache_file.exists():
        try:
            cached_color = color_cache_file.read_text().strip()
        except (OSError, UnicodeDecodeError):
            pass

    # If color changed, we need to regenerate all icons
    color_changed = cached_color != target_color

    # Check if already generated with same color
    if output_path.exists() and not color_changed:
        return str(output_path)

    # Load and recolor
    try:
        img = Image.open(base_path).convert('RGBA')
        pixels = img.load()
        target_rgb = hex_to_rgb(target_color)

        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a > 0:  # Only recolor non-transparent pixels
                    # Replace any non-transparent pixel with target color
                    # Preserve alpha for anti-aliasing
                    pixels[x, y] = (target_rgb[0], target_rgb[1], target_rgb[2], a)

        # Save
        output_dir.mkdir(parents=True, exist_ok=True)
        img.save(output_path)

        # Update folder color cache (only if color changed)
        if color_changed:
            try:
                color_cache_file.write_text(target_color)
            except OSError:
                pass

        logger.debug(f"Recolored icon: {icon_name} -> {target_color}")
        return str(output_path)

    except Exception as e:
        logger.error(f"Failed to recolor icon {icon_name}: {e}")
        return None


def get_themed_icon_path(icon_name: str, is_dark_theme: bool, icon_color: str) -> Optional[str]:
    """
    Get path to themed icon, generating if necessary.

    Falls back to legacy images/ folder if base icon doesn't exist.

    Args:
        icon_name: Name of the icon file
        is_dark_theme: True for dark theme, False for light
        icon_color: Hex color for the icon

    Returns:
        Path to the icon file (themed, generated, or fallback)
    """
    # Ensure .png extension for lookup
    lookup_name = icon_name if icon_name.endswith('.png') else f"{icon_name}.png"

    theme_variant = "dark" if is_dark_theme else "light"

    # Check if base icon exists for theming
    base_path = ICONS_PATH / "base" / lookup_name
    if base_path.exists():
        # Try to get/generate themed version
        themed_path = recolor_icon(icon_name, icon_color, theme_variant)
        if themed_path:
            # Also generate the opposite variant if its color is known
            other_variant = "light" if is_dark_theme else "dark"
            other_color_file = ICONS_PATH / other_variant / "_color.txt"
            if other_color_file.exists():
                try:
                    other_color = other_color_file.read_text().strip()
                    if other_color:
                        recolor_icon(icon_name, other_color, other_variant)
                except (OSError, UnicodeDecodeError):
                    pass
            return themed_path

    # Fallback to legacy images folder
    legacy_path = ASSETS_PATH / lookup_name
    if legacy_path.exists():
        return str(legacy_path)

    return None
