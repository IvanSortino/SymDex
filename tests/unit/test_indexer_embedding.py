# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import numpy as np
import uuid
import shutil
import sys
import logging
import builtins
from pathlib import Path
from unittest.mock import patch
from symdex.core.storage import get_connection, query_symbols, query_symbols_with_embeddings

FAKE_VEC = np.array([1.0] + [0.0] * 383, dtype="float32")


def _block_semantic_import():
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "symdex.search.semantic":
            raise AssertionError("semantic embeddings must not be imported")
        return real_import(name, globals, locals, fromlist, level)

    return patch("builtins.__import__", side_effect=guarded_import)


def test_indexing_stores_embeddings(tmp_path, monkeypatch):
    """After indexing, symbols should have embeddings stored."""
    repo_dir = tmp_path / "repo"
    state_dir = tmp_path / "state"
    repo_dir.mkdir()
    state_dir.mkdir()
    (repo_dir / "foo.py").write_text(
        'def hello():\n    """Say hello to the world."""\n    pass\n'
    )
    db_path = str(state_dir / "test.db")

    monkeypatch.setenv("SYMDEX_EMBED_MODEL", "all-MiniLM-L6-v2")

    with patch("symdex.search.semantic.embed_for_index", return_value=FAKE_VEC):
        # Import here to avoid circular issues
        from symdex.core.indexer import index_folder
        with patch("symdex.core.storage.get_db_path", return_value=db_path):
            with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                index_folder(str(repo_dir), name="embedtest")

    conn = get_connection(db_path)
    rows = query_symbols_with_embeddings(conn, repo="embedtest")
    conn.close()
    assert len(rows) >= 1
    assert rows[0]["embedding"] is not None


def test_indexing_stores_voyage_asset_embedding(monkeypatch):
    """Voyage multimodal mode should store a searchable asset row for binary files."""
    monkeypatch.setenv("SYMDEX_EMBED_BACKEND", "voyage")
    monkeypatch.setenv("SYMDEX_VOYAGE_MULTIMODAL", "1")

    repo_dir = Path.cwd() / ".voyage_test_tmp" / uuid.uuid4().hex
    repo_dir.mkdir(parents=True, exist_ok=True)
    try:
        (repo_dir / "shot.png").write_bytes(b"fake image bytes")
        db_path = str(repo_dir / "test.db")

        with patch("symdex.search.semantic.embed_asset_for_index", return_value=FAKE_VEC):
            from symdex.core.indexer import index_folder
            with patch("symdex.core.storage.get_db_path", return_value=db_path):
                with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                    index_folder(str(repo_dir), name="embedasset")

        conn = get_connection(db_path)
        rows = conn.execute(
            "SELECT name, kind, embedding FROM symbols WHERE repo=?",
            ("embedasset",),
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["kind"] == "asset"
        assert rows[0]["embedding"] is not None
    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)


def test_indexing_without_local_extra_skips_embeddings_once(tmp_path, monkeypatch, caplog):
    repo_dir = tmp_path / "repo"
    state_dir = tmp_path / "state"
    repo_dir.mkdir()
    state_dir.mkdir()
    (repo_dir / "foo.py").write_text(
        'def hello():\n    """Say hello to the world."""\n    pass\n'
    )
    db_path = str(state_dir / "test.db")

    monkeypatch.delenv("SYMDEX_EMBED_BACKEND", raising=False)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    from symdex.core.indexer import index_folder

    with caplog.at_level(logging.WARNING):
        with patch(
            "symdex.search.semantic.embed_for_index",
            side_effect=RuntimeError("The local semantic backend requires symdex[local]"),
        ):
            with patch("symdex.core.storage.get_db_path", return_value=db_path):
                with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                    result = index_folder(str(repo_dir), name="embedskip")

    conn = get_connection(db_path)
    rows = query_symbols_with_embeddings(conn, repo="embedskip")
    conn.close()

    assert result.indexed_count == 1
    assert rows == []
    warnings = [
        record.message for record in caplog.records
        if "symdex[local]" in record.message
    ]
    assert len(warnings) == 1


