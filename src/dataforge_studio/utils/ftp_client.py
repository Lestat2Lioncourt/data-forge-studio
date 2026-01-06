"""
FTP Client Abstraction - Unified interface for FTP, FTPS, and SFTP protocols.

This module provides:
- BaseFTPClient: Abstract base class defining the FTP client interface
- FTPClient: Standard FTP client using ftplib
- FTPSClient: FTP over SSL/TLS client using ftplib.FTP_TLS
- SFTPClient: SFTP client using paramiko
- FTPClientFactory: Factory for creating appropriate client based on protocol
"""
import ftplib
import logging
import socket
import stat
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Try to import paramiko for SFTP support
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    logger.warning("paramiko not available - SFTP support disabled")


class FTPProtocol(str, Enum):
    """Supported FTP protocols."""
    FTP = "ftp"
    FTPS = "ftps"
    SFTP = "sftp"


@dataclass
class RemoteFile:
    """Represents a remote file or directory."""
    name: str
    path: str
    is_dir: bool
    size: int
    modified: Optional[datetime] = None
    permissions: str = ""

    @property
    def extension(self) -> str:
        """Get file extension (lowercase, without dot)."""
        if self.is_dir:
            return ""
        return PurePosixPath(self.name).suffix.lstrip(".").lower()


