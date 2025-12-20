"""
Image Repository - CRUD operations for images, rootfolders, categories, and tags.
"""
import sqlite3
from typing import List, Optional
from datetime import datetime
import uuid

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import ImageRootfolder, SavedImage


class ImageRootfolderRepository(BaseRepository[ImageRootfolder]):
    """Repository for ImageRootfolder entities."""

    @property
    def table_name(self) -> str:
        return "image_rootfolders"

    def _row_to_model(self, row: sqlite3.Row) -> ImageRootfolder:
        return ImageRootfolder(**dict(row))

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO image_rootfolders
            (id, path, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE image_rootfolders
            SET path = ?, name = ?, description = ?, updated_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: ImageRootfolder) -> tuple:
        return (model.id, model.path, model.name,
                model.description, model.created_at, model.updated_at)

    def _model_to_update_tuple(self, model: ImageRootfolder) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.path, model.name, model.description,
                model.updated_at, model.id)


class SavedImageRepository(BaseRepository[SavedImage]):
    """Repository for SavedImage entities."""

    @property
    def table_name(self) -> str:
        return "saved_images"

    def _row_to_model(self, row: sqlite3.Row) -> SavedImage:
        return SavedImage(**dict(row))

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO saved_images
            (id, name, filepath, rootfolder_id, physical_path, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE saved_images
            SET name = ?, filepath = ?, rootfolder_id = ?, physical_path = ?,
                description = ?, updated_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: SavedImage) -> tuple:
        return (model.id, model.name, model.filepath, model.rootfolder_id,
                model.physical_path, model.description, model.created_at, model.updated_at)

    def _model_to_update_tuple(self, model: SavedImage) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.filepath, model.rootfolder_id, model.physical_path,
                model.description, model.updated_at, model.id)

    def get_all_images(self) -> List[SavedImage]:
        """Get all saved images ordered by path and name."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_images ORDER BY physical_path, name")
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_by_rootfolder(self, rootfolder_id: str) -> List[SavedImage]:
        """Get all images in a rootfolder."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM saved_images
                WHERE rootfolder_id = ?
                ORDER BY physical_path, name
            """, (rootfolder_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_by_physical_path(self, rootfolder_id: str, physical_path: str) -> List[SavedImage]:
        """Get all images in a specific physical path within a rootfolder."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM saved_images
                WHERE rootfolder_id = ? AND physical_path = ?
                ORDER BY name
            """, (rootfolder_id, physical_path))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_by_filepath(self, filepath: str) -> Optional[SavedImage]:
        """Get a saved image by filepath."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_images WHERE filepath = ?", (filepath,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None

    def add_image(self, name: str, filepath: str, rootfolder_id: str = None,
                  physical_path: str = "", description: str = "") -> Optional[str]:
        """
        Add a new saved image.

        Returns:
            Image ID if successful, None otherwise
        """
        try:
            image = SavedImage(
                id=str(uuid.uuid4()),
                name=name,
                filepath=filepath,
                rootfolder_id=rootfolder_id,
                physical_path=physical_path,
                description=description
            )

            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(self._get_insert_sql(), self._model_to_insert_tuple(image))

            return image.id
        except Exception:
            return None

    def delete_by_rootfolder(self, rootfolder_id: str) -> int:
        """Delete all images in a rootfolder. Returns count of deleted images."""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM saved_images WHERE rootfolder_id = ?",
                    (rootfolder_id,)
                )
                count = cursor.fetchone()[0]

            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM saved_images WHERE rootfolder_id = ?",
                    (rootfolder_id,)
                )

            return count
        except Exception:
            return 0

    def get_physical_paths(self, rootfolder_id: str) -> List[str]:
        """Get all unique physical paths within a rootfolder."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT physical_path FROM saved_images
                WHERE rootfolder_id = ?
                ORDER BY physical_path
            """, (rootfolder_id,))
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    # ==================== Categories ====================

    def get_categories(self, image_id: str) -> List[str]:
        """Get all logical categories for an image."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category_name FROM image_categories
                WHERE image_id = ?
                ORDER BY category_name
            """, (image_id,))
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def get_all_category_names(self) -> List[str]:
        """Get all unique logical category names across all images."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT category_name FROM image_categories
                ORDER BY category_name
            """)
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def get_by_category(self, category_name: str) -> List[SavedImage]:
        """Get all images in a logical category."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT si.* FROM saved_images si
                INNER JOIN image_categories ic ON si.id = ic.image_id
                WHERE ic.category_name = ?
                ORDER BY si.name
            """, (category_name,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def add_category(self, image_id: str, category_name: str) -> bool:
        """Add a logical category to an image."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO image_categories (image_id, category_name, created_at)
                    VALUES (?, ?, ?)
                """, (image_id, category_name, datetime.now().isoformat()))
            return True
        except Exception:
            return False

    def remove_category(self, image_id: str, category_name: str) -> bool:
        """Remove a logical category from an image."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM image_categories
                    WHERE image_id = ? AND category_name = ?
                """, (image_id, category_name))
            return True
        except Exception:
            return False

    def set_categories(self, image_id: str, category_names: List[str]) -> bool:
        """Set all logical categories for an image (replaces existing)."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()

                # Remove existing categories
                cursor.execute("DELETE FROM image_categories WHERE image_id = ?", (image_id,))

                # Add new categories
                now = datetime.now().isoformat()
                for cat_name in category_names:
                    if cat_name.strip():
                        cursor.execute("""
                            INSERT INTO image_categories (image_id, category_name, created_at)
                            VALUES (?, ?, ?)
                        """, (image_id, cat_name.strip(), now))
            return True
        except Exception:
            return False

    # ==================== Tags ====================

    def get_tags(self, image_id: str) -> List[str]:
        """Get all tags for an image."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tag_name FROM image_tags
                WHERE image_id = ?
                ORDER BY tag_name
            """, (image_id,))
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def get_all_tag_names(self) -> List[str]:
        """Get all unique tag names across all images."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT tag_name FROM image_tags
                ORDER BY tag_name
            """)
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def get_by_tag(self, tag_name: str) -> List[SavedImage]:
        """Get all images with a specific tag."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT si.* FROM saved_images si
                INNER JOIN image_tags it ON si.id = it.image_id
                WHERE it.tag_name = ?
                ORDER BY si.name
            """, (tag_name,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def add_tag(self, image_id: str, tag_name: str) -> bool:
        """Add a tag to an image."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO image_tags (image_id, tag_name, created_at)
                    VALUES (?, ?, ?)
                """, (image_id, tag_name.strip().lower(), datetime.now().isoformat()))
            return True
        except Exception:
            return False

    def remove_tag(self, image_id: str, tag_name: str) -> bool:
        """Remove a tag from an image."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM image_tags
                    WHERE image_id = ? AND tag_name = ?
                """, (image_id, tag_name))
            return True
        except Exception:
            return False

    def set_tags(self, image_id: str, tag_names: List[str]) -> bool:
        """Set all tags for an image (replaces existing)."""
        try:
            with self.pool.transaction() as conn:
                cursor = conn.cursor()

                # Remove existing tags
                cursor.execute("DELETE FROM image_tags WHERE image_id = ?", (image_id,))

                # Add new tags (normalized to lowercase)
                now = datetime.now().isoformat()
                for tag in tag_names:
                    tag_clean = tag.strip().lower()
                    if tag_clean:
                        cursor.execute("""
                            INSERT INTO image_tags (image_id, tag_name, created_at)
                            VALUES (?, ?, ?)
                        """, (image_id, tag_clean, now))
            return True
        except Exception:
            return False

    # ==================== Search ====================

    def search(self, query: str, search_name: bool = True,
               search_categories: bool = True, search_tags: bool = True) -> List[SavedImage]:
        """
        Search images by name, categories, and/or tags.

        Args:
            query: Search query string
            search_name: Include filename in search
            search_categories: Include logical categories in search
            search_tags: Include tags in search

        Returns:
            List of matching SavedImage objects (deduplicated)
        """
        if not query.strip():
            return []

        query_pattern = f"%{query.strip()}%"
        image_ids = set()

        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Search in name
            if search_name:
                cursor.execute("""
                    SELECT id FROM saved_images
                    WHERE name LIKE ? OR filepath LIKE ?
                """, (query_pattern, query_pattern))
                for row in cursor.fetchall():
                    image_ids.add(row[0])

            # Search in categories
            if search_categories:
                cursor.execute("""
                    SELECT DISTINCT image_id FROM image_categories
                    WHERE category_name LIKE ?
                """, (query_pattern,))
                for row in cursor.fetchall():
                    image_ids.add(row[0])

            # Search in tags
            if search_tags:
                cursor.execute("""
                    SELECT DISTINCT image_id FROM image_tags
                    WHERE tag_name LIKE ?
                """, (query_pattern.lower(),))
                for row in cursor.fetchall():
                    image_ids.add(row[0])

            # Fetch full image objects
            if not image_ids:
                return []

            placeholders = ",".join("?" * len(image_ids))
            cursor.execute(f"""
                SELECT * FROM saved_images
                WHERE id IN ({placeholders})
                ORDER BY name
            """, list(image_ids))
            rows = cursor.fetchall()

            return [self._row_to_model(row) for row in rows]
