# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

"""Regex-based HTTP route extractor across common web frameworks."""

from __future__ import annotations

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


# Python: Flask / FastAPI / Django
_PY_ROUTE = re.compile(
    rb"""@\w+\.(?:route|api_route)\(\s*["']([^"']+)["']\s*(?:,\s*methods\s*=\s*\[([^\]]*)\])?\s*\)"""
    rb"""\s*\n\s*(?:async\s+)?def\s+(\w+)""",
    re.DOTALL,
)
_PY_SHORTHAND = re.compile(
    rb"""@\w+\.(get|post|put|delete|patch|head|options)\(\s*["']([^"']+)["']\s*\)"""
    rb"""\s*\n\s*(?:async\s+)?def\s+(\w+)""",
    re.DOTALL,
)
_PY_DJANGO = re.compile(
    rb"""(?:re_path|path)\(\s*r?["']([^"']+)["']\s*,\s*([\w.]+(?:\([^)]*\))?)""",
)

# JavaScript / TypeScript: Express / routers
_JS_METHOD = re.compile(
    rb"""\b\w+\.(get|post|put|delete|patch|head|options|all)\(\s*["'`]([^"'`]+)["'`]\s*,\s*(?!async\b)([\w.$]+)""",
    re.IGNORECASE,
)
_JS_INLINE = re.compile(
    rb"""\b\w+\.(get|post|put|delete|patch|head|options|all)\(\s*["'`]([^"'`]+)["'`]\s*,\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*=>)""",
    re.IGNORECASE,
)
_JS_CHAIN_START = re.compile(
    rb"""\b\w+\.route\(\s*["'`]([^"'`]+)["'`]\s*\)""",
    re.IGNORECASE,
)
_JS_CHAIN_CALL = re.compile(
    rb"""\.\s*(get|post|put|delete|patch|head|options|all)\(\s*(?:async\s+)?(?:(function\b)|(\([^)]*\)\s*=>)|([\w.$]+))""",
    re.IGNORECASE,
)

# PHP: Laravel
_PHP_ROUTE = re.compile(
    rb"""\bRoute::(get|post|put|delete|patch|head|options|any)\(\s*["']([^"']+)["']\s*,\s*([^)]+)\)""",
    re.IGNORECASE,
)
_PHP_MATCH = re.compile(
    rb"""\bRoute::match\(\s*\[([^\]]+)\]\s*,\s*["']([^"']+)["']\s*,\s*([^)]+)\)""",
    re.IGNORECASE,
)

# Go: Gin / Echo / Fiber / chi / net/http
_GO_ROUTE = re.compile(
    rb"""\b\w+\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|Any|Get|Post|Put|Delete|Patch|Head|Options|Handle|HandleFunc)\(\s*["'`]([^"'`]+)["'`]\s*,\s*(?:([\w.]+)|func\b)""",
    re.IGNORECASE,
)

# Java / Kotlin: Spring MVC
_JAVA_SHORT_MAPPING = re.compile(
    rb"""@(Get|Post|Put|Delete|Patch)Mapping\(\s*([^)]*?)\)\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public|protected|private)?[^{;=\n]*?\s+(\w+)\s*\(""",
    re.IGNORECASE | re.DOTALL,
)
_JAVA_REQUEST_MAPPING = re.compile(
    rb"""@RequestMapping\(\s*([^)]*?)\)\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public|protected|private)?[^{;=\n]*?\s+(\w+)\s*\(""",
    re.IGNORECASE | re.DOTALL,
)

# C#: ASP.NET attribute routing
_CS_METHOD_BLOCK = re.compile(
    rb"""((?:\[[^\]]+\]\s*)+)(?:public|protected|private|internal)\s+[^{;=\n]*?\s+(\w+)\s*\(""",
    re.IGNORECASE | re.DOTALL,
)
_CS_HTTP_ATTR = re.compile(
    rb"""Http(Get|Post|Put|Delete|Patch|Head|Options)(?:\(\s*["']?([^"'\)]*)["']?\s*\))?""",
    re.IGNORECASE,
)
_CS_ROUTE_ATTR = re.compile(
    rb"""Route\(\s*["']([^"']+)["']\s*\)""",
    re.IGNORECASE,
)

