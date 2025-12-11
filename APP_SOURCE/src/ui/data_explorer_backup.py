"""
Data Explorer Module - Navigate and view files in RootFolders
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from typing import Optional, List
import csv
import json
from ..database.config_db import FileRoot, config_db
from ..utils.logger import logger


class DataExplorer(ttk.Frame):
    """Data Explorer - Navigate RootFolders and view files"""

    def __init__(self, parent):
        super().__init__(parent)
        self._create_widgets()
        self._load_root_folders()

    def _create_widgets(self):
        """Create explorer widgets"""
        # Header
        header_frame = ttk.Frame(self, padding="10")
        header_frame.pack(fill=tk.X)

        ttk.Label(
            header_frame,
            text="Data Explorer",
            font=("Arial", 14, "bold")
        ).pack(side=tk.LEFT)

        # Toolbar
        toolbar = ttk.Frame(self, padding="5")
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="🔄 Refresh", command=self._refresh).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="⬆️ Up Level", command=self._go_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🏠 Root", command=self._go_to_root).pack(side=tk.LEFT, padx=2)

        # Current path label
        self.path_label = ttk.Label(toolbar, text="", foreground="blue")
        self.path_label.pack(side=tk.LEFT, padx=10)

        # Main paned window (tree on left, content on right)
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: File tree
        left_frame = ttk.Frame(main_paned, width=350)
        main_paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Folders & Files", font=("Arial", 10, "bold")).pack(pady=5)

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree_scroll_y = ttk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.file_tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.file_tree.yview)
        tree_scroll_x.config(command=self.file_tree.xview)

        self.file_tree.bind("<Double-Button-1>", self._on_tree_double_click)
        self.file_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Right: File viewer
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        # File info
        info_frame = ttk.Frame(right_frame, padding="5")
        info_frame.pack(fill=tk.X)

        self.file_info_label = ttk.Label(info_frame, text="No file selected", font=("Arial", 9))
        self.file_info_label.pack(anchor=tk.W)

        # File content viewer
        viewer_frame = ttk.LabelFrame(right_frame, text="File Content", padding="5")
        viewer_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Viewer toolbar
        viewer_toolbar = ttk.Frame(viewer_frame)
        viewer_toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(viewer_toolbar, text="Encoding:").pack(side=tk.LEFT, padx=(0, 5))

        self.encoding_var = tk.StringVar(value="utf-8")
        encoding_combo = ttk.Combobox(
            viewer_toolbar,
            textvariable=self.encoding_var,
            values=["utf-8", "latin-1", "cp1252", "iso-8859-1"],
            state='readonly',
            width=15
        )
        encoding_combo.pack(side=tk.LEFT, padx=2)
        encoding_combo.bind("<<ComboboxSelected>>", lambda e: self._reload_file())

        ttk.Button(viewer_toolbar, text="Reload", command=self._reload_file).pack(side=tk.LEFT, padx=5)

        # Scrollable text widget
        self.content_text = scrolledtext.ScrolledText(
            viewer_frame,
            wrap=tk.NONE,
            font=("Consolas", 9),
            width=80,
            height=25
        )
        self.content_text.pack(fill=tk.BOTH, expand=True)

        # Storage
        self._current_path = None
        self._current_root = None
        self._path_items = {}  # Map tree items to Path objects

    def _load_root_folders(self):
        """Load root folders from database"""
        # Clear tree
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        self._path_items = {}

        # Load root folders
        root_folders = config_db.get_all_file_roots()

        if not root_folders:
            # Show message
            item = self.file_tree.insert("", "end", text="No root folders configured", tags=("info",))
            return

        # Add root folders to tree
        for root_folder in root_folders:
            root_path = Path(root_folder.path)

            if not root_path.exists():
                item = self.file_tree.insert(
                    "",
                    "end",
                    text=f"📁 {root_folder.path} [NOT FOUND]",
                    tags=("error",)
                )
                continue

            # Add root folder
            item = self.file_tree.insert(
                "",
                "end",
                text=f"💾 {root_path.name} ({root_folder.description})",
                tags=("root",)
            )
            self._path_items[item] = root_path

            # Add dummy child to make it expandable
            self.file_tree.insert(item, "end", text="Loading...")

        # Configure tags
        self.file_tree.tag_configure("root", foreground="blue")
        self.file_tree.tag_configure("folder", foreground="darkgreen")
        self.file_tree.tag_configure("file", foreground="black")
        self.file_tree.tag_configure("error", foreground="red")
        self.file_tree.tag_configure("info", foreground="gray")

        # Bind expand event
        self.file_tree.bind("<<TreeviewOpen>>", self._on_tree_expand)

        logger.info(f"Loaded {len(root_folders)} root folders")

    def _on_tree_expand(self, event):
        """Handle tree expand event"""
        item = self.file_tree.focus()
        if not item:
            return

        # Get path
        path = self._path_items.get(item)
        if not path or not path.is_dir():
            return

        # Remove dummy child
        children = self.file_tree.get_children(item)
        for child in children:
            if self.file_tree.item(child, "text") == "Loading...":
                self.file_tree.delete(child)

        # Load directory contents
        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

            for item_path in items:
                if item_path.name.startswith('.'):
                    continue  # Skip hidden files

                if item_path.is_dir():
                    # Add folder
                    child_item = self.file_tree.insert(
                        item,
                        "end",
                        text=f"📁 {item_path.name}",
                        tags=("folder",)
                    )
                    self._path_items[child_item] = item_path

                    # Add dummy child if folder has contents
                    try:
                        if any(item_path.iterdir()):
                            self.file_tree.insert(child_item, "end", text="Loading...")
                    except PermissionError:
                        pass

                else:
                    # Add file
                    size = item_path.stat().st_size
                    size_str = self._format_size(size)
                    child_item = self.file_tree.insert(
                        item,
                        "end",
                        text=f"📄 {item_path.name} ({size_str})",
                        tags=("file",)
                    )
                    self._path_items[child_item] = item_path

        except PermissionError:
            self.file_tree.insert(item, "end", text="[Permission Denied]", tags=("error",))
        except Exception as e:
            logger.error(f"Error loading directory {path}: {e}")
            self.file_tree.insert(item, "end", text=f"[Error: {e}]", tags=("error",))

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _on_tree_double_click(self, event):
        """Handle double-click on tree item"""
        item = self.file_tree.focus()
        if not item:
            return

        path = self._path_items.get(item)
        if not path:
            return

        if path.is_file():
            self._view_file(path)

    def _on_tree_select(self, event):
        """Handle tree selection"""
        item = self.file_tree.focus()
        if not item:
            return

        path = self._path_items.get(item)
        if not path:
            return

        self._current_path = path

        # Update path label
        self.path_label.config(text=str(path))

        # Update file info
        if path.is_file():
            stat = path.stat()
            size_str = self._format_size(stat.st_size)
            self.file_info_label.config(
                text=f"File: {path.name} | Size: {size_str} | Type: {path.suffix}"
            )
        else:
            try:
                count = len(list(path.iterdir()))
                self.file_info_label.config(
                    text=f"Folder: {path.name} | Items: {count}"
                )
            except:
                self.file_info_label.config(text=f"Folder: {path.name}")

    def _view_file(self, file_path: Path):
        """View file contents"""
        self.content_text.delete(1.0, tk.END)

        try:
            # Check file size
            size = file_path.stat().st_size
            if size > 5 * 1024 * 1024:  # 5 MB
                response = messagebox.askyesno(
                    "Large File",
                    f"File is {self._format_size(size)}. This may take a while.\n\nContinue?",
                    icon='warning'
                )
                if not response:
                    return

            # Detect file type and display
            suffix = file_path.suffix.lower()

            if suffix in ['.txt', '.log', '.md', '.py', '.js', '.java', '.cpp', '.h', '.sql']:
                # Text file
                self._view_text_file(file_path)

            elif suffix in ['.csv', '.tsv']:
                # CSV file
                self._view_csv_file(file_path)

            elif suffix == '.json':
                # JSON file
                self._view_json_file(file_path)

            else:
                # Binary or unknown file
                self.content_text.insert(1.0, f"[Binary file: {file_path.name}]\n\n")
                self.content_text.insert(tk.END, "Cannot display binary file content.\n")
                self.content_text.insert(tk.END, f"File size: {self._format_size(size)}\n")
                self.content_text.insert(tk.END, f"File type: {suffix}")

            logger.info(f"Viewing file: {file_path}")

        except Exception as e:
            logger.error(f"Error viewing file {file_path}: {e}")
            messagebox.showerror("Error", f"Error viewing file:\n{e}")

    def _view_text_file(self, file_path: Path):
        """View text file"""
        encoding = self.encoding_var.get()

        # Try multiple encodings if the selected one fails
        encodings_to_try = [encoding]
        if encoding == 'utf-8':
            encodings_to_try.extend(['latin-1', 'cp1252', 'iso-8859-1'])

        last_error = None
        for enc in encodings_to_try:
            try:
                content = file_path.read_text(encoding=enc)

                # Limit display to first 10,000 lines
                lines = content.splitlines()
                if len(lines) > 10000:
                    self.content_text.insert(1.0, f"[Showing first 10,000 of {len(lines)} lines]\n\n")
                    content = "\n".join(lines[:10000])

                # Success! Update encoding if we used a fallback
                if enc != encoding:
                    self.content_text.insert(1.0, f"[Auto-detected encoding: {enc}]\n\n")
                    self.encoding_var.set(enc)
                    logger.info(f"Auto-detected encoding {enc} for {file_path}")

                self.content_text.insert(tk.END, content)
                return  # Success - exit function

            except UnicodeDecodeError as e:
                last_error = e
                continue  # Try next encoding

        # If we get here, all encodings failed
        if last_error:
            self.content_text.insert(1.0, f"[ENCODING ERROR]\n\n")
            self.content_text.insert(tk.END, f"Cannot decode file with any common encoding.\n\n")
            self.content_text.insert(tk.END, f"Tried: {', '.join(encodings_to_try)}\n\n")
            self.content_text.insert(tk.END, f"Last error: {last_error}\n\n")
            self.content_text.insert(tk.END, "Try selecting a different encoding from the dropdown above and click 'Reload'.")
            logger.error(f"Failed to decode text file {file_path} with any encoding: {encodings_to_try}")

    def _view_csv_file(self, file_path: Path):
        """View CSV file in tabular format"""
        encoding = self.encoding_var.get()

        # Try multiple encodings if the selected one fails
        encodings_to_try = [encoding]
        if encoding == 'utf-8':
            encodings_to_try.extend(['latin-1', 'cp1252', 'iso-8859-1'])

        last_error = None
        for enc in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=enc, newline='') as f:
                    # Detect delimiter
                    sample = f.read(1024)
                    f.seek(0)
                    sniffer = csv.Sniffer()
                    try:
                        delimiter = sniffer.sniff(sample).delimiter
                    except:
                        delimiter = ','

                    reader = csv.reader(f, delimiter=delimiter)

                    # Read and display
                    lines = []
                    for i, row in enumerate(reader):
                        if i > 1000:  # Limit to 1000 rows
                            lines.append(f"\n[Showing first 1000 rows only]")
                            break
                        lines.append(delimiter.join(row))

                    # Success! Update encoding if we used a fallback
                    if enc != encoding:
                        self.content_text.insert(1.0, f"[Auto-detected encoding: {enc}]\n\n")
                        self.encoding_var.set(enc)
                        logger.info(f"Auto-detected encoding {enc} for {file_path}")

                    self.content_text.insert(tk.END, "\n".join(lines))
                    return  # Success - exit function

            except UnicodeDecodeError as e:
                last_error = e
                continue  # Try next encoding

            except Exception as e:
                self.content_text.insert(1.0, f"Error reading CSV: {e}")
                return

        # If we get here, all encodings failed
        if last_error:
            self.content_text.insert(1.0, f"[ENCODING ERROR]\n\n")
            self.content_text.insert(tk.END, f"Cannot decode CSV file with any common encoding.\n\n")
            self.content_text.insert(tk.END, f"Tried: {', '.join(encodings_to_try)}\n\n")
            self.content_text.insert(tk.END, f"Last error: {last_error}\n\n")
            self.content_text.insert(tk.END, "Try selecting a different encoding from the dropdown above and click 'Reload'.")
            logger.error(f"Failed to decode CSV {file_path} with any encoding: {encodings_to_try}")

    def _view_json_file(self, file_path: Path):
        """View JSON file with formatting"""
        encoding = self.encoding_var.get()

        # Try multiple encodings if the selected one fails
        encodings_to_try = [encoding]
        if encoding == 'utf-8':
            encodings_to_try.extend(['latin-1', 'cp1252', 'iso-8859-1'])

        last_error = None
        for enc in encodings_to_try:
            try:
                content = file_path.read_text(encoding=enc)
                data = json.loads(content)

                # Pretty print
                formatted = json.dumps(data, indent=2, ensure_ascii=False)

                # Success! Update encoding if we used a fallback
                if enc != encoding:
                    self.content_text.insert(1.0, f"[Auto-detected encoding: {enc}]\n\n")
                    self.encoding_var.set(enc)
                    logger.info(f"Auto-detected encoding {enc} for {file_path}")

                self.content_text.insert(tk.END, formatted)
                return  # Success - exit function

            except UnicodeDecodeError as e:
                last_error = e
                continue  # Try next encoding

            except json.JSONDecodeError as e:
                # JSON decode error - display the content as-is
                self.content_text.insert(1.0, f"[Invalid JSON]\n\n{content}")
                return

        # If we get here, all encodings failed
        if last_error:
            self.content_text.insert(1.0, f"[ENCODING ERROR]\n\n")
            self.content_text.insert(tk.END, f"Cannot decode JSON file with any common encoding.\n\n")
            self.content_text.insert(tk.END, f"Tried: {', '.join(encodings_to_try)}\n\n")
            self.content_text.insert(tk.END, f"Last error: {last_error}\n\n")
            self.content_text.insert(tk.END, "Try selecting a different encoding from the dropdown above and click 'Reload'.")
            logger.error(f"Failed to decode JSON {file_path} with any encoding: {encodings_to_try}")

    def _reload_file(self):
        """Reload current file with new encoding"""
        if self._current_path and self._current_path.is_file():
            self._view_file(self._current_path)

    def _refresh(self):
        """Refresh file tree"""
        self._load_root_folders()
        logger.info("File tree refreshed")

    def _go_up(self):
        """Go up one level"""
        if not self._current_path:
            messagebox.showinfo("Info", "No folder selected")
            return

        parent = self._current_path.parent
        if parent and parent != self._current_path:
            # Find parent in tree and select it
            for item, path in self._path_items.items():
                if path == parent:
                    self.file_tree.selection_set(item)
                    self.file_tree.focus(item)
                    self.file_tree.see(item)
                    break

    def _go_to_root(self):
        """Go to root folder"""
        self._current_path = None
        self._current_root = None
        self.path_label.config(text="")
        self.file_info_label.config(text="No file selected")
        self.content_text.delete(1.0, tk.END)
