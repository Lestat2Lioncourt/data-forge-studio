"""
Update Checker Module - Check for new releases on GitHub
"""
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from ..constants import APP_VERSION, GITHUB_REPO
from .logger import logger


class UpdateChecker:
    """Check for updates from GitHub releases"""

    def __init__(self, config_dir: Path):
        """
        Initialize update checker

        Args:
            config_dir: Path to config directory (e.g., _AppConfig)
        """
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "update_check.json"
        self.github_api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    def _load_config(self) -> Dict:
        """Load update check configuration"""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading update check config: {e}")
            return {}

    def _save_config(self, config: Dict):
        """Save update check configuration"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving update check config: {e}")

    def should_check(self) -> bool:
        """
        Check if we should perform an update check

        Returns:
            True if check should be performed, False if in cooldown period
        """
        config = self._load_config()

        # Get last dismissed date
        last_dismissed = config.get('last_dismissed')
        if not last_dismissed:
            return True

        try:
            # Parse last dismissed date
            dismissed_date = datetime.fromisoformat(last_dismissed)
            now = datetime.now()

            # Check if 24 hours have passed
            if now - dismissed_date < timedelta(hours=24):
                logger.info(f"Update check skipped (cooldown until {dismissed_date + timedelta(hours=24)})")
                return False

        except Exception as e:
            logger.error(f"Error parsing last dismissed date: {e}")

        return True

    def dismiss_update(self):
        """Mark update notification as dismissed (24h cooldown)"""
        config = self._load_config()
        config['last_dismissed'] = datetime.now().isoformat()
        self._save_config(config)
        logger.info("Update notification dismissed for 24 hours")

    def check_for_update(self, timeout: int = 5) -> Optional[Tuple[str, str, str]]:
        """
        Check GitHub for newer version

        Args:
            timeout: Request timeout in seconds

        Returns:
            Tuple of (version, release_url, release_notes) if update available, None otherwise
        """
        try:
            # Fetch latest release from GitHub API
            req = urllib.request.Request(
                self.github_api_url,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode())

            latest_version = data.get('tag_name', '').lstrip('v')
            release_url = data.get('html_url', '')
            release_notes = data.get('body', '')

            # Compare versions
            if self._is_newer_version(latest_version, APP_VERSION):
                logger.info(f"Update available: {latest_version} (current: {APP_VERSION})")
                return (latest_version, release_url, release_notes)
            else:
                logger.info(f"No update available (current: {APP_VERSION}, latest: {latest_version})")
                return None

        except urllib.error.URLError as e:
            logger.warning(f"Could not check for updates (network error): {e}")
            return None
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return None

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """
        Compare version strings

        Args:
            latest: Latest version string (e.g., "0.3.0")
            current: Current version string (e.g., "0.2.0")

        Returns:
            True if latest > current
        """
        try:
            # Parse semantic version (major.minor.patch)
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]

            # Pad to same length
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts += [0] * (max_len - len(latest_parts))
            current_parts += [0] * (max_len - len(current_parts))

            # Compare
            return latest_parts > current_parts

        except Exception as e:
            logger.error(f"Error comparing versions: {e}")
            return False


# Global instance
_update_checker: Optional[UpdateChecker] = None


def get_update_checker(config_dir: Path = None) -> UpdateChecker:
    """
    Get global update checker instance

    Args:
        config_dir: Path to config directory (only used on first call)

    Returns:
        UpdateChecker instance
    """
    global _update_checker

    if _update_checker is None:
        if config_dir is None:
            # Default to _AppConfig in project root
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "_AppConfig"

        _update_checker = UpdateChecker(config_dir)

    return _update_checker
