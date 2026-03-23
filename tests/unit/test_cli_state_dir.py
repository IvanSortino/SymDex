import json
import os

from typer.testing import CliRunner

from symdex.cli import app


runner = CliRunner()


def test_cli_state_dir_indexes_into_workspace_local_state(tmp_path, monkeypatch):
    monkeypatch.setenv("SYMDEX_DISABLE_UPDATE_CHECK", "1")
    workspace = tmp_path / "workspace"
    src = workspace / "src"
    workspace.mkdir()
    src.mkdir()
    monkeypatch.chdir(workspace)
    (src / "module.py").write_text("def hello():\n    return 1\n", encoding="utf-8")

    result = runner.invoke(app, ["--state-dir", ".symdex", "index", str(src), "--repo", "src"])

    assert result.exit_code == 0, result.output
    assert (workspace / ".symdex" / "src.db").exists()
    manifest = json.loads((workspace / ".symdex" / "registry.json").read_text(encoding="utf-8"))
    assert manifest[0]["root_path"] == "./src"
    assert manifest[0]["db_path"] == "./.symdex/src.db"


def test_cli_repos_auto_discovers_existing_local_state(tmp_path, monkeypatch):
    monkeypatch.setenv("SYMDEX_DISABLE_UPDATE_CHECK", "1")
    workspace = tmp_path / "workspace"
    src = workspace / "src"
    workspace.mkdir()
    src.mkdir()
    monkeypatch.chdir(workspace)
    (src / "module.py").write_text("def hello():\n    return 1\n", encoding="utf-8")

    indexed = runner.invoke(app, ["--state-dir", ".symdex", "index", str(src), "--repo", "src"])
    assert indexed.exit_code == 0, indexed.output

    repos = runner.invoke(app, ["repos", "--json"])
    assert repos.exit_code == 0, repos.output
    payload = json.loads(repos.output)
    assert payload["registry_json"].endswith(os.path.join('.symdex', 'registry.json'))
    assert any(r["name"] == "src" for r in payload["repos"])
