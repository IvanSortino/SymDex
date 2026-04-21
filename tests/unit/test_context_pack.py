# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from symdex.core.context_pack import build_context_pack
from symdex.core.indexer import index_folder
from symdex.core.storage import upsert_repo


def index_pack_fixture(tmp_path, monkeypatch, embed: bool = False) -> str:
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(tmp_path / ".symdex"))
    src = tmp_path / "packrepo"
    src.mkdir()
    (src / ".symdexignore").write_text("ignored/\n", encoding="utf-8")
    (src / "app.py").write_text(
        "class CheckoutRequest:\n"
        "    pass\n\n"
        "def charge_card():\n"
        "    return 'charged'\n\n"
        "def create_checkout():\n"
        "    return charge_card()\n\n"
        "@app.get('/checkout')\n"
        "def checkout_route():\n"
        "    return create_checkout()\n",
        encoding="utf-8",
    )
    docs = src / "docs"
    docs.mkdir()
    (docs / "checkout.md").write_text(
        "# Checkout API\n\n"
        "Use the checkout route to create checkout sessions.\n",
        encoding="utf-8",
    )
    tests = src / "tests"
    tests.mkdir()
    (tests / "test_checkout.py").write_text(
        "def test_checkout_route():\n"
        "    assert 'checkout'\n",
        encoding="utf-8",
    )
    ignored = src / "ignored"
    ignored.mkdir()
    (ignored / "secret.py").write_text(
        "def checkout_secret():\n"
        "    return 'ignore me'\n",
        encoding="utf-8",
    )

    result = index_folder(str(src), repo="pack_repo", embed=embed)
    upsert_repo(result.repo, root_path=str(src), db_path=result.db_path)
    return result.repo


def test_build_context_pack_respects_budget(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    pack = build_context_pack(repo=repo, query="alpha checkout", token_budget=30)

    assert pack["budget"]["estimated_tokens"] <= pack["budget"]["available_tokens"]
    assert pack["selected_evidence"]
    assert pack["omitted_candidates"]


def test_build_context_pack_includes_source_paths(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    pack = build_context_pack(repo=repo, query="checkout", token_budget=800)

    assert all(item["file"] for item in pack["selected_evidence"])
    assert all("source" in item for item in pack["selected_evidence"])


def test_build_context_pack_skips_semantic_when_no_embeddings(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch, embed=False)

    pack = build_context_pack(repo=repo, query="checkout", token_budget=800)

    assert pack["quality_summary"]["has_embeddings"] is False
    assert any("semantic search skipped" in warning for warning in pack["warnings"])


def test_context_pack_include_routes_only(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    pack = build_context_pack(
        repo=repo,
        query="checkout",
        include=["routes"],
        token_budget=800,
    )

    assert pack["routes"]
    assert {item["type"] for item in pack["selected_evidence"]} <= {"route"}


def test_context_pack_exclude_tests(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    pack = build_context_pack(
        repo=repo,
        query="checkout",
        exclude=["tests"],
        token_budget=1200,
    )

    assert not pack["tests"]


def test_context_pack_is_deterministic(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    first = build_context_pack(repo=repo, query="checkout", token_budget=800)
    second = build_context_pack(repo=repo, query="checkout", token_budget=800)

    assert first["selected_evidence"] == second["selected_evidence"]
    assert first["omitted_candidates"] == second["omitted_candidates"]


def test_context_pack_never_reads_ignored_files(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    pack = build_context_pack(repo=repo, query="checkout", token_budget=1200)

    paths = {item["file"] for item in pack["selected_evidence"]}
    paths.update(item["file"] for item in pack["omitted_candidates"])
    assert "ignored/secret.py" not in paths
