"""
Script to clean up duplicate FileRoot entries created for subfolders

This script identifies FileRoot entries that are subfolders of other FileRoots
and removes them from the database. These were incorrectly created when attaching
subfolders to projects.
"""

from pathlib import Path
from src.database.config_db import config_db
from src.utils.logger import logger


def find_duplicate_file_roots():
    """
    Find FileRoot entries that are subfolders of other FileRoots

    Returns:
        List of FileRoot objects that should be deleted
    """
    all_roots = config_db.get_all_file_roots()
    duplicates = []

    for i, root1 in enumerate(all_roots):
        path1 = Path(root1.path)

        for j, root2 in enumerate(all_roots):
            if i == j:
                continue

            path2 = Path(root2.path)

            # Check if path1 is a subfolder of path2
            try:
                path1.relative_to(path2)
                # path1 is a subfolder of path2
                duplicates.append(root1)
                break
            except ValueError:
                # Not a subfolder
                continue

    return duplicates


def cleanup_duplicate_file_roots(dry_run=True):
    """
    Clean up duplicate FileRoot entries

    Args:
        dry_run: If True, only print what would be deleted without actually deleting
    """
    logger.info("Starting cleanup of duplicate FileRoot entries...")

    duplicates = find_duplicate_file_roots()

    if not duplicates:
        logger.info("No duplicate FileRoot entries found!")
        return

    logger.info(f"Found {len(duplicates)} duplicate FileRoot entries:")

    for dup in duplicates:
        logger.info(f"  - {dup.path} (id: {dup.id})")

        # Check if this FileRoot is used in any projects
        projects = config_db.get_file_root_projects(dup.id)
        if projects:
            logger.info(f"    Used in {len(projects)} project(s): {[p.name for p in projects]}")

    if dry_run:
        logger.info("\nDRY RUN MODE - No changes made.")
        logger.info("Run with dry_run=False to actually delete these entries.")
        return

    # Actually delete the duplicates
    logger.info("\nDeleting duplicate FileRoot entries...")
    for dup in duplicates:
        success = config_db.delete_file_root(dup.id)
        if success:
            logger.important(f"Deleted FileRoot: {dup.path}")
        else:
            logger.error(f"Failed to delete FileRoot: {dup.path}")

    logger.info("Cleanup complete!")


if __name__ == "__main__":
    print("=" * 70)
    print("FileRoot Cleanup Script")
    print("=" * 70)
    print()
    print("This script will identify and remove FileRoot entries that are")
    print("subfolders of other FileRoots. These were incorrectly created when")
    print("attaching subfolders to projects.")
    print()
    print("Running in DRY RUN mode first to show what would be deleted...")
    print()

    # First run in dry-run mode
    cleanup_duplicate_file_roots(dry_run=True)

    print()
    print("=" * 70)
    response = input("\nDo you want to proceed with the cleanup? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        print("\nProceeding with cleanup...")
        cleanup_duplicate_file_roots(dry_run=False)
    else:
        print("\nCleanup cancelled.")
