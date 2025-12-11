"""
User Preferences - Persistent storage for user settings
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class UserPreferences:
    """
    Manages user preferences with persistent storage

    Preferences include:
    - theme: Visual theme name
    - language: Interface language (fr/en)
    """

    DEFAULT_PREFERENCES = {
        'theme': 'classic_light',
        'language': 'en',
        'query_format_style': 'expanded',  # SQL formatting style
    }

    _instance: Optional['UserPreferences'] = None

    def __init__(self):
        """Initialize user preferences"""
        self._preferences = self.DEFAULT_PREFERENCES.copy()
        self._config_dir = Path('_AppConfig')
        self._config_file = self._config_dir / 'preferences.json'
        self._observers = {}  # Key -> list of callbacks

        # Load preferences from file
        self.load()

        logger.info(f"UserPreferences initialized: {self._preferences}")

    @classmethod
    def get_instance(cls) -> 'UserPreferences':
        """Get singleton instance of UserPreferences"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a preference value

        Args:
            key: Preference key
            default: Default value if key not found

        Returns:
            Preference value or default
        """
        return self._preferences.get(key, default)

    def set(self, key: str, value: Any, save: bool = True):
        """
        Set a preference value

        Args:
            key: Preference key
            value: New value
            save: Whether to save to disk immediately
        """
        old_value = self._preferences.get(key)
        self._preferences[key] = value

        if save:
            self.save()

        # Notify observers if value changed
        if old_value != value:
            self._notify_observers(key, value)

        logger.info(f"Preference changed: {key} = {value}")

    def get_theme(self) -> str:
        """Get current theme name"""
        return self.get('theme', 'classic_light')

    def set_theme(self, theme: str):
        """Set theme and save"""
        self.set('theme', theme)

    def get_language(self) -> str:
        """Get current language"""
        return self.get('language', 'en')

    def set_language(self, language: str):
        """Set language and save"""
        self.set('language', language)

    def get_query_format_style(self) -> str:
        """Get current SQL query formatting style"""
        return self.get('query_format_style', 'expanded')

    def set_query_format_style(self, style: str):
        """Set SQL query formatting style and save"""
        self.set('query_format_style', style)

    def load(self):
        """Load preferences from file"""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    loaded_prefs = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self._preferences = self.DEFAULT_PREFERENCES.copy()
                    self._preferences.update(loaded_prefs)
                    logger.info(f"Loaded preferences from {self._config_file}")
            else:
                logger.info("No preferences file found, using defaults")
                # Create default file
                self.save()
        except Exception as e:
            logger.error(f"Error loading preferences: {e}")
            self._preferences = self.DEFAULT_PREFERENCES.copy()

    def save(self):
        """Save preferences to file"""
        try:
            # Ensure config directory exists
            self._config_dir.mkdir(exist_ok=True)

            # Write preferences to JSON
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._preferences, f, indent=2)

            logger.info(f"Saved preferences to {self._config_file}")
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")

    def reset_to_defaults(self):
        """Reset all preferences to default values"""
        self._preferences = self.DEFAULT_PREFERENCES.copy()
        self.save()
        logger.info("Preferences reset to defaults")

        # Notify all observers
        for key in self._preferences:
            self._notify_observers(key, self._preferences[key])

    def register_observer(self, key: str, callback):
        """
        Register a callback for preference changes

        Args:
            key: Preference key to observe
            callback: Function(new_value) to call on change
        """
        if key not in self._observers:
            self._observers[key] = []

        if callback not in self._observers[key]:
            self._observers[key].append(callback)
            logger.debug(f"Registered observer for preference: {key}")

    def unregister_observer(self, key: str, callback):
        """
        Unregister a preference observer

        Args:
            key: Preference key
            callback: Previously registered callback
        """
        if key in self._observers and callback in self._observers[key]:
            self._observers[key].remove(callback)
            logger.debug(f"Unregistered observer for preference: {key}")

    def _notify_observers(self, key: str, value: Any):
        """Notify observers of a preference change"""
        if key in self._observers:
            logger.debug(f"Notifying {len(self._observers[key])} observers for {key}")
            for callback in self._observers[key]:
                try:
                    callback(value)
                except Exception as e:
                    logger.error(f"Error notifying preference observer {callback}: {e}")

    def get_all(self) -> Dict[str, Any]:
        """Get all preferences as a dictionary"""
        return self._preferences.copy()


# Convenience function for global access
def get_preferences() -> UserPreferences:
    """Get the global UserPreferences instance"""
    return UserPreferences.get_instance()
