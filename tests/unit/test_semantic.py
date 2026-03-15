# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import numpy as np
from unittest.mock import patch
from symdex.search.semantic import embed_text, search_semantic, embed_for_index, embed_for_query
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

    with patch("symdex.search.semantic.embed_for_query", return_value=FAKE_VEC):
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

    with patch("symdex.search.semantic.embed_for_query", return_value=FAKE_VEC):
        results = search_semantic(conn, query="anything", repo="r")

    assert results == []


def test_hf_hub_env_vars_set():
    """HF Hub environment variables should be set after importing semantic module."""
    import os
    # Re-verify env vars are set (they should be set at module import time)
    assert os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS") == "1"
    assert os.environ.get("TOKENIZERS_PARALLELISM") == "false"
    assert os.environ.get("HF_HUB_VERBOSITY") == "error"


def test_get_model_lazy_loads():
    """_get_model() should only load the model on first call, not at import."""
    from symdex.search.semantic import _get_model
    # Just verify that _get_model can be called without errors (it will load on first call)
    model = _get_model()
    assert model is not None
    # Verify it's reused on second call (same object)
    model2 = _get_model()
    assert model is model2


@patch("symdex.search.semantic._get_model")
def test_embed_for_index_prepends_document_prefix(mock_model):
    """embed_for_index should prepend 'search_document: ' before embedding."""
    mock_model.return_value.encode.return_value = FAKE_VEC
    embed_for_index("hello")
    # Verify the model was called with the prefixed text
    mock_model.return_value.encode.assert_called_once_with(
        "search_document: hello",
        normalize_embeddings=True
    )


@patch("symdex.search.semantic._get_model")
def test_embed_for_query_prepends_query_prefix(mock_model):
    """embed_for_query should prepend 'search_query: ' before embedding."""
    mock_model.return_value.encode.return_value = FAKE_VEC
    embed_for_query("hello")
    # Verify the model was called with the prefixed text
    mock_model.return_value.encode.assert_called_once_with(
        "search_query: hello",
        normalize_embeddings=True
    )
