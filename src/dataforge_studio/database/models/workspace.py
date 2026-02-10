"""
Project/Workspace model - Project/Workspace configuration for organizing resources
"""
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class Project:
    """Project/Workspace configuration for organizing databases, queries, and files"""
    id: str
    name: str
    description: str
    is_default: bool = False
    auto_connect: bool = False  # Auto-connect all resources on startup
    created_at: str = None
    updated_at: str = None
    last_used_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


# Alias for Workspace (same as Project for backward compatibility)
Workspace = Project
