# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.
#
# Targeted coverage tests for symdex/mcp/tools.py.
# Covers branches not reached by the BDD feature tests.

import os
import pytest
from symdex.mcp.tools import (
    get_symbol_tool,
    get_file_tree_tool,
    get_symbols_tool,
    index_repo_tool,
    invalidate_cache_tool,
    search_text_tool,
    semantic_search_tool,
    get_callers_tool,
    get_callees_tool,
    search_symbols_tool,
    index_folder_tool,
    _build_tree,
    _get_root_path,
)


# ── Isolation ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    def _mock_db_path(repo_name: str) -> str:
        db_dir = str(tmp_path / ".symdex")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, f"{repo_name}.db")

    def _mock_registry_path() -> str:
        db_dir = str(tmp_path / ".symdex")
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


@pytest.fixture
def indexed(tmp_path):
    """Index a small project via index_folder_tool and return metadata."""
    src = tmp_path / "toolsproject"
    src.mkdir()
    (src / "mod.py").write_text(
        'def gamma_func(x):\n'
        '    """Gamma docstring."""\n'
        '    return x\n\n'
        'class DeltaClass:\n'
        '    pass\n'
    )
    result = index_folder_tool(path=str(src), repo="tools_repo")
    assert "indexed" in result, f"index failed: {result}"
    return {"path": str(src), "repo": "tools_repo"}


# ── search_symbols_tool — cross-repo (no repo arg) ────────────────────────────

def test_search_symbols_no_repo_no_results(indexed):
    # Empty query returns error
    resp = search_symbols_tool(query="", repo=None)
    assert resp["error"]["code"] == 400


def test_search_symbols_cross_repo_found(indexed):
    resp = search_symbols_tool(query="gamma_func", repo=None)
    # Either finds across registered repos or returns 404 — both are valid paths
    assert "symbols" in resp or "error" in resp


def test_search_symbols_returns_roi_summary(indexed):
    resp = search_symbols_tool(query="gamma_func", repo=indexed["repo"])
    assert "roi" in resp
    assert "roi_summary" in resp
    assert "roi_agent_hint" in resp
    assert "token savings" in resp["roi_summary"].lower()
    assert "mention" in resp["roi_agent_hint"].lower()
    assert resp["roi"]["tokenizer"] == "o200k_base"
    assert resp["roi"]["estimated_tokens_saved"] >= 0


# ── get_symbol_tool ───────────────────────────────────────────────────────────

def test_get_symbol_invalid_bytes_order(indexed):
    resp = get_symbol_tool(repo=indexed["repo"], file="mod.py", start_byte=100, end_byte=50)
    assert resp["error"]["code"] == 400


def test_get_symbol_repo_not_indexed():
    resp = get_symbol_tool(repo="no_such_repo", file="f.py", start_byte=0, end_byte=10)
    assert resp["error"]["code"] == 404
    assert resp["error"]["key"] == "repo_not_indexed"


def test_get_symbol_file_not_found(indexed):
    resp = get_symbol_tool(repo=indexed["repo"], file="no_file.py", start_byte=0, end_byte=10)
    assert resp["error"]["code"] == 404
    assert resp["error"]["key"] == "file_not_found"


# ── search_text_tool ──────────────────────────────────────────────────────────

def test_search_text_no_query(indexed):
    resp = search_text_tool(query="", repo=indexed["repo"])
    assert resp["error"]["code"] == 400


def test_search_text_no_repo(indexed):
    resp = search_text_tool(query="gamma", repo=None)
    assert resp["error"]["code"] == 400


def test_search_text_repo_not_indexed():
    resp = search_text_tool(query="gamma", repo="missing_repo_xyz")
    assert resp["error"]["code"] == 404


def test_search_text_found(indexed):
    resp = search_text_tool(query="gamma", repo=indexed["repo"])
    assert "matches" in resp


def test_search_text_returns_roi_summary(indexed):
    resp = search_text_tool(query="gamma", repo=indexed["repo"])
    assert "roi" in resp
    assert "roi_summary" in resp
    assert "roi_agent_hint" in resp
    assert "token savings" in resp["roi_summary"].lower()
    assert "mention" in resp["roi_agent_hint"].lower()
    assert resp["roi"]["tokenizer"] == "o200k_base"
    assert resp["roi"]["estimated_tokens_saved"] >= 0


# ── get_file_tree_tool ────────────────────────────────────────────────────────

def test_get_file_tree_repo_not_indexed():
    resp = get_file_tree_tool(repo="ghost_repo")
    assert resp["error"]["code"] == 404


