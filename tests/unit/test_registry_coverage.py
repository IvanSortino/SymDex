# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.
#
# Targeted coverage tests for symdex/graph/registry.py.
# Covers register_repo, list_all_repos, get_repo_db, and
# the exception-swallowing branch in search_across_repos.

import os
import pytest
from symdex.graph.registry import (
    register_repo,
    list_all_repos,
    get_repo_db,
    search_across_repos,
)
from symdex.core.storage import upsert_repo, query_repos


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
        "symdex.graph.registry.get_db_path",
    ):
        monkeypatch.setattr(site, _mock_db_path)

    try:
        monkeypatch.setattr("symdex.core.storage.get_registry_path", _mock_registry_path)
    except AttributeError:
        pass


# ── register_repo ──────────────────────────────────────────────────────────────

def test_register_repo_appears_in_query():
    register_repo("reg_test_repo", root_path="/tmp/reg_test")
    repos = query_repos()
    assert any(r["name"] == "reg_test_repo" for r in repos)


def test_register_repo_stores_root_path():
    register_repo("reg_test_repo2", root_path="/tmp/reg2")
    repos = query_repos()
    match = next(r for r in repos if r["name"] == "reg_test_repo2")
    assert match["root_path"] == "/tmp/reg2"


# ── list_all_repos ─────────────────────────────────────────────────────────────

def test_list_all_repos_empty():
    result = list_all_repos()
    assert result == []


def test_list_all_repos_after_registration():
    register_repo("list_test_repo", root_path="/tmp/list")
    result = list_all_repos()
    assert any(r["name"] == "list_test_repo" for r in result)


# ── get_repo_db ────────────────────────────────────────────────────────────────

def test_get_repo_db_returns_none_for_unknown():
    result = get_repo_db("totally_unknown_repo_xyz")
    assert result is None


def test_get_repo_db_returns_path_for_known(tmp_path):
    db_dir = str(tmp_path / ".symdex")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "known_repo.db")
    upsert_repo("known_repo", root_path="/tmp/known", db_path=db_path)
    result = get_repo_db("known_repo")
    assert result == db_path


# ── search_across_repos — exception branch ─────────────────────────────────────

def test_search_across_repos_skips_bad_db(tmp_path):
    """Register a repo pointing at a corrupt/nonexistent DB — should not raise."""
    upsert_repo("bad_db_repo", root_path="/tmp/bad", db_path="/nonexistent/path/bad.db")
    # Should silently continue past the bad DB and return []
    results = search_across_repos(query="anything")
    assert isinstance(results, list)


def test_search_across_repos_deduplication(tmp_path, monkeypatch):
    """Two repos with same symbol name — both should appear (different repo keys)."""
    from symdex.mcp.tools import index_folder_tool

    def _mock_db_path(repo_name: str) -> str:
        db_dir = str(tmp_path / ".symdex")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, f"{repo_name}.db")

    monkeypatch.setattr("symdex.mcp.tools.get_db_path", _mock_db_path)
    monkeypatch.setattr("symdex.core.indexer.get_db_path", _mock_db_path)
    monkeypatch.setattr("symdex.core.storage.get_db_path", _mock_db_path)

    src1 = tmp_path / "proj1"
    src1.mkdir()
    (src1 / "mod.py").write_text("def shared_name(): pass\n")
    index_folder_tool(path=str(src1), name="proj_one")

    src2 = tmp_path / "proj2"
    src2.mkdir()
    (src2 / "mod.py").write_text("def shared_name(): pass\n")
    index_folder_tool(path=str(src2), name="proj_two")

    results = search_across_repos(query="shared_name")
    # Both repos have the symbol — dedup is per (repo, file, name) so both should appear
    repo_names = {r["repo"] for r in results}
    assert "proj_one" in repo_names
    assert "proj_two" in repo_names
