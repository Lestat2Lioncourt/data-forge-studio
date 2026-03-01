"""
Core module - Shared data loading, parameter types, and script schemas.

- data_loader: Load heterogeneous sources into pandas DataFrame
- parameter_types: Script/Job parameter type system
- script_schemas: Built-in script definitions

Note: dataframe_model.py and data_viewer.py are legacy modules
      superseded by ui/widgets/dataframe_model.py and custom_datagridview.py.
"""

from .data_loader import (
    csv_to_dataframe,
    json_to_dataframe,
    excel_to_dataframe,
    query_to_dataframe,
    DataLoadResult,
    LARGE_DATASET_THRESHOLD,
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
