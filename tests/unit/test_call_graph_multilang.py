# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from unittest.mock import patch

import pytest

from symdex.core.indexer import index_folder
from symdex.core.storage import get_connection
from symdex.graph.call_graph import get_callees


@pytest.mark.parametrize(
    ("filename", "source"),
    [
        (
            "sample.kt",
            "fun callee(): Int = 1\n"
            "fun caller(): Int = callee()\n",
        ),
        (
            "sample.dart",
            "int callee() => 1;\n"
            "int caller() {\n"
            "  return callee();\n"
            "}\n",
        ),
        (
            "sample.swift",
            "func callee() -> Int { return 1 }\n"
            "func caller() -> Int { return callee() }\n",
        ),
    ],
)
def test_index_folder_extracts_mobile_language_call_graph(tmp_path, filename, source):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / filename).write_text(source, encoding="utf-8")

    db_path_store = {}

    def fake_db_path(repo):
        path = str(tmp_path / f"{repo}.db")
        db_path_store[repo] = path
        return path

    with (
        patch("symdex.core.indexer.get_db_path", fake_db_path),
        patch("symdex.core.storage.get_db_path", fake_db_path),
        patch("symdex.search.semantic.embed_text", return_value=[0.0] * 384),
    ):
        index_folder(str(repo_dir), name="mobile_call_graph")

    conn = get_connection(db_path_store["mobile_call_graph"])
    callees = get_callees(conn, "caller", "mobile_call_graph")
    conn.close()

    assert any(callee["name"] == "callee" for callee in callees)
