"""
Image Scanner - Scans a folder for images and adds them to the image library
"""

from pathlib import Path
from typing import List, Callable, Optional
import logging

from ..database.config_db import get_config_db, ImageRootfolder, SavedImage

logger = logging.getLogger(__name__)

# Supported image extensions
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg",
    ".tiff", ".tif", ".raw", ".psd", ".ai", ".eps"
}


def is_image_file(path: Path) -> bool:
    """Check if a file is a supported image type."""
    return path.suffix.lower() in IMAGE_EXTENSIONS


def scan_folder_for_images(folder_path: Path) -> List[Path]:
    """
    Recursively scan a folder for image files.

    Args:
        folder_path: Path to the folder to scan

    Returns:
        List of Path objects for all image files found
    """
    if not folder_path.exists() or not folder_path.is_dir():
        return []

    images = []
    try:
        for entry in folder_path.rglob("*"):
            if entry.is_file() and is_image_file(entry):
                images.append(entry)
    except PermissionError as e:
        logger.warning(f"Permission denied scanning {folder_path}: {e}")
    except Exception as e:
        logger.error(f"Error scanning {folder_path}: {e}")

    return images


def get_physical_path(image_path: Path, rootfolder_path: Path) -> str:
    """
    Calculate the physical path (subfolder) relative to the rootfolder.

    Args:
        image_path: Absolute path to the image file
        rootfolder_path: Absolute path to the rootfolder

    Returns:
        Relative path string (e.g., "Screenshots/2024") or "" if at root
    """
    try:
        relative = image_path.parent.relative_to(rootfolder_path)
        # Convert to forward slashes for consistency
        return str(relative).replace("\\", "/") if str(relative) != "." else ""
    except ValueError:
        return ""


class ImageScanner:
    """
    Scans a folder and adds images to the database.
    Supports progress callbacks for UI integration.
    """

    def __init__(self, rootfolder: ImageRootfolder):
        """
        Initialize scanner for a rootfolder.

        Args:
            rootfolder: ImageRootfolder object to scan
        """
        self.rootfolder = rootfolder
        self.rootfolder_path = Path(rootfolder.path)
        self.config_db = get_config_db()

        # Statistics
        self.total_found = 0
        self.added = 0
        self.skipped = 0
        self.errors = 0

    def scan(self, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> dict:
        """
        Scan the rootfolder and add images to the database.

        Args:
            progress_callback: Optional callback function(current, total, message)
                              Called for each image processed

        Returns:
            Dictionary with statistics:
            - total_found: Number of image files found
            - added: Number of new images added
            - skipped: Number of images already in database
            - errors: Number of errors encountered
        """
        if not self.rootfolder_path.exists():
            logger.error(f"Rootfolder does not exist: {self.rootfolder_path}")
            return {"total_found": 0, "added": 0, "skipped": 0, "errors": 1}

        # Phase 1: Discover all images
        if progress_callback:
            progress_callback(0, 0, "Scanning for images...")

        image_files = scan_folder_for_images(self.rootfolder_path)
        self.total_found = len(image_files)

        if self.total_found == 0:
            logger.info(f"No images found in {self.rootfolder_path}")
            return {"total_found": 0, "added": 0, "skipped": 0, "errors": 0}

        logger.info(f"Found {self.total_found} images in {self.rootfolder_path}")

        # Phase 2: Add images to database
        for i, image_path in enumerate(image_files):
            if progress_callback:
                progress_callback(i + 1, self.total_found, f"Processing: {image_path.name}")

            try:
                self._process_image(image_path)
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                self.errors += 1

        result = {
            "total_found": self.total_found,
            "added": self.added,
            "skipped": self.skipped,
            "errors": self.errors
        }

        logger.info(f"Scan complete: {result}")
        return result

    def _process_image(self, image_path: Path):
        """Process a single image file."""
        filepath_str = str(image_path)

        # Check if image already exists in database
        existing = self.config_db.get_saved_image_by_filepath(filepath_str)
        if existing:
            self.skipped += 1
            return

        # Calculate physical path
        physical_path = get_physical_path(image_path, self.rootfolder_path)

        # Add to database
        image_id = self.config_db.add_saved_image(
            name=image_path.stem,  # Filename without extension
            filepath=filepath_str,
            rootfolder_id=self.rootfolder.id,
            physical_path=physical_path,
            description=""
        )

        if image_id:
            self.added += 1
        else:
            self.errors += 1

    def rescan(self, progress_callback: Optional[Callable[[int, int, str], None]] = None,
               remove_missing: bool = True) -> dict:
        """
        Rescan the rootfolder, adding new images and optionally removing missing ones.

        Args:
            progress_callback: Optional callback function(current, total, message)
            remove_missing: If True, remove database entries for files that no longer exist

        Returns:
            Dictionary with statistics including 'removed' count
        """
        # First, check for missing files if requested
        removed = 0
        if remove_missing:
            if progress_callback:
                progress_callback(0, 0, "Checking for missing files...")

            existing_images = self.config_db.get_images_by_rootfolder(self.rootfolder.id)
            for img in existing_images:
                if not Path(img.filepath).exists():
                    self.config_db.delete_saved_image(img.id)
                    removed += 1
                    logger.info(f"Removed missing image: {img.filepath}")

        # Then scan for new images
        result = self.scan(progress_callback)
        result["removed"] = removed

        return result


def create_rootfolder_and_scan(path: str, name: str = None, description: str = "",
                                progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Optional[ImageRootfolder]:
    """
    Create a new image rootfolder and scan it for images.

    Args:
        path: Path to the folder
        name: Display name (defaults to folder name)
        description: Optional description
        progress_callback: Optional callback function(current, total, message)

    Returns:
        ImageRootfolder object if successful, None otherwise
    """
    folder_path = Path(path)

    if not folder_path.exists():
        logger.error(f"Path does not exist: {path}")
        return None

    if not folder_path.is_dir():
        logger.error(f"Path is not a directory: {path}")
        return None

    config_db = get_config_db()

    # Create rootfolder
    rootfolder = ImageRootfolder(
        id="",  # Will be generated
        path=str(folder_path),
        name=name or folder_path.name,
        description=description
    )

    if not config_db.add_image_rootfolder(rootfolder):
        logger.error(f"Failed to add rootfolder: {path}")
        return None

    logger.info(f"Created rootfolder: {rootfolder.name} ({rootfolder.id})")

    # Scan for images
    scanner = ImageScanner(rootfolder)
    result = scanner.scan(progress_callback)

    logger.info(f"Scan result: {result}")

    return rootfolder
