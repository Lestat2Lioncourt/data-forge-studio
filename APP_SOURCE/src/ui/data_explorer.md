# Data Explorer

## Overview

The Data Explorer is a powerful file navigation and viewing tool that allows you to browse folders, preview files, and analyze data from multiple sources.

## Features

### File Navigation

**Tree View**:
- Navigate through folder hierarchies
- View file and folder counts in real-time
- Expand/collapse folders with lazy loading
- Quick toolbar buttons: Refresh, Up Level, Root

**File Information**:
- File name, size, type
- Modification date
- File count for folders (recursive)

### File Viewing

**Supported File Types**:
- **Text files**: .txt, .log, .md, .py, .js, .java, .cpp, .h, .sql
- **CSV files**: .csv, .tsv (with table view)
- **JSON files**: .json (with pretty formatting)
- **Binary files**: Size and type information only

**Text File Viewer**:
- Automatic encoding detection (UTF-8, Latin-1, CP1252, ISO-8859-1)
- Manual encoding selection
- Horizontal and vertical scrolling
- Limit to first 10,000 lines for large files

**CSV File Viewer**:
- **Raw View**: Plain text with syntax highlighting
- **Table View**: Interactive data grid with:
  - Multi-column sorting (Ctrl+Click to add columns)
  - Export to CSV or Excel
  - Copy selection to clipboard
  - Fullscreen mode
  - Auto-sized columns

**JSON File Viewer**:
- Pretty-printed formatting
- Syntax highlighting
- Nested structure display

### Log File Filtering

For `.log` files, an advanced filtering toolbar appears:

**Filter Checkboxes**:
- **ERROR**: Show error messages
- **WARNING**: Show warning messages
- **IMPORTANT**: Show important messages
- **INFO**: Show informational messages

**How It Works**:
- All checkboxes checked = show everything (default)
- Uncheck levels to hide them
- Filter applies instantly
- Shows filtered count: "Showing X of Y lines"

**Supported Log Formats**:
- `[ERROR]`, `[WARNING]`, `[IMPORTANT]`, `[INFO]`
- `ERROR]`, `WARNING]`, `IMPORTANT]`, `INFO]`

### Column Statistics

When viewing CSV or database table data, statistics appear in the middle panel:

**Statistics Displayed**:
- **Column**: Column name
- **Total**: Total number of rows
- **Non-Null**: Rows with values
- **Empty**: Rows with NULL or empty values
- **Distinct**: Number of unique values

This helps quickly understand data quality and distribution.

## Database Integration

**View Database Tables**:
1. Navigate to a project with databases in the tree
2. Expand the database node
3. Right-click a table and select view option:
   - View All: Show all rows
   - View Top 100: Limit to 100 rows
   - View Top 1000: Limit to 1000 rows

**Direct Query Execution**:
- Query results display in the Data Explorer
- Statistics automatically calculated
- Export and sort capabilities enabled

## CSV Table View

**Multi-Column Sorting**:
1. Click column header to sort by that column
2. Click again to toggle ASC/DESC
3. **Ctrl+Click** other columns to add to sort
4. Visual indicators show sort order: 1▲, 2▼, 3▲

**Export Options**:
- Export to CSV
- Export to Excel (.xlsx)
- Copy selected rows to clipboard

**Fullscreen Mode**:
- Click fullscreen button to expand grid
- Opens in new window
- Preserves sorting, filtering, selection

## Projects and Root Folders

**Projects**:
- Organize related folders and databases
- Each project can have multiple root folders
- Each project can have multiple database connections

**Root Folders**:
- Quick access to frequently used directories
- Optional description for each folder
- File count shown in parentheses

**Managing Projects**:
- Menu: **Data** → **Manage Projects**
- Menu: **Data** → **Manage Root Folders**

## Keyboard Shortcuts

- **Double-Click**: Open file or expand folder
- **Right-Click**: Context menu (databases, tables)
- **Ctrl+Click** (in table): Add column to sort

## Tips and Tricks

**Large Files**:
- The viewer limits display to 10,000 lines
- Use encoding selector if file appears garbled
- Click "Reload" after changing encoding

**CSV Performance**:
- Start in Raw View for very large files
- Switch to Table View for analysis
- Use sorting on all loaded data, not just visible rows

**Log Analysis**:
- Use filters to focus on errors or warnings
- All filters work together (AND logic)
- Uncheck all to see only untagged lines

**Database Queries**:
- Right-click table for quick SELECT queries
- Results display with statistics
- Export results to CSV or Excel

## Encoding Issues

If text appears garbled:
1. Select different encoding from dropdown
2. Click "Reload"
3. Common encodings: UTF-8, Latin-1, CP1252, ISO-8859-1

Auto-detection tries multiple encodings automatically.
