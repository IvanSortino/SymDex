# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

"""Background file-system watcher that keeps the SymDex index up to date."""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from symdex.core.naming import derive_repo_name
from symdex.core.indexer import index_folder, _SKIP_DIRS, _SKIP_EXTENSIONS
from symdex.core.storage import get_db_path, get_connection
from symdex.core.state import WATCH_PID_SUFFIX, get_watch_pid_dir

logger = logging.getLogger(__name__)

_SKIP_DIR_PARTS = _SKIP_DIRS
_WATCHER_METADATA_SUFFIX = WATCH_PID_SUFFIX


class WatcherAlreadyRunningError(RuntimeError):
    """Raised when a live watcher already exists for the same repo/root."""


def _should_skip(path: str) -> bool:
    """Return True if this path should never be indexed."""
    parts = path.replace("\\", "/").split("/")
    for part in parts[:-1]:  # directories in the path
        if part in _SKIP_DIR_PARTS:
            return True
    ext = os.path.splitext(path)[1].lower()
    return ext in _SKIP_EXTENSIONS


def _watch_root(path: str) -> str:
    """Return a normalized absolute path used for watcher identity checks."""
    return os.path.normcase(os.path.abspath(path))


def _watch_pid_dir() -> Path:
    """Return the directory that stores watcher metadata files."""
    return Path(get_watch_pid_dir())


def _watch_pid_file(repo: str) -> Path:
    """Return the watcher metadata file for a repo."""
    return _watch_pid_dir() / f"{repo}{_WATCHER_METADATA_SUFFIX}"


def _process_is_alive(pid: int) -> bool:
    """Return True when *pid* still points at a live process."""
    if pid <= 0:
        return False

    if os.name == "nt":
        try:
            import ctypes
        except Exception:  # noqa: BLE001
            return False

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, int(pid))
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return ctypes.get_last_error() == 5

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _load_watch_metadata(pid_file: Path) -> Optional[dict[str, object]]:
    """Load watcher metadata from *pid_file*.

    Older SymDex releases wrote a plain pid string. Treat that as live metadata
    without a root so a new watcher does not silently duplicate an old one.
    """
    try:
        raw = pid_file.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            pid = int(raw.strip())
        except ValueError:
            return None
        repo = pid_file.name.removesuffix(_WATCHER_METADATA_SUFFIX)
        return {"pid": pid, "repo": repo, "root": None, "legacy": True}

    if not isinstance(data, dict):
        return None

    return data


def _metadata_identity(metadata: dict[str, object]) -> tuple[int, str, str | None] | None:
    """Extract the pid/repo/root identity from a metadata mapping."""
    try:
        pid = int(metadata["pid"])
        repo = str(metadata["repo"])
        raw_root = metadata.get("root")
        root = _watch_root(str(raw_root)) if raw_root else None
    except (KeyError, TypeError, ValueError):
        return None
    return pid, repo, root


def _metadata_matches(metadata: dict[str, object], pid: int, repo: str, root: str) -> bool:
    """Return True when the metadata belongs to the current watcher."""
    identity = _metadata_identity(metadata)
    if identity is None:
        return False
    existing_pid, existing_repo, existing_root = identity
    return (
        existing_pid == pid
        and existing_repo == repo
        and existing_root is not None
        and existing_root == root
    )


def _metadata_is_live_same_repo(metadata: dict[str, object], repo: str) -> bool:
    """Return True when *metadata* belongs to a live watcher for this repo."""
    identity = _metadata_identity(metadata)
    if identity is None:
        return False
    pid, existing_repo, _ = identity
    return existing_repo == repo and _process_is_alive(pid)


