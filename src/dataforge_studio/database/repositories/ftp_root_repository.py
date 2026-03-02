"""
FTP Root Repository - CRUD operations for FTP/SFTP/FTPS connections.
"""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .base_repository import BaseRepository
from ..connection_pool import ConnectionPool
from ..models import FTPRoot


class FTPRootRepository(BaseRepository[FTPRoot]):
    """Repository for FTPRoot entities."""

    @property
    def table_name(self) -> str:
        return "ftp_roots"

    def _row_to_model(self, row: sqlite3.Row) -> FTPRoot:
        row_dict = dict(row)
        row_dict['passive_mode'] = bool(row_dict.get('passive_mode', 1))
        return FTPRoot(**row_dict)

    def _get_insert_sql(self) -> str:
        return """
            INSERT INTO ftp_roots
            (id, name, protocol, host, port, initial_path, passive_mode, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

    def _get_update_sql(self) -> str:
        return """
            UPDATE ftp_roots
            SET name = ?, protocol = ?, host = ?, port = ?, initial_path = ?,
                passive_mode = ?, description = ?, updated_at = ?
            WHERE id = ?
        """

    def _model_to_insert_tuple(self, model: FTPRoot) -> tuple:
        return (model.id, model.name, model.protocol, model.host, model.port,
                model.initial_path, 1 if model.passive_mode else 0,
                model.description or '', model.created_at, model.updated_at)

    def _model_to_update_tuple(self, model: FTPRoot) -> tuple:
        model.updated_at = datetime.now().isoformat()
        return (model.name, model.protocol, model.host, model.port,
                model.initial_path, 1 if model.passive_mode else 0,
                model.description or '', model.updated_at, model.id)

    def save(self, ftp_root: FTPRoot) -> bool:
        """Save (insert or update) an FTP root using INSERT OR REPLACE."""
        try:
            now = datetime.now().isoformat()
            ftp_root.updated_at = now
            if not ftp_root.created_at:
                ftp_root.created_at = now

            with self.pool.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO ftp_roots
                    (id, name, protocol, host, port, initial_path, passive_mode,
                     description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ftp_root.id, ftp_root.name, ftp_root.protocol,
                    ftp_root.host, ftp_root.port, ftp_root.initial_path,
                    1 if ftp_root.passive_mode else 0,
                    ftp_root.description or '',
                    ftp_root.created_at, ftp_root.updated_at
                ))
            return True
        except sqlite3.Error:
            return False
