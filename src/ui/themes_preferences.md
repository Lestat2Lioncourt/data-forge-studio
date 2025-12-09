# Themes & Preferences

## Overview

Customize the Data Lake Loader interface to match your preferences with multiple themes and language options.

## Accessing Preferences

**Open Preferences Dialog**:
- Menu: **Settings** → **Preferences**
- Keyboard: (No shortcut by default)

The Preferences window has two tabs:
- **Appearance**: Visual theme selection
- **General**: Language and other settings

## Themes

### Available Themes

**Classic Light** (Default):
- Clean white background
- Black text for maximum readability
- Blue accents for selection
- Professional and familiar look
- Best for well-lit environments

**Dark Professional**:
- Dark gray background (#2b2b2b)
- Light gray text (#d4d4d4)
- Cyan accents for highlights
- Reduces eye strain in low light
- Popular with developers

**Azure Blue**:
- Light blue-tinted panels
- Professional blue headers
- Calming color scheme
- Modern and vibrant look
- Less sterile than pure white

### Changing Themes

**Steps**:
1. Open **Settings** → **Preferences**
2. Go to **Appearance** tab
3. Select desired theme from dropdown
4. Theme applies **immediately** (preview mode)
5. Click **OK** to save or **Cancel** to revert

**Live Preview**:
- Theme changes appear instantly
- Test different themes before saving
- Cancel button restores original theme

### Theme Components

Each theme affects:
- **Backgrounds**: Main window, panels, frames
- **Text**: Foreground colors for readability
- **TreeViews**: File navigation, database schema
- **Data Grids**: Table headers, rows, selection
- **Buttons**: Toolbar and action buttons
- **Selection**: Highlighted items and active states

## Language Settings

### Supported Languages

**English (en)**:
- Default language
- Complete interface translation
- All menus, dialogs, and messages

**Français (fr)**:
- French translation
- Interface complète en français
- Tous les menus, dialogues et messages

### Changing Language

**Steps**:
1. Open **Settings** → **Preferences**
2. Go to **General** tab
3. Select language from dropdown:
   - English (en)
   - Français (fr)
4. Language applies **immediately**
5. Click **OK** to save

**Note**: Some labels update immediately, others may require selecting a different view or reopening dialogs.

## Preferences Storage

**Location**:
- Preferences saved in: `_AppConfig/preferences.json`
- Automatically created on first run
- Updated when you click **OK**

**Persistence**:
- Settings persist between sessions
- Loaded automatically on startup
- No manual configuration required

**Format** (JSON):
```json
{
  "theme": "dark_professional",
  "language": "fr"
}
```

## Resetting Preferences

**Reset to Defaults**:
1. Open **Settings** → **Preferences**
2. Click **Reset to Defaults** button
3. Confirm reset action
4. All settings return to:
   - Theme: Classic Light
   - Language: English

## Theme Customization

### For Developers

Themes are defined in `src/config/theme_manager.py`:

**Color Keys**:
- `bg`, `fg`: Main background and foreground
- `select_bg`, `select_fg`: Selection colors
- `header_bg`, `header_fg`: Header colors
- `tree_bg`, `tree_fg`: TreeView colors
- `grid_bg`, `grid_fg`: DataGrid colors
- `button_bg`, `button_fg`: Button colors
- `accent`: Accent color for highlights

**Creating Custom Themes**:
1. Add new theme to `THEMES` dictionary
2. Define all required color keys
3. Use hex color codes (#RRGGBB)
4. Test with all components

## Translations

### For Developers

Translations defined in `src/config/i18n.py`:

**Adding Translations**:
1. Add key-value pairs to `TRANSLATIONS` dict
2. Provide translations for both 'en' and 'fr'
3. Use descriptive keys (e.g., 'btn_data_explorer')
4. Apply with `t('key_name')` function

**Translation Keys**:
- Menu items: `menu_*`
- Buttons: `btn_*`
- Messages: `msg_*`
- Preferences: `pref_*`
- Common: `ok`, `cancel`, `apply`, etc.

## Tips and Best Practices

**Choosing a Theme**:
- Use **Classic Light** for maximum readability
- Use **Dark Professional** for extended coding sessions
- Use **Azure Blue** for a modern, fresh look

**Language Switching**:
- Preview language change before saving
- Some elements update immediately
- Reopen dialogs to see full translation

**Performance**:
- Theme changes apply instantly
- No performance impact
- All themes equally fast

**Accessibility**:
- Classic Light has highest contrast
- Dark Professional may help with light sensitivity
- All themes designed for readability

## Troubleshooting

**Theme Not Applying**:
- Check that you clicked **OK** not **Cancel**
- Verify `_AppConfig/preferences.json` exists
- Try **Reset to Defaults** and reapply

**Language Not Changing**:
- Some labels update lazily
- Close and reopen dialogs
- Switch views to refresh

**Preferences Not Saving**:
- Ensure `_AppConfig/` folder is writable
- Check file permissions
- Verify disk space available

## Future Enhancements

Planned features:
- Font size customization
- High contrast mode
- Additional language support
- Custom theme creation UI
