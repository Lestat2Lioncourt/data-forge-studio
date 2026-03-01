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
        self.ftproot_manager = None
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
        self._last_resource_view = "database"  # Track last resource view for "Resources" menu
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

        # Tools menu
        from pathlib import Path
        tools_items = [
            (tr("menu_create_shortcut"), self._create_desktop_shortcut),
        ]
        # Dev-only: generate offline package
        packages_dir = Path(__file__).parent.parent.parent.parent.parent / "_packages"
        if packages_dir.exists():
            tools_items.append((None, None))  # separator
            tools_items.append((tr("menu_generate_package"), self._generate_offline_package))
        menu_bar.add_menu_with_submenu("tools", tr("menu_tools"), tools_items)

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
                   rootfolder_manager=None, ftproot_manager=None, queries_manager=None,
                   scripts_manager=None, jobs_manager=None,
                   database_manager=None, resources_manager=None, workspace_manager=None,
                   image_library_manager=None, icon_sidebar=None):
        """
        Set the frame and manager widgets after they're created.
        This allows frames and managers to be created separately and injected.

        Args:
            settings_frame: SettingsFrame instance
            help_frame: HelpFrame instance
            rootfolder_manager: RootFolderManager instance (optional)
            ftproot_manager: FTPRootManager instance (optional)
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
        self.ftproot_manager = ftproot_manager
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

        # Connect queries manager execution signal to open query in DatabaseManager
        if self.queries_manager:
            self.queries_manager.query_execute_requested.connect(self._on_execute_saved_query)

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
        if self.ftproot_manager:
            self.stacked_widget.addWidget(self.ftproot_manager)
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

        # Determine initial view: workspaces if favorite exists, otherwise database
        initial_view = self._get_initial_view()
        if initial_view == "workspaces" and self.workspace_manager:
            self.stacked_widget.setCurrentWidget(self.workspace_manager)
            self._current_view = "workspaces"
            self._update_active_menu("workspaces")
            # Hide icon sidebar for workspaces view
            self.window.left_panel.hide()
        elif self.database_manager:
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

        # Note: queries_manager signal is connected in set_frames() since
        # queries_manager is None at this point during __init__

    def _disconnect_signals(self):
        """Disconnect signals to prevent memory leaks on close."""
        try:
            # Unregister i18n observer
            self.i18n_bridge.unregister_observer(self._on_language_changed)
        except Exception:
            pass

        # Disconnect settings frame signals
        if self.settings_frame:
            try:
                self.settings_frame.debug_borders_changed.disconnect(self._on_debug_borders_changed)
                self.settings_frame.theme_changed.disconnect(self._on_theme_changed)
            except Exception:
                pass

        # Disconnect icon sidebar signals
        if self.icon_sidebar:
            try:
                self.icon_sidebar.manager_selected.disconnect(self._on_manager_selected)
                self.icon_sidebar.open_image_library_requested.disconnect()
            except Exception:
                pass

        # Disconnect resources manager signals
        if self.resources_manager:
            try:
                self.resources_manager.open_resource_requested.disconnect(self._on_open_resource)
                self.resources_manager.open_image_library_requested.disconnect()
            except Exception:
                pass

        # Disconnect database manager signals
        if self.database_manager and self.resources_manager:
            try:
                self.database_manager.query_saved.disconnect(self.resources_manager.refresh_queries)
            except Exception:
                pass

        # Disconnect queries manager signals
        if self.queries_manager:
            try:
                self.queries_manager.query_execute_requested.disconnect(self._on_execute_saved_query)
            except Exception:
                pass

    def _switch_frame(self, frame_name: str):
        """
        Switch to a different frame or manager.

        Args:
            frame_name: Name of the frame/manager to switch to
        """
        # "resources" means restore the last resource view (or default to database)
        if frame_name == "resources":
            frame_name = self._last_resource_view or "database"

        frame_map = {
            "rootfolders": (self.rootfolder_manager, "status_viewing_rootfolders"),
            "ftproots": (self.ftproot_manager, "status_viewing_ftproots"),
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
                resource_views = ["database", "rootfolders", "ftproots", "queries", "jobs", "scripts", "images"]
                if frame_name in resource_views:
                    # Remember last resource view for "Resources" menu
                    self._last_resource_view = frame_name
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

    def _check_updates(self, cached_result=None, silent=False):
        """Check for updates from GitHub.

        Args:
            cached_result: Optional pre-fetched (version, url, notes) tuple to avoid a second API call.
            silent: If True, don't show "no update available" dialog (used for startup check).
        """
        from ...utils.update_checker import get_update_checker
        from PySide6.QtWidgets import QMessageBox, QPushButton
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        checker = get_update_checker()
        result = cached_result or checker.check_for_update()

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
        elif not silent:
            # No update or error (only show when manually triggered)
            msg = QMessageBox(self.window)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle(tr("update_check_title"))
            msg.setText(tr("no_update_available"))
            msg.exec()

    def _create_desktop_shortcut(self):
        """Create a desktop shortcut to launch the application."""
        import sys
        from pathlib import Path
        from ..widgets.dialog_helper import DialogHelper

        project_root = Path(__file__).parent.parent.parent.parent.parent
        ico_icon = project_root / "src" / "dataforge_studio" / "ui" / "assets" / "images" / "DataForge-Studio-logo.ico"
        png_icon = project_root / "src" / "dataforge_studio" / "ui" / "assets" / "images" / "DataForge-Studio-logo.png"
        run_script = project_root / "run.py"

        if sys.platform == "win32":
            try:
                import win32com.client

                # Find desktop
                try:
                    shell = win32com.client.Dispatch("WScript.Shell")
                    desktop = Path(shell.SpecialFolders("Desktop"))
                except Exception:
                    desktop = Path.home() / "Desktop"
                    if not desktop.exists():
                        desktop = Path.home() / "Bureau"

                if not desktop.exists():
                    DialogHelper.error(tr("shortcut_desktop_not_found"), parent=self.window)
                    return

                # Find pythonw.exe (no console window)
                venv_pythonw = project_root / ".venv" / "Scripts" / "pythonw.exe"
                if not venv_pythonw.exists():
                    DialogHelper.error(tr("shortcut_pythonw_not_found"), parent=self.window)
                    return

                # Determine icon
                icon_to_use = ico_icon if ico_icon.exists() else (png_icon if png_icon.exists() else None)

                # Create shortcut
                shortcut_path = desktop / "DataForge Studio.lnk"
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(shortcut_path))
                shortcut.TargetPath = str(venv_pythonw)
                shortcut.Arguments = f'"{run_script}"'
                shortcut.WorkingDirectory = str(project_root)
                shortcut.Description = "DataForge Studio"
                if icon_to_use:
                    shortcut.IconLocation = str(icon_to_use)
                shortcut.save()

                DialogHelper.info(tr("shortcut_created"), parent=self.window)

            except ImportError:
                DialogHelper.error(tr("shortcut_pywin32_required"), parent=self.window)
            except Exception as e:
                DialogHelper.error(f"{tr('shortcut_error')}\n{e}", parent=self.window)

        elif sys.platform == "darwin":
            # macOS: create .command file on desktop
            try:
                desktop = Path.home() / "Desktop"
                command_file = desktop / "DataForge Studio.command"
                venv_python = project_root / ".venv" / "bin" / "python"
                command_file.write_text(f'#!/bin/bash\ncd "{project_root}"\n"{venv_python}" "{run_script}"\n')
                command_file.chmod(0o755)
                DialogHelper.info(tr("shortcut_created"), parent=self.window)
            except Exception as e:
                DialogHelper.error(f"{tr('shortcut_error')}\n{e}", parent=self.window)

        else:
            # Linux: create .desktop file
            try:
                desktop = Path.home() / "Desktop"
                desktop.mkdir(exist_ok=True)
                venv_python = project_root / ".venv" / "bin" / "python"
                icon = png_icon if png_icon.exists() else ""
                desktop_file = desktop / "dataforge-studio.desktop"
                desktop_file.write_text(
                    f"[Desktop Entry]\nType=Application\nName=DataForge Studio\n"
                    f"Exec={venv_python} {run_script}\nPath={project_root}\n"
                    f"Icon={icon}\nTerminal=false\n"
                )
                desktop_file.chmod(0o755)
                DialogHelper.info(tr("shortcut_created"), parent=self.window)
            except Exception as e:
                DialogHelper.error(f"{tr('shortcut_error')}\n{e}", parent=self.window)

    def _generate_offline_package(self):
        """Launch the offline package generation script in a progress dialog."""
        from pathlib import Path
        from ... import __version__
        from ..widgets.dialog_helper import DialogHelper
        from ..dialogs.package_progress_dialog import PackageProgressDialog

        # Resolve project root: main_window.py is in ui/core/, go up to project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        script_path = project_root / "_packages" / "prepare_package.bat"

        if not script_path.exists():
            DialogHelper.error(
                tr("pkg_script_not_found").format(path=str(script_path)),
                parent=self.window
            )
            return

        # Check if an archive for the current version already exists
        packages_dir = project_root / "_packages"
        current_archive = packages_dir / f"DataForgeStudio_v{__version__}.7z"
        if current_archive.exists():
            if not DialogHelper.confirm(
                tr("pkg_archive_exists").format(
                    name=current_archive.name
                ),
                parent=self.window
            ):
                return

        # Non-modal: user can keep using the app while package is building
        self._package_dialog = PackageProgressDialog(script_path, parent=self.window)
        self._package_dialog.show()

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

    def _get_initial_view(self) -> str:
        """
        Determine the initial view to show on startup.
        Returns 'workspaces' if a favorite workspace exists, otherwise 'database'.
        """
        try:
            from ...database.config_db import get_config_db
            config_db = get_config_db()
            workspace = config_db.get_auto_connect_workspace()
            if workspace:
                return "workspaces"
        except Exception:
            # Migration may not have run yet, or column doesn't exist
            pass
        return "database"

    def show(self):
        """Show the window."""
        self.wrapper.show()

        # Auto-connect workspace connections after window is shown
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self._auto_connect_startup)

    def _auto_connect_startup(self):
        """
        Auto-connect databases and FTP for the workspace with auto_connect enabled.
        This runs silently (no success popups, errors logged to status bar).
        """
        from ...database.config_db import get_config_db
        import logging

        logger = logging.getLogger(__name__)

        try:
            config_db = get_config_db()

            # Get workspace with auto_connect enabled
            workspace = config_db.get_auto_connect_workspace()
            if not workspace:
                return
        except Exception as e:
            # Migration may not have run yet, or column doesn't exist
            logger.debug(f"Auto-connect check skipped: {e}")
            return

        logger.info(f"Auto-connecting workspace: {workspace.name}")

        # Get databases and FTP roots for this workspace
        databases = config_db.get_workspace_databases(workspace.id)
        ftp_roots = config_db.get_workspace_ftp_roots(workspace.id)

        total_connections = len(databases) + len(ftp_roots)
        if total_connections == 0:
            self._show_status_message(f"⚡ {workspace.name}: aucune connexion à établir")
            return

        self._show_status_message(
            f"⚡ Auto-connexion {workspace.name}: 0/{total_connections}...", timeout=0
        )

        # Connect databases
        db_count = 0
        for i, db in enumerate(databases):
            if self.database_manager:
                try:
                    self._show_status_message(
                        f"⚡ Connexion DB {i+1}/{len(databases)}: {db.name}...", timeout=0
                    )
                    self.database_manager.connect_database_silent(db)
                    db_count += 1
                except Exception as e:
                    logger.warning(f"Auto-connect DB failed for {db.name}: {e}")

        # Connect FTP roots
        ftp_count = 0
        for i, ftp in enumerate(ftp_roots):
            if self.ftproot_manager:
                try:
                    self._show_status_message(
                        f"⚡ Connexion FTP {i+1}/{len(ftp_roots)}: {ftp.name}...", timeout=0
                    )
                    self.ftproot_manager.connect_ftp_root_silent(ftp)
                    ftp_count += 1
                except Exception as e:
                    logger.warning(f"Auto-connect FTP failed for {ftp.name}: {e}")

        # Final status
        self._show_status_message(
            f"✓ Auto-connexion terminée: {db_count} DB, {ftp_count} FTP"
        )

    def _show_status_message(self, message: str, timeout: int = 5000):
        """Show message in status bar."""
        if hasattr(self.window, 'statusBar'):
            self.window.statusBar().showMessage(message, timeout)

    def close(self):
        """Close the window."""
        self.window.close()

    def _on_close_event(self, event):
        """
        Handle window close event - cleanup all resources before closing.
        This ensures background threads are stopped properly.
        """
        import threading

        # Disconnect signals first to prevent callbacks during cleanup
        self._disconnect_signals()

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
                            self.jobs_manager, self.resources_manager,
                            self.workspace_manager, self.image_library_manager,
                            self.settings_frame]:
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

        # Build update commands per platform
        if sys.platform == 'win32':
            # Windows: use a .bat script to avoid nested quote issues in cmd /k
            bat_path = project_root / '_update.bat'
            bat_content = f'''@echo off
cd /d "{project_root}"
echo Updating DataForge Studio...
echo.
git config --global --add safe.directory "{str(project_root).replace(chr(92), '/')}"
git reset --hard
git checkout main
git pull origin main
if errorlevel 1 goto :failed
uv sync
if errorlevel 1 goto :failed
echo.
echo Update complete! Press any key to close.
pause
del "%~f0"
exit /b 0

:failed
echo.
echo ============================================
echo   UPDATE FAILED - Manual commands:
echo ============================================
echo.
echo   git reset --hard
echo   git pull origin main
echo   uv sync
echo.
echo ============================================
echo.
pause
del "%~f0"
'''
            bat_path.write_text(bat_content, encoding='utf-8')
            subprocess.Popen(f'start cmd /k "{bat_path}"', shell=True)

        elif sys.platform == 'darwin':
            # macOS: open new Terminal window
            project_root_str = str(project_root).replace('\\', '/')
            safe_dir_cmd = f'git config --global --add safe.directory "{project_root_str}"'
            git_update_cmd = 'git reset --hard && git checkout main && git pull origin main'
            fail_msg = "echo ''; echo '=== UPDATE FAILED - Manual commands: ==='; echo '  git reset --hard'; echo '  git pull origin main'; echo '  uv sync'; echo '========================================'"
            script = f'''
            tell application "Terminal"
                do script "cd '{project_root}' && echo 'Updating DataForge Studio...' && {safe_dir_cmd} && {git_update_cmd} && uv sync && echo '' && echo 'Update complete!' || ( {fail_msg} )"
                activate
            end tell
            '''
            subprocess.Popen(['osascript', '-e', script])

        else:
            # Linux: try common terminal emulators
            project_root_str = str(project_root).replace('\\', '/')
            safe_dir_cmd = f'git config --global --add safe.directory "{project_root_str}"'
            git_update_cmd = 'git reset --hard && git checkout main && git pull origin main'
            fail_msg = "echo ''; echo '=== UPDATE FAILED - Manual commands: ==='; echo '  git reset --hard'; echo '  git pull origin main'; echo '  uv sync'; echo '========================================'"
            commands = f"cd '{project_root}' && echo 'Updating DataForge Studio...' && {safe_dir_cmd} && {git_update_cmd} && uv sync && echo '' && echo 'Update complete! Press Enter to close.' && read || ( {fail_msg} && read )"
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
        from ..widgets.dialog_helper import DialogHelper

        if not self.database_manager:
            DialogHelper.warning(
                "Database Manager not available.",
                parent=self.window
            )
            return

        # Switch to database manager view
        self._switch_frame("database")

        # Delegate to DatabaseManager's execute_saved_query method
        self.database_manager.execute_saved_query(saved_query)
