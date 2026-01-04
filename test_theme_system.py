"""
Test script for the new theme system.
Tests palette loading, disposition loading, and color generation.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dataforge_studio.core.theme.models import Palette, Disposition, Theme, PALETTE_COLOR_NAMES
from dataforge_studio.core.theme.disposition_engine import DispositionEngine

# Paths
PALETTES_PATH = Path(__file__).parent / "_AppConfig" / "palettes"
DISPOSITIONS_PATH = Path(__file__).parent / "_AppConfig" / "dispositions"


def load_palette(palette_id: str) -> Palette:
    """Load a palette from JSON file."""
    path = PALETTES_PATH / f"{palette_id}.json"
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return Palette.from_dict(palette_id, data)


def load_disposition(disposition_id: str) -> Disposition:
    """Load a disposition from JSON file."""
    path = DISPOSITIONS_PATH / f"{disposition_id}.json"
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Filter out _comment keys
    if "vectors" in data:
        data["vectors"] = {k: v for k, v in data["vectors"].items() if not k.startswith("_")}
    return Disposition.from_dict(disposition_id, data)


def test_palettes():
    """Test loading all palettes."""
    print("=" * 60)
    print("TEST: Loading Palettes")
    print("=" * 60)

    for palette_id in ["sombre", "clair", "corporate"]:
        print(f"\n--- Palette: {palette_id} ---")
        try:
            palette = load_palette(palette_id)
            print(f"  Name: {palette.name}")
            print(f"  Colors: {len(palette.colors)}")
            print(f"  Valid: {palette.is_valid()}")

            if not palette.is_valid():
                print(f"  Missing: {palette.get_missing_colors()}")

            # Show colors
            for name in PALETTE_COLOR_NAMES:
                color = palette.colors.get(name, "MISSING")
                status = "OK" if name in palette.colors else "MISSING"
                print(f"    {name}: {color} [{status}]")

        except Exception as e:
            print(f"  ERROR: {e}")


def test_dispositions():
    """Test loading all dispositions."""
    print("\n" + "=" * 60)
    print("TEST: Loading Dispositions")
    print("=" * 60)

    for disposition_id in ["classic", "minimalist"]:
        print(f"\n--- Disposition: {disposition_id} ---")
        try:
            disposition = load_disposition(disposition_id)
            print(f"  Name: {disposition.name}")
            print(f"  Description: {disposition.description}")
            print(f"  Vectors count: {len(disposition.vectors)}")

            # Show first 10 vectors
            print("  First 10 vectors:")
            for i, (key, value) in enumerate(list(disposition.vectors.items())[:10]):
                print(f"    {key}: {value}")

        except Exception as e:
            print(f"  ERROR: {e}")


def test_engine():
    """Test the disposition engine."""
    print("\n" + "=" * 60)
    print("TEST: Disposition Engine")
    print("=" * 60)

    engine = DispositionEngine()

    # Test with sombre palette + classic disposition
    print("\n--- Sombre + Classic ---")
    try:
        palette = load_palette("sombre")
        disposition = load_disposition("classic")

        colors = engine.apply(palette, disposition)

        print(f"  Generated {len(colors)} colors")
        print(f"  is_dark: {colors.get('is_dark')}")

        # Show some key colors
        key_colors = [
            "background", "surface", "accent", "text",
            "button_bg", "button_hover_bg", "button_pressed_bg",
            "hover_bg", "selected_bg",
            "tree_line1_bg", "tree_line2_bg", "tree_selected_bg",
            "menubar_bg", "menubar_hover_bg"
        ]

        print("\n  Key colors:")
        for key in key_colors:
            value = colors.get(key, "NOT GENERATED")
            print(f"    {key}: {value}")

    except Exception as e:
        import traceback
        print(f"  ERROR: {e}")
        traceback.print_exc()

    # Test with clair palette + minimalist disposition
    print("\n--- Clair + Minimalist ---")
    try:
        palette = load_palette("clair")
        disposition = load_disposition("minimalist")

        colors = engine.apply(palette, disposition)

        print(f"  Generated {len(colors)} colors")
        print(f"  is_dark: {colors.get('is_dark')}")

        print("\n  Key colors:")
        for key in key_colors:
            value = colors.get(key, "NOT GENERATED")
            print(f"    {key}: {value}")

    except Exception as e:
        import traceback
        print(f"  ERROR: {e}")
        traceback.print_exc()


def test_theme_creation():
    """Test creating a theme with overrides."""
    print("\n" + "=" * 60)
    print("TEST: Theme with Overrides")
    print("=" * 60)

    engine = DispositionEngine()

    # Create a theme with some overrides
    theme = Theme(
        id="test_theme",
        name="Test Theme",
        palette_id="sombre",
        disposition_id="classic",
        overrides={
            "button_hover_bg": "#ff5500",
            "accent": "#00ff00"
        }
    )

    print(f"\n  Theme: {theme.name}")
    print(f"  Palette: {theme.palette_id}")
    print(f"  Disposition: {theme.disposition_id}")
    print(f"  Has overrides: {theme.has_overrides()}")
    print(f"  Overrides: {theme.overrides}")

    # Generate colors
    palette = load_palette(theme.palette_id)
    disposition = load_disposition(theme.disposition_id)

    colors = engine.apply(palette, disposition)

    # Apply overrides
    colors.update(theme.overrides)

    print(f"\n  Final button_hover_bg: {colors.get('button_hover_bg')}")
    print(f"  (Should be #ff5500 from override)")

    print(f"\n  Final accent: {colors.get('accent')}")
    print(f"  (Should be #00ff00 from override)")


def test_theme_bridge():
    """Test ThemeBridge integration."""
    print("\n" + "=" * 60)
    print("TEST: ThemeBridge Integration")
    print("=" * 60)

    try:
        from dataforge_studio.ui.core.theme_bridge import ThemeBridge

        bridge = ThemeBridge()

        print(f"\n  Palettes loaded: {len(bridge.get_palettes())}")
        for pid, p in bridge.get_palettes().items():
            print(f"    - {pid}: {p.name}")

        print(f"\n  Dispositions loaded: {len(bridge.get_dispositions())}")
        for did, d in bridge.get_dispositions().items():
            print(f"    - {did}: {d.name}")

        print(f"\n  V2 Themes loaded: {len(bridge.get_themes_v2())}")
        for tid, t in bridge.get_themes_v2().items():
            print(f"    - {tid}: {t.name} (palette={t.palette_id}, disposition={t.disposition_id})")

        # Test generating colors for a v2 theme
        if bridge.get_themes_v2():
            first_theme_id = list(bridge.get_themes_v2().keys())[0]
            print(f"\n  Testing get_theme_colors_v2('{first_theme_id}'):")
            colors = bridge.get_theme_colors_v2(first_theme_id)
            print(f"    Generated {len(colors)} colors")

            # Show some key colors
            key_colors = ["background", "surface", "accent", "text",
                          "button_bg", "button_hover_bg", "hover_bg", "selected_bg"]
            for key in key_colors:
                value = colors.get(key, "NOT FOUND")
                print(f"    {key}: {value}")

    except Exception as e:
        import traceback
        print(f"  ERROR: {e}")
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  NEW THEME SYSTEM TEST")
    print("=" * 60)

    test_palettes()
    test_dispositions()
    test_engine()
    test_theme_creation()
    test_theme_bridge()

    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
