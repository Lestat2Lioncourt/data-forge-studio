"""
Workspace Export/Import - JSON export for workspaces and connections

Supports exporting:
- Individual database connections
- Complete workspaces with all related resources
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from ..database.config_db import get_config_db, DatabaseConnection, Workspace
from ..database.models.saved_query import SavedQuery
from ..database.models.script import Script
from ..database.models.job import Job
from ..database.models.file_root import FileRoot

import logging
logger = logging.getLogger(__name__)

# Export format version
EXPORT_VERSION = "1.0"


def export_connections_to_json(
    connection_ids: Optional[List[str]] = None,
    include_credentials: bool = False
) -> Dict[str, Any]:
    """
    Export database connections to JSON format.

    Args:
        connection_ids: List of connection IDs to export, or None for all
        include_credentials: Whether to include passwords (default: False for security)

    Returns:
        Dictionary ready for JSON serialization
    """
    config_db = get_config_db()

    if connection_ids:
        connections = [config_db.get_database_connection(cid) for cid in connection_ids]
        connections = [c for c in connections if c is not None]
    else:
        connections = config_db.get_all_database_connections()

    export_data = {
        "export_type": "connections",
        "version": EXPORT_VERSION,
        "exported_at": datetime.now().isoformat(),
        "databases": []
    }

    for conn in connections:
        conn_data = _serialize_connection(conn, include_credentials)
        export_data["databases"].append(conn_data)

    return export_data


def export_workspace_to_json(
    workspace_id: str,
    include_credentials: bool = False,
    include_databases: bool = True,
    include_rootfolders: bool = True,
    include_queries: bool = True,
    include_scripts: bool = True,
    include_jobs: bool = True
) -> Dict[str, Any]:
    """
    Export a complete workspace with all related resources.

    Args:
        workspace_id: Workspace ID to export
        include_credentials: Whether to include passwords (default: False)
        include_databases: Include database connections
        include_rootfolders: Include file roots/folders
        include_queries: Include saved queries
        include_scripts: Include scripts
        include_jobs: Include jobs

    Returns:
        Dictionary ready for JSON serialization
    """
    config_db = get_config_db()

    workspace = config_db.get_workspace(workspace_id)
    if not workspace:
        raise ValueError(f"Workspace not found: {workspace_id}")

    export_data = {
        "export_type": "workspace",
        "version": EXPORT_VERSION,
        "exported_at": datetime.now().isoformat(),
        "workspace": {
            "name": workspace.name,
            "description": workspace.description,
            "is_default": workspace.is_default
        },
        "databases": [],
        "rootfolders": [],
        "queries": [],
        "scripts": [],
        "jobs": []
    }

    # Export databases with workspace context
    if include_databases:
        ws_databases = config_db.get_workspace_databases_with_context(workspace_id)
        for ws_db in ws_databases:
            conn_data = _serialize_connection(ws_db.connection, include_credentials)
            conn_data["workspace_context"] = {
                "database_name": ws_db.database_name or ""
            }
            export_data["databases"].append(conn_data)

    # Export rootfolders with workspace context
    if include_rootfolders:
        ws_roots = config_db.get_workspace_file_roots_with_context(workspace_id)
        for ws_root in ws_roots:
            root_data = _serialize_fileroot(ws_root.file_root)
            root_data["workspace_context"] = {
                "subfolder_path": ws_root.subfolder_path or ""
            }
            export_data["rootfolders"].append(root_data)

    # Export queries
    if include_queries:
        queries = config_db.get_workspace_queries(workspace_id)
        for query in queries:
            query_data = _serialize_query(query)
            export_data["queries"].append(query_data)

    # Export scripts
    if include_scripts:
        scripts = config_db.get_workspace_scripts(workspace_id)
        for script in scripts:
            script_data = _serialize_script(script)
            export_data["scripts"].append(script_data)

    # Export jobs
    if include_jobs:
        jobs = config_db.get_workspace_jobs(workspace_id)
        for job in jobs:
            job_data = _serialize_job(job)
            export_data["jobs"].append(job_data)

    return export_data


def save_export_to_file(export_data: Dict[str, Any], filepath: str) -> None:
    """
    Save export data to a JSON file.

    Args:
        export_data: Export dictionary
        filepath: Target file path
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Export saved to: {filepath}")


