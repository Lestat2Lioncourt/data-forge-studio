"""
Job model - Job definition (atomic or workflow)
"""
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class Job:
    """
    Job = Can be either:
    1. Atomic job: Script instance with configured parameters
    2. Workflow job: Container of other jobs
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
