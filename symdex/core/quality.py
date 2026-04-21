# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

from __future__ import annotations

from pathlib import PurePosixPath


_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".dart": "dart",
    ".swift": "swift",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c",
    ".h": "cpp",
    ".hpp": "cpp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".less": "css",
    ".styl": "css",
    ".stylus": "css",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ex": "elixir",
    ".exs": "elixir",
    ".rb": "ruby",
    ".vue": "vue",
    ".svelte": "svelte",
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdx": "markdown",
}

_GENERATED_PARTS = {
    "dist",
    "build",
    "coverage",
    "node_modules",
    "vendor",
    ".next",
    "__pycache__",
}

_GENERATED_SUFFIXES = (
    ".generated.py",
    ".generated.ts",
    ".pb.go",
    ".g.dart",
    ".designer.cs",
)


def normalize_confidence(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, min(1.0, float(value))), 4)


def infer_language_surface(path: str | None) -> str:
    if not path:
        return "unknown"
    normalized = path.replace("\\", "/").lower()
    if normalized.endswith(".markdown"):
        return "markdown"
    return _LANGUAGE_BY_SUFFIX.get(PurePosixPath(normalized).suffix, "unknown")


def detect_generated_path(path: str | None) -> bool:
    if not path:
        return False
    normalized = path.replace("\\", "/").lower()
    parts = set(PurePosixPath(normalized).parts)
    if parts & _GENERATED_PARTS:
        return True
    return normalized.endswith(_GENERATED_SUFFIXES)


def parser_mode_for_path(path: str | None, result_kind: str) -> str | None:
    language = infer_language_surface(path)
    if result_kind == "text":
        return "fallback_text"
    if result_kind == "route":
        return "regex_route"
    if language == "markdown":
        return "native_markdown"
    if language == "unknown":
        return "unknown"
    return "tree_sitter"


def _confidence_for(row: dict, result_kind: str) -> tuple[float, str, float | None]:
    if result_kind == "semantic":
        score = normalize_confidence(row.get("score")) or 0.0
        return score, "semantic embedding similarity", None
    if result_kind == "text":
        return 0.70, "indexed file text match", None
    if result_kind == "route":
        route_confidence = 0.85 if row.get("handler") else 0.65
        reason = (
            "route extracted with handler"
            if row.get("handler")
            else "route extracted without handler"
        )
        return route_confidence, reason, route_confidence
    if result_kind == "outline":
        return 0.90, "file outline from indexed symbols", None
    if result_kind == "symbol":
        return 0.92, "exact symbol match from parser", None
    return 0.50, "quality unknown", None


def build_item_quality(
    row: dict,
    result_kind: str,
    repo_has_embeddings: bool | None = None,
    index_status: dict | None = None,
) -> dict:
    path = row.get("file") or row.get("path")
    confidence, reason, route_confidence = _confidence_for(row, result_kind)
    stale = index_status.get("stale") if index_status else None
    return {
        "confidence": normalize_confidence(confidence),
        "confidence_reason": reason,
        "index_fresh": None if stale is None else not bool(stale),
        "last_indexed": index_status.get("last_indexed") if index_status else None,
        "parser_mode": parser_mode_for_path(path, result_kind),
        "language_surface": infer_language_surface(path),
        "is_generated": detect_generated_path(path),
        "is_ignored": False,
        "ignored_reason": None,
        "has_embeddings": repo_has_embeddings,
        "route_confidence": normalize_confidence(route_confidence),
    }


def attach_quality_to_items(
    rows: list[dict],
    result_kind: str,
    repo_has_embeddings: bool | None = None,
    index_status: dict | None = None,
) -> list[dict]:
    enriched = []
    for row in rows:
        item = dict(row)
        item["quality"] = build_item_quality(
            row=item,
            result_kind=result_kind,
            repo_has_embeddings=repo_has_embeddings,
            index_status=index_status,
        )
        enriched.append(item)
    return enriched
