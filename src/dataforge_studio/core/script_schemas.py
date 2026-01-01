"""
Script Schemas - Predefined parameter schemas for built-in scripts.

This module defines the parameters_schema for built-in scripts.
Each schema function returns a list of parameter definitions that can be
passed to Script.set_parameters() or create_parameters_schema().

Example usage:
    from dataforge_studio.core.script_schemas import get_dispatch_schema
    from dataforge_studio.core.parameter_types import create_parameters_schema

    schema = get_dispatch_schema()
    script.parameters_schema = create_parameters_schema(schema)
"""
from pathlib import Path
from .parameter_types import ParameterType, create_parameter

# Base path for built-in scripts
_SCRIPTS_DIR = Path(__file__).parent.parent / "plugins" / "scripts" / "available"


def get_dispatch_schema():
    """
    Get parameter schema for the 'dispatch' script.

    The dispatch script moves files from a source folder to subfolders
    based on filename prefix patterns.

    Example: With pattern '[d1]_[d2]*':
    - File 'CLIENT_PROJECT_report.csv' -> dispatched to 'CLIENT/PROJECT/'
    - File 'ABC_DEF_data.xlsx' -> dispatched to 'ABC/DEF/'

    Returns:
        List of parameter definitions
    """
    return [
        create_parameter(
            name="source_folder",
            param_type=ParameterType.ROOTFOLDER,
            label="Dossier source",
            required=True,
            description="Dossier contenant les fichiers à dispatcher"
        ),
        create_parameter(
            name="pattern",
            param_type=ParameterType.PATTERN,
            label="Pattern de dispatch",
            required=True,
            description="Pattern pour extraire les niveaux de dossier du nom de fichier",
            default="[d1]_[d2]*",
            options={
                "example": "[d1]_[d2]* -> CLIENT_PROJECT_file.csv -> CLIENT/PROJECT/",
                "variables": ["[d1]", "[d2]", "[d3]", "[d4]", "*"]
            }
        ),
        create_parameter(
            name="recursive",
            param_type=ParameterType.BOOLEAN,
            label="Sous-dossiers",
            required=False,
            description="Traiter aussi les fichiers dans les sous-dossiers",
            default=False
        ),
        create_parameter(
            name="create_folders",
            param_type=ParameterType.BOOLEAN,
            label="Creer les dossiers",
            required=False,
            description="Creer automatiquement les dossiers de destination s'ils n'existent pas",
            default=True
        ),
        create_parameter(
            name="overwrite",
            param_type=ParameterType.BOOLEAN,
            label="Ecraser existants",
            required=False,
            description="Ecraser les fichiers existants dans le dossier de destination",
            default=False
        ),
        create_parameter(
            name="file_filter",
            param_type=ParameterType.STRING,
            label="Filtre fichiers",
            required=False,
            description="Filtre glob pour les fichiers a traiter (ex: *.csv)",
            default="*",
            options={"placeholder": "*.csv;*.xlsx"}
        ),
    ]


def get_import_csv_schema():
    """
    Get parameter schema for the 'import_csv' script.

    Imports CSV files into a database table.

    Returns:
        List of parameter definitions
    """
    return [
        create_parameter(
            name="source_folder",
            param_type=ParameterType.ROOTFOLDER,
            label="Dossier source",
            required=True,
            description="Dossier contenant les fichiers CSV"
        ),
        create_parameter(
            name="target_database",
            param_type=ParameterType.DATABASE,
            label="Base de donnees",
            required=True,
            description="Base de donnees de destination"
        ),
        create_parameter(
            name="table_name",
            param_type=ParameterType.STRING,
            label="Nom de table",
            required=True,
            description="Nom de la table de destination",
            options={"placeholder": "imported_data"}
        ),
        create_parameter(
            name="delimiter",
            param_type=ParameterType.ENUM,
            label="Separateur",
            required=False,
            description="Separateur de colonnes",
            default=";",
            options={
                "choices": [
                    {"value": ";", "label": "Point-virgule (;)"},
                    {"value": ",", "label": "Virgule (,)"},
                    {"value": "\t", "label": "Tabulation"},
                    {"value": "|", "label": "Pipe (|)"}
                ]
            }
        ),
        create_parameter(
            name="encoding",
            param_type=ParameterType.ENUM,
            label="Encodage",
            required=False,
            description="Encodage des fichiers",
            default="utf-8",
            options={
                "choices": [
                    {"value": "utf-8", "label": "UTF-8"},
                    {"value": "utf-8-sig", "label": "UTF-8 BOM"},
                    {"value": "latin-1", "label": "Latin-1 (ISO-8859-1)"},
                    {"value": "cp1252", "label": "Windows-1252"}
                ]
            }
        ),
        create_parameter(
            name="truncate_table",
            param_type=ParameterType.BOOLEAN,
            label="Vider la table",
            required=False,
            description="Vider la table avant import",
            default=False
        ),
    ]


