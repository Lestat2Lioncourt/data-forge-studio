"""
FTPRoot Manager - FTP/SFTP/FTPS browser and file viewer.

Uses ObjectViewerWidget for unified file display.
"""

from typing import Optional, Dict
from pathlib import Path
import tempfile
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QMenu, QFileDialog, QInputDialog, QProgressDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction

from ..widgets.toolbar_builder import ToolbarBuilder
from ..widgets.dialog_helper import DialogHelper
from ..widgets.pinnable_panel import PinnablePanel
from ..widgets.object_viewer_widget import ObjectViewerWidget
from ..core.i18n_bridge import tr
from ..workers.ftp_workers import (
    FTPConnectionWorker, FTPListDirectoryWorker,
    FTPTransferWorker, FTPDeleteWorker, FTPCreateDirectoryWorker
)
from ...database.config_db import get_config_db
from ...database.models import FTPRoot
from ...utils.ftp_client import BaseFTPClient, RemoteFile, FTPClientFactory
from ...utils.credential_manager import CredentialManager
from ...utils.image_loader import get_icon

logger = logging.getLogger(__name__)


class FTPRootManager(QWidget):
    """
    FTP root browser and file viewer.

    Layout:
    - TOP: Toolbar (Add, Remove, Connect, Disconnect, Refresh, Upload, Download)
    - LEFT: FTP tree (FTP roots > folders > files, lazy loading)
    - RIGHT: ObjectViewerWidget (unified file display)
    """

    # Temporary directory for previews
    TEMP_DIR = Path(tempfile.gettempdir()) / "dataforge_ftp_preview"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.config_db = get_config_db()
        self._loaded = False
        self._workspace_filter: Optional[str] = None
        self._current_item: Optional[FTPRoot] = None

        # Active connections: {ftp_root_id: BaseFTPClient}
        self._connections: Dict[str, BaseFTPClient] = {}

        # Active workers (prevent garbage collection)
        self._workers: list = []

        # Ensure temp directory exists
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)

        self._setup_ui()

    def showEvent(self, event):
        """Override showEvent to lazy-load data on first show."""
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._load_ftp_roots)

    # ==================== ManagerProtocol Implementation ====================

    def refresh(self) -> None:
        """Refresh the view (reload FTP roots from database)."""
        self._load_ftp_roots()

    def set_workspace_filter(self, workspace_id: Optional[str]) -> None:
        """Set workspace filter and refresh the view."""
        self._workspace_filter = workspace_id
        if self._loaded:
            self.refresh()

    def get_workspace_filter(self) -> Optional[str]:
        """Get current workspace filter."""
        return self._workspace_filter

    def get_current_item(self) -> Optional[FTPRoot]:
        """Get currently selected FTP root."""
        return self._current_item

    def clear_selection(self) -> None:
        """Clear current selection."""
        self._current_item = None
        self.ftp_tree.clearSelection()

    # ==================== UI Setup ====================

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar_builder = ToolbarBuilder(self)
        toolbar_builder.add_button("Add FTP", self._add_ftp_root, icon="add.png")
        toolbar_builder.add_button("Remove", self._remove_ftp_root, icon="delete.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Connect", self._connect_selected, icon="connect.png")
        toolbar_builder.add_button("Disconnect", self._disconnect_selected, icon="disconnect.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button("Download", self._download_selected, icon="download.png")
        toolbar_builder.add_button("Upload", self._upload_file, icon="upload.png")
        toolbar_builder.add_separator()
        toolbar_builder.add_button(tr("btn_refresh"), self._refresh, icon="refresh.png")

        self.toolbar = toolbar_builder.build()
        layout.addWidget(self.toolbar)

        # Main splitter (left: tree, right: object viewer)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.setChildrenCollapsible(False)

        # Left panel: Pinnable panel with FTP tree
        self.left_panel = PinnablePanel(
            title="FTP Connections",
            icon_name="ftp.png"
        )
        self.left_panel.set_normal_width(280)

        # Tree widget inside the pinnable panel
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        self.ftp_tree = QTreeWidget()
        self.ftp_tree.setHeaderHidden(True)
        self.ftp_tree.setIndentation(20)
        self.ftp_tree.setRootIsDecorated(False)
        self.ftp_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ftp_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.ftp_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.ftp_tree.itemClicked.connect(self._on_tree_click)
        self.ftp_tree.itemExpanded.connect(self._on_item_expanded)
        tree_layout.addWidget(self.ftp_tree)

        self.left_panel.set_content(tree_container)
        self.main_splitter.addWidget(self.left_panel)

        # Right panel: ObjectViewerWidget (unified display)
        self.object_viewer = ObjectViewerWidget()
        self.main_splitter.addWidget(self.object_viewer)

        # Set splitter proportions (left 30%, right 70%)
        self.main_splitter.setSizes([350, 850])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.main_splitter)

    # ==================== Tree Loading ====================

    def _load_ftp_roots(self):
        """Load all FTP roots into tree."""
        self.ftp_tree.clear()

        if self._workspace_filter:
            ftp_roots = self.config_db.get_workspace_ftp_roots(self._workspace_filter)
        else:
            ftp_roots = self.config_db.get_all_ftp_roots()

        for ftp_root in ftp_roots:
            self._add_ftp_root_to_tree(ftp_root)

    def _add_ftp_root_to_tree(self, ftp_root: FTPRoot):
        """Add an FTP root to the tree."""
        root_item = QTreeWidgetItem(self.ftp_tree)

        # Check if connected
        is_connected = ftp_root.id in self._connections

        # Icon based on connection state
        icon_name = "ftp_connected.png" if is_connected else "ftp.png"
        root_icon = get_icon(icon_name, size=16)
        if not root_icon:
            root_icon = get_icon("database.png", size=16)  # Fallback
        if root_icon:
            root_item.setIcon(0, root_icon)

        # Display name with protocol
        display_name = ftp_root.name or f"{ftp_root.protocol.upper()}://{ftp_root.host}"
        status = " [connecte]" if is_connected else ""
        root_item.setText(0, f"{display_name}{status}")
        root_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "ftproot",
            "ftproot_obj": ftp_root,
            "id": ftp_root.id,
            "connected": is_connected
        })

        # Add dummy child for expansion if connected
        if is_connected:
            dummy = QTreeWidgetItem(root_item)
            dummy.setText(0, "Loading...")
            dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})

    def _load_remote_folder(self, parent_item: QTreeWidgetItem, ftp_root_id: str, remote_path: str):
        """Load contents of a remote folder."""
        if ftp_root_id not in self._connections:
            return

        client = self._connections[ftp_root_id]

        # Start background worker
        worker = FTPListDirectoryWorker(client, remote_path)
        worker.directory_loaded.connect(
            lambda path, files: self._on_directory_loaded(parent_item, ftp_root_id, path, files)
        )
        worker.error.connect(
            lambda msg: DialogHelper.warning(msg, parent=self)
        )
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_directory_loaded(self, parent_item: QTreeWidgetItem, ftp_root_id: str,
                              path: str, files: list):
        """Handle directory listing result."""
        # Remove dummy/loading items
        for i in range(parent_item.childCount() - 1, -1, -1):
            child = parent_item.child(i)
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("type") in ["dummy", "loading"]:
                parent_item.removeChild(child)

        # Sort: directories first, then files
        files_sorted = sorted(files, key=lambda f: (not f.is_dir, f.name.lower()))

        for remote_file in files_sorted:
            item = QTreeWidgetItem(parent_item)

            if remote_file.is_dir:
                icon = get_icon("folder.png", size=16)
                if icon:
                    item.setIcon(0, icon)
                item.setText(0, remote_file.name)
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "remote_folder",
                    "ftproot_id": ftp_root_id,
                    "path": remote_file.path,
                    "name": remote_file.name
                })

                # Add dummy for lazy loading
                dummy = QTreeWidgetItem(item)
                dummy.setText(0, "Loading...")
                dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})
            else:
                icon = self._get_file_icon(remote_file.name)
                if icon:
                    item.setIcon(0, icon)

                # Format size
                size_str = self._format_size(remote_file.size)
                item.setText(0, f"{remote_file.name} ({size_str})")
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "remote_file",
                    "ftproot_id": ftp_root_id,
                    "path": remote_file.path,
                    "name": remote_file.name,
                    "size": remote_file.size,
                    "modified": remote_file.modified
                })

    def _get_file_icon(self, filename: str) -> Optional[QIcon]:
        """Get icon based on file extension."""
        extension = Path(filename).suffix.lower()

        icon_map = {
            '.csv': 'csv.png',
            '.json': 'json.png',
            '.xlsx': 'excel.png',
            '.xls': 'excel.png',
            '.txt': 'text.png',
            '.xml': 'xml.png',
            '.sql': 'sql.png',
            '.py': 'python.png',
            '.md': 'markdown.png',
        }

        icon_name = icon_map.get(extension, 'file.png')
        return get_icon(icon_name, size=16)

    def _format_size(self, size: int) -> str:
        """Format file size for display."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    # ==================== Tree Event Handlers ====================

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Handle item expansion (lazy loading)."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        # Check for dummy child
        if item.childCount() == 1:
            first_child = item.child(0)
            child_data = first_child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("type") == "dummy":
                item.removeChild(first_child)

                if data["type"] == "ftproot":
                    ftp_root = data["ftproot_obj"]
                    self._load_remote_folder(item, ftp_root.id, ftp_root.initial_path)
                elif data["type"] == "remote_folder":
                    self._load_remote_folder(item, data["ftproot_id"], data["path"])

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        """Handle single click on tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data["type"] == "ftproot":
            self._show_ftproot_details(data["ftproot_obj"])
        elif data["type"] == "remote_folder":
            self._show_remote_folder_details(data)
        elif data["type"] == "remote_file":
            self._preview_remote_file(data)

    def _on_tree_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data["type"] == "ftproot":
            # Double-click connects/disconnects
            if data.get("connected"):
                # If connected, toggle expand instead of disconnect
                item.setExpanded(not item.isExpanded())
            else:
                self._connect_ftp_root(data["ftproot_obj"])
        elif data["type"] == "remote_folder":
            # Toggle expand/collapse
            item.setExpanded(not item.isExpanded())
        elif data["type"] == "remote_file":
            self._preview_remote_file(data)

    def _show_ftproot_details(self, ftp_root: FTPRoot):
        """Show FTP root details in the viewer."""
        self._current_item = ftp_root
        is_connected = ftp_root.id in self._connections

        info_html = f"""
        <h3>{ftp_root.name or ftp_root.host}</h3>
        <table>
            <tr><td><b>Protocole:</b></td><td>{ftp_root.protocol.upper()}</td></tr>
            <tr><td><b>Hote:</b></td><td>{ftp_root.host}</td></tr>
            <tr><td><b>Port:</b></td><td>{ftp_root.port}</td></tr>
            <tr><td><b>Chemin initial:</b></td><td>{ftp_root.initial_path}</td></tr>
            <tr><td><b>Mode passif:</b></td><td>{'Oui' if ftp_root.passive_mode else 'Non'}</td></tr>
            <tr><td><b>Etat:</b></td><td>{'Connecte' if is_connected else 'Deconnecte'}</td></tr>
        </table>
        """
        if ftp_root.description:
            info_html += f"<p><i>{ftp_root.description}</i></p>"

        self.object_viewer.show_html(info_html)

    def _show_remote_folder_details(self, data: dict):
        """Show remote folder details."""
        info_html = f"""
        <h3>{data.get('name', '-')}</h3>
        <table>
            <tr><td><b>Chemin:</b></td><td>{data.get('path', '-')}</td></tr>
            <tr><td><b>Type:</b></td><td>Dossier distant</td></tr>
        </table>
        """
        self.object_viewer.show_html(info_html)

    def _preview_remote_file(self, data: dict):
        """Preview a remote file by downloading to temp."""
        ftp_root_id = data.get("ftproot_id")
        if ftp_root_id not in self._connections:
            DialogHelper.warning("Non connecte. Double-cliquez sur le serveur pour vous connecter.", parent=self)
            return

        remote_path = data.get("path")
        filename = data.get("name")
        file_size = data.get("size", 0)

        # Check file size (limit preview to 10MB)
        if file_size > 10 * 1024 * 1024:
            DialogHelper.warning(
                f"Fichier trop volumineux pour la previsualisation ({self._format_size(file_size)}).\n"
                "Utilisez le bouton Download pour telecharger le fichier.",
                parent=self
            )
            return

        # Download to temp
        local_path = self.TEMP_DIR / filename

        client = self._connections[ftp_root_id]

        # Show progress
        progress = QProgressDialog("Telechargement...", "Annuler", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        worker = FTPTransferWorker(client, remote_path, str(local_path), is_upload=False)
        worker.progress.connect(lambda p, t, total: progress.setValue(p))
        worker.completed.connect(
            lambda success, path: self._on_preview_downloaded(success, path, progress)
        )
        worker.error.connect(
            lambda msg: self._on_preview_error(msg, progress)
        )
        worker.finished.connect(lambda: self._cleanup_worker(worker))

        progress.canceled.connect(worker.cancel)

        self._workers.append(worker)
        worker.start()

    def _on_preview_downloaded(self, success: bool, local_path: str, progress: QProgressDialog):
        """Handle preview download completion."""
        progress.close()
        if success:
            self.object_viewer.show_file(Path(local_path))

    def _on_preview_error(self, message: str, progress: QProgressDialog):
        """Handle preview download error."""
        progress.close()
        DialogHelper.warning(message, parent=self)

    # ==================== Connection Management ====================

    def _connect_selected(self):
        """Connect to selected FTP root."""
        item = self.ftp_tree.currentItem()
        if not item:
            DialogHelper.warning("Selectionnez un serveur FTP a connecter.", parent=self)
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data["type"] == "ftproot":
            if data.get("connected"):
                DialogHelper.info("Deja connecte.", parent=self)
            else:
                self._connect_ftp_root(data["ftproot_obj"])

    def _connect_ftp_root(self, ftp_root: FTPRoot):
        """Establish connection to FTP root."""
        # Check protocol availability
        if not FTPClientFactory.is_protocol_available(ftp_root.protocol):
            DialogHelper.warning(
                f"{ftp_root.protocol.upper()} n'est pas disponible.\n"
                "Installez paramiko pour le support SFTP: pip install paramiko",
                parent=self
            )
            return

        # Get credentials from keyring
        username, password = CredentialManager.get_credentials(ftp_root.id)

        if not username:
            # Ask for credentials
            from ..dialogs.ftp_connection_dialog import FTPConnectionDialog
            # For now, just show a simple input dialog
            username, ok = QInputDialog.getText(self, "Identifiants", "Utilisateur:")
            if not ok or not username:
                return

            from PySide6.QtWidgets import QLineEdit
            password, ok = QInputDialog.getText(
                self, "Identifiants", "Mot de passe:",
                QLineEdit.EchoMode.Password
            )
            if not ok:
                return

        # Start connection worker
        worker = FTPConnectionWorker(ftp_root, username, password)
        worker.connection_success.connect(self._on_connection_success)
        worker.connection_error.connect(self._on_connection_error)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_connection_success(self, ftp_root_id: str, client: BaseFTPClient):
        """Handle successful FTP connection."""
        self._connections[ftp_root_id] = client
        self._load_ftp_roots()  # Refresh tree to show connected state

        # Auto-expand the connected FTP root to show contents
        for i in range(self.ftp_tree.topLevelItemCount()):
            item = self.ftp_tree.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("id") == ftp_root_id:
                item.setExpanded(True)
                break

        DialogHelper.info("Connexion etablie!", parent=self)

    def _on_connection_error(self, ftp_root_id: str, message: str):
        """Handle FTP connection error."""
        DialogHelper.warning(f"Erreur de connexion:\n{message}", parent=self)

    def _disconnect_selected(self):
        """Disconnect from selected FTP root."""
        item = self.ftp_tree.currentItem()
        if not item:
            DialogHelper.warning("Selectionnez un serveur FTP a deconnecter.", parent=self)
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data["type"] == "ftproot":
            if data.get("connected"):
                self._disconnect_ftp_root(data["id"])
            else:
                DialogHelper.info("Pas connecte.", parent=self)

    def _disconnect_ftp_root(self, ftp_root_id: str):
        """Disconnect from FTP root."""
        if ftp_root_id in self._connections:
            try:
                self._connections[ftp_root_id].disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")
            del self._connections[ftp_root_id]
            self._load_ftp_roots()  # Refresh tree

    # ==================== File Operations ====================

    def _download_selected(self):
        """Download selected file."""
        item = self.ftp_tree.currentItem()
        if not item:
            DialogHelper.warning("Selectionnez un fichier a telecharger.", parent=self)
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data["type"] != "remote_file":
            DialogHelper.warning("Selectionnez un fichier (pas un dossier).", parent=self)
            return

        ftp_root_id = data.get("ftproot_id")
        if ftp_root_id not in self._connections:
            DialogHelper.warning("Non connecte.", parent=self)
            return

        remote_path = data.get("path")
        filename = data.get("name")

        # Ask where to save
        local_path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer sous",
            str(Path.home() / filename),
            "All Files (*)"
        )

        if not local_path:
            return

        client = self._connections[ftp_root_id]

        # Show progress
        progress = QProgressDialog("Telechargement...", "Annuler", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        worker = FTPTransferWorker(client, remote_path, local_path, is_upload=False)
        worker.progress.connect(lambda p, t, total: progress.setValue(p))
        worker.completed.connect(
            lambda success, path: self._on_download_completed(success, path, progress)
        )
        worker.error.connect(
            lambda msg: self._on_transfer_error(msg, progress)
        )
        worker.finished.connect(lambda: self._cleanup_worker(worker))

        progress.canceled.connect(worker.cancel)

        self._workers.append(worker)
        worker.start()

    def _on_download_completed(self, success: bool, local_path: str, progress: QProgressDialog):
        """Handle download completion."""
        progress.close()
        if success:
            DialogHelper.info(f"Telechargement termine:\n{local_path}", parent=self)

    def _upload_file(self):
        """Upload a file to the current remote folder."""
        item = self.ftp_tree.currentItem()
        if not item:
            DialogHelper.warning("Selectionnez un dossier ou serveur destination.", parent=self)
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        # Determine target folder and ftp_root_id
        if data["type"] == "ftproot":
            ftp_root = data["ftproot_obj"]
            ftp_root_id = ftp_root.id
            target_folder = ftp_root.initial_path
        elif data["type"] == "remote_folder":
            ftp_root_id = data.get("ftproot_id")
            target_folder = data.get("path")
        elif data["type"] == "remote_file":
            # Use parent folder
            ftp_root_id = data.get("ftproot_id")
            target_folder = str(Path(data.get("path")).parent).replace("\\", "/")
        else:
            DialogHelper.warning("Selectionnez un dossier destination.", parent=self)
            return

        if ftp_root_id not in self._connections:
            DialogHelper.warning("Non connecte.", parent=self)
            return

        # Ask for file to upload
        local_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selectionner le fichier a envoyer",
            str(Path.home()),
            "All Files (*)"
        )

        if not local_path:
            return

        filename = Path(local_path).name
        remote_path = f"{target_folder.rstrip('/')}/{filename}"

        client = self._connections[ftp_root_id]

        # Show progress
        progress = QProgressDialog("Envoi...", "Annuler", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        worker = FTPTransferWorker(client, remote_path, local_path, is_upload=True)
        worker.progress.connect(lambda p, t, total: progress.setValue(p))
        worker.completed.connect(
            lambda success, path: self._on_upload_completed(success, item, progress)
        )
        worker.error.connect(
            lambda msg: self._on_transfer_error(msg, progress)
        )
        worker.finished.connect(lambda: self._cleanup_worker(worker))

        progress.canceled.connect(worker.cancel)

        self._workers.append(worker)
        worker.start()

    def _on_upload_completed(self, success: bool, parent_item: QTreeWidgetItem, progress: QProgressDialog):
        """Handle upload completion."""
        progress.close()
        if success:
            DialogHelper.info("Envoi termine!", parent=self)
            # Refresh parent folder
            self._refresh_folder(parent_item)

    def _on_transfer_error(self, message: str, progress: QProgressDialog):
        """Handle transfer error."""
        progress.close()
        DialogHelper.warning(message, parent=self)

    def _refresh_folder(self, item: QTreeWidgetItem):
        """Refresh a folder's contents."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        # Clear children
        while item.childCount() > 0:
            item.removeChild(item.child(0))

        # Add loading dummy
        dummy = QTreeWidgetItem(item)
        dummy.setText(0, "Loading...")
        dummy.setData(0, Qt.ItemDataRole.UserRole, {"type": "dummy"})

        # Trigger reload
        if data["type"] == "ftproot":
            ftp_root = data["ftproot_obj"]
            self._load_remote_folder(item, ftp_root.id, ftp_root.initial_path)
        elif data["type"] == "remote_folder":
            self._load_remote_folder(item, data["ftproot_id"], data["path"])

    # ==================== Context Menu ====================

    def _on_tree_context_menu(self, position):
        """Show context menu for tree item."""
        item = self.ftp_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if data["type"] == "ftproot":
            if data.get("connected"):
                disconnect_action = QAction("Deconnecter", self)
                disconnect_action.triggered.connect(lambda: self._disconnect_ftp_root(data["id"]))
                menu.addAction(disconnect_action)

                refresh_action = QAction("Rafraichir", self)
                refresh_action.triggered.connect(lambda: self._refresh_folder(item))
                menu.addAction(refresh_action)
            else:
                connect_action = QAction("Connecter", self)
                connect_action.triggered.connect(lambda: self._connect_ftp_root(data["ftproot_obj"]))
                menu.addAction(connect_action)

            menu.addSeparator()

            edit_action = QAction("Modifier", self)
            edit_action.triggered.connect(lambda: self._edit_ftp_root(data["ftproot_obj"]))
            menu.addAction(edit_action)

            menu.addSeparator()

            workspace_menu = self._build_workspace_submenu(data["id"], None)
            menu.addMenu(workspace_menu)

            menu.addSeparator()

            remove_action = QAction("Supprimer", self)
            remove_action.triggered.connect(lambda: self._remove_ftp_root_by_id(data["id"]))
            menu.addAction(remove_action)

        elif data["type"] == "remote_folder":
            ftp_root_id = data.get("ftproot_id")

            upload_action = QAction("Envoyer un fichier ici", self)
            upload_action.triggered.connect(self._upload_file)
            menu.addAction(upload_action)

            new_folder_action = QAction("Nouveau dossier", self)
            new_folder_action.triggered.connect(lambda: self._create_remote_folder(item, data))
            menu.addAction(new_folder_action)

            menu.addSeparator()

            refresh_action = QAction("Rafraichir", self)
            refresh_action.triggered.connect(lambda: self._refresh_folder(item))
            menu.addAction(refresh_action)

            menu.addSeparator()

            # Workspace submenu for subfolder
            workspace_menu = self._build_workspace_submenu(ftp_root_id, data.get("path"))
            menu.addMenu(workspace_menu)

            menu.addSeparator()

            delete_action = QAction("Supprimer", self)
            delete_action.triggered.connect(lambda: self._delete_remote_item(data, is_directory=True))
            menu.addAction(delete_action)

        elif data["type"] == "remote_file":
            download_action = QAction("Telecharger", self)
            download_action.triggered.connect(self._download_selected)
            menu.addAction(download_action)

            preview_action = QAction("Previsualiser", self)
            preview_action.triggered.connect(lambda: self._preview_remote_file(data))
            menu.addAction(preview_action)

            menu.addSeparator()

            delete_action = QAction("Supprimer", self)
            delete_action.triggered.connect(lambda: self._delete_remote_item(data, is_directory=False))
            menu.addAction(delete_action)

        menu.exec(self.ftp_tree.viewport().mapToGlobal(position))

    def _create_remote_folder(self, parent_item: QTreeWidgetItem, parent_data: dict):
        """Create a new remote folder."""
        ftp_root_id = parent_data.get("ftproot_id")
        if ftp_root_id not in self._connections:
            DialogHelper.warning("Non connecte.", parent=self)
            return

        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier:")
        if not ok or not name.strip():
            return

        parent_path = parent_data.get("path", "/")
        new_path = f"{parent_path.rstrip('/')}/{name.strip()}"

        client = self._connections[ftp_root_id]

        worker = FTPCreateDirectoryWorker(client, new_path)
        worker.completed.connect(
            lambda success, path: self._on_folder_created(success, path, parent_item)
        )
        worker.error.connect(
            lambda msg: DialogHelper.warning(msg, parent=self)
        )
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_folder_created(self, success: bool, path: str, parent_item: QTreeWidgetItem):
        """Handle folder creation result."""
        if success:
            DialogHelper.info(f"Dossier cree: {path}", parent=self)
            self._refresh_folder(parent_item)

    def _delete_remote_item(self, data: dict, is_directory: bool):
        """Delete a remote file or folder."""
        path = data.get("path")
        name = data.get("name")
        ftp_root_id = data.get("ftproot_id")

        if ftp_root_id not in self._connections:
            DialogHelper.warning("Non connecte.", parent=self)
            return

        item_type = "dossier" if is_directory else "fichier"
        if not DialogHelper.confirm(f"Supprimer le {item_type} '{name}'?", parent=self):
            return

        client = self._connections[ftp_root_id]

        worker = FTPDeleteWorker(client, path, is_directory)
        worker.completed.connect(
            lambda success, p: self._on_item_deleted(success, p)
        )
        worker.error.connect(
            lambda msg: DialogHelper.warning(msg, parent=self)
        )
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_item_deleted(self, success: bool, path: str):
        """Handle delete result."""
        if success:
            DialogHelper.info("Supprime!", parent=self)
            self._load_ftp_roots()  # Refresh all

    # ==================== FTPRoot CRUD ====================

    def _add_ftp_root(self):
        """Add a new FTP root."""
        from ..dialogs.ftp_connection_dialog import FTPConnectionDialog

        dialog = FTPConnectionDialog(parent=self)
        if dialog.exec():
            self._refresh()

    def _edit_ftp_root(self, ftp_root: FTPRoot):
        """Edit an FTP root."""
        from ..dialogs.ftp_connection_dialog import FTPConnectionDialog

        dialog = FTPConnectionDialog(parent=self, ftp_root=ftp_root)
        if dialog.exec():
            self._refresh()

    def _remove_ftp_root(self):
        """Remove selected FTP root."""
        item = self.ftp_tree.currentItem()
        if not item:
            DialogHelper.warning("Selectionnez un serveur FTP a supprimer.", parent=self)
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data["type"] == "ftproot":
            self._remove_ftp_root_by_id(data["id"])
        else:
            DialogHelper.warning("Selectionnez un serveur FTP (pas un fichier ou dossier).", parent=self)

    def _remove_ftp_root_by_id(self, ftp_root_id: str):
        """Remove FTP root by ID."""
        if not DialogHelper.confirm("Supprimer cette connexion FTP?", parent=self):
            return

        # Disconnect if connected
        if ftp_root_id in self._connections:
            self._disconnect_ftp_root(ftp_root_id)

        try:
            self.config_db.delete_ftp_root(ftp_root_id)
            # Also delete stored credentials
            CredentialManager.delete_credentials(ftp_root_id)
            self._refresh()
            DialogHelper.info("Connexion FTP supprimee.", parent=self)

        except Exception as e:
            logger.error(f"Error removing FTP root: {e}")
            DialogHelper.error("Erreur lors de la suppression", details=str(e), parent=self)

    def _refresh(self):
        """Refresh the tree."""
        self._load_ftp_roots()
        self.object_viewer.clear()

    def _cleanup_worker(self, worker):
        """Remove worker from active list."""
        if worker in self._workers:
            self._workers.remove(worker)

    def get_tree_widget(self):
        """Return the tree widget for embedding in ResourcesManager."""
        return self.ftp_tree

    # ==================== Workspace Management ====================

    def _build_workspace_submenu(self, ftp_root_id: str, subfolder_path: Optional[str]) -> QMenu:
        """Build a submenu for adding/removing an FTP root to/from workspaces."""
        from ...database.config_db import Workspace

        menu = QMenu(tr("menu_workspaces"), self)

        workspaces = self.config_db.get_all_workspaces()
        current_workspaces = self.config_db.get_ftp_root_workspaces(ftp_root_id, subfolder_path)
        current_workspace_ids = {ws.id for ws in current_workspaces}

        for ws in workspaces:
            is_in_workspace = ws.id in current_workspace_ids
            action_text = f"* {ws.name}" if is_in_workspace else ws.name

            action = QAction(action_text, self)
            action.triggered.connect(
                lambda checked, wid=ws.id, fid=ftp_root_id, sp=subfolder_path, in_ws=is_in_workspace:
                    self._toggle_workspace(wid, fid, sp, in_ws)
            )
            menu.addAction(action)

        if workspaces:
            menu.addSeparator()

        new_action = QAction("+ " + tr("menu_workspaces_manage").replace("...", ""), self)
        new_action.triggered.connect(
            lambda: self._create_new_workspace_and_add(ftp_root_id, subfolder_path)
        )
        menu.addAction(new_action)

        return menu

    def _toggle_workspace(self, workspace_id: str, ftp_root_id: str, subfolder_path: Optional[str], is_in_workspace: bool):
        """Toggle an FTP root in/out of a workspace."""
        try:
            if is_in_workspace:
                self.config_db.remove_ftp_root_from_workspace(workspace_id, ftp_root_id)
            else:
                self.config_db.add_ftp_root_to_workspace(workspace_id, ftp_root_id, subfolder_path)

            logger.info(f"{'Removed from' if is_in_workspace else 'Added to'} workspace: FTP root {ftp_root_id}")

        except Exception as e:
            logger.error(f"Error toggling workspace: {e}")
            DialogHelper.error("Error updating workspace", details=str(e), parent=self)

    def _create_new_workspace_and_add(self, ftp_root_id: str, subfolder_path: Optional[str]):
        """Create a new workspace and add the FTP root to it."""
        from ...database.config_db import Workspace
        import uuid

        name, ok = QInputDialog.getText(self, "New Workspace", "Workspace name:")
        if ok and name.strip():
            ws = Workspace(
                id=str(uuid.uuid4()),
                name=name.strip(),
                description=""
            )

            if self.config_db.add_workspace(ws):
                self._toggle_workspace(ws.id, ftp_root_id, subfolder_path, False)
                logger.info(f"Created workspace '{ws.name}' and added FTP root")
            else:
                DialogHelper.warning("Failed to create workspace. Name may already exist.", parent=self)

    # ==================== Cleanup ====================

    def closeEvent(self, event):
        """Clean up connections on close."""
        for ftp_root_id, client in list(self._connections.items()):
            try:
                client.disconnect()
            except Exception:
                pass
        self._connections.clear()

        # Clean up temp files
        try:
            import shutil
            if self.TEMP_DIR.exists():
                shutil.rmtree(self.TEMP_DIR, ignore_errors=True)
        except Exception:
            pass

        super().closeEvent(event)
