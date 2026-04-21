# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from __future__ import annotations

import os
import re
from pathlib import PurePosixPath
from typing import Iterable

from symdex.core.quality import attach_quality_to_items, build_item_quality
from symdex.core.storage import (
    get_connection,
    get_db_path,
    get_index_status,
    query_repos,
    query_repo_has_embeddings,
    query_routes,
    search_text_in_index,
)
from symdex.core.token_metrics import DEFAULT_TOKENIZER, count_token_metrics
from symdex.graph.call_graph import get_callees, get_callers
from symdex.search.symbol_search import search_symbols

DEFAULT_CONTEXT_PACK_BUDGET = 6000
PACK_FILTERS = {"symbols", "text", "routes", "semantic", "graph", "docs", "tests"}
TYPE_TO_FILTER = {
    "symbol": "symbols",
    "text": "text",
    "route": "routes",
    "semantic": "semantic",
    "graph_neighbor": "graph",
    "doc": "docs",
    "test": "tests",
}
SOURCE_MAX_BYTES = 3000


def normalize_pack_filters(
    include: Iterable[str] | str | None,
    exclude: Iterable[str] | str | None,
) -> tuple[set[str], set[str], list[str]]:
    warnings: list[str] = []

    def _normalize(raw: Iterable[str] | str | None, label: str) -> set[str]:
        if raw is None:
            return set()
        values = raw.split(",") if isinstance(raw, str) else list(raw)
        normalized = {value.strip().lower() for value in values if value and value.strip()}
        unknown = normalized - PACK_FILTERS
        for name in sorted(unknown):
            warnings.append(f"unknown {label} filter ignored: {name}")
        return normalized & PACK_FILTERS

    return _normalize(include, "include"), _normalize(exclude, "exclude"), warnings


def build_context_pack(
    repo: str,
    query: str,
    token_budget: int = DEFAULT_CONTEXT_PACK_BUDGET,
    include: Iterable[str] | str | None = None,
    exclude: Iterable[str] | str | None = None,
) -> dict:
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")

    repo_entry = _repo_entry(repo)
    if repo_entry is None:
        raise ValueError(f"Repo not indexed: {repo}")

    requested_budget = max(1, int(token_budget or DEFAULT_CONTEXT_PACK_BUDGET))
    include_filters, exclude_filters, warnings = normalize_pack_filters(include, exclude)
    root = repo_entry["root_path"]
    db_path = get_db_path(repo)
    conn = get_connection(db_path)
    try:
        has_embeddings = query_repo_has_embeddings(conn, repo)
        try:
            index_status = get_index_status(repo, db_path)
        except Exception:  # noqa: BLE001
            index_status = None

        candidates: list[dict] = []
        candidates.extend(_gather_symbol_candidates(conn, repo, root, query, has_embeddings, index_status))
        candidates.extend(_gather_text_candidates(conn, repo, root, query, has_embeddings, index_status))
        candidates.extend(_gather_route_candidates(conn, repo, root, query, has_embeddings, index_status))
        if has_embeddings:
            candidates.extend(_gather_semantic_candidates(conn, repo, root, query, has_embeddings, index_status, warnings))
        elif _filter_allowed("semantic", include_filters, exclude_filters):
            warnings.append("semantic search skipped: repo has no embeddings")
        candidates.extend(_gather_graph_neighbor_candidates(conn, repo, root, candidates, has_embeddings, index_status))
    finally:
        conn.close()

    candidates = _filter_candidates(_dedupe_candidates(candidates), include_filters, exclude_filters)
    return _assemble_pack(
        repo=repo,
        query=query,
        requested_budget=requested_budget,
        candidates=candidates,
        has_embeddings=has_embeddings,
        index_status=index_status,
        warnings=warnings,
    )


def _repo_entry(repo: str) -> dict | None:
    for entry in query_repos():
        if entry["name"] == repo:
            return entry
    return None


