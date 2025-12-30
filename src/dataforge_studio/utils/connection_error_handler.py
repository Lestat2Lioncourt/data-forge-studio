"""
Connection Error Handler - User-friendly database connection error messages

Translates cryptic database error messages into user-friendly messages
with suggestions for resolution.
"""

import re
from typing import Tuple, Optional
from dataclasses import dataclass

import logging
logger = logging.getLogger(__name__)


@dataclass
class ConnectionErrorInfo:
    """Structured connection error information."""
    title: str  # Short error title
    message: str  # User-friendly message
    suggestion: str  # What to do to fix it
    original_error: str  # Original error for debugging

    def format_full(self) -> str:
        """Format complete error message for display."""
        parts = [self.title, "", self.message]
        if self.suggestion:
            parts.extend(["", "Suggestion:", self.suggestion])
        return "\n".join(parts)

    def format_short(self) -> str:
        """Format short error message."""
        return f"{self.title}\n\n{self.message}"


# Error patterns for different database types
# Format: (regex_pattern, title, message_template, suggestion)
# Use {match} in message_template to include regex group(1)

SQLSERVER_PATTERNS = [
    # Login failed
    (
        r"Login failed for user ['\"]?(\w+)['\"]?",
        "Authentification échouée",
        "L'utilisateur '{match}' n'a pas pu se connecter.",
        "Vérifiez le nom d'utilisateur et le mot de passe. "
        "Pour l'authentification Windows, vérifiez que vous êtes connecté au domaine."
    ),
    # Cannot open database
    (
        r"Cannot open database ['\"]?(\w+)['\"]?",
        "Base de données inaccessible",
        "La base de données '{match}' n'est pas accessible.",
        "Vérifiez que la base de données existe et que vous avez les droits d'accès."
    ),
    # Server not found / connection timeout
    (
        r"(?:TCP Provider|Named Pipes Provider).*(?:error: 40|Timeout expired)",
        "Serveur non accessible",
        "Impossible de joindre le serveur SQL Server.",
        "Vérifiez que:\n"
        "  - Le serveur est démarré\n"
        "  - Le nom du serveur est correct\n"
        "  - Le firewall autorise les connexions\n"
        "  - Le VPN est actif (si nécessaire)"
    ),
    # Connection refused
    (
        r"(?:connection refused|actively refused)",
        "Connexion refusée",
        "Le serveur a refusé la connexion.",
        "Vérifiez que SQL Server est démarré et écoute sur le bon port."
    ),
    # Driver not found
    (
        r"(?:driver|ODBC Driver).*(?:not found|introuvable|non trouvé)",
        "Driver ODBC manquant",
        "Le driver ODBC pour SQL Server n'est pas installé.",
        "Installez le driver 'ODBC Driver 17 for SQL Server' depuis:\n"
        "https://docs.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server"
    ),
    # Network error
    (
        r"(?:network-related|network error|réseau)",
        "Erreur réseau",
        "Une erreur réseau est survenue lors de la connexion.",
        "Vérifiez votre connexion réseau et le VPN si nécessaire."
    ),
    # SSL/TLS error
    (
        r"(?:SSL|TLS|certificate|certificat)",
        "Erreur SSL/TLS",
        "Problème de certificat ou de chiffrement.",
        "Ajoutez 'TrustServerCertificate=Yes' à la chaîne de connexion "
        "ou vérifiez la configuration SSL du serveur."
    ),
    # Permission denied
    (
        r"(?:permission denied|access denied|accès refusé)",
        "Accès refusé",
        "Vous n'avez pas les permissions nécessaires.",
        "Contactez l'administrateur de la base de données pour obtenir les droits d'accès."
    ),
]

