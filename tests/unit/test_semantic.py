# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import numpy as np
from unittest.mock import patch
from symdex.search.semantic import embed_text, search_semantic
from symdex.core.storage import get_connection, upsert_embedding

FAKE_VEC = np.array([1.0] + [0.0] * 383, dtype="float32")


@patch("symdex.search.semantic._get_model")
def test_embed_text_local(mock_model):
    mock_model.return_value.encode.return_value = FAKE_VEC
    result = embed_text("hello world")
    assert result.dtype == np.float32
    assert result.shape == (384,)


def test_search_semantic_returns_scored_results(tmp_path):
    db = str(tmp_path / "s.db")
    conn = get_connection(db)
    conn.execute(
        "INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte, docstring) VALUES (?,?,?,?,?,?,?)",
        ("r", "f.py", "parse_file", "function", 0, 10, "Parses source code files"),
    )
    conn.commit()
    sym_id = conn.execute("SELECT id FROM symbols WHERE name='parse_file'").fetchone()[0]
    upsert_embedding(conn, sym_id, FAKE_VEC)

    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        results = search_semantic(conn, query="parse source", repo="r")

    assert len(results) == 1
    assert results[0]["name"] == "parse_file"
    assert 0.0 <= results[0]["score"] <= 1.0


def test_search_semantic_null_embedding_excluded(tmp_path):
    db = str(tmp_path / "s.db")
    conn = get_connection(db)
    conn.execute(
        "INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte) VALUES (?,?,?,?,?,?)",
        ("r", "f.py", "no_embed", "function", 0, 5),
    )
    conn.commit()
    # No embedding upserted — embedding is NULL

    with patch("symdex.search.semantic.embed_text", return_value=FAKE_VEC):
        results = search_semantic(conn, query="anything", repo="r")

    assert results == []