def _query_terms(query: str) -> list[str]:
    terms = [term.lower() for term in re.findall(r"[A-Za-z_][A-Za-z0-9_/-]*", query)]
    filtered = [term for term in terms if len(term) > 1]
    return list(dict.fromkeys(filtered)) or [query.strip().lower()]


def _filter_allowed(item_type: str, include_filters: set[str], exclude_filters: set[str]) -> bool:
    filter_name = TYPE_TO_FILTER[item_type]
    if include_filters and filter_name not in include_filters:
        return False
    return filter_name not in exclude_filters


def _filter_candidates(candidates: list[dict], include_filters: set[str], exclude_filters: set[str]) -> list[dict]:
    return [
        candidate
        for candidate in candidates
        if _filter_allowed(candidate["type"], include_filters, exclude_filters)
    ]


def _dedupe_candidates(candidates: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    for candidate in candidates:
        existing = deduped.get(candidate["id"])
        if existing is None or candidate["rank_score"] > existing["rank_score"]:
            deduped[candidate["id"]] = candidate
    return sorted(
        deduped.values(),
        key=lambda item: (
            -item["rank_score"],
            item.get("file") or "",
            item.get("start_byte") or 0,
            item.get("line") or 0,
            item.get("title") or "",
        ),
    )


def _estimate_tokens(text: str) -> dict:
    return count_token_metrics(text or "", tokenizer=DEFAULT_TOKENIZER)


def _read_byte_range(root: str, file_path: str, start_byte: int | None, end_byte: int | None) -> str:
    abs_path = os.path.join(root, file_path)
    try:
        with open(abs_path, "rb") as fh:
            if start_byte is None or end_byte is None or end_byte <= start_byte:
                return fh.read(SOURCE_MAX_BYTES).decode("utf-8", errors="replace")
            fh.seek(max(0, start_byte))
            return fh.read(min(SOURCE_MAX_BYTES, max(0, end_byte - start_byte))).decode(
                "utf-8",
                errors="replace",
            )
    except OSError:
        return ""


def _path_kind(file_path: str) -> str:
    normalized = file_path.replace("\\", "/").lower()
    name = PurePosixPath(normalized).name
    suffix = PurePosixPath(normalized).suffix
    if normalized.startswith("tests/") or "/tests/" in normalized or name.startswith("test_") or name.endswith("_test.py"):
        return "test"
    if normalized.startswith("docs/") or suffix in {".md", ".markdown", ".mdx", ".rst"}:
        return "doc"
    return "text"


def _candidate_id(item_type: str, row: dict) -> str:
    file_path = row.get("file", "")
    start = row.get("start_byte", row.get("line", ""))
    end = row.get("end_byte", "")
    title = row.get("name") or row.get("handler") or row.get("path") or row.get("text", "")[:24]
    return f"{item_type}:{file_path}:{start}:{end}:{title}"


def _make_candidate(
    *,
    item_type: str,
    row: dict,
    source: str,
    rank_score: float,
    quality_kind: str,
    repo_has_embeddings: bool,
    index_status: dict | None,
    title: str | None = None,
) -> dict:
    item = dict(row)
    item["type"] = item_type
    item["id"] = _candidate_id(item_type, item)
    item["title"] = title or item.get("name") or item.get("handler") or item.get("path") or item.get("file") or item_type
    item["source"] = source
    item["rank_score"] = round(float(rank_score), 4)
    item["estimated_tokens"] = _estimate_tokens(source)["token_count"]
    item["quality"] = build_item_quality(
        row=item,
        result_kind=quality_kind,
        repo_has_embeddings=repo_has_embeddings,
        index_status=index_status,
    )
    return item


def _gather_symbol_candidates(
    conn,
    repo: str,
    root: str,
    query: str,
    has_embeddings: bool,
    index_status: dict | None,
) -> list[dict]:
    rows: list[dict] = []
    for term in _query_terms(query):
        rows.extend(search_symbols(conn, repo=repo, query=term, limit=8))
    rows = attach_quality_to_items(rows, "symbol", has_embeddings, index_status)
    return [
        _make_candidate(
            item_type="symbol",
            row=row,
            source=_read_byte_range(root, row["file"], row.get("start_byte"), row.get("end_byte")),
            rank_score=100,
            quality_kind="symbol",
            repo_has_embeddings=has_embeddings,
            index_status=index_status,
            title=row.get("name"),
        )
        for row in rows
        if row.get("file")
    ]


def _gather_text_candidates(
    conn,
    repo: str,
    root: str,
    query: str,
    has_embeddings: bool,
    index_status: dict | None,
) -> list[dict]:
    rows: list[dict] = []
    for term in _query_terms(query):
        rows.extend(search_text_in_index(conn, repo=repo, query=term, repo_root=root))

    candidates = []
    for row in rows:
        item_type = _path_kind(row["file"])
        rank = 60 if item_type in {"doc", "test"} else 90
        candidates.append(
            _make_candidate(
                item_type=item_type,
                row=row,
                source=row.get("text", ""),
                rank_score=rank,
                quality_kind="text",
                repo_has_embeddings=has_embeddings,
                index_status=index_status,
                title=f"{row.get('file')}:{row.get('line')}",
            )
        )
    return candidates


def _gather_route_candidates(
    conn,
    repo: str,
    root: str,
    query: str,
    has_embeddings: bool,
    index_status: dict | None,
) -> list[dict]:
    rows: list[dict] = []
    for term in _query_terms(query):
        rows.extend(query_routes(conn, repo=repo, path_contains=term, limit=20))
    rows = attach_quality_to_items(rows, "route", has_embeddings, index_status)
    return [
        _make_candidate(
            item_type="route",
            row=row,
            source=_read_byte_range(root, row["file"], row.get("start_byte"), row.get("end_byte")),
            rank_score=85,
            quality_kind="route",
            repo_has_embeddings=has_embeddings,
            index_status=index_status,
            title=f"{row.get('method')} {row.get('path')}",
        )
        for row in rows
        if row.get("file")
    ]


def _gather_semantic_candidates(
    conn,
    repo: str,
    root: str,
    query: str,
    has_embeddings: bool,
    index_status: dict | None,
    warnings: list[str],
) -> list[dict]:
    try:
        from symdex.search.semantic import search_semantic

        rows = search_semantic(conn, query=query, repo=repo, limit=8)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"semantic search skipped: {exc}")
        return []

    rows = attach_quality_to_items(rows, "semantic", has_embeddings, index_status)
    return [
        _make_candidate(
            item_type="semantic",
            row=row,
            source=_read_byte_range(root, row["file"], row.get("start_byte"), row.get("end_byte")),
            rank_score=75 + float(row.get("score") or 0),
            quality_kind="semantic",
            repo_has_embeddings=has_embeddings,
            index_status=index_status,
            title=row.get("name"),
        )
        for row in rows
        if row.get("file")
    ]