POSTGRESQL_PATTERNS = [
    # Authentication failed
    (
        r"password authentication failed for user ['\"]?(\w+)['\"]?",
        "Authentification échouée",
        "Mot de passe incorrect pour l'utilisateur '{match}'.",
        "Vérifiez le mot de passe ou demandez à l'administrateur de le réinitialiser."
    ),
    # Database does not exist
    (
        r"database ['\"]?(\w+)['\"]? does not exist",
        "Base de données inexistante",
        "La base de données '{match}' n'existe pas.",
        "Vérifiez le nom de la base de données ou créez-la d'abord."
    ),
    # Connection refused
    (
        r"(?:connection refused|could not connect)",
        "Connexion refusée",
        "Impossible de se connecter au serveur PostgreSQL.",
        "Vérifiez que:\n"
        "  - PostgreSQL est démarré\n"
        "  - Le serveur écoute sur le bon port (par défaut: 5432)\n"
        "  - pg_hba.conf autorise votre connexion"
    ),
    # Host not found
    (
        r"(?:could not translate host name|host not found)",
        "Serveur introuvable",
        "Le serveur PostgreSQL est introuvable.",
        "Vérifiez le nom d'hôte ou l'adresse IP du serveur."
    ),
    # SSL error
    (
        r"(?:SSL|sslmode)",
        "Erreur SSL",
        "Problème de connexion SSL.",
        "Essayez d'ajouter '?sslmode=disable' ou '?sslmode=require' à l'URL de connexion."
    ),
    # Timeout
    (
        r"(?:timeout|timed out)",
        "Délai d'attente dépassé",
        "Le serveur n'a pas répondu dans le délai imparti.",
        "Vérifiez la connexion réseau et le VPN si nécessaire."
    ),
    # Role does not exist
    (
        r"role ['\"]?(\w+)['\"]? does not exist",
        "Utilisateur inexistant",
        "L'utilisateur '{match}' n'existe pas sur le serveur.",
        "Vérifiez le nom d'utilisateur ou demandez à l'administrateur de créer le compte."
    ),
]

SQLITE_PATTERNS = [
    # File not found
    (
        r"(?:unable to open|no such file)",
        "Fichier introuvable",
        "Le fichier de base de données SQLite n'existe pas.",
        "Vérifiez le chemin du fichier .db ou .sqlite."
    ),
    # Database locked
    (
        r"database is locked",
        "Base de données verrouillée",
        "La base de données est utilisée par un autre processus.",
        "Fermez les autres applications utilisant ce fichier, ou attendez quelques instants."
    ),
    # Read-only
    (
        r"(?:read-only|readonly)",
        "Lecture seule",
        "La base de données est en lecture seule.",
        "Vérifiez les permissions du fichier ou du dossier parent."
    ),
    # Corrupt database
    (
        r"(?:corrupt|malformed)",
        "Base de données corrompue",
        "Le fichier de base de données semble corrompu.",
        "Essayez de restaurer une sauvegarde ou utilisez 'PRAGMA integrity_check'."
    ),
]

ACCESS_PATTERNS = [
    # File not found
    (
        r"(?:file not found|introuvable|n'existe pas)",
        "Fichier introuvable",
        "Le fichier Access (.mdb/.accdb) n'existe pas.",
        "Vérifiez le chemin du fichier."
    ),
    # File in use
    (
        r"(?:in use|utilisé|locked)",
        "Fichier en cours d'utilisation",
        "Le fichier Access est ouvert par une autre application.",
        "Fermez Microsoft Access ou les autres applications utilisant ce fichier."
    ),
    # Driver not found
    (
        r"(?:driver|Microsoft Access Driver).*(?:not found|introuvable)",
        "Driver Access manquant",
        "Le driver ODBC pour Microsoft Access n'est pas installé.",
        "Installez Microsoft Access Database Engine depuis:\n"
        "https://www.microsoft.com/en-us/download/details.aspx?id=54920"
    ),
]

# Generic patterns (for all database types)
GENERIC_PATTERNS = [
    # Timeout
    (
        r"(?:timeout|timed out|délai)",
        "Délai d'attente dépassé",
        "La connexion a pris trop de temps.",
        "Vérifiez la connexion réseau et réessayez."
    ),
    # Connection refused
    (
        r"(?:refused|refusée)",
        "Connexion refusée",
        "Le serveur a refusé la connexion.",
        "Vérifiez que le serveur de base de données est démarré."
    ),
    # Network unreachable
    (
        r"(?:unreachable|inaccessible|network)",
        "Réseau inaccessible",
        "Le serveur n'est pas accessible sur le réseau.",
        "Vérifiez votre connexion réseau et le VPN si nécessaire."
    ),
]


