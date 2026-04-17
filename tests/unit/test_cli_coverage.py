# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.
#
# Targeted coverage tests for symdex/cli.py.
# Covers branches not reached by the BDD feature tests.

import json
import os
import importlib.metadata
import pytest
import sys
from typer.testing import CliRunner
from symdex.cli import app
from symdex.core.naming import derive_repo_name

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

    monkeypatch.setenv("SYMDEX_DISABLE_UPDATE_CHECK", "1")


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
    result = runner.invoke(app, ["index", str(src), "--repo", "cov_repo"])
    assert result.exit_code == 0, f"index failed: {result.output}"
    return {"path": str(src), "repo": "cov_repo"}


# ── index command ─────────────────────────────────────────────────────────────

def test_index_bad_path_exits_1():
    result = runner.invoke(app, ["index", "/nonexistent/path/xyz"])
    assert result.exit_code == 1
    assert "Error" in result.output or "Error" in (result.stderr or "")


def test_index_success_shows_stats(indexed_dir):
    # Already indexed in fixture; index again to confirm output
    result = runner.invoke(app, ["index", indexed_dir["path"], "--repo", "cov_repo"])
    assert result.exit_code == 0
    # Table should contain the repo name
    assert "cov_repo" in result.output
    assert "Lines of Code" in result.output
    assert "Functions" in result.output


# ── search command ─────────────────────────────────────────────────────────────

