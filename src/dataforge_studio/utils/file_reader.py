"""
File Reader - Utility to read various file formats
"""

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def read_file_content(file_path: Path) -> Optional[str]:
    """
    Read file content as string.

    Args:
        file_path: Path to the file

    Returns:
        File content as string, or None if error
    """
    try:
        # Try UTF-8 first
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except:
                    continue

            # If all fail, return None
            logger.warning(f"Could not decode file {file_path} with common encodings")
            return None

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None
