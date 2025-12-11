# Projects & Root Folders Management

## Overview

Projects and Root Folders help you organize and quickly access frequently used directories and databases.

## Projects

### What is a Project?

A **Project** is a container that groups related:
- **Root Folders**: Directories to monitor
- **Databases**: Database connections

Projects help organize work by:
- Client / customer
- Application / system
- Environment (dev, test, prod)
- Department / team

### Managing Projects

**Create Project**:
1. Menu: **Data** → **Manage Projects**
2. Click **Add Project**
3. Enter project name and description
4. Click **Save**

**Edit Project**:
1. Menu: **Data** → **Manage Projects**
2. Select project from list
3. Click **Edit**
4. Modify name or description
5. Click **Save**

**Delete Project**:
1. Menu: **Data** → **Manage Projects**
2. Select project from list
3. Click **Delete**
4. Confirm deletion

**Note**: Deleting a project does NOT delete folders or databases, only the project reference.

### Project Structure

Each project can contain:
- Multiple root folders
- Multiple database connections
- Nested organization in tree view

## Root Folders

### What is a Root Folder?

A **Root Folder** is a monitored directory that:
- Appears in the Data Explorer tree
- Shows recursive file count
- Provides quick access to data files
- Can have optional description

### Managing Root Folders

**Add Root Folder**:
1. Menu: **Data** → **Manage Root Folders**
2. Click **Add Folder**
3. Fill in details:
   - **Path**: Directory path to monitor
   - **Name**: Display name (optional, uses folder name if empty)
   - **Description**: Purpose or content description
   - **Project**: Associated project (optional)
4. Click **Browse** to select folder
5. Click **Save**

**Edit Root Folder**:
1. Menu: **Data** → **Manage Root Folders**
2. Select folder from list
3. Click **Edit**
4. Modify details
5. Click **Save**

**Delete Root Folder**:
1. Menu: **Data** → **Manage Root Folders**
2. Select folder from list
3. Click **Delete**
4. Confirm deletion

**Note**: Deleting a root folder does NOT delete the actual directory, only the monitoring reference.

### Root Folder Display

In Data Explorer tree:
```
📁 Project Name
  📁 RootFolder1 (1523) - Description
  📁 RootFolder2 (847) - Description
  🗄️ Database1 (sqlite)
  🗄️ Database2 (sqlserver)
```

**File Count** (in parentheses):
- Shows total files recursively
- Updates on folder expand
- Includes all subdirectories
- Excludes hidden files (starting with '.')

## Database Connections in Projects

### Adding Database to Project

**Method 1 - During Creation**:
1. Create new database connection
2. Select project from dropdown
3. Save connection

**Method 2 - Edit Existing**:
1. Edit database connection
2. Change project assignment
3. Save changes

### Database Display

Databases appear under their assigned project:
```
📁 My Project
  📁 Data Folder (500)
  🗄️ Production DB (sqlserver)
    📊 Tables
    📊 Views
  🗄️ Analytics DB (postgres)
    📊 Tables
    📊 Views
```

## Tree View Organization

### Hierarchy

```
Root
├── 📁 Project 1
│   ├── 📁 Root Folder 1 (count)
│   │   ├── 📁 Subfolder A
│   │   └── 📄 File 1.csv
│   ├── 📁 Root Folder 2 (count)
│   └── 🗄️ Database 1
│       ├── 📊 Tables
│       └── 📊 Views
└── 📁 Project 2
    ├── 📁 Root Folder 3 (count)
    └── 🗄️ Database 2
```

### Expanding Items

- **Single-click**: Select item
- **Double-click**: Expand/collapse or open file
- **Right-click**: Context menu (for databases/tables)

### File Count Calculation

**Recursive Count**:
- Counts all files in folder and subfolders
- Updates when folder is expanded
- Shows: `📁 FolderName (count)`

**Performance**:
- Counted on-demand (lazy loading)
- Cached until refresh
- Handles permission errors gracefully

## Use Cases

### Organizing by Client

```
📁 Client A
  📁 Data Files (1200)
  🗄️ Client A Database

📁 Client B
  📁 Data Files (800)
  🗄️ Client B Database
```

### Organizing by Environment

```
📁 Development
  📁 Dev Data (500)
  🗄️ Dev Database

📁 Production
  📁 Prod Data (10000)
  🗄️ Prod Database
```

### Organizing by Type

```
📁 Customer Data
  📁 Raw Files (2000)
  📁 Processed Files (1500)
  🗄️ Customer DB

📁 Analytics
  📁 Reports (300)
  🗄️ Analytics DB
```

## Configuration Storage

**Projects**:
- Stored in: `_AppConfig/projects.db` (SQLite)
- Table: `projects`
- Fields: id, name, description, created_date

**Root Folders**:
- Stored in: `_AppConfig/projects.db` (SQLite)
- Table: `file_roots`
- Fields: id, path, name, description, project_id

**Database Connections**:
- Stored in: `_AppConfig/connections.json`
- Includes project_id reference

## Tips and Best Practices

**Project Naming**:
- Use clear, descriptive names
- Include version or environment if needed
- Keep names short for tree display

**Root Folder Paths**:
- Use absolute paths
- Verify paths exist before saving
- Use network paths for shared data

**Descriptions**:
- Describe folder contents or purpose
- Include data owner or contact
- Note update frequency

**Organization**:
- Group related folders under projects
- One project per client/application
- Separate development from production

**Performance**:
- Avoid extremely deep folder structures
- Limit number of root folders per project
- Use specific paths, not drive roots

## Troubleshooting

**Folder Not Appearing**:
- Check path is correct
- Verify folder exists
- Check read permissions
- Refresh tree (🔄 button)

**File Count Shows 0**:
- Folder may be empty
- Permission error (check logs)
- Hidden files excluded

**Database Not Listed**:
- Verify project assignment
- Check database connection is saved
- Refresh connections

**Tree Not Updating**:
- Click **Refresh** (🔄) button
- Close and reopen Data Explorer
- Check configuration database

## Advanced Features

### Path Variables

Future enhancement: Environment variables in paths
```
{HOMEPATH}\Data
{APPDATA}\MyApp\Files
```

### Folder Filters

Future enhancement: Filter files by extension or pattern
```
*.csv, *.xlsx, *.json
```

### Auto-Discovery

Future enhancement: Automatically discover databases in folders
```
Scan for .db, .sqlite, .mdb files
```