def test_search_found_table_output(indexed_dir):
    result = runner.invoke(app, ["search", "alpha", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 0
    assert "alpha" in result.output.lower()
    assert "SymDex token savings:" in result.output


def test_normal_command_prints_update_notice_when_newer_release_exists(indexed_dir, monkeypatch):
    monkeypatch.delenv("SYMDEX_DISABLE_UPDATE_CHECK", raising=False)
    monkeypatch.setattr("symdex.cli._stdout_is_terminal", lambda: True)
    monkeypatch.setattr(
        "symdex.cli.get_update_notice",
        lambda argv=None: {
            "installed_version": "0.1.15",
            "latest_version": "0.1.16",
            "pip_command": "py -m pip install -U symdex",
            "uv_tool_command": "uv tool upgrade symdex",
            "uvx_command": "uvx symdex@latest repos",
        },
    )
    monkeypatch.setattr("symdex.cli._UPDATE_NOTICE_EMITTED", False)

    result = runner.invoke(app, ["repos"])

    assert result.exit_code == 0
    assert "Update available: SymDex 0.1.16" in result.output
    assert "py -m pip install -U symdex" in result.output
    assert "uv tool upgrade symdex" in result.output
    assert "uvx symdex@latest repos" in result.output


def test_json_output_suppresses_update_notice(indexed_dir, monkeypatch):
    monkeypatch.delenv("SYMDEX_DISABLE_UPDATE_CHECK", raising=False)
    monkeypatch.setattr("symdex.cli._stdout_is_terminal", lambda: True)
    monkeypatch.setattr(
        "symdex.cli.get_update_notice",
        lambda argv=None: pytest.fail("update notice should be skipped for --json"),
    )
    monkeypatch.setattr("symdex.cli._UPDATE_NOTICE_EMITTED", False)

    result = runner.invoke(app, ["repos", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "repos" in data


def test_search_found_json_output(indexed_dir):
    result = runner.invoke(app, ["search", "alpha", "--repo", indexed_dir["repo"], "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "symbols" in data
    assert "roi" in data
    assert "roi_summary" in data
    assert "roi_agent_hint" in data
    assert "token savings" in data["roi_summary"].lower()
    assert "mention" in data["roi_agent_hint"].lower()


def test_search_not_found_exits_1(indexed_dir):
    result = runner.invoke(app, ["search", "zzz_nonexistent_xyz", "--repo", indexed_dir["repo"]])
    assert result.exit_code == 1


def test_search_across_repos_no_repo(indexed_dir):
    # Omit --repo → triggers search_across_repos path
    result = runner.invoke(app, ["search", "alpha"])
    # May succeed (finds in registered repo) or exit 1 if nothing found; either is valid
    assert result.exit_code in (0, 1)


def test_index_auto_names_repo(tmp_path):
    src = tmp_path / "autoindex"
    src.mkdir()
    (src / "module.py").write_text("def auto_name():\n    return 1\n")
    expected = derive_repo_name(str(src))
    result = runner.invoke(app, ["index", str(src)])
    assert result.exit_code == 0
    assert expected in result.output


def test_index_name_alias_still_works(tmp_path):
    src = tmp_path / "legacyindex"
    src.mkdir()
    (src / "module.py").write_text("def legacy_name():\n    return 1\n")
    result = runner.invoke(app, ["index", str(src), "--name", "legacy_repo"])
    assert result.exit_code == 0
    assert "legacy_repo" in result.output


def test_index_accepts_state_dir_after_subcommand(tmp_path):
    src = tmp_path / "stateafterindex"
    src.mkdir()
    (src / "module.py").write_text("def state_after_index():\n    return 1\n")
    result = runner.invoke(app, ["index", str(src), "--repo", "state_repo", "--state-dir", ".symdex"])
    assert result.exit_code == 0
    assert os.environ.get("SYMDEX_STATE_DIR") == ".symdex"


def test_index_folder_alias_works(tmp_path):
    src = tmp_path / "aliasindex"
    src.mkdir()
    (src / "module.py").write_text("def alias_index():\n    return 1\n")
    result = runner.invoke(app, ["index-folder", str(src), "--repo", "alias_repo"])
    assert result.exit_code == 0
    assert "alias_repo" in result.output


def test_index_help_shows_state_dir():
    result = runner.invoke(app, ["index", "--help"])
    assert result.exit_code == 0
    assert "--state-dir" in result.output


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
    assert "SymDex token savings:" in result.output


def test_text_found_json(indexed_dir):
    result = runner.invoke(app, ["text", "alpha", "--repo", indexed_dir["repo"], "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "matches" in data
    assert "roi" in data
    assert "roi_summary" in data
    assert "roi_agent_hint" in data
    assert "token savings" in data["roi_summary"].lower()
    assert "mention" in data["roi_agent_hint"].lower()


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


def test_repos_accepts_state_dir_after_subcommand(indexed_dir):
    result = runner.invoke(app, ["repos", "--state-dir", ".symdex"])
    assert result.exit_code == 0
    assert "cov_repo" in result.output


def test_list_repos_alias_works(indexed_dir):
    result = runner.invoke(app, ["list-repos"])
    assert result.exit_code == 0
    assert "cov_repo" in result.output


def test_repos_help_shows_state_dir():
    result = runner.invoke(app, ["repos", "--help"])
    assert result.exit_code == 0
    assert "--state-dir" in result.output


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


def test_semantic_repo_not_indexed_exits_1():
    result = runner.invoke(app, ["semantic", "some query", "--repo", "missing_repo"])
    assert result.exit_code == 1
    assert "Repo not indexed: missing_repo" in result.output


def test_semantic_missing_local_extra_exits_1(indexed_dir, monkeypatch):
    monkeypatch.delenv("SYMDEX_EMBED_BACKEND", raising=False)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    result = runner.invoke(app, ["semantic", "some query", "--repo", indexed_dir["repo"]])

    assert result.exit_code == 1
    assert 'symdex[local]' in result.output


def test_semantic_no_embeddings_gives_actionable_error(indexed_dir, monkeypatch):
    monkeypatch.setattr("symdex.cli._repo_has_semantic_embeddings", lambda conn, repo: False)

    result = runner.invoke(app, ["semantic", "some query", "--repo", indexed_dir["repo"]])

    assert result.exit_code == 1
    assert "Repo has no semantic embeddings" in result.output
    assert "symdex[local]" in result.output


def test_version_flag_prints_package_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert importlib.metadata.version("symdex") in result.output


def test_root_help_shows_version():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--version" in result.output
