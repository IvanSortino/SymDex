# tests/features/steps/registry_steps.py
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import os
import tempfile
import textwrap
from unittest.mock import patch

import numpy as np
from pytest_bdd import given, when, then, scenarios, parsers

from symdex.mcp.tools import (
    index_folder_tool,
    search_symbols_tool,
    list_repos_tool,
)

scenarios("../cross_repo.feature")

FAKE_VEC = np.array([1.0] + [0.0] * 383, dtype="float32")

_ctx: dict = {}

ALPHA_SRC = textwrap.dedent("""\
    def parse_file(path):
        '''Parse a source file in alpha.'''
        return []
""")

BETA_SRC = textwrap.dedent("""\
    def parse_file(src):
        '''Parse source in beta.'''
        return {}
""")


# ── helpers ─────────────────────────────────────────────────────────────────

def _make_db_patcher(db_dir: str):
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


# ── Background ───────────────────────────────────────────────────────────────

@given(parsers.parse('two separate repos "{alpha}" and "{beta}" are registered and indexed'))
def two_repos_indexed(alpha, beta, monkeypatch):
    _ctx.clear()
    tmp_dir = tempfile.mkdtemp()
    db_dir = os.path.join(tmp_dir, ".symdex")
    mock_db_path, mock_registry_path = _make_db_patcher(db_dir)
    _patch_all(monkeypatch, mock_db_path, mock_registry_path)

    alpha_dir = os.path.join(tmp_dir, alpha)
    os.makedirs(alpha_dir, exist_ok=True)
    with open(os.path.join(alpha_dir, "alpha_mod.py"), "w") as f:
        f.write(ALPHA_SRC)

    beta_dir = os.path.join(tmp_dir, beta)
    os.makedirs(beta_dir, exist_ok=True)
    with open(os.path.join(beta_dir, "beta_mod.py"), "w") as f:
        f.write(BETA_SRC)

    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        index_folder_tool(alpha_dir, name=alpha)
        index_folder_tool(beta_dir, name=beta)

    _ctx.update({"alpha": alpha, "beta": beta, "tmp_dir": tmp_dir})


# ── When steps ───────────────────────────────────────────────────────────────

@when("I call list_repos")
def call_list_repos():
    _ctx["response"] = list_repos_tool()


@when(parsers.parse('I call search_symbols with query "{query}" and no repo filter'))
def search_no_repo(query):
    _ctx["response"] = search_symbols_tool(query=query, repo=None)


@when(parsers.parse('I call search_symbols with repo "{repo}"'))
def search_bad_repo(repo):
    _ctx["response"] = search_symbols_tool(query="anything", repo=repo)


# ── Then steps ───────────────────────────────────────────────────────────────

@then(parsers.parse('the response contains "{repo_name}"'))
def response_contains_repo(repo_name):
    repos = _ctx["response"].get("repos", [])
    names = [r["name"] for r in repos]
    assert repo_name in names, f"{repo_name!r} not found in repos: {names}"


@then(parsers.parse('the response contains symbols from both "{alpha}" and "{beta}"'))
def symbols_from_both(alpha, beta):
    symbols = _ctx["response"].get("symbols", [])
    repos_found = {s.get("repo") for s in symbols}
    assert alpha in repos_found, f"{alpha!r} not in repos_found: {repos_found}"
    assert beta in repos_found, f"{beta!r} not in repos_found: {repos_found}"


@then('each symbol in the response includes a "repo" field')
def each_symbol_has_repo():
    symbols = _ctx["response"].get("symbols", [])
    assert symbols, "No symbols in response"
    for s in symbols:
        assert "repo" in s, f"Symbol missing 'repo' field: {s}"


@then(parsers.parse("the response is an error envelope with code {code:d}"))
def response_is_error(code):
    assert "error" in _ctx["response"], f"Expected error envelope, got: {_ctx['response']}"
    assert _ctx["response"]["error"]["code"] == code, (
        f"Expected code {code}, got {_ctx['response']['error']['code']}"
    )


@then(parsers.parse('the error key is "{key}"'))
def error_key_matches(key):
    assert _ctx["response"]["error"]["key"] == key, (
        f"Expected key {key!r}, got {_ctx['response']['error']['key']!r}"
    )
