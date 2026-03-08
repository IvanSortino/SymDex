# tests/features/steps/callgraph_steps.py
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import os
import tempfile

import numpy as np
from unittest.mock import patch
from pytest_bdd import given, when, then, scenarios, parsers

from symdex.mcp.tools import index_folder_tool, get_callers_tool, get_callees_tool

scenarios("../call_graph.feature")

FAKE_VEC = np.array([1.0] + [0.0] * 383, dtype="float32")

_ctx: dict = {}

CALLER_CALLEE_SRC = """\
def callee_func():
    pass

def caller_func():
    callee_func()
"""

EXTERNAL_CALLER_SRC = """\
import os

def external_caller():
    os.path.join("a", "b")
"""


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_db_patcher(tmp_dir: str):
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


# ── Background ─────────────────────────────────────────────────────────────────

@given('a Python file where "caller_func" calls "callee_func" has been indexed')
def background_cg(monkeypatch):
    _ctx.clear()
    tmp_dir = tempfile.mkdtemp()
    mock_db_path, mock_registry_path = _make_db_patcher(tmp_dir)
    _patch_all(monkeypatch, mock_db_path, mock_registry_path)
    src = os.path.join(tmp_dir, "module.py")
    open(src, "w").write(CALLER_CALLEE_SRC)
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        index_folder_tool(path=tmp_dir, name="cg_test")
    _ctx.update({"repo": "cg_test", "tmp_dir": tmp_dir, "mock_db_path": mock_db_path})


# ── Scenario: Unresolved external call has null file ───────────────────────────

@given("a Python file that calls an external library function has been indexed")
def external_call_indexed(monkeypatch):
    # Background already ran and created cg_test. Now create a separate repo
    # for the external-call scenario.
    tmp_dir = tempfile.mkdtemp()
    mock_db_path, mock_registry_path = _make_db_patcher(tmp_dir)
    _patch_all(monkeypatch, mock_db_path, mock_registry_path)
    src = os.path.join(tmp_dir, "ext_module.py")
    open(src, "w").write(EXTERNAL_CALLER_SRC)
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        index_folder_tool(path=tmp_dir, name="cg_external")
    _ctx["mock_db_path"] = mock_db_path


# ── Scenario: Re-indexing does not duplicate edges ─────────────────────────────

@given("the call graph repo has been indexed once")
def cg_dedup_indexed(monkeypatch):
    # Background already ran and created cg_test. Now create a separate repo
    # for the dedup scenario.
    tmp_dir = tempfile.mkdtemp()
    mock_db_path, mock_registry_path = _make_db_patcher(tmp_dir)
    _patch_all(monkeypatch, mock_db_path, mock_registry_path)
    src = os.path.join(tmp_dir, "module.py")
    open(src, "w").write(CALLER_CALLEE_SRC)
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        index_folder_tool(path=tmp_dir, name="cg_dedup")
    _ctx.update({"dedup_tmp": tmp_dir, "mock_db_path": mock_db_path})


# ── When steps ─────────────────────────────────────────────────────────────────

@when(parsers.parse('I call get_callers with name "{name}" and repo "{repo}"'))
def call_get_callers(name, repo):
    _ctx["result"] = get_callers_tool(name=name, repo=repo)


@when(parsers.parse('I call get_callees with name "{name}" and repo "{repo}"'))
def call_get_callees(name, repo):
    _ctx["result"] = get_callees_tool(name=name, repo=repo)


@when("I index the same folder again without changes")
def reindex_same():
    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        index_folder_tool(path=_ctx["dedup_tmp"], name="cg_dedup")


# ── Then steps ─────────────────────────────────────────────────────────────────

@then(parsers.parse('the response contains a "{key}" list'))
def response_contains_list(key):
    assert key in _ctx["result"], f"Missing '{key}' in {_ctx['result']}"
    assert isinstance(_ctx["result"][key], list)


@then(parsers.parse('the callers list includes a symbol named "{name}"'))
def callers_includes(name):
    names = [s["name"] for s in _ctx["result"]["callers"]]
    assert name in names, f"{name} not in callers: {names}"


@then(parsers.parse('the callees list includes an entry with name "{name}"'))
def callees_includes(name):
    names = [s["name"] for s in _ctx["result"]["callees"]]
    assert name in names, f"{name} not in callees: {names}"


@then("the callees list contains an entry where callee_file is null")
def callees_has_null_file():
    callees = _ctx["result"]["callees"]
    assert any(c["file"] is None for c in callees), (
        f"No null callee_file in {callees}"
    )


@then(parsers.parse('the callees list contains "{name}" exactly once'))
def callees_exactly_once(name):
    callees = _ctx["result"]["callees"]
    count = sum(1 for c in callees if c["name"] == name)
    assert count == 1, f"Expected '{name}' exactly once, got {count}: {callees}"
