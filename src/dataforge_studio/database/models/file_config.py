"""
FileConfig model - File configuration
"""
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class FileConfig:
    """File configuration"""
    id: str
    name: str
    location: str
    description: str
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
