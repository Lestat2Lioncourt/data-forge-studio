"""
Scan Progress Dialog - Shows progress during folder scanning operations
"""

from typing import Optional, Callable
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal


class ScanWorker(QThread):
    """Worker thread for scanning operations."""

    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(dict)  # result dictionary
    error = Signal(str)  # error message

    def __init__(self, scan_function: Callable, *args, **kwargs):
        """
        Initialize worker with a scan function.

        Args:
            scan_function: Function to call that accepts a progress_callback parameter
            *args, **kwargs: Additional arguments for the scan function
        """
        super().__init__()
        self.scan_function = scan_function
        self.args = args
        self.kwargs = kwargs
        self._cancelled = False

    def run(self):
        """Execute the scan function."""
        try:
            # Add progress callback to kwargs
            def progress_callback(current, total, message):
                if not self._cancelled:
                    self.progress.emit(current, total, message)

            self.kwargs['progress_callback'] = progress_callback
            result = self.scan_function(*self.args, **self.kwargs)
            if not self._cancelled:
                self.finished.emit(result if result else {})
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def cancel(self):
        """Request cancellation of the scan."""
        self._cancelled = True


class ScanProgressDialog(QDialog):
    """
    Dialog showing progress during a scanning operation.

    Usage:
        dialog = ScanProgressDialog(parent, "Scanning images...")
        dialog.set_scan_function(scanner.scan)
        result = dialog.exec_scan()
    """

    def __init__(self, parent=None, title: str = "Scanning...",
                 description: str = "Please wait..."):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._result = None
        self._error = None
        self._worker = None
        self._scan_function = None
        self._scan_args = ()
        self._scan_kwargs = {}

        self._setup_ui(description)

    def _setup_ui(self, description: str):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Description label
        self.description_label = QLabel(description)
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate initially
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        # Counter label
        self.counter_label = QLabel("")
        layout.addWidget(self.counter_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel / Annuler")
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def set_scan_function(self, function: Callable, *args, **kwargs):
        """
        Set the scan function to execute.

        Args:
            function: Function that accepts a progress_callback parameter
            *args, **kwargs: Additional arguments for the function
        """
        self._scan_function = function
        self._scan_args = args
        self._scan_kwargs = kwargs

    def exec_scan(self) -> Optional[dict]:
        """
        Execute the scan and show the dialog.

        Returns:
            Result dictionary from the scan function, or None if cancelled/error
        """
        if not self._scan_function:
            return None

        # Create and start worker
        self._worker = ScanWorker(self._scan_function, *self._scan_args, **self._scan_kwargs)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        # Show dialog (blocking)
        self.exec()

        # Wait for worker to finish
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)

        return self._result

    def _on_progress(self, current: int, total: int, message: str):
        """Handle progress updates."""
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
            self.counter_label.setText(f"{current} / {total}")
        else:
            self.progress_bar.setMaximum(0)  # Indeterminate
            self.counter_label.setText("")

        # Truncate long messages
        if len(message) > 50:
            message = "..." + message[-47:]
        self.status_label.setText(message)

        QApplication.processEvents()

    def _on_finished(self, result: dict):
        """Handle scan completion."""
        self._result = result
        self.accept()

    def _on_error(self, error_message: str):
        """Handle scan error."""
        self._error = error_message
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("color: red;")
        self.cancel_button.setText("Close / Fermer")

    def _on_cancel(self):
        """Handle cancel button click."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.status_label.setText("Cancelling...")
            self._worker.wait(1000)
        self.reject()

    def closeEvent(self, event):
        """Handle dialog close."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(1000)
        super().closeEvent(event)
