# symdex/graph/registry.py
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

from __future__ import annotations

from symdex.core.storage import (
    get_connection,
    get_db_path,
    query_repos,
    upsert_repo,
)
from symdex.search.symbol_search import search_symbols as _search_symbols


def register_repo(name: str, root_path: str) -> None:
    """Register a repo in the central registry."""
    db_path = get_db_path(name)
    upsert_repo(name, root_path=root_path, db_path=db_path)


def list_all_repos() -> list[dict]:
    """Return all registered repos as dicts with name/root_path/db_path/last_indexed."""
    return query_repos()


def get_repo_db(name: str) -> str | None:
    """Return db_path for the named repo, or None if not registered."""
    for r in query_repos():
        if r["name"] == name:
            return r["db_path"]
    return None


def search_across_repos(
    query: str,
    kind: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search symbols in all registered repos. Adds 'repo' field to each result.

    Results are deduplicated by (repo, file, name).
    """
    repos = query_repos()
    seen: set[tuple[str, str, str]] = set()
    aggregated: list[dict] = []

    for repo_info in repos:
        repo_name = repo_info["name"]
        db_path = repo_info["db_path"]
        try:
            conn = get_connection(db_path)
            try:
                results = _search_symbols(conn, repo=repo_name, query=query, kind=kind, limit=limit)
            finally:
                conn.close()
        except Exception:
            continue

        for sym in results:
            key = (repo_name, sym.get("file", ""), sym.get("name", ""))
            if key not in seen:
                seen.add(key)
                aggregated.append({**sym, "repo": repo_name})

    return aggregated
