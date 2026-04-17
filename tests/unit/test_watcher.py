# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from symdex.cli import app
from symdex.core.watcher import WatcherAlreadyRunningError, _should_skip, watch

FAKE_VEC = [0.1] * 384


def test_should_skip_git_dir():
    assert _should_skip(".git/config") is True


def test_should_skip_pycache():
    assert _should_skip("__pycache__/mod.pyc") is True


def test_should_skip_binary():
    assert _should_skip("image.png") is True


def test_should_not_skip_py():
    assert _should_skip("src/main.py") is False


def test_should_not_skip_js():
    assert _should_skip("app/index.js") is False


def _make_db_path_factory(state_dir: Path):
    """Return a get_db_path function that stores DBs under state_dir."""
    state_dir.mkdir(parents=True, exist_ok=True)

    def _mock_get_db_path(repo_name: str) -> str:
        return str(state_dir / f"{repo_name}.db")

    return _mock_get_db_path


def _watch_pid_file(pid_dir: Path, repo: str) -> Path:
    return pid_dir / f"{repo}.watch.pid"


class _FakeObserver:
    def schedule(self, handler, path, recursive=True):
        self.handler = handler
        self.path = path
        self.recursive = recursive

    def start(self):
        return None

    def stop(self):
        return None

    def join(self):
        return None


def test_watch_default_passes_embed_false(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    pid_dir = tmp_path / "pids"
    stop = threading.Event()
    stop.set()

    with patch("symdex.core.watcher.index_folder") as mock_index, \
         patch("symdex.core.watcher.Observer", return_value=_FakeObserver()), \
         patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir):
        watch(str(repo_dir), repo="watch_embed_default", stop_event=stop)

    mock_index.assert_called_once()
    assert mock_index.call_args.kwargs["embed"] is False


def test_watch_embed_true_passes_through(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    pid_dir = tmp_path / "pids"
    stop = threading.Event()
    stop.set()

    with patch("symdex.core.watcher.index_folder") as mock_index, \
         patch("symdex.core.watcher.Observer", return_value=_FakeObserver()), \
         patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir):
        watch(str(repo_dir), repo="watch_embed_true", embed=True, stop_event=stop)

    mock_index.assert_called_once()
    assert mock_index.call_args.kwargs["embed"] is True


def test_watch_reindexes_new_file(tmp_path):
    """watch() should pick up a new file written after start."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("def hello(): pass\n")

    mock_db_path = _make_db_path_factory(tmp_path / "state")
    pid_dir = tmp_path / "pids"
    stop = threading.Event()

    def run():
        with patch("symdex.core.indexer.get_db_path", side_effect=mock_db_path), \
             patch("symdex.core.storage.get_db_path", side_effect=mock_db_path), \
             patch("symdex.core.watcher.get_db_path", side_effect=mock_db_path), \
             patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir):
            watch(str(repo_dir), repo="test_watch", interval=0.5, stop_event=stop)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(1.5)

    (repo_dir / "new_file.py").write_text("def new_func(): pass\n")
    time.sleep(1.5)

    stop.set()
    t.join(timeout=5)

    from symdex.core.storage import get_connection

    conn = get_connection(mock_db_path("test_watch"))
    rows = conn.execute(
        "SELECT name FROM symbols WHERE repo='test_watch' AND name='new_func'"
    ).fetchall()
    conn.close()
    assert len(rows) == 1


def test_watch_removes_deleted_file(tmp_path):
    """watch() should remove symbols for deleted files from the index."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "main.py").write_text("def hello(): pass\n")
    to_delete = repo_dir / "old.py"
    to_delete.write_text("def goodbye(): pass\n")

    mock_db_path = _make_db_path_factory(tmp_path / "state")
    pid_dir = tmp_path / "pids"
    stop = threading.Event()

    def run():
        with patch("symdex.core.indexer.get_db_path", side_effect=mock_db_path), \
             patch("symdex.core.storage.get_db_path", side_effect=mock_db_path), \
             patch("symdex.core.watcher.get_db_path", side_effect=mock_db_path), \
             patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir):
            watch(str(repo_dir), repo="test_watch_del", interval=0.5, stop_event=stop)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(1.5)

    to_delete.unlink()
    time.sleep(1.5)

    stop.set()
    t.join(timeout=5)

    from symdex.core.storage import get_connection

    conn = get_connection(mock_db_path("test_watch_del"))
    rows = conn.execute(
        "SELECT name FROM symbols WHERE repo='test_watch_del' AND name='goodbye'"
    ).fetchall()
    conn.close()
    assert len(rows) == 0


