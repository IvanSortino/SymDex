# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import json

from typer.testing import CliRunner

from symdex.cli import app
from symdex.core.indexer import index_folder
from symdex.core.storage import upsert_repo


def _index_quality_repo(tmp_path, monkeypatch, repo: str = "quality_repo") -> str:
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(tmp_path / ".symdex"))
    src = tmp_path / "repo"
    src.mkdir()
    (src / "mod.py").write_text(
        "def alpha():\n"
        "    return 'needle'\n\n"
        "def beta():\n"
        "    return alpha()\n",
        encoding="utf-8",
    )
    result = index_folder(str(src), repo=repo, embed=False)
    upsert_repo(result.repo, root_path=str(src), db_path=result.db_path)
    return repo


def test_cli_search_json_includes_quality(tmp_path, monkeypatch):
    repo = _index_quality_repo(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["search", "alpha", "--repo", repo, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["symbols"][0]["quality"]["confidence"] == 0.92
    assert payload["symbols"][0]["quality"]["index_fresh"] in (True, False)


def test_cli_find_json_includes_quality(tmp_path, monkeypatch):
    repo = _index_quality_repo(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["find", "alpha", "--repo", repo, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["symbols"][0]["quality"]["confidence"] == 0.92


def test_cli_outline_json_includes_quality(tmp_path, monkeypatch):
    repo = _index_quality_repo(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["outline", "mod.py", "--repo", repo, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["symbols"][0]["quality"]["confidence"] == 0.90


def test_cli_text_json_includes_quality(tmp_path, monkeypatch):
    repo = _index_quality_repo(tmp_path, monkeypatch)

    result = CliRunner().invoke(app, ["text", "needle", "--repo", repo, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["matches"][0]["quality"]["confidence"] == 0.70


def test_cli_semantic_json_includes_quality(tmp_path, monkeypatch):
    repo = _index_quality_repo(tmp_path, monkeypatch)

    monkeypatch.setattr("symdex.cli._repo_has_semantic_embeddings", lambda conn, repo: True)
    monkeypatch.setattr(
        "symdex.cli._search_semantic",
        lambda conn, query, repo, limit, progress_callback=None: [
            {
                "name": "alpha",
                "file": "mod.py",
                "kind": "function",
                "start_byte": 0,
                "end_byte": 20,
                "score": 0.76,
            }
        ],
    )

    result = CliRunner().invoke(app, ["semantic", "alpha function", "--repo", repo, "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["symbols"][0]["quality"]["confidence"] == 0.76
    assert (
        payload["symbols"][0]["quality"]["confidence_reason"]
        == "semantic embedding similarity"
    )
