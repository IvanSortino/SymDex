# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import numpy as np
import pytest
from symdex.core.storage import get_connection, upsert_embedding, query_symbols_with_embeddings


def test_upsert_and_query_embedding(tmp_path):
    db = str(tmp_path / "test.db")
    conn = get_connection(db)
    conn.execute(
        "INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte) VALUES (?,?,?,?,?,?)",
        ("r", "f.py", "foo", "function", 0, 10),
    )
    conn.commit()
    sym_id = conn.execute("SELECT id FROM symbols WHERE name='foo'").fetchone()[0]
    vec = np.array([0.1, 0.2, 0.3], dtype="float32")
    upsert_embedding(conn, sym_id, vec)
    rows = query_symbols_with_embeddings(conn, repo="r")
    assert len(rows) == 1
    assert rows[0]["name"] == "foo"
    assert rows[0]["embedding"] is not None


def test_null_embedding_excluded(tmp_path):
    db = str(tmp_path / "test.db")
    conn = get_connection(db)
    conn.execute(
        "INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte) VALUES (?,?,?,?,?,?)",
        ("r", "f.py", "bar", "function", 0, 5),
    )
    conn.commit()
    # No embedding — should not appear in query_symbols_with_embeddings
    rows = query_symbols_with_embeddings(conn, repo="r")
    assert rows == []
