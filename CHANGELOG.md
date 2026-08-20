# Changelog

All notable changes to DataForge Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.20] - 2026-08-20

### Fixed
- **The old window survived "update and relaunch" as an empty frame.** The close
  fix shipped in 0.6.19, but the version doing the closing is the one being
  replaced — so it only takes effect from an install that already has it. This
  release is the first that can be verified end to end from a fixed install
- The whole update path is now exercised before publishing: a real clone at the
  previous tag runs the real batch against the real remote, and the release is
  only cut once the old process is confirmed to exit leaving nothing on screen


## [0.6.19] - 2026-08-20

### Fixed
- **A password ending with `@` broke the connection test.** Testing a remote MySQL
  connection failed with `Can't connect to MySQL server on '@192.168.86.30'
  ([Errno 11003] getaddrinfo failed)` — an `@` glued to the address, which of
  course does not resolve, so no packet ever left the machine. Five hand-rolled
  parsers all split the URL on the *first* `@`; the userinfo ends at the *last*
  one, and the path only starts after it. Saving and browsing were unaffected
  because stored connection strings carry no credentials — only the Test button
  injects them
  - `split_db_url()` is now the single parser (last-`@` rule, `/` in passwords,
    IPv6 literals, query params, percent decoding); the four copies are gone
  - credentials are percent-encoded when the test URL is built, so a raw `@`
    never produces a malformed URL in the first place
- **Closing the app left an empty frame on screen, or skipped its cleanup.** With
  `easy_resize=True` the visible top-level widget is the resize wrapper and the
  window sits inside it. Only the inner window's close was handled, leaving the
  two paths broken in opposite ways: the title-bar X skipped geometry save,
  manager cleanup and any pending update entirely, while the File menu and the
  updater tore the app down but left the wrapper visible and the process alive
- **The reachability probe could get the client IP blocked by MySQL** (error 1129,
  `max_connect_errors`). MySQL speaks first, so opening a socket on 3306 and
  closing it without answering the handshake counts as an aborted connection.
  The connection dialog no longer probes before connecting — the driver's own
  error is more precise and `parse_connection_error` already classifies it. Where
  the probe remains, it drains and shuts down cleanly, sending a FIN rather than
  the RST that network monitoring reported as coming from the client

### Added
- `tests/test_connection_url_parsing.py` — covers the reported URL verbatim and
  the credential-less shape actually stored, so existing connections stay untouched


## [0.6.18] - 2026-08-20

### Fixed
- **The in-app updater generated a batch file cmd refused to parse.** The console
  flashed and closed instantly and the app was left on a frozen grey window, with
  no Python traceback because the failure happened in `cmd`. Inside the
  `if not exist ".git" (` block, the line `echo This install is standalone
  (no .git folder).` had its closing parenthesis terminate the block, leaving a
  stray `.` behind. Since `cmd` parses a parenthesised block before executing it,
  this killed the batch on **every** install, including healthy git ones where
  that branch is never taken
  - Also removed two `::` comments with unbalanced parentheses and an em dash:
    the file is written as UTF-8 but read by `cmd` under the OEM codepage
- **A failed update launch could strand the app.** `_run_update_on_quit()` ran
  unprotected and before the close event: any exception was invisible under
  `pythonw.exe` and skipped the close, leaving the window up with its signals
  disconnected and its managers torn down. It is now wrapped, logged with its
  traceback, reported to the user with a pointer to `scripts/_force_update.bat`,
  and the window always closes

### Added
- `tests/test_update_batch.py`: renders the generated batch and rejects unescaped
  parentheses inside an `if (...)` block and any non-ASCII character. Both guards
  were mutation-tested against the bug that shipped
- `docs/RELEASE_CHECKLIST.md` and a pointer in `CONTRIBUTING.md`: publishing needs
  a tagged GitHub release, not just a push — the app reads `releases/latest`


## [0.6.17] - 2026-08-20

### Added
- **ER diagrams as a workspace resource**: diagrams can be attached to a workspace like every other
  resource type (new `project_er_diagrams` junction table, migration 13)
  - Right-click a diagram to add/remove it from workspaces, or a connection/database node to add all
    the diagrams below it at once
  - New "ER Diagrams" branch in the workspace tree, with a rendered preview in its own tab
  - `ERDiagramManager` exposes `show_diagram()`, `render_diagram()` and `get_diagram_context_actions()`
    so consumers delegate instead of duplicating the actions
