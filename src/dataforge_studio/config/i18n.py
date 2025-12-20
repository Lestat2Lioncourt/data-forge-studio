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
            'menu_view': 'Resources',
            'option': 'Options',
            'menu_preferences': 'Preferences...',
            'menu_exit': 'Exit',
            'menu_new_connection': 'New Connection',
            'menu_import': 'Import',
            'menu_quit': 'Quit',
            'menu_data_lake': 'Data Lake',
            'menu_database': 'Databases',
            'menu_queries': 'Queries',
            'menu_scripts': 'Scripts',
            'menu_jobs': 'Jobs',
            'menu_data_explorer': 'Data Explorer',
            'menu_themes': 'Themes...',
            'menu_documentation': 'Documentation',
            'menu_about': 'About',
            'menu_check_updates': 'Check for Updates',
            'menu_help': 'Help',
            'menu_workspaces': 'Workspaces',
            'menu_workspaces_all': 'All',
            'menu_workspaces_manage': 'Manage workspaces...',

            # Navigation tree
            'nav_data_lake': 'Data Lake',
            'nav_database_management': 'Database Management',
            'nav_databases': 'Databases',
            'nav_queries': 'Queries',
            'nav_scripts': 'Scripts',
            'nav_jobs': 'Jobs',
            'nav_data_explorer': 'Data Explorer',
            'nav_settings': 'Settings',
            'nav_help': 'Help',

            # Status bar
            'status_ready': 'Ready',
            'status_viewing_data_lake': 'Viewing Data Lake',
            'status_viewing_database': 'Viewing Database Manager',
            'status_viewing_queries': 'Viewing Queries',
            'status_viewing_scripts': 'Viewing Scripts',
            'status_viewing_jobs': 'Viewing Jobs',
            'status_viewing_data_explorer': 'Viewing Data Explorer',
            'status_viewing_settings': 'Viewing Settings',
            'status_viewing_help': 'Viewing Help',
            'status_viewing_rootfolders': 'Viewing RootFolders',
            'status_viewing_workspaces': 'Viewing Workspaces',

            # Toolbar buttons
            'btn_data_explorer': 'Data Explorer',
            'btn_databases': 'Databases',
            'btn_new_tab': 'New Tab',
            'btn_refresh_schema': 'Refresh Schema',

            # Database Manager
            'database_name': 'Database',
            'database_type': 'Type',
            'schema_explorer_label': 'Database Schema',
            'welcome_database_manager': 'Welcome to Database Manager',
            'click_new_tab_to_start': 'Click "New Tab" to start writing queries',
            'welcome_tab': 'Welcome',
            'select_top_100': 'SELECT Top 100 rows',
            'select_top_1000': 'SELECT Top 1000 rows',
            'select_top_10000': 'SELECT Top 10000 rows',
            'select_all': 'SELECT ALL rows (no limit)',
            'database_not_connected': 'Database not connected',
            'no_connections_configured': 'No connections configured',
            'new_query': 'New Query',
            'no_database_selected': 'No database selected',
            'select_database_first': 'Please select a database first',
            'error_loading_connections': 'Error loading database connections',
            'execute_query': 'Execute',
            'format_sql': 'Format',
            'clear_query': 'Clear',
            'export_results': 'Export',
            'enter_sql_query_here': 'Enter your SQL query here...',
            'no_query_to_execute': 'No query to execute',
            'no_results_to_export': 'No results to export',
            'query_executed_successfully': 'Query executed successfully ({rows} rows)',
            'query_executed_no_results': 'Query executed successfully (no results returned)',
            'query_execution_error': 'Error executing query',

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

            # Options/Settings Frame
            'opt_category': 'Category',
            'opt_language': 'Language',
            'opt_theme': 'Theme',
            'opt_debug_borders': 'Object Borders',
            'opt_current_language': 'Current Language:',
            'opt_current_theme': 'Current Theme:',
            'opt_select_language': 'Select Language:',
            'opt_select_theme': 'Select Theme:',
            'current_settings': 'Current Settings',
            'settings_theme': 'Theme',
            'settings_language': 'Language',
            'settings_select_theme': 'Select Theme:',
            'settings_select_language': 'Select Language:',
            'settings_applied': 'Settings applied successfully',
            'language_already_selected': 'This language is already selected',
            'btn_apply': 'Apply',
            'btn_save': 'Save',
            'btn_cancel': 'Cancel',

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
            'status_connection_created': 'Connection created successfully',
            'status_viewing_images': 'Viewing Image Library',
        },

        'fr': {
            # Menu items
            'menu_file': 'Fichier',
            'menu_edit': 'Édition',
            'menu_view': 'Ressources',
            'option': 'Options',
            'menu_preferences': 'Préférences...',
            'menu_exit': 'Quitter',
            'menu_new_connection': 'Nouvelle Connexion',
            'menu_import': 'Importer',
            'menu_quit': 'Quitter',
            'menu_data_lake': 'Data Lake',
            'menu_database': 'Bases de Données',
            'menu_queries': 'Requêtes',
            'menu_scripts': 'Scripts',
            'menu_jobs': 'Tâches',
            'menu_data_explorer': 'Explorateur de Données',
            'menu_themes': 'Thèmes...',
            'menu_documentation': 'Documentation',
            'menu_about': 'À propos',
            'menu_check_updates': 'Vérifier les Mises à Jour',
            'menu_help': 'Aide',
            'menu_workspaces': 'Espaces de travail',
            'menu_workspaces_all': 'Tous',
            'menu_workspaces_manage': 'Gérer les espaces de travail...',

            # Navigation tree
            'nav_data_lake': 'Data Lake',
            'nav_database_management': 'Gestion des Bases de Données',
            'nav_databases': 'Bases de Données',
            'nav_queries': 'Requêtes',
            'nav_scripts': 'Scripts',
            'nav_jobs': 'Tâches',
            'nav_data_explorer': 'Explorateur de Données',
            'nav_settings': 'Paramètres',
            'nav_help': 'Aide',

            # Status bar
            'status_ready': 'Prêt',
            'status_viewing_data_lake': 'Affichage Data Lake',
            'status_viewing_database': 'Affichage Gestionnaire de Bases de Données',
            'status_viewing_queries': 'Affichage Requêtes',
            'status_viewing_scripts': 'Affichage Scripts',
            'status_viewing_jobs': 'Affichage Tâches',
            'status_viewing_data_explorer': 'Affichage Explorateur de Données',
            'status_viewing_settings': 'Affichage Paramètres',
            'status_viewing_help': 'Affichage Aide',
            'status_viewing_rootfolders': 'Affichage RootFolders',
            'status_viewing_workspaces': 'Affichage Espaces de Travail',

            # Toolbar buttons
            'btn_data_explorer': 'Explorateur de Données',
            'btn_databases': 'Bases de Données',
            'btn_new_tab': 'Nouvel Onglet',
            'btn_refresh_schema': 'Actualiser le Schéma',

            # Database Manager
            'database_name': 'Base de Données',
            'database_type': 'Type',
            'schema_explorer_label': 'Schéma de Base de Données',
            'welcome_database_manager': 'Bienvenue dans le Gestionnaire de Bases de Données',
            'click_new_tab_to_start': 'Cliquez sur "Nouvel Onglet" pour commencer à écrire des requêtes',
            'welcome_tab': 'Bienvenue',
            'select_top_100': 'SELECT Top 100 lignes',
            'select_top_1000': 'SELECT Top 1000 lignes',
            'select_top_10000': 'SELECT Top 10000 lignes',
            'select_all': 'SELECT TOUTES les lignes (sans limite)',
            'database_not_connected': 'Base de données non connectée',
            'no_connections_configured': 'Aucune connexion configurée',
            'new_query': 'Nouvelle Requête',
            'no_database_selected': 'Aucune base de données sélectionnée',
            'select_database_first': 'Veuillez d\'abord sélectionner une base de données',
            'error_loading_connections': 'Erreur lors du chargement des connexions',
            'execute_query': 'Exécuter',
            'format_sql': 'Formater',
            'clear_query': 'Effacer',
            'export_results': 'Exporter',
            'enter_sql_query_here': 'Entrez votre requête SQL ici...',
            'no_query_to_execute': 'Aucune requête à exécuter',
            'no_results_to_export': 'Aucun résultat à exporter',
            'query_executed_successfully': 'Requête exécutée avec succès ({rows} lignes)',
            'query_executed_no_results': 'Requête exécutée avec succès (aucun résultat retourné)',
            'query_execution_error': 'Erreur lors de l\'exécution de la requête',

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

            # Options/Settings Frame
            'opt_category': 'Catégorie',
            'opt_language': 'Langue',
            'opt_theme': 'Thème',
            'opt_debug_borders': 'Contours objets',
            'opt_current_language': 'Langue Actuelle :',
            'opt_current_theme': 'Thème Actuel :',
            'opt_select_language': 'Sélectionner la Langue :',
            'opt_select_theme': 'Sélectionner le Thème :',
            'current_settings': 'Paramètres Actuels',
            'settings_theme': 'Thème',
            'settings_language': 'Langue',
            'settings_select_theme': 'Sélectionner le Thème :',
            'settings_select_language': 'Sélectionner la Langue :',
            'settings_applied': 'Paramètres appliqués avec succès',
            'language_already_selected': 'Cette langue est déjà sélectionnée',
            'btn_apply': 'Appliquer',
            'btn_save': 'Enregistrer',
            'btn_cancel': 'Annuler',

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
            'status_connection_created': 'Connexion créée avec succès',
            'status_viewing_images': 'Affichage Bibliothèque d\'Images',
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
