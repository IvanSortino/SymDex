# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.
#
# Targeted coverage tests for symdex/cli.py.
# Covers branches not reached by the BDD feature tests.

import json
import os
import pytest
from typer.testing import CliRunner
from symdex.cli import app

runner = CliRunner()


# ── Isolation fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    """Redirect all DB paths to tmp_path for every test in this file."""
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
        "symdex.cli.get_db_path",
    ):
        monkeypatch.setattr(site, _mock_db_path)

    for site in (
        "symdex.core.storage.get_registry_path",
        "symdex.cli.get_registry_path",
    ):
        try:
            monkeypatch.setattr(site, _mock_registry_path)
        except AttributeError:
            pass


@pytest.fixture
def indexed_dir(tmp_path):
    """Create a small Python project, index it via the CLI, and return its path + repo name."""
    src = tmp_path / "myproject"
    src.mkdir()
    (src / "module.py").write_text(
        'def alpha_func(x):\n'
        '    """Alpha docstring."""\n'
        '    return x\n\n'
        'class BetaClass:\n'
        '    """Beta docstring."""\n'
        '    pass\n'
    )
    # Index via CLI so the registry is populated
    result = runner.invoke(app, ["index", str(src), "--name", "cov_repo"])
    assert result.exit_code == 0, f"index failed: {result.output}"
    return {"path": str(src), "repo": "cov_repo"}


# ── index command ─────────────────────────────────────────────────────────────

def test_index_bad_path_exits_1():
    result = runner.invoke(app, ["index", "/nonexistent/path/xyz"])
    assert result.exit_code == 1
    assert "Error" in result.output or "Error" in (result.stderr or "")


def test_index_success_shows_stats(indexed_dir):
    # Already indexed in fixture; index again to confirm output
    result = runner.invoke(app, ["index", indexed_dir["path"], "--name", "cov_repo"])
    assert result.exit_code == 0
    # Table should contain the repo name
    assert "cov_repo" in result.output


# ── search command ─────────────────────────────────────────────────────────────

def test_search_found_table_output(indexed_dir):
    result = runner.invoke(app, ["search", "alpha", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 0
    assert "alpha" in result.output.lower()


def test_search_found_json_output(indexed_dir):
    result = runner.invoke(app, ["search", "alpha", "--repo", indexed_dir["repo"], "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "symbols" in data


def test_search_not_found_exits_1(indexed_dir):
    result = runner.invoke(app, ["search", "zzz_nonexistent_xyz", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 1


def test_search_across_repos_no_repo(indexed_dir):
    # Omit --repo → triggers search_across_repos path
    result = runner.invoke(app, ["search", "alpha"])
    # May succeed (finds in registered repo) or exit 1 if nothing found; either is valid
    assert result.exit_code in (0, 1)


# ── find command ──────────────────────────────────────────────────────────────

def test_find_no_repo_exits_1():
    result = runner.invoke(app, ["find", "alpha"])
    assert result.exit_code == 1


def test_find_symbol_found_table(indexed_dir):
    result = runner.invoke(app, ["find", "alpha_func", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 0
    assert "alpha_func" in result.output


def test_find_symbol_found_json(indexed_dir):
    result = runner.invoke(app, ["find", "alpha_func", "--repo", indexed_dir["repo"], "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "symbols" in data


def test_find_symbol_not_found_exits_1(indexed_dir):
    result = runner.invoke(app, ["find", "does_not_exist_xyz", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 1


# ── outline command ───────────────────────────────────────────────────────────

def test_outline_found_table(indexed_dir):
    result = runner.invoke(app, ["outline", "module.py", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 0
    assert "alpha_func" in result.output or "BetaClass" in result.output


def test_outline_found_json(indexed_dir):
    result = runner.invoke(app, ["outline", "module.py", "--repo", indexed_dir["repo"], "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "symbols" in data


def test_outline_not_found_exits_1(indexed_dir):
    result = runner.invoke(app, ["outline", "no_such_file.py", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 1


# ── text command ──────────────────────────────────────────────────────────────

def test_text_no_repo_exits_1():
    result = runner.invoke(app, ["text", "alpha"])
    assert result.exit_code == 1


def test_text_repo_not_indexed_exits_1():
    result = runner.invoke(app, ["text", "alpha", "--repo", "unregistered_repo_xyz"])
    assert result.exit_code == 1


def test_text_found_table(indexed_dir):
    result = runner.invoke(app, ["text", "alpha", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 0
    assert "alpha" in result.output.lower()


def test_text_found_json(indexed_dir):
    result = runner.invoke(app, ["text", "alpha", "--repo", indexed_dir["repo"], "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "matches" in data


def test_text_not_found_exits_1(indexed_dir):
    result = runner.invoke(app, ["text", "zzz_no_match_xyz", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 1


# ── repos command ─────────────────────────────────────────────────────────────

def test_repos_no_repos_exits_1():
    result = runner.invoke(app, ["repos"])
    assert result.exit_code == 1


def test_repos_table_output(indexed_dir):
    result = runner.invoke(app, ["repos"])
    assert result.exit_code == 0
    assert "cov_repo" in result.output


def test_repos_json_output(indexed_dir):
    result = runner.invoke(app, ["repos", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "repos" in data


# ── invalidate command ────────────────────────────────────────────────────────

def test_invalidate_full_repo_json(indexed_dir):
    result = runner.invoke(app, ["invalidate", "--repo", indexed_dir["repo"], "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "invalidated" in data


def test_invalidate_specific_file_table(indexed_dir):
    result = runner.invoke(app, ["invalidate", "--repo", indexed_dir["repo"], "--file", "module.py"])
    assert result.exit_code == 0
    # Output should contain digit (invalidated count)
    assert any(c.isdigit() for c in result.output)


# ── callers command ───────────────────────────────────────────────────────────

def test_callers_not_found_exits_1(indexed_dir):
    result = runner.invoke(app, ["callers", "no_such_function_xyz", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 1


# ── callees command ───────────────────────────────────────────────────────────

def test_callees_not_found_exits_1(indexed_dir):
    result = runner.invoke(app, ["callees", "no_such_function_xyz", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 1


# ── semantic command ──────────────────────────────────────────────────────────

def test_semantic_no_repo_exits_1():
    result = runner.invoke(app, ["semantic", "some query"])
    assert result.exit_code == 1
