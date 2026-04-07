"""
ER Diagram Dialogs - New diagram, table picker, rename.
"""

from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QListWidget, QListWidgetItem,
    QAbstractItemView
)
from PySide6.QtCore import Qt

from ...core.i18n_bridge import tr

import logging
logger = logging.getLogger(__name__)


class NewDiagramDialog(QDialog):
    """Dialog to create a new ER diagram."""

    def __init__(self, available_tables: List[str], parent=None):
        """
        Args:
            available_tables: List of available table names to select from
        """
        super().__init__(parent)
        self.setWindowTitle("New ER Diagram")
        self.setMinimumSize(500, 500)

        self._name = ""
        self._description = ""
        self._selected_tables: List[str] = []

        layout = QVBoxLayout(self)

        # Name
        layout.addWidget(QLabel("Diagram name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g., Datamart Ventes")
        layout.addWidget(self._name_edit)

        # Description
        layout.addWidget(QLabel("Description (optional):"))
        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(60)
        layout.addWidget(self._desc_edit)

        # Table selection
        layout.addWidget(QLabel(f"Select tables ({len(available_tables)} available):"))

        # Filter
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter tables...")
        self._filter_edit.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._filter_edit)

        # Table list with checkboxes
        self._table_list = QListWidget()
        self._table_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for table in sorted(available_tables):
            item = QListWidgetItem(table)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._table_list.addItem(item)
        layout.addWidget(self._table_list, stretch=1)

        # Select all / none
        btn_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        btn_row.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none)
        btn_row.addWidget(select_none_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # OK / Cancel
        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Create")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        button_row.addWidget(ok_btn)

        layout.addLayout(button_row)

    def _on_filter_changed(self, text: str):
        """Filter the table list."""
        text_lower = text.lower()
        for i in range(self._table_list.count()):
            item = self._table_list.item(i)
            item.setHidden(text_lower not in item.text().lower())

    def _select_all(self):
        """Check all visible items."""
        for i in range(self._table_list.count()):
            item = self._table_list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        """Uncheck all items."""
        for i in range(self._table_list.count()):
            self._table_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _on_ok(self):
        """Validate and accept."""
        self._name = self._name_edit.text().strip()
        if not self._name:
            self._name_edit.setFocus()
            self._name_edit.setStyleSheet("border: 1px solid red;")
            return

        self._description = self._desc_edit.toPlainText().strip()
        self._selected_tables = []
        for i in range(self._table_list.count()):
            item = self._table_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                self._selected_tables.append(item.text())

        if not self._selected_tables:
            return

        self.accept()

    @property
    def diagram_name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def selected_tables(self) -> List[str]:
        return self._selected_tables


class TablePickerDialog(QDialog):
    """Dialog to add tables to an existing diagram."""

    def __init__(self, available_tables: List[str], already_selected: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Tables to Diagram")
        self.setMinimumSize(400, 400)

        self._selected_tables: List[str] = []

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select tables to add:"))

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter tables...")
        self._filter_edit.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._filter_edit)

        self._table_list = QListWidget()
        for table in sorted(available_tables):
            if table not in already_selected:
                item = QListWidgetItem(table)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self._table_list.addItem(item)
        layout.addWidget(self._table_list, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)
        ok_btn = QPushButton("Add")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        button_row.addWidget(ok_btn)
        layout.addLayout(button_row)

    def _on_filter_changed(self, text: str):
        text_lower = text.lower()
        for i in range(self._table_list.count()):
            item = self._table_list.item(i)
            item.setHidden(text_lower not in item.text().lower())

    def _on_ok(self):
        self._selected_tables = []
        for i in range(self._table_list.count()):
            item = self._table_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                self._selected_tables.append(item.text())
        if self._selected_tables:
            self.accept()

    @property
    def selected_tables(self) -> List[str]:
        return self._selected_tables
