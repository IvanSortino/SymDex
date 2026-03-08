# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import sqlite3
from symdex.core.storage import query_symbols


def search_symbols(
    conn: sqlite3.Connection,
    repo: str | None,
    query: str,
    kind: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search symbols by name. Prefix match first, falls back to contains.

    Args:
        conn: Open SQLite connection.
        repo: Repo name filter, or None to search all repos.
        query: Symbol name query string.
        kind: Optional kind filter ('function', 'class', 'method').
        limit: Max results to return.

    Returns:
        List of symbol dicts.
    """
    return query_symbols(conn, repo=repo, name_pattern=query, kind=kind, limit=limit)
