"""
Script Dialog - Dialog for creating/editing Scripts with parameter schema editor.
"""
from typing import Optional, List, Dict, Any
import json

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QDialogButtonBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSpinBox, QAbstractItemView,
    QWidget, QLabel, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt

from ..core.i18n_bridge import tr
from ..widgets.dialog_helper import DialogHelper
from ...database.models import Script
from ...database.config_db import get_config_db
from ...core.parameter_types import (
    ParameterType, create_parameter, create_parameters_schema,
    parse_parameters_schema
)
from ...core.script_schemas import BUILTIN_SCRIPTS

import logging
logger = logging.getLogger(__name__)


# Script types available
SCRIPT_TYPES = [
    ("python", "Python"),
    ("powershell", "PowerShell"),
    ("bash", "Bash/Shell"),
    ("batch", "Batch/CMD"),
    ("sql", "SQL"),
    ("javascript", "JavaScript"),
    ("custom", "Autre"),
]

# Map file extensions to script types
EXTENSION_TO_SCRIPT_TYPE = {
    ".py": "python",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".psd1": "powershell",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".bat": "batch",
    ".cmd": "batch",
    ".sql": "sql",
    ".js": "javascript",
}


class ParameterEditorDialog(QDialog):
    """Dialog for editing a single parameter definition."""

    def __init__(self, parent=None, parameter: Optional[Dict] = None):
        super().__init__(parent)
        self.parameter = parameter or {}
        self.setWindowTitle("Editer le parametre" if parameter else "Nouveau parametre")
        self.setMinimumWidth(500)
        self._setup_ui()
        self._load_parameter()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Name (identifier)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("ex: source_folder")
        form.addRow("Identifiant:", self.name_edit)

        # Label (display name)
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("ex: Dossier source")
        form.addRow("Libelle:", self.label_edit)

        # Type
        self.type_combo = QComboBox()
        for pt in ParameterType:
            self.type_combo.addItem(pt.value, pt.value)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Type:", self.type_combo)

        # Required
        self.required_cb = QCheckBox()
        self.required_cb.setChecked(True)
        form.addRow("Requis:", self.required_cb)

        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Description du parametre...")
        form.addRow("Description:", self.description_edit)

        # Default value
        self.default_edit = QLineEdit()
        self.default_edit.setPlaceholderText("Valeur par defaut (optionnel)")
        form.addRow("Defaut:", self.default_edit)

        # Options (JSON for complex options)
        self.options_edit = QTextEdit()
        self.options_edit.setMaximumHeight(80)
        self.options_edit.setPlaceholderText('{"choices": [...], "min": 0, "max": 100}')
        form.addRow("Options (JSON):", self.options_edit)

        layout.addLayout(form)

        # Type-specific help
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.help_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Initial help text
        self._on_type_changed()

    def _on_type_changed(self):
        """Update help text based on selected type."""
        param_type = self.type_combo.currentData()
        help_texts = {
            "rootfolder": "Reference a un RootFolder. L'utilisateur selectionnera dans une liste.",
            "database": "Reference a une connexion base de donnees.",
            "query": "Reference a une requete sauvegardee.",
            "string": "Texte libre. Options: min_length, max_length, multiline, placeholder",
            "number": "Nombre. Options: min, max, step, decimals",
            "boolean": "Case a cocher vrai/faux.",
            "enum": "Liste de choix. Options: choices=[{value, label}, ...], allow_multiple",
            "path": "Chemin fichier/dossier. Options: mode (file/folder/save), filter",
            "pattern": "Pattern de dispatch. Ex: [d1]_[d2]*",
            "date": "Selecteur de date.",
            "datetime": "Selecteur date et heure.",
        }
        self.help_label.setText(help_texts.get(param_type, ""))

    def _load_parameter(self):
        """Load existing parameter into fields."""
        if not self.parameter:
            return

        self.name_edit.setText(self.parameter.get("name", ""))
        self.label_edit.setText(self.parameter.get("label", ""))

        # Set type
        param_type = self.parameter.get("type", "string")
        idx = self.type_combo.findData(param_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        self.required_cb.setChecked(self.parameter.get("required", True))
        self.description_edit.setPlainText(self.parameter.get("description", ""))

        # Default value
        default = self.parameter.get("default")
        if default is not None:
            if isinstance(default, bool):
                self.default_edit.setText("true" if default else "false")
            else:
                self.default_edit.setText(str(default))

        # Options as JSON
        options = self.parameter.get("options", {})
        if options:
            self.options_edit.setPlainText(json.dumps(options, ensure_ascii=False, indent=2))

    def _validate_and_accept(self):
        """Validate and accept dialog."""
        name = self.name_edit.text().strip()
        if not name:
            DialogHelper.warning("L'identifiant est requis", parent=self)
            return

        # Validate name format (snake_case)
        if not name.replace("_", "").isalnum():
            DialogHelper.warning("L'identifiant doit etre en snake_case (lettres, chiffres, _)", parent=self)
            return

        label = self.label_edit.text().strip()
        if not label:
            DialogHelper.warning("Le libelle est requis", parent=self)
            return

        # Validate options JSON if provided
        options_text = self.options_edit.toPlainText().strip()
        if options_text:
            try:
                json.loads(options_text)
            except json.JSONDecodeError as e:
                DialogHelper.warning(f"Options JSON invalide: {e}", parent=self)
                return

        self.accept()

    def get_parameter(self) -> Dict:
        """Get parameter definition from dialog."""
        param_type = self.type_combo.currentData()

        # Parse default value based on type
        default_text = self.default_edit.text().strip()
        default = None
        if default_text:
            if param_type == "boolean":
                default = default_text.lower() in ("true", "1", "yes", "oui")
            elif param_type == "number":
                try:
                    default = float(default_text) if "." in default_text else int(default_text)
                except ValueError:
                    default = default_text
            else:
                default = default_text

        # Parse options JSON
        options = {}
        options_text = self.options_edit.toPlainText().strip()
        if options_text:
            try:
                options = json.loads(options_text)
            except json.JSONDecodeError:
                pass

        return create_parameter(
            name=self.name_edit.text().strip(),
            param_type=param_type,
            label=self.label_edit.text().strip(),
            required=self.required_cb.isChecked(),
            description=self.description_edit.toPlainText().strip(),
            default=default,
            options=options
        )


class ScriptDialog(QDialog):
    """Dialog for creating/editing Script with parameter schema."""

    def __init__(self, parent=None, script: Optional[Script] = None):
        super().__init__(parent)
        self.script = script
        self.is_editing = script is not None
        self.parameters: List[Dict] = []

        self.setWindowTitle("Modifier le script" if self.is_editing else "Nouveau script")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        self._setup_ui()
        self._load_script()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # === Basic Info Group ===
        info_group = QGroupBox("Informations")
        info_layout = QFormLayout(info_group)

        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nom du script")
        info_layout.addRow("Nom:", self.name_edit)

        # Type
        self.type_combo = QComboBox()
        for type_id, type_label in SCRIPT_TYPES:
            self.type_combo.addItem(type_label, type_id)
        info_layout.addRow("Type:", self.type_combo)

        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Description du script...")
        info_layout.addRow("Description:", self.description_edit)

        # File path selector
        file_path_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Chemin vers le fichier script...")
        self.file_path_edit.textChanged.connect(self._on_file_path_changed)
        file_path_layout.addWidget(self.file_path_edit)

        browse_btn = QPushButton("Parcourir...")
        browse_btn.clicked.connect(self._browse_file)
        file_path_layout.addWidget(browse_btn)

        info_layout.addRow("Fichier:", file_path_layout)

        # Template selector (for new scripts)
        if not self.is_editing:
            template_layout = QHBoxLayout()
            self.template_combo = QComboBox()
            self.template_combo.addItem("-- Aucun template --", None)
            for key, info in BUILTIN_SCRIPTS.items():
                self.template_combo.addItem(info["name"], key)
            template_layout.addWidget(self.template_combo)

            apply_btn = QPushButton("Appliquer")
            apply_btn.clicked.connect(self._apply_template)
            template_layout.addWidget(apply_btn)

            info_layout.addRow("Template:", template_layout)

        layout.addWidget(info_group)

        # === Parameters Group ===
        params_group = QGroupBox("Parametres")
        params_layout = QVBoxLayout(params_group)

        # Parameters table
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(5)
        self.params_table.setHorizontalHeaderLabels([
            "Identifiant", "Type", "Libelle", "Requis", "Defaut"
        ])
        self.params_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.params_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.params_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.params_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.params_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.params_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.params_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.params_table.doubleClicked.connect(self._edit_parameter)
        params_layout.addWidget(self.params_table)

        # Parameter buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self._add_parameter)
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("Modifier")
        edit_btn.clicked.connect(self._edit_parameter)
        btn_layout.addWidget(edit_btn)

        remove_btn = QPushButton("Supprimer")
        remove_btn.clicked.connect(self._remove_parameter)
        btn_layout.addWidget(remove_btn)

        btn_layout.addStretch()

        move_up_btn = QPushButton("Monter")
        move_up_btn.clicked.connect(self._move_parameter_up)
        btn_layout.addWidget(move_up_btn)

        move_down_btn = QPushButton("Descendre")
        move_down_btn.clicked.connect(self._move_parameter_down)
        btn_layout.addWidget(move_down_btn)

        params_layout.addLayout(btn_layout)
        layout.addWidget(params_group)

        # === Dialog Buttons ===
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_script(self):
        """Load existing script into fields."""
        if not self.script:
            return

        self.name_edit.setText(self.script.name)

        # Set type
        idx = self.type_combo.findData(self.script.script_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        self.description_edit.setPlainText(self.script.description or "")

        # Set file path
        self.file_path_edit.setText(self.script.file_path or "")

        # Load parameters
        self.parameters = self.script.get_parameters()
        self._refresh_parameters_table()

    def _browse_file(self):
        """Open file browser to select script file."""
        file_filter = (
            "Scripts (*.py *.ps1 *.sh *.bash *.bat *.cmd *.sql *.js);;"
            "Python (*.py);;"
            "PowerShell (*.ps1 *.psm1 *.psd1);;"
            "Shell (*.sh *.bash *.zsh);;"
            "Batch (*.bat *.cmd);;"
            "SQL (*.sql);;"
            "JavaScript (*.js);;"
            "Tous les fichiers (*.*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier script",
            "",
            file_filter
        )
        if file_path:
            self.file_path_edit.setText(file_path)

    def _on_file_path_changed(self, file_path: str):
        """Auto-detect script type from file extension."""
        if not file_path:
            return

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        script_type = EXTENSION_TO_SCRIPT_TYPE.get(ext)
        if script_type:
            idx = self.type_combo.findData(script_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

        # Auto-fill name from filename if empty
        if not self.name_edit.text().strip():
            basename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(basename)[0]
            self.name_edit.setText(name_without_ext)

    def _apply_template(self):
        """Apply selected template."""
        template_key = self.template_combo.currentData()
        if not template_key:
            return

        info = BUILTIN_SCRIPTS.get(template_key)
        if not info:
            return

        # Confirm if parameters exist
        if self.parameters:
            if not DialogHelper.confirm(
                "Cela va remplacer les parametres existants. Continuer?",
                parent=self
            ):
                return

        # Apply template
        self.name_edit.setText(info["name"])
        self.description_edit.setPlainText(info["description"])

        # Set type
        idx = self.type_combo.findData(info["script_type"])
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        # Set file path if provided
        file_path = info.get("file_path", "")
        if file_path:
            self.file_path_edit.setText(file_path)

        # Get parameters - either from list or schema function (backward compat)
        if "parameters" in info:
            self.parameters = info["parameters"]
            self._refresh_parameters_table()
        elif "get_schema" in info:
            # Legacy: get_schema function
            schema_func = info["get_schema"]
            self.parameters = schema_func()
            self._refresh_parameters_table()

    def _refresh_parameters_table(self):
        """Refresh the parameters table from self.parameters."""
        self.params_table.setRowCount(len(self.parameters))

        for row, param in enumerate(self.parameters):
            # Name
            name_item = QTableWidgetItem(param.get("name", ""))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.params_table.setItem(row, 0, name_item)

            # Type
            type_item = QTableWidgetItem(param.get("type", "string"))
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.params_table.setItem(row, 1, type_item)

            # Label
            label_item = QTableWidgetItem(param.get("label", ""))
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.params_table.setItem(row, 2, label_item)

            # Required
            required = "Oui" if param.get("required", True) else "Non"
            required_item = QTableWidgetItem(required)
            required_item.setFlags(required_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.params_table.setItem(row, 3, required_item)

            # Default
            default = param.get("default")
            default_str = str(default) if default is not None else ""
            default_item = QTableWidgetItem(default_str)
            default_item.setFlags(default_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.params_table.setItem(row, 4, default_item)

    def _add_parameter(self):
        """Add a new parameter."""
        dialog = ParameterEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            param = dialog.get_parameter()

            # Check for duplicate name
            for existing in self.parameters:
                if existing.get("name") == param.get("name"):
                    DialogHelper.warning(
                        f"Un parametre avec l'identifiant '{param.get('name')}' existe deja.",
                        parent=self
                    )
                    return

            self.parameters.append(param)
            self._refresh_parameters_table()

    def _edit_parameter(self):
        """Edit selected parameter."""
        row = self.params_table.currentRow()
        if row < 0 or row >= len(self.parameters):
            return

        param = self.parameters[row]
        dialog = ParameterEditorDialog(self, parameter=param)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_param = dialog.get_parameter()

            # Check for duplicate name (excluding current)
            for i, existing in enumerate(self.parameters):
                if i != row and existing.get("name") == new_param.get("name"):
                    DialogHelper.warning(
                        f"Un parametre avec l'identifiant '{new_param.get('name')}' existe deja.",
                        parent=self
                    )
                    return

            self.parameters[row] = new_param
            self._refresh_parameters_table()

    def _remove_parameter(self):
        """Remove selected parameter."""
        row = self.params_table.currentRow()
        if row < 0 or row >= len(self.parameters):
            return

        param_name = self.parameters[row].get("name", "")
        if DialogHelper.confirm(
            f"Supprimer le parametre '{param_name}'?",
            parent=self
        ):
            del self.parameters[row]
            self._refresh_parameters_table()

    def _move_parameter_up(self):
        """Move selected parameter up."""
        row = self.params_table.currentRow()
        if row <= 0:
            return

        self.parameters[row], self.parameters[row - 1] = \
            self.parameters[row - 1], self.parameters[row]
        self._refresh_parameters_table()
        self.params_table.selectRow(row - 1)

    def _move_parameter_down(self):
        """Move selected parameter down."""
        row = self.params_table.currentRow()
        if row < 0 or row >= len(self.parameters) - 1:
            return

        self.parameters[row], self.parameters[row + 1] = \
            self.parameters[row + 1], self.parameters[row]
        self._refresh_parameters_table()
        self.params_table.selectRow(row + 1)

    def _on_save(self):
        """Validate and save script."""
        name = self.name_edit.text().strip()
        if not name:
            DialogHelper.warning("Le nom est requis", parent=self)
            return

        file_path = self.file_path_edit.text().strip()
        if file_path and not os.path.isfile(file_path):
            DialogHelper.warning(f"Le fichier n'existe pas: {file_path}", parent=self)
            return

        script_type = self.type_combo.currentData()
        description = self.description_edit.toPlainText().strip()

        # Create parameters schema JSON
        parameters_schema = create_parameters_schema(self.parameters)

        try:
            config_db = get_config_db()

            if self.is_editing:
                # Update existing
                self.script.name = name
                self.script.script_type = script_type
                self.script.description = description
                self.script.file_path = file_path
                self.script.parameters_schema = parameters_schema
                config_db.update_script(self.script)
            else:
                # Create new
                self.script = Script(
                    id="",  # Will be generated
                    name=name,
                    script_type=script_type,
                    description=description,
                    file_path=file_path,
                    parameters_schema=parameters_schema
                )
                config_db.add_script(self.script)

            self.accept()

        except Exception as e:
            logger.error(f"Error saving script: {e}")
            DialogHelper.error(f"Erreur lors de la sauvegarde: {e}", parent=self)

    def get_script(self) -> Optional[Script]:
        """Get the created/edited script."""
        return self.script
