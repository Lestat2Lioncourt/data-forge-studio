"""
Main Window - DataForge Studio
Main application window using window-template
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QStackedWidget
from PySide6.QtCore import Slot

from ..templates.window import create_window
from .theme_bridge import ThemeBridge
from .i18n_bridge import I18nBridge, tr
from ...config.user_preferences import UserPreferences


class DataForgeMainWindow:
    """Main application window for DataForge Studio."""

    def __init__(self):
        # Create window using factory from window-template
        self.wrapper = create_window("DataForge Studio", easy_resize=True)
        self.window = self.wrapper.window

        # Initialize managers
        self.theme_bridge = ThemeBridge.get_instance()
        self.i18n_bridge = I18nBridge.instance()
        self.user_prefs = UserPreferences.instance()

        # Frame and manager references (will be set when created)
        self.settings_frame = None
        self.help_frame = None
        self.rootfolder_manager = None
        self.queries_manager = None
        self.scripts_manager = None
        self.jobs_manager = None
        self.database_manager = None
        self.resources_manager = None
        self.workspace_manager = None
        self.image_library_manager = None
        self.icon_sidebar = None
        self.workspace_selector = None
        self.stacked_widget = None
        self._current_view = None  # Track current view
        self._current_workspace_id: Optional[str] = None  # Active workspace filter
        self._pending_update = False  # Flag for update on quit

        # Setup UI
        self._setup_menu_bar()
        self._setup_workspace_selector()
        self._setup_central_widget()
        self._setup_status_bar()
        self._connect_signals()

        # Override close event to cleanup resources
        self._original_close_event = self.window.closeEvent
        self.window.closeEvent = self._on_close_event

        # Apply initial theme (uses current_theme set by generate_global_qss)
        self.theme_bridge.apply_theme(self.window, self.theme_bridge.current_theme)

        # Apply debug borders if enabled in preferences
        if self.user_prefs.get("objects_borders", False):
            self._add_debug_borders()

    def _setup_menu_bar(self):
        """Setup menu bar with dropdowns."""
        menu_bar = self.window.menu_bar

        # Clear existing menus to avoid duplication
        menu_bar.clear_menu()

        # File menu
        menu_bar.add_menu_with_submenu("file", tr("menu_file"), [
            (tr("menu_quit"), self.window.close)
        ])

        # Workspaces - simple button (no submenu, opens directly)
        menu_bar.add_menu_item("workspaces", tr("menu_workspaces"), lambda: self._switch_frame("workspaces"))

        # Resources menu - direct button (opens unified resource view)
        menu_bar.add_menu_item("view", tr("menu_view"), lambda: self._switch_frame("resources"))

        # Options menu
        menu_bar.add_menu_with_submenu("options", tr("option"), [
            (tr("menu_preferences"), lambda: self._switch_frame("options"))
        ])

        # Help menu
        menu_bar.add_menu_with_submenu("help", tr("menu_help"), [
            (tr("menu_documentation"), lambda: self._switch_frame("help")),
            (tr("menu_about"), self._show_about),
            (None, None),
            (tr("menu_check_updates"), self._check_updates)
        ])

    def _setup_workspace_selector(self):
        """Setup workspace filter selector in the menu bar area."""
        from ..widgets.workspace_selector import WorkspaceSelector

        self.workspace_selector = WorkspaceSelector(show_label=True)
        self.workspace_selector.workspace_changed.connect(self._on_workspace_filter_changed)

        # Add to menu bar's right side (if supported by window template)
        if hasattr(self.window.menu_bar, 'add_right_widget'):
            self.window.menu_bar.add_right_widget(self.workspace_selector)
        else:
            # Fallback: add as a menu item that opens workspace selector
            # The workspace selector will still work but won't be visible in menu bar
            pass

    @Slot(object)
    def _on_workspace_filter_changed(self, workspace_id: Optional[str]):
        """
        Handle workspace filter change - refresh all managers with new filter.

        Args:
            workspace_id: Selected workspace ID, or None for "All"
        """
        self._current_workspace_id = workspace_id

        # Update status bar
        if workspace_id:
            workspace = self.workspace_selector.get_current_workspace()
            if workspace:
                self.window.status_bar.set_message(f"Workspace: {workspace.name}")
        else:
            self.window.status_bar.set_message(tr("status_ready"))

        # Notify all managers to refresh with new filter
        self._apply_workspace_filter(workspace_id)

    def _apply_workspace_filter(self, workspace_id: Optional[str]):
        """
        Apply workspace filter to all managers.

        Args:
            workspace_id: Workspace ID to filter by, or None for all
        """
        # Apply filter to managers that support it
        managers_with_filter = [
            self.resources_manager,
            self.queries_manager,
            self.jobs_manager,
            self.scripts_manager,
            self.rootfolder_manager,
        ]

        for manager in managers_with_filter:
            if manager and hasattr(manager, 'set_workspace_filter'):
                manager.set_workspace_filter(workspace_id)

    def get_current_workspace_id(self) -> Optional[str]:
        """Get the current workspace filter ID."""
        return self._current_workspace_id

    def _setup_central_widget(self):
        """Setup central stacked widget for different frames."""
        self.stacked_widget = QStackedWidget()

        # For now, create a simple placeholder widget
        # Real frames will be created in Phase 1.4
        placeholder = QWidget()
        self.stacked_widget.addWidget(placeholder)

        # Set as right panel (single mode)
        self.window.set_right_panel_widget(self.stacked_widget)

        # Left panel will contain icon sidebar (set in set_frames)

    def set_frames(self, settings_frame, help_frame,
                   rootfolder_manager=None, queries_manager=None, scripts_manager=None, jobs_manager=None,
                   database_manager=None, resources_manager=None, workspace_manager=None,
                   image_library_manager=None, icon_sidebar=None):
        """
        Set the frame and manager widgets after they're created.
        This allows frames and managers to be created separately and injected.

        Args:
            settings_frame: SettingsFrame instance
            help_frame: HelpFrame instance
            rootfolder_manager: RootFolderManager instance (optional)
            queries_manager: QueriesManager instance (optional)
            scripts_manager: ScriptsManager instance (optional)
            jobs_manager: JobsManager instance (optional)
            database_manager: DatabaseManager instance (optional)
            resources_manager: ResourcesManager instance (optional)
            workspace_manager: WorkspaceManager instance (optional)
            image_library_manager: ImageLibraryManager instance (optional)
            icon_sidebar: IconSidebar instance for left panel navigation (optional)
        """
        self.settings_frame = settings_frame
        self.help_frame = help_frame
        self.rootfolder_manager = rootfolder_manager
        self.queries_manager = queries_manager
        self.scripts_manager = scripts_manager
        self.jobs_manager = jobs_manager
        self.database_manager = database_manager
        self.resources_manager = resources_manager
        self.workspace_manager = workspace_manager
        self.image_library_manager = image_library_manager
        self.icon_sidebar = icon_sidebar

        # Connect signals from settings frame
        if self.settings_frame:
            self.settings_frame.debug_borders_changed.connect(self._on_debug_borders_changed)
            self.settings_frame.theme_changed.connect(self._on_theme_changed)

        # Connect icon sidebar selection to switch managers
        if self.icon_sidebar:
            self.icon_sidebar.manager_selected.connect(self._on_manager_selected)
            self.icon_sidebar.open_image_library_requested.connect(
                lambda: self._switch_frame("images")
            )

        # Connect signal from resources manager to open in dedicated manager
        if self.resources_manager:
            self.resources_manager.open_resource_requested.connect(self._on_open_resource)
            self.resources_manager.open_image_library_requested.connect(
                lambda: self._switch_frame("images")
            )

        # Connect database_manager.query_saved to refresh queries in resources_manager
        if self.database_manager and self.resources_manager:
            self.database_manager.query_saved.connect(self.resources_manager.refresh_queries)

        # Clear stacked widget and add all views
        while self.stacked_widget.count() > 0:
            widget = self.stacked_widget.widget(0)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()

        # Add frames
        self.stacked_widget.addWidget(self.settings_frame)
        self.stacked_widget.addWidget(self.help_frame)

        # Add managers if provided
        if self.rootfolder_manager:
            self.stacked_widget.addWidget(self.rootfolder_manager)
        if self.database_manager:
            self.stacked_widget.addWidget(self.database_manager)
        if self.queries_manager:
            self.stacked_widget.addWidget(self.queries_manager)
        if self.scripts_manager:
            self.stacked_widget.addWidget(self.scripts_manager)
        if self.jobs_manager:
            self.stacked_widget.addWidget(self.jobs_manager)
        if self.workspace_manager:
            self.stacked_widget.addWidget(self.workspace_manager)
        if self.image_library_manager:
            self.stacked_widget.addWidget(self.image_library_manager)
        if self.resources_manager:
            self.stacked_widget.addWidget(self.resources_manager)

        # Set icon_sidebar in left panel - always visible for resource navigation
        if self.icon_sidebar:
            self.window.set_left_panel_widget(self.icon_sidebar)
            self.window.left_panel.show()

        # Initially show database manager
        if self.database_manager:
            self.stacked_widget.setCurrentWidget(self.database_manager)
            self._current_view = "database"
            self._update_active_menu("view")

    def _setup_status_bar(self):
        """Setup status bar."""
        self.window.status_bar.set_message(tr("status_ready"))

    def _connect_signals(self):
        """Connect signals and slots."""
        # Connect i18n language change to UI update
        self.i18n_bridge.register_observer(self._on_language_changed)

        # Connect queries manager execution signal
        if self.queries_manager:
            self.queries_manager.query_execute_requested.connect(self._on_execute_saved_query)

    def _switch_frame(self, frame_name: str):
        """
        Switch to a different frame or manager.

        Args:
            frame_name: Name of the frame/manager to switch to
        """
        # "resources" now means show the database manager (icon sidebar always visible)
        if frame_name == "resources":
            frame_name = "database"

        frame_map = {
            "rootfolders": (self.rootfolder_manager, "status_viewing_rootfolders"),
            "options": (self.settings_frame, "status_viewing_settings"),
            "settings": (self.settings_frame, "status_viewing_settings"),  # Alias for backward compatibility
            "help": (self.help_frame, "status_viewing_help"),
            "database": (self.database_manager, "status_viewing_database"),
            "queries": (self.queries_manager, "status_viewing_queries"),
            "scripts": (self.scripts_manager, "status_viewing_scripts"),
            "jobs": (self.jobs_manager, "status_viewing_jobs"),
            "workspaces": (self.workspace_manager, "status_viewing_workspaces"),
            "images": (self.image_library_manager, "status_viewing_images")
        }

        if frame_name in frame_map:
            frame, status_key = frame_map[frame_name]
            if frame is not None:
                self.stacked_widget.setCurrentWidget(frame)
                self.window.status_bar.set_message(tr(status_key))
                self._current_view = frame_name
                self._update_active_menu(frame_name)

                # Show/hide icon sidebar based on context
                resource_views = ["database", "rootfolders", "queries", "jobs", "scripts", "images"]
                if frame_name in resource_views:
                    # Show sidebar and sync selection
                    if self.icon_sidebar:
                        self.window.left_panel.show()
                        self.icon_sidebar.update_selection(frame_name)
                else:
                    # Hide sidebar for non-resource contexts (Settings, Help, Workspaces)
                    self.window.left_panel.hide()
            else:
                # Manager not yet initialized
                self.window.status_bar.set_message(tr("status_ready"))

    def _update_active_menu(self, frame_name: str):
        """
        Update which menu button is shown as active/selected.

        Args:
            frame_name: Name of the current frame/manager
        """
        # Map frame names to menu button names
        frame_to_menu = {
            "resources": "view",
            "rootfolders": "view",
            "database": "view",
            "queries": "view",
            "scripts": "view",
            "jobs": "view",
            "images": "view",
            "workspaces": "workspaces",
            "options": "options",
            "settings": "options",
            "help": "help",
        }

        menu_name = frame_to_menu.get(frame_name, "view")

        # Apply selected style to the correct menu button
        colors = self.theme_bridge.get_theme_colors()
        self.window.menu_bar.set_active_menu(menu_name, {
            "selected_bg": colors.get("feature_menu_bar_selected_bg", "#4d4d4d"),
            "selected_fg": colors.get("feature_menu_bar_selected_fg", "#ffffff")
        })

    def _show_theme_dialog(self):
        """Show theme selection dialog."""
        # TODO: Implement theme dialog
        # For now, just switch to settings
        self._switch_frame("settings")

    def _show_about(self):
        """Show about dialog."""
        from ..widgets.about_dialog import AboutDialog
        about_dialog = AboutDialog(parent=self.window)
        about_dialog.show()

    def _check_updates(self):
        """Check for updates from GitHub."""
        from ...utils.update_checker import get_update_checker
        from PySide6.QtWidgets import QMessageBox, QPushButton
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        checker = get_update_checker()
        result = checker.check_for_update()

        if result:
            version, url, notes = result
            # Update available
            msg = QMessageBox(self.window)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle(tr("update_available_title"))
            msg.setText(tr("update_available_text").format(version=version))

            # Truncate notes if too long
            if len(notes) > 500:
                notes = notes[:500] + "..."
            msg.setDetailedText(notes)

            # Add custom buttons
            btn_update_quit = msg.addButton(tr("update_on_quit"), QMessageBox.ButtonRole.AcceptRole)
            btn_open = msg.addButton(tr("open_github"), QMessageBox.ButtonRole.ActionRole)
            btn_later = msg.addButton(tr("remind_later"), QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            clicked = msg.clickedButton()
            if clicked == btn_update_quit:
                self._pending_update = True
                self.window.status_bar.set_message(tr("status_update_on_quit"))
            elif clicked == btn_open:
                QDesktopServices.openUrl(QUrl(url))
            else:
                checker.dismiss_update()
        else:
            # No update or error
            msg = QMessageBox(self.window)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle(tr("update_check_title"))
            msg.setText(tr("no_update_available"))
            msg.exec()

    @Slot(str, str)
    def _on_open_resource(self, resource_type: str, resource_id: str):
        """
        Handle request to open a resource in its dedicated manager.

        Args:
            resource_type: Type of resource (database, query, rootfolder, job, script)
            resource_id: ID of the resource (UUID string)
        """
        # Map resource types to frame names and managers
        type_to_frame = {
            "database": ("database", self.database_manager),
            "query": ("queries", self.queries_manager),
            "rootfolder": ("rootfolders", self.rootfolder_manager),
            "job": ("jobs", self.jobs_manager),
            "script": ("scripts", self.scripts_manager),
        }

        if resource_type in type_to_frame:
            frame_name, manager = type_to_frame[resource_type]
            if manager:
                self._switch_frame(frame_name)
                # TODO: Select the specific resource in the manager if supported

    @Slot(str)
    def _on_manager_selected(self, manager_id: str):
        """
        Handle icon sidebar selection - switch to the selected manager.

        Args:
            manager_id: ID of the selected manager (database, rootfolders, queries, jobs, scripts, images)
        """
        self._switch_frame(manager_id)

    @Slot()
    def _on_language_changed(self):
        """Handle language change - update all UI text."""
        # Recreate menu bar with new language
        # Note: This is a simplified approach, a more elegant solution
        # would be to update only the text without recreating
        self._setup_menu_bar()

    def _add_debug_borders(self):
        """Add colored borders to all zones for debugging layout (preserves theme colors)."""
        # Get current theme colors
        colors = self.theme_bridge.get_theme_colors()
        window_bg = colors.get('window_bg', '#1e1e1e')
        panel_bg = colors.get('panel_bg', '#252525')

        # Window template zones - only add borders, preserve backgrounds
        self.window.title_bar.setStyleSheet(f"background-color: {colors.get('main_menu_bar_bg', panel_bg)}; border: 2px solid purple;")
        self.window.menu_bar.setStyleSheet(f"background-color: {colors.get('feature_menu_bar_bg', panel_bg)}; border: 2px solid magenta;")
        self.window.left_panel.setStyleSheet(f"background-color: {panel_bg}; border: 2px solid brown;")
        self.window.right_container.setStyleSheet(f"background-color: {panel_bg}; border: 2px solid pink;")
        self.window.main_container.setStyleSheet(f"background-color: {panel_bg}; border: 2px solid navy;")
        self.window.status_bar.setStyleSheet(f"background-color: {colors.get('status_bar_bg', panel_bg)}; border: 2px solid lime;")

        # Central widget - preserve theme background
        central = self.window.centralWidget()
        if central:
            central.setStyleSheet(f"background-color: {window_bg}; border: 2px solid white;")

        # Stacked widget (contains frames)
        self.stacked_widget.setStyleSheet("border: 3px solid cyan;")

        # Apply borders to all widgets in stacked widget
        for i in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(i)
            if widget:
                self._apply_debug_borders_recursive(widget)

    def _apply_debug_borders_recursive(self, widget):
        """
        Apply debug borders recursively to a widget and its children.

        Args:
            widget: Widget to apply borders to
        """
        from PySide6.QtWidgets import QWidget, QGroupBox, QFrame

        # Skip if already has explicit stylesheet (to avoid overriding existing styles)
        current_style = widget.styleSheet()

        # Add border to the widget
        if isinstance(widget, (QGroupBox, QFrame)):
            # For containers, use a distinct color
            widget.setStyleSheet(current_style + " QWidget { border: 1px solid orange; }")
        else:
            widget.setStyleSheet(current_style + " QWidget { border: 1px solid yellow; }")

        # Apply to all children
        for child in widget.findChildren(QWidget):
            if child.parent() == widget:  # Only direct children to avoid too deep recursion
                self._apply_debug_borders_recursive(child)

    def _remove_debug_borders(self):
        """Remove all debug borders by reapplying the current theme."""
        from PySide6.QtWidgets import QApplication

        # Clear styles from stacked widget and its children first
        self.stacked_widget.setStyleSheet("")
        for i in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(i)
            if widget:
                self._remove_debug_borders_recursive(widget)

        # Reapply global QSS FIRST (base styles for all widgets)
        app = QApplication.instance()
        if app and self.theme_bridge:
            global_qss = self.theme_bridge.generate_global_qss(self.theme_bridge.current_theme)
            app.setStyleSheet(global_qss)

        # Then apply theme to window-template components (overrides global for specific widgets)
        self.theme_bridge.apply_theme(self.window, self.theme_bridge.current_theme)

    def _remove_debug_borders_recursive(self, widget):
        """
        Remove debug borders recursively from a widget and its children.

        Args:
            widget: Widget to remove borders from
        """
        from PySide6.QtWidgets import QWidget

        # Reset stylesheet (this removes the border we added)
        widget.setStyleSheet("")

        # Remove from all children
        for child in widget.findChildren(QWidget):
            if child.parent() == widget:  # Only direct children
                self._remove_debug_borders_recursive(child)

    @Slot(bool)
    def _on_debug_borders_changed(self, enabled: bool):
        """
        Handle debug borders setting change.

        Args:
            enabled: Whether debug borders should be shown
        """
        if enabled:
            self._add_debug_borders()
        else:
            self._remove_debug_borders()

    @Slot(str)
    def _on_theme_changed(self, theme_id: str):
        """
        Handle theme change - apply theme to window-template components.

        Args:
            theme_id: Theme identifier (e.g., "minimal_dark", "minimal_light")
        """
        # Apply theme to window-template components (title bar, menu bar, status bar, panels)
        self.theme_bridge.apply_theme(self.window, theme_id)

        # Reapply active menu style with new theme colors
        if self._current_view:
            self._update_active_menu(self._current_view)

    # ==================== Window Control ====================

    def show(self):
        """Show the window."""
        self.wrapper.show()

    def close(self):
        """Close the window."""
        self.window.close()

    def _on_close_event(self, event):
        """
        Handle window close event - cleanup all resources before closing.
        This ensures background threads are stopped properly.
        """
        import threading

        # Run cleanup in background to not block the close event
        def async_cleanup():
            # Cleanup database manager (has query tabs with background loaders)
            if self.database_manager:
                try:
                    self.database_manager.cleanup()
                except Exception:
                    pass

            # Cleanup other managers if they have cleanup methods
            for manager in [self.queries_manager, self.scripts_manager,
                            self.jobs_manager, self.resources_manager]:
                if manager and hasattr(manager, 'cleanup'):
                    try:
                        manager.cleanup()
                    except Exception:
                        pass

        # Start cleanup in daemon thread (won't block app exit)
        cleanup_thread = threading.Thread(target=async_cleanup, daemon=True)
        cleanup_thread.start()

        # Run update if pending
        if self._pending_update:
            self._run_update_on_quit()

        # Call original close event immediately - don't wait for cleanup
        if self._original_close_event:
            self._original_close_event(event)

    def _run_update_on_quit(self):
        """Run update commands in a new terminal window."""
        import subprocess
        import sys
        from pathlib import Path

        # Get project root directory
        project_root = Path(__file__).parent.parent.parent.parent.parent
        project_root_str = str(project_root).replace('\\', '/')

        # Git safe.directory command (fixes "dubious ownership" error on Windows)
        safe_dir_cmd = f'git config --global --add safe.directory "{project_root_str}"'

        # Git update commands: stash local changes if any, checkout main, pull, then drop stash if exists
        git_update_cmd = 'git stash || true && git checkout main && git pull origin main && (git stash drop 2>nul || true)'

        # Build update commands
        if sys.platform == 'win32':
            # Windows: open new cmd window with update commands
            cmd = f'start cmd /k "cd /d {project_root} && echo Updating DataForge Studio... && {safe_dir_cmd} && {git_update_cmd} && uv sync && echo. && echo Update complete! Press any key to close. && pause"'
            subprocess.Popen(cmd, shell=True)
        elif sys.platform == 'darwin':
            # macOS: open new Terminal window
            script = f'''
            tell application "Terminal"
                do script "cd '{project_root}' && echo 'Updating DataForge Studio...' && {safe_dir_cmd} && {git_update_cmd} && uv sync && echo '' && echo 'Update complete!'"
                activate
            end tell
            '''
            subprocess.Popen(['osascript', '-e', script])
        else:
            # Linux: try common terminal emulators
            commands = f"cd '{project_root}' && echo 'Updating DataForge Studio...' && {safe_dir_cmd} && {git_update_cmd} && uv sync && echo '' && echo 'Update complete! Press Enter to close.' && read"
            terminals = [
                ['gnome-terminal', '--', 'bash', '-c', commands],
                ['xterm', '-e', f'bash -c "{commands}"'],
                ['konsole', '-e', f'bash -c "{commands}"'],
            ]
            for term_cmd in terminals:
                try:
                    subprocess.Popen(term_cmd)
                    break
                except FileNotFoundError:
                    continue

    def _on_execute_saved_query(self, saved_query):
        """
        Handle saved query execution request from QueriesManager.
        Opens the query in DatabaseManager and executes it.
        """
        from ..managers.query_tab import QueryTab
        from ..widgets.dialog_helper import DialogHelper

        if not self.database_manager:
            DialogHelper.warning(
                "Database Manager not available.\nLe gestionnaire de bases de données n'est pas disponible.",
                parent=self.window
            )
            return

        # Get the target database connection
        db_id = saved_query.target_database_id
        if not db_id:
            DialogHelper.warning(
                "No target database specified for this query.\nAucune base de données cible n'est spécifiée pour cette requête.",
                parent=self.window
            )
            return

        # Check if database is connected, if not try to connect
        connection = self.database_manager.connections.get(db_id)
        db_conn = self.database_manager._get_connection_by_id(db_id)

        if not db_conn:
            DialogHelper.warning(
                "Target database not found in connections.\nBase de données cible non trouvée dans les connexions.",
                parent=self.window
            )
            return

        if not connection:
            # Try to connect
            try:
                connection = self.database_manager.reconnect_database(db_id)
                if not connection:
                    DialogHelper.error(
                        f"Failed to connect to {db_conn.name}.\nÉchec de la connexion à {db_conn.name}.",
                        parent=self.window
                    )
                    return
            except Exception as e:
                DialogHelper.error(f"Connection error: {e}", parent=self.window)
                return

        # Switch to database manager view
        self._switch_frame("database")

        # Create a new query tab named after the saved query
        tab_name = saved_query.name

        query_tab = QueryTab(
            parent=self.database_manager,
            connection=connection,
            db_connection=db_conn,
            tab_name=tab_name,
            database_manager=self.database_manager
        )

        # Connect query_saved signal
        query_tab.query_saved.connect(self.database_manager.query_saved.emit)

        # Add to tab widget
        index = self.database_manager.tab_widget.addTab(query_tab, tab_name)
        self.database_manager.tab_widget.setCurrentIndex(index)

        # Set query text and execute
        query_tab.set_query_text(saved_query.query_text or "")
        query_tab._execute_as_query()

        import logging
        logging.getLogger(__name__).info(f"Executed saved query: {saved_query.name}")
