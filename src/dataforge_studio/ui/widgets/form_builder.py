"""
Form Builder - Builder for detail forms with label-value pairs
Eliminates repetitive form creation code
"""

from typing import Dict, Optional
from PySide6.QtWidgets import QWidget, QFormLayout, QLabel, QGroupBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt


class FormBuilder:
    """
    Builder for detail forms with label-value pairs.

    Provides a fluent API for creating forms with bold labels and
    selectable value labels. Commonly used for displaying item details
    in managers (queries, scripts, jobs, etc.).

    Example:
        form = FormBuilder(parent, title="Query Details") \\
            .add_field("Name:", "name") \\
            .add_field("Description:", "description") \\
            .add_field("Created:", "created") \\
            .build()

        # Later, update values:
        form.set_value("name", "My Query")
        form.set_value("description", "Fetches user data")
    """

    def __init__(self, parent: Optional[QWidget] = None, title: Optional[str] = None):
        """
        Initialize form builder.

        Args:
            parent: Parent widget (optional)
            title: Optional title for the form (creates QGroupBox)
        """
        if title:
            self.container = QGroupBox(title, parent)
        else:
            self.container = QWidget(parent)

        self.layout = QFormLayout(self.container)
        self.value_labels: Dict[str, QLabel] = {}

    def add_field(self, label: str, field_id: str, default_value: str = "",
                 bold_label: bool = True) -> 'FormBuilder':
        """
        Add a field with label and value.

        Args:
            label: Label text (usually ends with ":")
            field_id: Internal identifier for this field
            default_value: Default value to display
            bold_label: Whether to make label bold (default: True)

        Returns:
            self for chaining
        """
        # Create label widget
        label_widget = QLabel(label)
        if bold_label:
            label_font = QFont()
            label_font.setBold(True)
            label_widget.setFont(label_font)

        # Create value widget
        value_widget = QLabel(default_value)
        value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value_widget.setWordWrap(True)

        # Add to layout
        self.layout.addRow(label_widget, value_widget)

        # Store reference
        self.value_labels[field_id] = value_widget

        return self

    def add_separator(self) -> 'FormBuilder':
        """
        Add a horizontal separator line.

        Returns:
            self for chaining
        """
        from PySide6.QtWidgets import QFrame

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addRow(separator)

        return self

    def add_custom_row(self, label: str, widget: QWidget) -> 'FormBuilder':
        """
        Add a custom row with a label and any widget.

        Args:
            label: Label text
            widget: Custom widget to add

        Returns:
            self for chaining
        """
        label_widget = QLabel(label)
        label_font = QFont()
        label_font.setBold(True)
        label_widget.setFont(label_font)

        self.layout.addRow(label_widget, widget)

        return self

    def set_value(self, field_id: str, value: str):
        """
        Update a field value.

        Args:
            field_id: Field identifier (from add_field)
            value: New value to display
        """
        if field_id in self.value_labels:
            self.value_labels[field_id].setText(value)

    def get_value(self, field_id: str) -> str:
        """
        Get a field value.

        Args:
            field_id: Field identifier

        Returns:
            Current value or empty string if not found
        """
        if field_id in self.value_labels:
            return self.value_labels[field_id].text()
        return ""

    def clear(self):
        """Clear all field values (set to empty string)."""
        for label in self.value_labels.values():
            label.setText("")

    def clear_field(self, field_id: str):
        """
        Clear a specific field value.

        Args:
            field_id: Field identifier
        """
        if field_id in self.value_labels:
            self.value_labels[field_id].setText("")

    def set_field_style(self, field_id: str, stylesheet: str):
        """
        Apply custom stylesheet to a specific field.

        Args:
            field_id: Field identifier
            stylesheet: QSS stylesheet string
        """
        if field_id in self.value_labels:
            self.value_labels[field_id].setStyleSheet(stylesheet)

    def get_widget(self, field_id: str) -> Optional[QLabel]:
        """
        Get the QLabel widget for a field.

        Args:
            field_id: Field identifier

        Returns:
            QLabel widget or None if not found
        """
        return self.value_labels.get(field_id)

    def build(self) -> QWidget:
        """
        Return the built form widget.

        Returns:
            QWidget (or QGroupBox) containing the form
        """
        return self.container
