from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

LOCAL_STATE_DIRNAME = ".symdex"


@dataclass(frozen=True)
class StatePaths:
    base_dir: str
    registry_db_path: str
    registry_json_path: str
    workspace_root: str
    local_mode: bool


def get_default_global_state_dir() -> str:
    return os.path.join(os.path.expanduser("~"), LOCAL_STATE_DIRNAME)


def _normalize_state_dir(path: str) -> str:
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return os.path.normpath(path)


def discover_local_state_dir(start_path: str | None = None) -> str | None:
    current = Path(os.path.abspath(start_path or os.getcwd()))
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        state_dir = candidate / LOCAL_STATE_DIRNAME
        if state_dir.is_dir():
            return str(state_dir)
    return None


def get_state_paths() -> StatePaths:
    explicit = os.environ.get("SYMDEX_STATE_DIR")
    if explicit:
        base_dir = _normalize_state_dir(explicit)
    else:
        discovered = discover_local_state_dir()
        base_dir = discovered or get_default_global_state_dir()

    global_base = _normalize_state_dir(get_default_global_state_dir())
    local_mode = os.path.normcase(base_dir) != os.path.normcase(global_base)
    workspace_root = os.path.dirname(base_dir) if local_mode else os.path.expanduser("~")
    return StatePaths(
        base_dir=base_dir,
        registry_db_path=os.path.join(base_dir, "registry.db"),
        registry_json_path=os.path.join(base_dir, "registry.json"),
        workspace_root=workspace_root,
        local_mode=local_mode,
    )


def serialize_registry_value(path: str, state: StatePaths) -> str:
    absolute = os.path.abspath(path)
    if not state.local_mode:
        return absolute

    relative = os.path.relpath(absolute, state.workspace_root).replace("\\", "/")
    if relative == ".":
        return "."
    if relative.startswith(".."):
        return relative
    return f"./{relative}"


def resolve_registry_value(path: str, state: StatePaths) -> str:
    if os.path.isabs(path):
        return os.path.normpath(path)
    if path in {"", "."}:
        return os.path.normpath(state.workspace_root)
    return os.path.normpath(os.path.join(state.workspace_root, path))
