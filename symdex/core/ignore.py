# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import os
import pathspec


# Built-in default patterns (always applied, even without any ignore files)
DEFAULT_PATTERNS = [
    "__pycache__/",
    "*.pyc",
    ".venv/",
    "venv/",
    "node_modules/",
    "dist/",
    "build/",
    ".next/",
    ".nuxt/",
    "coverage/",
    ".coverage",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.egg-info/",
    ".git/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".worktrees/",
    ".symdex/",
]


def build_ignore_spec(root_path: str) -> pathspec.PathSpec:
    """Build a combined ignore spec from built-in patterns, .gitignore, and .symdexignore.

    Args:
        root_path: Root directory path to search for .gitignore and .symdexignore files.

    Returns:
        A pathspec.PathSpec that can be used to filter file paths.
    """
    all_patterns = list(DEFAULT_PATTERNS)

    # Load .gitignore if it exists
    gitignore_path = os.path.join(root_path, ".gitignore")
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    # Skip comments and blank lines
                    if line and not line.startswith("#"):
                        all_patterns.append(line)
        except Exception:
            pass

    # Load .symdexignore if it exists
    symdexignore_path = os.path.join(root_path, ".symdexignore")
    if os.path.isfile(symdexignore_path):
        try:
            with open(symdexignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    # Skip comments and blank lines
                    if line and not line.startswith("#"):
                        all_patterns.append(line)
        except Exception:
            pass

    return pathspec.PathSpec.from_lines("gitignore", all_patterns)
