"""
I18nManager - Central registry for modular translations.

This module provides a centralized translation management system where:
- Each plugin/module can register its own translations
- Translations are merged at runtime
- New languages from any module appear automatically in the UI
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Set, Callable, List

logger = logging.getLogger(__name__)


class I18nManager:
    """
    Central registry for modular internationalization.

    Features:
    - Modules register their translations with a namespace
    - Automatic language discovery across all modules
    - Fallback chain: module -> core -> english -> key
    - Observer pattern for language changes

    Usage:
        # In a plugin's i18n/__init__.py
        from dataforge_studio.config.i18n import i18n_manager
        i18n_manager.register_module("database", Path(__file__).parent)

        # In code
        from dataforge_studio.config.i18n import t
        label = t("database.connection_failed")  # Namespaced
        label = t("ok")  # Core/common translation
    """

    _instance: Optional['I18nManager'] = None

    def __init__(self):
        self._current_language = 'en'
        self._observers: List[Callable] = []

        # Module translations: {module_name: {lang_code: {key: value}}}
        self._modules: Dict[str, Dict[str, Dict[str, str]]] = {}

        # Core translations (common, menu, etc.)
        self._core: Dict[str, Dict[str, str]] = {}

        # Track all available languages across all modules
        self._available_languages: Set[str] = {'en', 'fr'}  # Default supported

        # Language display names
        self._language_names: Dict[str, str] = {
            'en': 'English',
            'fr': 'Français',
        }

        logger.debug("I18nManager initialized")

    @classmethod
    def get_instance(cls) -> 'I18nManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_module(self, module_name: str, translations_path: Path) -> bool:
        """
        Register a module's translations.

        Args:
            module_name: Unique module identifier (e.g., "database", "queries")
            translations_path: Path to directory containing {lang}.json files

        Returns:
            True if registration successful
        """
        if not translations_path.exists():
            logger.warning(f"Translations path does not exist: {translations_path}")
            return False

        self._modules[module_name] = {}

        # Load all language files in the directory
        for lang_file in translations_path.glob("*.json"):
            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)

                if isinstance(translations, dict):
                    self._modules[module_name][lang_code] = translations
                    self._available_languages.add(lang_code)

                    # Extract language name if provided
                    if 'lang_name' in translations:
                        self._language_names[lang_code] = translations['lang_name']

                    logger.debug(f"Loaded {lang_code} translations for module '{module_name}' ({len(translations)} keys)")

            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load {lang_file}: {e}")

        return True

    def register_core(self, translations_path: Path) -> bool:
        """
        Register core translations (common, menu, etc.).

        Args:
            translations_path: Path to directory containing {lang}.json files

        Returns:
            True if registration successful
        """
        if not translations_path.exists():
            logger.warning(f"Core translations path does not exist: {translations_path}")
            return False

        for lang_file in translations_path.glob("*.json"):
            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)

                if isinstance(translations, dict):
                    if lang_code not in self._core:
                        self._core[lang_code] = {}
                    self._core[lang_code].update(translations)
                    self._available_languages.add(lang_code)

                    # Extract language name if provided
                    if 'lang_name' in translations:
                        self._language_names[lang_code] = translations['lang_name']

                    logger.debug(f"Loaded core {lang_code} translations ({len(translations)} keys)")

            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load core {lang_file}: {e}")

        return True

    def load_legacy_translations(self, translations: Dict[str, Dict[str, str]]):
        """
        Load legacy hardcoded translations (for backwards compatibility).

        Args:
            translations: Dict of {lang_code: {key: value}}
        """
        for lang_code, trans in translations.items():
            if lang_code not in self._core:
                self._core[lang_code] = {}
            self._core[lang_code].update(trans)
            self._available_languages.add(lang_code)

        logger.debug(f"Loaded legacy translations for {len(translations)} languages")

    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key.

        Supports namespaced keys (module.key) and simple keys.

        Fallback chain:
        1. Namespaced: module[lang] -> module[en] -> core[lang] -> core[en] -> key
        2. Simple: core[lang] -> core[en] -> all modules -> key

        Args:
            key: Translation key (e.g., "ok" or "database.connection_failed")
            **kwargs: Format parameters for string interpolation

        Returns:
            Translated string or key if not found
        """
        lang = self._current_language
        text = None

        # Check if namespaced (module.key)
        if '.' in key:
            parts = key.split('.', 1)
            module_name, sub_key = parts[0], parts[1]

            # Try module translations
            if module_name in self._modules:
                module_trans = self._modules[module_name]
                text = module_trans.get(lang, {}).get(sub_key)
                if text is None:
                    text = module_trans.get('en', {}).get(sub_key)

        # Try core translations
        if text is None:
            text = self._core.get(lang, {}).get(key)

        if text is None:
            text = self._core.get('en', {}).get(key)

        # Search all modules for non-namespaced key
        if text is None and '.' not in key:
            for module_trans in self._modules.values():
                text = module_trans.get(lang, {}).get(key)
                if text:
                    break
                text = module_trans.get('en', {}).get(key)
                if text:
                    break

        # Final fallback: return the key itself
        if text is None:
            text = key

        # Apply string formatting
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error formatting translation '{key}': {e}")

        return text

    def get_current_language(self) -> str:
        """Get current language code."""
        return self._current_language

    def set_language(self, lang_code: str):
        """
        Set the current language.

        Args:
            lang_code: Language code (e.g., 'en', 'fr')
        """
        if lang_code not in self._available_languages:
            logger.warning(f"Language '{lang_code}' not available, keeping '{self._current_language}'")
            return

        if lang_code != self._current_language:
            self._current_language = lang_code
            logger.info(f"Language changed to: {lang_code}")
            self._notify_observers()

    def get_available_languages(self) -> Dict[str, str]:
        """
        Get all available languages.

        Returns:
            Dict mapping lang_code to display name
        """
        return {
            code: self._language_names.get(code, code.upper())
            for code in sorted(self._available_languages)
        }

    def register_observer(self, callback: Callable):
        """Register a callback for language changes."""
        if callback not in self._observers:
            self._observers.append(callback)

    def unregister_observer(self, callback: Callable):
        """Unregister a language change observer."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self):
        """Notify all observers of language change."""
        for callback in self._observers:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error notifying i18n observer: {e}")


# Singleton instance
_manager: Optional[I18nManager] = None


def get_manager() -> I18nManager:
    """Get the global I18nManager instance."""
    global _manager
    if _manager is None:
        _manager = I18nManager.get_instance()
    return _manager


def t(key: str, **kwargs) -> str:
    """
    Translate a key (convenience function).

    Args:
        key: Translation key
        **kwargs: Format parameters

    Returns:
        Translated string
    """
    return get_manager().t(key, **kwargs)
