"""
Workspace Sharing - Read/write shared resources (diagrams, queries) to a shared folder.

Shared resources are stored as JSON files in a folder structure:
    shared_path/
    ├── diagrams/
    │   └── diagram-name.json
    ├── queries/
    │   └── query-name.json
    └── connections/
        └── connection-name.json  (without credentials)
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import asdict

from ..database.models import ERDiagram, ERDiagramTable, ERDiagramFKMidpoint, SavedQuery

logger = logging.getLogger(__name__)


def is_shared_path_accessible(shared_path: str) -> bool:
    """Check if the shared folder is accessible."""
    if not shared_path:
        return False
    try:
        p = Path(shared_path)
        return p.exists() and p.is_dir()
    except (OSError, PermissionError):
        return False


def ensure_shared_structure(shared_path: str) -> bool:
    """Create the shared folder structure if it doesn't exist."""
    try:
        base = Path(shared_path)
        (base / "diagrams").mkdir(parents=True, exist_ok=True)
        (base / "queries").mkdir(parents=True, exist_ok=True)
        (base / "connections").mkdir(parents=True, exist_ok=True)
        return True
    except (OSError, PermissionError) as e:
        logger.error(f"Cannot create shared folder structure: {e}")
        return False


# ==================== Diagrams ====================

def _safe_filename(name: str) -> str:
    """Convert a name to a safe filename."""
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip()


def publish_diagram(shared_path: str, diagram: ERDiagram) -> bool:
    """Publish an ER diagram to the shared folder."""
    try:
        ensure_shared_structure(shared_path)
        filename = f"{_safe_filename(diagram.name)}.json"
        filepath = Path(shared_path) / "diagrams" / filename

        data = {
            'id': diagram.id,
            'name': diagram.name,
            'connection_id': diagram.connection_id,
            'database_name': diagram.database_name,
            'description': diagram.description,
            'zoom_level': diagram.zoom_level,
            'tables': [
                {'table_name': t.table_name, 'schema_name': t.schema_name,
                 'pos_x': t.pos_x, 'pos_y': t.pos_y}
                for t in diagram.tables
            ],
            'fk_midpoints': [
                {'from_table': m.from_table, 'from_column': m.from_column,
                 'to_table': m.to_table, 'to_column': m.to_column,
                 'mid_x': m.mid_x, 'mid_y': m.mid_y}
                for m in diagram.fk_midpoints
            ],
            'created_at': diagram.created_at,
            'updated_at': diagram.updated_at,
        }

        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        logger.info(f"Published diagram '{diagram.name}' to {filepath}")
        return True
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to publish diagram: {e}")
        return False


def load_shared_diagrams(shared_path: str) -> List[ERDiagram]:
    """Load all shared diagrams from the shared folder."""
    diagrams = []
    diagrams_dir = Path(shared_path) / "diagrams"
    if not diagrams_dir.exists():
        return diagrams

    for filepath in sorted(diagrams_dir.glob("*.json")):
        try:
            data = json.loads(filepath.read_text(encoding='utf-8'))
            diagram = ERDiagram(
                id=data.get('id', ''),
                name=data.get('name', filepath.stem),
                connection_id=data.get('connection_id', ''),
                database_name=data.get('database_name', ''),
                description=data.get('description', ''),
                zoom_level=data.get('zoom_level', 1.0),
                tables=[
                    ERDiagramTable(**t) for t in data.get('tables', [])
                ],
                fk_midpoints=[
                    ERDiagramFKMidpoint(**m) for m in data.get('fk_midpoints', [])
                ],
                created_at=data.get('created_at', ''),
                updated_at=data.get('updated_at', ''),
            )
            diagrams.append(diagram)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to load shared diagram {filepath.name}: {e}")

    return diagrams


# ==================== Queries ====================

def publish_query(shared_path: str, query: SavedQuery) -> bool:
    """Publish a saved query to the shared folder."""
    try:
        ensure_shared_structure(shared_path)
        filename = f"{_safe_filename(query.name)}.json"
        filepath = Path(shared_path) / "queries" / filename

        data = {
            'id': query.id,
            'name': query.name,
            'description': query.description,
            'query_text': query.query_text,
            'category': query.category,
            'target_database_id': query.target_database_id,
            'created_at': query.created_at,
            'updated_at': query.updated_at,
        }

        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        logger.info(f"Published query '{query.name}' to {filepath}")
        return True
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to publish query: {e}")
        return False


def load_shared_queries(shared_path: str) -> List[dict]:
    """Load all shared queries from the shared folder.

    Returns list of dicts (not SavedQuery objects) to avoid dependency on target_database_id.
    """
    queries = []
    queries_dir = Path(shared_path) / "queries"
    if not queries_dir.exists():
        return queries

    for filepath in sorted(queries_dir.glob("*.json")):
        try:
            data = json.loads(filepath.read_text(encoding='utf-8'))
            queries.append(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load shared query {filepath.name}: {e}")

    return queries
