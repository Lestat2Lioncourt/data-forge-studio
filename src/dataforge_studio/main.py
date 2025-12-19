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
from .ui.frames.settings_frame import SettingsFrame
from .ui.frames.help_frame import HelpFrame
from .ui.managers import (
    QueriesManager,
    ScriptsManager,
    JobsManager,
    DatabaseManager,
    RootFolderManager,
    WorkspaceManager
)
from .ui.managers.resources_manager_v2 import ResourcesManagerV2
from .ui.managers.image_library_manager import ImageLibraryManager


def main():
    """Main entry point for DataForge Studio."""

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("DataForge Studio")
    app.setApplicationVersion("0.50.0")
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

    # Generate and apply global theme
    splash.update_progress(f"Application theme: {saved_theme}...", 12)
    global_qss = theme_bridge.generate_global_qss(saved_theme)
    app.setStyleSheet(global_qss)

    # Create main window
    splash.update_progress("Creation fenetre principale...", 18)
    main_window = DataForgeMainWindow()

    # Create frames
    splash.update_progress("Chargement SettingsFrame...", 24)
    settings_frame = SettingsFrame()

    splash.update_progress("Chargement HelpFrame...", 30)
    help_frame = HelpFrame()

    # Create managers
    splash.update_progress("Chargement RootFolderManager...", 40)
    rootfolder_manager = RootFolderManager()

    splash.update_progress("Chargement QueriesManager...", 50)
    queries_manager = QueriesManager()

    splash.update_progress("Chargement ScriptsManager...", 58)
    scripts_manager = ScriptsManager()

    splash.update_progress("Chargement JobsManager...", 66)
    jobs_manager = JobsManager()

    splash.update_progress("Chargement DatabaseManager...", 76)
    database_manager = DatabaseManager()

    splash.update_progress("Chargement WorkspaceManager...", 82)
    workspace_manager = WorkspaceManager()

    splash.update_progress("Chargement ImageLibraryManager...", 85)
    image_library_manager = ImageLibraryManager()

    splash.update_progress("Chargement ResourcesManager...", 90)
    resources_manager = ResourcesManagerV2()

    # Set frames and managers in main window (must be before set_managers for signal connection)
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
        image_library_manager=image_library_manager
    )

    # Connect ResourcesManager to all managers (after set_frames for signal connection)
    resources_manager.set_managers(
        database_manager=database_manager,
        rootfolder_manager=rootfolder_manager,
        queries_manager=queries_manager,
        jobs_manager=jobs_manager,
        scripts_manager=scripts_manager,
        image_library_manager=image_library_manager
    )

    # Finalize
    splash.update_progress("Finalisation...", 98)

    # Connect cleanup to application quit signal
    # Note: Cleanup runs in daemon threads so it won't block app exit
    # The main_window._on_close_event already handles cleanup in a daemon thread
    # This is a backup in case the window is closed differently
    def on_about_to_quit():
        """Cleanup all resources before application quits (non-blocking)."""
        import threading

        def async_cleanup():
            if database_manager:
                try:
                    database_manager.cleanup()
                except Exception:
                    pass

        # Run in daemon thread so it doesn't block app exit
        thread = threading.Thread(target=async_cleanup, daemon=True)
        thread.start()
        # Don't wait - the thread is daemon so it will be terminated when app exits

    app.aboutToQuit.connect(on_about_to_quit)

    # Show window and close splash (ensure minimum 4 seconds display)
    splash.update_progress("Pret!", 100)

    # Ensure splash is visible for at least 4 seconds
    elapsed = time.time() - splash_start_time
    min_splash_time = 4.0
    if elapsed < min_splash_time:
        time.sleep(min_splash_time - elapsed)

    main_window.show()
    splash.finish(main_window.wrapper)

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
