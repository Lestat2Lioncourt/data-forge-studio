"""
Data Loading Mixin - Background data loading for QueryTab.
"""
from __future__ import annotations

import logging
import time
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QTableWidgetItem, QApplication

from ..query_loader import BackgroundRowLoader
from ...core.i18n_bridge import tr
from ....core.data_loader import LARGE_DATASET_THRESHOLD

if TYPE_CHECKING:
    from ..query_tab import ResultTabState

logger = logging.getLogger(__name__)


class QueryDataLoadingMixin:
    """Background data loading methods for QueryTab."""

    # =========================================================================
    # Per-Tab Background Loading
    # =========================================================================

    def _start_background_loading_for_tab(self, tab_state: ResultTabState):
        """Start background loading for a specific results tab."""
        tab_state.is_loading = True

        # Create loader for this tab
        loader = BackgroundRowLoader(tab_state.cursor, self.batch_size)
        tab_state.background_loader = loader

        # Connect signals with tab_state context using closures
        loader.batch_loaded.connect(
            lambda data, ts=tab_state: self._on_tab_batch_loaded(ts, data)
        )
        loader.loading_complete.connect(
            lambda status, ts=tab_state: self._on_tab_loading_complete(ts)
        )
        loader.loading_error.connect(
            lambda error, ts=tab_state: self._on_tab_loading_error(ts, error)
        )

        loader.start()
        self._update_loading_buttons()

    def _on_tab_batch_loaded(self, tab_state: ResultTabState, data: list):
        """Handle batch loaded for a specific tab."""
        if not data:
            return

        tab_state.total_rows_fetched += len(data)

        # Append to grid
        table = tab_state.grid.table
        table.setUpdatesEnabled(False)
        try:
            current_row = table.rowCount()
            table.setRowCount(current_row + len(data))

            for row_idx, row_data in enumerate(data):
                for col_idx, cell in enumerate(row_data):
                    item = QTableWidgetItem(str(cell) if cell is not None else "")
                    table.setItem(current_row + row_idx, col_idx, item)

            tab_state.grid.data.extend(data)
        finally:
            table.setUpdatesEnabled(True)

        self._update_overall_status()

    def _on_tab_loading_complete(self, tab_state: ResultTabState):
        """Handle loading complete for a specific tab."""
        tab_state.is_loading = False
        tab_state.has_more_rows = False
        tab_state.background_loader = None

        self._append_message(
            f"  → Statement {tab_state.statement_index + 1}: {tab_state.total_rows_fetched:,} row(s) loaded"
        )

        self._update_overall_status()
        self._update_loading_buttons()

    def _on_tab_loading_error(self, tab_state: ResultTabState, error_msg: str):
        """Handle loading error for a specific tab."""
        tab_state.is_loading = False
        tab_state.background_loader = None

        self._append_message(
            f"Error loading results for statement {tab_state.statement_index + 1}: {error_msg}",
            is_error=True
        )

        self._update_overall_status()
        self._update_loading_buttons()

    def _stop_all_background_loading(self):
        """Stop all background loading across all tabs."""
        for tab_state in self._result_tabs:
            if tab_state.background_loader and tab_state.background_loader.isRunning():
                tab_state.background_loader.stop()
                tab_state.background_loader.wait(500)
                tab_state.is_loading = False

        # Also stop legacy loader if exists
        if self._background_loader and self._background_loader.isRunning():
            self._background_loader.stop()
            self._background_loader.wait(500)

        self._update_loading_buttons()

        duration = self._get_duration_str()
        total_rows = sum(ts.total_rows_fetched for ts in self._result_tabs)
        self.result_info_label.setText(f"⏸ {total_rows:,} row(s) loaded in {duration} - Stopped")
        self.result_info_label.setStyleSheet("color: orange;")

    def _update_loading_buttons(self):
        """Update visibility of loading control buttons."""
        loading_count = sum(1 for ts in self._result_tabs if ts.is_loading)
        self.stop_loading_btn.setVisible(loading_count > 0)
        # Load more button not used in multi-tab mode for now
        self.load_more_btn.setVisible(False)

    def _update_overall_status(self):
        """Update the overall status label based on all tabs."""
        loading_count = sum(1 for ts in self._result_tabs if ts.is_loading)

        if loading_count > 0:
            total_rows = sum(ts.total_rows_fetched for ts in self._result_tabs)
            duration = self._get_duration_str()
            self.result_info_label.setText(
                f"⏳ Loading... {total_rows:,} row(s) in {duration} ({loading_count} result set(s) in progress)"
            )
            self.result_info_label.setStyleSheet("color: #3498db;")
        else:
            duration = self._get_duration_str()
            total_rows = sum(ts.total_rows_fetched for ts in self._result_tabs)
            stmt_count = len(self._result_tabs)
            self.result_info_label.setText(
                tr("query_completed_summary",
                   statements=stmt_count,
                   results=stmt_count,
                   duration=duration) + f" ({total_rows:,} rows)"
            )
            self.result_info_label.setStyleSheet("color: green;")

    def _get_query_row_count(self, query: str) -> Optional[int]:
        """
        Try to get the total row count for a SELECT query.
        Returns None if count cannot be determined.
        """
        # Clean query - remove trailing semicolons and whitespace
        clean_query = query.strip().rstrip(';').strip()
        query_upper = clean_query.upper()

        # Only try for SELECT queries
        if not query_upper.startswith("SELECT"):
            logger.debug("Count skipped: not a SELECT query")
            return None

        # Skip if query has TOP/LIMIT (count would be misleading)
        if "TOP " in query_upper or " LIMIT " in query_upper:
            logger.debug("Count skipped: query has TOP/LIMIT")
            return None

        # Skip if query has ORDER BY (SQL Server requires TOP with ORDER BY in subquery)
        # We'll remove ORDER BY for the count query
        if " ORDER BY " in query_upper:
            # Find ORDER BY position and remove it for count
            order_pos = query_upper.rfind(" ORDER BY ")
            clean_query = clean_query[:order_pos].strip()
            logger.debug("Removed ORDER BY clause for count query")

        try:
            # Wrap query in COUNT subquery
            count_query = f"SELECT COUNT(*) FROM ({clean_query}) AS count_subquery"
            logger.info(f"Counting rows with: {count_query[:150]}...")

            cursor = self.connection.cursor()
            cursor.execute(count_query)
            result = cursor.fetchone()
            cursor.close()

            if result:
                count = result[0]
                logger.info(f"Query row count: {count:,}")
                return count

        except Exception as e:
            # Count failed - not critical, we'll load without known total
            logger.warning(f"Could not get row count: {e}")

        return None

    def _handle_large_dataset_warning(self, row_count: int) -> bool:
        """
        Handle warning for large query results (> 100k rows).

        Args:
            row_count: Number of rows detected

        Returns:
            True to proceed with loading, False to cancel
        """
        from PySide6.QtWidgets import QMessageBox

        # Format numbers with thousands separator
        row_count_fmt = f"{row_count:,}"
        threshold_fmt = f"{LARGE_DATASET_THRESHOLD:,}"

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Large Query Result Warning")
        msg.setText(f"This query will return {row_count_fmt} rows.")
        msg.setInformativeText(
            f"Loading more than {threshold_fmt} rows may:\n"
            f"• Be slow to load\n"
            f"• Consume significant memory\n"
            f"• Slow down the interface\n\n"
            f"Consider adding TOP/LIMIT to your query.\n\n"
            f"Do you want to continue?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)

        result = msg.exec()
        return result == QMessageBox.StandardButton.Yes

    # =========================================================================
    # Legacy single-loader methods
    # =========================================================================

    def _start_background_loading(self, cursor):
        """Start background thread to load remaining rows"""
        self._is_loading = True
        self.stop_loading_btn.setVisible(True)
        self.load_more_btn.setVisible(False)

        # Update status
        self._update_loading_status()

        # Create and start background loader
        self._background_loader = BackgroundRowLoader(cursor, self.batch_size)
        self._background_loader.batch_loaded.connect(self._on_batch_loaded)
        self._background_loader.loading_complete.connect(self._on_loading_complete)
        self._background_loader.loading_error.connect(self._on_loading_error)
        self._background_loader.start()

    def _on_batch_loaded(self, data: list):
        """Handle batch of rows loaded from background thread"""
        if not data:
            return

        self.total_rows_fetched += len(data)
        self._append_data_optimized(data)
        self._update_loading_status()

    def _on_loading_complete(self, status: int):
        """Handle background loading completed"""
        self._is_loading = False
        self.has_more_rows = False
        self.stop_loading_btn.setVisible(False)
        self.load_more_btn.setVisible(False)

        duration = self._get_duration_str()

        if self.total_rows_expected:
            self.result_info_label.setText(
                f"✓ {self.total_rows_fetched:,}/{self.total_rows_expected:,} row(s) (100%) in {duration}"
            )
        else:
            self.result_info_label.setText(
                f"✓ {self.total_rows_fetched:,} row(s) loaded in {duration}"
            )
        self.result_info_label.setStyleSheet("color: green;")

        logger.info(f"Background loading complete: {self.total_rows_fetched} total rows in {duration}")

        # Cleanup
        self._background_loader = None

    def _on_loading_error(self, error_msg: str):
        """Handle background loading error"""
        self._is_loading = False
        self.stop_loading_btn.setVisible(False)
        self.load_more_btn.setVisible(self.has_more_rows)

        duration = self._get_duration_str()
        self.result_info_label.setText(
            f"⚠ {self.total_rows_fetched} row(s) loaded in {duration} - Error: {error_msg}"
        )
        self.result_info_label.setStyleSheet("color: orange;")

        logger.error(f"Background loading error: {error_msg}")

    def _stop_background_loading(self):
        """Stop background loading"""
        if self._background_loader and self._background_loader.isRunning():
            self._background_loader.stop()
            self._background_loader.wait(1000)  # Wait up to 1 second
            self._background_loader = None

        self._is_loading = False
        self.stop_loading_btn.setVisible(False)

        if self.has_more_rows:
            self.load_more_btn.setVisible(True)
            duration = self._get_duration_str()
            self.result_info_label.setText(
                f"⏸ {self.total_rows_fetched} row(s) loaded in {duration} - Stopped"
            )
            self.result_info_label.setStyleSheet("color: orange;")

    def _update_loading_status(self):
        """Update the loading status label with progress and duration"""
        duration = self._get_duration_str()

        if self.total_rows_expected:
            # Show progress with known total
            percent = (self.total_rows_fetched / self.total_rows_expected) * 100
            self.result_info_label.setText(
                f"⏳ {self.total_rows_fetched:,}/{self.total_rows_expected:,} row(s) "
                f"({percent:.0f}%) in {duration}"
            )
        else:
            # Show progress without known total
            self.result_info_label.setText(
                f"⏳ {self.total_rows_fetched:,} row(s) loaded in {duration}..."
            )

        self.result_info_label.setStyleSheet("color: #3498db;")  # Blue for loading

    def _get_duration_str(self) -> str:
        """Get formatted duration string"""
        if not self._loading_start_time:
            return "0.0s"

        elapsed = time.time() - self._loading_start_time

        if elapsed < 60:
            return f"{elapsed:.1f}s"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = elapsed % 60
            return f"{minutes}m {seconds:.0f}s"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}h {minutes}m"

    def _load_data_optimized(self, data: list):
        """Load data into grid with optimizations for large datasets"""
        table = self.results_grid.table

        # Disable updates during loading for better performance
        table.setUpdatesEnabled(False)
        table.setSortingEnabled(False)

        try:
            self.results_grid.set_data(data)
        finally:
            # Re-enable updates
            table.setUpdatesEnabled(True)

    def _load_more_rows(self):
        """Load more rows from the cursor"""
        if not self._cursor or not self.has_more_rows:
            return

        try:
            self.result_info_label.setText(tr("query_loading_more"))
            self.result_info_label.setStyleSheet("color: orange;")
            QApplication.processEvents()

            # Fetch next batch
            rows = self._cursor.fetchmany(self.batch_size)

            if not rows:
                self.has_more_rows = False
                self.load_more_btn.setVisible(False)
                self.result_info_label.setText(
                    f"✓ {self.total_rows_fetched} row(s) - All rows loaded"
                )
                self.result_info_label.setStyleSheet("color: green;")
                return

            self.total_rows_fetched += len(rows)

            # Check if there are more rows
            if len(rows) < self.batch_size:
                self.has_more_rows = False
                self.load_more_btn.setVisible(False)

            # Convert and append to grid
            data = [[cell for cell in row] for row in rows]
            self._append_data_optimized(data)

            # Update status
            if self.has_more_rows:
                self.result_info_label.setText(
                    f"✓ {self.total_rows_fetched} row(s) loaded (more available)"
                )
            else:
                self.result_info_label.setText(
                    f"✓ {self.total_rows_fetched} row(s) - All rows loaded"
                )
            self.result_info_label.setStyleSheet("color: green;")

            logger.info(f"Loaded {len(rows)} more rows, total: {self.total_rows_fetched}")

        except Exception as e:
            self.result_info_label.setText(f"✗ Error loading more rows: {str(e)}")
            self.result_info_label.setStyleSheet("color: red;")
            self.load_more_btn.setVisible(False)
            logger.error(f"Error loading more rows: {e}")

    def _append_data_optimized(self, data: list):
        """Append data to existing grid with optimizations"""
        table = self.results_grid.table

        # Disable updates during loading
        table.setUpdatesEnabled(False)

        try:
            current_row_count = table.rowCount()
            table.setRowCount(current_row_count + len(data))

            for row_idx, row_data in enumerate(data):
                actual_row = current_row_count + row_idx
                for col_idx, cell_value in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_value) if cell_value is not None else "")
                    table.setItem(actual_row, col_idx, item)

            # Also update the stored data in results_grid
            self.results_grid.data.extend(data)

        finally:
            table.setUpdatesEnabled(True)