class BaseFTPClient(ABC):
    """Abstract base class for FTP/SFTP clients."""

    def __init__(self, timeout: int = 30):
        self._timeout = timeout
        self._connected = False

    @abstractmethod
    def connect(self, host: str, port: int, username: str, password: str) -> bool:
        """Connect to the server.

        Args:
            host: Server hostname or IP
            port: Server port
            username: Login username
            password: Login password

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the server."""
        pass

    @abstractmethod
    def list_directory(self, path: str = "/") -> List[RemoteFile]:
        """List contents of a remote directory.

        Args:
            path: Remote directory path

        Returns:
            List of RemoteFile objects
        """
        pass

    @abstractmethod
    def download_file(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Download a file from the server.

        Args:
            remote_path: Path to remote file
            local_path: Path to save locally
            progress_callback: Optional callback(bytes_transferred, total_bytes)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Upload a file to the server.

        Args:
            local_path: Path to local file
            remote_path: Path on server
            progress_callback: Optional callback(bytes_transferred, total_bytes)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """Delete a remote file.

        Args:
            remote_path: Path to file to delete

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete_directory(self, remote_path: str) -> bool:
        """Delete a remote directory (must be empty).

        Args:
            remote_path: Path to directory to delete

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def create_directory(self, remote_path: str) -> bool:
        """Create a remote directory.

        Args:
            remote_path: Path of directory to create

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def rename(self, old_path: str, new_path: str) -> bool:
        """Rename a remote file or directory.

        Args:
            old_path: Current path
            new_path: New path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_current_directory(self) -> str:
        """Get current working directory on server.

        Returns:
            Current directory path
        """
        pass

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Check if a remote file exists.

        Args:
            remote_path: Path to check

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def get_file_size(self, remote_path: str) -> int:
        """Get size of a remote file.

        Args:
            remote_path: Path to file

        Returns:
            File size in bytes, or -1 if error
        """
        pass

    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._connected


class FTPClient(BaseFTPClient):
    """Standard FTP client using ftplib."""

    def __init__(self, passive_mode: bool = True, timeout: int = 30):
        super().__init__(timeout)
        self._ftp: Optional[ftplib.FTP] = None
        self._passive_mode = passive_mode

    def connect(self, host: str, port: int, username: str, password: str) -> bool:
        try:
            self._ftp = ftplib.FTP()
            self._ftp.connect(host, port, timeout=self._timeout)
            self._ftp.login(username, password)
            self._ftp.set_pasv(self._passive_mode)
            self._connected = True
            logger.info(f"FTP connected to {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"FTP connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                try:
                    self._ftp.close()
                except Exception:
                    pass
            finally:
                self._ftp = None
                self._connected = False
                logger.info("FTP disconnected")

    def list_directory(self, path: str = "/") -> List[RemoteFile]:
        if not self._ftp:
            return []

        result = []
        try:
            # Try MLSD first (modern, provides detailed info)
            try:
                for name, facts in self._ftp.mlsd(path):
                    if name in (".", ".."):
                        continue
                    is_dir = facts.get("type") == "dir"
                    size = int(facts.get("size", 0)) if not is_dir else 0
                    modified = None
                    if "modify" in facts:
                        try:
                            modified = datetime.strptime(facts["modify"], "%Y%m%d%H%M%S")
                        except ValueError:
                            pass
                    file_path = f"{path.rstrip('/')}/{name}"
                    result.append(RemoteFile(
                        name=name,
                        path=file_path,
                        is_dir=is_dir,
                        size=size,
                        modified=modified
                    ))
                return result
            except (ftplib.error_perm, AttributeError):
                # MLSD not supported, fall back to NLST + checks
                pass

            # Fallback: use NLST
            names = self._ftp.nlst(path)
            for name in names:
                if "/" in name:
                    # Full path returned, extract name
                    name = name.rsplit("/", 1)[-1]
                if name in (".", ".."):
                    continue

                file_path = f"{path.rstrip('/')}/{name}"

                # Try to determine if it's a directory
                is_dir = False
                size = 0
                try:
                    # Try to CWD into it - if successful, it's a directory
                    current = self._ftp.pwd()
                    self._ftp.cwd(file_path)
                    self._ftp.cwd(current)
                    is_dir = True
                except ftplib.error_perm:
                    # Not a directory, try to get size
                    try:
                        size = self._ftp.size(file_path) or 0
                    except Exception:
                        size = 0

                result.append(RemoteFile(
                    name=name,
                    path=file_path,
                    is_dir=is_dir,
                    size=size
                ))

        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")

        return result

    def download_file(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        if not self._ftp:
            return False

        try:
            total_size = self.get_file_size(remote_path)
            transferred = [0]  # Use list to allow modification in callback

            def write_callback(data: bytes):
                f.write(data)
                transferred[0] += len(data)
                if progress_callback and total_size > 0:
                    progress_callback(transferred[0], total_size)

            with open(local_path, "wb") as f:
                self._ftp.retrbinary(f"RETR {remote_path}", write_callback)

            logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return False

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        if not self._ftp:
            return False

        try:
            from pathlib import Path
            total_size = Path(local_path).stat().st_size
            transferred = [0]

            def read_callback(data: bytes):
                transferred[0] += len(data)
                if progress_callback:
                    progress_callback(transferred[0], total_size)
                return data

            with open(local_path, "rb") as f:
                # Wrap file to track progress
                self._ftp.storbinary(f"STOR {remote_path}", f, callback=lambda _: None)

            logger.info(f"Uploaded {local_path} to {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error uploading to {remote_path}: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        if not self._ftp:
            return False
        try:
            self._ftp.delete(remote_path)
            logger.info(f"Deleted file {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {remote_path}: {e}")
            return False

    def delete_directory(self, remote_path: str) -> bool:
        if not self._ftp:
            return False
        try:
            self._ftp.rmd(remote_path)
            logger.info(f"Deleted directory {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting directory {remote_path}: {e}")
            return False

    def create_directory(self, remote_path: str) -> bool:
        if not self._ftp:
            return False
        try:
            self._ftp.mkd(remote_path)
            logger.info(f"Created directory {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating directory {remote_path}: {e}")
            return False

    def rename(self, old_path: str, new_path: str) -> bool:
        if not self._ftp:
            return False
        try:
            self._ftp.rename(old_path, new_path)
            logger.info(f"Renamed {old_path} to {new_path}")
            return True
        except Exception as e:
            logger.error(f"Error renaming {old_path}: {e}")
            return False

    def get_current_directory(self) -> str:
        if not self._ftp:
            return "/"
        try:
            return self._ftp.pwd()
        except Exception:
            return "/"

    def file_exists(self, remote_path: str) -> bool:
        if not self._ftp:
            return False
        try:
            self._ftp.size(remote_path)
            return True
        except Exception:
            return False

    def get_file_size(self, remote_path: str) -> int:
        if not self._ftp:
            return -1
        try:
            return self._ftp.size(remote_path) or 0
        except Exception:
            return -1


class FTPSClient(FTPClient):
    """FTP over SSL/TLS client using ftplib.FTP_TLS."""

    def connect(self, host: str, port: int, username: str, password: str) -> bool:
        try:
            self._ftp = ftplib.FTP_TLS()
            self._ftp.connect(host, port, timeout=self._timeout)
            self._ftp.login(username, password)
            self._ftp.prot_p()  # Switch to secure data connection
            self._ftp.set_pasv(self._passive_mode)
            self._connected = True
            logger.info(f"FTPS connected to {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"FTPS connection failed: {e}")
            self._connected = False
            return False


class SFTPClient(BaseFTPClient):
    """SFTP client using paramiko."""

    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self._transport: Optional["paramiko.Transport"] = None
        self._sftp: Optional["paramiko.SFTPClient"] = None

    def connect(self, host: str, port: int, username: str, password: str) -> bool:
        if not PARAMIKO_AVAILABLE:
            logger.error("SFTP not available - paramiko not installed")
            return False

        try:
            self._transport = paramiko.Transport((host, port))
            self._transport.connect(username=username, password=password)
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            self._connected = True
            logger.info(f"SFTP connected to {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"SFTP connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._transport:
            try:
                self._transport.close()
            except Exception:
                pass
            self._transport = None

        self._connected = False
        logger.info("SFTP disconnected")

    def list_directory(self, path: str = "/") -> List[RemoteFile]:
        if not self._sftp:
            return []

        result = []
        try:
            for attr in self._sftp.listdir_attr(path):
                name = attr.filename
                if name in (".", ".."):
                    continue

                is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
                size = attr.st_size if attr.st_size else 0
                modified = None
                if attr.st_mtime:
                    modified = datetime.fromtimestamp(attr.st_mtime)

                file_path = f"{path.rstrip('/')}/{name}"
                result.append(RemoteFile(
                    name=name,
                    path=file_path,
                    is_dir=is_dir,
                    size=size,
                    modified=modified,
                    permissions=self._format_permissions(attr.st_mode) if attr.st_mode else ""
                ))
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")

        return result

    def _format_permissions(self, mode: int) -> str:
        """Format Unix permissions as string."""
        perms = ""
        for who in (stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR,
                    stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP,
                    stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH):
            if mode & who:
                perms += "r" if who in (stat.S_IRUSR, stat.S_IRGRP, stat.S_IROTH) else \
                         "w" if who in (stat.S_IWUSR, stat.S_IWGRP, stat.S_IWOTH) else "x"
            else:
                perms += "-"
        return perms

    def download_file(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        if not self._sftp:
            return False

        try:
            if progress_callback:
                total_size = self.get_file_size(remote_path)
                self._sftp.get(
                    remote_path,
                    local_path,
                    callback=lambda transferred, total: progress_callback(transferred, total_size)
                )
            else:
                self._sftp.get(remote_path, local_path)

            logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return False

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        if not self._sftp:
            return False

        try:
            from pathlib import Path
            total_size = Path(local_path).stat().st_size

            if progress_callback:
                self._sftp.put(
                    local_path,
                    remote_path,
                    callback=lambda transferred, total: progress_callback(transferred, total_size)
                )
            else:
                self._sftp.put(local_path, remote_path)

            logger.info(f"Uploaded {local_path} to {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error uploading to {remote_path}: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        if not self._sftp:
            return False
        try:
            self._sftp.remove(remote_path)
            logger.info(f"Deleted file {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {remote_path}: {e}")
            return False

    def delete_directory(self, remote_path: str) -> bool:
        if not self._sftp:
            return False
        try:
            self._sftp.rmdir(remote_path)
            logger.info(f"Deleted directory {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting directory {remote_path}: {e}")
            return False

    def create_directory(self, remote_path: str) -> bool:
        if not self._sftp:
            return False
        try:
            self._sftp.mkdir(remote_path)
            logger.info(f"Created directory {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating directory {remote_path}: {e}")
            return False

    def rename(self, old_path: str, new_path: str) -> bool:
        if not self._sftp:
            return False
        try:
            self._sftp.rename(old_path, new_path)
            logger.info(f"Renamed {old_path} to {new_path}")
            return True
        except Exception as e:
            logger.error(f"Error renaming {old_path}: {e}")
            return False

    def get_current_directory(self) -> str:
        if not self._sftp:
            return "/"
        try:
            return self._sftp.getcwd() or "/"
        except Exception:
            return "/"

    def file_exists(self, remote_path: str) -> bool:
        if not self._sftp:
            return False
        try:
            self._sftp.stat(remote_path)
            return True
        except IOError:
            return False

    def get_file_size(self, remote_path: str) -> int:
        if not self._sftp:
            return -1
        try:
            return self._sftp.stat(remote_path).st_size or 0
        except Exception:
            return -1


class FTPClientFactory:
    """Factory for creating FTP clients based on protocol."""

    @staticmethod
    def create(protocol: str, passive_mode: bool = True, timeout: int = 30) -> BaseFTPClient:
        """Create an FTP client for the given protocol.

        Args:
            protocol: "ftp", "ftps", or "sftp"
            passive_mode: Use passive mode for FTP/FTPS
            timeout: Connection timeout in seconds

        Returns:
            Appropriate FTP client instance

        Raises:
            ValueError: If protocol is not supported
        """
        protocol = protocol.lower()

        if protocol == FTPProtocol.FTP.value:
            return FTPClient(passive_mode=passive_mode, timeout=timeout)
        elif protocol == FTPProtocol.FTPS.value:
            return FTPSClient(passive_mode=passive_mode, timeout=timeout)
        elif protocol == FTPProtocol.SFTP.value:
            if not PARAMIKO_AVAILABLE:
                raise ValueError("SFTP not available - paramiko not installed")
            return SFTPClient(timeout=timeout)
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")

    @staticmethod
    def is_protocol_available(protocol: str) -> bool:
        """Check if a protocol is available.

        Args:
            protocol: Protocol to check

        Returns:
            True if protocol is available
        """
        protocol = protocol.lower()
        if protocol in (FTPProtocol.FTP.value, FTPProtocol.FTPS.value):
            return True
        elif protocol == FTPProtocol.SFTP.value:
            return PARAMIKO_AVAILABLE
        return False
