"""
Script Template Loader - Discovers and loads script templates from YAML files.

Templates are stored in plugins/scripts/available/ as .yaml files.
Each YAML file defines a script template with its metadata and parameters.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)

# Default path for built-in scripts
_DEFAULT_SCRIPTS_DIR = Path(__file__).parent.parent / "plugins" / "scripts" / "available"


@dataclass
class ScriptTemplate:
    """A script template loaded from YAML."""
    id: str
    name: str
    description: str
    version: str
    script_type: str
    file_path: str
    entry_point: str
    author: str
    requires: List[str] = field(default_factory=list)
    parameters: List[Dict] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    @property
    def has_file(self) -> bool:
        """Check if the script file exists."""
        return self.file_path and Path(self.file_path).is_file()

    def get_source_code(self) -> Optional[str]:
        """Read and return the source code from file_path."""
        if not self.has_file:
            return None
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading script file {self.file_path}: {e}")
            return None


class ScriptTemplateLoader:
    """
    Loads script templates from YAML files.

    Usage:
        loader = ScriptTemplateLoader()
        templates = loader.get_all_templates()
        template = loader.get_template("file_dispatcher")
    """

    def __init__(self, scripts_dir: Optional[Path] = None):
        """
        Initialize the loader.

        Args:
            scripts_dir: Directory containing script YAML files.
                        Defaults to plugins/scripts/available/
        """
        self.scripts_dir = scripts_dir or _DEFAULT_SCRIPTS_DIR
        self._cache: Dict[str, ScriptTemplate] = {}
        self._loaded = False

    def _load_templates(self, force: bool = False):
        """Load all templates from YAML files."""
        if self._loaded and not force:
            return

        self._cache.clear()

        if not self.scripts_dir.exists():
            logger.warning(f"Scripts directory does not exist: {self.scripts_dir}")
            self._loaded = True
            return

        for yaml_file in self.scripts_dir.glob("*.yaml"):
            try:
                template = self._load_template_file(yaml_file)
                if template:
                    self._cache[template.id] = template
                    logger.debug(f"Loaded script template: {template.id}")
            except Exception as e:
                logger.error(f"Error loading template {yaml_file}: {e}")

        self._loaded = True
        logger.info(f"Loaded {len(self._cache)} script templates from {self.scripts_dir}")

    def _load_template_file(self, yaml_path: Path) -> Optional[ScriptTemplate]:
        """Load a single template from a YAML file."""
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        # Resolve file_path relative to YAML location
        file_path = data.get("file_path", "")
        if not file_path:
            # Default: same name as YAML but with .py extension
            py_file = yaml_path.with_suffix(".py")
            if py_file.exists():
                file_path = str(py_file)
        elif not Path(file_path).is_absolute():
            # Relative path: resolve from YAML directory
            file_path = str(yaml_path.parent / file_path)

        # Parse parameters from YAML format
        parameters = self._parse_parameters(data.get("parameters", []))

        return ScriptTemplate(
            id=data.get("id", yaml_path.stem),
            name=data.get("name", yaml_path.stem),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            script_type=data.get("script_type", "python"),
            file_path=file_path,
            entry_point=data.get("entry_point", "run"),
            author=data.get("author", ""),
            requires=data.get("requires", []),
            parameters=parameters,
            aliases=data.get("aliases", []),
        )

    def _parse_parameters(self, params_data: List[Dict]) -> List[Dict]:
        """Parse parameters from YAML format to internal format."""
        from .parameter_types import ParameterType, create_parameter

        parameters = []
        for p in params_data:
            # Map YAML type to ParameterType
            type_mapping = {
                "rootfolder": ParameterType.ROOTFOLDER,
                "database": ParameterType.DATABASE,
                "query": ParameterType.QUERY,
                "script": ParameterType.SCRIPT,
                "file": ParameterType.PATH,
                "path": ParameterType.PATH,
                "string": ParameterType.STRING,
                "int": ParameterType.NUMBER,
                "number": ParameterType.NUMBER,
                "bool": ParameterType.BOOLEAN,
                "boolean": ParameterType.BOOLEAN,
                "json": ParameterType.STRING,  # JSON stored as string
                "enum": ParameterType.ENUM,
                "choice": ParameterType.ENUM,
                "date": ParameterType.DATE,
                "datetime": ParameterType.DATETIME,
                "pattern": ParameterType.PATTERN,
            }

            param_type = type_mapping.get(p.get("type", "string"), ParameterType.STRING)

            param = create_parameter(
                name=p.get("name", ""),
                param_type=param_type,
                label=p.get("label", p.get("name", "")),
                required=p.get("required", False),
                description=p.get("description", ""),
                default=p.get("default"),
                options=p.get("options"),
            )
            parameters.append(param)

        return parameters

    def get_all_templates(self) -> List[ScriptTemplate]:
        """Get all available script templates."""
        self._load_templates()
        return list(self._cache.values())

    def get_template(self, template_id: str) -> Optional[ScriptTemplate]:
        """Get a specific template by ID."""
        self._load_templates()
        return self._cache.get(template_id)

    def get_template_by_name(self, name: str) -> Optional[ScriptTemplate]:
        """Get a template by name (case-insensitive)."""
        self._load_templates()
        name_lower = name.lower()
        for template in self._cache.values():
            # Check main name
            if template.name.lower() == name_lower:
                return template
            # Check aliases
            for alias in template.aliases:
                if alias.lower() == name_lower:
                    return template
        return None

    def get_file_path_for_script(self, script_name: str, script_type: str = None) -> Optional[str]:
        """
        Get the file path for a script by matching it to a template.

        Args:
            script_name: Name of the script
            script_type: Optional script type to help matching

        Returns:
            File path if a matching template is found, None otherwise
        """
        template = self.get_template_by_name(script_name)
        if template and template.has_file:
            return template.file_path

        # Try matching by ID (lowercase, underscores)
        script_id = script_name.lower().replace(" ", "_")
        template = self.get_template(script_id)
        if template and template.has_file:
            return template.file_path

        return None

    def reload(self):
        """Force reload all templates."""
        self._load_templates(force=True)


# Singleton instance
_loader: Optional[ScriptTemplateLoader] = None


def get_template_loader() -> ScriptTemplateLoader:
    """Get the singleton template loader instance."""
    global _loader
    if _loader is None:
        _loader = ScriptTemplateLoader()
    return _loader
