# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import logging
from unittest.mock import patch

from symdex.core.indexer import index_folder
from symdex.core.storage import get_connection, get_repo_stats, upsert_symbol
from symdex.graph.call_graph import extract_edges, get_callees, get_callers


def test_index_folder_populates_edges_for_fresh_symbols(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "sample.ts").write_text(
        "export function callee(): number {\n"
        "  return 1;\n"
        "}\n"
        "\n"
        "export function caller(): number {\n"
        "  return callee();\n"
        "}\n",
        encoding="utf-8",
    )

    db_path = str(tmp_path / "symdex_issue18.db")

    def fake_db_path(repo):
        return db_path

    with (
        patch("symdex.core.indexer.get_db_path", fake_db_path),
        patch("symdex.core.storage.get_db_path", fake_db_path),
    ):
        result = index_folder(str(repo_dir), repo="issue18", embed=False)

    conn = get_connection(result.db_path)
    try:
        edge_count = conn.execute(
            "SELECT COUNT(*) FROM edges e "
            "JOIN symbols s ON e.caller_id = s.id "
            "WHERE s.repo = ?",
            (result.repo,),
        ).fetchone()[0]
        callees = get_callees(conn, "caller", result.repo)
        callers = get_callers(conn, "callee", result.repo)
        stats = get_repo_stats(result.repo, result.db_path)
    finally:
        conn.close()

    assert edge_count > 0
    assert any(callee["name"] == "callee" for callee in callees)
    assert any(caller["name"] == "caller" for caller in callers)
    assert stats["edge_count"] == edge_count


def test_extract_edges_warns_when_symbol_rows_have_no_kind(tmp_path, caplog):
    source_file = tmp_path / "sample.py"
    source = (
        "def callee():\n"
        "    return 1\n"
        "\n"
        "def caller():\n"
        "    return callee()\n"
    )
    source_file.write_text(source, encoding="utf-8")

    conn = get_connection(str(tmp_path / "symdex_issue18.db"))
    try:
        symbol_id = upsert_symbol(
            conn,
            repo="issue18",
            file="sample.py",
            name="caller",
            kind="function",
            start_byte=0,
            end_byte=len(source.encode("utf-8")),
            signature=None,
            docstring=None,
        )

        caplog.set_level(logging.WARNING, logger="symdex.graph.call_graph")
        extract_edges(
            conn,
            repo="issue18",
            file_path="sample.py",
            abs_file=str(source_file),
            symbols=[
                {
                    "id": symbol_id,
                    "name": "caller",
                    "start_byte": 0,
                    "end_byte": len(source.encode("utf-8")),
                }
            ],
        )
    finally:
        conn.close()

    assert "missing required 'kind'" in caplog.text
