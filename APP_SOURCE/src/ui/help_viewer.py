"""
Help Viewer Module - Display markdown documentation files
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from typing import List, Dict


class HelpViewer(tk.Toplevel):
    """Help documentation viewer"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Help Documentation")
        self.geometry("1000x700")
        self.transient(parent)

        # Get all markdown files
        self.docs = self._find_documentation_files()

        self._create_widgets()
        self._load_first_doc()

    def _find_documentation_files(self) -> List[Dict]:
        """Find all markdown documentation files"""
        app_folder = Path(__file__).parent
        md_files = list(app_folder.glob("*.md"))

        docs = []
        for md_file in sorted(md_files):
            # Skip README if it's just a placeholder
            if md_file.name == "README.md":
                continue

            docs.append({
                "name": md_file.stem.replace("_", " ").title(),
                "filename": md_file.name,
                "path": md_file
            })

        return docs

    def _create_widgets(self):
        """Create help viewer widgets"""
        # Header
        header_frame = ttk.Frame(self, padding="10")
        header_frame.pack(fill=tk.X)

        ttk.Label(
            header_frame,
            text="📚 Help Documentation",
            font=("Arial", 14, "bold")
        ).pack(side=tk.LEFT)

        # Main container with paned window
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Document list
        left_frame = ttk.Frame(main_paned, width=250)
        main_paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Documentation Topics", font=("Arial", 10, "bold")).pack(pady=5)

        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.doc_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
            activestyle='none'
        )
        self.doc_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.doc_listbox.yview)

        # Populate list
        for doc in self.docs:
            self.doc_listbox.insert(tk.END, doc["name"])

        self.doc_listbox.bind("<<ListboxSelect>>", self._on_doc_select)

        # Right: Document content
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)

        # Title
        self.doc_title = ttk.Label(right_frame, text="", font=("Arial", 12, "bold"))
        self.doc_title.pack(pady=5)

        # Filename
        self.doc_filename = ttk.Label(right_frame, text="", foreground="gray", font=("Arial", 9))
        self.doc_filename.pack(pady=2)

        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Content
        content_frame = ttk.Frame(right_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        content_scroll_y = ttk.Scrollbar(content_frame)
        content_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        content_scroll_x = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL)
        content_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.content_text = tk.Text(
            content_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            yscrollcommand=content_scroll_y.set,
            xscrollcommand=content_scroll_x.set,
            padx=10,
            pady=10
        )
        self.content_text.pack(fill=tk.BOTH, expand=True)
        content_scroll_y.config(command=self.content_text.yview)
        content_scroll_x.config(command=self.content_text.xview)

        # Configure text tags for formatting
        self.content_text.tag_configure("h1", font=("Arial", 16, "bold"), foreground="#1a5490", spacing1=10, spacing3=5)
        self.content_text.tag_configure("h2", font=("Arial", 14, "bold"), foreground="#2968a8", spacing1=8, spacing3=4)
        self.content_text.tag_configure("h3", font=("Arial", 12, "bold"), foreground="#3a7fc0", spacing1=6, spacing3=3)
        self.content_text.tag_configure("code", font=("Consolas", 9), background="#f5f5f5", foreground="#c7254e")
        self.content_text.tag_configure("code_block", font=("Consolas", 9), background="#f8f8f8", foreground="#333333", lmargin1=20, lmargin2=20)
        self.content_text.tag_configure("bold", font=("Arial", 10, "bold"))
        self.content_text.tag_configure("italic", font=("Arial", 10, "italic"))
        self.content_text.tag_configure("list_item", lmargin1=20, lmargin2=40)
        self.content_text.tag_configure("blockquote", lmargin1=20, lmargin2=20, foreground="#666666", background="#f9f9f9")

        # Buttons
        button_frame = ttk.Frame(self, padding="5")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(button_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _load_first_doc(self):
        """Load the first document"""
        if self.docs:
            self.doc_listbox.selection_set(0)
            self._display_document(self.docs[0])

    def _on_doc_select(self, event):
        """Handle document selection"""
        selection = self.doc_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index < len(self.docs):
            self._display_document(self.docs[index])

    def _display_document(self, doc: Dict):
        """Display markdown document with basic formatting"""
        self.doc_title.config(text=doc["name"])
        self.doc_filename.config(text=f"File: {doc['filename']}")

        # Clear content
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)

        # Read file
        try:
            with open(doc["path"], "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.content_text.insert(tk.END, f"Error loading document: {e}")
            self.content_text.config(state=tk.DISABLED)
            return

        # Parse and format markdown
        self._format_markdown(content)

        self.content_text.config(state=tk.DISABLED)
        self.content_text.see(1.0)

    def _format_markdown(self, content: str):
        """Basic markdown formatting"""
        lines = content.split("\n")
        in_code_block = False
        code_block_content = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Code block
            if line.strip().startswith("```"):
                if in_code_block:
                    # End code block
                    code_text = "\n".join(code_block_content)
                    self.content_text.insert(tk.END, code_text + "\n", "code_block")
                    code_block_content = []
                    in_code_block = False
                else:
                    # Start code block
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                code_block_content.append(line)
                i += 1
                continue

            # Headers
            if line.startswith("# "):
                self.content_text.insert(tk.END, line[2:] + "\n", "h1")
            elif line.startswith("## "):
                self.content_text.insert(tk.END, line[3:] + "\n", "h2")
            elif line.startswith("### "):
                self.content_text.insert(tk.END, line[4:] + "\n", "h3")
            elif line.startswith("#### "):
                self.content_text.insert(tk.END, line[5:] + "\n", "h3")

            # Horizontal rule
            elif line.strip().startswith("---") or line.strip().startswith("==="):
                self.content_text.insert(tk.END, "\n" + "─" * 80 + "\n\n")

            # List items
            elif line.strip().startswith("- ") or line.strip().startswith("* ") or line.strip().startswith("+ "):
                formatted_line = "• " + line.strip()[2:]
                self._format_inline(formatted_line, "list_item")
                self.content_text.insert(tk.END, "\n")

            # Numbered list
            elif len(line) > 2 and line[0].isdigit() and line[1:3] in (". ", ") "):
                self._format_inline(line, "list_item")
                self.content_text.insert(tk.END, "\n")

            # Blockquote
            elif line.strip().startswith(">"):
                quote_text = line.strip()[1:].strip()
                self.content_text.insert(tk.END, quote_text + "\n", "blockquote")

            # Normal line
            else:
                if line.strip():
                    self._format_inline(line)
                    self.content_text.insert(tk.END, "\n")
                else:
                    self.content_text.insert(tk.END, "\n")

            i += 1

    def _format_inline(self, line: str, base_tag=None):
        """Format inline markdown (bold, italic, code)"""
        # Simple inline formatting
        parts = []
        current = ""
        i = 0

        while i < len(line):
            # Inline code `code`
            if line[i] == '`':
                if current:
                    parts.append(("text", current))
                    current = ""

                # Find closing backtick
                j = i + 1
                while j < len(line) and line[j] != '`':
                    j += 1

                if j < len(line):
                    code_text = line[i+1:j]
                    parts.append(("code", code_text))
                    i = j + 1
                    continue

            # Bold **text**
            elif i + 1 < len(line) and line[i:i+2] == '**':
                if current:
                    parts.append(("text", current))
                    current = ""

                # Find closing **
                j = i + 2
                while j + 1 < len(line) and line[j:j+2] != '**':
                    j += 1

                if j + 1 < len(line):
                    bold_text = line[i+2:j]
                    parts.append(("bold", bold_text))
                    i = j + 2
                    continue

            # Italic *text*
            elif line[i] == '*':
                if current:
                    parts.append(("text", current))
                    current = ""

                # Find closing *
                j = i + 1
                while j < len(line) and line[j] != '*':
                    j += 1

                if j < len(line):
                    italic_text = line[i+1:j]
                    parts.append(("italic", italic_text))
                    i = j + 1
                    continue

            current += line[i]
            i += 1

        if current:
            parts.append(("text", current))

        # Insert formatted parts
        for part_type, text in parts:
            if part_type == "code":
                self.content_text.insert(tk.END, text, "code")
            elif part_type == "bold":
                self.content_text.insert(tk.END, text, "bold")
            elif part_type == "italic":
                self.content_text.insert(tk.END, text, "italic")
            else:
                if base_tag:
                    self.content_text.insert(tk.END, text, base_tag)
                else:
                    self.content_text.insert(tk.END, text)


def show_help(parent):
    """Show help viewer window"""
    help_window = HelpViewer(parent)
    help_window.focus()
