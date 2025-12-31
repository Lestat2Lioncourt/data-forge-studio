"""
Job Dialog - Dialog for creating/editing Jobs with dynamic parameter form.

The parameter form is dynamically generated based on the selected Script's
parameters_schema. Each parameter type gets an appropriate widget.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QDialogButtonBox, QGroupBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QDateEdit, QDateTimeEdit, QFileDialog,
    QWidget, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QDate, QDateTime

from ..core.i18n_bridge import tr
from ..widgets.dialog_helper import DialogHelper
from ...database.models import Script, Job
from ...database.config_db import get_config_db
from ...core.parameter_types import (
    ParameterType, parse_parameters_schema, parse_job_parameters,
    create_job_parameters, validate_job_parameters
)

import logging
logger = logging.getLogger(__name__)


class DynamicParameterForm(QWidget):
    """
    Widget that dynamically generates parameter input fields
    based on a Script's parameters_schema.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_db = get_config_db()
        self.parameter_widgets: Dict[str, QWidget] = {}
        self.parameter_defs: List[Dict] = []

        self.layout = QFormLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def set_parameters(self, parameters: List[Dict], values: Optional[Dict[str, Any]] = None):
        """
        Setup the form based on parameter definitions.

        Args:
            parameters: List of parameter definitions from Script.parameters_schema
            values: Optional dict of existing values (from Job.parameters)
        """
        # Clear existing widgets
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.parameter_widgets.clear()
        self.parameter_defs = parameters
        values = values or {}

        # Create widget for each parameter
        for param_def in parameters:
            name = param_def.get("name", "")
            label = param_def.get("label", name)
            param_type = param_def.get("type", "string")
            required = param_def.get("required", True)
            default = param_def.get("default")
            options = param_def.get("options", {})
            description = param_def.get("description", "")

            # Add asterisk for required fields
            if required:
                label = f"{label} *"

            # Get current value or default
            current_value = values.get(name, default)

            # Create appropriate widget based on type
            widget = self._create_widget(param_type, current_value, options, description)

            if widget:
                self.parameter_widgets[name] = widget
                self.layout.addRow(label + ":", widget)

    def _create_widget(self, param_type: str, value: Any, options: Dict, description: str) -> QWidget:
        """Create appropriate widget for parameter type."""

        if param_type == ParameterType.ROOTFOLDER.value:
            return self._create_rootfolder_widget(value)

        elif param_type == ParameterType.DATABASE.value:
            return self._create_database_widget(value, options)

        elif param_type == ParameterType.QUERY.value:
            return self._create_query_widget(value, options)

        elif param_type == ParameterType.SCRIPT.value:
            return self._create_script_widget(value)

        elif param_type == ParameterType.STRING.value:
            return self._create_string_widget(value, options)

        elif param_type == ParameterType.NUMBER.value:
            return self._create_number_widget(value, options)

        elif param_type == ParameterType.BOOLEAN.value:
            return self._create_boolean_widget(value)

        elif param_type == ParameterType.ENUM.value:
            return self._create_enum_widget(value, options)

        elif param_type == ParameterType.PATH.value:
            return self._create_path_widget(value, options)

        elif param_type == ParameterType.PATTERN.value:
            return self._create_pattern_widget(value, options)

        elif param_type == ParameterType.DATE.value:
            return self._create_date_widget(value)

        elif param_type == ParameterType.DATETIME.value:
            return self._create_datetime_widget(value)

        else:
            # Fallback to string
            return self._create_string_widget(value, options)

    def _create_rootfolder_widget(self, value: str) -> QComboBox:
        """Create combobox for rootfolder selection."""
        combo = QComboBox()
        combo.addItem("-- Selectionner --", None)

        file_roots = self.config_db.get_all_file_roots()
        for fr in file_roots:
            combo.addItem(f"{fr.name} ({fr.path})", fr.id)

        # Set current value
        if value:
            idx = combo.findData(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        return combo

    def _create_database_widget(self, value: str, options: Dict) -> QComboBox:
        """Create combobox for database connection selection."""
        combo = QComboBox()
        combo.addItem("-- Selectionner --", None)

        connections = self.config_db.get_all_database_connections()
        filter_driver = options.get("filter_driver")

        for conn in connections:
            if filter_driver and conn.db_type != filter_driver:
                continue
            combo.addItem(f"{conn.name} ({conn.db_type})", conn.id)

        # Set current value
        if value:
            idx = combo.findData(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        return combo

    def _create_query_widget(self, value: str, options: Dict) -> QComboBox:
        """Create combobox for query selection."""
        combo = QComboBox()
        combo.addItem("-- Selectionner --", None)

        queries = self.config_db.get_all_saved_queries()
        filter_db = options.get("filter_database")

        for query in queries:
            if filter_db and query.target_database_id != filter_db:
                continue
            combo.addItem(query.name, query.id)

        # Set current value
        if value:
            idx = combo.findData(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        return combo

    def _create_script_widget(self, value: str) -> QComboBox:
        """Create combobox for script selection."""
        combo = QComboBox()
        combo.addItem("-- Selectionner --", None)

        scripts = self.config_db.get_all_scripts()
        for script in scripts:
            combo.addItem(f"{script.name} ({script.script_type})", script.id)

        # Set current value
        if value:
            idx = combo.findData(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        return combo

    def _create_string_widget(self, value: str, options: Dict) -> QWidget:
        """Create string input widget."""
        if options.get("multiline"):
            widget = QTextEdit()
            widget.setMaximumHeight(100)
            if value:
                widget.setPlainText(str(value))
            if options.get("placeholder"):
                widget.setPlaceholderText(options["placeholder"])
        else:
            widget = QLineEdit()
            if value:
                widget.setText(str(value))
            if options.get("placeholder"):
                widget.setPlaceholderText(options["placeholder"])

        return widget

    def _create_number_widget(self, value: Any, options: Dict) -> QWidget:
        """Create number input widget."""
        decimals = options.get("decimals", 0)

        if decimals > 0:
            widget = QDoubleSpinBox()
            widget.setDecimals(decimals)
        else:
            widget = QSpinBox()

        # Set range
        min_val = options.get("min", -999999)
        max_val = options.get("max", 999999)
        widget.setMinimum(int(min_val) if decimals == 0 else min_val)
        widget.setMaximum(int(max_val) if decimals == 0 else max_val)

        # Set step
        if "step" in options:
            widget.setSingleStep(options["step"])

        # Set value
        if value is not None:
            try:
                widget.setValue(int(value) if decimals == 0 else float(value))
            except (ValueError, TypeError):
                pass

        return widget

    def _create_boolean_widget(self, value: bool) -> QCheckBox:
        """Create boolean checkbox widget."""
        widget = QCheckBox()
        if value:
            widget.setChecked(bool(value))
        return widget

    def _create_enum_widget(self, value: Any, options: Dict) -> QComboBox:
        """Create enum selection widget."""
        widget = QComboBox()

        choices = options.get("choices", [])
        for choice in choices:
            if isinstance(choice, dict):
                widget.addItem(choice.get("label", ""), choice.get("value", ""))
            else:
                widget.addItem(str(choice), choice)

        # Set current value
        if value is not None:
            idx = widget.findData(value)
            if idx >= 0:
                widget.setCurrentIndex(idx)

        return widget

    def _create_path_widget(self, value: str, options: Dict) -> QWidget:
        """Create path input with browse button."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit()
        if value:
            line_edit.setText(str(value))
        layout.addWidget(line_edit)

        browse_btn = QPushButton("...")
        browse_btn.setMaximumWidth(30)

        mode = options.get("mode", "file")
        file_filter = options.get("filter", "")

        def browse():
            if mode == "folder":
                path = QFileDialog.getExistingDirectory(
                    container, "Selectionner un dossier"
                )
            elif mode == "save":
                path, _ = QFileDialog.getSaveFileName(
                    container, "Enregistrer sous", "", file_filter
                )
            else:
                path, _ = QFileDialog.getOpenFileName(
                    container, "Selectionner un fichier", "", file_filter
                )

            if path:
                line_edit.setText(path)

        browse_btn.clicked.connect(browse)
        layout.addWidget(browse_btn)

        # Store reference to line_edit for value retrieval
        container.line_edit = line_edit
        return container

    def _create_pattern_widget(self, value: str, options: Dict) -> QWidget:
        """Create pattern input widget with help."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        line_edit = QLineEdit()
        if value:
            line_edit.setText(str(value))
        line_edit.setPlaceholderText("[d1]_[d2]*")
        layout.addWidget(line_edit)

        # Help text
        example = options.get("example", "")
        if example:
            help_label = QLabel(example)
            help_label.setStyleSheet("color: gray; font-size: 10px;")
            layout.addWidget(help_label)

        # Store reference
        container.line_edit = line_edit
        return container

    def _create_date_widget(self, value: str) -> QDateEdit:
        """Create date picker widget."""
        widget = QDateEdit()
        widget.setCalendarPopup(True)

        if value:
            try:
                date = QDate.fromString(value, Qt.DateFormat.ISODate)
                if date.isValid():
                    widget.setDate(date)
            except Exception:
                widget.setDate(QDate.currentDate())
        else:
            widget.setDate(QDate.currentDate())

        return widget

    def _create_datetime_widget(self, value: str) -> QDateTimeEdit:
        """Create datetime picker widget."""
        widget = QDateTimeEdit()
        widget.setCalendarPopup(True)

        if value:
            try:
                dt = QDateTime.fromString(value, Qt.DateFormat.ISODate)
                if dt.isValid():
                    widget.setDateTime(dt)
            except Exception:
                widget.setDateTime(QDateTime.currentDateTime())
        else:
            widget.setDateTime(QDateTime.currentDateTime())

        return widget

    def get_values(self) -> Dict[str, Any]:
        """Get all parameter values from widgets."""
        values = {}

        for param_def in self.parameter_defs:
            name = param_def.get("name", "")
            param_type = param_def.get("type", "string")
            widget = self.parameter_widgets.get(name)

            if not widget:
                continue

            value = self._get_widget_value(widget, param_type)
            if value is not None:
                values[name] = value

        return values

    def _get_widget_value(self, widget: QWidget, param_type: str) -> Any:
        """Extract value from widget based on type."""

        if isinstance(widget, QComboBox):
            return widget.currentData()

        elif isinstance(widget, QCheckBox):
            return widget.isChecked()

        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.value()

        elif isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()

        elif isinstance(widget, QLineEdit):
            return widget.text().strip()

        elif isinstance(widget, QDateEdit):
            return widget.date().toString(Qt.DateFormat.ISODate)

        elif isinstance(widget, QDateTimeEdit):
            return widget.dateTime().toString(Qt.DateFormat.ISODate)

        elif hasattr(widget, 'line_edit'):
            # For compound widgets (path, pattern)
            return widget.line_edit.text().strip()

        return None


class JobDialog(QDialog):
    """Dialog for creating/editing Jobs with dynamic parameter form."""

    def __init__(self, parent=None, job: Optional[Job] = None):
        super().__init__(parent)
        self.job = job
        self.is_editing = job is not None
        self.config_db = get_config_db()
        self.current_script: Optional[Script] = None

        self.setWindowTitle("Modifier le job" if self.is_editing else "Nouveau job")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._setup_ui()
        self._load_job()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # === Script Selection Group ===
        script_group = QGroupBox("Script")
        script_layout = QFormLayout(script_group)

        self.script_combo = QComboBox()
        self.script_combo.addItem("-- Selectionner un script --", None)

        scripts = self.config_db.get_all_scripts()
        for script in scripts:
            self.script_combo.addItem(f"{script.name} ({script.script_type})", script.id)

        self.script_combo.currentIndexChanged.connect(self._on_script_changed)
        script_layout.addRow("Script:", self.script_combo)

        # Script description (read-only)
        self.script_description = QLabel()
        self.script_description.setWordWrap(True)
        self.script_description.setStyleSheet("color: gray; font-style: italic;")
        script_layout.addRow("", self.script_description)

        layout.addWidget(script_group)

        # === Job Info Group ===
        info_group = QGroupBox("Informations du job")
        info_layout = QFormLayout(info_group)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nom du job")
        info_layout.addRow("Nom:", self.name_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Description du job...")
        info_layout.addRow("Description:", self.description_edit)

        self.enabled_cb = QCheckBox("Job actif")
        self.enabled_cb.setChecked(True)
        info_layout.addRow("", self.enabled_cb)

        layout.addWidget(info_group)

        # === Parameters Group (scrollable) ===
        params_group = QGroupBox("Parametres")
        params_layout = QVBoxLayout(params_group)

        # Scroll area for parameters
        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.param_form = DynamicParameterForm()
        self.params_scroll.setWidget(self.param_form)

        params_layout.addWidget(self.params_scroll)

        # Placeholder when no script selected
        self.no_params_label = QLabel("Selectionnez un script pour configurer les parametres")
        self.no_params_label.setStyleSheet("color: gray; font-style: italic;")
        self.no_params_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        params_layout.addWidget(self.no_params_label)

        # Initially hide scroll area
        self.params_scroll.hide()

        layout.addWidget(params_group, stretch=1)

        # === Dialog Buttons ===
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_job(self):
        """Load existing job into fields."""
        if not self.job:
            return

        self.name_edit.setText(self.job.name)
        self.description_edit.setPlainText(self.job.description or "")
        self.enabled_cb.setChecked(self.job.enabled)

        # Set script
        if self.job.script_id:
            idx = self.script_combo.findData(self.job.script_id)
            if idx >= 0:
                self.script_combo.setCurrentIndex(idx)
                # Parameters will be loaded by _on_script_changed

    def _on_script_changed(self):
        """Handle script selection change."""
        script_id = self.script_combo.currentData()

        if not script_id:
            self.current_script = None
            self.script_description.setText("")
            self.params_scroll.hide()
            self.no_params_label.show()
            return

        # Load script
        self.current_script = self.config_db.get_script(script_id)

        if not self.current_script:
            self.script_description.setText("")
            self.params_scroll.hide()
            self.no_params_label.show()
            return

        # Show script description
        self.script_description.setText(self.current_script.description or "")

        # Get existing parameter values if editing
        existing_values = {}
        if self.job and self.job.script_id == script_id:
            existing_values = self.job.get_parameters()

        # Setup parameter form
        parameters = self.current_script.get_parameters()

        if parameters:
            self.param_form.set_parameters(parameters, existing_values)
            self.params_scroll.show()
            self.no_params_label.hide()
        else:
            self.params_scroll.hide()
            self.no_params_label.setText("Ce script n'a pas de parametres")
            self.no_params_label.show()

        # Auto-fill job name if empty
        if not self.name_edit.text().strip():
            self.name_edit.setText(f"Job - {self.current_script.name}")

    def _on_save(self):
        """Validate and save job."""
        # Validate script selection
        if not self.current_script:
            DialogHelper.warning("Veuillez selectionner un script", parent=self)
            return

        name = self.name_edit.text().strip()
        if not name:
            DialogHelper.warning("Le nom est requis", parent=self)
            return

        # Get parameter values
        param_values = self.param_form.get_values()

        # Validate parameters against schema
        is_valid, errors = validate_job_parameters(
            param_values,
            self.current_script.get_parameters()
        )

        if not is_valid:
            error_msg = "\n".join(f"- {e}" for e in errors)
            DialogHelper.warning(f"Parametres invalides:\n{error_msg}", parent=self)
            return

        # Create parameters JSON
        parameters_json = create_job_parameters(param_values)

        try:
            if self.is_editing:
                # Update existing
                self.job.name = name
                self.job.description = self.description_edit.toPlainText().strip()
                self.job.script_id = self.current_script.id
                self.job.enabled = self.enabled_cb.isChecked()
                self.job.parameters = parameters_json
                self.config_db.update_job(self.job)
            else:
                # Create new
                self.job = Job(
                    id="",  # Will be generated
                    name=name,
                    description=self.description_edit.toPlainText().strip(),
                    job_type="script",  # "script" for atomic jobs, "workflow" for workflows
                    script_id=self.current_script.id,
                    enabled=self.enabled_cb.isChecked(),
                    parameters=parameters_json
                )
                self.config_db.add_job(self.job)

            self.accept()

        except Exception as e:
            logger.error(f"Error saving job: {e}")
            DialogHelper.error(f"Erreur lors de la sauvegarde: {e}", parent=self)

    def get_job(self) -> Optional[Job]:
        """Get the created/edited job."""
        return self.job