# Ruby: Rails / Sinatra
_RB_RAILS_TO = re.compile(
    rb"""\b(get|post|put|patch|delete|head|options)\s+["']([^"']+)["']\s*,\s*to:\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_RB_RAILS_ARROW = re.compile(
    rb"""\b(get|post|put|patch|delete|head|options)\s+["']([^"']+)["']\s*=>\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_RB_SINATRA = re.compile(
    rb"""\b(get|post|put|patch|delete|head|options)\s+["']([^"']+)["']\s+do\b""",
    re.IGNORECASE,
)

# Elixir: Phoenix router
_EX_ROUTE = re.compile(
    rb"""\b(get|post|put|patch|delete|head|options)\s+["']([^"']+)["']\s*,\s*([\w.]+)\s*,\s*:(\w+)""",
    re.IGNORECASE,
)

# Rust: Actix
_RUST_ATTR = re.compile(
    rb"""#\[(get|post|put|delete|patch|head|options)\(\s*["']([^"']+)["']\s*\)\]\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)""",
    re.IGNORECASE | re.DOTALL,
)

_ANNOTATION_PATH = re.compile(
    rb"""(?:\b(?:value|path)\s*=\s*)?["'`]([^"'`]+)["'`]""",
    re.IGNORECASE,
)
_REQUEST_METHOD = re.compile(
    rb"""RequestMethod\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)""",
    re.IGNORECASE,
)


def _parse_methods(raw: bytes) -> List[str]:
    """Extract method strings from b'"GET", "POST"' raw bytes."""
    return [_normalize_method(m.strip(b"\"' ").decode()) for m in raw.split(b",") if m.strip()]


def _normalize_method(raw: str) -> str:
    method = raw.strip().upper()
    return "ANY" if method in {"ALL", "ANY", "HANDLE", "HANDLEFUNC"} else method


def _clean_handler(raw: bytes) -> str:
    return raw.decode(errors="replace").strip().rstrip(",").strip()


def _extract_annotation_path(raw: bytes) -> str | None:
    match = _ANNOTATION_PATH.search(raw)
    if not match:
        return None
    return match.group(1).decode(errors="replace")


def _extract_request_methods(raw: bytes) -> List[str]:
    return [_normalize_method(m.decode()) for m in _REQUEST_METHOD.findall(raw)]


def _append_route(
    results: List[RouteInfo],
    seen: set[tuple[str, str, str, int, int]],
    *,
    method: str,
    path: str,
    handler: str,
    start_byte: int,
    end_byte: int,
) -> None:
    key = (_normalize_method(method), path, handler, start_byte, end_byte)
    if key in seen or not path:
        return
    seen.add(key)
    results.append(
        RouteInfo(
            method=key[0],
            path=path,
            handler=handler,
            start_byte=start_byte,
            end_byte=end_byte,
        )
    )


def extract_routes(source: bytes, file_path: str, lang: str) -> List[RouteInfo]:
    """Extract HTTP route definitions from *source*.

    Args:
        source: Raw file bytes.
        file_path: Relative file path (for context only).
        lang: Language string, e.g. 'python', 'javascript', 'typescript'.

    Returns:
        List of RouteInfo objects. Empty list if lang not supported or no routes found.
    """
    del file_path  # Reserved for future framework-specific heuristics.

    if not source:
        return []

    lang = lang.lower()
    results: List[RouteInfo] = []
    seen: set[tuple[str, str, str, int, int]] = set()

    if lang == "python":
        for match in _PY_ROUTE.finditer(source):
            path = match.group(1).decode(errors="replace")
            raw_methods = match.group(2) or b""
            methods = _parse_methods(raw_methods) if raw_methods.strip() else ["GET"]
            handler = match.group(3).decode(errors="replace")
            for method in methods:
                _append_route(
                    results,
                    seen,
                    method=method,
                    path=path,
                    handler=handler,
                    start_byte=match.start(),
                    end_byte=match.end(),
                )

        for match in _PY_SHORTHAND.finditer(source):
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler=match.group(3).decode(errors="replace"),
                start_byte=match.start(),
                end_byte=match.end(),
            )

        for match in _PY_DJANGO.finditer(source):
            _append_route(
                results,
                seen,
                method="ANY",
                path=match.group(1).decode(errors="replace"),
                handler=match.group(2).decode(errors="replace"),
                start_byte=match.start(),
                end_byte=match.end(),
            )

    elif lang in ("javascript", "typescript"):
        for match in _JS_METHOD.finditer(source):
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler=match.group(3).decode(errors="replace"),
                start_byte=match.start(),
                end_byte=match.end(),
            )

        for match in _JS_INLINE.finditer(source):
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler="<inline>",
                start_byte=match.start(),
                end_byte=match.end(),
            )

        for match in _JS_CHAIN_START.finditer(source):
            statement_end = source.find(b";", match.end())
            if statement_end == -1:
                statement_end = len(source)
            chain = source[match.end():statement_end]
            for chain_match in _JS_CHAIN_CALL.finditer(chain):
                handler = (
                    chain_match.group(4).decode(errors="replace")
                    if chain_match.group(4)
                    else "<inline>"
                )
                _append_route(
                    results,
                    seen,
                    method=chain_match.group(1).decode(),
                    path=match.group(1).decode(errors="replace"),
                    handler=handler,
                    start_byte=match.start(),
                    end_byte=statement_end,
                )

    elif lang == "php":
        for match in _PHP_ROUTE.finditer(source):
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler=_clean_handler(match.group(3)),
                start_byte=match.start(),
                end_byte=match.end(),
            )

        for match in _PHP_MATCH.finditer(source):
            methods = _parse_methods(match.group(1))
            path = match.group(2).decode(errors="replace")
            handler = _clean_handler(match.group(3))
            for method in methods:
                _append_route(
                    results,
                    seen,
                    method=method,
                    path=path,
                    handler=handler,
                    start_byte=match.start(),
                    end_byte=match.end(),
                )

    elif lang == "go":
        for match in _GO_ROUTE.finditer(source):
            handler = match.group(3).decode(errors="replace") if match.group(3) else "<inline>"
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler=handler,
                start_byte=match.start(),
                end_byte=match.end(),
            )

    elif lang in ("java", "kotlin"):
        for match in _JAVA_SHORT_MAPPING.finditer(source):
            path = _extract_annotation_path(match.group(2))
            if path is None:
                continue
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=path,
                handler=match.group(3).decode(errors="replace"),
                start_byte=match.start(),
                end_byte=match.end(),
            )

        for match in _JAVA_REQUEST_MAPPING.finditer(source):
            path = _extract_annotation_path(match.group(1))
            if path is None:
                continue
            methods = _extract_request_methods(match.group(1)) or ["ANY"]
            for method in methods:
                _append_route(
                    results,
                    seen,
                    method=method,
                    path=path,
                    handler=match.group(2).decode(errors="replace"),
                    start_byte=match.start(),
                    end_byte=match.end(),
                )

    elif lang in ("csharp", "c_sharp", "c#"):
        for match in _CS_METHOD_BLOCK.finditer(source):
            attrs = match.group(1)
            handler = match.group(2).decode(errors="replace")
            http_attr = _CS_HTTP_ATTR.search(attrs)
            if not http_attr:
                continue
            path = http_attr.group(2).decode(errors="replace") if http_attr.group(2) else ""
            if not path:
                route_attr = _CS_ROUTE_ATTR.search(attrs)
                path = route_attr.group(1).decode(errors="replace") if route_attr else ""
            if not path:
                continue
            _append_route(
                results,
                seen,
                method=http_attr.group(1).decode(),
                path=path,
                handler=handler,
                start_byte=match.start(),
                end_byte=match.end(),
            )

    elif lang == "ruby":
        for match in _RB_RAILS_TO.finditer(source):
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler=match.group(3).decode(errors="replace"),
                start_byte=match.start(),
                end_byte=match.end(),
            )

        for match in _RB_RAILS_ARROW.finditer(source):
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler=match.group(3).decode(errors="replace"),
                start_byte=match.start(),
                end_byte=match.end(),
            )

        for match in _RB_SINATRA.finditer(source):
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler="<inline>",
                start_byte=match.start(),
                end_byte=match.end(),
            )

    elif lang == "elixir":
        for match in _EX_ROUTE.finditer(source):
            handler = (
                f"{match.group(3).decode(errors='replace')}.{match.group(4).decode(errors='replace')}"
            )
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler=handler,
                start_byte=match.start(),
                end_byte=match.end(),
            )

    elif lang == "rust":
        for match in _RUST_ATTR.finditer(source):
            _append_route(
                results,
                seen,
                method=match.group(1).decode(),
                path=match.group(2).decode(errors="replace"),
                handler=match.group(3).decode(errors="replace"),
                start_byte=match.start(),
                end_byte=match.end(),
            )

    return results
