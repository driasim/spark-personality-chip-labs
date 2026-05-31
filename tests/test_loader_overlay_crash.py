"""Verify loader skips broken overlay YAML files instead of crashing."""
import pytest
from pathlib import Path
import tempfile
import os

from personality_engine.loader import _load_directory


def test_loader_module_loads():
    """Structural smoke — verifies loader module imports after fix."""
    from personality_engine.loader import load_personality
    assert load_personality is not None


def test_broken_overlay_yaml_skipped_not_crashed():
    """A directory with a malformed overlay YAML file should still load the base personality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        # Valid base personality.yaml
        (base / "personality.yaml").write_text(
            "id: test-chip\nname: Test\narchetype: sage\n"
        )
        # Malformed overlay — unparseable YAML
        (base / "traits.yaml").write_text("openness: :::broken:::\n")
        try:
            spec = _load_directory(base)
            # Should have loaded base spec despite broken overlay
            assert isinstance(spec, dict)
            assert spec.get("name") == "Test"
        except Exception as e:
            pytest.fail(f"_load_directory crashed on broken overlay: {e}")


def test_valid_overlay_still_merges():
    """Valid overlay files should still merge correctly after the fix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "personality.yaml").write_text(
            "id: test-chip\nname: Test\narchetype: sage\ntraits:\n  openness: 0.5\n"
        )
        (base / "traits.yaml").write_text(
            "traits:\n  openness: 0.9\n  extraversion: 0.7\n"
        )
        spec = _load_directory(base)
        assert spec.get("traits", {}).get("openness") == 0.9
        assert spec.get("traits", {}).get("extraversion") == 0.7