- **Diagram tree**: the diagram list is now a connection -> database -> diagram tree
- **Rename a diagram** from the tree, via a targeted UPDATE that does not commit pending layout edits
- **Explicit save for diagrams**: an unsaved-changes indicator plus a Save/Discard/Cancel prompt when
  switching diagrams. Adding/removing tables and toggling Group FKs no longer write to the database
  behind the user's back
- **Missing icon warning**: a missing icon now logs a warning naming the expected `.svg` file instead
  of silently falling back to the red placeholder
- `docs/ER_DIAGRAMS_ROUTING.md`: normative specification of the FK routing rules (R1..R6) and shared
  vocabulary

### Changed
- **FK auto-routing rewritten**: straight line > L-path > Z-path, instead of forcing parallel sides on
  every diagonal pair. `_compute_line_offsets` (385 lines) split into 11 named methods
  - A straight link is only kept when it does not push an anchor into a corner
  - Anchors constrained by an included edge impose their middle; the rest spread homogeneously
- **Save icon**: the toolbar uses a floppy disk icon instead of a star
- FK hover overlay extracted to `er_diagram/hover_overlay.py`, shared by the editing view and previews

### Fixed
- **Reachability probe scanned unrelated ports**: the probe never extracted the port and swept
  `[1433, 3306, 5432, 27017, 1521, 445]` on every remote server, so a MySQL test knocked on the SQL
  Server port and on SMB. It now only tests the port the connection actually uses
- **Host mis-parsed when the password contains `@` or `/`**: the connection string was split on the
  first `@`, yielding a nonexistent host and reporting a working server as unreachable
- **Flattened fields in the SQL Server connection dialog**: the dialog opened shorter than its content
  required and the deficit was absorbed by the text boxes (9 px instead of 26). Connection dialogs now
  open at least as tall as they need
- **Oblique FK segments**: waypoints saved under a different side assignment produced diagonal segments
  and a first segment running back inside the table. Restored chains are validated against the
  orthogonality invariant and discarded when incompatible
- **Stale diagram preview**: a preview left open in the workspace kept showing the layout it was built
  with; it is now revalidated on save, on view switch and on refresh
- Read-only previews could still be moved: the view's unfreeze safety net undid the freeze on first click


## [0.5.2] - 2025-12-21

### Added
- **Update on Quit feature**: When an update is available, users can choose to update automatically when closing the app
  - Opens terminal window with `git pull && uv sync` commands
  - Cross-platform support (Windows cmd, macOS Terminal, Linux terminals)
- **Git safe.directory handling**: Automatically fixes "dubious ownership" error on Windows drives

### Fixed
- **Dynamic version display**: About dialog and Help page now use version from `pyproject.toml` instead of hardcoded value
- **Update dialog**: Now has three buttons (Update on Quit, View on GitHub, Remind Later) instead of two

## [0.5.1] - 2025-12-21

### Added
- **DataExplorer file loading**: Full implementation using existing `data_loader.py`
  - CSV files with automatic encoding and separator detection
  - JSON files with row-keyed object detection (`{"id1": {...}, "id2": {...}}` → table)
  - Excel files (.xlsx, .xls) support
  - Text files with encoding detection
  - Large dataset warning (> 100k rows)
- **Open in file explorer**: Cross-platform support (Windows/Mac/Linux)
- **Add File Root dialog**: Connected to existing `EditRootFolderDialog`
- **New translation keys**: 20+ keys added to EN and FR language files

### Improved
- **JSON row-keyed detection**: Objects with dict values are now correctly displayed as tables
  - Adds `_id` column with original keys for traceability
  - Detects common keys across sub-objects

### Fixed
- DataExplorer no longer shows placeholder data - uses real file content

## [0.5.0] - 2025-12-21

### Added
- Theme opacity system (Selected_Opacity, Hover_Opacity)
- IconSidebar theming integration
- Splash screen with 4-second minimum display
- Automatic update check on startup (24h cooldown)

### Changed
- Major UI refactoring from TKinter to PySide6
- 60% code reduction through intelligent patterns

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
