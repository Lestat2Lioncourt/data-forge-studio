#!/usr/bin/env python3
"""
Check for DataForge Studio updates - Standalone script
Works independently of the main application

Usage:
    python scripts/check_update.py
    uv run python scripts/check_update.py
"""

import json
import urllib.request
import urllib.error
import sys
from pathlib import Path

GITHUB_REPO = "Lestat2Lioncourt/data-forge-studio"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_current_version() -> str:
    """Get current version from pyproject.toml"""
    try:
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding='utf-8')
            for line in content.split('\n'):
                if line.startswith('version = '):
                    return line.split('"')[1]
    except Exception:
        pass
    return "unknown"


def check_for_update() -> tuple:
    """
    Check GitHub for latest version

    Returns:
        (latest_version, current_version, release_url, is_newer)
    """
    current = get_current_version()

    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'DataForge-Studio-UpdateChecker'
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        latest = data.get('tag_name', '').lstrip('v')
        release_url = data.get('html_url', '')

        # Compare versions
        is_newer = compare_versions(latest, current)

        return (latest, current, release_url, is_newer)

    except urllib.error.URLError as e:
        print(f"[ERROR] Network error: {e}")
        return (None, current, None, False)
    except Exception as e:
        print(f"[ERROR] {e}")
        return (None, current, None, False)


def compare_versions(latest: str, current: str) -> bool:
    """Compare semantic versions, return True if latest > current"""
    try:
        if current == "unknown":
            return True

        latest_parts = [int(x) for x in latest.split('.')]
        current_parts = [int(x) for x in current.split('.')]

        max_len = max(len(latest_parts), len(current_parts))
        latest_parts += [0] * (max_len - len(latest_parts))
        current_parts += [0] * (max_len - len(current_parts))

        return latest_parts > current_parts
    except Exception:
        return False


def main():
    print("=" * 60)
    print("DataForge Studio - Update Checker")
    print("=" * 60)
    print()

    print("Checking for updates...")
    latest, current, url, is_newer = check_for_update()

    print()
    print(f"  Current version: {current}")
    print(f"  Latest version:  {latest or 'unknown'}")
    print()

    if is_newer and latest:
        print("=" * 60)
        print("  UPDATE AVAILABLE!")
        print("=" * 60)
        print()
        print(f"  Release page: {url}")
        print()
        print("  To update, run:")
        print()
        # Get project root for safe.directory
        project_root = Path(__file__).parent.parent
        safe_dir = str(project_root).replace('\\', '/')
        print(f'    git config --global --add safe.directory "{safe_dir}"')
        print("    git pull")
        print("    uv sync")
        print()
        print("  (The first command fixes 'dubious ownership' errors on Windows)")
        print()
        return 1  # Exit code 1 = update available
    else:
        print("  You are running the latest version.")
        print()
        return 0  # Exit code 0 = up to date


if __name__ == "__main__":
    sys.exit(main())