def _serialize_connection(conn: DatabaseConnection, include_credentials: bool) -> Dict[str, Any]:
    """Serialize a database connection."""
    conn_string = conn.connection_string

    # Optionally mask credentials in connection string
    if not include_credentials:
        conn_string = _mask_credentials(conn_string, conn.db_type)

    return {
        "name": conn.name,
        "db_type": conn.db_type,
        "connection_string": conn_string,
        "description": conn.description or ""
    }


def _serialize_fileroot(root: FileRoot) -> Dict[str, Any]:
    """Serialize a file root."""
    return {
        "name": root.name or "",
        "path": root.path,
        "description": root.description or ""
    }


def _serialize_query(query: SavedQuery) -> Dict[str, Any]:
    """Serialize a saved query."""
    return {
        "name": query.name,
        "query_text": query.query_text,
        "category": query.category or "",
        "description": query.description or "",
        "target_database_name": ""  # Will be resolved on import
    }


def _serialize_script(script: Script) -> Dict[str, Any]:
    """Serialize a script."""
    return {
        "name": script.name,
        "script_type": script.script_type or "",
        "parameters_schema": script.parameters_schema or "",
        "description": script.description or ""
    }


def _serialize_job(job: Job) -> Dict[str, Any]:
    """Serialize a job."""
    return {
        "name": job.name,
        "job_type": job.job_type or "script",
        "parameters": job.parameters or "",
        "enabled": job.enabled,
        "description": ""  # Jobs don't have description in current model
    }


def _mask_credentials(connection_string: str, db_type: str) -> str:
    """
    Mask passwords in connection strings for security.

    Args:
        connection_string: Original connection string
        db_type: Database type (sqlite, sqlserver, postgresql, etc.)

    Returns:
        Connection string with password masked
    """
    import re

    if db_type == "sqlite":
        return connection_string  # No credentials in SQLite

    if db_type == "postgresql":
        # postgresql://user:password@host:port/db
        # Mask password between : and @
        pattern = r'(://[^:]+:)([^@]+)(@)'
        return re.sub(pattern, r'\1***MASKED***\3', connection_string)

    if db_type in ("sqlserver", "access"):
        # PWD=xxx; or Password=xxx;
        pattern = r'(PWD=|Password=)([^;]+)(;?)'
        return re.sub(pattern, r'\1***MASKED***\3', connection_string, flags=re.IGNORECASE)

    if db_type == "mysql":
        # mysql+pymysql://user:password@host:port/db
        pattern = r'(://[^:]+:)([^@]+)(@)'
        return re.sub(pattern, r'\1***MASKED***\3', connection_string)

    return connection_string


def get_export_summary(export_data: Dict[str, Any]) -> str:
    """
    Get a human-readable summary of export data.

    Args:
        export_data: Export dictionary

    Returns:
        Summary string
    """
    export_type = export_data.get("export_type", "unknown")

    if export_type == "connections":
        count = len(export_data.get("databases", []))
        return f"Export: {count} connexion(s)"

    elif export_type == "workspace":
        ws_name = export_data.get("workspace", {}).get("name", "Unknown")
        counts = {
            "databases": len(export_data.get("databases", [])),
            "rootfolders": len(export_data.get("rootfolders", [])),
            "queries": len(export_data.get("queries", [])),
            "scripts": len(export_data.get("scripts", [])),
            "jobs": len(export_data.get("jobs", []))
        }

        parts = [f"Workspace: {ws_name}"]
        for key, count in counts.items():
            if count > 0:
                parts.append(f"{count} {key}")

        return " | ".join(parts)

    return "Export inconnu"


# =============================================================================
# IMPORT FUNCTIONS
# =============================================================================

class ImportConflictMode:
    """Modes for handling workspace name conflicts."""
    RENAME = "rename"      # Create with new name
    MERGE = "merge"        # Merge into existing workspace
    CANCEL = "cancel"      # Cancel import


