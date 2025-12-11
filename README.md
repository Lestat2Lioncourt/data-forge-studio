# DataForge Studio v0.50 🚀

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.10+-green.svg)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.50.0-orange.svg)](CHANGELOG.md)

**Multi-database management tool with modern PySide6 interface**

![DataForge Studio](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

## ✨ What's New in v0.50

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
├── src/dataforge_studio/      # v0.50 PySide6 version
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

### Prerequisites
- **Python 3.10 or higher**
- **uv** (recommended) or pip for package management

### Quick Start with UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/data-forge-studio.git
cd data-forge-studio

# Install dependencies
uv sync

# Run the application
uv run run.py
```

### Alternative: Standard pip installation

```bash
# Clone and navigate
git clone https://github.com/yourusername/data-forge-studio.git
cd data-forge-studio

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Run the application
python run.py
```

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
git clone https://github.com/yourusername/data-forge-studio.git
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
- PySide6 Migration: v0.50.0

## 🙏 Acknowledgments

- **window-template** - Frameless window implementation
- **PySide6** - Qt for Python framework
- **UV** - Fast Python package installer
- **SQLAlchemy** - Database abstraction layer
- **sqlparse** - SQL formatting library

## 📜 Changelog

### v0.50.0 (2025-12-11) - Major Release
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
