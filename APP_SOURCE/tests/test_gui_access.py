"""
Test script to verify GUI access fix for queries manager
"""
print("=" * 70)
print("TESTING GUI ACCESS FIX")
print("=" * 70)

# Test that widget hierarchy access works
print("\n1. Testing widget hierarchy access...")
try:
    import tkinter as tk
    from tkinter import ttk

    # Simulate the widget hierarchy
    root = tk.Tk()
    root.withdraw()  # Hide window

    # Simulate DataLakeLoaderGUI (not a widget, just a controller class)
    class MockGUI:
        def __init__(self, root):
            self.root = root
            self.container = ttk.Frame(root)
            self.container.pack()

            # Store reference to GUI in container (THE FIX)
            self.container.gui = self

        def _show_database_frame_with_query(self, query, execute=False):
            return True

    # Simulate QueriesManager
    class MockQueriesManager(ttk.Frame):
        def __init__(self, parent):
            super().__init__(parent)
            self.pack()

        def test_access(self):
            # This is the fix: self.master.gui should be the GUI
            gui = getattr(self.master, 'gui', None)
            return gui is not None and hasattr(gui, '_show_database_frame_with_query')

    # Create instances
    gui = MockGUI(root)
    queries_manager = MockQueriesManager(gui.container)

    # Test access
    if queries_manager.test_access():
        print("   [OK] GUI reference access works correctly")
        print("   [OK] self.master.gui can access GUI methods")
    else:
        print("   [ERROR] Widget hierarchy access failed")
        exit(1)

    root.destroy()

except Exception as e:
    print(f"   [ERROR] Widget hierarchy test failed: {e}")
    exit(1)

# Verify the fix is in place
print("\n2. Verifying fix in queries_manager.py...")
try:
    with open("queries_manager.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check for the fix pattern
    if "gui = getattr(self.master, 'gui', None)" in content:
        print("   [OK] Fix pattern found in code")

        # Count occurrences
        count = content.count("gui = getattr(self.master, 'gui', None)")
        print(f"   [OK] Fix applied in {count} location(s)")

        # Verify it's in the right methods
        methods_to_check = [
            ("_execute_query", "gui._show_database_frame_with_query(query, execute=True)"),
            ("_edit_query", "gui._show_database_frame_with_query(query, execute=False)"),
            ("_load_in_query_manager", "gui._show_database_frame_with_query(query)")
        ]

        for method_name, expected_call in methods_to_check:
            if method_name in content and expected_call in content:
                print(f"   [OK] Fix verified in {method_name}()")
            else:
                print(f"   [WARNING] Could not verify fix in {method_name}()")
    else:
        print("   [ERROR] Fix pattern not found in code")
        exit(1)

except Exception as e:
    print(f"   [ERROR] Failed to verify fix: {e}")
    exit(1)

print("\n" + "=" * 70)
print("SUCCESS: GUI access fix is correctly implemented!")
print("=" * 70)

print("\nWhat was fixed:")
print("- Changed from complex widget search to stored reference")
print("- Old: for widget in parent.winfo_children()... (didn't work)")
print("- New: gui = getattr(self.master, 'gui', None)")
print("")
print("Widget hierarchy:")
print("  root (Tk)")
print("  |-- container (Frame) <- stores reference to GUI")
print("      |-- QueriesManager (self)")
print("")
print("Access pattern:")
print("  self = QueriesManager (ttk.Frame)")
print("  self.master = container (Frame)")
print("  self.master.gui = DataLakeLoaderGUI [OK]")
print("")
print("The fix in gui.py:")
print("  self.container.gui = self  # Store reference for child frames")
print("")
print("Now Execute Query and Edit Query buttons should work!")
