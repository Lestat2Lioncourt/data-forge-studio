# DataForge Studio v0.6.10 🚀

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.10+-green.svg)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.6.10-orange.svg)](CHANGELOG.md)

**Multi-Datasource management tool with modern PySide6 interface**

![DataForge Studio](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

## ✨ Features

### 🎨 Complete UI Overhaul
- **Migrated from TKinter to PySide6** - Modern, professional Qt-based interface
- **Frameless Custom Window** - Using integrated window-template with custom title bar
- **60% Code Reduction** - From ~11,441 lines to ~4,600 lines through intelligent refactoring
- **Reusable Widget Library** - Consistent, modular UI components
- **Enhanced Architecture** - BaseManagerView pattern eliminates code duplication

### 🔧 New Features
- **Multi-tab SQL Editor** - Execute multiple queries simultaneously in DatabaseManager
- **Hierarchical Data Explorer** - Navigate projects, file roots, and files in tree view
- **Live Logs Panel** - Real-time script execution logs with filtering (INFO, WARNING, ERROR)
- **Job Scheduler** - Manage automated tasks with enable/disable, run now features
- **Internationalization** - Full EN/FR support with dynamic language switching
- **Dynamic Theming** - Real-time theme changes across entire application

### 📊 Managers Available
1. **Database Manager** - Multi-tab SQL query interface with results export
2. **Queries Manager** - Save and organize SQL queries
3. **Scripts Manager** - Python script management with execution logs
4. **Jobs Manager** - Scheduled task automation
5. **Data Explorer** - Project and file hierarchy navigation

## 📁 Project Structure

```
data-forge-studio/
├── APP_SOURCE/                # v0.3.0 TKinter version (archived)
│
├── src/dataforge_studio/      # v0.5.0 PySide6 version
│   ├── ui/                    # User Interface
│   │   ├── window_template/   # Frameless window base
│   │   ├── core/              # Main window, themes, i18n
│   │   ├── widgets/           # Reusable components
│   │   │   ├── dialog_helper.py
│   │   │   ├── toolbar_builder.py
│   │   │   ├── form_builder.py
│   │   │   ├── custom_treeview.py
│   │   │   ├── custom_datagridview.py
│   │   │   └── log_panel.py
│   │   ├── frames/            # Application frames
│   │   │   ├── data_lake_frame.py
│   │   │   ├── settings_frame.py
│   │   │   └── help_frame.py
│   │   └── managers/          # Data managers
│   │       ├── base_manager_view.py
│   │       ├── queries_manager.py
│   │       ├── scripts_manager.py
│   │       ├── jobs_manager.py
│   │       ├── database_manager.py
│   │       └── data_explorer.py
│   │
│   ├── database/              # Database layer
│   │   ├── config_db.py
│   │   └── connections_config.py
│   │
│   ├── utils/                 # Utilities
│   │   ├── logger.py
│   │   ├── sql_highlighter.py (PySide6 QSyntaxHighlighter)
│   │   └── config.py
│   │
│   ├── scripts/               # Business scripts
│   │   ├── file_dispatcher.py
│   │   └── data_loader.py
│   │
│   └── main.py               # Application entry point
│
├── run.py                     # Launcher script
├── cli.py                     # Command-line interface
├── pyproject.toml             # Project configuration
└── uv.lock                    # Dependency lock file
```

## 🚀 Installation

### Quick Start (Recommended)

**No Python installed? No problem!** UV installs Python automatically.

#### 🪟 Windows

```powershell
# 1. Install UV (one-time setup)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Clone, install and run (UV installs Python automatically)
git clone https://github.com/Lestat2Lioncourt/data-forge-studio.git
cd data-forge-studio
uv sync
uv run python run.py

# ⚠️ Corporate proxy? If uv sync fails with "invalid peer certificate",
# run this once then restart your terminal and retry uv sync:
# setx UV_SYSTEM_CERTS 1
```

#### 🍎 MacOS

```bash
# 1. Install UV (one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone, install and run (UV installs Python automatically)
git clone https://github.com/Lestat2Lioncourt/data-forge-studio.git
cd data-forge-studio
uv sync
uv run python run.py

# ⚠️ Corporate proxy? If uv sync fails with "invalid peer certificate",
# add this to ~/.zshrc then restart your terminal and retry uv sync:
# echo 'export UV_SYSTEM_CERTS=1' >> ~/.zshrc && source ~/.zshrc
```

#### 🐧 Linux (Ubuntu/Debian)

```bash
# 1. Install UV (one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone, install and run (UV installs Python automatically)
git clone https://github.com/Lestat2Lioncourt/data-forge-studio.git
cd data-forge-studio
uv sync
uv run python run.py

# ⚠️ Corporate proxy? If uv sync fails with "invalid peer certificate",
# add this to ~/.bashrc then restart your terminal and retry uv sync:
# echo 'export UV_SYSTEM_CERTS=1' >> ~/.bashrc && source ~/.bashrc
```

> **Note**: `uv sync` automatically downloads and installs the correct Python version (3.10+) if not present on your system.

---

### SQL Server Drivers (Optional)

Only needed if you want to connect to SQL Server databases.

#### MacOS
```bash
brew install unixodbc
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew install msodbcsql18
```

#### Linux (Ubuntu/Debian)
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

---

### Alternative: Standard pip installation

If you prefer pip over UV (requires Python 3.10+ already installed):

```bash
git clone https://github.com/Lestat2Lioncourt/data-forge-studio.git
cd data-forge-studio
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
python run.py
```

---

### 📦 Offline Installation (No Internet on Target Machine)

For machines without internet access (e.g., behind restrictive VPN), a user with internet can generate a self-contained package from the app via **Tools > Generate Offline Package**, then transfer it to the target machine.

See [`_packages/README_OFFLINE.md`](_packages/README_OFFLINE.md) for detailed instructions.

---

### Create Desktop Shortcut (Optional)

After installation, create a desktop shortcut with icon:

```bash
uv run python scripts/create_shortcut.py
```

This works on all platforms:
- **Windows**: Creates `.lnk` shortcut with icon
- **MacOS**: Creates `.app` bundle (drag to Dock)
- **Linux**: Creates `.desktop` entry in app menu

### Check for Updates

Check if a new version is available:

```bash
uv run python scripts/check_update.py
```

To update to the latest version:

```bash
git pull
uv sync
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Certificate error (`UnknownIssuer`) | Corporate proxy: `setx UV_SYSTEM_CERTS 1` then restart terminal |
| PySide6 import error | `uv pip install --force-reinstall PySide6` |
| ODBC driver not found | Install msodbcsql18 (see platform instructions above) |
| Apple Silicon (M1/M2/M3) | Ensure arm64 packages: `uv sync --reinstall` |
| MacOS icon not showing | Install Pillow: `uv pip install pillow` |

## 💻 Usage

### Launch Application
```bash
uv run run.py
```

### Navigation
- **View Menu** → Access all managers (Database, Queries, Scripts, Jobs, Data Explorer)
- **Settings Menu** → Configure themes and language preferences
- **Help Menu** → Documentation and about information

### Key Features

#### 🗄️ Database Manager
- Multi-tab interface for concurrent SQL queries
- Connection selector with multiple database support
- Execute, format, and clear SQL queries
- Export results to CSV
- Syntax highlighting for SQL

#### 📝 Queries Manager
- Save frequently used SQL queries
- Organize by database and description
- Execute saved queries
- View query details (name, database, created/modified dates)

#### 🐍 Scripts Manager
- Manage Python scripts for data processing
- Execute scripts with live log output
- Filter logs by level (INFO, WARNING, ERROR, SUCCESS)
- View script details and execution history

#### ⏰ Jobs Manager
- Schedule automated tasks
- Enable/disable jobs
- Run jobs immediately (bypass schedule)
- View job status, schedule, and last/next run times
- Configure job parameters in JSON format

#### 🗂️ Data Explorer
- Hierarchical project navigation
- File roots with directory browsing
- CSV file preview in data grid
- JSON/TXT file viewer with syntax formatting
- Open file locations in system explorer

## 🎨 Themes

DataForge Studio includes multiple built-in themes:
- **Dark Mode** (default)
- **Light Mode**
- **High Contrast**

Switch themes via **Settings → Preferences → Select Theme**

## 🌍 Internationalization

Supported languages:
- **English** (en)
- **Français** (fr)

Switch languages via **Settings → Preferences → Select Language**

## 📊 Database Support

Supported databases:
- **SQL Server** (via pyodbc)
- **PostgreSQL** (via sqlalchemy)
- **SQLite** (built-in)
- **MySQL** (via sqlalchemy)
- **Oracle** (via sqlalchemy)

## 🏗️ Architecture Highlights

### Design Patterns
- **Builder Pattern** - ToolbarBuilder, FormBuilder for consistent UI construction
- **Observer Pattern** - Theme and language change notifications
- **Singleton Pattern** - ThemeBridge, I18nBridge for global state
- **Template Method** - BaseManagerView with abstract methods
- **Dependency Injection** - Managers injected into MainWindow

### Code Reduction Statistics
| Component | Before (TKinter) | After (PySide6) | Reduction |
|-----------|------------------|-----------------|-----------|
| QueriesManager | 445 lines | 230 lines | **-48%** |
| ScriptsManager | 625 lines | 272 lines | **-56%** |
| JobsManager | 870 lines | 297 lines | **-66%** |
| DatabaseManager | 1,411 lines | 306 lines | **-78%** |
| DataExplorer | 2,094 lines | 373 lines | **-82%** |
| **Total** | **~11,441 lines** | **~4,600 lines** | **-60%** |

### Why PySide6?
- **Modern Qt Framework** - Industry-standard GUI toolkit
- **Better Performance** - Native rendering, hardware acceleration
- **Professional Look** - Consistent cross-platform appearance
- **Rich Widgets** - QTableWidget, QTreeWidget with built-in sorting, filtering
- **Easy Styling** - QSS (Qt Style Sheets) similar to CSS
- **Signal/Slot** - Robust event handling mechanism

## 📚 Documentation

- **INTEGRATION_MANAGERS.md** - Manager integration guide
- **Plan file** - Complete migration plan (TKinter → PySide6)
- **API Documentation** - Coming soon
- **User Guide** - Coming soon

## 🧪 Testing

```bash
# Run all managers test
uv run python test_managers.py

# Run unit tests (when available)
uv run pytest tests/
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone and install development dependencies
git clone https://github.com/Lestat2Lioncourt/data-forge-studio.git
cd data-forge-studio
uv sync --dev

# Run tests before committing
uv run pytest
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**DataForge Studio Development Team**
- Original TKinter version: v0.1.0 - v0.3.0
- PySide6 Migration: v0.4.0+

## 🙏 Acknowledgments

- **window-template** - Frameless window implementation
- **PySide6** - Qt for Python framework
- **UV** - Fast Python package installer
- **SQLAlchemy** - Database abstraction layer
- **sqlparse** - SQL formatting library

## 📜 Changelog

### v0.6.10 (2026-04-08) - ER Diagrams, Shared Workspaces, Corporate Proxy
- Interactive ER Diagrams (tables, FK lines, drag, zoom, save, export PNG/SVG)
- Workspace shared folder configuration (OneDrive, SharePoint, network share)
- Corporate proxy support: UV_SYSTEM_CERTS documentation for certificate issues
- SQL formatter: CTE hierarchy, = alias alignment, OUTER/CROSS APPLY
- Auto-indent editor, tab to spaces, smart reconnect
- Audit #7: score 8.6/10

### v0.6.7 (2026-03-03) - SQL Formatter, Variables & Syntax Highlighting
- SQL formatter: multi-statement support (split by ;, format individually)
- SQL formatter: fix WHERE/AND keyword alignment
- Session variables (DECLARE/SET @) persist across statements (single batch execution)
- Syntax highlighting for @variables and additional T-SQL keywords
- Sort indicator auto-resize, splash screen on active monitor

### v0.6.6 (2026-03-03) - Combined File View & Context Menu Refactoring
- Right-click folder: "View all data files combined" (CSV/Excel/JSON merged view)
- Context menu delegation refactoring (workspace delegates to specialized managers)
- Fix sort indicator arrows in themed QHeaderView
- Detachable query tabs, split toggle (stacked / side-by-side)
- PopupWindow edge-resize support

### v0.6.5 (2026-03-03) - SVG Icon Migration
- Migrate icon system from PNG to SVG (37 icons, scalable, no PIL dependency)
- SVG recoloring via text replacement, QSvgRenderer rendering
- Database-specific logos in connection selector dialog
- Fix self-deleting update batch file error

### v0.6.4 (2026-03-02) - Code Quality & Refactoring
- Refactor config_db.py as pure facade delegating to 10 repositories
- Split query_tab.py into 6 mixin modules (2061→417 lines)
- Replace 169 generic `except Exception` with specific exception types
- Remove `shell=True` from subprocess calls, parameterize SQL queries
- Sanitize SQL identifiers in access_dialect, data_loader and base dialect
- Audit #5: score 7.9/10, all P1/P2 fixes resolved

### v0.6.3 (2026-03-01) - Database Manager Refactoring
- Split database_manager.py into mixin modules + fix PostgreSQL quoting
- Redesign About dialog and standardize close button icon
- Always show update notification in status bar on startup

### v0.6.2 (2026-02-28) - Editable Tabs & Update Improvements
- Add EditableTabWidget for renamable query tabs
- Fix update-on-quit mechanism, use git reset in update script
- Eliminate query tab duplication between managers
- Use icon_color instead of toolbarbtn_fg for themed icons
- Auto-create _AppConfig directories on first launch

### v0.6.1 (2026-02-26) - SQL Formatter Enhancement
- Ultimate-style formatting for UPDATE/SET with leading commas
- Multiline CASE WHEN with operator alignment (IS NOT NULL, =, etc.)
- Multiline COALESCE/function expansion with args aligned under `(`

### v0.6.0 (2026-02-16) - Offline Package Generation
- Tools > Generate offline package: build self-contained package from the app
- Real-time console output with colored log lines and 7z progress bar
- Versioned archive naming (DataForgeStudio_vX.Y.Z.7z)

### v0.5.9 (2025-02-10) - Offline Installation
- Offline package preparation script (`_packages/prepare_package.bat`)
- Complete standalone package (~2 GB) with Python, dependencies, UV
- Updated README with offline installation instructions

### v0.5.8 (2025-02-10) - Workspace Filter & Auto-Connect
- Workspace tree filter with debounce (400ms)
- Auto-expand branches including FTP (async connection)
- Favorite workspace with auto-connect at startup
- FTP reachability check (3s timeout)
- File count display for FTP folders
- Shared `tree_helpers.py` module
- CLI roadmap (EVO-1) with Script/Instance model

### v0.5.0 (2025-12-21) - Theme & UI Improvements
- Theme opacity system (`Selected_Opacity`, `Hover_Opacity`)
- IconSidebar theme integration with transparency
- Pin button visibility fix (tinted based on theme)
- ImageLibraryManager now uses PinnablePanel
- Splash screen timing fix
- Log/Text viewer theming
- Quick Theme Frame: IconSidebar colors

### v0.4.0 (2025-12-11) - Major Release
- Complete UI migration from TKinter to PySide6
- Integrated frameless window template
- 60% code reduction through refactoring
- New reusable widget library
- Enhanced manager architecture
- Full internationalization (EN/FR)
- Dynamic theming system

### v0.3.0 (Previous)
- Automatic update checker
- Enhanced status bar
- i18n support (EN/FR)
- Theme editor

### v0.2.0 and earlier
- See APP_SOURCE/README_v0.3.0.md for legacy version history

---

**Built with ❤️ using PySide6 and Python**