def load_import_from_file(filepath: str) -> Dict[str, Any]:
    """
    Load import data from a JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        Dictionary with import data

    Raises:
        ValueError: If file format is invalid
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate format
    if "export_type" not in data or "version" not in data:
        raise ValueError("Invalid export file format")

    return data


def check_workspace_conflict(workspace_name: str) -> Optional[Workspace]:
    """
    Check if a workspace with the given name already exists.

    Args:
        workspace_name: Name to check

    Returns:
        Existing Workspace if found, None otherwise
    """
    config_db = get_config_db()
    workspaces = config_db.get_all_workspaces()

    for ws in workspaces:
        if ws.name.lower() == workspace_name.lower():
            return ws

    return None


def import_connections_from_json(
    import_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Import database connections from JSON data.

    Args:
        import_data: Dictionary with import data

    Returns:
        Dictionary with import results:
        - created: list of created connection names
        - existing: list of reused existing connection names
        - errors: list of error messages
    """
    config_db = get_config_db()
    results = {"created": [], "existing": [], "errors": []}

    databases = import_data.get("databases", [])

    for db_data in databases:
        try:
            conn, is_new = _import_or_match_connection(db_data, config_db)
            if is_new:
                results["created"].append(conn.name)
            else:
                results["existing"].append(conn.name)
        except Exception as e:
            results["errors"].append(f"{db_data.get('name', 'Unknown')}: {str(e)}")

    return results


