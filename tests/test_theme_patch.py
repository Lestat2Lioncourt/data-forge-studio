"""
Tests for Theme Patch system (Quick Theme Creator).
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestThemePatchExpansion:
    """Test _expand_patch_theme method in ThemeBridge."""

    @pytest.fixture
    def mock_themes(self):
        """Create mock base themes."""
        return {
            "minimal_dark": {
                "name": "Mode sombre",
                "type": "minimal",
                "palette": {
                    "is_dark": True,
                    "TopBar_BG": "#2b2b2b",
                    "TopBar_FG": "#ffffff",
                    "Frame_BG": "#252525",
                    "Accent": "#0078d7",
                    "Normal_FG": "#ffffff",
                    "Success_FG": "#2ecc71",
                    "Error_FG": "#e74c3c",
                }
            },
            "minimal_light": {
                "name": "Mode clair",
                "type": "minimal",
                "palette": {
                    "is_dark": False,
                    "TopBar_BG": "#f0f0f0",
                    "TopBar_FG": "#333333",
                    "Frame_BG": "#ffffff",
                    "Accent": "#0078d7",
                    "Normal_FG": "#333333",
                    "Success_FG": "#27ae60",
                    "Error_FG": "#c0392b",
                }
            }
        }

    def test_expand_patch_with_dark_base(self, mock_themes):
        """Test expanding a patch based on dark theme."""
        from dataforge_studio.ui.core.theme_bridge import ThemeBridge

        # Create a mock ThemeBridge-like object
        class MockBridge:
            themes = mock_themes

            def _expand_patch_theme(self, patch_data):
                return ThemeBridge._expand_patch_theme(self, patch_data)

        bridge = MockBridge()

        patch_data = {
            "name": "My Custom Theme",
            "type": "patch",
            "base": "minimal_dark",
            "overrides": {
                "Accent": "#ff6600",
                "Frame_BG": "#1a1a2e"
            }
        }

        result = bridge._expand_patch_theme(patch_data)

        assert result["name"] == "My Custom Theme"
        assert result["type"] == "minimal"
        assert "palette" in result

        palette = result["palette"]
        # Overridden values
        assert palette["Accent"] == "#ff6600"
        assert palette["Frame_BG"] == "#1a1a2e"
        # Base values preserved
        assert palette["TopBar_BG"] == "#2b2b2b"
        assert palette["is_dark"] == True

    def test_expand_patch_with_light_base(self, mock_themes):
        """Test expanding a patch based on light theme."""
        from dataforge_studio.ui.core.theme_bridge import ThemeBridge

        class MockBridge:
            themes = mock_themes

            def _expand_patch_theme(self, patch_data):
                return ThemeBridge._expand_patch_theme(self, patch_data)

        bridge = MockBridge()

        patch_data = {
            "name": "Custom Light",
            "type": "patch",
            "base": "minimal_light",
            "overrides": {
                "Accent": "#e91e63"
            }
        }

        result = bridge._expand_patch_theme(patch_data)

        assert result["name"] == "Custom Light"
        assert result["type"] == "minimal"

        palette = result["palette"]
        assert palette["Accent"] == "#e91e63"
        assert palette["is_dark"] == False
        assert palette["TopBar_BG"] == "#f0f0f0"

    def test_expand_patch_with_unknown_base(self, mock_themes):
        """Test expanding a patch with unknown base uses fallback."""
        from dataforge_studio.ui.core.theme_bridge import ThemeBridge

        class MockBridge:
            themes = mock_themes

            def _expand_patch_theme(self, patch_data):
                return ThemeBridge._expand_patch_theme(self, patch_data)

        bridge = MockBridge()

        patch_data = {
            "name": "Orphan Theme",
            "type": "patch",
            "base": "non_existent_theme",
            "overrides": {
                "Accent": "#9c27b0"
            }
        }

        result = bridge._expand_patch_theme(patch_data)

        # Should use fallback dark palette
        assert result["palette"]["is_dark"] == True
        assert result["palette"]["Accent"] == "#9c27b0"

    def test_expand_patch_empty_overrides(self, mock_themes):
        """Test expanding a patch with no overrides."""
        from dataforge_studio.ui.core.theme_bridge import ThemeBridge

        class MockBridge:
            themes = mock_themes

            def _expand_patch_theme(self, patch_data):
                return ThemeBridge._expand_patch_theme(self, patch_data)

        bridge = MockBridge()

        patch_data = {
            "name": "Unchanged Theme",
            "type": "patch",
            "base": "minimal_dark",
            "overrides": {}
        }

        result = bridge._expand_patch_theme(patch_data)

        # Should be identical to base
        assert result["palette"]["Accent"] == "#0078d7"
        assert result["palette"]["Frame_BG"] == "#252525"


class TestPatchThemeFileFormat:
    """Test the patch theme JSON file format."""

    def test_patch_theme_json_structure(self):
        """Test that patch themes have correct JSON structure."""
        patch_theme = {
            "name": "Test Theme",
            "type": "patch",
            "base": "minimal_dark",
            "overrides": {
                "Accent": "#ff0000",
                "Frame_BG": "#000000"
            }
        }

        # Validate structure
        assert patch_theme["type"] == "patch"
        assert "base" in patch_theme
        assert "overrides" in patch_theme
        assert isinstance(patch_theme["overrides"], dict)

        # Serialize and deserialize
        json_str = json.dumps(patch_theme, indent=2)
        loaded = json.loads(json_str)

        assert loaded == patch_theme

    def test_patch_theme_roundtrip(self, tmp_path):
        """Test saving and loading a patch theme file."""
        patch_theme = {
            "name": "Roundtrip Test",
            "type": "patch",
            "base": "minimal_light",
            "overrides": {
                "Accent": "#00ff00"
            }
        }

        theme_file = tmp_path / "test_theme.json"
        with open(theme_file, 'w', encoding='utf-8') as f:
            json.dump(patch_theme, f, indent=2, ensure_ascii=False)

        with open(theme_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        assert loaded["name"] == "Roundtrip Test"
        assert loaded["type"] == "patch"
        assert loaded["base"] == "minimal_light"
        assert loaded["overrides"]["Accent"] == "#00ff00"
