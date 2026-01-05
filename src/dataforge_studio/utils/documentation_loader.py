"""
Documentation Loader - Load and parse markdown documentation files.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

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


class DocumentationLoader:
    """
    Loads documentation from markdown files.

    Scans the docs/ directory and provides access to documentation content.
    """

    # Category mappings based on filename patterns
    CATEGORY_PATTERNS = {
        "Database": ["SQLITE", "SQL_", "QUERIES", "CONFIG_DB"],
        "Features": ["FEATURES", "NEW_FEATURES", "SUMMARY"],
        "Guides": ["GUIDE", "HELP", "MENU"],
        "Projects": ["PROJECTS", "WORKSPACE"],
        "Development": ["MIGRATION", "PATTERNS", "PYPROJECT"],
    }

    # User-facing documentation (hide internal/dev docs)
    USER_DOCS = [
        "SUMMARY_ALL_FEATURES.md",
        "RIGHT_CLICK_MENU.md",
        "SAVE_QUERIES_GUIDE.md",
        "NEW_FEATURES_QUERIES_DB.md",
        "SQLITE_NATIVE_SUPPORT.md",
        "HELP_VIEWER_GUIDE.md",
        "SQL_FORMAT_STYLES_GUIDE.md",
        "PROJECTS_FEATURE.md",
    ]

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
        self._entries: Dict[str, DocEntry] = {}
        self._loaded = False

    def load(self, user_docs_only: bool = True) -> None:
        """
        Load documentation entries from the docs directory.

        Args:
            user_docs_only: If True, only load user-facing documentation.
        """
        if not self.docs_path.exists():
            logger.warning(f"Documentation path not found: {self.docs_path}")
            return

        self._entries.clear()

        for md_file in self.docs_path.glob("*.md"):
            # Skip non-user docs if requested
            if user_docs_only and md_file.name not in self.USER_DOCS:
                continue

            entry = self._create_entry(md_file)
            if entry:
                self._entries[entry.id] = entry

        self._loaded = True
        logger.debug(f"Loaded {len(self._entries)} documentation entries")

    def _create_entry(self, path: Path) -> Optional[DocEntry]:
        """Create a DocEntry from a markdown file."""
        try:
            # Generate ID from filename
            doc_id = path.stem.lower().replace("_", "-")

            # Extract title from first H1 or use filename
            title = self._extract_title(path)

            # Determine category
            category = self._determine_category(path.name)

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

    def _determine_category(self, filename: str) -> str:
        """Determine category based on filename patterns."""
        upper_name = filename.upper()
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern in upper_name:
                    return category
        return "General"

    def get_entries(self) -> List[DocEntry]:
        """Get all loaded documentation entries."""
        if not self._loaded:
            self.load()
        return list(self._entries.values())

    def get_entries_by_category(self) -> Dict[str, List[DocEntry]]:
        """Get entries grouped by category."""
        if not self._loaded:
            self.load()

        by_category: Dict[str, List[DocEntry]] = {}
        for entry in self._entries.values():
            if entry.category not in by_category:
                by_category[entry.category] = []
            by_category[entry.category].append(entry)

        # Sort entries within each category
        for entries in by_category.values():
            entries.sort(key=lambda e: e.title)

        return by_category

    def get_entry(self, doc_id: str) -> Optional[DocEntry]:
        """Get a specific documentation entry by ID."""
        if not self._loaded:
            self.load()
        return self._entries.get(doc_id)

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

        for entry in self._entries.values():
            content = self.get_content(entry.id)
            if content and query_lower in content.lower():
                # Extract snippet around match
                idx = content.lower().find(query_lower)
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 50)
                snippet = "..." + content[start:end] + "..."
                results.append((entry, snippet))

        return results


# Singleton instance
_loader: Optional[DocumentationLoader] = None


def get_documentation_loader() -> DocumentationLoader:
    """Get the singleton documentation loader instance."""
    global _loader
    if _loader is None:
        _loader = DocumentationLoader()
    return _loader
