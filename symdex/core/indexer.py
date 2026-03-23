# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import hashlib
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional
from symdex.core.parser import parse_file
from symdex.core.ignore import build_ignore_spec
from symdex.core.naming import derive_repo_name
from symdex.core.token_metrics import count_lines_of_code
from symdex.graph.call_graph import extract_edges as _extract_edges
from symdex.core.route_extractor import extract_routes as _extract_routes
from symdex.core.storage import (
    get_connection,
    get_db_path,
    get_file_hash,
    get_repo_summary,
    upsert_file,
    upsert_symbol,
    upsert_embedding,
    delete_file_routes,
    upsert_route,
)

logger = logging.getLogger(__name__)
_OPTIONAL_EMBEDDING_WARNINGS: set[str] = set()
_ROUTE_LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".php": "php",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cs": "csharp",
    ".rb": "ruby",
    ".ex": "elixir",
    ".exs": "elixir",
    ".rs": "rust",
}


def _warn_optional_embedding_once(message: str) -> None:
    if message in _OPTIONAL_EMBEDDING_WARNINGS:
        return
    _OPTIONAL_EMBEDDING_WARNINGS.add(message)
    logger.warning(message)

def _embed_symbols(
    conn,
    repo: str,
    file_path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> None:
    """Compute and store embeddings for all symbols in repo+file.

    Queries symbols already inserted for this repo/file, computes an embedding
    text from signature, docstring, and name, then calls embed_for_index and stores
    the result via upsert_embedding. Failures per symbol are logged and skipped
    so that a single bad symbol never aborts indexing.

    Note: Existing indexed DBs have pre-prefix vectors. For improved recall with
    asymmetric models (nomic-embed-text, MiniLM), re-index your repositories.
    """
    from symdex.search.semantic import embed_for_index  # local import avoids circular dep

    rows = conn.execute(
        "SELECT id, name, signature, docstring FROM symbols WHERE repo=? AND file=?",
        (repo, file_path),
    ).fetchall()

    for row in rows:
        symbol_id = row["id"]
        name = row["name"] or ""
        signature = row["signature"] or ""
        docstring = row["docstring"] or ""
        embed_input = f"{signature}\n{docstring}\n{name}".strip()
        try:
            vec = embed_for_index(embed_input, progress_callback=progress_callback)
            upsert_embedding(conn, symbol_id, vec)
        except RuntimeError as exc:
            message = str(exc)
            if "symdex[" in message:
                _warn_optional_embedding_once(message)
                return
            logger.warning("Embedding failed for symbol %s (id=%s): %s", name, symbol_id, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embedding failed for symbol %s (id=%s): %s", name, symbol_id, exc)


_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", "dist", "build", ".mypy_cache", ".pytest_cache",
}

_SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf",
    ".zip", ".tar", ".gz", ".whl", ".egg",
    ".db", ".sqlite", ".sqlite3",
    ".lock",
}

_VOYAGE_ASSET_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".webp", ".bmp",
}


@dataclass
class IndexResult:
    repo: str
    db_path: str
    indexed_count: int
    skipped_count: int
    summary: dict


