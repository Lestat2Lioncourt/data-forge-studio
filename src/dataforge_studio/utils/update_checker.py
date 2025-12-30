"""
Update Checker Module - Check for new releases on GitHub
"""
import json
import urllib.request
import urllib.error
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Constants
GITHUB_REPO = "Lestat2Lioncourt/data-forge-studio"


def get_app_version() -> str:
    """Get app version from installed package or pyproject.toml"""
    # First try: importlib.metadata (works for installed packages)
    try:
        from importlib.metadata import version
        return version("data-forge-studio")
    except Exception:
        pass

    # Second try: pyproject.toml (works in development)
    try:
        import tomllib
        pyproject = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "0.0.0")
    except Exception:
        pass

    return "0.0.0"  # Fallback


class UpdateChecker:
    """Check for updates from GitHub releases"""

    def __init__(self, config_dir: Path = None):
        """
        Initialize update checker

        Args:
            config_dir: Path to config directory (e.g., _AppConfig)
        """
        if config_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            config_dir = project_root / "_AppConfig"

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "update_check.json"
        self.github_api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        self.current_version = get_app_version()

    def _load_config(self) -> Dict:
        """Load update check configuration"""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error loading update config: {e}")
            return {}

    def _save_config(self, config: Dict):
        """Save update check configuration"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.debug(f"Error saving update config: {e}")

    def should_check(self) -> bool:
        """
        Check if we should perform an update check

        Returns:
            True if check should be performed, False if in cooldown period
        """
        config = self._load_config()

        last_dismissed = config.get('last_dismissed')
        if not last_dismissed:
            return True

        try:
            dismissed_date = datetime.fromisoformat(last_dismissed)
            now = datetime.now()

            # 24 hour cooldown
            if now - dismissed_date < timedelta(hours=24):
                return False

        except Exception:
            pass

        return True

    def dismiss_update(self):
        """Mark update notification as dismissed (24h cooldown)"""
        config = self._load_config()
        config['last_dismissed'] = datetime.now().isoformat()
        self._save_config(config)

    def check_for_update(self, timeout: int = 5) -> Optional[Tuple[str, str, str]]:
        """
        Check GitHub for newer version

        Args:
            timeout: Request timeout in seconds

        Returns:
            Tuple of (version, release_url, release_notes) if update available, None otherwise
        """
        try:
            req = urllib.request.Request(
                self.github_api_url,
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'DataForge-Studio-UpdateChecker'
                }
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode())

            latest_version = data.get('tag_name', '').lstrip('v')
            release_url = data.get('html_url', '')
            release_notes = data.get('body', '')

            if self._is_newer_version(latest_version, self.current_version):
                return (latest_version, release_url, release_notes)
            else:
                return None

        except urllib.error.URLError as e:
            logger.debug(f"Update check network error: {e}")
            return None
        except Exception as e:
            logger.debug(f"Update check error: {e}")
            return None

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """
        Compare version strings

        Args:
            latest: Latest version string (e.g., "0.5.1")
            current: Current version string (e.g., "0.5.0")

        Returns:
            True if latest > current
        """
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]

            max_len = max(len(latest_parts), len(current_parts))
            latest_parts += [0] * (max_len - len(latest_parts))
            current_parts += [0] * (max_len - len(current_parts))

            return latest_parts > current_parts

        except Exception:
            return False


# Global instance
_update_checker: Optional[UpdateChecker] = None


def get_update_checker() -> UpdateChecker:
    """Get global update checker instance"""
    global _update_checker

    if _update_checker is None:
        _update_checker = UpdateChecker()

    return _update_checker
