# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import numpy as np

from symdex.core.storage import (
    get_connection,
    query_repo_has_embeddings,
    upsert_embedding,
    upsert_symbol,
)
from symdex.core.quality import (
    build_item_quality,
    detect_generated_path,
    infer_language_surface,
    normalize_confidence,
)


def test_normalize_confidence_clamps_values():
    assert normalize_confidence(-1) == 0.0
    assert normalize_confidence(2) == 1.0
    assert normalize_confidence(0.42) == 0.42


def test_detect_generated_path_known_patterns():
    assert detect_generated_path("web/dist/app.js") is True
    assert detect_generated_path("pkg/foo.pb.go") is True
    assert detect_generated_path("src/app.py") is False


def test_infer_language_surface_markdown_and_python():
    assert infer_language_surface("README.md") == "markdown"
    assert infer_language_surface("docs/page.mdx") == "markdown"
    assert infer_language_surface("symdex/cli.py") == "python"


def test_build_item_quality_symbol_defaults():
    quality = build_item_quality(
        row={"file": "symdex/cli.py", "name": "search", "kind": "function"},
        result_kind="symbol",
        repo_has_embeddings=True,
        index_status={"stale": False, "last_indexed": "2026-04-19 00:00:00"},
    )

    assert quality["confidence"] == 0.92
    assert quality["confidence_reason"] == "exact symbol match from parser"
    assert quality["index_fresh"] is True
    assert quality["last_indexed"] == "2026-04-19 00:00:00"
    assert quality["parser_mode"] == "tree_sitter"
    assert quality["language_surface"] == "python"
    assert quality["is_generated"] is False
    assert quality["is_ignored"] is False
    assert quality["ignored_reason"] is None
    assert quality["has_embeddings"] is True
    assert quality["route_confidence"] is None


def test_query_repo_has_embeddings(tmp_path):
    db_path = tmp_path / "quality.db"
    conn = get_connection(str(db_path))
    try:
        assert query_repo_has_embeddings(conn, "repo") is False
        symbol_id = upsert_symbol(
            conn,
            repo="repo",
            file="mod.py",
            name="hello",
            kind="function",
            start_byte=0,
            end_byte=10,
            signature=None,
            docstring=None,
        )
        assert query_repo_has_embeddings(conn, "repo") is False
        upsert_embedding(conn, symbol_id, np.array([0.1, 0.2], dtype="float32"))
        assert query_repo_has_embeddings(conn, "repo") is True
    finally:
        conn.close()