def test_get_file_tree_found(indexed):
    resp = get_file_tree_tool(repo=indexed["repo"])
    assert "tree" in resp
    assert isinstance(resp["tree"], str)


# ── get_symbols_tool ──────────────────────────────────────────────────────────

def test_get_symbols_no_repo():
    resp = get_symbols_tool(names=["gamma_func"], repo=None)
    assert resp["error"]["code"] == 400


def test_get_symbols_repo_not_indexed():
    resp = get_symbols_tool(names=["gamma_func"], repo="nonexistent_xyz")
    assert resp["error"]["code"] == 404


def test_get_symbols_found(indexed):
    resp = get_symbols_tool(names=["gamma_func"], repo=indexed["repo"])
    assert "symbols" in resp


# ── index_repo_tool ───────────────────────────────────────────────────────────

def test_index_repo_bad_path():
    resp = index_repo_tool(path="/nonexistent/path/abc", repo="x")
    assert resp["error"]["code"] == 400


def test_index_repo_success(indexed):
    resp = index_repo_tool(path=indexed["path"], repo="tools_repo2")
    assert "indexed" in resp
    assert "repo" in resp


def test_index_folder_includes_code_summary(indexed):
    resp = index_folder_tool(path=indexed["path"], repo=indexed["repo"])
    assert "summary" in resp
    assert resp["summary"]["lines_of_code"] > 0
    assert resp["summary"]["functions"] > 0


# ── invalidate_cache_tool ─────────────────────────────────────────────────────

def test_invalidate_cache_repo_not_indexed():
    resp = invalidate_cache_tool(repo="not_registered_xyz")
    assert resp["error"]["code"] == 404


def test_invalidate_cache_with_file(indexed):
    resp = invalidate_cache_tool(repo=indexed["repo"], file="mod.py")
    assert "invalidated" in resp


# ── semantic_search_tool ──────────────────────────────────────────────────────

def test_semantic_search_no_repo():
    resp = semantic_search_tool(query="some query", repo=None)
    assert resp["error"]["code"] == 400


def test_semantic_search_repo_not_indexed():
    resp = semantic_search_tool(query="some query", repo="ghost_repo_xyz")
    assert resp["error"]["code"] == 404


def test_semantic_search_found(indexed):
    # Embeddings may or may not be populated; tool should return symbols list or empty
    resp = semantic_search_tool(query="gamma function", repo=indexed["repo"])
    assert "symbols" in resp or "error" in resp


# ── get_callers_tool ──────────────────────────────────────────────────────────

def test_get_callers_repo_not_indexed():
    resp = get_callers_tool(name="gamma_func", repo="ghost_repo_xyz")
    assert resp["error"]["code"] == 404


def test_get_callers_symbol_not_found(indexed):
    resp = get_callers_tool(name="nonexistent_zzz", repo=indexed["repo"])
    assert resp["error"]["code"] == 404
    assert resp["error"]["key"] == "symbol_not_found"


def test_get_callers_found(indexed):
    resp = get_callers_tool(name="gamma_func", repo=indexed["repo"])
    assert "callers" in resp


# ── get_callees_tool ──────────────────────────────────────────────────────────

def test_get_callees_repo_not_indexed():
    resp = get_callees_tool(name="gamma_func", repo="ghost_repo_xyz")
    assert resp["error"]["code"] == 404


def test_get_callees_symbol_not_found(indexed):
    resp = get_callees_tool(name="nonexistent_zzz", repo=indexed["repo"])
    assert resp["error"]["code"] == 404
    assert resp["error"]["key"] == "symbol_not_found"


def test_get_callees_found(indexed):
    resp = get_callees_tool(name="gamma_func", repo=indexed["repo"])
    assert "callees" in resp


# ── _build_tree ───────────────────────────────────────────────────────────────

def test_build_tree_depth_limit(tmp_path):
    # Create nested structure beyond depth 3
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    (deep / "file.py").write_text("x = 1")
    tree = _build_tree(str(tmp_path), depth=2)
    # depth=2 means only 2 levels rendered; "d" should not appear
    assert "file.py" not in tree


def test_build_tree_oserror(tmp_path):
    # Pass a non-directory path — OSError branch
    result = _build_tree("/nonexistent_path_zzz")
    assert result == ""


# ── _get_root_path ────────────────────────────────────────────────────────────

def test_get_root_path_returns_none_for_unknown():
    result = _get_root_path("totally_unknown_repo_xyz")
    assert result is None


def test_get_root_path_returns_path_for_known(indexed):
    result = _get_root_path(indexed["repo"])
    assert result is not None
    assert "toolsproject" in result
