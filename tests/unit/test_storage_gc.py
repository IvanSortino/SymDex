# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import os
from pathlib import Path

from symdex.core.indexer import index_folder
from symdex.core.storage import get_db_path, get_stale_repos


def test_get_stale_repos_detects_missing_db(tmp_path, monkeypatch):
    """Deleting the .db file should leave a stale registry entry."""
    state_dir = tmp_path / ".symdex"
    monkeypatch.setenv("SYMDEX_STATE_DIR", str(state_dir))
    project = tmp_path / "proj"
    project.mkdir()
    (project / "module.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")

    result = index_folder(str(project), repo="stale_repo")

    db_path = get_db_path("stale_repo")
    assert os.path.isfile(db_path)
    os.remove(db_path)
    stale = get_stale_repos()
    assert any(entry["name"] == result.repo for entry in stale)
