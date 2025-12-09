# Database Manager

## Overview

The Database Manager provides a comprehensive interface for managing database connections, executing SQL queries, and viewing query results.

## Database Connections

### Supported Database Types

- **SQLite**: Embedded database files
- **SQL Server**: Microsoft SQL Server
- **PostgreSQL**: PostgreSQL databases
- **MySQL**: MySQL and MariaDB
- **Oracle**: Oracle Database

### Creating a Connection

**Via Menu**:
1. Go to **Databases** → **New Connection**
2. Fill in connection details:
   - **Name**: Friendly name for the connection
   - **Type**: Database type (SQLite, SQL Server, etc.)
   - **Connection String**: Database connection string
3. Click **Test Connection** to verify
4. Click **Save** to store the connection

**Connection String Examples**:

**SQLite**:
```
Database=path/to/database.db
```

**SQL Server**:
```
Driver={SQL Server};Server=localhost;Database=mydb;Trusted_Connection=yes;
```

**PostgreSQL**:
```
Driver={PostgreSQL};Server=localhost;Port=5432;Database=mydb;Uid=user;Pwd=password;
```

**MySQL**:
```
Driver={MySQL ODBC 8.0};Server=localhost;Database=mydb;User=user;Password=password;
```

### Managing Connections

**Edit Connection**:
- Menu: **Databases** → **Manage Connections**
- Select connection and click **Edit**
- Modify details and **Save**

**Delete Connection**:
- Menu: **Databases** → **Manage Connections**
- Select connection and click **Delete**
- Confirm deletion

**Test Connection**:
- Use **Test** button before saving
- Verifies connection string is valid
- Shows error if connection fails

## Query Execution

### Creating a Query Tab

**Method 1 - From Menu**:
1. Switch to **🗄️ Databases** view
2. Right-click a database in the schema tree
3. Select **New Query**

**Method 2 - From Data Explorer**:
1. Select a database or table in Data Explorer tree
2. Click **🗄️ Databases** toolbar button
3. Query tab opens automatically for selected database

### Writing Queries

**Query Editor**:
- SQL syntax editing
- Multiple query tabs supported
- Each tab connected to specific database

**Execute Query**:
1. Write SQL query in text area
2. Click **▶ Execute** button
3. Results appear in data grid below

**Supported Query Types**:
- `SELECT`: View query results
- `INSERT`, `UPDATE`, `DELETE`: Modify data
- `CREATE`, `ALTER`, `DROP`: Modify schema
- `EXEC`, `CALL`: Execute stored procedures

### Viewing Results

**Results Grid**:
- Scrollable data grid
- Column headers show data types
- Multi-column sorting available
- Export capabilities

**Result Statistics**:
- Row count displayed
- Execution time shown
- Error messages if query fails

### Managing Queries

**Save Query**:
- Click **💾 Save** button
- Enter query name and description
- Query saved for future use

**Load Saved Query**:
- Switch to **📋 Queries** view
- Double-click saved query to open
- Query opens in new tab

**Close Query Tab**:
- Click **✖** on query tab
- Unsaved changes prompt confirmation

## Schema Browser

**Database Tree**:
- Left panel shows database structure
- Expand database to see tables and views
- Expand table to see columns

**Table Information**:
- Column names
- Data types
- Primary keys (🔑 icon)
- Foreign keys (🔗 icon)

**Right-Click Actions**:
- **New Query**: Create query for database
- **View Top 1000**: Quick SELECT query
- **Refresh Schema**: Reload database structure

## Query Tab Features

### Multi-Tab Support

- Multiple query tabs open simultaneously
- Each tab independent
- Switch between tabs easily

### Query History

- Recent queries saved automatically
- Access from query dropdown
- Re-run previous queries quickly

### Export Results

**Export Formats**:
- **CSV**: Comma-separated values
- **Excel**: .xlsx format with formatting
- **Copy**: Copy selected rows to clipboard

**Export Steps**:
1. Execute query to get results
2. Click **Export** button in results grid
3. Choose format and location
4. File saved successfully

## Database-Specific Features

### SQLite

- Browse file-based databases
- Create new database files
- Compact database option

### SQL Server

- Windows authentication support
- Multiple schema support
- View execution plans

### PostgreSQL

- Schema support
- Advanced data types
- Array and JSON support

### MySQL

- Character set selection
- Multiple database support
- ENGINE specifications

## Tips and Best Practices

**Performance**:
- Use `LIMIT` or `TOP` for large tables
- Create indexes for frequently queried columns
- Avoid `SELECT *` in production queries

**Safety**:
- Test queries on development databases first
- Use transactions for multiple changes
- Backup databases before bulk operations

**Organization**:
- Save frequently used queries
- Use descriptive query names
- Group queries by function

**Troubleshooting**:
- Check connection string if connection fails
- Verify database permissions
- Review error messages carefully

## Keyboard Shortcuts

- **F5**: Execute query
- **Ctrl+S**: Save query
- **Ctrl+N**: New query tab
- **Ctrl+W**: Close current tab

## Security Notes

- Connection strings stored in `_AppConfig/connections.json`
- Credentials stored in plain text (use trusted machine only)
- Consider using Windows authentication when possible
- Encrypt sensitive configuration files
