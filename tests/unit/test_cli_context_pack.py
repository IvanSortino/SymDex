# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import json

from typer.testing import CliRunner

from symdex.cli import app
from symdex.core.indexer import index_folder
from symdex.core.storage import upsert_repo


def index_pack_fixture(tmp_path, monkeypatch) -> str:
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(tmp_path / ".symdex"))
    monkeypatch.setenv("SYMDEX_DISABLE_UPDATE_CHECK", "1")
    src = tmp_path / "clipackrepo"
    src.mkdir()
    (src / "app.py").write_text(
        "def create_checkout():\n"
        "    return 'checkout'\n\n"
        "@app.get('/checkout')\n"
        "def checkout_route():\n"
        "    return create_checkout()\n",
        encoding="utf-8",
    )
    result = index_folder(str(src), repo="cli_pack_repo", embed=False)
    upsert_repo(result.repo, root_path=str(src), db_path=result.db_path)
    return result.repo


def test_cli_pack_json_outputs_context_pack(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    result = CliRunner().invoke(
        app,
        ["pack", "checkout", "--repo", repo, "--budget", "800", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["query"] == "checkout"
    assert payload["selected_evidence"]


def test_cli_pack_text_outputs_sections(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    result = CliRunner().invoke(
        app,
        ["pack", "checkout", "--repo", repo, "--budget", "800"],
    )

    assert result.exit_code == 0
    assert "Context Pack" in result.output
    assert "Selected Evidence" in result.output


def test_cli_pack_rejects_unknown_format(tmp_path, monkeypatch):
    repo = index_pack_fixture(tmp_path, monkeypatch)

    result = CliRunner().invoke(
        app,
        ["pack", "checkout", "--repo", repo, "--format", "xml"],
    )

    assert result.exit_code == 1
    assert "format must be 'text' or 'json'" in result.output
