"""
Test script to verify paste triggers syntax highlighting
"""
import tkinter as tk
from tkinter import scrolledtext
from sql_highlighter import SQLHighlighter
import time

print("=" * 70)
print("TESTING PASTE HIGHLIGHTING FIX")
print("=" * 70)

print("\n1. Creating test window...")
root = tk.Tk()
root.title("Paste Highlighting Test")
root.geometry("600x400")

# Create text widget
text_widget = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Consolas", 10))
text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Initialize highlighter
highlighter = SQLHighlighter(text_widget)
highlight_timer = None

def on_text_modified(event=None):
    """Handle text modification for syntax highlighting"""
    global highlight_timer

    # Cancel previous timer
    if highlight_timer:
        highlight_timer.cancel()

    # Schedule highlighting after 500ms
    import threading
    highlight_timer = threading.Timer(0.5, apply_highlighting)
    highlight_timer.start()

    print(f"   Event triggered: {event}")

def apply_highlighting():
    """Apply syntax highlighting"""
    highlighter.highlight()
    print("   [OK] Highlighting applied")

# Bind events (same as in database_manager.py)
text_widget.bind("<KeyRelease>", on_text_modified)
text_widget.bind("<<Paste>>", on_text_modified)
text_widget.bind("<Control-v>", on_text_modified)
text_widget.bind("<Control-V>", on_text_modified)
text_widget.bind("<Shift-Insert>", on_text_modified)

print("   [OK] Test window created")
print("\n2. Event bindings configured:")
print("   - <KeyRelease>")
print("   - <<Paste>>")
print("   - <Control-v>")
print("   - <Control-V>")
print("   - <Shift-Insert>")

# Insert test instructions
instructions = """-- SQL SYNTAX HIGHLIGHTING TEST

Instructions:
1. Copy this SQL query:
   SELECT id, name FROM users WHERE status='active'

2. Paste it below using Ctrl+V or right-click paste

3. The highlighting should apply automatically after 500ms

Test SQL Query (copy this):
SELECT u.id, u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.created_at > '2024-01-01' GROUP BY u.id HAVING COUNT(o.id) > 5

Expected result:
- SELECT, FROM, WHERE, etc. should be BLUE and BOLD
- 'active', '2024-01-01' should be RED
- Numbers should be GREEN
- Comments (--) should be GREEN and ITALIC

Press any key after pasting to see highlighting...
"""

text_widget.insert(1.0, instructions)

print("\n" + "=" * 70)
print("MANUAL TEST REQUIRED")
print("=" * 70)
print("\nThe test window is now open.")
print("\nPlease test:")
print("  1. Copy the SQL query from the window")
print("  2. Paste it using Ctrl+V")
print("  3. Wait 500ms - highlighting should appear automatically")
print("  4. If it works, the paste fix is successful!")
print("\nClose the window when done testing.")

root.mainloop()

print("\n[OK] Test window closed")
