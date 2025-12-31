"""
Core module - Shared data loading and viewing functions.

This module implements the DataFrame-Pivot pattern:
- data_loader: Load heterogeneous sources into pandas DataFrame
- data_viewer: Display DataFrame in Qt widgets
- dataframe_model: High-performance Qt model for large datasets
- parameter_types: Script/Job parameter type system

Architecture:
    Sources (CSV, JSON, Excel, SQL)
           ↓
    data_loader.py → DataFrame (pivot)
           ↓
    data_viewer.py → Qt Widgets (TreeView, TableView, ComboBox)
"""

from .data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    excel_to_dataframe,
    query_to_dataframe,
    DataLoadResult,
    LARGE_DATASET_THRESHOLD,
)

from .dataframe_model import DataFrameTableModel

from .data_viewer import (
    dataframe_to_tableview,
    dataframe_to_datagridview,
    dataframe_to_treeview,
    dataframe_to_combobox,
)

from .parameter_types import (
    ParameterType,
    create_parameter,
    create_parameters_schema,
    parse_parameters_schema,
    parse_job_parameters,
    create_job_parameters,
    validate_parameter_value,
    validate_job_parameters,
    get_default_values,
)

from .script_schemas import (
    BUILTIN_SCRIPTS,
    get_builtin_script_info,
    get_dispatch_schema,
    get_import_csv_schema,
    get_export_query_schema,
    get_backup_schema,
)

__all__ = [
    # Data loading
    'csv_to_dataframe',
    'json_to_dataframe',
    'excel_to_dataframe',
    'query_to_dataframe',
    'DataLoadResult',
    'LARGE_DATASET_THRESHOLD',
    # Model
    'DataFrameTableModel',
    # Data viewing
    'dataframe_to_tableview',
    'dataframe_to_datagridview',
    'dataframe_to_treeview',
    'dataframe_to_combobox',
    # Parameter types
    'ParameterType',
    'create_parameter',
    'create_parameters_schema',
    'parse_parameters_schema',
    'parse_job_parameters',
    'create_job_parameters',
    'validate_parameter_value',
    'validate_job_parameters',
    'get_default_values',
    # Script schemas
    'BUILTIN_SCRIPTS',
    'get_builtin_script_info',
    'get_dispatch_schema',
    'get_import_csv_schema',
    'get_export_query_schema',
    'get_backup_schema',
]
