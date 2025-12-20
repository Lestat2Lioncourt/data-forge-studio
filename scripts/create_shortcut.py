"""
Create Desktop Shortcut for DataForge Studio
This script creates a Windows desktop shortcut with icon
"""

import os
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def convert_png_to_ico(png_path: Path, ico_path: Path):
    """Convert PNG to ICO format for Windows shortcuts"""
    try:
        from PIL import Image

        # Open PNG image
        img = Image.open(png_path)

        # Convert RGBA to RGB if necessary
        if img.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background

        # Save as ICO with multiple sizes (for different display contexts)
        img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(f"✓ Icon converted: {ico_path}")
        return True
    except ImportError:
        print("✗ Error: Pillow is required to convert PNG to ICO")
        print("  Install with: uv pip install pillow")
        return False
    except Exception as e:
        print(f"✗ Error converting PNG to ICO: {e}")
        return False


def create_windows_shortcut(target_path: Path, shortcut_name: str, icon_path: Path = None, description: str = ""):
    """Create a Windows shortcut (.lnk) on the desktop"""
    try:
        import win32com.client

        # Get desktop path
        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / f"{shortcut_name}.lnk"

        # Delete existing shortcut if it exists
        if shortcut_path.exists():
            shortcut_path.unlink()
            print(f"  Removed existing shortcut: {shortcut_path}")

        # Create shortcut
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))

        # Use cmd.exe to run the batch file (more reliable)
        shortcut.TargetPath = "cmd.exe"
        shortcut.Arguments = f'/c "{target_path}"'
        shortcut.WorkingDirectory = str(target_path.parent)
        shortcut.Description = description

        if icon_path and icon_path.exists():
            shortcut.IconLocation = str(icon_path)

        shortcut.save()
        print(f"✓ Shortcut created: {shortcut_path}")
        return True
    except ImportError:
        print("✗ Error: pywin32 is required to create shortcuts")
        print("  Install with: uv pip install pywin32")
        return False
    except Exception as e:
        print(f"✗ Error creating shortcut: {e}")
        return False


def main():
    """Main function to create shortcut with icon"""
    print("=" * 60)
    print("DataForge Studio - Desktop Shortcut Creator")
    print("=" * 60)
    print()

    # Get project root
    project_root = Path(__file__).parent

    # Paths
    ico_icon = project_root / "src" / "dataforge_studio" / "ui" / "assets" / "images" / "DataForge Studio.ico"
    png_icon = project_root / "src" / "dataforge_studio" / "ui" / "assets" / "images" / "DataForge Studio.png"
    run_script = project_root / "run.py"

    # Check if run.py exists
    if not run_script.exists():
        print(f"✗ Error: run.py not found at {run_script}")
        return 1

    # Step 1: Check for icon files
    print("Step 1: Checking for icon files...")
    if ico_icon.exists():
        icon_to_use = ico_icon
        print(f"✓ Using ICO icon: {ico_icon}")
    elif png_icon.exists():
        print(f"⚠️  ICO not found, converting PNG to ICO...")
        if convert_png_to_ico(png_icon, ico_icon):
            icon_to_use = ico_icon
        else:
            print("\nℹ️  Icon conversion failed, using PNG...")
            icon_to_use = png_icon
    else:
        print(f"✗ Error: No icon found at {ico_icon} or {png_icon}")
        return 1

    print()

    # Step 2: Create shortcut
    print("Step 2: Creating desktop shortcut...")

    # Get Python executable in virtual environment
    if sys.platform == "win32":
        python_exe = Path(sys.executable)

        # Create a batch file to launch the app WITHOUT console window
        # Using pythonw.exe instead of python.exe to hide console
        batch_file = project_root / "DataForgeStudio.bat"
        venv_pythonw = project_root / ".venv" / "Scripts" / "pythonw.exe"

        if not venv_pythonw.exists():
            print(f"✗ Error: pythonw.exe not found at {venv_pythonw}")
            print("  Please run 'uv sync' first to create the virtual environment")
            return 1

        with open(batch_file, 'w') as f:
            f.write('@echo off\n')
            f.write(f'cd /d "{project_root}"\n')
            # Use pythonw.exe to avoid console window
            f.write(f'"{venv_pythonw}" run.py\n')

        print(f"✓ Batch launcher created (no console): {batch_file}")

        # Create shortcut to batch file
        # Try different desktop locations (Windows can have different paths)
        # Priority: user's personal desktop first, then public
        import os

        # Try to get desktop via Windows Shell (most reliable)
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            actual_desktop = Path(shell.SpecialFolders("Desktop"))
        except:
            actual_desktop = None

        # Fallback to manual search if shell method fails
        if not actual_desktop or not actual_desktop.exists():
            desktop_paths = [
                Path.home() / "Desktop",
                Path.home() / "Bureau",  # French Windows
                Path(os.environ.get('USERPROFILE', '')) / "Desktop",
                Path(os.environ.get('USERPROFILE', '')) / "Bureau",
                # Public desktop last (requires admin rights)
                Path(os.environ.get('PUBLIC', '')) / "Desktop"
            ]

            # Find the actual desktop path
            for dp in desktop_paths:
                if dp.exists():
                    actual_desktop = dp
                    break

        if not actual_desktop:
            print(f"✗ Error: Could not find desktop folder")
            print(f"  Tried: {[str(p) for p in desktop_paths]}")
            return 1

        print(f"  Desktop location: {actual_desktop}")

        # Create shortcut using simplified name first
        shortcut_path = actual_desktop / "DataForgeStudio.lnk"

        # Remove if exists
        if shortcut_path.exists():
            shortcut_path.unlink()
            print(f"  Removed existing shortcut")

        # Create manually using win32com
        # Point DIRECTLY to pythonw.exe (no cmd.exe, no batch file)
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))

            # Direct launch with pythonw.exe (no console window at all)
            shortcut.TargetPath = str(venv_pythonw)
            shortcut.Arguments = f'"{run_script}"'
            shortcut.WorkingDirectory = str(project_root)
            shortcut.Description = "DataForge Studio - Multi-database management tool"

            if icon_to_use.exists():
                shortcut.IconLocation = str(icon_to_use)

            shortcut.save()
            print(f"✓ Shortcut created (direct pythonw, no console): {shortcut_path}")
            success = True
        except Exception as e:
            print(f"✗ Error creating shortcut: {e}")
            success = False
    else:
        print("✗ This script currently only supports Windows")
        return 1

    print()

    if success:
        print("=" * 60)
        print("✓ SUCCESS!")
        print("=" * 60)
        print()
        print("Desktop shortcut created with icon!")
        print()
        print("You can now:")
        print("  1. Double-click the 'DataForge Studio' shortcut on your desktop")
        print("  2. Pin it to Start Menu or Taskbar for quick access")
        print()
        return 0
    else:
        print()
        print("=" * 60)
        print("✗ FAILED")
        print("=" * 60)
        print()
        print("Shortcut creation failed. Please check the errors above.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
