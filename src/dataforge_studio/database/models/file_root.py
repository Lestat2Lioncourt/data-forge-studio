"""
FileRoot model - File root directory configuration
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import uuid


@dataclass
class FileRoot:
    """File root directory configuration"""
    id: str
    path: str
    name: str = None  # Display name for the root folder
    description: str = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            # Default name from path if not provided
            self.name = Path(self.path).name if self.path else "Unnamed"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
