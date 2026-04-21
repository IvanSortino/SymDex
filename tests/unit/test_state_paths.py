import json
import os

from symdex.core.state import (
    discover_local_state_dir,
    get_default_global_state_dir,
    get_state_paths,
    get_watch_pid_dir,
    get_watch_pid_path,
    resolve_registry_value,
    serialize_registry_value,
)


def test_get_state_paths_defaults_to_global(tmp_path, monkeypatch):
    monkeypatch.delenv("SYMDEX_STATE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("symdex.core.state.discover_local_state_dir", lambda start_path=None: None)

    state = get_state_paths()

    assert state.base_dir == os.path.normpath(get_default_global_state_dir())
    assert state.local_mode is False


def test_discover_local_state_dir_from_nested_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    nested = workspace / "a" / "b"
    state_dir = workspace / ".symdex"
    nested.mkdir(parents=True)
    state_dir.mkdir()
    monkeypatch.chdir(nested)
    monkeypatch.delenv("SYMDEX_STATE_DIR", raising=False)

    discovered = discover_local_state_dir()
    state = get_state_paths()

    assert os.path.normpath(discovered) == os.path.normpath(str(state_dir))
    assert os.path.normpath(state.base_dir) == os.path.normpath(str(state_dir))
    assert state.local_mode is True


def test_explicit_state_dir_env_wins_over_discovery(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    other = tmp_path / "override-state"
    (workspace / ".symdex").mkdir(parents=True)
    workspace.mkdir(exist_ok=True)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(other))

    state = get_state_paths()

    assert os.path.normpath(state.base_dir) == os.path.normpath(str(other))
    assert state.local_mode is True


def test_registry_value_round_trip_for_local_state(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(workspace / ".symdex"))

    state = get_state_paths()
    target = workspace / "src" / "module.py"
    target.parent.mkdir(parents=True)
    target.write_text("pass\n", encoding="utf-8")

    stored = serialize_registry_value(str(target), state)
    resolved = resolve_registry_value(stored, state)

    assert stored == "./src/module.py"
    assert os.path.normpath(resolved) == os.path.normpath(str(target))


def test_watch_pid_path_defaults_to_legacy_global_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("SYMDEX_STATE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("symdex.core.state.discover_local_state_dir", lambda start_path=None: None)

    expected_dir = os.path.join(os.path.expanduser("~"), ".symdex-mcp")

    assert os.path.normpath(get_watch_pid_dir()) == os.path.normpath(expected_dir)
    assert os.path.normpath(get_watch_pid_path("repo")) == os.path.normpath(
        os.path.join(expected_dir, "repo.watch.pid")
    )


def test_watch_pid_path_uses_local_state_dir(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    state_dir = workspace / ".symdex"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(state_dir))

    expected_dir = state_dir / "watchers"

    assert os.path.normpath(get_watch_pid_dir()) == os.path.normpath(str(expected_dir))
    assert os.path.normpath(get_watch_pid_path("repo")) == os.path.normpath(
        str(expected_dir / "repo.watch.pid")
    )
