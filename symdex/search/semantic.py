# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Callable, Optional

# Suppress HuggingFace Hub noise at import time
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import numpy as np

logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

try:  # pragma: no cover - optional dependency hygiene
    from transformers.utils import logging as hf_logging  # type: ignore
    hf_logging.set_verbosity_error()
except Exception:  # noqa: BLE001
    pass

_model = None
_voyage_client = None


def _notify(progress_callback: Optional[Callable[[str], None]], message: str) -> None:
    if progress_callback is not None:
        progress_callback(message)


def _backend() -> str:
    return os.environ.get("SYMDEX_EMBED_BACKEND", "local").strip().lower()


def _missing_extra_message(feature: str, extra: str, package: str) -> str:
    return (
        f"{feature} requires the optional '{package}' package. "
        f"Install it with `pip install \"symdex[{extra}]\"`."
    )


def _is_closed_hf_client_error(exc: Exception) -> bool:
    return "client has been closed" in str(exc).lower()


def _reset_huggingface_client() -> None:
    try:
        from huggingface_hub import close_session  # type: ignore
    except Exception:  # noqa: BLE001
        return
    try:
        close_session()
    except Exception:  # noqa: BLE001
        pass


def _get_model(progress_callback: Optional[Callable[[str], None]] = None):
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on user install
            raise RuntimeError(
                _missing_extra_message(
                    "The local semantic backend",
                    "local",
                    "sentence-transformers",
                )
            ) from exc
        model_name = os.environ.get("SYMDEX_EMBED_MODEL", "all-MiniLM-L6-v2")
        _notify(progress_callback, f"Loading embedding model: {model_name}")
        try:
            _model = SentenceTransformer(model_name)
        except RuntimeError as exc:
            if not _is_closed_hf_client_error(exc):
                raise
            _notify(progress_callback, "Resetting Hugging Face client and retrying model load.")
            _reset_huggingface_client()
            try:
                _model = SentenceTransformer(model_name)
            except RuntimeError as retry_exc:
                if not _is_closed_hf_client_error(retry_exc):
                    raise
                _notify(progress_callback, "Falling back to the cached local embedding model.")
                _model = SentenceTransformer(model_name, local_files_only=True)
        _notify(progress_callback, "Embedding model ready.")
    return _model


def _get_voyage_client(progress_callback: Optional[Callable[[str], None]] = None):
    global _voyage_client
    if _voyage_client is None:
        _notify(progress_callback, "Loading Voyage API client.")
        try:
            import voyageai
        except ImportError as exc:  # pragma: no cover - depends on user install
            raise RuntimeError(
                _missing_extra_message(
                    "The Voyage backend",
                    "voyage",
                    "voyageai",
                )
            ) from exc

        api_key = os.environ.get("VOYAGE_API_KEY")
        _voyage_client = voyageai.Client(api_key=api_key) if api_key else voyageai.Client()
        _notify(progress_callback, "Voyage API client ready.")
    return _voyage_client


def _voyage_text_model() -> str:
    return os.environ.get("SYMDEX_VOYAGE_MODEL", "voyage-code-3")


def _voyage_multimodal_model() -> str:
    return os.environ.get("SYMDEX_VOYAGE_MULTIMODAL_MODEL", "voyage-multimodal-3.5")


def _voyage_multimodal_enabled() -> bool:
    return os.environ.get("SYMDEX_VOYAGE_MULTIMODAL", "0").strip().lower() in {"1", "true", "yes", "on"}


def _extract_embedding(result: Any) -> np.ndarray:
    embeddings = getattr(result, "embeddings", None)
    if embeddings is None:
        raise RuntimeError("Voyage response did not include embeddings.")
    if not embeddings:
        raise RuntimeError("Voyage response returned no embeddings.")
    return np.array(embeddings[0], dtype="float32")


