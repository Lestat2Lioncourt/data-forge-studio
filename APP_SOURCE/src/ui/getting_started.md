# Getting Started

## Overview

Data Lake Loader is a comprehensive data management application designed for exploring, viewing, and managing data from multiple sources including files, databases, and data lakes.

## Key Features

- **Data Explorer**: Navigate through folders, view files (CSV, JSON, text, logs)
- **Database Manager**: Connect to multiple databases, execute queries, view results
- **Theme Support**: Multiple visual themes (Classic Light, Dark Professional, Azure Blue)
- **Multi-language**: Interface available in English and French
- **Log Filtering**: Advanced filtering for log files by severity level
- **Data Grids**: Sortable, exportable data grids with statistics

## Quick Start

### 1. Launch the Application

Run the application from the command line:

```bash
uv run src/main.py
```

Or on Windows:

```cmd
python src\main.py
```

### 2. Navigate the Interface

The main window contains:

- **Toolbar**: Quick access to main views (Data Explorer, Data Lake, Databases, Queries)
- **Menu Bar**: Access to all features, settings, and documentation
- **Main Panel**: Content area that changes based on selected view

### 3. First Steps

**Explore Data**:
1. Click **📂 Data Explorer** in the toolbar
2. Navigate through the folder tree on the left
3. Double-click a file to view its content
4. For CSV files, toggle between raw and table view

**Connect to Database**:
1. Go to **Databases** menu → **New Connection**
2. Enter connection details (name, type, connection string)
3. Click **Test Connection** then **Save**
4. Access your database from the **🗄️ Databases** view

**Customize Interface**:
1. Go to **Settings** menu → **Preferences**
2. Select your preferred theme (Classic Light, Dark Professional, Azure Blue)
3. Choose your language (English / Français)
4. Changes apply immediately

## Main Views

### Data Explorer

Navigate files and folders, view content with advanced filtering and sorting capabilities.

### Data Lake

Manage data lake operations, dispatch files, and load data to databases.

### Databases

Execute SQL queries, manage connections, view database schemas and tables.

### Queries

Save and organize frequently used queries for quick access.

## Getting Help

- **Documentation**: Help menu → Documentation
- **About**: Help menu → About

## System Requirements

- Python 3.10 or higher
- Windows / Linux / macOS
- Dependencies: tkinter, pandas, pyodbc (for databases)

## Configuration

Configuration files are stored in:
- `_AppConfig/`: User preferences, database connections, themes
- `logs/`: Application logs

## Next Steps

- Read the **Data Explorer** guide to learn about file navigation and viewing
- Read the **Database Manager** guide to learn about SQL queries and data management
- Explore the **Themes & Preferences** guide to customize your experience
