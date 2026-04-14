# symdex/graph/call_graph.py
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

from __future__ import annotations
import logging
import os
import re
import sqlite3

from symdex.core.parser import _get_language as _parser_get_language

logger = logging.getLogger(__name__)

_SUPPORTED_EXTS = {
    ".py",
    ".js",
    ".mjs",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".dart",
    ".swift",
    ".r",
    ".R",
}
_DART_CALL_RE = re.compile(r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\s*\(")


def _get_language(ext: str):
    if ext.lower() not in _SUPPORTED_EXTS:
        return None, None
    return _parser_get_language(ext)


def _extract_callee_name_from_text(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    text = text.split(".")[-1]
    return text or None


def _find_calls_in_range(node, start_byte: int, end_byte: int, *, lang_name: str, source_bytes: bytes) -> list[str]:
    """Return callee names for all call nodes within [start_byte, end_byte)."""
    results = []
    if node.end_byte <= start_byte or node.start_byte >= end_byte:
        return results

    if node.type == "call" and start_byte <= node.start_byte < end_byte:
        func_node = node.child_by_field_name("function")
        if func_node:
            if func_node.type == "attribute":
                attr = func_node.child_by_field_name("attribute")
                name = attr.text.decode("utf-8", "replace") if attr else func_node.text.decode("utf-8", "replace")
            else:
                name = func_node.text.decode("utf-8", "replace")
            if name:
                results.append(name)

    if node.type == "call_expression" and start_byte <= node.start_byte < end_byte:
        func_node = node.child_by_field_name("function")
        if func_node is None:
            func_node = next(
                (
                    child
                    for child in node.children
                    if child.is_named and child.type not in {"value_arguments", "call_suffix", "argument_part"}
                ),
                None,
            )
        if func_node is not None:
            raw = source_bytes[func_node.start_byte:func_node.end_byte].decode("utf-8", "replace")
            name = _extract_callee_name_from_text(raw)
            if name:
                results.append(name)

    if lang_name == "dart" and node.type in {"function_body", "expression_statement"}:
        text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", "replace")
        for match in _DART_CALL_RE.finditer(text):
            name = _extract_callee_name_from_text(match.group(1))
            if name and name not in {"if", "for", "while", "switch", "return"}:
                results.append(name)

    for child in node.children:
        results.extend(_find_calls_in_range(child, start_byte, end_byte, lang_name=lang_name, source_bytes=source_bytes))
    return results


def extract_edges(
    conn: sqlite3.Connection,
    repo: str,
    file_path: str,
    abs_file: str,
    symbols: list[dict],
) -> None:
    """Extract call edges from a file and store them in the edges table."""
    if not symbols:
        return
    ext = os.path.splitext(abs_file)[1]
    lang_name, language = _get_language(ext)
    if language is None:
        return

    try:
        source_bytes = open(abs_file, "rb").read()
    except OSError as exc:
        logger.warning("Could not read %s for edge extraction: %s", abs_file, exc)
        return

    try:
        from tree_sitter import Parser as TSParser
        parser = TSParser(language)
        tree = parser.parse(source_bytes)
    except Exception as exc:
        logger.warning("Tree-sitter parse failed for %s: %s", abs_file, exc)
        return

    # Delete old edges for this file's symbols
    conn.execute(
        "DELETE FROM edges WHERE caller_id IN (SELECT id FROM symbols WHERE repo=? AND file=?)",
        (repo, file_path),
    )

    for sym in symbols:
        sym_id = sym.get("id")
        if sym_id is None:
            continue
        if sym.get("kind") not in {"function", "method"}:
            continue
        start_b = sym.get("start_byte", 0)
        end_b = sym.get("end_byte", 0)
        callee_names = _find_calls_in_range(tree.root_node, start_b, end_b, lang_name=lang_name or "", source_bytes=source_bytes)
        for callee_name in dict.fromkeys(callee_names):
            # Attempt to resolve file
            row = conn.execute(
                "SELECT file FROM symbols WHERE repo=? AND name=? LIMIT 1",
                (repo, callee_name),
            ).fetchone()
            callee_file = row["file"] if row else None
            conn.execute(
                "INSERT OR IGNORE INTO edges (caller_id, callee_name, callee_file) VALUES (?, ?, ?)",
                (sym_id, callee_name, callee_file),
            )

    conn.commit()


def get_callers(conn: sqlite3.Connection, name: str, repo: str) -> list[dict]:
    """Return symbols that call the function named `name` in `repo`."""
    rows = conn.execute("""
        SELECT s.id, s.repo, s.file, s.name, s.kind, s.start_byte, s.end_byte, s.signature
        FROM edges e
        JOIN symbols s ON e.caller_id = s.id
        WHERE e.callee_name = ? AND s.repo = ?
    """, (name, repo)).fetchall()
    return [dict(r) for r in rows]


def get_callees(conn: sqlite3.Connection, name: str, repo: str) -> list[dict]:
    """Return names called by the function named `name` in `repo`."""
    rows = conn.execute("""
        SELECT e.callee_name, e.callee_file
        FROM edges e
        JOIN symbols s ON e.caller_id = s.id
        WHERE s.name = ? AND s.repo = ?
    """, (name, repo)).fetchall()
    return [{"name": r["callee_name"], "file": r["callee_file"]} for r in rows]


def find_circular_deps(repo: str, db_path: str) -> dict:
    """
    Detect circular dependencies via DFS over the edges adjacency map.
    Returns {"cycles": [["a.py", "b.py", "a.py"], ...], "count": N}
    Cap at 20 cycles. Return {"cycles": [], "count": 0} if none.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # 1. Build adjacency map: file -> set of files it calls
        adj: dict[str, set[str]] = {}
        edge_rows = conn.execute(
            """
            SELECT s.file AS caller_file, e.callee_file
            FROM edges e
            JOIN symbols s ON e.caller_id = s.id
            WHERE s.repo = ? AND e.callee_file IS NOT NULL
            """,
            (repo,),
        ).fetchall()

        for row in edge_rows:
            caller_file = row["caller_file"]
            callee_file = row["callee_file"]
            if caller_file and callee_file:
                adj.setdefault(caller_file, set()).add(callee_file)

        # 2. DFS to find cycles
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()  # Current recursion stack

        def dfs(node: str, path: list[str]) -> None:
            """DFS with cycle detection via recursion stack."""
            if len(cycles) >= 20:  # Cap at 20 cycles
                return

            if node in rec_stack:
                # Found a cycle: extract from path
                if node in path:
                    cycle_start_idx = path.index(node)
                    cycle = path[cycle_start_idx:] + [node]
                    # Normalize cycle to start with lexicographically smallest element
                    if cycle:
                        body = cycle[:-1]
                        min_idx = body.index(min(body))
                        rotated = body[min_idx:] + body[:min_idx]
                        normalized = rotated + [rotated[0]]
                        # Dedup: don't add if we've already recorded this cycle
                        if normalized not in cycles:
                            cycles.append(normalized)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adj.get(node, set()):
                dfs(neighbor, path)

            path.pop()
            rec_stack.remove(node)

        # Start DFS from each unvisited node
        for node in adj:
            if node not in visited:
                dfs(node, [])

        return {
            "cycles": cycles,
            "count": len(cycles),
        }
    finally:
        conn.close()
