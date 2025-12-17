"""
Dialog Helper - Centralized dialog management for DataForge Studio
Replaces tkinter messagebox calls with PySide6 QMessageBox
"""

from typing import Optional
from PySide6.QtWidgets import QMessageBox, QWidget


class DialogHelper:
    """
    Centralized dialog management with static methods.

    Provides consistent dialog styling and behavior across the application.
    Replaces the 178+ tkinter messagebox calls from the original codebase.
    """

    @staticmethod
    def info(message: str, title: str = "Information", parent: Optional[QWidget] = None):
        """
        Show information dialog.

        Args:
            message: Message to display
            title: Dialog title (default: "Information")
            parent: Parent widget (optional)
        """
        QMessageBox.information(parent, title, message)

    @staticmethod
    def warning(message: str, title: str = "Attention", parent: Optional[QWidget] = None):
        """
        Show warning dialog.

        Args:
            message: Warning message to display
            title: Dialog title (default: "Attention")
            parent: Parent widget (optional)
        """
        QMessageBox.warning(parent, title, message)

    @staticmethod
    def error(message: str, title: str = "Erreur", parent: Optional[QWidget] = None,
              details: Optional[str] = None):
        """
        Show error dialog with optional details.

        Args:
            message: Error message to display
            title: Dialog title (default: "Erreur")
            parent: Parent widget (optional)
            details: Optional detailed error information
        """
        msg = message
        if details:
            msg += f"\n\n{details}"
        QMessageBox.critical(parent, title, msg)

    @staticmethod
    def confirm(message: str, title: str = "Confirmation", parent: Optional[QWidget] = None) -> bool:
        """
        Show yes/no confirmation dialog.

        Args:
            message: Question to ask
            title: Dialog title (default: "Confirmation")
            parent: Parent widget (optional)

        Returns:
            True if user clicked Yes, False otherwise
        """
        reply = QMessageBox.question(
            parent, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def question(message: str, title: str = "Question",
                buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.Cancel,
                parent: Optional[QWidget] = None) -> QMessageBox.StandardButton:
        """
        Show custom question dialog with configurable buttons.

        Args:
            message: Question to ask
            title: Dialog title
            buttons: Button combination to show
            default_button: Default selected button
            parent: Parent widget (optional)

        Returns:
            The button that was clicked
        """
        return QMessageBox.question(parent, title, message, buttons, default_button)

    @staticmethod
    def error_with_log(logger, message: str, exception: Exception,
                      title: str = "Erreur", parent: Optional[QWidget] = None):
        """
        Show error dialog and log the exception.

        Convenient method that logs the error and shows it to the user.

        Args:
            logger: Logger instance
            message: User-friendly error message
            exception: Exception object
            title: Dialog title (default: "Erreur")
            parent: Parent widget (optional)
        """
        logger.error(f"{message}: {exception}")
        DialogHelper.error(message, title, parent, details=str(exception))

    @staticmethod
    def save_confirm(filename: str = None, parent: Optional[QWidget] = None) -> bool:
        """
        Show save confirmation dialog.

        Args:
            filename: Optional filename to mention
            parent: Parent widget (optional)

        Returns:
            True if user wants to save, False otherwise
        """
        msg = "Voulez-vous sauvegarder les modifications ?"
        if filename:
            msg = f"Voulez-vous sauvegarder les modifications dans '{filename}' ?"

        return DialogHelper.confirm(msg, "Sauvegarder", parent)

    @staticmethod
    def delete_confirm(item_name: str = None, parent: Optional[QWidget] = None) -> bool:
        """
        Show delete confirmation dialog.

        Args:
            item_name: Optional name of item to delete
            parent: Parent widget (optional)

        Returns:
            True if user confirms deletion, False otherwise
        """
        msg = "Êtes-vous sûr de vouloir supprimer cet élément ?"
        if item_name:
            msg = f"Êtes-vous sûr de vouloir supprimer '{item_name}' ?\n\nCette action est irréversible."

        reply = QMessageBox.warning(
            parent, "Confirmer la suppression", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def input_dialog(prompt: str, title: str = "Saisie", default_value: str = "",
                    parent: Optional[QWidget] = None) -> Optional[str]:
        """
        Show input dialog for text entry.

        Args:
            prompt: Prompt text
            title: Dialog title
            default_value: Default input value
            parent: Parent widget (optional)

        Returns:
            User input string or None if cancelled
        """
        from PySide6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(parent, title, prompt, text=default_value)
        return text if ok else None