def test_duplicate_live_watcher_is_rejected(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    pid_dir = tmp_path / "pids"
    stop = threading.Event()
    pid_file = _watch_pid_file(pid_dir, "dup_watch")

    def run():
        with patch("symdex.core.watcher.index_folder"), \
             patch("symdex.core.watcher.Observer", return_value=_FakeObserver()), \
             patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir):
            watch(str(repo_dir), repo="dup_watch", interval=0.05, stop_event=stop)

    t = threading.Thread(target=run, daemon=True)
    t.start()

    for _ in range(100):
        if pid_file.exists():
            break
        time.sleep(0.02)
    assert pid_file.exists()

    with patch("symdex.core.watcher.index_folder"), \
         patch("symdex.core.watcher.Observer", return_value=_FakeObserver()), \
         patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir):
        with pytest.raises(WatcherAlreadyRunningError):
            watch(str(repo_dir), repo="dup_watch", interval=0.05, stop_event=threading.Event())

    stop.set()
    t.join(timeout=5)
    assert not t.is_alive()


def test_live_same_repo_different_root_is_rejected(tmp_path):
    repo_dir = tmp_path / "repo"
    other_root = tmp_path / "other"
    repo_dir.mkdir()
    other_root.mkdir()
    pid_dir = tmp_path / "pids"
    pid_dir.mkdir()
    pid_file = _watch_pid_file(pid_dir, "same_repo")
    pid_file.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "repo": "same_repo",
                "root": os.path.normcase(os.path.abspath(str(other_root))),
                "started_at": 1.0,
            }
        ),
        encoding="utf-8",
    )

    with patch("symdex.core.watcher.index_folder"), \
         patch("symdex.core.watcher.Observer", return_value=_FakeObserver()), \
         patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir), \
         patch("symdex.core.watcher._process_is_alive", return_value=True):
        with pytest.raises(WatcherAlreadyRunningError):
            watch(str(repo_dir), repo="same_repo", interval=0.05, stop_event=threading.Event())


def test_stale_pid_file_is_replaced(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    pid_dir = tmp_path / "pids"
    pid_dir.mkdir()
    pid_file = _watch_pid_file(pid_dir, "stale_watch")
    pid_file.write_text(
        json.dumps(
            {
                "pid": 99999999,
                "repo": "stale_watch",
                "root": os.path.normcase(os.path.abspath(str(repo_dir))),
                "started_at": 1.0,
            }
        ),
        encoding="utf-8",
    )
    stop = threading.Event()

    def run():
        with patch("symdex.core.watcher.index_folder"), \
             patch("symdex.core.watcher.Observer", return_value=_FakeObserver()), \
             patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir), \
             patch("symdex.core.watcher._process_is_alive", return_value=False):
            watch(str(repo_dir), repo="stale_watch", interval=0.05, stop_event=stop)

    t = threading.Thread(target=run, daemon=True)
    t.start()

    metadata = None
    for _ in range(100):
        if not pid_file.exists():
            time.sleep(0.02)
            continue
        metadata = json.loads(pid_file.read_text(encoding="utf-8"))
        if metadata.get("pid") == os.getpid():
            break
        time.sleep(0.02)
    assert metadata is not None
    assert metadata["pid"] == os.getpid()
    assert metadata["repo"] == "stale_watch"
    assert metadata["root"] == os.path.normcase(os.path.abspath(str(repo_dir)))
    assert isinstance(metadata["started_at"], (int, float))

    stop.set()
    t.join(timeout=5)
    assert not t.is_alive()


def test_watch_idle_timeout_exits(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    pid_dir = tmp_path / "pids"

    with patch("symdex.core.watcher.index_folder"), \
         patch("symdex.core.watcher.Observer", return_value=_FakeObserver()), \
         patch("symdex.core.watcher._watch_pid_dir", return_value=pid_dir):
        watch(str(repo_dir), repo="idle_watch", interval=0.01, idle_timeout=0.02)

    assert not _watch_pid_file(pid_dir, "idle_watch").exists()


def test_watch_cli_help():
    runner = CliRunner()
    result = runner.invoke(app, ["watch", "--help"])
    assert result.exit_code == 0
    assert "--interval" in result.output
    assert "--embed" in result.output
    assert "--idle-timeout" in result.output
    assert "--forever" in result.output


def test_watch_cli_duplicate_watcher_exits_cleanly(monkeypatch):
    runner = CliRunner()

    def _raise_duplicate(*args, **kwargs):
        raise WatcherAlreadyRunningError("watcher already running for repo='dup'")

    monkeypatch.setattr("symdex.cli._watch_repo", _raise_duplicate)

    result = runner.invoke(app, ["watch", ".", "--repo", "dup"])

    assert result.exit_code == 0
    assert "watcher already running" in result.output