def _embed_voyage_text(
    text: str,
    input_type: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> np.ndarray:
    client = _get_voyage_client(progress_callback=progress_callback)
    model = _voyage_text_model()
    _notify(progress_callback, f"Embedding with Voyage model: {model}")
    result = client.embed(
        texts=[text],
        model=model,
        input_type=input_type,
        truncation=True,
    )
    _notify(progress_callback, "Voyage embedding ready.")
    return _extract_embedding(result)


def _load_multimodal_input(path: str):
    suffix = Path(path).suffix.lower()
    image_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg"}

    if suffix in image_suffixes:
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - depends on user install
            raise RuntimeError(
                _missing_extra_message(
                    "Voyage multimodal indexing for image assets",
                    "voyage-multimodal",
                    "pillow",
                )
            ) from exc

        image = Image.open(path)
        try:
            return image.copy() if hasattr(image, "copy") else image
        finally:
            close = getattr(image, "close", None)
            if callable(close):
                close()

    if suffix == ".pdf":
        try:
            import fitz  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                _missing_extra_message(
                    "Voyage multimodal indexing for PDFs",
                    "voyage-multimodal",
                    "pymupdf",
                )
            ) from exc

        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - depends on user install
            raise RuntimeError(
                _missing_extra_message(
                    "Voyage multimodal indexing for PDFs",
                    "voyage-multimodal",
                    "pillow",
                )
            ) from exc

        with fitz.open(path) as doc:
            if doc.page_count == 0:
                raise RuntimeError("Cannot embed an empty PDF.")
            page = doc.load_page(0)
            pix = page.get_pixmap(alpha=False)
            return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    raise RuntimeError(f"Voyage multimodal indexing does not support '{suffix}' files.")


def embed_asset_for_index(
    path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> np.ndarray:
    """Return a Voyage multimodal embedding for a supported asset file."""
    if _backend() != "voyage":
        raise RuntimeError("Asset embeddings are only available with the Voyage backend.")
    if not _voyage_multimodal_enabled():
        raise RuntimeError("Voyage multimodal mode is disabled.")

    client = _get_voyage_client(progress_callback=progress_callback)
    model = _voyage_multimodal_model()
    _notify(progress_callback, f"Embedding asset with Voyage multimodal model: {model}")
    image = _load_multimodal_input(path)
    result = client.multimodal_embed(
        inputs=[[image]],
        model=model,
        input_type="document",
        truncation=True,
    )
    _notify(progress_callback, "Voyage multimodal embedding ready.")
    return _extract_embedding(result)


def embed_text(text: str, progress_callback: Optional[Callable[[str], None]] = None) -> np.ndarray:
    """Return float32 embedding vector for text."""
    backend = _backend()
    if backend == "mcpclient":
        return _embed_mcpclient(text)
    if backend == "voyage":
        return _embed_voyage_text(text, input_type="document", progress_callback=progress_callback)
    model = _get_model(progress_callback=progress_callback)
    vec = model.encode(text, normalize_embeddings=True)
    return vec.astype("float32")


def embed_for_index(
    text: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> np.ndarray:
    """Return float32 embedding for indexing with 'search_document: ' prefix.

    Asymmetric models expect the 'search_document: ' prefix for indexed text.
    """
    backend = _backend()
    if backend == "mcpclient":
        return _embed_mcpclient(f"search_document: {text}")
    if backend == "voyage":
        return _embed_voyage_text(text, input_type="document", progress_callback=progress_callback)
    model = _get_model(progress_callback=progress_callback)
    vec = model.encode(f"search_document: {text}", normalize_embeddings=True)
    return vec.astype("float32")


def embed_for_query(
    text: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> np.ndarray:
    """Return float32 embedding for search queries with 'search_query: ' prefix.

    Asymmetric models expect the 'search_query: ' prefix for query text.
    """
    backend = _backend()
    if backend == "mcpclient":
        return _embed_mcpclient(f"search_query: {text}")
    if backend == "voyage":
        return _embed_voyage_text(text, input_type="query", progress_callback=progress_callback)
    model = _get_model(progress_callback=progress_callback)
    vec = model.encode(f"search_query: {text}", normalize_embeddings=True)
    return vec.astype("float32")


def _embed_mcpclient(text: str) -> np.ndarray:
    import mcp
    client = mcp.MCP project()
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
    progress_callback: Optional[Callable[[str], None]] = None,
) -> list[dict]:
    """Cosine similarity search over stored embeddings."""
    from symdex.core.storage import query_symbols_with_embeddings

    query_vec = embed_for_query(query, progress_callback=progress_callback)
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
