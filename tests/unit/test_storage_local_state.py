import json
import os

from symdex.core.storage import get_db_path, query_repos, remove_repo, upsert_repo


def test_local_state_manifest_uses_relative_paths(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = workspace / "src"
    root.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(workspace / ".symdex"))

    db_path = get_db_path("src")
    upsert_repo("src", root_path=str(root), db_path=db_path)

    repos = query_repos()
    assert repos[0]["root_path"] == str(root)
    assert repos[0]["db_path"] == db_path

    manifest = json.loads((workspace / ".symdex" / "registry.json").read_text(encoding="utf-8"))
    assert manifest[0]["root_path"] == "./src"
    assert manifest[0]["db_path"] == "./.symdex/src.db"
    assert len(manifest[0]["last_indexed"]) == 19


def test_remove_repo_deletes_local_db_and_updates_manifest(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = workspace / "src"
    root.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(workspace / ".symdex"))

    db_path = get_db_path("src")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    open(db_path, "w", encoding="utf-8").close()
    upsert_repo("src", root_path=str(root), db_path=db_path)

    remove_repo("src")

    assert not os.path.exists(db_path)
    manifest = json.loads((workspace / ".symdex" / "registry.json").read_text(encoding="utf-8"))
    assert manifest == []
