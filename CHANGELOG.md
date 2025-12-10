# Changelog

All notable changes to DataForge Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2025-12-10

### Fixed
- **Multi-column sorting in CustomDataGridView**: Completely rewrote sorting algorithm using Python's stable sort
  - Fixed broken logic where ASC and DESC used the same values
  - Reduced code from 82 lines to 45 lines
  - Sorting now properly works with multiple columns using Ctrl+Click
- **Column auto-sizing**: Fixed columns not respecting width settings
  - Added `stretch=False` to force Treeview columns to respect width parameter
  - Columns now properly auto-size to content width
- **Fullscreen mode sorting**: Added click handlers for column headers in fullscreen
  - New `_on_fullscreen_header_click` method
  - New `_refresh_fullscreen_display` method
  - Fullscreen now supports full sorting functionality
- **Saved Queries execution**: Fixed queries redirecting to Database Manager
  - Queries now execute locally in Saved Queries Manager
  - Restored result grid display
  - Added `_connect_sqlite` method for SQLite connections
  - Fixed connection handling for both SQLite and other databases
- **Fullscreen consistency**: Removed custom fullscreen implementation in Data Explorer
  - Deleted 51 lines of duplicate code
  - All views now use consistent fullscreen behavior from CustomDataGridView

## [0.3.0] - 2025-12-10

### Added
- **Automatic Update Checker**: Checks GitHub for new releases on startup
  - 24-hour cooldown after dismissal to avoid notification spam
  - Status bar notification with clickable link to details
  - Manual check option in Help menu
- **Update Dialog** with detailed release notes and instructions
  - View release on GitHub button
  - "Update on Quit" feature for automatic update when closing app
  - "Remind Tomorrow" option to defer update
- **One-Click Update Script**: `uv run run.py --update`
  - Automatically runs `git pull` and `uv sync`
  - Opens in new terminal window with progress display
  - Error handling with fallback to manual instructions
- **Enhanced Status Bar**:
  - Now visible at bottom of window
  - Shows "Your version is up to date" / "Votre version est à jour"
  - Update notifications in bold dark green for better readability
  - Internationalized messages (EN/FR)

### Changed
- Improved status bar visibility and positioning
- Update notifications now use bold dark green text instead of orange

## [0.2.0] - 2025-12-09

### Added
- Multi-database support (SQL Server, SQLite, PostgreSQL)
- Advanced SQL formatter with 4 styles:
  - Expanded (one column per line)
  - Compact (multiple columns per line)
  - Comma First (commas at beginning)
  - Aligned (keywords and operators aligned)
- Project organization system
- Query management with folders and favorites
- Theme customization with built-in themes
- Theme editor for creating custom themes
- Internationalization support (i18n)
- Language switching (EN/FR)
- Data explorer with search and filter
- File root manager for data lake operations
- Preferences dialog with multiple tabs
- Context menus for database objects
- Export results (CSV, Excel, JSON)
- Query history
- Syntax highlighting for SQL
- Connection manager
- Help viewer with embedded documentation

### Changed
- Rebranded from "Load_Data_Lake" to "DataForge Studio"
- Migrated configuration from JSON to SQLite
- Improved UI with modern tkinter widgets
- Enhanced logging system with filters

### Fixed
- Various bug fixes and stability improvements

## [0.1.0] - 2024-12-08

### Added
- Initial release as "Load_Data_Lake"
- Basic file dispatcher
- Data loader for SQL Server
- Simple GUI interface
- CLI support

[Unreleased]: https://github.com/Lestat2Lioncourt/data-forge-studio/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/Lestat2Lioncourt/data-forge-studio/releases/tag/v0.4.0
[0.3.0]: https://github.com/Lestat2Lioncourt/data-forge-studio/releases/tag/v0.3.0
[0.2.0]: https://github.com/Lestat2Lioncourt/data-forge-studio/releases/tag/v0.2.0
[0.1.0]: https://github.com/Lestat2Lioncourt/data-forge-studio/releases/tag/v0.1.0
