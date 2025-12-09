"""
Logging Module - Centralized logging with colors and file output
"""
from pathlib import Path
from datetime import datetime
from enum import Enum
from colorama import init, Fore, Style
from .config import Config

# Initialize colorama for Windows compatibility
init(autoreset=True)


class LogLevel(Enum):
    """Log level enumeration"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    IMPORTANT = "IMPORTANT"
    INFO = "INFO"


class Logger:
    """Centralized logger with colored console output and file logging"""

    _instance = None
    _log_file = None
    _gui_callback = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._gui_callback = None
        self._setup_log_file()

    def set_gui_callback(self, callback):
        """Set callback function for GUI logging"""
        self._gui_callback = callback

    def _setup_log_file(self):
        """Setup log file in the project logs folder"""
        from pathlib import Path

        # Store logs in project root logs folder
        # Go up from src/utils/ to project root
        project_root = Path(__file__).parent.parent.parent
        log_folder = project_root / "logs"
        log_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file = log_folder / f"dataforge_{timestamp}.log"

        self.info(f"Log file created: {self._log_file}")

    def _get_color(self, level: LogLevel) -> str:
        """Get color code for log level"""
        color_map = {
            LogLevel.ERROR: Fore.RED,
            LogLevel.WARNING: Fore.YELLOW,
            LogLevel.IMPORTANT: Fore.BLUE,
            LogLevel.INFO: Fore.RESET
        }
        return color_map.get(level, Fore.RESET)

    def _log(self, level: LogLevel, message: str):
        """Core logging method"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level.value:10}] {message}"

        color = self._get_color(level)
        colored_entry = f"{color}{log_entry}{Style.RESET_ALL}"

        print(colored_entry)

        if self._gui_callback:
            try:
                self._gui_callback(level, timestamp, message)
            except Exception as e:
                print(f"{Fore.RED}Failed to send to GUI: {e}{Style.RESET_ALL}")

        if self._log_file:
            try:
                with open(self._log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry + '\n')
            except Exception as e:
                print(f"{Fore.RED}Failed to write to log file: {e}{Style.RESET_ALL}")

    def error(self, message: str):
        """Log error message"""
        self._log(LogLevel.ERROR, message)

    def warning(self, message: str):
        """Log warning message"""
        self._log(LogLevel.WARNING, message)

    def important(self, message: str):
        """Log important message"""
        self._log(LogLevel.IMPORTANT, message)

    def info(self, message: str):
        """Log info message"""
        self._log(LogLevel.INFO, message)


# Global logger instance
logger = Logger()

# Export LogLevel for external use
__all__ = ['logger', 'Logger', 'LogLevel']