def _gather_graph_neighbor_candidates(
    conn,
    repo: str,
    root: str,
    candidates: list[dict],
    has_embeddings: bool,
    index_status: dict | None,
) -> list[dict]:
    names = [candidate.get("name") for candidate in candidates if candidate.get("type") == "symbol" and candidate.get("name")]
    rows: list[dict] = []
    for name in list(dict.fromkeys(names))[:5]:
        for row in get_callers(conn, name=name, repo=repo):
            row["relation"] = f"caller of {name}"
            rows.append(row)
        for row in get_callees(conn, name=name, repo=repo):
            if row.get("file"):
                row["relation"] = f"callee of {name}"
                row["start_byte"] = row.get("start_byte", 0)
                row["end_byte"] = row.get("end_byte", 0)
                rows.append(row)

    return [
        _make_candidate(
            item_type="graph_neighbor",
            row=row,
            source=_read_byte_range(root, row["file"], row.get("start_byte"), row.get("end_byte")),
            rank_score=65,
            quality_kind="symbol",
            repo_has_embeddings=has_embeddings,
            index_status=index_status,
            title=row.get("relation") or row.get("name"),
        )
        for row in rows
        if row.get("file")
    ]


def _outline_candidate(candidate: dict, available_tokens: int) -> dict:
    outline = dict(candidate)
    outline["source"] = f"{candidate['type']} {candidate.get('title', '')} in {candidate.get('file', '')}".strip()
    outline["estimated_tokens"] = min(_estimate_tokens(outline["source"])["token_count"], available_tokens)
    return outline


