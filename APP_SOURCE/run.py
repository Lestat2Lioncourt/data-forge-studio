"""
Quick launcher for DataForge Studio Application
"""
import sys
import os
import subprocess
import argparse

def update_application():
    """Update DataForge Studio to the latest version"""
    print("=" * 60)
    print("DataForge Studio - Update")
    print("=" * 60)
    print()

    try:
        # Step 1: Git pull
        print("📥 Pulling latest changes from GitHub...")
        result = subprocess.run(
            ["git", "pull"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)

        if "Already up to date" in result.stdout:
            print("✅ Repository is already up to date")
        else:
            print("✅ Changes pulled successfully")

        print()

        # Step 2: UV sync
        print("📦 Syncing dependencies with uv...")
        result = subprocess.run(
            ["uv", "sync"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("✅ Dependencies synced successfully")

        print()
        print("=" * 60)
        print("✅ Update completed successfully!")
        print("=" * 60)
        print()
        print("You can now restart DataForge Studio.")
        print("Run: uv run run.py")
        print()

        return 0

    except subprocess.CalledProcessError as e:
        print()
        print("❌ Error during update:")
        print(e.stderr if e.stderr else str(e))
        print()
        print("Please check the error and try again, or update manually:")
        print("  1. git pull")
        print("  2. uv sync")
        return 1
    except FileNotFoundError as e:
        print()
        print("❌ Error: Command not found")
        print(str(e))
        print()
        print("Make sure git and uv are installed and in your PATH")
        return 1

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="DataForge Studio Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run run.py           Launch the application
  uv run run.py --update  Update to the latest version
        """
    )

    parser.add_argument(
        '--update',
        action='store_true',
        help='Update DataForge Studio to the latest version (git pull + uv sync)'
    )

    args = parser.parse_args()

    if args.update:
        sys.exit(update_application())
    else:
        # Add src directory to Python path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

        # Launch the application
        from main import main as app_main
        app_main()

if __name__ == "__main__":
    main()
