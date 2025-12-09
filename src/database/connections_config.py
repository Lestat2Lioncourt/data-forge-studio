"""
Connections Configuration Module - Bridge to SQLite configuration database
This module provides backward compatibility with the old JSON-based system
"""
from pathlib import Path
from typing import List, Optional
from .config_db import config_db, DatabaseConnection
from ..utils.config import Config


class ConnectionsManager:
    """Manager for database connections - now using SQLite backend"""

    DB_TYPES = {
        'sqlserver': '🗄️ SQL Server',
        'mysql': '🐬 MySQL',
        'postgresql': '🐘 PostgreSQL',
        'oracle': '🔶 Oracle',
        'sqlite': '📁 SQLite',
        'other': '💾 Other'
    }

    def __init__(self):
        # Check if we need to migrate from old JSON format (multiple possible locations)
        from pathlib import Path

        # Check in app folder first
        app_folder = Path(__file__).parent
        old_json_file = app_folder / "_AppConfig" / "database_connections.json"

        # Also check old location in data folder
        if not old_json_file.exists():
            old_json_file = Config.DATA_ROOT_FOLDER / "_Config" / "database_connections.json"

        if old_json_file.exists():
            print(f"Migrating from old JSON format to SQLite from {old_json_file}...")
            config_db.migrate_from_json(old_json_file)
            # Rename old file to prevent re-migration
            old_json_file.rename(old_json_file.with_suffix('.json.migrated'))
            print("Migration complete")

    def add_connection(self, connection: DatabaseConnection):
        """Add a new connection"""
        config_db.add_database_connection(connection)

    def update_connection(self, connection_id: str, updated_connection: DatabaseConnection):
        """Update an existing connection"""
        updated_connection.id = connection_id
        config_db.update_database_connection(updated_connection)

    def delete_connection(self, connection_id: str):
        """Delete a connection"""
        config_db.delete_database_connection(connection_id)

    def get_connection(self, connection_id: str) -> Optional[DatabaseConnection]:
        """Get a connection by ID"""
        return config_db.get_database_connection(connection_id)

    def get_all_connections(self) -> List[DatabaseConnection]:
        """Get all connections"""
        return config_db.get_all_database_connections()

    @staticmethod
    def get_db_type_icon(db_type: str) -> str:
        """Get icon for database type"""
        return ConnectionsManager.DB_TYPES.get(db_type, ConnectionsManager.DB_TYPES['other'])


# Global connections manager instance
connections_manager = ConnectionsManager()

# Export for backward compatibility
__all__ = ['connections_manager', 'ConnectionsManager', 'DatabaseConnection']
