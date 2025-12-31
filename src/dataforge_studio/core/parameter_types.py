"""
Parameter Types - Type definitions for Script parameters and Job values.

This module defines the standardized parameter system:
- Scripts define parameters_schema (what parameters are needed)
- Jobs define parameters (actual values bound to the schema)

JSON Schema Format for Script.parameters_schema:
{
    "parameters": [
        {
            "name": "source_folder",           # Unique identifier (snake_case)
            "label": "Dossier source",         # Display label (i18n key or text)
            "type": "rootfolder",              # Parameter type (see ParameterType)
            "required": true,                  # Whether value is mandatory
            "description": "Dossier à traiter",# Help text
            "default": null,                   # Default value (optional)
            "options": {}                      # Type-specific options
        }
    ]
}

JSON Format for Job.parameters:
{
    "source_folder": "uuid-of-rootfolder",
    "pattern": "[d1]_[d2]*",
    "recursive": true
}
"""
import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ParameterType(Enum):
    """
    Available parameter types for Script parameters.

    Reference types (link to existing entities):
    - ROOTFOLDER: Reference to a RootFolder entity
    - DATABASE: Reference to a DatabaseConnection entity
    - QUERY: Reference to a saved Query
    - SCRIPT: Reference to another Script

    Basic types:
    - STRING: Free text input
    - NUMBER: Integer or decimal number
    - BOOLEAN: True/False checkbox
    - ENUM: Selection from predefined choices

    Special types:
    - PATH: File or folder path (with browse dialog)
    - PATTERN: Dispatch pattern like [d1]_[d2]*
    - DATE: Date picker
    - DATETIME: Date and time picker
    """
    # Reference types
    ROOTFOLDER = "rootfolder"
    DATABASE = "database"
    QUERY = "query"
    SCRIPT = "script"

    # Basic types
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"

    # Special types
    PATH = "path"
    PATTERN = "pattern"
    DATE = "date"
    DATETIME = "datetime"


# Type-specific options documentation
PARAMETER_OPTIONS = {
    ParameterType.STRING: {
        "min_length": "Minimum character count",
        "max_length": "Maximum character count",
        "multiline": "Allow multiple lines (textarea)",
        "placeholder": "Placeholder text",
    },
    ParameterType.NUMBER: {
        "min": "Minimum value",
        "max": "Maximum value",
        "step": "Increment step",
        "decimals": "Number of decimal places (0 for integer)",
    },
    ParameterType.ENUM: {
        "choices": "List of {value, label} dicts",
        "allow_multiple": "Allow selecting multiple values",
    },
    ParameterType.PATH: {
        "mode": "file|folder|save",
        "filter": "File filter (e.g., '*.csv;*.xlsx')",
        "relative_to": "Base path for relative paths",
    },
    ParameterType.PATTERN: {
        "example": "Example pattern for help text",
        "variables": "List of available variables like [d1], [d2]",
    },
    ParameterType.ROOTFOLDER: {
        "filter_type": "Optional filter by rootfolder type",
    },
    ParameterType.DATABASE: {
        "filter_driver": "Optional filter by driver type",
    },
    ParameterType.QUERY: {
        "filter_database": "Optional filter by database_id",
    },
}


def create_parameter(
    name: str,
    param_type: ParameterType,
    label: str,
    required: bool = True,
    description: str = "",
    default: Any = None,
    options: Optional[Dict] = None
) -> Dict:
    """
    Create a parameter definition.

    Args:
        name: Unique parameter identifier (snake_case)
        param_type: Parameter type (ParameterType enum)
        label: Display label
        required: Whether value is mandatory
        description: Help text
        default: Default value
        options: Type-specific options

    Returns:
        Parameter definition dict
    """
    return {
        "name": name,
        "type": param_type.value if isinstance(param_type, ParameterType) else param_type,
        "label": label,
        "required": required,
        "description": description,
        "default": default,
        "options": options or {}
    }


def create_parameters_schema(parameters: List[Dict]) -> str:
    """
    Create a parameters_schema JSON string from parameter definitions.

    Args:
        parameters: List of parameter dicts from create_parameter()

    Returns:
        JSON string for Script.parameters_schema
    """
    schema = {"parameters": parameters}
    return json.dumps(schema, ensure_ascii=False, indent=2)


def parse_parameters_schema(schema_json: str) -> List[Dict]:
    """
    Parse parameters_schema JSON string to list of parameter definitions.

    Supports two formats:
    1. New format: {"parameters": [{"name": "x", "type": "string", ...}]}
    2. Legacy format: {"param_name": {"type": "string", ...}}

    Args:
        schema_json: JSON string from Script.parameters_schema

    Returns:
        List of parameter definition dicts
    """
    if not schema_json:
        return []

    try:
        schema = json.loads(schema_json)

        # New format: has "parameters" key with list
        if "parameters" in schema and isinstance(schema["parameters"], list):
            return schema["parameters"]

        # Legacy format: dict of param_name -> param_definition
        # Convert to new format
        parameters = []
        for name, definition in schema.items():
            if isinstance(definition, dict):
                # Map legacy type names to new type names
                legacy_type_map = {
                    "file_root": "rootfolder",
                    "database_connection": "database",
                    "saved_query": "query",
                    "text": "string",
                    "integer": "number",
                    "float": "number",
                    "bool": "boolean",
                    "choice": "enum",
                    "file_path": "path",
                    "folder_path": "path",
                }

                param_type = definition.get("type", "string")
                param_type = legacy_type_map.get(param_type, param_type)

                param = {
                    "name": name,
                    "type": param_type,
                    "label": definition.get("label", name.replace("_", " ").title()),
                    "required": definition.get("required", True),
                    "description": definition.get("description", ""),
                    "default": definition.get("default"),
                    "options": {}
                }

                # Convert legacy options
                if "choices" in definition:
                    param["options"]["choices"] = definition["choices"]
                if "min" in definition:
                    param["options"]["min"] = definition["min"]
                if "max" in definition:
                    param["options"]["max"] = definition["max"]

                parameters.append(param)

        return parameters

    except json.JSONDecodeError as e:
        logger.error(f"Invalid parameters_schema JSON: {e}")
        return []


