# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import numpy as np
from unittest.mock import patch
from symdex.core.storage import get_connection, query_symbols_with_embeddings

FAKE_VEC = np.array([1.0] + [0.0] * 383, dtype="float32")


def test_indexing_stores_embeddings(tmp_path, monkeypatch):
    """After indexing, symbols should have embeddings stored."""
    (tmp_path / "foo.py").write_text(
        'def hello():\n    """Say hello to the world."""\n    pass\n'
    )
    db_path = str(tmp_path / "test.db")

    monkeypatch.setenv("SYMDEX_EMBED_MODEL", "all-MiniLM-L6-v2")

    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        # Import here to avoid circular issues
        from symdex.core.indexer import index_folder
        with patch("symdex.core.storage.get_db_path", return_value=db_path):
            with patch("symdex.core.indexer.get_db_path", return_value=db_path):
                result = index_folder(str(tmp_path), name="embedtest")

    conn = get_connection(db_path)
    rows = query_symbols_with_embeddings(conn, repo="embedtest")
    assert len(rows) >= 1
    assert rows[0]["embedding"] is not None
