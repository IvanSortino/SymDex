# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from __future__ import annotations

import hashlib
import os
import re


def _slugify(value: str) -> str:
    """Convert a value into a lowercase repo-safe slug."""
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower()
    return slug or "repo"


def _short_path_hash(path: str, length: int = 8) -> str:
    """Return a short stable hash for a filesystem path."""
    digest = hashlib.sha256(os.path.abspath(path).encode("utf-8", errors="ignore")).hexdigest()
    return digest[:length]


def normalize_repo_name(name: str) -> str:
    """Normalize an explicit repo name for storage and lookup."""
    return _slugify(name)


def derive_repo_name(path: str, repo: str | None = None, name: str | None = None) -> str:
    """Derive a stable repo name from the explicit name, git branch, and path.

    Priority:
    1. Explicit repo/name override.
    2. Folder name + git branch + short path hash.
    3. Folder name + short path hash.
    """
    explicit = repo or name
    if explicit:
        return normalize_repo_name(explicit)

    abs_path = os.path.abspath(path)
    base = _slugify(os.path.basename(abs_path) or "repo")
    parts = [base]

    try:
        from symdex.core.indexer import get_git_branch

        branch = get_git_branch(abs_path)
    except Exception:  # noqa: BLE001
        branch = None

    if branch:
        parts.append(_slugify(branch))

    parts.append(_short_path_hash(abs_path))
    return "-".join(parts)
