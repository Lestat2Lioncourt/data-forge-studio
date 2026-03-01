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
"""

from .manager import I18nManager, get_manager, t

# Global manager instance for convenience
i18n_manager = get_manager()

# Register core translations
from . import core  # noqa: F401, E402


__all__ = [
    'I18nManager',
    'i18n_manager',
    'get_manager',
    't',
]
