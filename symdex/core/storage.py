# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import datetime
import fnmatch
import json
import os
import sqlite3
import pathlib
from typing import Optional

import numpy as np
import sqlite_vec

from symdex.core.state import get_state_paths, resolve_registry_value, serialize_registry_value

DEFAULT_SYMBOL_LIMIT = 20


_EXT_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rb": "ruby",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".ex": "elixir",
    ".exs": "elixir",
    ".php": "php",
    ".dart": "dart",
    ".swift": "swift",
    ".mjs": "javascript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".md": "markdown",
    ".markdown": "markdown",
}


def _ensure_files_line_count_column(conn: sqlite3.Connection) -> None:
    """Add files.line_count for older databases that do not have it yet."""
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(files)").fetchall()
    }
    if "line_count" not in columns:
        conn.execute("ALTER TABLE files ADD COLUMN line_count INTEGER NOT NULL DEFAULT 0")
        conn.commit()


def _try_load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Best-effort sqlite-vec load; returns True when extension is active."""
    enable_load_extension = getattr(conn, "enable_load_extension", None)
    if not callable(enable_load_extension):
        return False

    try:
        enable_load_extension(True)
        sqlite_vec.load(conn)
        return True
    except (sqlite3.Error, AttributeError):
        return False
    finally:
        try:
            enable_load_extension(False)
        except (sqlite3.Error, AttributeError):
            pass


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open or create a SQLite DB, apply schema, enable WAL mode."""
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    _try_load_sqlite_vec(conn)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    schema_path = pathlib.Path(__file__).parent / "schema.sql"
    conn.executescript(schema_path.read_text())
    _ensure_files_line_count_column(conn)
    conn.commit()
    return conn


