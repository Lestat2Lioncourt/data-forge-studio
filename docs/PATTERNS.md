# DataForge Studio - Design Patterns & Standards

This document describes the standard patterns used throughout the DataForge Studio codebase.

---

## 1. Manager View Architecture

### 1.1 BaseManagerView (Standard Pattern)

For simple list-based managers (Queries, Scripts, Jobs):

```
┌─────────────────────────────────────────────────────┐
│ Toolbar                                              │
├──────────────┬──────────────────────────────────────┤
│              │  Details Panel                        │
│  PinnablePanel  ├──────────────────────────────────────┤
│  (TreeView)  │  Content Panel                        │
│              │                                        │
└──────────────┴──────────────────────────────────────┘
```

**Inherit from**: `BaseManagerView` or `HierarchicalManagerView`

**Required overrides**:
- `_get_tree_columns()` - Column names for tree
- `_load_items()` - Load data into tree
- `_display_item(item_data)` - Display selected item
- `_setup_toolbar()` - Configure toolbar buttons

### 1.2 Specialized Managers

For complex managers with unique requirements:

**DatabaseManager** - Multi-tab query interface
```
┌─────────────────────────────────────────────────────┐
│ Toolbar                                              │
├──────────────┬──────────────────────────────────────┤
│              │  ┌─────┬─────┬─────┐                  │
│  PinnablePanel  │  Tab │ Tab │ Tab │ (Query Tabs)    │
│  (Schema Tree)│  └─────┴─────┴─────┘                  │
│              │  Query Editor + Results               │
└──────────────┴──────────────────────────────────────┘
```

**RootFolderManager** - File browser with multiple view modes
```
┌─────────────────────────────────────────────────────┐
│ Toolbar                                              │
├──────────────┬──────────────────────────────────────┤
│              │  File Details (FormBuilder)           │
│  PinnablePanel  ├──────────────────────────────────────┤
│  (File Tree) │  Content Viewer (Grid/Raw/Text)       │
│              │                                        │
└──────────────┴──────────────────────────────────────┘
```

---

## 2. Widget Patterns

### 2.1 PinnablePanel

SSMS-style collapsible panel with pin/unpin functionality.

```python
from ui.widgets.pinnable_panel import PinnablePanel

# Create panel
self.left_panel = PinnablePanel(
    title="Explorer",
    icon_name="icon.png"
)
self.left_panel.set_normal_width(280)

# Set content
tree_container = QWidget()
# ... setup tree widget ...
self.left_panel.set_content(tree_container)
```

### 2.2 ToolbarBuilder

Fluent API for building toolbars.

```python
from ui.widgets.toolbar_builder import ToolbarBuilder

toolbar_builder = ToolbarBuilder(self)
toolbar_builder.add_button("Add", self._add_item, icon="add.png")
toolbar_builder.add_button("Delete", self._delete_item, icon="delete.png")
toolbar_builder.add_separator()
toolbar_builder.add_button("Refresh", self._refresh, icon="refresh.png")

self.toolbar = toolbar_builder.build()
```

### 2.3 FormBuilder

Fluent API for building detail forms.

```python
from ui.widgets.form_builder import FormBuilder

self.details_form = FormBuilder(title="Details") \
    .add_field("Name:", "name") \
    .add_field("Type:", "type") \
    .add_field("Description:", "description")

form_widget = self.details_form.build()

# Update values
self.details_form.set_value("name", item.name)
```

### 2.4 CustomTreeView

Enhanced tree widget with common functionality.

```python
from ui.widgets.custom_treeview import CustomTreeView

self.tree_view = CustomTreeView(
    columns=["Name", "Description"],
    on_select=self._on_item_selected,
    on_double_click=self._on_item_double_clicked
)

# Add items
item = self.tree_view.add_item(
    parent=parent_item,
    text=["Item Name", "Item Description"],
    data={"type": "item", "item": item_obj}
)
```

### 2.5 DialogHelper

Standardized dialog boxes.

```python
from ui.widgets.dialog_helper import DialogHelper

# Information
DialogHelper.info("Operation completed.", parent=self)

# Warning
DialogHelper.warning("No item selected.", parent=self)

# Error with details
DialogHelper.error(
    "Operation failed.",
    parent=self,
    details=str(exception)
)

# Confirmation
if DialogHelper.confirm("Delete this item?", parent=self):
    # User confirmed
    pass
```

---

## 3. Data Loading Patterns

### 3.1 Centralized Data Loader

Use `core/data_loader.py` for loading data files.

```python
from core.data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    excel_to_dataframe,
    DataLoadResult,
    LARGE_DATASET_THRESHOLD
)

result = csv_to_dataframe(file_path)
if result.success:
    df = result.data
    if result.warnings:
        # Handle warnings (truncation, encoding issues, etc.)
        pass
else:
    # Handle error
    error_msg = result.error
```

