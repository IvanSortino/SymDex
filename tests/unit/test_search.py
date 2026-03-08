# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import pytest
from symdex.core.storage import get_connection, upsert_symbol
from symdex.search.symbol_search import search_symbols
from symdex.search.text_search import search_text


@pytest.fixture
def conn_with_symbols(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    upsert_symbol(conn, "repo1", "a.py", "validate_email", "function", 0, 100,
                  "def validate_email(email):", "Validates an email address.")
    upsert_symbol(conn, "repo1", "a.py", "validate_phone", "function", 101, 200,
                  "def validate_phone(phone):", None)
    upsert_symbol(conn, "repo1", "b.py", "UserModel", "class", 0, 500,
                  "class UserModel:", "Represents a user.")
    upsert_symbol(conn, "repo2", "c.py", "parse_csv", "function", 0, 150,
                  "def parse_csv(path):", None)
    return conn, db_path


def test_search_symbols_prefix_match(conn_with_symbols):
    conn, _ = conn_with_symbols
    results = search_symbols(conn, repo="repo1", query="validate")
    names = [r["name"] for r in results]
    assert "validate_email" in names
    assert "validate_phone" in names


def test_search_symbols_exact_match(conn_with_symbols):
    conn, _ = conn_with_symbols
    results = search_symbols(conn, repo="repo1", query="UserModel")
    assert len(results) == 1
    assert results[0]["name"] == "UserModel"


def test_search_symbols_kind_filter(conn_with_symbols):
    conn, _ = conn_with_symbols
    results = search_symbols(conn, repo="repo1", query="validate", kind="class")
    assert len(results) == 0


def test_search_symbols_no_repo_searches_all(conn_with_symbols):
    conn, _ = conn_with_symbols
    results = search_symbols(conn, repo=None, query="parse_csv")
    assert len(results) == 1
    assert results[0]["name"] == "parse_csv"


def test_search_symbols_returns_empty_on_no_match(conn_with_symbols):
    conn, _ = conn_with_symbols
    results = search_symbols(conn, repo="repo1", query="nonexistent_xyz")
    assert results == []


# --- text_search tests ---

@pytest.fixture
def indexed_dir_with_files(tmp_path, monkeypatch):
    from symdex.core.indexer import index_folder

    # Patch get_db_path so DB goes to tmp_path
    def _mock_get_db_path(repo_name: str) -> str:
        import os
        db_dir = str(tmp_path / ".symdex")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, f"{repo_name}.db")

    monkeypatch.setattr("symdex.core.indexer.get_db_path", _mock_get_db_path)
    monkeypatch.setattr("symdex.core.storage.get_db_path", _mock_get_db_path)
    monkeypatch.setattr("symdex.search.text_search.get_db_path", _mock_get_db_path)

    (tmp_path / "main.py").write_text("def hello():\n    print('hello world')\n")
    (tmp_path / "util.py").write_text("# utility functions\ndef helper(): pass\n")
    result = index_folder(str(tmp_path), name="textrepo")
    return str(tmp_path), result


def test_search_text_finds_match(indexed_dir_with_files):
    dirpath, result = indexed_dir_with_files
    matches = search_text(query="hello", repo="textrepo", repo_root=dirpath)
    assert len(matches) > 0
    assert any("hello" in m["text"].lower() for m in matches)


def test_search_text_returns_file_and_line(indexed_dir_with_files):
    dirpath, result = indexed_dir_with_files
    matches = search_text(query="hello", repo="textrepo", repo_root=dirpath)
    m = matches[0]
    assert "file" in m
    assert "line" in m
    assert "text" in m
    assert isinstance(m["line"], int)


def test_search_text_no_match_returns_empty(indexed_dir_with_files):
    dirpath, result = indexed_dir_with_files
    matches = search_text(query="xyznonexistent", repo="textrepo", repo_root=dirpath)
    assert matches == []


def test_search_text_file_pattern_filter(indexed_dir_with_files):
    dirpath, result = indexed_dir_with_files
    matches = search_text(query="helper", repo="textrepo", repo_root=dirpath, file_pattern="util.py")
    assert all(m["file"] == "util.py" for m in matches)
