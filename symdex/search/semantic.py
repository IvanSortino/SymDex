# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

import os

# Suppress HuggingFace Hub noise at import time
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")

import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get("SYMDEX_EMBED_MODEL", "all-MiniLM-L6-v2")
        _model = SentenceTransformer(model_name)
    return _model


def embed_text(text: str) -> np.ndarray:
    """Return float32 embedding vector for text."""
    backend = os.environ.get("SYMDEX_EMBED_BACKEND", "local")
    if backend == "claude":
        return _embed_claude(text)
    model = _get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.astype("float32")


def embed_for_index(text: str) -> np.ndarray:
    """Return float32 embedding for indexing with 'search_document: ' prefix.

    Asymmetric models expect the 'search_document: ' prefix for indexed text.
    """
    backend = os.environ.get("SYMDEX_EMBED_BACKEND", "local")
    if backend == "claude":
        return _embed_claude(f"search_document: {text}")
    model = _get_model()
    vec = model.encode(f"search_document: {text}", normalize_embeddings=True)
    return vec.astype("float32")


def embed_for_query(text: str) -> np.ndarray:
    """Return float32 embedding for search queries with 'search_query: ' prefix.

    Asymmetric models expect the 'search_query: ' prefix for query text.
    """
    backend = os.environ.get("SYMDEX_EMBED_BACKEND", "local")
    if backend == "claude":
        return _embed_claude(f"search_query: {text}")
    model = _get_model()
    vec = model.encode(f"search_query: {text}", normalize_embeddings=True)
    return vec.astype("float32")


def _embed_claude(text: str) -> np.ndarray:
    import anthropic
    client = anthropic.Anthropic()
    response = client.embeddings.create(
        model="voyage-code-2",
        input=[text],
    )
    return np.array(response.embeddings[0].embedding, dtype="float32")


def search_semantic(
    conn,
    query: str,
    repo: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Cosine similarity search over stored embeddings."""
    from symdex.core.storage import query_symbols_with_embeddings

    query_vec = embed_for_query(query)
    rows = query_symbols_with_embeddings(conn, repo=repo)

    if not rows:
        return []

    results = []
    for row in rows:
        blob = row["embedding"]
        stored_vec = np.frombuffer(blob, dtype="float32")
        score = float(np.dot(query_vec, stored_vec))
        result = {k: v for k, v in row.items() if k != "embedding"}
        result["score"] = round(score, 4)
        results.append(result)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
