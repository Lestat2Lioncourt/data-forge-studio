"""
Manager Protocols - Common interfaces for all manager views.

Defines the ManagerProtocol that all managers should implement for
consistent behavior across the application.
"""

from typing import Optional, Any, Protocol, runtime_checkable


@runtime_checkable
class ManagerProtocol(Protocol):
    """
    Protocol defining the common interface for all manager views.

    All managers should implement these methods to ensure consistent
    behavior for:
    - Data refresh
    - Workspace filtering
    - Item selection

    Usage:
        def process_manager(manager: ManagerProtocol) -> None:
            manager.refresh()
            manager.set_workspace_filter("workspace-id")
            item = manager.get_current_item()
    """

    def refresh(self) -> None:
        """
        Refresh the manager view.

        Reloads all data from the database and updates the display.
        Should be called when:
        - Workspace filter changes
        - Data is modified externally
        - User requests explicit refresh
        """
        ...

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        """
        Set the workspace filter for this manager.

        When a workspace filter is set, the manager should only display
        items that belong to the specified workspace.

        Args:
            workspace_id: Workspace ID to filter by, or None to show all items
        """
        ...

    def get_workspace_filter(self) -> Optional[str]:
        """
        Get the current workspace filter.

        Returns:
            Current workspace ID filter, or None if showing all items
        """
        ...

    def get_current_item(self) -> Optional[Any]:
        """
        Get the currently selected item.

        Returns:
            The currently selected item data, or None if nothing is selected
        """
        ...


@runtime_checkable
class RefreshableProtocol(Protocol):
    """
    Minimal protocol for refreshable components.

    Use this when you only need refresh capability without
    workspace filtering.
    """

    def refresh(self) -> None:
        """Refresh the component's data and display."""
        ...


@runtime_checkable
class WorkspaceAwareProtocol(Protocol):
    """
    Protocol for components that support workspace filtering.

    Components implementing this protocol can filter their content
    based on the active workspace.
    """

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        """Set workspace filter."""
        ...

    def get_workspace_filter(self) -> Optional[str]:
        """Get current workspace filter."""
        ...


@runtime_checkable
class SelectableProtocol(Protocol):
    """
    Protocol for components that have selectable items.

    Components implementing this protocol maintain a current selection
    that can be queried.
    """

    def get_current_item(self) -> Optional[Any]:
        """Get currently selected item."""
        ...

    def clear_selection(self) -> None:
        """Clear the current selection."""
        ...


def implements_manager_protocol(obj: Any) -> bool:
    """
    Check if an object implements the ManagerProtocol.

    Args:
        obj: Object to check

    Returns:
        True if object implements all ManagerProtocol methods
    """
    return isinstance(obj, ManagerProtocol)
