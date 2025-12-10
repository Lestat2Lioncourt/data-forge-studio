"""
Internationalization (i18n) - Multi-language support
"""
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Set

logger = logging.getLogger(__name__)


class I18n:
    """
    Internationalization manager for multi-language support

    Supported languages:
    - en: English
    - fr: French (Français)
    """

    TRANSLATIONS = {
        'en': {
            # Menu items
            'menu_file': 'File',
            'menu_edit': 'Edit',
            'menu_view': 'View',
            'menu_settings': 'Settings',
            'menu_preferences': 'Preferences...',
            'menu_exit': 'Exit',

            # Toolbar buttons
            'btn_data_explorer': 'Data Explorer',
            'btn_databases': 'Databases',

            # Preferences dialog
            'pref_title': 'Preferences',
            'pref_appearance': 'Appearance',
            'pref_general': 'General',
            'pref_theme': 'Theme:',
            'pref_language': 'Language:',
            'pref_apply': 'Apply',
            'pref_ok': 'OK',
            'pref_cancel': 'Cancel',
            'pref_reset': 'Reset to Defaults',

            # Theme names
            'theme_classic_light': 'Classic Light',
            'theme_dark_professional': 'Dark Professional',
            'theme_azure_blue': 'Azure Blue',

            # Language names
            'lang_english': 'English',
            'lang_french': 'Français',

            # Data Explorer
            'explorer_title': 'Data Explorer',
            'explorer_file_info': 'File Information',
            'explorer_column_stats': 'Column Statistics',
            'explorer_no_file': 'No file selected',

            # Database Manager
            'db_title': 'Database Manager',
            'db_connections': 'Connections',
            'db_new_query': 'New Query',
            'db_execute': 'Execute',
            'db_save': 'Save',

            # Column statistics
            'stat_column': 'Column',
            'stat_total': 'Total',
            'stat_non_null': 'Non-Null',
            'stat_empty': 'Empty',
            'stat_distinct': 'Distinct',

            # Context menu
            'ctx_open': 'Open',
            'ctx_view_all': 'View All',
            'ctx_view_top_100': 'View Top 100',
            'ctx_view_top_1000': 'View Top 1000',
            'ctx_refresh': 'Refresh',
            'ctx_new_query': 'New Query',

            # Common
            'yes': 'Yes',
            'no': 'No',
            'ok': 'OK',
            'cancel': 'Cancel',
            'apply': 'Apply',
            'close': 'Close',
            'save': 'Save',
            'open': 'Open',
            'delete': 'Delete',
            'edit': 'Edit',
            'refresh': 'Refresh',
            'search': 'Search',
            'filter': 'Filter',
            'export': 'Export',
            'import': 'Import',
            'copy': 'Copy',
            'paste': 'Paste',
            'error': 'Error',
            'warning': 'Warning',
            'info': 'Information',
            'loading': 'Loading...',

            # Messages
            'msg_restart_required': 'Some changes may require restart to take full effect.',
            'msg_preferences_saved': 'Preferences saved successfully.',
            'msg_theme_changed': 'Theme changed to: {theme}',
            'msg_language_changed': 'Language changed to: {language}',

            # Status bar
            'status_version_up_to_date': 'Your version is up to date',
            'status_update_on_quit': 'Update will run when you close the application',
        },

        'fr': {
            # Menu items
            'menu_file': 'Fichier',
            'menu_edit': 'Édition',
            'menu_view': 'Affichage',
            'menu_settings': 'Paramètres',
            'menu_preferences': 'Préférences...',
            'menu_exit': 'Quitter',

            # Toolbar buttons
            'btn_data_explorer': 'Explorateur de Données',
            'btn_databases': 'Bases de Données',

            # Preferences dialog
            'pref_title': 'Préférences',
            'pref_appearance': 'Apparence',
            'pref_general': 'Général',
            'pref_theme': 'Thème :',
            'pref_language': 'Langue :',
            'pref_apply': 'Appliquer',
            'pref_ok': 'OK',
            'pref_cancel': 'Annuler',
            'pref_reset': 'Réinitialiser',

            # Theme names
            'theme_classic_light': 'Classique Clair',
            'theme_dark_professional': 'Sombre Professionnel',
            'theme_azure_blue': 'Bleu Azure',

            # Language names
            'lang_english': 'English',
            'lang_french': 'Français',

            # Data Explorer
            'explorer_title': 'Explorateur de Données',
            'explorer_file_info': 'Informations du Fichier',
            'explorer_column_stats': 'Statistiques des Colonnes',
            'explorer_no_file': 'Aucun fichier sélectionné',

            # Database Manager
            'db_title': 'Gestionnaire de Bases de Données',
            'db_connections': 'Connexions',
            'db_new_query': 'Nouvelle Requête',
            'db_execute': 'Exécuter',
            'db_save': 'Sauvegarder',

            # Column statistics
            'stat_column': 'Colonne',
            'stat_total': 'Total',
            'stat_non_null': 'Non-Null',
            'stat_empty': 'Vide',
            'stat_distinct': 'Distinct',

            # Context menu
            'ctx_open': 'Ouvrir',
            'ctx_view_all': 'Afficher Tout',
            'ctx_view_top_100': 'Afficher Top 100',
            'ctx_view_top_1000': 'Afficher Top 1000',
            'ctx_refresh': 'Actualiser',
            'ctx_new_query': 'Nouvelle Requête',

            # Common
            'yes': 'Oui',
            'no': 'Non',
            'ok': 'OK',
            'cancel': 'Annuler',
            'apply': 'Appliquer',
            'close': 'Fermer',
            'save': 'Sauvegarder',
            'open': 'Ouvrir',
            'delete': 'Supprimer',
            'edit': 'Éditer',
            'refresh': 'Actualiser',
            'search': 'Rechercher',
            'filter': 'Filtrer',
            'export': 'Exporter',
            'import': 'Importer',
            'copy': 'Copier',
            'paste': 'Coller',
            'error': 'Erreur',
            'warning': 'Avertissement',
            'info': 'Information',
            'loading': 'Chargement...',

            # Messages
            'msg_restart_required': 'Certains changements peuvent nécessiter un redémarrage.',
            'msg_preferences_saved': 'Préférences sauvegardées avec succès.',
            'msg_theme_changed': 'Thème changé en : {theme}',
            'msg_language_changed': 'Langue changée en : {language}',

            # Status bar
            'status_version_up_to_date': 'Votre version est à jour',
            'status_update_on_quit': 'La mise à jour se lancera à la fermeture de l\'application',
        },
    }

    _instance: Optional['I18n'] = None
    LANGUAGES_DIR = Path('_AppConfig/languages')

    def __init__(self):
        """Initialize i18n manager"""
        self._current_language = 'en'
        self._observers = []
        self._external_translations: Dict[str, Dict[str, str]] = {}
        self._available_languages: Set[str] = set()

        # Load external language files
        self._load_external_translations()

        logger.info(f"I18n initialized with language: {self._current_language}")
        logger.info(f"Available languages: {', '.join(sorted(self._available_languages))}")

    @classmethod
    def get_instance(cls) -> 'I18n':
        """Get singleton instance of I18n"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_external_translations(self):
        """
        Load all external language files from _AppConfig/languages/
        Falls back to hardcoded translations if files don't exist
        """
        # Always include hardcoded languages
        self._available_languages.update(self.TRANSLATIONS.keys())

        # Check if languages directory exists
        if not self.LANGUAGES_DIR.exists():
            logger.warning(f"Languages directory not found: {self.LANGUAGES_DIR}")
            logger.info("Using hardcoded translations only")
            return

        # Load all .json files from languages directory
        try:
            for lang_file in self.LANGUAGES_DIR.glob('*.json'):
                lang_code = lang_file.stem  # filename without extension
                translations = self._load_language_file(lang_file)

                if translations:
                    self._external_translations[lang_code] = translations
                    self._available_languages.add(lang_code)
                    logger.info(f"Loaded external language file: {lang_code} ({len(translations)} keys)")

                    # Validate translation completeness
                    self._validate_translation(lang_code, translations)

        except Exception as e:
            logger.error(f"Error loading external translations: {e}")

    def _load_language_file(self, file_path: Path) -> Optional[Dict[str, str]]:
        """
        Load a single language JSON file

        Args:
            file_path: Path to the language JSON file

        Returns:
            Dictionary of translations or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)

            if not isinstance(translations, dict):
                logger.error(f"Invalid format in {file_path}: expected JSON object")
                return None

            return translations

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None

    def _validate_translation(self, lang_code: str, translations: Dict[str, str]):
        """
        Validate that a translation has all required keys (comparing to English)

        Args:
            lang_code: Language code
            translations: Translation dictionary
        """
        # Get reference keys from English (hardcoded or external)
        reference_keys = set(self.TRANSLATIONS.get('en', {}).keys())

        # If we have external English, use that as reference
        if 'en' in self._external_translations:
            reference_keys = set(self._external_translations['en'].keys())

        translation_keys = set(translations.keys())

        # Check for missing keys
        missing_keys = reference_keys - translation_keys
        if missing_keys:
            logger.warning(f"Language '{lang_code}' is missing {len(missing_keys)} keys: {', '.join(sorted(missing_keys)[:5])}{'...' if len(missing_keys) > 5 else ''}")

        # Check for extra keys
        extra_keys = translation_keys - reference_keys
        if extra_keys:
            logger.info(f"Language '{lang_code}' has {len(extra_keys)} extra keys not in reference")

    def get_current_language(self) -> str:
        """Get current language code"""
        return self._current_language

    def set_language(self, language: str):
        """
        Set the current language

        Args:
            language: Language code (e.g., 'en', 'fr', or any custom language)
        """
        # Check if language is available (external or hardcoded)
        if language not in self._available_languages:
            logger.warning(f"Unknown language: {language}, keeping current language")
            logger.info(f"Available languages: {', '.join(sorted(self._available_languages))}")
            return

        self._current_language = language
        logger.info(f"Language changed to: {language}")

        # Notify observers
        self._notify_observers()

    def get_available_languages(self) -> Dict[str, str]:
        """
        Get dictionary of language codes to display names

        Returns all discovered languages (both hardcoded and external)
        """
        result = {}

        for lang_code in sorted(self._available_languages):
            # Try to get display name from the language's own translations
            # First check external, then hardcoded
            lang_key = f'lang_{lang_code.lower()}'

            if lang_code in self._external_translations:
                # Check if language defines its own name
                display_name = self._external_translations[lang_code].get(
                    lang_key,
                    self._external_translations[lang_code].get('lang_name', lang_code.upper())
                )
            elif lang_code in self.TRANSLATIONS:
                # Check hardcoded translations
                display_name = self.TRANSLATIONS[lang_code].get(lang_key, lang_code.upper())
            else:
                # Fallback to language code in uppercase
                display_name = lang_code.upper()

            result[lang_code] = display_name

        return result

    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language

        Priority: External translations > Hardcoded translations > Key itself

        Args:
            key: Translation key
            **kwargs: Format parameters for string interpolation

        Returns:
            Translated string or key if not found
        """
        text = None

        # 1. Try external translation for current language
        if self._current_language in self._external_translations:
            text = self._external_translations[self._current_language].get(key)

        # 2. Fallback to hardcoded translation for current language
        if text is None and self._current_language in self.TRANSLATIONS:
            text = self.TRANSLATIONS[self._current_language].get(key)

        # 3. Fallback to external English
        if text is None and 'en' in self._external_translations:
            text = self._external_translations['en'].get(key)

        # 4. Fallback to hardcoded English
        if text is None:
            text = self.TRANSLATIONS.get('en', {}).get(key)

        # 5. Final fallback: return the key itself
        if text is None:
            text = key

        # Apply string formatting if kwargs provided
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception as e:
                logger.error(f"Error formatting translation '{key}': {e}")

        return text

    def register_observer(self, callback):
        """
        Register a callback for language changes

        Args:
            callback: Function to call when language changes (no arguments)
        """
        if callback not in self._observers:
            self._observers.append(callback)
            logger.debug(f"Registered i18n observer: {callback}")

    def unregister_observer(self, callback):
        """
        Unregister a language change observer

        Args:
            callback: Previously registered callback
        """
        if callback in self._observers:
            self._observers.remove(callback)
            logger.debug(f"Unregistered i18n observer: {callback}")

    def _notify_observers(self):
        """Notify all registered observers of language change"""
        logger.info(f"Notifying {len(self._observers)} i18n observers")
        for callback in self._observers:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error notifying i18n observer {callback}: {e}")


# Convenience function for global access
def get_i18n() -> I18n:
    """Get the global I18n instance"""
    return I18n.get_instance()


# Convenience function for translation
def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current language

    Args:
        key: Translation key
        **kwargs: Format parameters

    Returns:
        Translated string
    """
    return I18n.get_instance().t(key, **kwargs)
