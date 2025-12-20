"""
Modular Internationalization (i18n) System.

This package provides a centralized translation management system where:
- Each plugin/module can register its own translations
- Translations are merged at runtime
- New languages from any module appear automatically in the UI

Usage:
    # Simple translation
    from dataforge_studio.config.i18n import t
    label = t("ok")  # Core/common translation
    label = t("database.connection_failed")  # Namespaced module translation

    # Register a module's translations (in module's __init__.py)
    from dataforge_studio.config.i18n import i18n_manager
    i18n_manager.register_module("my_plugin", Path(__file__).parent / "i18n")

    # Get/set language
    from dataforge_studio.config.i18n import i18n_manager
    current = i18n_manager.get_current_language()
    i18n_manager.set_language("fr")

    # Get available languages
    languages = i18n_manager.get_available_languages()  # {"en": "English", "fr": "Français"}

    # Register observer for language changes
    i18n_manager.register_observer(my_callback)

Backwards Compatibility:
    The old I18n class and get_i18n() function are still available for
    existing code that uses them.
"""

from .manager import I18nManager, get_manager, t

# Global manager instance for convenience
i18n_manager = get_manager()

# Register core translations
from . import core  # noqa: F401, E402


# ============================================================================
# Backwards Compatibility Layer
# ============================================================================
# These classes and functions maintain compatibility with code that used
# the old config/i18n.py module.

class I18n:
    """
    DEPRECATED: Use i18n_manager instead.

    This class is a thin wrapper for backwards compatibility.
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> 'I18n':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_current_language(self) -> str:
        """Get current language code"""
        return i18n_manager.get_current_language()

    def set_language(self, language: str):
        """Set the current language"""
        i18n_manager.set_language(language)

    def get_available_languages(self):
        """Get available languages"""
        return i18n_manager.get_available_languages()

    def t(self, key: str, **kwargs) -> str:
        """Translate a key"""
        return t(key, **kwargs)

    def register_observer(self, callback):
        """Register a language change observer"""
        i18n_manager.register_observer(callback)

    def unregister_observer(self, callback):
        """Unregister a language change observer"""
        i18n_manager.unregister_observer(callback)


def get_i18n() -> I18n:
    """DEPRECATED: Use i18n_manager instead."""
    return I18n.get_instance()


__all__ = [
    # New API
    'I18nManager',
    'i18n_manager',
    'get_manager',
    't',
    # Backwards compatibility
    'I18n',
    'get_i18n',
]
