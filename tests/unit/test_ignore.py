# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import os
import tempfile
from pathlib import Path

import pytest
import pathspec

from symdex.core.ignore import build_ignore_spec


def test_default_patterns_block_pycache():
    """Test that default patterns block __pycache__/ and .pyc files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = build_ignore_spec(tmpdir)

        # __pycache__/ should be matched (blocked)
        assert spec.match_file("__pycache__/some.py") is True
        assert spec.match_file("__pycache__/cache.pyc") is True


def test_symdexignore_excludes_file():
    """Test that .symdexignore patterns are applied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        symdexignore_path = os.path.join(tmpdir, ".symdexignore")
        with open(symdexignore_path, "w") as f:
            f.write("secrets.txt\n")

        spec = build_ignore_spec(tmpdir)

        # secrets.txt should be matched (blocked)
        assert spec.match_file("secrets.txt") is True


def test_normal_file_not_excluded():
    """Test that normal source files are not excluded by default patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = build_ignore_spec(tmpdir)

        # src/main.py should NOT be matched (allowed)
        assert spec.match_file("src/main.py") is False


def test_indexer_skips_ignored_files():
    """Test that the indexer respects ignore patterns."""
    from symdex.core.indexer import index_folder
    from symdex.core.storage import get_connection, get_db_path

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Python file in a normal directory
        src_dir = os.path.join(tmpdir, "src")
        os.makedirs(src_dir)
        main_py = os.path.join(src_dir, "main.py")
        with open(main_py, "w") as f:
            f.write("def hello():\n    return 'world'\n")

        # Create a .symdexignore to exclude a pattern
        symdexignore_path = os.path.join(tmpdir, ".symdexignore")
        with open(symdexignore_path, "w") as f:
            f.write("ignored/\n")

        # Create a file in the ignored directory
        ignored_dir = os.path.join(tmpdir, "ignored")
        os.makedirs(ignored_dir)
        ignored_py = os.path.join(ignored_dir, "ignored.py")
        with open(ignored_py, "w") as f:
            f.write("def secret():\n    pass\n")

        # Index the folder
        result = index_folder(tmpdir, name="test-ignore")

        # Query the database to check what was indexed
        db_path = get_db_path("test-ignore")
        conn = get_connection(db_path)
        try:
            indexed_files = conn.execute(
                "SELECT path FROM files WHERE repo=?", ("test-ignore",)
            ).fetchall()
            indexed_paths = [row["path"] for row in indexed_files]

            # src/main.py should be indexed
            assert "src/main.py" in indexed_paths, f"Expected src/main.py in {indexed_paths}"

            # ignored/ignored.py should NOT be indexed
            assert "ignored/ignored.py" not in indexed_paths, f"Did not expect ignored/ignored.py in {indexed_paths}"
        finally:
            conn.close()