def parse_job_parameters(parameters_json: str) -> Dict[str, Any]:
    """
    Parse Job.parameters JSON string to dict.

    Args:
        parameters_json: JSON string from Job.parameters

    Returns:
        Dict mapping parameter names to values
    """
    if not parameters_json:
        return {}

    try:
        return json.loads(parameters_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid parameters JSON: {e}")
        return {}


def create_job_parameters(values: Dict[str, Any]) -> str:
    """
    Create Job.parameters JSON string from values dict.

    Args:
        values: Dict mapping parameter names to values

    Returns:
        JSON string for Job.parameters
    """
    return json.dumps(values, ensure_ascii=False, indent=2)


def validate_parameter_value(
    value: Any,
    param_def: Dict,
    context: Optional[Dict] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a parameter value against its definition.

    Args:
        value: The value to validate
        param_def: Parameter definition dict
        context: Optional context with repositories for reference validation

    Returns:
        Tuple of (is_valid, error_message or None)
    """
    param_type = param_def.get("type", "string")
    required = param_def.get("required", True)
    options = param_def.get("options", {})
    name = param_def.get("name", "parameter")

    # Check required
    if required and (value is None or value == ""):
        return False, f"Le paramètre '{name}' est requis"

    # Skip validation if not required and empty
    if not required and (value is None or value == ""):
        return True, None

    # Type-specific validation
    if param_type == ParameterType.NUMBER.value:
        try:
            num_value = float(value)
            if "min" in options and num_value < options["min"]:
                return False, f"La valeur doit être >= {options['min']}"
            if "max" in options and num_value > options["max"]:
                return False, f"La valeur doit être <= {options['max']}"
        except (ValueError, TypeError):
            return False, f"'{value}' n'est pas un nombre valide"

    elif param_type == ParameterType.STRING.value:
        str_value = str(value)
        if "min_length" in options and len(str_value) < options["min_length"]:
            return False, f"Minimum {options['min_length']} caractères"
        if "max_length" in options and len(str_value) > options["max_length"]:
            return False, f"Maximum {options['max_length']} caractères"

    elif param_type == ParameterType.BOOLEAN.value:
        if not isinstance(value, bool) and value not in (0, 1, "true", "false", "True", "False"):
            return False, "La valeur doit être vrai ou faux"

    elif param_type == ParameterType.ENUM.value:
        choices = options.get("choices", [])
        valid_values = [c.get("value") if isinstance(c, dict) else c for c in choices]

        if options.get("allow_multiple"):
            if isinstance(value, list):
                for v in value:
                    if v not in valid_values:
                        return False, f"Valeur '{v}' non autorisée"
            else:
                return False, "Une liste de valeurs est attendue"
        else:
            if value not in valid_values:
                return False, f"Valeur '{value}' non autorisée"

    elif param_type == ParameterType.PATTERN.value:
        # Basic pattern validation
        str_value = str(value)
        if not str_value:
            return False, "Le pattern ne peut pas être vide"
        # Pattern should contain at least one variable or be a simple separator
        # More complex validation can be done at runtime

    elif param_type in (ParameterType.ROOTFOLDER.value, ParameterType.DATABASE.value,
                         ParameterType.QUERY.value, ParameterType.SCRIPT.value):
        # Reference types - validate UUID format
        if not value or not isinstance(value, str):
            return False, f"Référence invalide pour '{name}'"

        # If context provided, validate existence
        if context:
            # This would check against repositories
            # Implementation depends on available context
            pass

    return True, None


def validate_job_parameters(
    job_parameters: Dict[str, Any],
    schema_parameters: List[Dict],
    context: Optional[Dict] = None
) -> Tuple[bool, List[str]]:
    """
    Validate all Job parameters against Script schema.

    Args:
        job_parameters: Dict from Job.parameters
        schema_parameters: List from Script.parameters_schema
        context: Optional context for reference validation

    Returns:
        Tuple of (all_valid, list of error messages)
    """
    errors = []

    for param_def in schema_parameters:
        name = param_def.get("name")
        value = job_parameters.get(name)

        is_valid, error = validate_parameter_value(value, param_def, context)
        if not is_valid:
            errors.append(error)

    return len(errors) == 0, errors


def get_default_values(schema_parameters: List[Dict]) -> Dict[str, Any]:
    """
    Get default values for all parameters in schema.

    Args:
        schema_parameters: List from Script.parameters_schema

    Returns:
        Dict mapping parameter names to default values
    """
    defaults = {}
    for param_def in schema_parameters:
        name = param_def.get("name")
        default = param_def.get("default")
        param_type = param_def.get("type", "string")

        if default is not None:
            defaults[name] = default
        else:
            # Type-specific defaults
            if param_type == ParameterType.BOOLEAN.value:
                defaults[name] = False
            elif param_type == ParameterType.NUMBER.value:
                defaults[name] = 0
            elif param_type == ParameterType.STRING.value:
                defaults[name] = ""
            else:
                defaults[name] = None

    return defaults
