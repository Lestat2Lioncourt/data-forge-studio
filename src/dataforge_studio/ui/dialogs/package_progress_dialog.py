"""
Package Progress Dialog - Shows real-time output of the offline package generation script.
Uses QProcess to run prepare_package.bat non-blocking.
"""

import ctypes
import re
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QProgressBar, QPushButton, QHBoxLayout
)
from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QFont

from ..core.i18n_bridge import tr


class PackageProgressDialog(QDialog):
    """Modal dialog that runs prepare_package.bat and displays its output in real-time."""

    # Regex patterns for line coloring
    _COLOR_MAP = {
        re.compile(r"\[OK\]"): "#4ec950",      # green
        re.compile(r"\[ERREUR\]"): "#e05555",   # red
        re.compile(r"\[WARN\]"): "#e0a030",     # orange
        re.compile(r"\[INFO\]"): "#55b8d0",     # cyan
    }
    _DEFAULT_COLOR = "#cccccc"
    _RE_7Z_PROGRESS = re.compile(r"^\s*(\d{1,3})%")

    def __init__(self, script_path: Path, parent=None):
        super().__init__(parent)
        self._script_path = script_path
        self._process = None
        self._in_7z_phase = False
        # Detect the Windows ANSI code page (e.g. cp1252 for French).
        # When stdout is redirected to a pipe (QProcess), system commands
        # like xcopy output in the ANSI codepage, not the OEM codepage.
        self._encoding = f"cp{ctypes.windll.kernel32.GetACP()}"

        self.setWindowTitle(tr("pkg_dialog_title"))
        self.setMinimumSize(650, 450)
        self.resize(650, 450)

        self._setup_ui()
        self._start_process()

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)

        # Console output
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Consolas", 9))
        self._output.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #cccccc; border: 1px solid #444; }"
        )
        layout.addWidget(self._output)

        # Progress bar (indeterminate)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        layout.addWidget(self._progress)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._btn_close = QPushButton(tr("btn_close"))
        self._btn_close.setEnabled(False)
        self._btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self._btn_close)
        layout.addLayout(btn_layout)

    def _start_process(self):
        """Launch the batch script via QProcess."""
        self._process = QProcess(self)
        self._process.setWorkingDirectory(str(self._script_path.parent))
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)

        # Use setNativeArguments to avoid QProcess double-quoting the path.
        self._process.setProgram("cmd.exe")
        self._process.setNativeArguments(f'/c "{self._script_path}"')
        self._process.start()

    def _on_stdout(self):
        """Handle standard output data."""
        data = self._process.readAllStandardOutput()
        text = data.data().decode(self._encoding, errors="replace")
        for line in text.splitlines():
            # Detect 7z compression phase
            if not self._in_7z_phase and "Compression en 7z" in line:
                self._in_7z_phase = True

            # During 7z phase: parse progress, skip noise
            if self._in_7z_phase:
                m = self._RE_7Z_PROGRESS.match(line)
                if m:
                    pct = int(m.group(1))
                    if self._progress.maximum() == 0:
                        # Switch from indeterminate to determinate
                        self._progress.setRange(0, 100)
                    self._progress.setValue(pct)
                    self._progress.setFormat(f"Compression 7z : {pct}%")
                    continue  # don't flood the log with per-file progress lines
                # End of 7z phase when a tagged line appears (e.g. [OK], [WARN])
                if re.search(r"\[(OK|WARN|ERREUR)\]", line):
                    self._in_7z_phase = False
                    self._progress.setRange(0, 0)  # back to indeterminate
                    self._progress.resetFormat()
                elif not line.strip():
                    continue  # skip empty lines from 7z \r output

            self._append_colored_line(line)

    def _on_stderr(self):
        """Handle standard error data."""
        data = self._process.readAllStandardError()
        text = data.data().decode(self._encoding, errors="replace")
        for line in text.splitlines():
            self._append_colored_line(line, fallback_color="#e05555")

    def _append_colored_line(self, line: str, fallback_color: str | None = None):
        """Append a line to the output with color based on prefix tags."""
        color = fallback_color or self._DEFAULT_COLOR
        for pattern, c in self._COLOR_MAP.items():
            if pattern.search(line):
                color = c
                break

        escaped = (
            line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        self._output.append(f'<span style="color:{color}">{escaped}</span>')

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        """Handle process completion."""
        # Stop indeterminate animation
        self._progress.setRange(0, 1)
        self._progress.setValue(1)

        # Enable close button
        self._btn_close.setEnabled(True)

        # Summary message
        if exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit:
            self._append_colored_line("")
            self._append_colored_line(f"[OK] {tr('pkg_finished_success')}")
        else:
            self._append_colored_line("")
            self._append_colored_line(
                f"[ERREUR] {tr('pkg_finished_error')} (code: {exit_code})"
            )

    def closeEvent(self, event):
        """Prevent closing while the script is running."""
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            event.ignore()
        else:
            super().closeEvent(event)