def get_export_query_schema():
    """
    Get parameter schema for the 'export_query' script.

    Exports query results to files.

    Returns:
        List of parameter definitions
    """
    return [
        create_parameter(
            name="query",
            param_type=ParameterType.QUERY,
            label="Requete",
            required=True,
            description="Requete a executer"
        ),
        create_parameter(
            name="output_folder",
            param_type=ParameterType.ROOTFOLDER,
            label="Dossier de sortie",
            required=True,
            description="Dossier de destination des fichiers"
        ),
        create_parameter(
            name="output_format",
            param_type=ParameterType.ENUM,
            label="Format",
            required=True,
            description="Format de sortie",
            default="csv",
            options={
                "choices": [
                    {"value": "csv", "label": "CSV"},
                    {"value": "xlsx", "label": "Excel (XLSX)"},
                    {"value": "json", "label": "JSON"},
                    {"value": "parquet", "label": "Parquet"}
                ]
            }
        ),
        create_parameter(
            name="filename_pattern",
            param_type=ParameterType.STRING,
            label="Nom de fichier",
            required=False,
            description="Pattern pour le nom de fichier (variables: {date}, {time}, {query_name})",
            default="{query_name}_{date}",
            options={"placeholder": "export_{date}_{time}"}
        ),
    ]


def get_backup_schema():
    """
    Get parameter schema for the 'backup' script.

    Backs up files with compression.

    Returns:
        List of parameter definitions
    """
    return [
        create_parameter(
            name="source_folder",
            param_type=ParameterType.ROOTFOLDER,
            label="Dossier source",
            required=True,
            description="Dossier a sauvegarder"
        ),
        create_parameter(
            name="backup_folder",
            param_type=ParameterType.ROOTFOLDER,
            label="Dossier de backup",
            required=True,
            description="Dossier de destination des sauvegardes"
        ),
        create_parameter(
            name="compression",
            param_type=ParameterType.ENUM,
            label="Compression",
            required=False,
            description="Type de compression",
            default="zip",
            options={
                "choices": [
                    {"value": "none", "label": "Aucune"},
                    {"value": "zip", "label": "ZIP"},
                    {"value": "gzip", "label": "GZIP"},
                    {"value": "7z", "label": "7-Zip"}
                ]
            }
        ),
        create_parameter(
            name="include_subfolders",
            param_type=ParameterType.BOOLEAN,
            label="Inclure sous-dossiers",
            required=False,
            description="Inclure les sous-dossiers dans la sauvegarde",
            default=True
        ),
        create_parameter(
            name="retention_days",
            param_type=ParameterType.NUMBER,
            label="Retention (jours)",
            required=False,
            description="Nombre de jours de retention des sauvegardes (0 = illimite)",
            default=30,
            options={"min": 0, "max": 365, "decimals": 0}
        ),
    ]


def get_builtin_scripts() -> dict:
    """
    Get all built-in scripts from YAML templates.

    Returns:
        Dict mapping script_id to script info dict
    """
    from .script_template_loader import get_template_loader

    loader = get_template_loader()
    templates = loader.get_all_templates()

    result = {}
    for template in templates:
        result[template.id] = {
            "name": template.name,
            "description": template.description,
            "script_type": template.script_type,
            "file_path": template.file_path,
            "parameters": template.parameters,
        }

    return result


# For backward compatibility - lazily loaded
class _BuiltinScriptsProxy(dict):
    """Proxy dict that loads templates on first access."""

    def __init__(self):
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            super().clear()
            super().update(get_builtin_scripts())
            self._loaded = True

    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)

    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)

    def __iter__(self):
        self._ensure_loaded()
        return super().__iter__()

    def items(self):
        self._ensure_loaded()
        return super().items()

    def keys(self):
        self._ensure_loaded()
        return super().keys()

    def values(self):
        self._ensure_loaded()
        return super().values()

    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)


BUILTIN_SCRIPTS = _BuiltinScriptsProxy()


def get_builtin_script_info(script_key: str) -> dict:
    """
    Get information about a built-in script.

    Args:
        script_key: Key in BUILTIN_SCRIPTS dict

    Returns:
        Dict with name, description, script_type, and parameters schema
    """
    if script_key not in BUILTIN_SCRIPTS:
        return None

    info = BUILTIN_SCRIPTS[script_key].copy()
    schema_func = info.pop("get_schema")
    info["parameters"] = schema_func()
    return info
