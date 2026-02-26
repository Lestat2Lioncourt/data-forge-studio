"""
Create Desktop Shortcut for DataForge Studio
Cross-platform script: Windows, MacOS, Linux
"""

import os
import sys
import stat
import shutil
import subprocess
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent


def convert_png_to_ico(png_path: Path, ico_path: Path) -> bool:
    """Convert PNG to ICO format for Windows shortcuts"""
    try:
        from PIL import Image

        img = Image.open(png_path)

        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(f"  [OK] Icon converted: {ico_path}")
        return True
    except ImportError:
        print("  [!] Pillow required for PNG to ICO conversion")
        print("      Install with: uv pip install pillow")
        return False
    except Exception as e:
        print(f"  [X] Error converting PNG to ICO: {e}")
        return False


def convert_png_to_icns(png_path: Path, icns_path: Path) -> bool:
    """Convert PNG to ICNS format for MacOS"""
    try:
        # Create iconset directory
        iconset_path = icns_path.parent / "DataForgeStudio.iconset"
        iconset_path.mkdir(exist_ok=True)

        from PIL import Image
        img = Image.open(png_path)

        # MacOS iconset requires specific sizes
        sizes = [16, 32, 64, 128, 256, 512]
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(iconset_path / f"icon_{size}x{size}.png")
            # Retina versions
            if size <= 256:
                resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
                resized_2x.save(iconset_path / f"icon_{size}x{size}@2x.png")

        # Convert iconset to icns using iconutil
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_path), "-o", str(icns_path)],
            capture_output=True, text=True
        )

        # Cleanup iconset
        shutil.rmtree(iconset_path)

        if result.returncode == 0:
            print(f"  [OK] ICNS icon created: {icns_path}")
            return True
        else:
            print(f"  [X] iconutil failed: {result.stderr}")
            return False

    except ImportError:
        print("  [!] Pillow required for icon conversion")
        print("      Install with: uv pip install pillow")
        return False
    except FileNotFoundError:
        print("  [!] iconutil not found (MacOS command line tools required)")
        return False
    except Exception as e:
        print(f"  [X] Error creating ICNS: {e}")
        return False


# =============================================================================
# WINDOWS
# =============================================================================

def create_windows_shortcut() -> bool:
    """Create Windows desktop shortcut with icon"""
    print("\n[Windows] Creating desktop shortcut...")

    project_root = get_project_root()
    ico_icon = project_root / "src" / "dataforge_studio" / "ui" / "assets" / "images" / "DataForge Studio.ico"
    png_icon = project_root / "src" / "dataforge_studio" / "ui" / "assets" / "images" / "DataForge Studio.png"
    run_script = project_root / "run.py"

    if not run_script.exists():
        print(f"  [X] run.py not found at {run_script}")
        return False

    # Check/create icon
    if ico_icon.exists():
        icon_to_use = ico_icon
        print(f"  [OK] Using ICO icon: {ico_icon.name}")
    elif png_icon.exists():
        print("  [>] Converting PNG to ICO...")
        if convert_png_to_ico(png_icon, ico_icon):
            icon_to_use = ico_icon
        else:
            icon_to_use = None
    else:
        print(f"  [!] No icon found")
        icon_to_use = None

    # Get pythonw.exe (no console)
    venv_pythonw = project_root / ".venv" / "Scripts" / "pythonw.exe"
    if not venv_pythonw.exists():
        print(f"  [X] pythonw.exe not found. Run 'uv sync' first.")
        return False

    # Find desktop
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = Path(shell.SpecialFolders("Desktop"))
    except:
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / "Bureau"  # French

    if not desktop.exists():
        print(f"  [X] Desktop folder not found")
        return False

    print(f"  [>] Desktop: {desktop}")

    # Create shortcut
    shortcut_path = desktop / "DataForge Studio.lnk"
    if shortcut_path.exists():
        shortcut_path.unlink()

    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = str(venv_pythonw)
        shortcut.Arguments = f'"{run_script}"'
        shortcut.WorkingDirectory = str(project_root)
        shortcut.Description = "DataForge Studio - Multi-database management tool"

        if icon_to_use and icon_to_use.exists():
            shortcut.IconLocation = str(icon_to_use)

        shortcut.save()
        print(f"  [OK] Shortcut created: {shortcut_path.name}")
        return True

    except ImportError:
        print("  [X] pywin32 required. Install with: uv pip install pywin32")
        return False
    except Exception as e:
        print(f"  [X] Error: {e}")
        return False


# =============================================================================
# MACOS
# =============================================================================

