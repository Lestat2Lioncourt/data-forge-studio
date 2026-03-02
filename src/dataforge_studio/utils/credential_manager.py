"""
Credential Manager - Secure storage for database credentials using system keyring
"""

import keyring
import logging

try:
    from keyring.errors import KeyringError
except ImportError:
    KeyringError = Exception  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manages secure storage of database credentials using the system's credential manager.

    - Windows: Windows Credential Manager (DPAPI encryption)
    - macOS: Keychain
    - Linux: Secret Service (freedesktop.org)
    """

    SERVICE_NAME = "dataforge-studio"

    @staticmethod
    def save_credentials(connection_id: str, username: str, password: str) -> bool:
        """
        Save username and password securely in system credential manager.

        Args:
            connection_id: Unique database connection ID
            username: Database username
            password: Database password

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            keyring.set_password(
                CredentialManager.SERVICE_NAME,
                f"db:{connection_id}:username",
                username
            )
            keyring.set_password(
                CredentialManager.SERVICE_NAME,
                f"db:{connection_id}:password",
                password
            )
            logger.info(f"Credentials saved securely for connection {connection_id}")
            return True
        except KeyringError as e:
            logger.error(f"Failed to save credentials: {e}")
            return False

    @staticmethod
    def get_credentials(connection_id: str) -> tuple[str, str]:
        """
        Retrieve username and password from system credential manager.

        Args:
            connection_id: Unique database connection ID

        Returns:
            Tuple of (username, password). Returns ("", "") if not found.
        """
        try:
            username = keyring.get_password(
                CredentialManager.SERVICE_NAME,
                f"db:{connection_id}:username"
            )
            password = keyring.get_password(
                CredentialManager.SERVICE_NAME,
                f"db:{connection_id}:password"
            )
            return (username or "", password or "")
        except KeyringError as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return ("", "")

    @staticmethod
    def delete_credentials(connection_id: str) -> bool:
        """
        Delete credentials from system credential manager.

        Args:
            connection_id: Unique database connection ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            try:
                keyring.delete_password(
                    CredentialManager.SERVICE_NAME,
                    f"db:{connection_id}:username"
                )
            except keyring.errors.PasswordDeleteError:
                pass  # Already deleted or doesn't exist

            try:
                keyring.delete_password(
                    CredentialManager.SERVICE_NAME,
                    f"db:{connection_id}:password"
                )
            except keyring.errors.PasswordDeleteError:
                pass  # Already deleted or doesn't exist

            logger.info(f"Credentials deleted for connection {connection_id}")
            return True
        except KeyringError as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False

    @staticmethod
    def has_credentials(connection_id: str) -> bool:
        """
        Check if credentials exist for a connection.

        Args:
            connection_id: Unique database connection ID

        Returns:
            True if credentials are stored, False otherwise
        """
        try:
            username = keyring.get_password(
                CredentialManager.SERVICE_NAME,
                f"db:{connection_id}:username"
            )
            return username is not None
        except KeyringError as e:
            logger.error(f"Failed to check credentials: {e}")
            return False
