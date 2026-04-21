# tests/unit/test_registry.py
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import os
import pytest
from symdex.core.storage import get_registry_path, upsert_repo, query_repos


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    def _mock_registry_path() -> str:
        db_dir = str(tmp_path / ".symdex")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "registry.db")

    monkeypatch.setattr("symdex.core.storage.get_registry_path", _mock_registry_path)


def test_query_repos_empty():
    assert query_repos() == []


def test_upsert_repo_then_query():
    upsert_repo("myrepo", root_path="/some/path", db_path="/some/.symdex/myrepo.db")
    repos = query_repos()
    assert any(r["name"] == "myrepo" for r in repos)


def test_upsert_repo_stores_root_path():
    upsert_repo("myrepo", root_path="/some/path", db_path="/some/.symdex/myrepo.db")
    repos = query_repos()
    match = next(r for r in repos if r["name"] == "myrepo")
    assert match["root_path"] == os.path.normpath(os.path.abspath("/some/path"))


def test_upsert_repo_updates_existing():
    upsert_repo("myrepo", root_path="/old", db_path="/old.db")
    upsert_repo("myrepo", root_path="/new", db_path="/new.db")
    repos = query_repos()
    matches = [r for r in repos if r["name"] == "myrepo"]
    assert len(matches) == 1
    assert matches[0]["root_path"] == os.path.normpath(os.path.abspath("/new"))


def test_upsert_repo_multiple_repos():
    upsert_repo("alpha", root_path="/alpha", db_path="/alpha.db")
    upsert_repo("beta", root_path="/beta", db_path="/beta.db")
    repos = query_repos()
    names = [r["name"] for r in repos]
    assert "alpha" in names
    assert "beta" in names
