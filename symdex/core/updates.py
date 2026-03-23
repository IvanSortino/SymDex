# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from symdex.core.storage import get_registry_path

PACKAGE_NAME = "symdex"
PYPI_JSON_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
CACHE_FILENAME = "update_check.json"
CACHE_TTL_SECONDS = 60 * 60 * 6
DISABLE_ENV_VAR = "SYMDEX_DISABLE_UPDATE_CHECK"


def get_installed_version() -> str:
    return importlib.metadata.version(PACKAGE_NAME)


def should_check_for_updates(argv: list[str] | None = None) -> bool:
    if os.environ.get(DISABLE_ENV_VAR):
        return False
    args = argv or sys.argv[1:]
    return "--json" not in args


def get_update_notice(argv: list[str] | None = None) -> dict[str, str] | None:
    if not should_check_for_updates(argv):
        return None

    installed = get_installed_version()
    latest = _get_latest_version(installed)
    if latest is None or not _is_newer(latest, installed):
        return None

    return {
        "installed_version": installed,
        "latest_version": latest,
        "pip_command": "py -m pip install -U symdex",
        "uv_tool_command": "uv tool upgrade symdex",
        "uvx_command": _build_uvx_upgrade_command(argv or sys.argv[1:]),
    }


def _build_uvx_upgrade_command(argv: list[str]) -> str:
    rerun_args = argv or ["--help"]
    if os.name == "nt":
        return subprocess.list2cmdline(["uvx", "symdex@latest", *rerun_args])
    return " ".join(["uvx", "symdex@latest", *rerun_args])


def _get_cache_path() -> Path:
    return Path(get_registry_path()).resolve().parent / CACHE_FILENAME


def _get_latest_version(installed_version: str) -> str | None:
    cache = _load_cache()
    now = time.time()
    if cache and now - float(cache.get("checked_at", 0)) < CACHE_TTL_SECONDS:
        return str(cache.get("latest_version", installed_version))

    latest = _fetch_latest_version()
    if latest is None:
        return str(cache.get("latest_version")) if cache else None

    _save_cache({"checked_at": now, "latest_version": latest})
    return latest


def _fetch_latest_version() -> str | None:
    request = urllib.request.Request(
        PYPI_JSON_URL,
        headers={"User-Agent": "symdex-update-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=1.5) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    return str(payload.get("info", {}).get("version") or "")


def _load_cache() -> dict[str, object] | None:
    cache_path = _get_cache_path()
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _save_cache(payload: dict[str, object]) -> None:
    cache_path = _get_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        return


def _is_newer(candidate: str, installed: str) -> bool:
    try:
        return _parse_version(candidate) > _parse_version(installed)
    except ValueError:
        return False


def _parse_version(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3:
        raise ValueError(value)
    return tuple(int(part) for part in parts)
