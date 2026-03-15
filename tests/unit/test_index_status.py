# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.
#
# Tests for get_index_status MCP tool.

import os
import pytest
import tempfile
from symdex.mcp.tools import get_index_status_tool, index_folder_tool


# ── Isolation ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    """Isolate tests by using a unique temp directory for each test."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        def _mock_db_path(repo_name: str) -> str:
            db_dir = os.path.join(tmp_dir, ".symdex")
            os.makedirs(db_dir, exist_ok=True)
            return os.path.join(db_dir, f"{repo_name}.db")

        def _mock_registry_path() -> str:
            db_dir = os.path.join(tmp_dir, ".symdex")
            os.makedirs(db_dir, exist_ok=True)
            return os.path.join(db_dir, "registry.db")

        for site in (
            "symdex.core.indexer.get_db_path",
            "symdex.core.storage.get_db_path",
            "symdex.mcp.tools.get_db_path",
        ):
            monkeypatch.setattr(site, _mock_db_path)

        for site in ("symdex.core.storage.get_registry_path",):
            try:
                monkeypatch.setattr(site, _mock_registry_path)
            except AttributeError:
                pass

        yield


# ── Tests ──────────────────────────────────────────────────────────────────

def test_get_index_status_repo_not_found():
    """Calling get_index_status on an unknown repo returns error."""
    resp = get_index_status_tool(repo="no_such_repo")
    assert "error" in resp
    assert resp["error"]["code"] == 404


def test_get_index_status_returns_fields():
    """Index a tiny project and verify all status fields are present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        src = Path(tmpdir) / "statusproject"
        src.mkdir()
        (src / "mod.py").write_text(
            'def hello():\n'
            '    """Say hello."""\n'
            '    return "hello"\n\n'
            'class Greeter:\n'
            '    pass\n'
        )

        # Index the project
        result = index_folder_tool(path=str(src), name="status_repo")
        assert "indexed" in result
        assert result["indexed"] > 0

        # Get status
        resp = get_index_status_tool(repo="status_repo")

        # Verify all required fields are present
        assert "repo" in resp
        assert "symbol_count" in resp
        assert "file_count" in resp
        assert "last_indexed" in resp
        assert "age_seconds" in resp
        assert "stale" in resp
        assert "watcher_active" in resp

        # Verify field types and values
        assert resp["repo"] == "status_repo"
        assert isinstance(resp["symbol_count"], int)
        assert resp["symbol_count"] > 0  # We indexed a function and a class
        assert isinstance(resp["file_count"], int)
        assert resp["file_count"] > 0  # At least one file
        assert isinstance(resp["last_indexed"], str)
        assert isinstance(resp["age_seconds"], (int, float))
        assert resp["age_seconds"] >= 0
        assert isinstance(resp["stale"], bool)
        assert resp["stale"] is False  # Freshly indexed, not stale
        assert isinstance(resp["watcher_active"], bool)
        assert resp["watcher_active"] is False  # No watcher running in test
