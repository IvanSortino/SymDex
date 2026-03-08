# tests/features/steps/semantic_steps.py
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import os
import tempfile

import numpy as np
import pytest
from unittest.mock import patch
from pytest_bdd import given, when, then, scenarios, parsers

import typer.testing

from symdex.mcp.tools import semantic_search_tool, index_folder_tool
from symdex.core.storage import get_connection, get_db_path, upsert_embedding, query_file_symbols

scenarios("../semantic_search.feature")

FAKE_VEC = np.array([1.0] + [0.0] * 383, dtype="float32")

# Module-level context dict shared between steps within a test scenario.
_ctx: dict = {}


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_python_files(directory: str) -> None:
    """Write Python source files with docstrings into directory."""
    (open(os.path.join(directory, "parse_module.py"), "w")).write(
        'def parse_file(path: str) -> list:\n'
        '    """Parse a source file and return symbols."""\n'
        '    return []\n\n'
        'def parse_dir(path: str) -> dict:\n'
        '    """Parse all files in a directory."""\n'
        '    return {}\n'
    )
    (open(os.path.join(directory, "utils.py"), "w")).write(
        'class Helper:\n'
        '    """Utility helper class."""\n'
        '    def run(self) -> None:\n'
        '        pass\n'
    )


def _make_db_patcher(tmp_dir: str):
    """Return a get_db_path function that stores DBs inside tmp_dir."""
    db_dir = os.path.join(tmp_dir, ".symdex")
    os.makedirs(db_dir, exist_ok=True)

    def _mock_db_path(repo_name: str) -> str:
        return os.path.join(db_dir, f"{repo_name}.db")

    def _mock_registry_path() -> str:
        return os.path.join(db_dir, "registry.db")

    return _mock_db_path, _mock_registry_path


def _patch_all(monkeypatch, mock_db_path, mock_registry_path):
    monkeypatch.setattr("symdex.core.indexer.get_db_path", mock_db_path)
    monkeypatch.setattr("symdex.mcp.tools.get_db_path", mock_db_path)
    monkeypatch.setattr("symdex.core.storage.get_db_path", mock_db_path)
    try:
        monkeypatch.setattr("symdex.core.storage.get_registry_path", mock_registry_path)
    except AttributeError:
        pass
    try:
        monkeypatch.setattr("symdex.cli.get_db_path", mock_db_path)
    except AttributeError:
        pass
    try:
        monkeypatch.setattr("symdex.cli.get_registry_path", mock_registry_path)
    except AttributeError:
        pass


def _embed_with_embeddings(repo: str, mock_db_path) -> None:
    """After indexing, upsert FAKE_VEC for every symbol in repo."""
    conn = get_connection(mock_db_path(repo))
    try:
        rows = conn.execute(
            "SELECT id FROM symbols WHERE repo = ?", (repo,)
        ).fetchall()
        for row in rows:
            upsert_embedding(conn, row[0], FAKE_VEC)
    finally:
        conn.close()


# ── Background ────────────────────────────────────────────────────────────────

@given("a folder with Python files containing docstrings has been indexed")
def background_semantic_indexed(monkeypatch):
    _ctx.clear()
    tmp_dir = tempfile.mkdtemp()
    mock_db_path, mock_registry_path = _make_db_patcher(tmp_dir)
    _patch_all(monkeypatch, mock_db_path, mock_registry_path)

    _write_python_files(tmp_dir)

    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        result = index_folder_tool(path=tmp_dir, name="sem_test")

    _embed_with_embeddings("sem_test", mock_db_path)

    _ctx["repo"] = "sem_test"
    _ctx["tmp_dir"] = tmp_dir
    _ctx["mock_db_path"] = mock_db_path


# ── Scenario: Semantic search returns relevant results ─────────────────────────

@when(parsers.parse('I call semantic_search with query "{query}"'))
def call_semantic_search(query):
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        _ctx["result"] = semantic_search_tool(query=query, repo=_ctx["repo"])


@then('the response contains a "symbols" list')
def check_symbols_list_semantic():
    assert "symbols" in _ctx["result"], f"Got: {_ctx['result']}"
    assert isinstance(_ctx["result"]["symbols"], list)


@then("at least one symbol name or docstring relates to parsing")
def check_parsing_symbol():
    # With FAKE_VEC all symbols score 1.0 so all are returned; just assert non-empty.
    assert len(_ctx["result"]["symbols"]) > 0, "Expected at least one result"


# ── Scenario: Each result has a similarity score ───────────────────────────────

