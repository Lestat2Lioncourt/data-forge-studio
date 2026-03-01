"""
Job model - Job definition (atomic or workflow)

A Job is an instance of a Script with concrete parameter values:
- script_id: Reference to the Script template
- parameters: JSON with actual values for the Script's parameters_schema

Jobs can also be workflows containing other jobs.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid


@dataclass
class Job:
    """
    Job = Can be either:
    1. Atomic job: Script instance with configured parameters
    2. Workflow job: Container of other jobs

    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Description of what this job does
        job_type: 'atomic' or 'workflow'
        script_id: Reference to Script (for atomic jobs)
        project_id: Optional project grouping
        parent_job_id: Parent workflow job (if nested)
        previous_job_id: Previous job in sequence (for ordering)
        parameters: JSON string with concrete parameter values
        enabled: Whether job is active
        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_run_at: Last execution timestamp
    """
    id: str
    name: str
    description: str
    job_type: str
    script_id: str = None
    project_id: str = None
    parent_job_id: str = None
    previous_job_id: str = None
    parameters: str = None
    enabled: bool = True
    created_at: str = None
    updated_at: str = None
    last_run_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def get_parameters(self) -> Dict[str, Any]:
        """
        Parse parameters JSON and return values dict.

        Returns:
            Dict mapping parameter names to values
        """
        from ...core.parameter_types import parse_job_parameters
        return parse_job_parameters(self.parameters)

    def set_parameters(self, values: Dict[str, Any]) -> None:
        """
        Set parameters from values dict.

        Args:
            values: Dict mapping parameter names to values
        """
        from ...core.parameter_types import create_job_parameters
        self.parameters = create_job_parameters(values)
        self.updated_at = datetime.now().isoformat()

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """
        Get a single parameter value.

        Args:
            name: Parameter name
            default: Default value if not found

        Returns:
            Parameter value or default
        """
        return self.get_parameters().get(name, default)

    def set_parameter(self, name: str, value: Any):
        """
        Set a single parameter value.

        Args:
            name: Parameter name
            value: Parameter value
        """
        params = self.get_parameters()
        params[name] = value
        self.set_parameters(params)

    def validate_parameters(self, script: 'Script') -> Tuple[bool, List[str]]:
        """
        Validate job parameters against script schema.

        Args:
            script: The Script this job is based on

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        from ...core.parameter_types import validate_job_parameters
        return validate_job_parameters(
            self.get_parameters(),
            script.get_parameters()
        )

    def has_parameters(self) -> bool:
        """
        Check if job has any parameters defined.

        Returns:
            True if parameters JSON contains values
        """
        return len(self.get_parameters()) > 0

    def is_script_job(self) -> bool:
        """
        Check if this is a script job (has script_id).

        Returns:
            True if script job
        """
        return self.job_type == "script" and self.script_id is not None

    def is_workflow(self) -> bool:
        """
        Check if this is a workflow job.

        Returns:
            True if workflow job
        """
        return self.job_type == "workflow"

    # Alias for backward compatibility
    is_atomic = is_script_job

    def mark_run(self):
        """Update last_run_at to current time."""
        self.last_run_at = datetime.now().isoformat()
