# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from symdex.core.storage import search_text_in_index, get_connection, get_db_path


def search_text(
    query: str,
    repo: str,
    repo_root: str,
    file_pattern: str | None = None,
) -> list[dict]:
    """Search text across indexed files in a repo.

    Args:
        query: Case-insensitive substring to search for.
        repo: Repo name (used to look up DB).
        repo_root: Absolute path to the repo root on disk.
        file_pattern: Optional glob pattern to filter files (e.g. '*.py').

    Returns:
        List of {file, line, text} dicts. Max 5 per file, 100 total.
    """
    db_path = get_db_path(repo)
    conn = get_connection(db_path)
    try:
        results = search_text_in_index(
            conn, repo=repo, query=query,
            repo_root=repo_root, file_pattern=file_pattern
        )
    finally:
        conn.close()
    return results
