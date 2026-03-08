# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import os
import pytest
from symdex.core.indexer import index_folder, invalidate


PY_A = '''\
def func_a():
    pass
'''

PY_B = '''\
class ClassB:
    pass
'''

PY_C = '''\
def func_c():
    return 1
'''


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect DB storage to tmp_path for every test — prevents stale state in ~/.symdex/."""
    def _mock_get_db_path(repo_name: str) -> str:
        db_dir = str(tmp_path / ".symdex")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, f"{repo_name}.db")

    monkeypatch.setattr("symdex.core.indexer.get_db_path", _mock_get_db_path)
    monkeypatch.setattr("symdex.core.storage.get_db_path", _mock_get_db_path)


@pytest.fixture
def three_file_dir(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text(PY_A)
    (src / "b.py").write_text(PY_B)
    (src / "c.py").write_text(PY_C)
    return str(src)


@pytest.fixture
def dir_with_node_modules(tmp_path):
    src = tmp_path / "proj"
    src.mkdir()
    (src / "main.py").write_text(PY_A)
    nm = src / "node_modules"
    nm.mkdir()
    (nm / "lib.py").write_text("def node_func(): pass")
    return str(src)


def test_index_three_files_returns_correct_count(three_file_dir):
    result = index_folder(three_file_dir)
    assert result.indexed_count == 3
    assert result.skipped_count == 0


def test_reindex_unchanged_skips_all(three_file_dir):
    index_folder(three_file_dir)
    result = index_folder(three_file_dir)
    assert result.indexed_count == 0
    assert result.skipped_count == 3


def test_reindex_after_modification_indexes_one(three_file_dir):
    index_folder(three_file_dir)
    with open(os.path.join(three_file_dir, "a.py"), "w") as f:
        f.write("def func_a_modified(): pass\n")
    result = index_folder(three_file_dir)
    assert result.indexed_count == 1
    assert result.skipped_count == 2


def test_node_modules_excluded(dir_with_node_modules):
    result = index_folder(dir_with_node_modules)
    assert result.indexed_count == 1


def test_index_folder_returns_repo_name(three_file_dir):
    result = index_folder(three_file_dir)
    assert result.repo == os.path.basename(three_file_dir)


def test_index_folder_custom_name(three_file_dir):
    result = index_folder(three_file_dir, name="myproject")
    assert result.repo == "myproject"


def test_index_folder_creates_db_file(three_file_dir):
    result = index_folder(three_file_dir)
    assert os.path.exists(result.db_path)


def test_invalidate_full_repo_causes_reindex(three_file_dir):
    """After invalidating a repo, next index_folder re-indexes all files."""
    index_folder(three_file_dir)
    result_skipped = index_folder(three_file_dir)
    assert result_skipped.skipped_count == 3  # confirm all skipped

    repo_name = os.path.basename(three_file_dir)
    invalidate(repo_name)

    result_reindexed = index_folder(three_file_dir)
    assert result_reindexed.indexed_count == 3


def test_invalidate_single_file_causes_partial_reindex(three_file_dir):
    """After invalidating one file, only that file is re-indexed."""
    index_folder(three_file_dir)
    repo_name = os.path.basename(three_file_dir)
    invalidate(repo_name, file="a.py")

    result = index_folder(three_file_dir)
    assert result.indexed_count == 1
    assert result.skipped_count == 2
