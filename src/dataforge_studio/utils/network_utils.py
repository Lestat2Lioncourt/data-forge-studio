"""
Network utilities for connection testing.
"""

import socket
import subprocess
import platform
import re
import os
from pathlib import Path
from typing import Optional, Tuple

import logging
logger = logging.getLogger(__name__)


def ping_host(host: str, timeout: int = 3, port: int = None) -> Tuple[bool, str]:
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
        reachable, msg = _check_host_socket(host, timeout, port=port)
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
    # Only probe the port the connection actually uses. Sweeping every
    # known database port (1433, 445, ...) reaches services the user never
    # asked about and shows up as scanning on monitored networks.
    ports_to_try = [port] if port else sorted(set(DEFAULT_PORTS.values()))

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
        except OSError:
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


DEFAULT_PORTS = {
    "sqlserver": 1433,
    "mysql": 3306,
    "mariadb": 3306,
    "postgresql": 5432,
    "mongodb": 27017,
    "oracle": 1521,
}


def extract_host_port_from_connection_string(
        connection_string: str, db_type: str = None) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract host and port from a connection string.

    Returns (host, port). Either may be None. The port matters: probing a
    server on a port it does not serve looks like a port scan to network
    equipment, and tells us nothing about the database being reachable.
    """
    if not connection_string:
        return None, None

    conn_str_lower = connection_string.lower()
    if "sqlite" in conn_str_lower or connection_string.endswith(".db"):
        return None, None

    host = port = None

    if "://" in connection_string:
        # URL style: scheme://[user[:password]@]host[:port][/database]
        after_scheme = connection_string.split("://", 1)[1]
        # Split on the LAST '@': a password may legitimately contain one, and
        # splitting on the first would take part of it for the host.
        _userinfo, sep, remainder = after_scheme.rpartition("@")
        if not sep:
            remainder = after_scheme
        # Only cut the path AFTER the credentials — a password may contain '/'
        host_port = remainder.split("/", 1)[0]

        if host_port.startswith("["):          # IPv6 literal
            host, _, rest = host_port.partition("]")
            host = host.lstrip("[")
            port_part = rest.lstrip(":")
        else:
            host, _, port_part = host_port.partition(":")

        if port_part.isdigit():
            port = int(port_part)
    else:
        # ODBC / key=value style
        m = re.search(r'(?:server|data source|host)\s*=\s*([^;]+)', connection_string,
                      re.IGNORECASE)
        if m:
            host = m.group(1).strip()
            # SQL Server writes the port after a comma: SERVER=host,1433
            if "," in host:
                host, _, port_part = host.partition(",")
                host, port_part = host.strip(), port_part.strip()
                if port_part.isdigit():
                    port = int(port_part)
        m = re.search(r'port\s*=\s*(\d+)', connection_string, re.IGNORECASE)
        if m:
            port = int(m.group(1))

    if host:
        # Drop a named instance (SERVER\INSTANCE) — not part of the hostname
        host = host.split("\\")[0].strip()

    if port is None and db_type:
        port = DEFAULT_PORTS.get(db_type.lower())

    return (host or None), port


def extract_host_from_connection_string(connection_string: str, db_type: str = None) -> Optional[str]:
    """Extract host/server from a connection string (see the *_port variant)."""
    return extract_host_port_from_connection_string(connection_string, db_type)[0]


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
    host, port = extract_host_port_from_connection_string(connection_string, db_type)

    # No host to check (e.g., SQLite)
    if not host:
        return True, None

    # Skip localhost
    if host.lower() in ('localhost', '127.0.0.1', '::1', '.'):
        return True, None

    success, message = ping_host(host, timeout, port=port)

    if success:
        return True, None
    else:
        # Return VPN suggestion message
        return False, f"Cannot reach server '{host}'.\n\nIs a VPN required for this connection?\nEst-ce que cette connexion requiert un VPN ?"


def check_path_accessible(path: str, timeout: int = 3) -> Tuple[bool, Optional[str]]:
    """
    Check if a file or directory path is accessible.
    Works for local paths and network paths (UNC).

    Args:
        path: File or directory path
        timeout: Timeout in seconds (for network paths)

    Returns:
        Tuple of (accessible: bool, error_message: str or None)
    """
    if not path:
        return False, "Chemin non spécifié"

    try:
        p = Path(path)

        # For network paths (UNC), try to check if parent exists first
        if str(path).startswith("\\\\") or str(path).startswith("//"):
            # Extract server name from UNC path
            parts = str(path).replace("\\", "/").split("/")
            server = parts[2] if len(parts) > 2 else None
            if server:
                # Check if server is reachable
                success, msg = ping_host(server, timeout)
                if not success:
                    return False, f"Serveur réseau non accessible : {server}"

        # Check if path exists
        if p.exists():
            # Check if readable
            if p.is_file():
                if os.access(path, os.R_OK):
                    return True, None
                else:
                    return False, f"Fichier non lisible : {path}"
            elif p.is_dir():
                if os.access(path, os.R_OK | os.X_OK):
                    return True, None
                else:
                    return False, f"Dossier non accessible : {path}"
        else:
            return False, f"Chemin introuvable : {path}"

    except PermissionError:
        return False, f"Accès refusé : {path}"
    except OSError as e:
        return False, f"Erreur d'accès : {e}"
    except Exception as e:
        return False, f"Erreur : {e}"

    return False, f"Chemin non accessible : {path}"


def is_connection_reachable(db_conn, timeout: int = 3) -> Tuple[bool, Optional[str]]:
    """
    Check if a database connection is reachable.
    Unified function for all database types.

    Args:
        db_conn: DatabaseConnection object with db_type and connection_string
        timeout: Timeout in seconds

    Returns:
        Tuple of (reachable: bool, error_message: str or None)
    """
    if not db_conn:
        return False, "Connexion non spécifiée"

    db_type = getattr(db_conn, 'db_type', '').lower()
    conn_str = getattr(db_conn, 'connection_string', '')

    # File-based databases (SQLite, Access)
    if db_type in ('sqlite', 'access', 'msaccess'):
        # Extract path from connection string
        db_path = None

        if conn_str.startswith("sqlite:///"):
            db_path = conn_str.replace("sqlite:///", "")
        elif "Database=" in conn_str:
            match = re.search(r'Database=([^;]+)', conn_str)
            db_path = match.group(1) if match else None
        elif "DBQ=" in conn_str.upper():
            match = re.search(r'DBQ=([^;]+)', conn_str, re.IGNORECASE)
            db_path = match.group(1) if match else None
        else:
            # Assume the whole string is a path
            db_path = conn_str

        if db_path:
            return check_path_accessible(db_path, timeout)
        else:
            return False, "Chemin de base de données non trouvé"

    # Server-based databases (SQL Server, MySQL, PostgreSQL, etc.)
    else:
        return check_server_reachable(conn_str, db_type, timeout)
