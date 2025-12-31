"""
Script model - Script definition (generic, reusable)

A Script is a reusable template that defines:
- script_type: The type of script (e.g., 'dispatch', 'import', 'transform')
- parameters_schema: JSON schema defining what parameters the script needs

Jobs instantiate Scripts with concrete parameter values.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class Script:
    """
    Script definition (generic, reusable template).

    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Description of what the script does
        script_type: Type identifier (e.g., 'dispatch', 'import')
        parameters_schema: JSON string defining required parameters
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    name: str
    description: str
    script_type: str
    parameters_schema: str
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def get_parameters(self) -> List[Dict]:
        """
        Parse parameters_schema and return list of parameter definitions.

        Returns:
            List of parameter definition dicts
        """
        from ...core.parameter_types import parse_parameters_schema
        return parse_parameters_schema(self.parameters_schema)

    def set_parameters(self, parameters: List[Dict]):
        """
        Set parameters_schema from list of parameter definitions.

        Args:
            parameters: List of parameter dicts
        """
        from ...core.parameter_types import create_parameters_schema
        self.parameters_schema = create_parameters_schema(parameters)
        self.updated_at = datetime.now().isoformat()

    def get_parameter_names(self) -> List[str]:
        """
        Get list of parameter names defined in schema.

        Returns:
            List of parameter names
        """
        return [p.get("name") for p in self.get_parameters()]

    def get_required_parameters(self) -> List[Dict]:
        """
        Get only required parameters.

        Returns:
            List of required parameter definitions
        """
        return [p for p in self.get_parameters() if p.get("required", True)]

    def get_default_values(self) -> Dict[str, Any]:
        """
        Get default values for all parameters.

        Returns:
            Dict mapping parameter names to default values
        """
        from ...core.parameter_types import get_default_values
        return get_default_values(self.get_parameters())

    def has_parameters(self) -> bool:
        """
        Check if script has any defined parameters.

        Returns:
            True if parameters_schema contains parameters
        """
        return len(self.get_parameters()) > 0
