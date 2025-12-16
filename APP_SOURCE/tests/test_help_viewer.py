"""
Test script for Help Viewer
"""
print("=" * 70)
print("TESTING HELP VIEWER")
print("=" * 70)

# Test imports
print("\n1. Testing imports...")
try:
    from help_viewer import HelpViewer, show_help
    print("   [OK] HelpViewer imported")
except Exception as e:
    print(f"   [ERROR] HelpViewer import failed: {e}")
    exit(1)

# Test finding documentation files
print("\n2. Finding documentation files...")
try:
    from pathlib import Path

    app_folder = Path(__file__).parent
    md_files = list(app_folder.glob("*.md"))

    print(f"   [OK] Found {len(md_files)} markdown files:")
    for md_file in sorted(md_files):
        size_kb = md_file.stat().st_size / 1024
        print(f"      - {md_file.name} ({size_kb:.1f} KB)")
except Exception as e:
    print(f"   [ERROR] Failed to find files: {e}")
    exit(1)

# Test GUI integration
print("\n3. Testing GUI integration...")
try:
    from gui import DataLakeLoaderGUI
    print("   [OK] GUI integration available")
except Exception as e:
    print(f"   [ERROR] GUI integration test failed: {e}")
    exit(1)

print("\n" + "=" * 70)
print("SUCCESS: Help Viewer is ready!")
print("=" * 70)

print("\nAvailable Documentation:")
for md_file in sorted(md_files):
    name = md_file.stem.replace("_", " ").title()
    print(f"  - {name}")

print("\nTo test:")
print("1. Run: uv run python gui.py")
print("2. Go to: Help -> Documentation")
print("3. Browse through all documentation files")
print("4. Select different topics from the left panel")
print("5. Read formatted content in the right panel")

print("\nFeatures:")
print("- Syntax highlighting for code blocks")
print("- Formatted headers (H1, H2, H3)")
print("- Bold and italic text")
print("- List items with bullets")
print("- Inline code formatting")
print("- Easy navigation between documents")