def parse_connection_error(
    error: Exception,
    db_type: str = ""
) -> ConnectionErrorInfo:
    """
    Parse a database connection error and return user-friendly information.

    Args:
        error: The exception that occurred
        db_type: Database type (sqlserver, postgresql, sqlite, access)

    Returns:
        ConnectionErrorInfo with user-friendly message and suggestion
    """
    error_str = str(error).lower()
    original_error = str(error)

    # Select patterns based on database type
    patterns = []
    if db_type == "sqlserver":
        patterns = SQLSERVER_PATTERNS + GENERIC_PATTERNS
    elif db_type == "postgresql":
        patterns = POSTGRESQL_PATTERNS + GENERIC_PATTERNS
    elif db_type == "sqlite":
        patterns = SQLITE_PATTERNS + GENERIC_PATTERNS
    elif db_type == "access":
        patterns = ACCESS_PATTERNS + GENERIC_PATTERNS
    else:
        # Try all patterns
        patterns = (
            SQLSERVER_PATTERNS +
            POSTGRESQL_PATTERNS +
            SQLITE_PATTERNS +
            ACCESS_PATTERNS +
            GENERIC_PATTERNS
        )

    # Try to match error against known patterns
    for pattern, title, message_template, suggestion in patterns:
        match = re.search(pattern, error_str, re.IGNORECASE)
        if match:
            # Replace {match} with captured group if present
            message = message_template
            if "{match}" in message and match.groups():
                message = message.replace("{match}", match.group(1))

            return ConnectionErrorInfo(
                title=title,
                message=message,
                suggestion=suggestion,
                original_error=original_error
            )

    # No pattern matched - return generic error
    return ConnectionErrorInfo(
        title="Erreur de connexion",
        message="Une erreur est survenue lors de la connexion à la base de données.",
        suggestion="Vérifiez les paramètres de connexion et réessayez.",
        original_error=original_error
    )


def format_connection_error(
    error: Exception,
    db_type: str = "",
    include_original: bool = True
) -> str:
    """
    Format a connection error for display to the user.

    Args:
        error: The exception that occurred
        db_type: Database type
        include_original: Whether to include original error message

    Returns:
        Formatted error message string
    """
    info = parse_connection_error(error, db_type)

    parts = [info.title, "", info.message]

    if info.suggestion:
        parts.extend(["", "💡 Suggestion:", info.suggestion])

    if include_original:
        parts.extend(["", "---", "Détails techniques:", info.original_error[:500]])

    return "\n".join(parts)


def get_server_unreachable_message(
    server_name: str,
    db_type: str = ""
) -> str:
    """
    Get a user-friendly message for server unreachable errors.

    Args:
        server_name: Name of the server
        db_type: Database type

    Returns:
        Formatted error message
    """
    suggestions = [
        f"Le serveur '{server_name}' n'est pas accessible.",
        "",
        "Vérifiez que:",
        "  • Le serveur est démarré et en ligne",
        "  • Le nom ou l'adresse IP est correct",
        "  • Le firewall autorise les connexions",
    ]

    # Add VPN suggestion for remote servers
    if not _is_local_server(server_name):
        suggestions.append("  • Le VPN est actif (si requis)")

    # Add port suggestions based on database type
    if db_type == "sqlserver":
        suggestions.append("  • SQL Server écoute sur le port 1433")
    elif db_type == "postgresql":
        suggestions.append("  • PostgreSQL écoute sur le port 5432")
    elif db_type == "mysql":
        suggestions.append("  • MySQL écoute sur le port 3306")

    return "\n".join(suggestions)


def _is_local_server(server_name: str) -> bool:
    """Check if server name refers to localhost."""
    local_names = ["localhost", "127.0.0.1", ".", "(local)", "::1"]
    return server_name.lower().split("\\")[0] in local_names