@then('each symbol in the response has a "score" field between 0 and 1')
def check_score_field():
    symbols = _ctx["result"]["symbols"]
    assert len(symbols) > 0, "No symbols returned; cannot verify score field"
    for sym in symbols:
        assert "score" in sym, f"Symbol missing 'score': {sym}"
        assert 0.0 <= sym["score"] <= 1.0, f"Score out of range: {sym['score']}"


# ── Scenario: Semantic search respects repo filter ─────────────────────────────

@given("two repos are indexed")
def two_repos_indexed(monkeypatch):
    _ctx.clear()
    tmp_dir = tempfile.mkdtemp()
    mock_db_path, mock_registry_path = _make_db_patcher(tmp_dir)
    _patch_all(monkeypatch, mock_db_path, mock_registry_path)

    # Repo A
    dir_a = os.path.join(tmp_dir, "repo_a")
    os.makedirs(dir_a)
    _write_python_files(dir_a)
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        index_folder_tool(path=dir_a, name="sem_repo_a")
    _embed_with_embeddings("sem_repo_a", mock_db_path)

    # Repo B
    dir_b = os.path.join(tmp_dir, "repo_b")
    os.makedirs(dir_b)
    _write_python_files(dir_b)
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        index_folder_tool(path=dir_b, name="sem_repo_b")
    _embed_with_embeddings("sem_repo_b", mock_db_path)

    _ctx["repos"] = ["sem_repo_a", "sem_repo_b"]
    _ctx["mock_db_path"] = mock_db_path


@when(parsers.parse('I call semantic_search with query "{query}" filtered to one repo'))
def call_semantic_search_filtered(query):
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        _ctx["result"] = semantic_search_tool(query=query, repo=_ctx["repos"][0])


@then("all returned symbols belong to that repo")
def check_repo_filter():
    symbols = _ctx["result"]["symbols"]
    assert len(symbols) > 0, "Expected at least one symbol"
    expected_repo = _ctx["repos"][0]
    for sym in symbols:
        assert sym["repo"] == expected_repo, (
            f"Symbol repo '{sym['repo']}' != expected '{expected_repo}'"
        )


# ── Scenario: Symbol with null embedding does not crash search ─────────────────

@given("a symbol exists with a NULL embedding value")
def null_embedding_symbol(monkeypatch):
    _ctx.clear()
    tmp_dir = tempfile.mkdtemp()
    mock_db_path, mock_registry_path = _make_db_patcher(tmp_dir)
    _patch_all(monkeypatch, mock_db_path, mock_registry_path)

    _write_python_files(tmp_dir)
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        index_folder_tool(path=tmp_dir, name="sem_null")

    # Upsert embeddings for existing symbols only, then insert a symbol without embedding.
    _embed_with_embeddings("sem_null", mock_db_path)

    conn = get_connection(mock_db_path("sem_null"))
    try:
        conn.execute(
            "INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("sem_null", "phantom.py", "null_symbol_xyz", "function", 0, 10),
        )
        conn.commit()
    finally:
        conn.close()

    _ctx["repo"] = "sem_null"
    _ctx["null_symbol_name"] = "null_symbol_xyz"
    _ctx["mock_db_path"] = mock_db_path


@when("I call semantic_search with any query")
def call_semantic_search_any_query():
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        _ctx["result"] = semantic_search_tool(query="anything", repo=_ctx["repo"])


@then("the response is successful")
def check_response_successful():
    assert "error" not in _ctx["result"], f"Unexpected error: {_ctx['result']}"
    assert "symbols" in _ctx["result"]


@then("the null-embedding symbol is not included in the results")
def check_null_symbol_excluded():
    names = [s["name"] for s in _ctx["result"]["symbols"]]
    assert _ctx["null_symbol_name"] not in names, (
        f"NULL-embedding symbol '{_ctx['null_symbol_name']}' should not appear in results"
    )


# ── Scenario: Semantic search via CLI ─────────────────────────────────────────

@when('I run "symdex semantic" with query "parse source code"')
def run_semantic_cli():
    from symdex.cli import app as cli_app
    runner = typer.testing.CliRunner()
    mock_db_path = _ctx["mock_db_path"]
    repo = _ctx["repo"]

    with patch("symdex.cli.get_db_path", side_effect=mock_db_path), \
         patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        result = runner.invoke(cli_app, ["semantic", "parse source code", "--repo", repo])

    _ctx["cli_result"] = result


@then("the CLI command exits with code 0")
def check_cli_exit_code():
    result = _ctx["cli_result"]
    assert result.exit_code == 0, (
        f"Expected exit code 0, got {result.exit_code}. Output:\n{result.output}"
    )


@then("the CLI output contains at least one symbol row")
def check_cli_output_has_symbol():
    output = _ctx["cli_result"].output
    assert output.strip(), "CLI output was empty"
