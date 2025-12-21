"""
Theme Image Generator - Dynamic PNG generation for theme-colored UI elements

Generates images at runtime with theme-specific colors:
- Dropdown arrows for combo boxes
- Tree branch lines and expand/collapse arrows
"""

from pathlib import Path

# Path to assets (for fallback images)
ASSETS_PATH = Path(__file__).parent.parent / "assets" / "images"


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