def _candidate_summary(candidate: dict) -> dict:
    return {
        "id": candidate["id"],
        "type": candidate["type"],
        "file": candidate.get("file"),
        "title": candidate.get("title"),
        "estimated_tokens": candidate.get("estimated_tokens", 0),
        "rank_score": candidate.get("rank_score", 0),
    }


def _bucket_selected(selected: list[dict]) -> dict[str, list[dict]]:
    return {
        "symbols": [item for item in selected if item["type"] in {"symbol", "semantic"}],
        "routes": [item for item in selected if item["type"] == "route"],
        "graph_neighbors": [item for item in selected if item["type"] == "graph_neighbor"],
        "docs": [item for item in selected if item["type"] == "doc"],
        "tests": [item for item in selected if item["type"] == "test"],
    }


def _quality_summary(selected: list[dict], has_embeddings: bool, index_status: dict | None, warnings: list[str]) -> dict:
    confidences = [
        item.get("quality", {}).get("confidence")
        for item in selected
        if item.get("quality", {}).get("confidence") is not None
    ]
    stale = index_status.get("stale") if index_status else None
    return {
        "item_count": len(selected),
        "highest_confidence": max(confidences) if confidences else None,
        "lowest_confidence": min(confidences) if confidences else None,
        "index_fresh": None if stale is None else not bool(stale),
        "has_embeddings": has_embeddings,
        "warnings": list(warnings),
    }


def _assemble_pack(
    *,
    repo: str,
    query: str,
    requested_budget: int,
    candidates: list[dict],
    has_embeddings: bool,
    index_status: dict | None,
    warnings: list[str],
) -> dict:
    reserved_tokens = max(1, requested_budget // 10)
    available_tokens = max(1, requested_budget - reserved_tokens)
    selected: list[dict] = []
    omitted: list[dict] = []
    used_tokens = 0

    for candidate in candidates:
        item_tokens = int(candidate.get("estimated_tokens") or 0)
        if item_tokens <= max(0, available_tokens - used_tokens):
            selected.append(candidate)
            used_tokens += item_tokens
            continue
        if not selected:
            outline = _outline_candidate(candidate, available_tokens)
            selected.append(outline)
            used_tokens += int(outline.get("estimated_tokens") or 0)
        else:
            omitted.append(_candidate_summary(candidate))

    buckets = _bucket_selected(selected)
    token_meta = _estimate_tokens("\n".join(item.get("source", "") for item in selected))
    estimated_tokens = min(used_tokens, available_tokens)
    return {
        "repo": repo,
        "query": query,
        "budget": {
            "requested_tokens": requested_budget,
            "reserved_tokens": reserved_tokens,
            "available_tokens": available_tokens,
            "estimated_tokens": estimated_tokens,
            "tokenizer": token_meta["tokenizer"],
            "approximate": token_meta["approximate"],
        },
        "selected_evidence": selected,
        "symbols": buckets["symbols"],
        "routes": buckets["routes"],
        "graph_neighbors": buckets["graph_neighbors"],
        "docs": buckets["docs"],
        "tests": buckets["tests"],
        "omitted_candidates": omitted,
        "quality_summary": _quality_summary(selected, has_embeddings, index_status, warnings),
        "warnings": list(warnings),
        "agent_hint": "Use selected_evidence first; omitted_candidates exceeded budget."
        if omitted
        else "Use selected_evidence as source-backed context for this query.",
    }
