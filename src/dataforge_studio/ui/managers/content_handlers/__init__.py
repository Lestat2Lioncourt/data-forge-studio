"""
Content Handlers - Modular content display handlers for ResourcesManager

Each handler manages a specific type of content display:
- FileContentHandler: CSV, Excel, JSON, text files
- ImageContentHandler: Image preview and management
"""

from .file_content_handler import FileContentHandler
from .image_content_handler import ImageContentHandler

__all__ = [
    "FileContentHandler",
    "ImageContentHandler",
]
