"""
I18n Bridge - Internationalization for DataForge Studio with PySide6

This module provides a thin wrapper around the central I18nManager,
maintaining backwards compatibility with existing code that uses tr().
"""

import logging
from typing import Dict, Callable

from dataforge_studio.config.i18n import i18n_manager, t as central_t

logger = logging.getLogger(__name__)


class I18nBridge:
    """
    Internationalization bridge with Observer pattern.

    This class delegates to the central I18nManager while providing
    a compatible interface for existing UI code.
    """

    _instance = None

    def __init__(self):
        """Initialize i18n bridge"""
        # Register a forwarder to sync observers
        self._local_observers = []

    @classmethod
    def instance(cls):
        """Get singleton instance of I18nBridge"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_language(self, lang_code: str):
        """
        Set current language and notify observers.

        Args:
            lang_code: Language code ('en', 'fr')
        """
        i18n_manager.set_language(lang_code)

    def get_current_language(self) -> str:
        """Get current language code"""
        return i18n_manager.get_current_language()

    def get_available_languages(self) -> Dict[str, str]:
        """
        Get dictionary of language codes to display names.

        Returns:
            Dict mapping lang_code to display_name
        """
        return i18n_manager.get_available_languages()

    def tr(self, key: str, **kwargs) -> str:
        """
        Translate a key to current language.

        Args:
            key: Translation key
            **kwargs: Format parameters for string interpolation

        Returns:
            Translated string or key if not found
        """
        return central_t(key, **kwargs)

    def register_observer(self, callback: Callable):
        """
        Register observer for language changes.

        Args:
            callback: Function to call when language changes (no arguments)
        """
        i18n_manager.register_observer(callback)

    def unregister_observer(self, callback: Callable):
        """
        Unregister observer.

        Args:
            callback: Previously registered callback
        """
        i18n_manager.unregister_observer(callback)


# Convenience function for global access
def tr(key: str, **kwargs) -> str:
    """
    Shortcut for translation.

    Args:
        key: Translation key
        **kwargs: Format parameters

    Returns:
        Translated string
    """
    return central_t(key, **kwargs)
