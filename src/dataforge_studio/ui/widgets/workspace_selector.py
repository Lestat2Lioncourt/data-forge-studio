"""
Workspace Selector - Global workspace filter dropdown

Provides a dropdown widget for selecting the active workspace filter.
When a workspace is selected, all resource managers filter their views
to show only items belonging to that workspace.
"""

from typing import Optional, List
from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt

from ..core.i18n_bridge import tr
from ...database.config_db import get_config_db, Project
from ...utils.image_loader import get_icon


class WorkspaceSelector(QWidget):
    """
    Global workspace filter selector.

    Emits workspace_changed signal when selection changes.
    Use get_current_workspace_id() to get the selected workspace ID (None = all).

    Example:
        selector = WorkspaceSelector()
        selector.workspace_changed.connect(self._on_workspace_filter_changed)

        # In the handler:
        def _on_workspace_filter_changed(self, workspace_id: Optional[str]):
            if workspace_id:
                # Filter by workspace
                items = config_db.get_workspace_queries(workspace_id)
            else:
                # Show all items
                items = config_db.get_all_queries()
    """

    # Signal emitted when workspace selection changes (workspace_id or None for all)
    workspace_changed = Signal(object)  # Optional[str]

    def __init__(self, parent: Optional[QWidget] = None, show_label: bool = True):
        """
        Initialize workspace selector.

        Args:
            parent: Parent widget
            show_label: If True, show "Workspace:" label before dropdown
        """
        super().__init__(parent)

        self._config_db = get_config_db()
        self._current_workspace_id: Optional[str] = None
        self._show_label = show_label

        self._setup_ui()
        self._load_workspaces()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        # Label (optional)
        if self._show_label:
            label = QLabel("Workspace:")
            label.setStyleSheet("font-size: 9pt;")
            layout.addWidget(label)

        # Workspace dropdown
        self.workspace_combo = QComboBox()
        self.workspace_combo.setMinimumWidth(150)
        self.workspace_combo.setMaximumWidth(250)
        self.workspace_combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self.workspace_combo)

        # Refresh button
        refresh_btn = QPushButton()
        refresh_btn.setFixedSize(24, 24)
        refresh_btn.setToolTip("Refresh workspaces")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_icon = get_icon("refresh", size=16)
        if refresh_icon:
            refresh_btn.setIcon(refresh_icon)
        else:
            refresh_btn.setText("↻")
        refresh_btn.clicked.connect(self._load_workspaces)
        layout.addWidget(refresh_btn)

    def _load_workspaces(self):
        """Load workspaces into dropdown."""
        # Remember current selection
        current_id = self._current_workspace_id

        # Block signals during update
        self.workspace_combo.blockSignals(True)
        self.workspace_combo.clear()

        # Add "All Workspaces" option
        self.workspace_combo.addItem("📁 All / Tous", None)

        # Load workspaces
        workspaces = self._config_db.get_all_workspaces()

        for ws in workspaces:
            # Use icon based on default status
            icon_prefix = "⭐ " if ws.is_default else "📂 "
            self.workspace_combo.addItem(f"{icon_prefix}{ws.name}", ws.id)

        # Restore selection
        if current_id:
            index = self.workspace_combo.findData(current_id)
            if index >= 0:
                self.workspace_combo.setCurrentIndex(index)

        self.workspace_combo.blockSignals(False)

    def _on_selection_changed(self, index: int):
        """Handle dropdown selection change."""
        workspace_id = self.workspace_combo.itemData(index)
        self._current_workspace_id = workspace_id
        self.workspace_changed.emit(workspace_id)

    def get_current_workspace_id(self) -> Optional[str]:
        """
        Get the currently selected workspace ID.

        Returns:
            Workspace ID string, or None if "All" is selected
        """
        return self._current_workspace_id

    def get_current_workspace(self) -> Optional[Project]:
        """
        Get the currently selected workspace object.

        Returns:
            Workspace (Project) object, or None if "All" is selected
        """
        if self._current_workspace_id:
            return self._config_db.get_workspace(self._current_workspace_id)
        return None

    def set_workspace(self, workspace_id: Optional[str]):
        """
        Set the current workspace programmatically.

        Args:
            workspace_id: Workspace ID to select, or None for "All"
        """
        if workspace_id is None:
            self.workspace_combo.setCurrentIndex(0)
        else:
            index = self.workspace_combo.findData(workspace_id)
            if index >= 0:
                self.workspace_combo.setCurrentIndex(index)

    def refresh(self):
        """Refresh the workspace list."""
        self._load_workspaces()