def get_git_branch(path: str) -> str | None:
    """Return the current git branch name for path, or None if not a git repo / detached HEAD."""
    try:
        result = subprocess.run(
            ["git", "-C", path, "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        branch = result.stdout.strip()
        if not branch:
            return None
        # Sanitize: replace path separators and special chars with '-', lowercase
        sanitized = re.sub(r"[/\\@\s]+", "-", branch).lower().strip("-")
        return sanitized or None
    except Exception:  # noqa: BLE001
        return None


def _file_hash_and_loc(path: str) -> tuple[str, int]:
    with open(path, "rb") as fh:
        data = fh.read()
    h = hashlib.sha256(data)
    text = data.decode("utf-8", errors="ignore")
    return h.hexdigest(), count_lines_of_code(text)


def _voyage_multimodal_enabled() -> bool:
    return (
        os.environ.get("SYMDEX_EMBED_BACKEND", "local").strip().lower() == "voyage"
        and os.environ.get("SYMDEX_VOYAGE_MULTIMODAL", "0").strip().lower() in {"1", "true", "yes", "on"}
    )


def index_folder(
    path: str,
    repo: str | None = None,
    name: str | None = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> IndexResult:
    """Index all source files in path. Skips unchanged files via SHA256 hash.

    Args:
        path: Absolute path to the directory to index.
        repo: Repo name override. When omitted, a stable repo name is derived
            from the folder name, git branch (if available), and path hash.
        name: Backward-compatible alias for repo.

    Returns:
        IndexResult with repo, db_path, indexed_count, skipped_count.
    """
    abs_path = os.path.abspath(path)
    repo = derive_repo_name(abs_path, repo=repo, name=name)
    db_path = get_db_path(repo)
    conn = get_connection(db_path)

    indexed = 0
    skipped = 0
    errored = 0
    ignore_spec = build_ignore_spec(abs_path)

    try:
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in _SKIP_EXTENSIONS and not (_voyage_multimodal_enabled() and ext in _VOYAGE_ASSET_EXTENSIONS):
                    continue

                abs_file = os.path.join(dirpath, filename)
                rel_file = os.path.relpath(abs_file, path).replace("\\", "/")

                # Skip files matching ignore patterns
                if ignore_spec.match_file(rel_file):
                    continue

                try:
                    current_hash, line_count = _file_hash_and_loc(abs_file)
                except OSError as exc:
                    logger.warning("Skipping %s: %s", abs_file, exc)
                    errored += 1
                    continue

                stored_hash = get_file_hash(conn, repo, rel_file)
                if stored_hash == current_hash:
                    skipped += 1
                    continue

                conn.execute(
                    "DELETE FROM symbols WHERE repo=? AND file=?", (repo, rel_file)
                )

                if _voyage_multimodal_enabled() and ext in _VOYAGE_ASSET_EXTENSIONS:
                    from symdex.search.semantic import embed_asset_for_index

                    asset_name = rel_file
                    try:
                        upsert_symbol(
                            conn,
                            repo=repo,
                            file=rel_file,
                            name=asset_name,
                            kind="asset",
                            start_byte=0,
                            end_byte=0,
                            signature=None,
                            docstring=None,
                        )
                        vec = embed_asset_for_index(abs_file, progress_callback=progress_callback)
                        asset_id = conn.execute(
                            "SELECT id FROM symbols WHERE repo=? AND file=? AND name=?",
                            (repo, rel_file, asset_name),
                        ).fetchone()["id"]
                        upsert_embedding(conn, asset_id, vec)
                    except RuntimeError as exc:
                        message = str(exc)
                        if "symdex[" in message:
                            _warn_optional_embedding_once(message)
                            continue
                        logger.warning("Asset embedding failed for %s: %s", abs_file, exc)
                        errored += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Asset embedding failed for %s: %s", abs_file, exc)
                        errored += 1
                else:
                    symbols = parse_file(abs_file, path)
                    for sym in symbols:
                        upsert_symbol(
                            conn,
                            repo=repo,
                            file=rel_file,
                            name=sym["name"],
                            kind=sym["kind"],
                            start_byte=sym["start_byte"],
                            end_byte=sym["end_byte"],
                            signature=sym.get("signature"),
                            docstring=sym.get("docstring"),
                        )
                    _embed_symbols(conn, repo=repo, file_path=rel_file, progress_callback=progress_callback)
                    sym_rows = conn.execute(
                        "SELECT id, name, start_byte, end_byte FROM symbols WHERE repo=? AND file=?",
                        (repo, rel_file),
                    ).fetchall()
                    _extract_edges(conn, repo=repo, file_path=rel_file, abs_file=abs_file, symbols=[dict(r) for r in sym_rows])
                    file_lang = _ROUTE_LANG_MAP.get(ext)
                    if file_lang:
                        try:
                            with open(abs_file, "rb") as rh:
                                raw = rh.read()
                            file_routes = _extract_routes(raw, rel_file, file_lang)
                            delete_file_routes(conn, repo=repo, file=rel_file)
                            for route in file_routes:
                                upsert_route(
                                    conn,
                                    repo=repo,
                                    file=rel_file,
                                    method=route.method,
                                    path=route.path,
                                    handler=route.handler,
                                    start_byte=route.start_byte,
                                    end_byte=route.end_byte,
                                )
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Route extraction failed for %s: %s", abs_file, exc)
                upsert_file(
                    conn,
                    repo=repo,
                    path=rel_file,
                    file_hash=current_hash,
                    line_count=line_count,
                )
                indexed += 1
        conn.commit()
    finally:
        conn.close()

    summary = get_repo_summary(repo, db_path)
    summary["skipped"] = skipped
    summary["errored"] = errored
    return IndexResult(
        repo=repo,
        db_path=db_path,
        indexed_count=indexed,
        skipped_count=skipped,
        summary=summary,
    )


def invalidate(repo: str, file: str | None = None) -> int:
    """Delete hash records (and their symbols) for the repo or a specific file.

    Returns count of file records deleted.
    """
    db_path = get_db_path(repo)
    conn = get_connection(db_path)
    try:
        if file:
            cursor = conn.execute(
                "DELETE FROM files WHERE repo=? AND path=?", (repo, file)
            )
            conn.execute(
                "DELETE FROM symbols WHERE repo=? AND file=?", (repo, file)
            )
        else:
            cursor = conn.execute("DELETE FROM files WHERE repo=?", (repo,))
            conn.execute("DELETE FROM symbols WHERE repo=?", (repo,))
        count = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    return count