def import_workspace_from_json(
    import_data: Dict[str, Any],
    conflict_mode: str = ImportConflictMode.RENAME,
    existing_workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Import a complete workspace from JSON data.

    Args:
        import_data: Dictionary with import data
        conflict_mode: How to handle workspace name conflicts
        existing_workspace_id: If merging, the ID of existing workspace

    Returns:
        Dictionary with import results:
        - workspace_id: ID of created/merged workspace
        - workspace_name: Final name of workspace
        - resources: dict with counts per resource type
        - errors: list of error messages
    """
    import uuid
    from datetime import datetime

    config_db = get_config_db()
    results = {
        "workspace_id": None,
        "workspace_name": None,
        "resources": {
            "databases": {"created": 0, "existing": 0},
            "rootfolders": {"created": 0, "existing": 0},
            "queries": {"created": 0, "existing": 0},
            "scripts": {"created": 0, "existing": 0},
            "jobs": {"created": 0, "existing": 0}
        },
        "errors": []
    }

    ws_data = import_data.get("workspace", {})
    ws_name = ws_data.get("name", "Imported Workspace")

    # Handle workspace creation based on conflict mode
    if conflict_mode == ImportConflictMode.MERGE and existing_workspace_id:
        workspace_id = existing_workspace_id
        workspace = config_db.get_workspace(workspace_id)
        results["workspace_name"] = workspace.name if workspace else ws_name
    elif conflict_mode == ImportConflictMode.RENAME:
        # Find unique name
        base_name = ws_name
        counter = 1
        while check_workspace_conflict(ws_name):
            ws_name = f"{base_name} (importé {counter})"
            counter += 1

        # Create new workspace
        workspace_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        workspace = Workspace(
            id=workspace_id,
            name=ws_name,
            description=ws_data.get("description", ""),
            is_default=False,  # Never import as default
            created_at=now,
            updated_at=now,
            last_used_at=now
        )
        config_db.add_workspace(workspace)
        results["workspace_name"] = ws_name
    else:
        # Cancel mode - should not reach here
        results["errors"].append("Import cancelled")
        return results

    results["workspace_id"] = workspace_id

    # Import databases and attach to workspace
    for db_data in import_data.get("databases", []):
        try:
            conn, is_new = _import_or_match_connection(db_data, config_db)
            context = db_data.get("workspace_context", {})
            database_name = context.get("database_name", "")

            # Attach to workspace
            config_db.add_database_to_workspace(workspace_id, conn.id, database_name or None)

            if is_new:
                results["resources"]["databases"]["created"] += 1
            else:
                results["resources"]["databases"]["existing"] += 1
        except Exception as e:
            results["errors"].append(f"Database {db_data.get('name', '?')}: {str(e)}")

    # Import rootfolders and attach to workspace
    for rf_data in import_data.get("rootfolders", []):
        try:
            fileroot, is_new = _import_or_match_fileroot(rf_data, config_db)
            context = rf_data.get("workspace_context", {})
            subfolder_path = context.get("subfolder_path", "")

            # Attach to workspace
            config_db.add_file_root_to_workspace(workspace_id, fileroot.id, subfolder_path or None)

            if is_new:
                results["resources"]["rootfolders"]["created"] += 1
            else:
                results["resources"]["rootfolders"]["existing"] += 1
        except Exception as e:
            results["errors"].append(f"Rootfolder {rf_data.get('path', '?')}: {str(e)}")

    # Import queries and attach to workspace
    for q_data in import_data.get("queries", []):
        try:
            query, is_new = _import_query(q_data, config_db)

            # Attach to workspace
            config_db.add_query_to_workspace(workspace_id, query.id)

            if is_new:
                results["resources"]["queries"]["created"] += 1
            else:
                results["resources"]["queries"]["existing"] += 1
        except Exception as e:
            results["errors"].append(f"Query {q_data.get('name', '?')}: {str(e)}")

    # Import scripts and attach to workspace
    for s_data in import_data.get("scripts", []):
        try:
            script, is_new = _import_script(s_data, config_db)

            # Attach to workspace
            config_db.add_script_to_workspace(workspace_id, script.id)

            if is_new:
                results["resources"]["scripts"]["created"] += 1
            else:
                results["resources"]["scripts"]["existing"] += 1
        except Exception as e:
            results["errors"].append(f"Script {s_data.get('name', '?')}: {str(e)}")

    # Import jobs and attach to workspace
    for j_data in import_data.get("jobs", []):
        try:
            job, is_new = _import_job(j_data, config_db, workspace_id)

            # Attach to workspace
            config_db.add_job_to_workspace(workspace_id, job.id)

            if is_new:
                results["resources"]["jobs"]["created"] += 1
            else:
                results["resources"]["jobs"]["existing"] += 1
        except Exception as e:
            results["errors"].append(f"Job {j_data.get('name', '?')}: {str(e)}")

    return results


def _import_or_match_connection(db_data: Dict[str, Any], config_db) -> tuple:
    """
    Import a connection or match an existing one.

    Returns:
        Tuple of (DatabaseConnection, is_new)
    """
    import uuid
    from datetime import datetime

    name = db_data.get("name", "")
    db_type = db_data.get("db_type", "")
    conn_string = db_data.get("connection_string", "")

    # Check for existing connection with same name and type
    existing = config_db.get_all_database_connections()
    for conn in existing:
        if conn.name.lower() == name.lower() and conn.db_type == db_type:
            # Match found - reuse existing
            return (conn, False)

    # Create new connection
    now = datetime.now().isoformat()
    new_conn = DatabaseConnection(
        id=str(uuid.uuid4()),
        name=name,
        db_type=db_type,
        connection_string=conn_string,
        description=db_data.get("description", ""),
        created_at=now,
        updated_at=now
    )
    config_db.add_database_connection(new_conn)
    return (new_conn, True)


def _import_or_match_fileroot(rf_data: Dict[str, Any], config_db) -> tuple:
    """
    Import a file root or match an existing one.

    Returns:
        Tuple of (FileRoot, is_new)
    """
    import uuid
    from datetime import datetime

    path = rf_data.get("path", "")

    # Check for existing fileroot with same path
    existing = config_db.get_all_file_roots()
    for root in existing:
        if root.path.lower() == path.lower():
            # Match found - reuse existing
            return (root, False)

    # Create new fileroot
    now = datetime.now().isoformat()
    new_root = FileRoot(
        id=str(uuid.uuid4()),
        path=path,
        name=rf_data.get("name", ""),
        description=rf_data.get("description", ""),
        created_at=now,
        updated_at=now
    )
    config_db.add_file_root(new_root)
    return (new_root, True)


def _import_query(q_data: Dict[str, Any], config_db) -> tuple:
    """
    Import a query (always creates new with suffix if conflict).

    Returns:
        Tuple of (SavedQuery, is_new)
    """
    import uuid
    from datetime import datetime

    name = q_data.get("name", "")
    category = q_data.get("category", "")

    # Check for conflict and rename if needed
    existing = config_db.get_all_saved_queries()
    original_name = name
    counter = 1
    while any(q.name.lower() == name.lower() and (q.category or "") == category for q in existing):
        name = f"{original_name} (importé {counter})"
        counter += 1

    # Create new query
    now = datetime.now().isoformat()
    new_query = SavedQuery(
        id=str(uuid.uuid4()),
        name=name,
        query_text=q_data.get("query_text", ""),
        target_database_id=None,  # Will need to be linked manually
        category=category,
        description=q_data.get("description", ""),
        created_at=now,
        updated_at=now
    )
    config_db.add_saved_query(new_query)
    return (new_query, True)


def _import_script(s_data: Dict[str, Any], config_db) -> tuple:
    """
    Import a script (always creates new with suffix if conflict).

    Returns:
        Tuple of (Script, is_new)
    """
    import uuid
    from datetime import datetime

    name = s_data.get("name", "")
    script_type = s_data.get("script_type", "")

    # Check for conflict and rename if needed
    existing = config_db.get_all_scripts()
    original_name = name
    counter = 1
    while any(s.name.lower() == name.lower() and (s.script_type or "") == script_type for s in existing):
        name = f"{original_name} (importé {counter})"
        counter += 1

    # Create new script
    now = datetime.now().isoformat()
    new_script = Script(
        id=str(uuid.uuid4()),
        name=name,
        script_type=script_type,
        parameters_schema=s_data.get("parameters_schema", ""),
        description=s_data.get("description", ""),
        created_at=now,
        updated_at=now
    )
    config_db.add_script(new_script)
    return (new_script, True)


def _import_job(j_data: Dict[str, Any], config_db, project_id: str) -> tuple:
    """
    Import a job (always creates new with suffix if conflict).

    Returns:
        Tuple of (Job, is_new)
    """
    import uuid
    from datetime import datetime

    name = j_data.get("name", "")

    # Check for conflict and rename if needed
    existing = config_db.get_all_jobs()
    original_name = name
    counter = 1
    while any(j.name.lower() == name.lower() for j in existing):
        name = f"{original_name} (importé {counter})"
        counter += 1

    # Create new job
    now = datetime.now().isoformat()
    new_job = Job(
        id=str(uuid.uuid4()),
        name=name,
        job_type=j_data.get("job_type", "script"),
        script_id=None,  # Will need to be linked manually
        project_id=project_id,
        parameters=j_data.get("parameters", ""),
        enabled=j_data.get("enabled", True),
        last_run_at=None,
        parent_job_id=None,
        previous_job_id=None,
        created_at=now,
        updated_at=now
    )
    config_db.add_job(new_job)
    return (new_job, True)


def get_import_summary(results: Dict[str, Any]) -> str:
    """
    Get a human-readable summary of import results.

    Args:
        results: Import results dictionary

    Returns:
        Summary string
    """
    lines = []

    ws_name = results.get("workspace_name")
    if ws_name:
        lines.append(f"Workspace: {ws_name}")

    resources = results.get("resources", {})
    for res_type, counts in resources.items():
        created = counts.get("created", 0)
        existing = counts.get("existing", 0)
        if created > 0 or existing > 0:
            parts = []
            if created > 0:
                parts.append(f"{created} créé(s)")
            if existing > 0:
                parts.append(f"{existing} existant(s)")
            lines.append(f"  {res_type}: {', '.join(parts)}")

    errors = results.get("errors", [])
    if errors:
        lines.append(f"\nErreurs: {len(errors)}")
        for err in errors[:5]:  # Show first 5 errors
            lines.append(f"  - {err}")
        if len(errors) > 5:
            lines.append(f"  ... et {len(errors) - 5} autres erreurs")

    return "\n".join(lines)
