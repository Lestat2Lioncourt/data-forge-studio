"""
Network utilities for connection testing.
"""

import socket
import subprocess
import platform
import re
from typing import Optional, Tuple

import logging
logger = logging.getLogger(__name__)


def ping_host(host: str, timeout: int = 3) -> Tuple[bool, str]:
    """
    Ping a host to check if it's reachable.

    Args:
        host: Hostname or IP address
        timeout: Timeout in seconds

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not host:
        return False, "No host specified"

    try:
        # Try socket connection first (faster and more reliable for servers)
        # This checks if the host is reachable on common ports
        reachable, msg = _check_host_socket(host, timeout)
        if reachable:
            return True, msg

        # Fallback to ICMP ping
        return _ping_icmp(host, timeout)

    except Exception as e:
        logger.error(f"Error pinging host {host}: {e}")
        return False, str(e)


def _check_host_socket(host: str, timeout: int, port: int = None) -> Tuple[bool, str]:
    """
    Check if host is reachable via socket connection.

    Args:
        host: Hostname or IP address
        timeout: Timeout in seconds
        port: Specific port to check (None = try common ports)

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Common database ports to try
    ports_to_try = [port] if port else [1433, 3306, 5432, 27017, 1521, 445]

    for test_port in ports_to_try:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, test_port))
            sock.close()

            if result == 0:
                return True, f"Host {host} is reachable (port {test_port})"
        except socket.gaierror:
            # DNS resolution failed
            return False, f"Cannot resolve hostname: {host}"
        except socket.timeout:
            continue
        except Exception:
            continue

    return False, f"Host {host} is not reachable on common ports"


def _ping_icmp(host: str, timeout: int) -> Tuple[bool, str]:
    """
    Ping host using ICMP (system ping command).

    Args:
        host: Hostname or IP address
        timeout: Timeout in seconds

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Determine ping command based on OS
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout), host]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower() == "windows" else 0
        )

        if result.returncode == 0:
            return True, f"Host {host} is reachable (ICMP)"
        else:
            return False, f"Host {host} did not respond to ping"

    except subprocess.TimeoutExpired:
        return False, f"Ping timeout for host {host}"
    except FileNotFoundError:
        return False, "Ping command not available"
    except Exception as e:
        return False, f"Ping error: {str(e)}"


def extract_host_from_connection_string(connection_string: str, db_type: str = None) -> Optional[str]:
    """
    Extract host/server from a connection string.

    Args:
        connection_string: Database connection string
        db_type: Database type hint (sqlserver, mysql, postgresql, etc.)

    Returns:
        Host/server name or None if not found
    """
    if not connection_string:
        return None

    conn_str_lower = connection_string.lower()

    # SQLite - no host needed
    if "sqlite" in conn_str_lower or connection_string.endswith(".db"):
        return None

    # Try common patterns
    patterns = [
        # ODBC style: Server=hostname or SERVER=hostname
        r'(?:server|data source)\s*=\s*([^;,\s]+)',
        # URL style: //hostname:port/ or //hostname/
        r'://(?:[^:@]+(?::[^@]+)?@)?([^:/]+)',
        # Host= style
        r'host\s*=\s*([^;,\s]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, connection_string, re.IGNORECASE)
        if match:
            host = match.group(1).strip()
            # Remove instance name if present (e.g., SERVER\INSTANCE)
            if '\\' in host:
                host = host.split('\\')[0]
            return host

    return None


def check_server_reachable(connection_string: str, db_type: str = None, timeout: int = 3) -> Tuple[bool, Optional[str]]:
    """
    Check if the server in a connection string is reachable.

    Args:
        connection_string: Database connection string
        db_type: Database type hint
        timeout: Timeout in seconds

    Returns:
        Tuple of (reachable: bool, error_message: str or None)
        If reachable, error_message is None
        If not reachable, error_message contains the VPN suggestion
    """
    host = extract_host_from_connection_string(connection_string, db_type)

    # No host to check (e.g., SQLite)
    if not host:
        return True, None

    # Skip localhost
    if host.lower() in ('localhost', '127.0.0.1', '::1', '.'):
        return True, None

    success, message = ping_host(host, timeout)

    if success:
        return True, None
    else:
        # Return VPN suggestion message
        return False, f"Cannot reach server '{host}'.\n\nIs a VPN required for this connection?\nEst-ce que cette connexion requiert un VPN ?"
