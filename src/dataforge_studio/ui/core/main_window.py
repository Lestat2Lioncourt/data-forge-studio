"""
Main Window - DataForge Studio v0.50
Main application window using window-template
"""

from PySide6.QtWidgets import QWidget, QStackedWidget
from PySide6.QtCore import Slot

from ..window_template import create_window
from .theme_bridge import ThemeBridge
from .i18n_bridge import I18nBridge, tr


class DataForgeMainWindow:
    """Main application window for DataForge Studio."""

    def __init__(self):
        # Create window using factory from window-template
        self.wrapper = create_window("DataForge Studio v0.50", easy_resize=True)
        self.window = self.wrapper.window

        # Initialize managers
        self.theme_bridge = ThemeBridge.get_instance()
        self.i18n_bridge = I18nBridge.instance()

        # Frame and manager references (will be set when created)
        self.data_lake_frame = None
        self.settings_frame = None
        self.help_frame = None
        self.queries_manager = None
        self.scripts_manager = None
        self.jobs_manager = None
        self.database_manager = None
        self.data_explorer = None
        self.stacked_widget = None

        # Setup UI
        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._connect_signals()

        # Apply initial theme
        self.theme_bridge.apply_theme(self.window, "dark_mode")

    def _setup_menu_bar(self):
        """Setup menu bar with dropdowns."""
        menu_bar = self.window.menu_bar

        # File menu
        menu_bar.add_menu_with_submenu("file", tr("menu_file"), [
            (tr("menu_new_connection"), self._new_connection),
            (tr("menu_import"), self._import_data),
            (None, None),  # Separator
            (tr("menu_quit"), self.window.close)
        ])

        # View menu
        menu_bar.add_menu_with_submenu("view", tr("menu_view"), [
            (tr("menu_data_lake"), lambda: self._switch_frame("data_lake")),
            (None, None),  # Separator
            (tr("menu_database"), lambda: self._switch_frame("database")),
            (tr("menu_queries"), lambda: self._switch_frame("queries")),
            (tr("menu_scripts"), lambda: self._switch_frame("scripts")),
            (tr("menu_jobs"), lambda: self._switch_frame("jobs")),
            (tr("menu_data_explorer"), lambda: self._switch_frame("data_explorer"))
        ])

        # Settings menu
        menu_bar.add_menu_with_submenu("settings", tr("menu_settings"), [
            (tr("menu_preferences"), lambda: self._switch_frame("settings")),
            (tr("menu_themes"), self._show_theme_dialog)
        ])

        # Help menu
        menu_bar.add_menu_with_submenu("help", tr("menu_help"), [
            (tr("menu_documentation"), lambda: self._switch_frame("help")),
            (tr("menu_about"), self._show_about),
            (None, None),
            (tr("menu_check_updates"), self._check_updates)
        ])

    def _setup_central_widget(self):
        """Setup central stacked widget for different frames."""
        self.stacked_widget = QStackedWidget()

        # For now, create a simple placeholder widget
        # Real frames will be created in Phase 1.4
        placeholder = QWidget()
        self.stacked_widget.addWidget(placeholder)

        # Set as right panel (single mode)
        self.window.set_right_panel_widget(self.stacked_widget)

    def set_frames(self, data_lake_frame, settings_frame, help_frame,
                   queries_manager=None, scripts_manager=None, jobs_manager=None,
                   database_manager=None, data_explorer=None):
        """
        Set the frame and manager widgets after they're created.
        This allows frames and managers to be created separately and injected.

        Args:
            data_lake_frame: DataLakeFrame instance
            settings_frame: SettingsFrame instance
            help_frame: HelpFrame instance
            queries_manager: QueriesManager instance (optional)
            scripts_manager: ScriptsManager instance (optional)
            jobs_manager: JobsManager instance (optional)
            database_manager: DatabaseManager instance (optional)
            data_explorer: DataExplorer instance (optional)
        """
        self.data_lake_frame = data_lake_frame
        self.settings_frame = settings_frame
        self.help_frame = help_frame
        self.queries_manager = queries_manager
        self.scripts_manager = scripts_manager
        self.jobs_manager = jobs_manager
        self.database_manager = database_manager
        self.data_explorer = data_explorer

        # Clear stacked widget and add all views
        while self.stacked_widget.count() > 0:
            widget = self.stacked_widget.widget(0)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()

        # Add frames
        self.stacked_widget.addWidget(self.data_lake_frame)
        self.stacked_widget.addWidget(self.settings_frame)
        self.stacked_widget.addWidget(self.help_frame)

        # Add managers if provided
        if self.database_manager:
            self.stacked_widget.addWidget(self.database_manager)
        if self.queries_manager:
            self.stacked_widget.addWidget(self.queries_manager)
        if self.scripts_manager:
            self.stacked_widget.addWidget(self.scripts_manager)
        if self.jobs_manager:
            self.stacked_widget.addWidget(self.jobs_manager)
        if self.data_explorer:
            self.stacked_widget.addWidget(self.data_explorer)

        # Initially show data lake
        self.stacked_widget.setCurrentWidget(self.data_lake_frame)

    def _setup_status_bar(self):
        """Setup status bar."""
        self.window.status_bar.set_message(tr("status_ready"))

    def _connect_signals(self):
        """Connect signals and slots."""
        # Connect i18n language change to UI update
        self.i18n_bridge.register_observer(self._on_language_changed)

    def _switch_frame(self, frame_name: str):
        """
        Switch to a different frame or manager.

        Args:
            frame_name: Name of the frame/manager to switch to
        """
        frame_map = {
            "data_lake": (self.data_lake_frame, "status_viewing_data_lake"),
            "settings": (self.settings_frame, "status_viewing_settings"),
            "help": (self.help_frame, "status_viewing_help"),
            "database": (self.database_manager, "status_viewing_database"),
            "queries": (self.queries_manager, "status_viewing_queries"),
            "scripts": (self.scripts_manager, "status_viewing_scripts"),
            "jobs": (self.jobs_manager, "status_viewing_jobs"),
            "data_explorer": (self.data_explorer, "status_viewing_data_explorer")
        }

        if frame_name in frame_map:
            frame, status_key = frame_map[frame_name]
            if frame is not None:
                self.stacked_widget.setCurrentWidget(frame)
                self.window.status_bar.set_message(tr(status_key))
            else:
                # Manager not yet initialized
                self.window.status_bar.set_message(tr("status_ready"))

    def _new_connection(self):
        """Handle new connection action."""
        # TODO: Implement new connection dialog
        print("New connection - to be implemented")

    def _import_data(self):
        """Handle import data action."""
        # TODO: Implement import dialog
        print("Import data - to be implemented")

    def _show_theme_dialog(self):
        """Show theme selection dialog."""
        # TODO: Implement theme dialog
        # For now, just switch to settings
        self._switch_frame("settings")

    def _show_about(self):
        """Show about dialog."""
        # TODO: Implement about dialog
        print("About - to be implemented")

    def _check_updates(self):
        """Check for updates."""
        # TODO: Implement update checker
        print("Check updates - to be implemented")

    @Slot()
    def _on_language_changed(self):
        """Handle language change - update all UI text."""
        # Recreate menu bar with new language
        # Note: This is a simplified approach, a more elegant solution
        # would be to update only the text without recreating
        self._setup_menu_bar()

    def show(self):
        """Show the window."""
        self.wrapper.show()

    def close(self):
        """Close the window."""
        self.window.close()
