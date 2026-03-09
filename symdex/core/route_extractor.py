# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

"""Regex-based HTTP route extractor for Python and JavaScript/TypeScript source files."""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class RouteInfo:
    method: str       # GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, ANY
    path: str         # /users/{id}
    handler: str      # function or view name, may be empty string
    start_byte: int
    end_byte: int


# ── Python patterns ──────────────────────────────────────────────────────────

# @app.route("/path", methods=["GET", "POST"])
_PY_ROUTE = re.compile(
    rb"""@\w+\.route\(\s*["']([^"']+)["']\s*(?:,\s*methods\s*=\s*\[([^\]]*)\])?\s*\)"""
    rb"""\s*\n\s*(?:async\s+)?def\s+(\w+)""",
    re.DOTALL,
)

# @app.get("/path") / @app.post / @app.put / @app.delete / @app.patch
_PY_SHORTHAND = re.compile(
    rb"""@\w+\.(get|post|put|delete|patch|head|options)\(\s*["']([^"']+)["']\s*\)"""
    rb"""\s*\n\s*(?:async\s+)?def\s+(\w+)""",
    re.DOTALL,
)

# Django path("route/", view) and re_path(r"...", view)
_PY_DJANGO = re.compile(
    rb"""(?:re_path|path)\(\s*r?["']([^"']+)["']\s*,\s*([\w.]+)""",
)

# ── JavaScript / TypeScript patterns ─────────────────────────────────────────

# app.get("/path", handler) / router.post("/path", handler)
_JS_METHOD = re.compile(
    rb"""\b\w+\.(get|post|put|delete|patch|head|options|all)\(\s*["'`]([^"'`]+)["'`]\s*,\s*(\w+)""",
    re.IGNORECASE,
)


def _parse_methods(raw: bytes) -> List[str]:
    """Extract method strings from b'"GET", "POST"' raw bytes."""
    return [m.strip(b"\"' ").decode().upper() for m in raw.split(b",") if m.strip()]


def extract_routes(source: bytes, file_path: str, lang: str) -> List[RouteInfo]:
    """Extract HTTP route definitions from *source*.

    Args:
        source: Raw file bytes.
        file_path: Relative file path (for context only).
        lang: Language string, e.g. 'python', 'javascript', 'typescript'.

    Returns:
        List of RouteInfo objects. Empty list if lang not supported or no routes found.
    """
    if not source:
        return []

    lang = lang.lower()
    results: List[RouteInfo] = []

    if lang == "python":
        # @app.route(...)
        for m in _PY_ROUTE.finditer(source):
            path = m.group(1).decode(errors="replace")
            raw_methods = m.group(2) or b""
            methods = _parse_methods(raw_methods) if raw_methods.strip() else ["GET"]
            handler = m.group(3).decode(errors="replace")
            for method in methods:
                results.append(RouteInfo(
                    method=method,
                    path=path,
                    handler=handler,
                    start_byte=m.start(),
                    end_byte=m.end(),
                ))

        # @app.get / @app.post / etc.
        for m in _PY_SHORTHAND.finditer(source):
            method = m.group(1).decode().upper()
            path = m.group(2).decode(errors="replace")
            handler = m.group(3).decode(errors="replace")
            results.append(RouteInfo(
                method=method,
                path=path,
                handler=handler,
                start_byte=m.start(),
                end_byte=m.end(),
            ))

        # Django urlpatterns
        for m in _PY_DJANGO.finditer(source):
            path = m.group(1).decode(errors="replace")
            handler = m.group(2).decode(errors="replace")
            results.append(RouteInfo(
                method="ANY",
                path=path,
                handler=handler,
                start_byte=m.start(),
                end_byte=m.end(),
            ))

    elif lang in ("javascript", "typescript"):
        for m in _JS_METHOD.finditer(source):
            method = m.group(1).decode().upper()
            path = m.group(2).decode(errors="replace")
            handler = m.group(3).decode(errors="replace")
            results.append(RouteInfo(
                method=method,
                path=path,
                handler=handler,
                start_byte=m.start(),
                end_byte=m.end(),
            ))

    return results
