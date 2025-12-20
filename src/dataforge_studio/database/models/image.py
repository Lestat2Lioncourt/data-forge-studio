"""
Image models - ImageRootfolder and SavedImage
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import uuid


@dataclass
class ImageRootfolder:
    """Image root folder for automatic image scanning"""
    id: str
    path: str
    name: str = None
    description: str = ""
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            self.name = Path(self.path).name if self.path else "Unnamed"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


@dataclass
class SavedImage:
    """
    Saved image reference for image library.

    An image has:
    - Physical location: rootfolder + physical_path (subfolder within rootfolder)
    - Logical categories: many-to-many (stored in image_categories table)
    - Tags: many-to-many (stored in image_tags table)
    """
    id: str
    name: str
    filepath: str  # Absolute path to the image file
    rootfolder_id: str = None  # FK to image_rootfolders (None if manually added)
    physical_path: str = ""  # Relative path within rootfolder (e.g., "Screenshots/2024")
    description: str = ""
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
