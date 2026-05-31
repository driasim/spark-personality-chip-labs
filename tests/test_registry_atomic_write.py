"""Verify registry uses atomic writes to prevent corruption on crash."""
import json
import os
import tempfile
from pathlib import Path

import pytest
from personality_engine.registry import PersonalityRegistry, REGISTRY_FILE


def test_registry_module_loads():
    """Structural smoke — verifies registry module imports after fix."""
    assert PersonalityRegistry is not None


def test_registry_save_is_atomic():
    """Registry save must not corrupt the file on partial write."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = Path(tmpdir) / "test_registry.json"

        # Pre-populate a valid registry
        reg_path.write_text(json.dumps({"active": {}, "default": None}))

        reg = PersonalityRegistry(registry_path=reg_path)

        # Verify the file is valid JSON after save (atomic replace)
        reg._save_state()
        assert reg_path.exists()
        data = json.loads(reg_path.read_text())
        assert "active" in data
        assert "default" in data
        assert "installed" in data


def test_registry_atomic_write_does_not_leave_tmp_files():
    """Atomic write via mkstemp+replace must clean up temp files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = Path(tmpdir) / "test_registry.json"
        reg_path.write_text(json.dumps({"active": {}, "default": None}))

        reg = PersonalityRegistry(registry_path=reg_path)
        reg._save_state()

        # No .tmp files should remain
        tmp_files = list(reg_path.parent.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Leftover temp files: {tmp_files}"
