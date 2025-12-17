"""
I18n Bridge - Internationalization for DataForge Studio with PySide6
Simplified version with Observer pattern support
"""

from typing import Dict, List, Callable


class I18nBridge:
    """
    Internationalization manager with Observer pattern.

    Provides simple translation system compatible with PySide6.
    """

    _instance = None

    # Translation dictionaries
    TRANSLATIONS = {
        'en': {
            # Menu items
            'menu_file': 'File',
            'menu_new_connection': 'New Connection',
            'menu_import': 'Import',
            'menu_quit': 'Quit',

            'menu_view': 'Resources',
            'menu_workspaces': 'Workspaces',
            'menu_workspaces_all': 'All',
            'menu_workspaces_manage': 'Manage workspaces...',
            'menu_data_lake': 'Data Lake',
            'menu_database': 'Databases',
            'menu_queries': 'Queries',
            'menu_scripts': 'Scripts',
            'menu_jobs': 'Jobs',
            'menu_data_explorer': 'Data Explorer',

            'menu_settings': 'Settings',
            'option': 'Options',
            'menu_preferences': 'Preferences',
            'menu_themes': 'Themes',

            'menu_help': 'Help',
            'menu_documentation': 'Documentation',
            'menu_about': 'About',
            'menu_check_updates': 'Check for Updates',

            # Buttons
            'btn_refresh': 'Refresh',
            'btn_add': 'Add',
            'btn_edit': 'Edit',
            'btn_delete': 'Delete',
            'btn_execute': 'Execute',
            'btn_import': 'Import',
            'btn_export': 'Export',
            'btn_settings': 'Settings',
            'btn_apply': 'Apply',
            'btn_ok': 'OK',
            'btn_cancel': 'Cancel',
            'btn_close': 'Close',

            # Settings
            'settings_theme': 'Theme',
            'settings_select_theme': 'Select Theme:',
            'settings_language': 'Language',
            'settings_select_language': 'Select Language:',
            'settings_applied': 'Settings applied successfully',
            'current_settings': 'Current Settings',
            'opt_current_language': 'Current Language:',
            'opt_current_theme': 'Current Theme:',
            'language_already_selected': 'This language is already selected',

            # Status messages
            'status_ready': 'Ready',
            'status_viewing_data_lake': 'Viewing Data Lake',
            'status_viewing_database': 'Database Manager',
            'status_viewing_queries': 'Queries Manager',
            'status_viewing_scripts': 'Scripts Manager',
            'status_viewing_jobs': 'Jobs Manager',
            'status_viewing_resources': 'Resources Manager',
            'status_viewing_settings': 'Viewing Settings',
            'status_viewing_theme_editor': 'Theme Editor',
            'status_viewing_help': 'Viewing Help',
            'status_viewing_rootfolders': 'RootFolders Manager',
            'status_version_up_to_date': 'Your version is up to date',

            # Log messages
            'log_refreshing': 'Refreshing data...',

            # Common
            'yes': 'Yes',
            'no': 'No',
            'error': 'Error',
            'warning': 'Warning',
            'info': 'Information',
            'loading': 'Loading...',

            # Queries Manager
            'col_name': 'Name',
            'col_database': 'Database',
            'col_description': 'Description',
            'query_details': 'Query Details',
            'field_name': 'Name:',
            'field_description': 'Description:',
            'field_database': 'Database:',
            'field_created': 'Created:',
            'field_modified': 'Modified:',
            'sql_placeholder': 'SQL query text will appear here...',
            'error_loading_queries': 'Failed to load queries',
            'error_title': 'Error',
            'feature_coming_soon': 'This feature is coming soon',
            'add_query_title': 'Add Query',
            'edit_query_title': 'Edit Query',
            'delete_query_title': 'Delete Query',
            'execute_query_title': 'Execute Query',
            'select_query_first': 'Please select a query first',
            'confirm_delete_query': 'Are you sure you want to delete query "{name}"?',
            'query_deleted': 'Query deleted successfully',

            # Scripts Manager
            'col_type': 'Type',
            'script_details': 'Script Details',
            'field_type': 'Type:',
            'code_placeholder': 'Python code will appear here...',
            'error_loading_scripts': 'Failed to load scripts',
            'btn_run': 'Run',
            'add_script_title': 'Add Script',
            'edit_script_title': 'Edit Script',
            'delete_script_title': 'Delete Script',
            'run_script_title': 'Run Script',
            'select_script_first': 'Please select a script first',
            'confirm_delete_script': 'Are you sure you want to delete script "{name}"?',
            'script_deleted': 'Script deleted successfully',
            'script_execution_started': 'Script execution started...',

            # Jobs Manager
            'col_status': 'Status',
            'col_schedule': 'Schedule',
            'job_details': 'Job Details',
            'field_status': 'Status:',
            'field_schedule': 'Schedule:',
            'field_last_run': 'Last Run:',
            'field_next_run': 'Next Run:',
            'field_script': 'Script:',
            'job_config_placeholder': 'Job configuration will appear here...',
            'error_loading_jobs': 'Failed to load jobs',
            'btn_run_now': 'Run Now',
            'btn_enable': 'Enable/Disable',
            'add_job_title': 'Add Job',
            'edit_job_title': 'Edit Job',
            'delete_job_title': 'Delete Job',
            'run_job_title': 'Run Job',
            'toggle_job_title': 'Toggle Job',
            'select_job_first': 'Please select a job first',
            'confirm_delete_job': 'Are you sure you want to delete job "{name}"?',
            'job_deleted': 'Job deleted successfully',
            'job_execution_started': 'Job execution started...',
            'job_status_changed': 'Job status changed to: {status}',

            # Database Manager
            'btn_format': 'Format SQL',
            'btn_clear': 'Clear',
            'btn_new_tab': 'New Tab',
            'btn_connect': 'Connect',
            'connection_label': 'Connection:',
            'sql_editor_label': 'SQL Editor',
            'results_label': 'Results',
            'sql_editor_placeholder': 'Enter SQL query here...\n\nExample:\nSELECT * FROM users\nWHERE active = 1\nORDER BY created_date DESC;',
            'no_connection': 'No Connection',
            'new_query': 'New Query',
            'empty_query_warning': 'Please enter a SQL query',
            'format_sql_title': 'Format SQL',
            'clear_editor_title': 'Clear Editor',
            'confirm_clear_editor': 'Are you sure you want to clear the editor and results?',
            'export_results_title': 'Export Results',
            'no_results_to_export': 'No results to export',
            'confirm_close_tab': 'This tab contains unsaved SQL query. Close anyway?',
            'close_tab_title': 'Close Tab',
            'select_connection_first': 'Please select a database connection first',
            'connect_title': 'Connect to Database',
            'connection_success': 'Successfully connected to: {name}',
            'connection_failed': 'Failed to connect to database',
            'error_loading_connections': 'Failed to load database connections',

            # Data Explorer
            'col_path': 'Path',
            'item_details': 'Item Details',
            'field_path': 'Path:',
            'field_size': 'Size:',
            'btn_add_project': 'Add Project',
            'btn_add_file_root': 'Add File Root',
            'btn_open_location': 'Open Location',
            'text_viewer_placeholder': 'File content will appear here...',
            'error_loading_projects': 'Failed to load projects',
            'error_loading_csv': 'Failed to load CSV file',
            'error_loading_file': 'Failed to load file',
            'add_project_title': 'Add Project',
            'add_file_root_title': 'Add File Root',
            'delete_item_title': 'Delete Item',
            'open_location_title': 'Open Location',
            'select_project_first': 'Please select a project first',
            'select_item_first': 'Please select an item first',
            'confirm_delete_item': 'Are you sure you want to delete "{name}"?',
            'item_deleted': 'Item deleted successfully',
            'no_path_for_item': 'This item has no file path',
        },

        'fr': {
            # Menu items
            'menu_file': 'Fichier',
            'menu_new_connection': 'Nouvelle Connexion',
            'menu_import': 'Importer',
            'menu_quit': 'Quitter',

            'menu_view': 'Ressources',
            'menu_workspaces': 'Espaces de travail',
            'menu_workspaces_all': 'Tous',
            'menu_workspaces_manage': 'Gérer les espaces de travail...',
            'menu_data_lake': 'Data Lake',
            'menu_database': 'Bases de Données',
            'menu_queries': 'Requêtes',
            'menu_scripts': 'Scripts',
            'menu_jobs': 'Jobs',
            'menu_data_explorer': 'Explorateur de Données',

            'menu_settings': 'Paramètres',
            'option': 'Options',
            'menu_preferences': 'Préférences',
            'menu_themes': 'Thèmes',

            'menu_help': 'Aide',
            'menu_documentation': 'Documentation',
            'menu_about': 'À propos',
            'menu_check_updates': 'Vérifier les Mises à Jour',

            # Buttons
            'btn_refresh': 'Actualiser',
            'btn_add': 'Ajouter',
            'btn_edit': 'Éditer',
            'btn_delete': 'Supprimer',
            'btn_execute': 'Exécuter',
            'btn_import': 'Importer',
            'btn_export': 'Exporter',
            'btn_settings': 'Paramètres',
            'btn_apply': 'Appliquer',
            'btn_ok': 'OK',
            'btn_cancel': 'Annuler',
            'btn_close': 'Fermer',

            # Settings
            'settings_theme': 'Thème',
            'settings_select_theme': 'Sélectionner le Thème :',
            'settings_language': 'Langue',
            'settings_select_language': 'Sélectionner la Langue :',
            'settings_applied': 'Paramètres appliqués avec succès',
            'current_settings': 'Paramètres actuels',
            'opt_current_language': 'Langue actuelle :',
            'opt_current_theme': 'Thème actuel :',
            'language_already_selected': 'Cette langue est déjà sélectionnée',

            # Status messages
            'status_ready': 'Prêt',
            'status_viewing_data_lake': 'Affichage Data Lake',
            'status_viewing_database': 'Gestionnaire de Base de Données',
            'status_viewing_queries': 'Gestionnaire de Requêtes',
            'status_viewing_scripts': 'Gestionnaire de Scripts',
            'status_viewing_jobs': 'Gestionnaire de Jobs',
            'status_viewing_resources': 'Gestionnaire de Ressources',
            'status_viewing_settings': 'Affichage Paramètres',
            'status_viewing_theme_editor': 'Éditeur de Thèmes',
            'status_viewing_help': 'Affichage Aide',
            'status_viewing_rootfolders': 'Gestionnaire RootFolders',
            'status_version_up_to_date': 'Votre version est à jour',

            # Log messages
            'log_refreshing': 'Actualisation des données...',

            # Common
            'yes': 'Oui',
            'no': 'Non',
            'error': 'Erreur',
            'warning': 'Avertissement',
            'info': 'Information',
            'loading': 'Chargement...',

            # Queries Manager
            'col_name': 'Nom',
            'col_database': 'Base de Données',
            'col_description': 'Description',
            'query_details': 'Détails de la Requête',
            'field_name': 'Nom :',
            'field_description': 'Description :',
            'field_database': 'Base de Données :',
            'field_created': 'Créé le :',
            'field_modified': 'Modifié le :',
            'sql_placeholder': 'Le texte de la requête SQL apparaîtra ici...',
            'error_loading_queries': 'Échec du chargement des requêtes',
            'error_title': 'Erreur',
            'feature_coming_soon': 'Cette fonctionnalité arrive bientôt',
            'add_query_title': 'Ajouter une Requête',
            'edit_query_title': 'Éditer la Requête',
            'delete_query_title': 'Supprimer la Requête',
            'execute_query_title': 'Exécuter la Requête',
            'select_query_first': 'Veuillez d\'abord sélectionner une requête',
            'confirm_delete_query': 'Êtes-vous sûr de vouloir supprimer la requête "{name}" ?',
            'query_deleted': 'Requête supprimée avec succès',

            # Scripts Manager
            'col_type': 'Type',
            'script_details': 'Détails du Script',
            'field_type': 'Type :',
            'code_placeholder': 'Le code Python apparaîtra ici...',
            'error_loading_scripts': 'Échec du chargement des scripts',
            'btn_run': 'Exécuter',
            'add_script_title': 'Ajouter un Script',
            'edit_script_title': 'Éditer le Script',
            'delete_script_title': 'Supprimer le Script',
            'run_script_title': 'Exécuter le Script',
            'select_script_first': 'Veuillez d\'abord sélectionner un script',
            'confirm_delete_script': 'Êtes-vous sûr de vouloir supprimer le script "{name}" ?',
            'script_deleted': 'Script supprimé avec succès',
            'script_execution_started': 'Exécution du script démarrée...',

            # Jobs Manager
            'col_status': 'Statut',
            'col_schedule': 'Planification',
            'job_details': 'Détails du Job',
            'field_status': 'Statut :',
            'field_schedule': 'Planification :',
            'field_last_run': 'Dernière Exécution :',
            'field_next_run': 'Prochaine Exécution :',
            'field_script': 'Script :',
            'job_config_placeholder': 'La configuration du job apparaîtra ici...',
            'error_loading_jobs': 'Échec du chargement des jobs',
            'btn_run_now': 'Exécuter Maintenant',
            'btn_enable': 'Activer/Désactiver',
            'add_job_title': 'Ajouter un Job',
            'edit_job_title': 'Éditer le Job',
            'delete_job_title': 'Supprimer le Job',
            'run_job_title': 'Exécuter le Job',
            'toggle_job_title': 'Basculer le Job',
            'select_job_first': 'Veuillez d\'abord sélectionner un job',
            'confirm_delete_job': 'Êtes-vous sûr de vouloir supprimer le job "{name}" ?',
            'job_deleted': 'Job supprimé avec succès',
            'job_execution_started': 'Exécution du job démarrée...',
            'job_status_changed': 'Statut du job changé à : {status}',

            # Database Manager
            'btn_format': 'Formater SQL',
            'btn_clear': 'Effacer',
            'btn_new_tab': 'Nouvel Onglet',
            'btn_connect': 'Connecter',
            'connection_label': 'Connexion :',
            'sql_editor_label': 'Éditeur SQL',
            'results_label': 'Résultats',
            'sql_editor_placeholder': 'Saisissez votre requête SQL ici...\n\nExemple :\nSELECT * FROM users\nWHERE active = 1\nORDER BY created_date DESC;',
            'no_connection': 'Aucune Connexion',
            'new_query': 'Nouvelle Requête',
            'empty_query_warning': 'Veuillez saisir une requête SQL',
            'format_sql_title': 'Formater SQL',
            'clear_editor_title': 'Effacer l\'Éditeur',
            'confirm_clear_editor': 'Êtes-vous sûr de vouloir effacer l\'éditeur et les résultats ?',
            'export_results_title': 'Exporter les Résultats',
            'no_results_to_export': 'Aucun résultat à exporter',
            'confirm_close_tab': 'Cet onglet contient une requête SQL non sauvegardée. Fermer quand même ?',
            'close_tab_title': 'Fermer l\'Onglet',
            'select_connection_first': 'Veuillez d\'abord sélectionner une connexion à la base de données',
            'connect_title': 'Connexion à la Base de Données',
            'connection_success': 'Connecté avec succès à : {name}',
            'connection_failed': 'Échec de la connexion à la base de données',
            'error_loading_connections': 'Échec du chargement des connexions',

            # Data Explorer
            'col_path': 'Chemin',
            'item_details': 'Détails de l\'Élément',
            'field_path': 'Chemin :',
            'field_size': 'Taille :',
            'btn_add_project': 'Ajouter un Projet',
            'btn_add_file_root': 'Ajouter un Répertoire',
            'btn_open_location': 'Ouvrir l\'Emplacement',
            'text_viewer_placeholder': 'Le contenu du fichier apparaîtra ici...',
            'error_loading_projects': 'Échec du chargement des projets',
            'error_loading_csv': 'Échec du chargement du fichier CSV',
            'error_loading_file': 'Échec du chargement du fichier',
            'add_project_title': 'Ajouter un Projet',
            'add_file_root_title': 'Ajouter un Répertoire',
            'delete_item_title': 'Supprimer l\'Élément',
            'open_location_title': 'Ouvrir l\'Emplacement',
            'select_project_first': 'Veuillez d\'abord sélectionner un projet',
            'select_item_first': 'Veuillez d\'abord sélectionner un élément',
            'confirm_delete_item': 'Êtes-vous sûr de vouloir supprimer "{name}" ?',
            'item_deleted': 'Élément supprimé avec succès',
            'no_path_for_item': 'Cet élément n\'a pas de chemin de fichier',
        }
    }

    def __init__(self):
        """Initialize i18n manager"""
        self._current_language = 'en'
        self._observers: List[Callable] = []

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
        if lang_code not in self.TRANSLATIONS:
            print(f"Warning: Unknown language '{lang_code}', keeping current language")
            return

        self._current_language = lang_code
        self._notify_observers()

    def get_current_language(self) -> str:
        """Get current language code"""
        return self._current_language

    def get_available_languages(self) -> Dict[str, str]:
        """
        Get dictionary of language codes to display names.

        Returns:
            Dict mapping lang_code to display_name
        """
        return {
            'en': 'English',
            'fr': 'Français'
        }

    def tr(self, key: str, **kwargs) -> str:
        """
        Translate a key to current language.

        Args:
            key: Translation key
            **kwargs: Format parameters for string interpolation

        Returns:
            Translated string or key if not found
        """
        # Try current language
        text = self.TRANSLATIONS.get(self._current_language, {}).get(key)

        # Fallback to English
        if text is None:
            text = self.TRANSLATIONS.get('en', {}).get(key)

        # Final fallback: return key
        if text is None:
            text = key

        # Apply string formatting if kwargs provided
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception as e:
                print(f"Error formatting translation '{key}': {e}")

        return text

    def register_observer(self, callback: Callable):
        """
        Register observer for language changes.

        Args:
            callback: Function to call when language changes (no arguments)
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def unregister_observer(self, callback: Callable):
        """
        Unregister observer.

        Args:
            callback: Previously registered callback
        """
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self):
        """Notify all registered observers of language change"""
        for observer in self._observers:
            try:
                observer()
            except Exception as e:
                print(f"Error notifying i18n observer: {e}")


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
    return I18nBridge.instance().tr(key, **kwargs)