def create_macos_app() -> bool:
    """Create MacOS .app bundle"""
    print("\n[MacOS] Creating application bundle...")

    project_root = get_project_root()
    png_icon = project_root / "src" / "dataforge_studio" / "ui" / "assets" / "images" / "DataForge Studio.png"
    run_script = project_root / "run.py"

    if not run_script.exists():
        print(f"  [X] run.py not found at {run_script}")
        return False

    # Create .app bundle structure
    app_name = "DataForge Studio.app"
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        desktop = Path.home() / "Bureau"  # French

    app_path = desktop / app_name
    contents_path = app_path / "Contents"
    macos_path = contents_path / "MacOS"
    resources_path = contents_path / "Resources"

    # Remove existing
    if app_path.exists():
        shutil.rmtree(app_path)
        print(f"  [>] Removed existing: {app_name}")

    # Create directories
    macos_path.mkdir(parents=True)
    resources_path.mkdir(parents=True)

    # Create launcher script
    launcher_script = macos_path / "DataForgeStudio"

    # Find Python in venv
    venv_python = project_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        # Try to use uv run
        launcher_content = f'''#!/bin/bash
cd "{project_root}"
exec uv run python run.py "$@"
'''
    else:
        launcher_content = f'''#!/bin/bash
cd "{project_root}"
exec "{venv_python}" run.py "$@"
'''

    launcher_script.write_text(launcher_content)
    launcher_script.chmod(launcher_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  [OK] Launcher script created")

    # Create Info.plist
    info_plist = contents_path / "Info.plist"
    plist_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>DataForge Studio</string>
    <key>CFBundleDisplayName</key>
    <string>DataForge Studio</string>
    <key>CFBundleIdentifier</key>
    <string>com.dataforgestudio.app</string>
    <key>CFBundleVersion</key>
    <string>0.6.1</string>
    <key>CFBundleShortVersionString</key>
    <string>0.6.1</string>
    <key>CFBundleExecutable</key>
    <string>DataForgeStudio</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
'''
    info_plist.write_text(plist_content)
    print(f"  [OK] Info.plist created")

    # Create icon
    if png_icon.exists():
        icns_path = resources_path / "AppIcon.icns"
        if not convert_png_to_icns(png_icon, icns_path):
            # Fallback: just copy PNG
            shutil.copy(png_icon, resources_path / "AppIcon.png")
            print(f"  [!] Using PNG icon (ICNS conversion failed)")
    else:
        print(f"  [!] No icon found")

    print(f"  [OK] App bundle created: {app_path}")
    print(f"\n  You can now:")
    print(f"    - Double-click '{app_name}' on your Desktop")
    print(f"    - Drag it to Applications folder")
    print(f"    - Drag it to Dock for quick access")

    return True


# =============================================================================
# LINUX
# =============================================================================

def create_linux_desktop_entry() -> bool:
    """Create Linux .desktop file"""
    print("\n[Linux] Creating desktop entry...")

    project_root = get_project_root()
    png_icon = project_root / "src" / "dataforge_studio" / "ui" / "assets" / "images" / "DataForge Studio.png"
    run_script = project_root / "run.py"

    if not run_script.exists():
        print(f"  [X] run.py not found at {run_script}")
        return False

    # Paths
    applications_dir = Path.home() / ".local" / "share" / "applications"
    icons_dir = Path.home() / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    desktop_dir = Path.home() / "Desktop"
    if not desktop_dir.exists():
        desktop_dir = Path.home() / "Bureau"  # French

    # Create directories
    applications_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    # Copy icon
    icon_dest = icons_dir / "dataforge-studio.png"
    if png_icon.exists():
        shutil.copy(png_icon, icon_dest)
        print(f"  [OK] Icon installed: {icon_dest}")
    else:
        print(f"  [!] No icon found")

    # Find Python
    venv_python = project_root / ".venv" / "bin" / "python"
    if venv_python.exists():
        exec_command = f'"{venv_python}" "{run_script}"'
    else:
        exec_command = f'uv run python "{run_script}"'

    # Create .desktop file
    desktop_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name=DataForge Studio
Comment=Multi-database management tool
Exec={exec_command}
Icon=dataforge-studio
Path={project_root}
Terminal=false
Categories=Development;Database;
StartupWMClass=dataforge-studio
'''

    # Install to applications
    desktop_file = applications_dir / "dataforge-studio.desktop"
    desktop_file.write_text(desktop_content)
    desktop_file.chmod(desktop_file.stat().st_mode | stat.S_IXUSR)
    print(f"  [OK] Desktop entry installed: {desktop_file}")

    # Also create on Desktop if it exists
    if desktop_dir.exists():
        desktop_shortcut = desktop_dir / "DataForge Studio.desktop"
        desktop_shortcut.write_text(desktop_content)
        desktop_shortcut.chmod(desktop_shortcut.stat().st_mode | stat.S_IXUSR)
        print(f"  [OK] Desktop shortcut created: {desktop_shortcut}")

    # Update desktop database
    try:
        subprocess.run(
            ["update-desktop-database", str(applications_dir)],
            capture_output=True, check=False
        )
    except FileNotFoundError:
        pass

    print(f"\n  You can now:")
    print(f"    - Find 'DataForge Studio' in your application menu")
    print(f"    - Double-click the shortcut on your Desktop")

    return True


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main function - detect platform and create shortcut"""
    print("=" * 60)
    print("DataForge Studio - Desktop Shortcut Creator")
    print("=" * 60)

    project_root = get_project_root()
    print(f"\nProject root: {project_root}")
    print(f"Platform: {sys.platform}")

    success = False

    if sys.platform == "win32":
        success = create_windows_shortcut()

    elif sys.platform == "darwin":
        success = create_macos_app()

    elif sys.platform.startswith("linux"):
        success = create_linux_desktop_entry()

    else:
        print(f"\n[X] Unsupported platform: {sys.platform}")
        return 1

    print()
    print("=" * 60)
    if success:
        print("[OK] SUCCESS!")
    else:
        print("[X] FAILED - Check errors above")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
