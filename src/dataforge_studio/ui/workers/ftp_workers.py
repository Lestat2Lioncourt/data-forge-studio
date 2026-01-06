"""
FTP Workers - Background workers for FTP operations.

These workers run FTP operations in background threads to keep the UI responsive.
"""

from typing import Optional, List, Callable
from pathlib import Path
import logging

from PySide6.QtCore import QThread, Signal

from ...utils.ftp_client import FTPClientFactory, BaseFTPClient, RemoteFile
from ...database.models import FTPRoot

logger = logging.getLogger(__name__)


class FTPConnectionWorker(QThread):
    """
    Worker for establishing FTP connection.

    Signals:
        connection_success: Emitted with (ftp_root_id, client) on success
        connection_error: Emitted with (ftp_root_id, error_message) on failure
    """

    connection_success = Signal(str, object)  # ftp_root_id, client
    connection_error = Signal(str, str)       # ftp_root_id, error message

    def __init__(self, ftp_root: FTPRoot, username: str, password: str):
        super().__init__()
        self.ftp_root = ftp_root
        self.username = username
        self.password = password

    def run(self):
        try:
            # Create client based on protocol
            client = FTPClientFactory.create(
                self.ftp_root.protocol,
                passive_mode=self.ftp_root.passive_mode,
                timeout=30
            )

            # Attempt connection
            if client.connect(
                self.ftp_root.host,
                self.ftp_root.port,
                self.username,
                self.password
            ):
                logger.info(f"FTP connection established: {self.ftp_root.host}")
                self.connection_success.emit(self.ftp_root.id, client)
            else:
                self.connection_error.emit(
                    self.ftp_root.id,
                    "Echec de connexion - verifiez vos identifiants"
                )

        except Exception as e:
            logger.error(f"FTP connection error: {e}")
            self.connection_error.emit(self.ftp_root.id, str(e))


class FTPListDirectoryWorker(QThread):
    """
    Worker for listing remote directory contents.

    Signals:
        directory_loaded: Emitted with (path, file_list) on success
        error: Emitted with error message on failure
    """

    directory_loaded = Signal(str, list)  # path, List[RemoteFile]
    error = Signal(str)

    def __init__(self, client: BaseFTPClient, remote_path: str):
        super().__init__()
        self.client = client
        self.remote_path = remote_path

    def run(self):
        try:
            files = self.client.list_directory(self.remote_path)
            self.directory_loaded.emit(self.remote_path, files)

        except Exception as e:
            logger.error(f"Error listing directory {self.remote_path}: {e}")
            self.error.emit(f"Erreur de lecture du dossier: {str(e)}")


class FTPTransferWorker(QThread):
    """
    Worker for file transfer operations (download/upload).

    Signals:
        progress: Emitted with (percentage, bytes_transferred, total_bytes)
        completed: Emitted with (success, local_path) on completion
        error: Emitted with error message on failure
    """

    progress = Signal(int, int, int)      # percentage, transferred, total
    completed = Signal(bool, str)         # success, local_path
    error = Signal(str)

    def __init__(self, client: BaseFTPClient,
                 remote_path: str, local_path: str,
                 is_upload: bool = False):
        super().__init__()
        self.client = client
        self.remote_path = remote_path
        self.local_path = local_path
        self.is_upload = is_upload
        self._cancelled = False

    def cancel(self):
        """Cancel the transfer."""
        self._cancelled = True

    def _progress_callback(self, transferred: int, total: int) -> bool:
        """
        Progress callback for transfer.

        Returns False to cancel, True to continue.
        """
        if self._cancelled:
            return False

        percentage = int((transferred / total) * 100) if total > 0 else 0
        self.progress.emit(percentage, transferred, total)
        return True

    def run(self):
        try:
            if self.is_upload:
                success = self.client.upload_file(
                    self.local_path,
                    self.remote_path,
                    self._progress_callback
                )
            else:
                success = self.client.download_file(
                    self.remote_path,
                    self.local_path,
                    self._progress_callback
                )

            if self._cancelled:
                self.error.emit("Transfert annule")
            else:
                self.completed.emit(success, self.local_path)

        except Exception as e:
            logger.error(f"Transfer error: {e}")
            self.error.emit(f"Erreur de transfert: {str(e)}")


class FTPDeleteWorker(QThread):
    """
    Worker for deleting remote files/directories.

    Signals:
        completed: Emitted with (success, path) on completion
        error: Emitted with error message on failure
    """

    completed = Signal(bool, str)  # success, path
    error = Signal(str)

    def __init__(self, client: BaseFTPClient, remote_path: str, is_directory: bool = False):
        super().__init__()
        self.client = client
        self.remote_path = remote_path
        self.is_directory = is_directory

    def run(self):
        try:
            if self.is_directory:
                success = self.client.delete_directory(self.remote_path)
            else:
                success = self.client.delete_file(self.remote_path)

            self.completed.emit(success, self.remote_path)

        except Exception as e:
            logger.error(f"Delete error: {e}")
            self.error.emit(f"Erreur de suppression: {str(e)}")


class FTPCreateDirectoryWorker(QThread):
    """
    Worker for creating remote directory.

    Signals:
        completed: Emitted with (success, path) on completion
        error: Emitted with error message on failure
    """

    completed = Signal(bool, str)  # success, path
    error = Signal(str)

    def __init__(self, client: BaseFTPClient, remote_path: str):
        super().__init__()
        self.client = client
        self.remote_path = remote_path

    def run(self):
        try:
            success = self.client.create_directory(self.remote_path)
            self.completed.emit(success, self.remote_path)

        except Exception as e:
            logger.error(f"Create directory error: {e}")
            self.error.emit(f"Erreur de creation: {str(e)}")
