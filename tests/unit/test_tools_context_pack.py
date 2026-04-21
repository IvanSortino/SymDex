# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from symdex.core.indexer import index_folder
from symdex.core.storage import upsert_repo
from symdex.mcp.tools import build_context_pack_tool


def indexed_pack_repo(tmp_path, monkeypatch) -> dict:
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(tmp_path / ".symdex"))
    src = tmp_path / "toolpackrepo"
    src.mkdir()
    (src / "app.py").write_text(
        "def create_checkout():\n"
        "    return 'checkout'\n\n"
        "@app.get('/checkout')\n"
        "def checkout_route():\n"
        "    return create_checkout()\n",
        encoding="utf-8",
    )
    result = index_folder(str(src), repo="tool_pack_repo", embed=False)
    upsert_repo(result.repo, root_path=str(src), db_path=result.db_path)
    return {"repo": result.repo, "path": str(src)}


def test_build_context_pack_tool_returns_pack(tmp_path, monkeypatch):
    indexed = indexed_pack_repo(tmp_path, monkeypatch)

    resp = build_context_pack_tool(
        repo=indexed["repo"],
        query="checkout",
        token_budget=800,
    )

    assert resp["repo"] == indexed["repo"]
    assert resp["selected_evidence"]
    assert "quality_summary" in resp


def test_build_context_pack_tool_validates_query(tmp_path, monkeypatch):
    indexed = indexed_pack_repo(tmp_path, monkeypatch)

    resp = build_context_pack_tool(repo=indexed["repo"], query="")

    assert resp["error"]["code"] == 400
    assert resp["error"]["key"] == "invalid_request"


def test_build_context_pack_tool_validates_repo():
    resp = build_context_pack_tool(repo="missing_pack_repo", query="checkout")

    assert resp["error"]["code"] == 404
    assert resp["error"]["key"] == "repo_not_indexed"