def _write_watch_metadata(pid_file: Path, metadata: dict[str, object]) -> None:
    """Atomically write watcher metadata, failing if the file already exists."""
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(metadata, sort_keys=True)
    fd = os.open(str(pid_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            pid_file.unlink()
        except OSError:
            pass
        raise


def _claim_watch_pid_file(pid_file: Path, repo: str, root: str) -> dict[str, object]:
    """Create the watcher metadata file or replace stale/corrupt entries."""
    metadata = {
        "pid": os.getpid(),
        "repo": repo,
        "root": root,
        "started_at": time.time(),
    }

    while True:
        try:
            _write_watch_metadata(pid_file, metadata)
            return metadata
        except FileExistsError:
            existing = _load_watch_metadata(pid_file)
            if existing and _metadata_is_live_same_repo(existing, repo):
                existing_pid, _, existing_root = _metadata_identity(existing) or (None, None, None)
                root_detail = f" root={existing_root!r}" if existing_root else ""
                raise WatcherAlreadyRunningError(
                    f"watcher already running for repo={repo!r}{root_detail} "
                    f"(pid={existing_pid})"
                )

            try:
                pid_file.unlink()
            except OSError:
                pass
            continue


def _cleanup_watch_pid_file(pid_file: Path, metadata: dict[str, object]) -> None:
    """Remove the watcher metadata file only if it still belongs to us."""
    current = _load_watch_metadata(pid_file)
    if current is None:
        return

    pid = os.getpid()
    repo = str(metadata.get("repo", ""))
    root = str(metadata.get("root", ""))
    if _metadata_matches(current, pid, repo, _watch_root(root)):
        try:
            pid_file.unlink()
            logger.info("Deleted watcher pid file: %s", pid_file)
        except OSError as e:
            logger.warning("Failed to delete pid file: %s", e)


def _remove_file_from_index(repo: str, rel_path: str) -> None:
    """Delete all symbols and file hash record for a deleted file."""
    db_path = get_db_path(repo)
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM symbols WHERE repo=? AND file=?", (repo, rel_path))
        conn.execute("DELETE FROM files WHERE repo=? AND path=?", (repo, rel_path))
        conn.commit()
        logger.info("Removed deleted file from index: %s", rel_path)
    finally:
        conn.close()


class _Handler(FileSystemEventHandler):
    def __init__(self, root: str, repo: str) -> None:
        self._root = root
        self._repo = repo
        self._lock = threading.Lock()
        self._changed: set[str] = set()
        self._deleted: set[str] = set()

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue(event.src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue(event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            rel = os.path.relpath(event.src_path, self._root).replace("\\", "/")
            with self._lock:
                self._deleted.add(rel)

    def _queue(self, abs_path: str) -> None:
        if _should_skip(abs_path):
            return
        with self._lock:
            self._changed.add(abs_path)

    def flush(self) -> tuple[set[str], set[str]]:
        with self._lock:
            changed, deleted = self._changed.copy(), self._deleted.copy()
            self._changed.clear()
            self._deleted.clear()
        return changed, deleted


def watch(
    path: str,
    repo: Optional[str] = None,
    name: Optional[str] = None,
    interval: float = 5.0,
    embed: bool = False,
    idle_timeout: Optional[float] = None,
    stop_event: Optional[threading.Event] = None,
) -> None:
    """Watch *path* and keep its SymDex index up to date.

    Performs an initial full index, then re-indexes changed files and
    removes deleted files every *interval* seconds.

    Args:
        path: Absolute or relative path to the directory to watch.
        repo: Repo name override. When omitted, a stable repo name is derived
            from the folder name, git branch (if available), and path hash.
        name: Backward-compatible alias for repo.
        interval: Seconds between flush cycles.
        embed: Whether to build semantic embeddings while indexing.
        idle_timeout: Optional idle shutdown timeout in seconds.
        stop_event: Optional threading.Event to signal shutdown.
    """
    abs_path = os.path.abspath(path)
    repo = derive_repo_name(abs_path, repo=repo, name=name)
    root = _watch_root(abs_path)

    pid_file = _watch_pid_file(repo)
    watch_metadata = _claim_watch_pid_file(pid_file, repo, root)
    logger.info("Created watcher pid file: %s", pid_file)

    logger.info("Initial index of %s ...", abs_path)
    index_folder(abs_path, repo=repo, embed=embed)

    handler = _Handler(abs_path, repo)
    observer = Observer()
    observer_started = False
    observer.schedule(handler, abs_path, recursive=True)
    observer.start()
    observer_started = True
    logger.info("Watching %s (repo=%s, interval=%.1fs)", abs_path, repo, interval)

    last_activity = time.monotonic()
    try:
        while stop_event is None or not stop_event.is_set():
            time.sleep(interval)
            changed, deleted = handler.flush()
            now = time.monotonic()

            for rel in deleted:
                _remove_file_from_index(repo, rel)

            if changed or deleted:
                last_activity = now

            if changed:
                logger.info("Re-indexing %d changed file(s) ...", len(changed))
                index_folder(abs_path, repo=repo, embed=embed)

            if idle_timeout is not None and idle_timeout > 0 and now - last_activity >= idle_timeout:
                logger.info(
                    "Watcher idle for %.1fs; shutting down %s (repo=%s)",
                    idle_timeout,
                    abs_path,
                    repo,
                )
                break

    finally:
        if observer_started:
            observer.stop()
            observer.join()
        _cleanup_watch_pid_file(pid_file, watch_metadata)