### 3.2 Background Loading

For large datasets, use background threads.

```python
from ui.managers.query_loader import BackgroundRowLoader

loader = BackgroundRowLoader(cursor, batch_size=1000)
loader.batch_loaded.connect(self._on_batch_loaded)
loader.loading_complete.connect(self._on_loading_complete)
loader.loading_error.connect(self._on_loading_error)
loader.start()
```

---

## 4. Error Handling Patterns

### 4.1 Standard Try-Except Pattern

```python
def _perform_operation(self):
    try:
        # Operation that might fail
        result = some_operation()

        # Success feedback
        DialogHelper.info("Operation completed.", parent=self)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        DialogHelper.error(
            "Operation failed.",
            parent=self,
            details=str(e)
        )
```

### 4.2 Validation Pattern

```python
def _delete_item(self):
    # Check selection
    if not self._current_item:
        DialogHelper.warning("Please select an item first.", parent=self)
        return

    # Confirm action
    if not DialogHelper.confirm("Delete this item?", parent=self):
        return

    # Perform action
    try:
        self._do_delete(self._current_item)
        DialogHelper.info("Item deleted.", parent=self)
        self.refresh()
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        DialogHelper.error("Failed to delete item.", parent=self, details=str(e))
```

### 4.3 BaseManagerView Helper

```python
# Using _check_item_selected helper
def _edit_item(self):
    if not self._check_item_selected("Please select an item.", "Edit"):
        return
    # Continue with edit...
```

---

## 5. Theme Integration

### 5.1 ThemeBridge

```python
from ui.core.theme_bridge import ThemeBridge

theme_bridge = ThemeBridge.get_instance()

# Get current colors
colors = theme_bridge.get_theme_colors()
bg_color = colors.get("panel_bg", "#2d2d2d")

# Register for theme changes
theme_bridge.register_observer(self._on_theme_changed)

def _on_theme_changed(self, theme_colors: dict):
    # Update widget styling
    pass
```

---

## 6. Workspace Integration

### 6.1 WorkspaceMenuBuilder

```python
from ui.widgets.workspace_menu_builder import build_workspace_menu

menu = build_workspace_menu(
    parent=self,
    item_id=item.id,
    get_item_workspaces=lambda: config_db.get_query_workspaces(item.id),
    add_to_workspace=lambda ws_id: config_db.add_query_to_workspace(ws_id, item.id),
    remove_from_workspace=lambda ws_id: config_db.remove_query_from_workspace(ws_id, item.id),
)
```

---

## 7. Database Schema Loading

### 7.1 SchemaLoaderFactory

```python
from database.schema_loaders import SchemaLoaderFactory, SchemaNode, SchemaNodeType

# Get appropriate loader
loader = SchemaLoaderFactory.get_loader(connection)

# Load schema
schema = loader.load_schema()

# Navigate schema tree
for database in schema.children:
    for table in database.children:
        for column in table.children:
            print(f"{database.name}.{table.name}.{column.name}")
```

---

## 8. File Structure Conventions

```
src/dataforge_studio/
├── core/                    # Core utilities (data_loader, etc.)
├── database/
│   ├── config_db.py        # Configuration database
│   ├── models/             # Dataclass models
│   └── schema_loaders/     # Database schema loaders
├── ui/
│   ├── core/               # UI core (theme, i18n, main_window)
│   ├── managers/           # Manager views
│   │   ├── base/          # Base classes
│   │   └── *.py           # Concrete managers
│   ├── widgets/           # Reusable widgets
│   ├── frames/            # Frame views
│   └── utils/             # UI utilities
├── utils/                  # General utilities
└── config/                # Configuration
```

---

## 9. Naming Conventions

- **Managers**: `*Manager` (e.g., `DatabaseManager`, `QueriesManager`)
- **Widgets**: Descriptive names (e.g., `PinnablePanel`, `CustomTreeView`)
- **Private methods**: `_method_name`
- **Signals**: `action_performed` (e.g., `query_saved`, `item_selected`)
- **Slots**: `_on_event_name` (e.g., `_on_tree_click`, `_on_item_selected`)

---

## 10. Best Practices

1. **Use DialogHelper** for all user-facing messages
2. **Use ToolbarBuilder** for creating toolbars
3. **Use FormBuilder** for detail forms
4. **Use ThemeBridge** for theme-aware styling
5. **Use centralized data_loader** for file loading
6. **Log errors** before showing dialogs
7. **Validate input** before performing actions
8. **Confirm destructive actions** with user
9. **Refresh views** after data changes
10. **Use lazy loading** for large data sets
