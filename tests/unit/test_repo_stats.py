# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.
#
# Tests for get_repo_stats MCP tool.

import os
import pytest
import tempfile
from symdex.mcp.tools import get_repo_stats_tool, index_folder_tool


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

def test_get_repo_stats_repo_not_found():
    """Calling get_repo_stats on an unknown repo returns error."""
    resp = get_repo_stats_tool(repo="no_such_repo")
    assert "error" in resp
    assert resp["error"]["code"] == 404


def test_get_repo_stats_returns_fields():
    """Index a tiny multi-file project and verify all stats fields are present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from pathlib import Path
        src = Path(tmpdir) / "statsproject"
        src.mkdir()

        # Create Python files
        (src / "utils.py").write_text(
            'def helper():\n'
            '    """A helper function."""\n'
            '    return "helper"\n\n'
            'def another_helper():\n'
            '    """Another one."""\n'
            '    return "another"\n'
        )
        (src / "main.py").write_text(
            'def main():\n'
            '    """Main entry."""\n'
            '    return "main"\n'
        )

        # Create a JavaScript file
        (src / "script.js").write_text(
            'function greet(name) {\n'
            '  return "Hello " + name;\n'
            '}\n'
        )

        # Index the project
        result = index_folder_tool(path=str(src), name="stats_repo")
        assert "indexed" in result
        assert result["indexed"] > 0

        # Get stats
        resp = get_repo_stats_tool(repo="stats_repo")

        # Verify no error
        assert "error" not in resp, f"Got error: {resp.get('error')}"

        # Verify all required fields are present
        assert "repo" in resp
        assert "symbol_count" in resp
        assert "file_count" in resp
        assert "lines_of_code" in resp
        assert "language_distribution" in resp
        assert "top_fan_in" in resp
        assert "top_fan_out" in resp
        assert "orphan_files" in resp
        assert "circular_dep_count" in resp
        assert "edge_count" in resp

        # Verify field types and values
        assert resp["repo"] == "stats_repo"
        assert isinstance(resp["symbol_count"], int)
        assert resp["symbol_count"] > 0  # We indexed functions
        assert isinstance(resp["file_count"], int)
        assert resp["file_count"] > 0  # At least 2 Python + 1 JS files
        assert isinstance(resp["lines_of_code"], int)
        assert resp["lines_of_code"] > 0
        assert isinstance(resp["language_distribution"], dict)
        assert "python" in resp["language_distribution"]
        assert resp["language_distribution"]["python"] > 0
        assert isinstance(resp["top_fan_in"], list)
        assert isinstance(resp["top_fan_out"], list)
        assert isinstance(resp["orphan_files"], list)
        assert isinstance(resp["circular_dep_count"], int)
        assert resp["circular_dep_count"] >= 0
        assert isinstance(resp["edge_count"], int)
        assert resp["edge_count"] >= 0
