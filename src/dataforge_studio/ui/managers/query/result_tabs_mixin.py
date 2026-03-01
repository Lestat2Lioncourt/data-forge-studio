"""
Result Tabs Mixin - Result tab management for QueryTab.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...widgets.custom_datagridview import CustomDataGridView
from ...core.i18n_bridge import tr

if TYPE_CHECKING:
    from ..query_tab import ResultTabState

logger = logging.getLogger(__name__)


class QueryResultTabsMixin:
    """Result tab management methods for QueryTab."""

    def _clear_result_tabs(self):
        """Clear all result tabs except Messages."""
        # Stop any running loaders
        for tab_state in self._result_tabs:
            if tab_state.background_loader and tab_state.background_loader.isRunning():
                tab_state.background_loader.stop()
                tab_state.background_loader.wait(100)

        # Remove all tabs except Messages (last tab)
        while self.results_tab_widget.count() > 1:
            widget = self.results_tab_widget.widget(0)
            self.results_tab_widget.removeTab(0)
            widget.deleteLater()

        self._result_tabs.clear()
        self._messages_text.clear()
        self.results_grid = None

    def _create_result_tab(self, statement_index: int, tab_name: str = None) -> ResultTabState:
        """Create a new results tab with its own grid."""
        from ..query_tab import ResultTabState

        if tab_name is None:
            tab_name = tr("query_results_tab", index=len(self._result_tabs) + 1)

        grid = CustomDataGridView(show_toolbar=True)

        # Connect "Edit Query" signal for Query column cells
        grid.edit_query_requested.connect(self._on_edit_query_requested)

        tab_state = ResultTabState(
            grid=grid,
            statement_index=statement_index
        )

        # Insert before Messages tab (which is always last)
        insert_index = self.results_tab_widget.count() - 1
        self.results_tab_widget.insertTab(insert_index, grid, tab_name)

        self._result_tabs.append(tab_state)
        return tab_state

    def _append_message(self, message: str, is_error: bool = False):
        """Append a message to the Messages tab."""
        if is_error:
            self._messages_text.append(f'<span style="color: #e74c3c;">{message}</span>')
        else:
            self._messages_text.append(message)

    def _generate_result_tab_name(self, sql_text: str, index: int) -> str:
        """Generate a name for a result tab, using the query tab name if available."""
        tab_widget = self._get_parent_tab_widget()
        if tab_widget:
            tab_idx = tab_widget.indexOf(self)
            if tab_idx >= 0:
                name = tab_widget.tabText(tab_idx)
                if name:
                    return name if index <= 1 else f"{name}({index})"
        return f"Query({index})"

    def _load_data_to_grid(self, grid: CustomDataGridView, data: list):
        """Load data into a specific grid with optimizations."""
        table = grid.table
        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)
        try:
            grid.set_data(data)
        finally:
            table.setUpdatesEnabled(True)