def test_indexing_with_embed_false_skips_symbol_embeddings(tmp_path):
    """Low-memory callers can index symbols without loading embedding backends."""
    repo_dir = tmp_path / "repo"
    state_dir = tmp_path / "state"
    repo_dir.mkdir()
    state_dir.mkdir()
    (repo_dir / "foo.py").write_text(
        'def hello():\n    """Say hello to the world."""\n    pass\n'
    )
    db_path = str(state_dir / "test.db")

    from symdex.core.indexer import index_folder

    with patch("symdex.core.indexer._embed_symbols", side_effect=AssertionError("embedding should be skipped")):
        with patch("symdex.core.storage.get_db_path", return_value=db_path):
            with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                result = index_folder(str(repo_dir), name="noembed", embed=False)

    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT name, embedding FROM symbols WHERE repo=? ORDER BY name",
        ("noembed",),
    ).fetchall()
    conn.close()

    assert result.indexed_count == 1
    assert [row["name"] for row in rows] == ["hello"]
    assert rows[0]["embedding"] is None


def test_reindex_with_embed_true_backfills_missing_embeddings_for_unchanged_files():
    repo_dir = Path.cwd() / ".indexer_test_tmp" / uuid.uuid4().hex
    state_dir = repo_dir / "state"
    repo_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir()
    try:
        (repo_dir / "foo.py").write_text(
            'def hello():\n    """Say hello to the world."""\n    pass\n'
        )
        db_path = str(state_dir / "test.db")

        from symdex.core.indexer import index_folder

        with patch("symdex.core.storage.get_db_path", return_value=db_path):
            with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                index_folder(str(repo_dir), name="backfill", embed=False)

        with patch("symdex.search.semantic.embed_for_index", return_value=FAKE_VEC):
            with patch("symdex.core.storage.get_db_path", return_value=db_path):
                with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                    index_folder(str(repo_dir), name="backfill", embed=True)

        conn = get_connection(db_path)
        rows = query_symbols_with_embeddings(conn, repo="backfill")
        conn.close()

        assert len(rows) >= 1
        assert rows[0]["embedding"] is not None
    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)


def test_indexing_without_embeddings_skips_semantic_import_and_keeps_symbols(tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    state_dir = tmp_path / "state"
    repo_dir.mkdir()
    state_dir.mkdir()
    (repo_dir / "foo.py").write_text(
        'def hello():\n    """Say hello to the world."""\n    pass\n'
    )
    db_path = str(state_dir / "test.db")

    monkeypatch.delenv("SYMDEX_EMBED_BACKEND", raising=False)
    monkeypatch.delenv("SYMDEX_VOYAGE_MULTIMODAL", raising=False)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    monkeypatch.delitem(sys.modules, "symdex.search.semantic", raising=False)

    from symdex.core.indexer import index_folder

    with _block_semantic_import():
        with patch("symdex.core.storage.get_db_path", return_value=db_path):
            with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                result = index_folder(str(repo_dir), name="noembed", embed=False)

    conn = get_connection(db_path)
    symbol_rows = query_symbols(conn, repo="noembed", name_pattern="hello")
    embedding_rows = query_symbols_with_embeddings(conn, repo="noembed")
    conn.close()

    assert result.indexed_count == 1
    assert symbol_rows
    assert embedding_rows == []


def test_indexing_without_embeddings_skips_voyage_asset_indexing(monkeypatch):
    monkeypatch.setenv("SYMDEX_EMBED_BACKEND", "voyage")
    monkeypatch.setenv("SYMDEX_VOYAGE_MULTIMODAL", "1")
    monkeypatch.delitem(sys.modules, "symdex.search.semantic", raising=False)

    repo_dir = Path.cwd() / ".voyage_test_tmp" / uuid.uuid4().hex
    repo_dir.mkdir(parents=True, exist_ok=True)
    try:
        (repo_dir / "shot.png").write_bytes(b"fake image bytes")
        db_path = str(Path.cwd() / ".voyage_test_tmp" / f"{uuid.uuid4().hex}.db")

        from symdex.core.indexer import index_folder

        with _block_semantic_import():
            with patch("symdex.core.storage.get_db_path", return_value=db_path):
                with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                    result = index_folder(str(repo_dir), name="noassetembed", embed=False)

        conn = get_connection(db_path)
        rows = conn.execute(
            "SELECT name, kind, embedding FROM symbols WHERE repo=?",
            ("noassetembed",),
        ).fetchall()
        conn.close()

        assert result.indexed_count == 0
        assert rows == []
    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)
