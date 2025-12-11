"""
Preferences Dialog - User settings window
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from ..config.theme_manager import get_theme_manager
from ..config.user_preferences import get_preferences
from ..config.i18n import get_i18n
from .theme_editor_dialog import ThemeEditorDialog

logger = logging.getLogger(__name__)


class PreferencesDialog(tk.Toplevel):
    """
    Preferences dialog window

    Allows users to:
    - Select visual theme
    - Choose interface language
    """

    def __init__(self, parent):
        """
        Initialize preferences dialog

        Args:
            parent: Parent window
        """
        super().__init__(parent)

        self.theme_manager = get_theme_manager()
        self.preferences = get_preferences()
        self.i18n = get_i18n()

        # Store original values for cancel
        self.original_theme = self.preferences.get_theme()
        self.original_language = self.preferences.get_language()

        # Normalize theme name: convert display name to theme ID if needed
        available_themes = self.theme_manager.get_available_themes()
        normalized_theme = self.original_theme

        # If the stored theme is not in the theme IDs, try to find it by display name
        if normalized_theme not in available_themes:
            for theme_id, display_name in available_themes.items():
                if display_name == normalized_theme:
                    normalized_theme = theme_id
                    # Update the preference to use the correct ID
                    self.preferences.set_theme(theme_id)
                    break

        # If still not found, use default
        if normalized_theme not in available_themes:
            normalized_theme = 'classic_light'
            self.preferences.set_theme(normalized_theme)

        self.original_theme = normalized_theme

        # Variables for form
        self.theme_var = tk.StringVar(value=normalized_theme)
        self.language_var = tk.StringVar(value=self.original_language)

        self._create_ui()
        self._center_window()
        self._apply_theme()

        logger.info("Preferences dialog opened")

    def _create_ui(self):
        """Create the dialog UI"""
        self.title(self.i18n.t('pref_title'))
        self.resizable(False, False)

        # Set explicit window size to prevent TTK style issues
        self.geometry("500x300")

        # Make dialog modal
        self.transient(self.master)
        self.grab_set()

        # Main container
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # ===== Appearance Tab =====
        appearance_frame = ttk.Frame(notebook, padding="15")
        notebook.add(appearance_frame, text=self.i18n.t('pref_appearance'))

        # Theme selection
        theme_label = ttk.Label(appearance_frame, text=self.i18n.t('pref_theme'))
        theme_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        theme_combo = ttk.Combobox(
            appearance_frame,
            textvariable=self.theme_var,
            state='readonly',
            width=25
        )
        # Get theme names with localized display names
        theme_names = self.theme_manager.get_available_themes()
        theme_combo['values'] = list(theme_names.keys())

        # Create a mapping for display
        self.theme_display = {}
        for theme_id, theme_name in theme_names.items():
            # Try to get localized theme name
            localized_key = f'theme_{theme_id}'
            display_name = self.i18n.t(localized_key)
            if display_name == localized_key:  # No translation found
                display_name = theme_name
            self.theme_display[theme_id] = display_name

        # Show localized names in combo
        theme_combo['values'] = [self.theme_display[t] for t in theme_names.keys()]
        theme_combo.set(self.theme_display[self.theme_var.get()])

        theme_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # Bind theme change to immediate preview
        theme_combo.bind('<<ComboboxSelected>>', self._on_theme_preview)

        # Theme preview hint
        theme_hint = ttk.Label(
            appearance_frame,
            text="Preview updates immediately",
            font=("Arial", 8),
            foreground="gray"
        )
        theme_hint.grid(row=1, column=1, sticky=tk.W, pady=(0, 10), padx=(10, 0))

        # Theme management buttons
        theme_buttons_frame = ttk.Frame(appearance_frame)
        theme_buttons_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 10))

        create_theme_btn = ttk.Button(
            theme_buttons_frame,
            text="Create New Theme",
            command=self._create_new_theme
        )
        create_theme_btn.pack(side=tk.LEFT, padx=(0, 5))

        edit_theme_btn = ttk.Button(
            theme_buttons_frame,
            text="Edit Theme",
            command=self._edit_theme
        )
        edit_theme_btn.pack(side=tk.LEFT)

        # ===== General Tab =====
        try:
            general_frame = ttk.Frame(notebook, padding="15")
            notebook.add(general_frame, text=self.i18n.t('pref_general'))

            # Language selection
            lang_label = ttk.Label(general_frame, text=self.i18n.t('pref_language'))
            lang_label.grid(row=0, column=0, sticky=tk.W, pady=5)

            lang_combo = ttk.Combobox(
                general_frame,
                state='readonly',
                width=25
            )

            # Get available languages
            languages = self.i18n.get_available_languages()
            logger.info(f"Available languages in preferences: {languages}")

            # Check if languages dict is empty
            if not languages:
                logger.error("No languages available!")
                languages = {'en': 'English', 'fr': 'Français'}  # Fallback

            # Create mapping for display (code -> "Name (code)")
            self.language_display = {}
            self.language_reverse = {}  # "Name (code)" -> code
            for lang_code, lang_name in languages.items():
                display = f"{lang_name} ({lang_code})"
                self.language_display[lang_code] = display
                self.language_reverse[display] = lang_code

            # Set combo values with display format
            lang_combo['values'] = [self.language_display[code] for code in sorted(languages.keys())]

            # Set current value
            current_lang_code = self.language_var.get()
            if current_lang_code in self.language_display:
                lang_combo.set(self.language_display[current_lang_code])
            else:
                logger.warning(f"Current language '{current_lang_code}' not in available languages, defaulting to 'en'")
                lang_combo.set(self.language_display.get('en', 'English (en)'))

            lang_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))

            # Bind language change
            lang_combo.bind('<<ComboboxSelected>>', self._on_language_preview)

            # Language hint
            lang_hint = ttk.Label(
                general_frame,
                text="Language changes apply immediately",
                font=("Arial", 8),
                foreground="gray"
            )
            lang_hint.grid(row=1, column=1, sticky=tk.W, pady=(0, 10), padx=(10, 0))

            # Store language combo for later reference
            self.lang_combo = lang_combo

            logger.info("General tab created successfully")
        except Exception as e:
            logger.error(f"Error creating General tab: {e}", exc_info=True)
            self.lang_combo = None  # Set to None if creation failed

        # Store theme combo for later reference
        self.theme_combo = theme_combo

        # ===== Button Frame =====
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # Reset button (left side)
        reset_btn = ttk.Button(
            button_frame,
            text=self.i18n.t('pref_reset'),
            command=self._reset_to_defaults
        )
        reset_btn.pack(side=tk.LEFT)

        # Right side buttons
        ok_btn = ttk.Button(
            button_frame,
            text=self.i18n.t('pref_ok'),
            command=self._on_ok,
            width=10
        )
        ok_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_btn = ttk.Button(
            button_frame,
            text=self.i18n.t('pref_cancel'),
            command=self._on_cancel,
            width=10
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Bind escape key to cancel
        self.bind('<Escape>', lambda e: self._on_cancel())

    def _center_window(self):
        """Center the dialog on the parent window"""
        self.update_idletasks()

        # Get parent window position and size
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        # Get dialog size
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"+{x}+{y}")

    def _apply_theme(self):
        """Apply current theme colors to dialog"""
        theme = self.theme_manager.get_current_theme()

        # Apply to dialog window
        try:
            self.configure(bg=theme.get('dialog_bg'))
        except Exception as e:
            pass  # Silently fail

    def _on_theme_preview(self, event=None):
        """Preview theme change immediately"""
        # Get selected theme from display name
        selected_display = self.theme_combo.get()

        # Find theme ID from display name
        selected_theme = None
        for theme_id, display_name in self.theme_display.items():
            if display_name == selected_display:
                selected_theme = theme_id
                break

        if selected_theme:
            self.theme_var.set(selected_theme)
            self.theme_manager.set_theme(selected_theme)
            logger.info(f"Theme preview: {selected_theme}")

    def _on_language_preview(self, event=None):
        """Preview language change immediately"""
        if not self.lang_combo:
            logger.warning("Language combo not available")
            return

        # Get language code from display format using reverse mapping
        selected_display = self.lang_combo.get()
        lang_code = self.language_reverse.get(selected_display)

        if lang_code:
            self.language_var.set(lang_code)
            self.i18n.set_language(lang_code)

            # Update dialog labels
            self._update_labels()

            logger.info(f"Language preview: {lang_code}")

    def _update_labels(self):
        """Update all labels with current language"""
        self.title(self.i18n.t('pref_title'))
        # Note: Full UI update would require rebuilding the dialog
        # For now, labels will update on next open

    def _reset_to_defaults(self):
        """Reset preferences to default values"""
        if messagebox.askyesno(
            self.i18n.t('warning'),
            "Reset all preferences to default values?"
        ):
            self.preferences.reset_to_defaults()

            # Apply defaults
            default_theme = self.preferences.get_theme()
            default_language = self.preferences.get_language()

            self.theme_manager.set_theme(default_theme)
            self.i18n.set_language(default_language)

            # Update UI
            self.theme_var.set(default_theme)
            self.language_var.set(default_language)

            self.theme_combo.set(self.theme_display[default_theme])
            if self.lang_combo:
                self.lang_combo.set(self.language_display.get(default_language, f'{default_language} ({default_language})'))

            logger.info("Preferences reset to defaults")
            messagebox.showinfo(
                self.i18n.t('info'),
                self.i18n.t('msg_preferences_saved')
            )

    def _on_ok(self):
        """Save preferences and close dialog"""
        # Save theme preference
        self.preferences.set_theme(self.theme_var.get())

        # Save language preference
        self.preferences.set_language(self.language_var.get())

        logger.info("Preferences saved")
        self.destroy()

    def _on_cancel(self):
        """Restore original settings and close dialog"""
        # Restore original theme
        if self.theme_var.get() != self.original_theme:
            self.theme_manager.set_theme(self.original_theme)
            logger.info(f"Theme restored to: {self.original_theme}")

        # Restore original language
        if self.language_var.get() != self.original_language:
            self.i18n.set_language(self.original_language)
            logger.info(f"Language restored to: {self.original_language}")

        self.destroy()

    def _create_new_theme(self):
        """Open theme editor to create a new theme"""
        logger.info("Opening theme editor to create new theme")
        dialog = ThemeEditorDialog(self, theme_name=None)
        self.wait_window(dialog)

        # Refresh theme list
        self._refresh_theme_list()

    def _edit_theme(self):
        """Open theme editor to edit current theme"""
        current_theme = self.theme_var.get()
        logger.info(f"Opening theme editor to edit theme: {current_theme}")
        dialog = ThemeEditorDialog(self, theme_name=current_theme)
        self.wait_window(dialog)

        # Refresh theme list
        self._refresh_theme_list()

    def _refresh_theme_list(self):
        """Refresh the theme combo box with updated theme list"""
        # Get updated theme names
        theme_names = self.theme_manager.get_available_themes()

        # Update theme display mapping
        self.theme_display = {}
        for theme_id, theme_name in theme_names.items():
            # Try to get localized theme name
            localized_key = f'theme_{theme_id}'
            display_name = self.i18n.t(localized_key)
            if display_name == localized_key:  # No translation found
                display_name = theme_name
            self.theme_display[theme_id] = display_name

        # Update combo values
        self.theme_combo['values'] = [self.theme_display[t] for t in theme_names.keys()]

        # Update current selection
        current_theme = self.theme_var.get()
        if current_theme in self.theme_display:
            self.theme_combo.set(self.theme_display[current_theme])

        logger.info("Theme list refreshed")
