# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import numpy as np
import sys
import types
import uuid
import shutil
from pathlib import Path
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


def test_get_model_lazy_loads(monkeypatch):
    """_get_model() should only load the model on first call, not at import."""
    from symdex.search import semantic as semantic_mod

    semantic_mod._model = None

    class _FakeModel:
        def encode(self, text, normalize_embeddings=True):
            return FAKE_VEC

    fake_module = types.SimpleNamespace(SentenceTransformer=lambda model_name: _FakeModel())
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    model = semantic_mod._get_model()
    assert model is not None
    model2 = semantic_mod._get_model()
    assert model is model2


def test_get_model_reports_progress(monkeypatch):
    from symdex.search import semantic as semantic_mod

    semantic_mod._model = None
    calls: list[str] = []

    class _FakeModel:
        def encode(self, text, normalize_embeddings=True):
            return FAKE_VEC

    fake_module = types.SimpleNamespace(SentenceTransformer=lambda model_name: _FakeModel())
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    semantic_mod._get_model(progress_callback=calls.append)
    assert calls[0].startswith("Loading embedding model:")
    assert calls[-1] == "Embedding model ready."


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


def test_voyage_embed_for_index_uses_document_input_type(monkeypatch):
    from symdex.search import semantic as semantic_mod

    semantic_mod._model = None
    calls: list[tuple] = []

    class _FakeClient:
        def embed(self, texts, model=None, input_type=None, truncation=None):
            calls.append((texts, model, input_type, truncation))
            return types.SimpleNamespace(embeddings=[FAKE_VEC.tolist()])

    monkeypatch.setitem(
        sys.modules,
        "voyageai",
        types.SimpleNamespace(Client=lambda api_key=None: _FakeClient()),
    )
    monkeypatch.setenv("SYMDEX_EMBED_BACKEND", "voyage")
    monkeypatch.setenv("SYMDEX_VOYAGE_MODEL", "voyage-code-3")

    vec = semantic_mod.embed_for_index("hello")

    assert vec.dtype == np.float32
    assert calls == [(["hello"], "voyage-code-3", "document", True)]


def test_voyage_embed_for_query_uses_query_input_type(monkeypatch):
    from symdex.search import semantic as semantic_mod

    semantic_mod._model = None
    semantic_mod._voyage_client = None
    calls: list[tuple] = []

    class _FakeClient:
        def embed(self, texts, model=None, input_type=None, truncation=None):
            calls.append((texts, model, input_type, truncation))
            return types.SimpleNamespace(embeddings=[FAKE_VEC.tolist()])

    monkeypatch.setitem(
        sys.modules,
        "voyageai",
        types.SimpleNamespace(Client=lambda api_key=None: _FakeClient()),
    )
    monkeypatch.setenv("SYMDEX_EMBED_BACKEND", "voyage")
    monkeypatch.setenv("SYMDEX_VOYAGE_MODEL", "voyage-code-3")

    vec = semantic_mod.embed_for_query("hello")

    assert vec.dtype == np.float32
    assert calls == [(["hello"], "voyage-code-3", "query", True)]


def test_voyage_embed_asset_for_index_uses_multimodal_embed(monkeypatch):
    from symdex.search import semantic as semantic_mod

    semantic_mod._voyage_client = None
    calls: list[tuple] = []

    class _FakeClient:
        def multimodal_embed(self, inputs, model=None, input_type=None, truncation=None):
            calls.append((inputs, model, input_type, truncation))
            return types.SimpleNamespace(embeddings=[FAKE_VEC.tolist()])

    class _FakeImageModule:
        @staticmethod
        def open(path):
            return f"image:{path}"

    fake_pil = types.SimpleNamespace(Image=_FakeImageModule)
    monkeypatch.setitem(
        sys.modules,
        "voyageai",
        types.SimpleNamespace(Client=lambda api_key=None: _FakeClient()),
    )
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)
    monkeypatch.setitem(sys.modules, "PIL.Image", _FakeImageModule)
    monkeypatch.setenv("SYMDEX_EMBED_BACKEND", "voyage")
    monkeypatch.setenv("SYMDEX_VOYAGE_MULTIMODAL", "1")
    monkeypatch.setenv("SYMDEX_VOYAGE_MULTIMODAL_MODEL", "voyage-multimodal-3.5")

    tmp_dir = Path.cwd() / ".voyage_test_tmp" / uuid.uuid4().hex
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        image_path = tmp_dir / "shot.png"
        image_path.write_bytes(b"fake")

        vec = semantic_mod.embed_asset_for_index(str(image_path))

        assert vec.dtype == np.float32
        assert calls == [([[f"image:{image_path}"]], "voyage-multimodal-3.5", "document", True)]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