def upsert_symbol(
    conn: sqlite3.Connection,
    repo: str,
    file: str,
    name: str,
    kind: str,
    start_byte: int,
    end_byte: int,
    signature: Optional[str],
    docstring: Optional[str],
) -> int:
    """Insert or replace a symbol. Returns the row id."""
    with conn:
        conn.execute(
            "DELETE FROM symbols WHERE repo=? AND file=? AND name=?",
            (repo, file, name),
        )
        cursor = conn.execute(
            """
        INSERT INTO symbols (repo, file, name, kind, start_byte, end_byte, signature, docstring)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (repo, file, name, kind, start_byte, end_byte, signature, docstring),
        )
    return cursor.lastrowid


def upsert_file(
    conn: sqlite3.Connection,
    repo: str,
    path: str,
    file_hash: str,
    line_count: int = 0,
) -> None:
    """Insert or replace a file hash record."""
    conn.execute(
        "INSERT OR REPLACE INTO files (repo, path, hash, line_count) VALUES (?, ?, ?, ?)",
        (repo, path, file_hash, line_count),
    )
    conn.commit()


def get_file_hash(conn: sqlite3.Connection, repo: str, path: str) -> Optional[str]:
    """Return stored SHA256 hash for (repo, path), or None if not indexed."""
    row = conn.execute(
        "SELECT hash FROM files WHERE repo=? AND path=?", (repo, path)
    ).fetchone()
    return row["hash"] if row else None


def query_symbols(
    conn: sqlite3.Connection,
    repo: Optional[str],
    name_pattern: str,
    kind: Optional[str] = None,
    limit: int = DEFAULT_SYMBOL_LIMIT,
) -> list[dict]:
    """Prefix search, falling back to contains search. Returns list of dicts."""
    kind_clause = " AND kind=?" if kind else ""
    repo_clause = " AND repo=?" if repo else ""

    def _run(pattern: str) -> list:
        sql = (
            "SELECT name, file, kind, start_byte, end_byte, signature, docstring "
            "FROM symbols WHERE name LIKE ?" + repo_clause + kind_clause + " LIMIT ?"
        )
        args: list = [pattern]
        if repo:
            args.append(repo)
        if kind:
            args.append(kind)
        args.append(limit)
        return conn.execute(sql, args).fetchall()

    rows = _run(f"{name_pattern}%")
    if not rows:
        rows = _run(f"%{name_pattern}%")
    return [dict(r) for r in rows]


def query_file_symbols(
    conn: sqlite3.Connection, repo: str, file: str
) -> list[dict]:
    """Return all symbols in a specific file, ordered by byte offset."""
    rows = conn.execute(
        "SELECT name, file, kind, start_byte, end_byte, signature, docstring "
        "FROM symbols WHERE repo=? AND file=? ORDER BY start_byte",
        (repo, file),
    ).fetchall()
    return [dict(r) for r in rows]


def search_text_in_index(
    conn: sqlite3.Connection,
    repo: str,
    query: str,
    repo_root: str,
    file_pattern: Optional[str] = None,
) -> list[dict]:
    """Scan indexed files on disk for lines matching query (case-insensitive).

    Returns [{file, line, text}]. Max 5 matches per file, 100 total.
    """
    rows = conn.execute(
        "SELECT DISTINCT path FROM files WHERE repo=?", (repo,)
    ).fetchall()

    results = []
    query_lower = query.lower()

    for row in rows:
        rel_path = row["path"]
        if file_pattern and not fnmatch.fnmatch(rel_path, file_pattern):
            continue

        abs_path = os.path.join(repo_root, rel_path)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                file_matches = 0
                for line_num, line in enumerate(fh, start=1):
                    if query_lower in line.lower():
                        results.append({"file": rel_path, "line": line_num, "text": line.rstrip()})
                        file_matches += 1
                        if file_matches >= 5:
                            break
        except OSError:
            continue

        if len(results) >= 100:
            break

    return results


def get_db_path(repo_name: str) -> str:
    """Return path to the active state directory's repo database."""
    state = get_state_paths()
    os.makedirs(state.base_dir, exist_ok=True)
    return os.path.join(state.base_dir, f"{repo_name.lower()}.db")


def get_registry_path() -> str:
    """Return path to the active state directory's registry database."""
    state = get_state_paths()
    os.makedirs(state.base_dir, exist_ok=True)
    return state.registry_db_path


def get_registry_json_path() -> str:
    """Return path to the human-readable registry manifest."""
    return os.path.join(os.path.dirname(get_registry_path()), "registry.json")


def _current_timestamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_repo_row(row: dict, resolve_paths: bool = True) -> dict:
    if not resolve_paths:
        return dict(row)
    state = get_state_paths()
    normalized = dict(row)
    normalized["root_path"] = resolve_registry_value(normalized["root_path"], state)
    normalized["db_path"] = resolve_registry_value(normalized["db_path"], state)
    return normalized


def _write_registry_manifest(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT name, root_path, db_path, last_indexed FROM repos ORDER BY name"
    ).fetchall()
    manifest_path = get_registry_json_path()
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump([dict(row) for row in rows], fh, indent=2)
        fh.write("\n")


def _get_registry_connection() -> sqlite3.Connection:
    """Open the central registry DB, create repos table if needed."""
    conn = sqlite3.connect(get_registry_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repos (
            name         TEXT PRIMARY KEY,
            root_path    TEXT NOT NULL,
            db_path      TEXT NOT NULL,
            last_indexed DATETIME
        )
        """
    )
    conn.commit()
    return conn


def upsert_repo(name: str, root_path: str, db_path: str) -> None:
    """Register or update a repo in the active registry."""
    name = name.lower()
    state = get_state_paths()
    stored_root = serialize_registry_value(root_path, state)
    stored_db = serialize_registry_value(db_path, state)
    timestamp = _current_timestamp()
    conn = _get_registry_connection()
    try:
        conn.execute(
            """
            INSERT INTO repos (name, root_path, db_path, last_indexed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                root_path    = excluded.root_path,
                db_path      = excluded.db_path,
                last_indexed = excluded.last_indexed
            """,
            (name, stored_root, stored_db, timestamp),
        )
        conn.commit()
        _write_registry_manifest(conn)
    finally:
        conn.close()


def query_repos(resolve_paths: bool = True) -> list[dict]:
    """Return all registered repos from the active registry, ordered by name."""
    conn = _get_registry_connection()
    try:
        rows = conn.execute(
            "SELECT name, root_path, db_path, last_indexed FROM repos ORDER BY name"
        ).fetchall()
        return [_normalize_repo_row(dict(r), resolve_paths=resolve_paths) for r in rows]
    finally:
        conn.close()


def get_stale_repos() -> list[dict]:
    """Return registry entries whose root_path or db_path are gone."""
    stale = []
    for row in query_repos():
        root_missing = not os.path.isdir(row["root_path"])
        db_missing = not os.path.isfile(row["db_path"])
        if root_missing or db_missing:
            stale.append(row)
    return stale


def remove_repo(name: str) -> None:
    """Delete a repo's registry entry and its .db file."""
    state = get_state_paths()
    conn = _get_registry_connection()
    try:
        row = conn.execute(
            "SELECT db_path FROM repos WHERE name=?", (name.lower(),)
        ).fetchone()
        if row:
            db_path = resolve_registry_value(row["db_path"], state)
            conn.execute("DELETE FROM repos WHERE name=?", (name.lower(),))
            conn.commit()
            _write_registry_manifest(conn)
            if os.path.isfile(db_path):
                os.remove(db_path)
    finally:
        conn.close()


def upsert_embedding(conn: sqlite3.Connection, symbol_id: int, embedding: np.ndarray) -> None:
    """Store float32 embedding blob for a symbol."""
    blob = embedding.astype("float32").tobytes()
    conn.execute("UPDATE symbols SET embedding = ? WHERE id = ?", (blob, symbol_id))
    conn.commit()


def query_symbols_with_embeddings(
    conn: sqlite3.Connection, repo: str | None = None
) -> list[dict]:
    """Return all symbols that have a non-NULL embedding."""
    sql = (
        "SELECT id, repo, file, name, kind, start_byte, end_byte, "
        "signature, docstring, embedding FROM symbols WHERE embedding IS NOT NULL"
    )
    params: list = []
    if repo:
        sql += " AND repo = ?"
        params.append(repo)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def upsert_route(
    conn: sqlite3.Connection,
    repo: str,
    file: str,
    method: str,
    path: str,
    handler: Optional[str],
    start_byte: int,
    end_byte: int,
) -> None:
    """Insert or ignore an HTTP route record."""
    conn.execute(
        """
        INSERT OR IGNORE INTO routes (repo, file, method, path, handler, start_byte, end_byte)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (repo, file, method.upper(), path, handler or "", start_byte, end_byte),
    )


def query_routes(
    conn: sqlite3.Connection,
    repo: str,
    method: Optional[str] = None,
    path_contains: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Query HTTP routes for a repo with optional method and path filters."""
    sql = "SELECT * FROM routes WHERE repo=?"
    params: list = [repo]
    if method:
        sql += " AND method=?"
        params.append(method.upper())
    if path_contains:
        sql += " AND path LIKE ?"
        params.append(f"%{path_contains}%")
    sql += " ORDER BY file, start_byte LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def delete_file_routes(conn: sqlite3.Connection, repo: str, file: str) -> None:
    """Remove all route records for a specific file in a repo."""
    conn.execute("DELETE FROM routes WHERE repo=? AND file=?", (repo, file))


def _repo_language_distribution(conn: sqlite3.Connection, repo: str) -> dict[str, int]:
    """Infer language distribution from indexed file extensions."""
    rows = conn.execute(
        "SELECT DISTINCT path FROM files WHERE repo=?",
        (repo,),
    ).fetchall()
    language_distribution: dict[str, int] = {}
    for row in rows:
        path = row["path"]
        ext = os.path.splitext(path)[1].lower()
        language = _EXT_TO_LANGUAGE.get(ext, "other")
        language_distribution[language] = language_distribution.get(language, 0) + 1
    return dict(sorted(language_distribution.items()))


def get_repo_summary(repo: str, db_path: str) -> dict:
    """Return code-summary counts for a repo."""
    conn = get_connection(db_path)
    try:
        file_count = conn.execute(
            "SELECT COUNT(DISTINCT path) FROM files WHERE repo=?",
            (repo,),
        ).fetchone()[0]
        symbol_count = conn.execute(
            "SELECT COUNT(*) FROM symbols WHERE repo=?",
            (repo,),
        ).fetchone()[0]
        lines_of_code = conn.execute(
            "SELECT COALESCE(SUM(line_count), 0) FROM files WHERE repo=?",
            (repo,),
        ).fetchone()[0]
        kind_rows = conn.execute(
            "SELECT kind, COUNT(*) AS count FROM symbols WHERE repo=? GROUP BY kind",
            (repo,),
        ).fetchall()
        kind_counts = {row["kind"]: row["count"] for row in kind_rows}
        routes_count = conn.execute(
            "SELECT COUNT(*) FROM routes WHERE repo=?",
            (repo,),
        ).fetchone()[0]
        language_distribution = _repo_language_distribution(conn, repo)
    finally:
        conn.close()

    return {
        "repo": repo,
        "file_count": file_count,
        "symbol_count": symbol_count,
        "lines_of_code": lines_of_code,
        "functions": kind_counts.get("function", 0),
        "classes": kind_counts.get("class", 0),
        "methods": kind_counts.get("method", 0),
        "constants": kind_counts.get("constant", 0),
        "variables": kind_counts.get("variable", 0),
        "routes": routes_count,
        "language_distribution": language_distribution,
    }


def get_index_status(repo: str, db_path: str) -> dict:
    """
    Returns index status for a repo.

    Fields:
    - repo: str
    - symbol_count: int (count of rows in symbols table for this repo)
    - file_count: int (count of rows in files table for this repo)
    - last_indexed: str ISO8601 UTC (max indexed_at from files table, or None)
    - age_seconds: float (seconds since last_indexed, or None)
    - stale: bool (True if any file's mtime > last_indexed, False otherwise)
    - watcher_active: bool (True if ~/.symdex-mcp/{repo}.watch.pid exists)
    """
    import datetime
    from pathlib import Path

    conn = get_connection(db_path)
    try:
        # Count symbols for this repo
        symbol_count = conn.execute(
            "SELECT COUNT(*) FROM symbols WHERE repo=?", (repo,)
        ).fetchone()[0]

        # Count distinct files for this repo
        file_count = conn.execute(
            "SELECT COUNT(DISTINCT path) FROM files WHERE repo=?", (repo,)
        ).fetchone()[0]

        lines_of_code = conn.execute(
            "SELECT COALESCE(SUM(line_count), 0) FROM files WHERE repo=?",
            (repo,),
        ).fetchone()[0]

        # Get last_indexed timestamp
        row = conn.execute(
            "SELECT MAX(indexed_at) FROM files WHERE repo=?", (repo,)
        ).fetchone()
        last_indexed_str = row[0] if row[0] else None

        # Calculate age_seconds
        age_seconds = None
        if last_indexed_str:
            # Parse ISO8601 datetime from SQLite (in UTC).
            # Use fromisoformat and then treat as UTC by replacing tzinfo.
            last_indexed_dt = datetime.datetime.fromisoformat(last_indexed_str)
            # SQLite's datetime('now') is UTC, so we need to use UTC now for comparison
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            age_seconds = (now_utc - last_indexed_dt.replace(tzinfo=datetime.timezone.utc)).total_seconds()

        # Check if any file is stale (mtime > last_indexed)
        stale = False
        if last_indexed_str:
            # SQLite stores datetime('now') as UTC string.
            # File mtimes are in local time (UNIX timestamp).
            # The safest way: query the current time from SQLite in the same way
            # so we know the system's interpretation.
            # Actually, we need to compare: is the file newer than when it was indexed?
            # Get the timestamp SQLite recorded for the index.
            # Parse the string and convert to UNIX timestamp assuming it's UTC.
            last_indexed_dt = datetime.datetime.fromisoformat(last_indexed_str)
            # This datetime is naive, but represents UTC per SQLite's datetime('now').
            # Convert to UNIX timestamp by treating as UTC:
            # Use a timezone-aware datetime to properly convert UTC to UNIX timestamp.
            last_indexed_dt_utc = last_indexed_dt.replace(
                tzinfo=datetime.timezone.utc
            )
            last_indexed_timestamp = last_indexed_dt_utc.timestamp()

            # Get resolved root_path from the active registry
            root_path = None
            repo_entry = next((row for row in query_repos() if row["name"] == repo), None)
            if repo_entry:
                root_path = repo_entry["root_path"]

            if root_path:
                # Check all indexed files
                file_rows = conn.execute(
                    "SELECT DISTINCT path FROM files WHERE repo=?", (repo,)
                ).fetchall()
                for file_row in file_rows:
                    rel_path = file_row["path"]
                    abs_path = os.path.join(root_path, rel_path)
                    try:
                        file_mtime = os.path.getmtime(abs_path)
                        # Compare timestamps: if file was modified after indexing, it's stale
                        if file_mtime > last_indexed_timestamp:
                            stale = True
                            break
                    except OSError:
                        # File deleted or inaccessible
                        stale = True
                        break

        # Check if watcher is active
        watch_pid_path = Path.home() / ".symdex-mcp" / f"{repo}.watch.pid"
        watcher_active = watch_pid_path.exists()

    finally:
        conn.close()

    return {
        "repo": repo,
        "symbol_count": symbol_count,
        "file_count": file_count,
        "lines_of_code": lines_of_code,
        "last_indexed": last_indexed_str,
        "age_seconds": age_seconds,
        "stale": stale,
        "watcher_active": watcher_active,
    }


def get_repo_stats(repo: str, db_path: str) -> dict:
    """
    Returns comprehensive statistics for a repo.

    Fields:
    - repo: str
    - symbol_count: int (total symbols in repo)
    - file_count: int (total files indexed in repo)
    - language_distribution: dict (language -> count of symbols)
    - top_fan_in: list[dict] (top 5 files with most dependents; each: {name, dependents})
    - top_fan_out: list[dict] (top 5 files with most outgoing calls; each: {name, calls})
    - orphan_files: list[str] (files with no symbols and no edges)
    - circular_dep_count: int (number of distinct files in circular dependencies, or 0 if not computed)
    - edge_count: int (total edges for this repo)
    """
    conn = get_connection(db_path)
    try:
        summary = get_repo_summary(repo, db_path)
        symbol_count = summary["symbol_count"]
        file_count = summary["file_count"]
        lines_of_code = summary["lines_of_code"]
        lang_dist = summary["language_distribution"]

        # 4. top_fan_in: files with most dependents (filtered to this repo via caller)
        fan_in_rows = conn.execute(
            "SELECT e.callee_file, COUNT(*) as dependents FROM edges e "
            "JOIN symbols s ON e.caller_id = s.id "
            "WHERE e.callee_file IS NOT NULL AND s.repo=? "
            "GROUP BY e.callee_file ORDER BY dependents DESC LIMIT 5",
            (repo,),
        ).fetchall()
        top_fan_in = [
            {"name": row["callee_file"], "dependents": row["dependents"]}
            for row in fan_in_rows
        ]

        # 5. top_fan_out: files with most outgoing calls
        # Join symbols to edges via caller_id, group by file, count edges
        fan_out_rows = conn.execute(
            "SELECT s.file, COUNT(*) as calls FROM edges e "
            "JOIN symbols s ON e.caller_id = s.id "
            "WHERE s.repo=? GROUP BY s.file ORDER BY calls DESC LIMIT 5",
            (repo,),
        ).fetchall()
        top_fan_out = [
            {"name": row["file"], "calls": row["calls"]}
            for row in fan_out_rows
        ]

        # 6. orphan_files: files with no symbols and no edges
        orphan_rows = conn.execute(
            "SELECT f.path FROM files f "
            "WHERE f.repo=? "
            "AND NOT EXISTS (SELECT 1 FROM symbols s WHERE s.repo=f.repo AND s.file=f.path) "
            "AND NOT EXISTS ("
            "SELECT 1 FROM edges e JOIN symbols s ON e.caller_id=s.id "
            "WHERE e.callee_file=f.path AND s.repo=f.repo"
            ")",
            (repo,),
        ).fetchall()
        orphan_files = [row["path"] for row in orphan_rows]

        # 7. circular_dep_count: count distinct files involved in cycles
        # Import and call find_circular_deps to get the actual count
        from symdex.graph.call_graph import find_circular_deps
        circular_deps_result = find_circular_deps(repo, db_path)
        circular_dep_count = circular_deps_result.get("count", 0)

        # 8. edge_count: total edges for this repo
        edge_count = conn.execute(
            "SELECT COUNT(*) FROM edges e "
            "WHERE e.caller_id IN (SELECT id FROM symbols WHERE repo=?)",
            (repo,),
        ).fetchone()[0]

    finally:
        conn.close()

    return {
        "repo": repo,
        "symbol_count": symbol_count,
        "file_count": file_count,
        "lines_of_code": lines_of_code,
        "language_distribution": lang_dist,
        "top_fan_in": top_fan_in,
        "top_fan_out": top_fan_out,
        "orphan_files": orphan_files,
        "circular_dep_count": circular_dep_count,
        "edge_count": edge_count,
    }
