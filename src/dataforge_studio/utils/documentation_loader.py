"""
Documentation Loader - Load and parse markdown documentation files.

Reads documentation structure from docs/help_manifest.yaml
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import yaml

import logging
logger = logging.getLogger(__name__)


@dataclass
class DocEntry:
    """Represents a documentation entry."""
    id: str
    title: str
    path: Path
    category: str = "General"
    content: Optional[str] = None


@dataclass
class DocCategory:
    """Represents a documentation category."""
    name: str
    icon: str = "file.png"
    entries: List[DocEntry] = field(default_factory=list)


class DocumentationLoader:
    """
    Loads documentation from markdown files based on a YAML manifest.

    The manifest file (docs/help_manifest.yaml) defines:
    - Categories and their order
    - Which documents to include
    - Icons for each category
    """

    MANIFEST_FILE = "help_manifest.yaml"

    def __init__(self, docs_path: Optional[Path] = None):
        """
        Initialize the documentation loader.

        Args:
            docs_path: Path to docs directory. Auto-detected if None.
        """
        if docs_path is None:
            # Auto-detect docs path relative to package
            package_root = Path(__file__).parent.parent.parent.parent
            docs_path = package_root / "docs"

        self.docs_path = docs_path
        self._categories: List[DocCategory] = []
        self._entries_by_id: Dict[str, DocEntry] = {}
        self._loaded = False

    def load(self) -> None:
        """Load documentation entries from the manifest file."""
        manifest_path = self.docs_path / self.MANIFEST_FILE

        if not manifest_path.exists():
            logger.warning(f"Documentation manifest not found: {manifest_path}")
            self._load_fallback()
            return

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)

            self._parse_manifest(manifest)
            self._loaded = True
            logger.debug(f"Loaded {len(self._entries_by_id)} documentation entries from manifest")

        except Exception as e:
            logger.error(f"Error loading documentation manifest: {e}")
            self._load_fallback()

    def _parse_manifest(self, manifest: dict) -> None:
        """Parse the manifest structure."""
        self._categories.clear()
        self._entries_by_id.clear()

        categories_data = manifest.get("categories", [])

        for cat_data in categories_data:
            cat_name = cat_data.get("name", "General")
            cat_icon = cat_data.get("icon", "file.png")
            docs_list = cat_data.get("docs", [])

            category = DocCategory(name=cat_name, icon=cat_icon)

            for doc_filename in docs_list:
                doc_path = self.docs_path / doc_filename

                if not doc_path.exists():
                    logger.warning(f"Documentation file not found: {doc_path}")
                    continue

                entry = self._create_entry(doc_path, cat_name)
                if entry:
                    category.entries.append(entry)
                    self._entries_by_id[entry.id] = entry

            if category.entries:
                self._categories.append(category)

    def _load_fallback(self) -> None:
        """Fallback: load all markdown files without manifest."""
        self._categories.clear()
        self._entries_by_id.clear()

        if not self.docs_path.exists():
            logger.warning(f"Documentation path not found: {self.docs_path}")
            return

        category = DocCategory(name="Documentation", icon="file.png")

        for md_file in sorted(self.docs_path.glob("*.md")):
            if md_file.name == "README.md":
                continue  # Skip README

            entry = self._create_entry(md_file, "Documentation")
            if entry:
                category.entries.append(entry)
                self._entries_by_id[entry.id] = entry

        if category.entries:
            self._categories.append(category)

        self._loaded = True

    def _create_entry(self, path: Path, category: str) -> Optional[DocEntry]:
        """Create a DocEntry from a markdown file."""
        try:
            # Generate ID from filename
            doc_id = path.stem.lower().replace("_", "-")

            # Extract title from first H1 or use filename
            title = self._extract_title(path)

            return DocEntry(
                id=doc_id,
                title=title,
                path=path,
                category=category
            )
        except Exception as e:
            logger.error(f"Error creating entry for {path}: {e}")
            return None

    def _extract_title(self, path: Path) -> str:
        """Extract title from markdown file (first H1 heading)."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("# "):
                        return line[2:].strip()
            # Fallback: use filename
            return path.stem.replace("_", " ").title()
        except Exception:
            return path.stem.replace("_", " ").title()

    def get_categories(self) -> List[DocCategory]:
        """Get all documentation categories with their entries."""
        if not self._loaded:
            self.load()
        return self._categories

    def get_entries(self) -> List[DocEntry]:
        """Get all loaded documentation entries."""
        if not self._loaded:
            self.load()
        return list(self._entries_by_id.values())

    def get_entries_by_category(self) -> Dict[str, List[DocEntry]]:
        """Get entries grouped by category (for backward compatibility)."""
        if not self._loaded:
            self.load()

        by_category: Dict[str, List[DocEntry]] = {}
        for category in self._categories:
            by_category[category.name] = category.entries

        return by_category

    def get_entry(self, doc_id: str) -> Optional[DocEntry]:
        """Get a specific documentation entry by ID."""
        if not self._loaded:
            self.load()
        return self._entries_by_id.get(doc_id)

    def get_content(self, doc_id: str) -> Optional[str]:
        """
        Get the content of a documentation entry.

        Args:
            doc_id: The documentation ID.

        Returns:
            Markdown content as string, or None if not found.
        """
        entry = self.get_entry(doc_id)
        if entry is None:
            return None

        # Load content if not cached
        if entry.content is None:
            try:
                with open(entry.path, "r", encoding="utf-8") as f:
                    entry.content = f.read()
            except Exception as e:
                logger.error(f"Error reading {entry.path}: {e}")
                return None

        return entry.content

    def search(self, query: str) -> List[Tuple[DocEntry, str]]:
        """
        Search documentation for a query string.

        Args:
            query: Search query.

        Returns:
            List of (entry, snippet) tuples matching the query.
        """
        if not self._loaded:
            self.load()

        results = []
        query_lower = query.lower()

        for entry in self._entries_by_id.values():
            content = self.get_content(entry.id)
            if content and query_lower in content.lower():
                # Extract snippet around match
                idx = content.lower().find(query_lower)
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 50)
                snippet = "..." + content[start:end] + "..."
                results.append((entry, snippet))

        return results

    def get_category_icon(self, category_name: str) -> str:
        """Get the icon name for a category."""
        for category in self._categories:
            if category.name == category_name:
                return category.icon
        return "file.png"


# Singleton instance
_loader: Optional[DocumentationLoader] = None


def get_documentation_loader() -> DocumentationLoader:
    """Get the singleton documentation loader instance."""
    global _loader
    if _loader is None:
        _loader = DocumentationLoader()
    return _loader
