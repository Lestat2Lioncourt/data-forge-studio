"""
Query Loader - Background thread for loading query results

Provides asynchronous loading of large result sets without blocking the UI.
"""

from PySide6.QtCore import QThread, Signal


class BackgroundRowLoader(QThread):
    """Background thread for loading rows from cursor"""

    # Signals
    batch_loaded = Signal(list)  # Emits batch of rows
    loading_complete = Signal(int)  # Emits total row count
    loading_error = Signal(str)  # Emits error message

    def __init__(self, cursor, batch_size: int = 1000):
        super().__init__()
        self.cursor = cursor
        self.batch_size = batch_size
        self._stop_requested = False

    def run(self):
        """Load rows in background"""
        try:
            while not self._stop_requested:
                rows = self.cursor.fetchmany(self.batch_size)

                if not rows:
                    break

                # Convert to list of lists
                data = [[cell for cell in row] for row in rows]
                self.batch_loaded.emit(data)

                # Small pause to allow UI updates
                self.msleep(10)

            self.loading_complete.emit(0)  # 0 = normal completion

        except Exception as e:
            self.loading_error.emit(str(e))

    def stop(self):
        """Request stop"""
        self._stop_requested = True
