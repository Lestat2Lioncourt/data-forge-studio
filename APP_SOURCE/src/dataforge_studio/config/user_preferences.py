"""User preferences management using SQLite database."""

from typing import Any, Optional

# Default preferences
DEFAULT_PREFERENCES = {
    "objects_borders": "false",  # Show debug borders on UI components
    "theme": "minimal_dark",
    "language": "fr"
}


class UserPreferences:
    """Singleton class to manage user preferences stored in SQLite database."""

    _instance = None

    @classmethod
    def instance(cls) -> 'UserPreferences':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize preferences manager."""
        # Import here to avoid circular imports
        from ..database.config_db import get_config_db
        self._config_db = get_config_db()
        self._ensure_defaults()

    def _ensure_defaults(self):
        """Ensure default preferences exist in database."""
        for key, value in DEFAULT_PREFERENCES.items():
            if self._config_db.get_preference(key) is None:
                self._config_db.set_preference(key, str(value))

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get preference value.

        Args:
            key: Preference key
            default: Default value if key not found

        Returns:
            Preference value (converted to appropriate type)
        """
        value = self._config_db.get_preference(key)
        if value is None:
            return default

        # Convert string values to appropriate types
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        elif value.isdigit():
            return int(value)
        return value

    def set(self, key: str, value: Any):
        """
        Set preference value and save to database.

        Args:
            key: Preference key
            value: Preference value
        """
        # Convert to string for storage
        str_value = str(value).lower() if isinstance(value, bool) else str(value)
        self._config_db.set_preference(key, str_value)

    def get_all(self) -> dict:
        """Get all preferences."""
        prefs = self._config_db.get_all_preferences()
        # Convert string values to appropriate types
        result = {}
        for key, value in prefs.items():
            if value.lower() == 'true':
                result[key] = True
            elif value.lower() == 'false':
                result[key] = False
            elif value.isdigit():
                result[key] = int(value)
            else:
                result[key] = value
        return result
