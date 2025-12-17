#!/usr/bin/env python
"""
Integration Tests for DataForge Studio v0.50
Tests all major components and imports
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test all critical imports."""
    print("=" * 60)
    print("TEST 1: Import Tests")
    print("=" * 60)

    errors = []

    # Core UI components
    try:
        from dataforge_studio.ui.core.main_window import DataForgeMainWindow
        print("[OK] MainWindow imported")
    except Exception as e:
        errors.append(f"[FAIL] MainWindow import failed: {e}")
        print(errors[-1])

    try:
        from dataforge_studio.ui.core.theme_bridge import ThemeBridge
        print("[OK] ThemeBridge imported")
    except Exception as e:
        errors.append(f"[FAIL] ThemeBridge import failed: {e}")
        print(errors[-1])

    try:
        from dataforge_studio.ui.core.i18n_bridge import I18nBridge, tr
        print("[OK] I18nBridge imported")
    except Exception as e:
        errors.append(f"[FAIL] I18nBridge import failed: {e}")
        print(errors[-1])

    # Widgets
    try:
        from dataforge_studio.ui.widgets import (
            DialogHelper, ToolbarBuilder, FormBuilder,
            CustomTreeView, CustomDataGridView, LogPanel
        )
        print("[OK] All widgets imported")
    except Exception as e:
        errors.append(f"[FAIL] Widgets import failed: {e}")
        print(errors[-1])

    # Frames
    try:
        from dataforge_studio.ui.frames import DataLakeFrame, SettingsFrame, HelpFrame
        print("[OK] All frames imported")
    except Exception as e:
        errors.append(f"[FAIL] Frames import failed: {e}")
        print(errors[-1])

    # Managers
    try:
        from dataforge_studio.ui.managers import (
            BaseManagerView, QueriesManager, ScriptsManager,
            JobsManager, DatabaseManager, DataExplorer
        )
        print("[OK] All managers imported")
    except Exception as e:
        errors.append(f"[FAIL] Managers import failed: {e}")
        print(errors[-1])

    # Utils
    try:
        from dataforge_studio.utils.sql_highlighter import SQLHighlighter
        print("[OK] SQL Highlighter imported")
    except Exception as e:
        errors.append(f"[FAIL] SQL Highlighter import failed: {e}")
        print(errors[-1])

    print()
    if errors:
        print(f"FAILED: {len(errors)} import error(s)")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("PASSED: All imports successful")
        return True


def test_managers_creation():
    """Test manager instantiation."""
    print("\n" + "=" * 60)
    print("TEST 2: Manager Creation Tests")
    print("=" * 60)

    errors = []

    try:
        from dataforge_studio.ui.managers import (
            QueriesManager, ScriptsManager, JobsManager,
            DatabaseManager, DataExplorer
        )

        managers = {
            "QueriesManager": QueriesManager,
            "ScriptsManager": ScriptsManager,
            "JobsManager": JobsManager,
            "DatabaseManager": DatabaseManager,
            "DataExplorer": DataExplorer
        }

        for name, Manager in managers.items():
            try:
                manager = Manager()
                print(f"[OK] {name} created successfully")
            except Exception as e:
                errors.append(f"[FAIL] {name} creation failed: {e}")
                print(errors[-1])

    except Exception as e:
        errors.append(f"[FAIL] Manager import failed: {e}")
        print(errors[-1])

    print()
    if errors:
        print(f"FAILED: {len(errors)} creation error(s)")
        return False
    else:
        print("PASSED: All managers created successfully")
        return True


def test_i18n():
    """Test internationalization."""
    print("\n" + "=" * 60)
    print("TEST 3: Internationalization Tests")
    print("=" * 60)

    try:
        from dataforge_studio.ui.core.i18n_bridge import I18nBridge, tr

        i18n = I18nBridge.instance()

        # Test English
        i18n.set_language('en')
        assert tr('menu_file') == 'File', "English translation failed"
        print("[OK] English translations working")

        # Test French
        i18n.set_language('fr')
        assert tr('menu_file') == 'Fichier', "French translation failed"
        print("[OK] French translations working")

        # Test missing key fallback
        result = tr('nonexistent_key')
        assert result == 'nonexistent_key', "Fallback failed"
        print("[OK] Missing key fallback working")

        print("\nPASSED: Internationalization working")
        return True

    except Exception as e:
        print(f"\nFAILED: I18n test failed: {e}")
        return False


def test_themes():
    """Test theme system."""
    print("\n" + "=" * 60)
    print("TEST 4: Theme System Tests")
    print("=" * 60)

    try:
        from dataforge_studio.ui.core.theme_bridge import ThemeBridge

        theme = ThemeBridge.get_instance()

        # Test theme availability
        themes = theme.get_available_themes()
        assert len(themes) > 0, "No themes available"
        print(f"[OK] Found {len(themes)} theme(s): {', '.join(themes.keys())}")

        # Test theme colors
        colors = theme.get_theme_colors("dark_mode")
        assert colors is not None, "Theme colors not loaded"
        assert 'window_bg' in colors, "Missing window_bg color"
        print("[OK] Theme colors loaded")

        # Test QSS generation
        qss = theme.get_qss_for_widget("QTreeWidget", "dark_mode")
        assert qss, "QSS generation failed"
        print("[OK] QSS generation working")

        print("\nPASSED: Theme system working")
        return True

    except Exception as e:
        print(f"\nFAILED: Theme test failed: {e}")
        return False


def test_widgets():
    """Test widget creation."""
    print("\n" + "=" * 60)
    print("TEST 5: Widget Creation Tests")
    print("=" * 60)

    try:
        from dataforge_studio.ui.widgets import (
            ToolbarBuilder, FormBuilder, LogPanel
        )

        # Test ToolbarBuilder
        toolbar = ToolbarBuilder().add_button("Test", lambda: None).build()
        print("[OK] ToolbarBuilder working")

        # Test FormBuilder
        form = FormBuilder(title="Test").add_field("Field", "id").build()
        print("[OK] FormBuilder working")

        # Test LogPanel
        log_panel = LogPanel(with_filters=True)
        log_panel.add_message("Test", "INFO")
        print("[OK] LogPanel working")

        print("\nPASSED: All widgets created successfully")
        return True

    except Exception as e:
        print(f"\nFAILED: Widget test failed: {e}")
        return False


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("DataForge Studio v0.50 - Integration Tests")
    print("=" * 60)
    print()

    results = []

    # Run all tests
    results.append(("Imports", test_imports()))
    results.append(("Manager Creation", test_managers_creation()))
    results.append(("I18n", test_i18n()))
    results.append(("Themes", test_themes()))
    results.append(("Widgets", test_widgets()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] PASSED" if result else "[FAIL] FAILED"
        print(f"{status} - {name}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n ALL TESTS PASSED! DataForge Studio v0.50 is ready!")
        return 0
    else:
        print(f"\n {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
