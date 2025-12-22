"""
DataForge Studio - Main entry point
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from .ui.core.main_window import DataForgeMainWindow
from .ui.core.theme_bridge import ThemeBridge
from .ui.core.splash_screen import show_splash_screen
from .core.plugin_manager import PluginManager
from .plugins import ALL_PLUGINS
from .ui.managers import ResourcesManager
from .ui.widgets.icon_sidebar import IconSidebar


def main():
    """Main entry point for DataForge Studio."""

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("DataForge Studio")
    app.setApplicationVersion("0.5.3")
    app.setOrganizationName("DataForge")

    # Set application icon (for taskbar and window)
    icon_path = Path(__file__).parent / "ui" / "assets" / "images" / "DataForge Studio.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        # Fallback to PNG if ICO not found
        icon_path_png = Path(__file__).parent / "ui" / "assets" / "images" / "DataForge Studio.png"
        if icon_path_png.exists():
            app.setWindowIcon(QIcon(str(icon_path_png)))

    # On Windows, set AppUserModelID for taskbar icon grouping
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = 'dataforge.studio.v050'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # Show splash screen
    import time
    splash_start_time = time.time()
    splash = show_splash_screen()

    # Load configuration database
    splash.update_progress("Connexion base de configuration...", 3)
    from .database.config_db import get_config_db
    config_db = get_config_db()

    # Load user preferences
    splash.update_progress("Chargement preferences utilisateur...", 6)
    from .config.user_preferences import UserPreferences
    user_prefs = UserPreferences.instance()
    saved_theme = user_prefs.get("theme", "minimal_dark")

    # Initialize theme bridge
    splash.update_progress("Initialisation gestionnaire themes...", 9)
    theme_bridge = ThemeBridge.get_instance()
    from .ui.core.i18n_bridge import I18nBridge
    i18n_bridge = I18nBridge.instance()

    # Generate and apply global theme
    splash.update_progress(f"Application theme: {saved_theme}...", 12)
    global_qss = theme_bridge.generate_global_qss(saved_theme)
    app.setStyleSheet(global_qss)

    # Create main window
    splash.update_progress("Creation fenetre principale...", 18)
    main_window = DataForgeMainWindow()

    # Initialize Plugin Manager
    splash.update_progress("Initialisation systeme de plugins...", 22)
    plugin_manager = PluginManager()

    # Register all plugins
    splash.update_progress("Enregistrement des plugins...", 26)
    for plugin_class in ALL_PLUGINS:
        plugin_manager.register_class(plugin_class)

    # Initialize plugins with app context
    splash.update_progress("Initialisation des plugins...", 30)
    app_context = {
        'theme_bridge': theme_bridge,
        'i18n_bridge': i18n_bridge,
        'config_db': config_db,
        'user_prefs': user_prefs,
        'main_window': main_window,
    }
    plugin_manager.initialize_all(app_context)

    # Create plugin widgets with progress updates
    plugin_progress = {
        'database': ("Chargement DatabaseManager...", 40),
        'rootfolders': ("Chargement RootFolderManager...", 48),
        'queries': ("Chargement QueriesManager...", 54),
        'scripts': ("Chargement ScriptsManager...", 60),
        'jobs': ("Chargement JobsManager...", 66),
        'images': ("Chargement ImageLibraryManager...", 72),
        'workspaces': ("Chargement WorkspaceManager...", 78),
        'settings': ("Chargement SettingsFrame...", 82),
        'help': ("Chargement HelpFrame...", 86),
    }

    for plugin_id, (message, progress) in plugin_progress.items():
        splash.update_progress(message, progress)
        plugin = plugin_manager.get_plugin(plugin_id)
        if plugin:
            plugin.create_widget()

    # Create ResourcesManager (unified view - not a plugin)
    splash.update_progress("Chargement ResourcesManager...", 88)
    resources_manager = ResourcesManager()

    # Create IconSidebar
    splash.update_progress("Chargement IconSidebar...", 90)
    icon_sidebar = IconSidebar()

    # Get widgets from plugins for backward compatibility with set_frames
    settings_frame = plugin_manager.get_plugin_widget('settings')
    help_frame = plugin_manager.get_plugin_widget('help')
    database_manager = plugin_manager.get_plugin_widget('database')
    rootfolder_manager = plugin_manager.get_plugin_widget('rootfolders')
    queries_manager = plugin_manager.get_plugin_widget('queries')
    scripts_manager = plugin_manager.get_plugin_widget('scripts')
    jobs_manager = plugin_manager.get_plugin_widget('jobs')
    workspace_manager = plugin_manager.get_plugin_widget('workspaces')
    image_library_manager = plugin_manager.get_plugin_widget('images')

    # Set frames and managers in main window
    splash.update_progress("Connexion des composants...", 94)
    main_window.set_frames(
        settings_frame, help_frame,
        rootfolder_manager=rootfolder_manager,
        queries_manager=queries_manager,
        scripts_manager=scripts_manager,
        jobs_manager=jobs_manager,
        database_manager=database_manager,
        resources_manager=resources_manager,
        workspace_manager=workspace_manager,
        image_library_manager=image_library_manager,
        icon_sidebar=icon_sidebar
    )

    # Connect ResourcesManager to all managers
    resources_manager.set_managers(
        database_manager=database_manager,
        rootfolder_manager=rootfolder_manager,
        queries_manager=queries_manager,
        jobs_manager=jobs_manager,
        scripts_manager=scripts_manager,
        image_library_manager=image_library_manager
    )

    # Connect WorkspaceManager to managers for subtree loading
    if workspace_manager:
        workspace_manager.set_managers(
            database_manager=database_manager,
            rootfolder_manager=rootfolder_manager
        )

    # Connect plugin signals
    plugin_manager.connect_all_signals()

    # Finalize
    splash.update_progress("Finalisation...", 98)

    # Connect cleanup to application quit signal using plugin manager
    def on_about_to_quit():
        """Cleanup all resources before application quits (non-blocking)."""
        import threading

        def async_cleanup():
            plugin_manager.cleanup_all()

        # Run in daemon thread so it doesn't block app exit
        thread = threading.Thread(target=async_cleanup, daemon=True)
        thread.start()

    app.aboutToQuit.connect(on_about_to_quit)

    # Show window and close splash (ensure minimum 4 seconds display)
    splash.update_progress("Pret!", 100)

    # Ensure splash is visible for at least 4 seconds
    # Use processEvents loop instead of time.sleep to allow UI updates
    elapsed = time.time() - splash_start_time
    min_splash_time = 4.0
    if elapsed < min_splash_time:
        remaining = min_splash_time - elapsed
        end_time = time.time() + remaining
        while time.time() < end_time:
            app.processEvents()
            time.sleep(0.05)  # Small sleep to avoid CPU spinning

    main_window.show()
    splash.finish(main_window.wrapper)

    # Check for updates after a short delay (non-blocking)
    from PySide6.QtCore import QTimer
    QTimer.singleShot(2000, lambda: _check_updates_on_startup(main_window))

    # Start event loop
    sys.exit(app.exec())


def _check_updates_on_startup(main_window):
    """Check for updates on startup (respects 24h cooldown)."""
    try:
        from .utils.update_checker import get_update_checker

        checker = get_update_checker()

        # Only check if not in cooldown period
        if not checker.should_check():
            return

        result = checker.check_for_update()

        if result:
            version, url, notes = result
            # Show status bar notification
            if hasattr(main_window, 'window') and hasattr(main_window.window, 'status_bar'):
                main_window.window.status_bar.set_message(
                    f"🔔 v{version} disponible - Aide → Vérifier les Mises à Jour"
                )
    except Exception as e:
        print(f"[UpdateChecker] Startup check failed: {e}")


if __name__ == "__main__":
    main()
