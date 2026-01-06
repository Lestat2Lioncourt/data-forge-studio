"""
FTPRoot model - FTP/SFTP/FTPS connection configuration
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class FTPProtocol(str, Enum):
    """Supported FTP protocols."""
    FTP = "ftp"
    FTPS = "ftps"
    SFTP = "sftp"

    @classmethod
    def default_port(cls, protocol: "FTPProtocol") -> int:
        """Get default port for a protocol."""
        if protocol == cls.SFTP:
            return 22
        return 21  # FTP and FTPS


@dataclass
class FTPRoot:
    """FTP/SFTP/FTPS connection configuration.

    Credentials are stored separately in the system keyring via CredentialManager.
    """
    id: str
    name: str                    # Display name/alias
    protocol: str                # "ftp", "ftps", "sftp"
    host: str                    # Server hostname or IP
    port: int                    # Default: 21 (FTP/FTPS) or 22 (SFTP)
    initial_path: str = "/"      # Initial remote directory
    passive_mode: bool = True    # Passive mode for FTP/FTPS (ignored for SFTP)
    description: str = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            # Default name from host if not provided
            self.name = f"{self.protocol.upper()}://{self.host}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    @property
    def display_name(self) -> str:
        """Get display name with protocol indicator."""
        return f"[{self.protocol.upper()}] {self.name}"

    @property
    def connection_string(self) -> str:
        """Get connection string for display (no credentials)."""
        return f"{self.protocol}://{self.host}:{self.port}{self.initial_path}"

    def is_sftp(self) -> bool:
        """Check if this is an SFTP connection."""
        return self.protocol == FTPProtocol.SFTP.value

    def is_secure(self) -> bool:
        """Check if this is a secure connection (FTPS or SFTP)."""
        return self.protocol in (FTPProtocol.FTPS.value, FTPProtocol.SFTP.value)
