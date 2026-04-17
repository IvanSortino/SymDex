# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import importlib
import logging
import os
import re
from typing import Optional, TypedDict

try:
    from tree_sitter import Language, Parser as TSParser
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    _TREE_SITTER_AVAILABLE = False
    Language = None  # type: ignore
    TSParser = None  # type: ignore

try:
    from tree_sitter_language_pack import get_language as _get_language_from_pack
except ImportError:  # pragma: no cover - optional fallback
    _get_language_from_pack = None

logger = logging.getLogger(__name__)

_MARKDOWN_EXTENSIONS = {".md", ".markdown"}

# Map file extension -> (language_name, grammar_module, preferred_loader_attr)
_EXT_MAP: dict[str, tuple[str, Optional[str], Optional[str]]] = {
    ".py":   ("python",     "tree_sitter_python", None),
    ".js":   ("javascript", "tree_sitter_javascript", None),
    ".jsx":  ("javascript", "tree_sitter_javascript", None),
    ".mjs":  ("javascript", "tree_sitter_javascript", None),
    ".ts":   ("typescript", "tree_sitter_typescript", "language_typescript"),
    ".tsx":  ("typescript", "tree_sitter_typescript", "language_tsx"),
    ".go":   ("go",         "tree_sitter_go", None),
    ".rs":   ("rust",       "tree_sitter_rust", None),
    ".java": ("java",       "tree_sitter_java", None),
    ".php":  ("php",        "tree_sitter_php", "language_php"),
    ".cs":   ("c_sharp",    "tree_sitter_c_sharp", None),
    ".c":    ("c",          "tree_sitter_c", None),
    ".h":    ("cpp",        "tree_sitter_cpp", None),
    ".cpp":  ("cpp",        "tree_sitter_cpp", None),
    ".cc":   ("cpp",        "tree_sitter_cpp", None),
    ".ex":   ("elixir",     "tree_sitter_elixir", None),
    ".exs":  ("elixir",     "tree_sitter_elixir", None),
    ".rb":   ("ruby",       "tree_sitter_ruby", None),
    ".kt":   ("kotlin",     "tree_sitter_kotlin", None),
    ".kts":  ("kotlin",     "tree_sitter_kotlin", None),
    ".dart": ("dart",       None, None),
    ".swift": ("swift",     None, None),
}

_MARKDOWN_CODE_EXTS = {
    "py": ".py",
    "python": ".py",
    "js": ".js",
    "javascript": ".js",
    "jsx": ".jsx",
    "mjs": ".mjs",
    "ts": ".ts",
    "typescript": ".ts",
    "tsx": ".tsx",
    "go": ".go",
    "golang": ".go",
    "rs": ".rs",
    "rust": ".rs",
    "java": ".java",
    "php": ".php",
    "cs": ".cs",
    "csharp": ".cs",
    "c#": ".cs",
    "c": ".c",
    "cpp": ".cpp",
    "c++": ".cpp",
    "cc": ".cc",
    "elixir": ".ex",
    "ex": ".ex",
    "ruby": ".rb",
    "rb": ".rb",
    "kotlin": ".kt",
    "kt": ".kt",
    "kts": ".kts",
    "dart": ".dart",
    "swift": ".swift",
}
# node_type → kind mapping per language
_NODE_KINDS: dict[str, dict[str, str]] = {
    "python": {
        "function_definition": "function",
        "class_definition": "class",
        "decorated_definition": "decorated",
    },
    "javascript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
    },
    "typescript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "abstract_class_declaration": "class",
        "interface_declaration": "class",
        "method_definition": "method",
        "method_signature": "method",
        "abstract_method_signature": "method",
        "function_signature": "function",
        "type_alias_declaration": "type",
        "enum_declaration": "enum",
    },
    "go": {
        "function_declaration": "function",
        "method_declaration": "method",
        "type_declaration": "class",
    },
    "rust": {
        "function_item": "function",
        "function_signature_item": "function",
        "struct_item": "class",
        "trait_item": "class",
    },
    "java": {
        "method_declaration": "method",
        "class_declaration": "class",
        "interface_declaration": "class",
    },
    "php": {
        "function_definition": "function",
        "class_declaration": "class",
        "method_declaration": "method",
    },
    "c_sharp": {
        "method_declaration": "method",
        "class_declaration": "class",
        "interface_declaration": "class",
    },
    "c": {
        "function_definition": "function",
        "struct_specifier": "class",
    },
    "cpp": {
        "function_definition": "function",
        "class_specifier": "class",
        "struct_specifier": "class",
    },
    "elixir": {
        "def": "function",
        "defmodule": "class",
        "defp": "function",
    },
    "ruby": {
        "method": "method",
        "class": "class",
        "module": "class",
    },
    "kotlin": {
        "function_declaration": "function",
        "class_declaration": "class",
        "type_alias": "type",
    },
    "dart": {
        "class_definition": "class",
        "function_signature": "function",
        "method_signature": "method",
        "declaration": "function",
        "enum_declaration": "enum",
        "type_alias": "type",
    },
    "swift": {
        "class_declaration": "class",
        "function_declaration": "function",
        "protocol_declaration": "class",
        "protocol_function_declaration": "method",
    },
}


class SymbolDict(TypedDict):
    name: str
    file: str
    kind: str
    start_byte: int
    end_byte: int
    signature: Optional[str]
    docstring: Optional[str]


def _get_language(ext: str):
    """Return (lang_name, Language) for the extension, or (None, None)."""
    entry = _EXT_MAP.get(ext.lower())
    if not entry:
        return None, None
    lang_name, module_name, preferred_loader = entry
    module_error: Exception | None = None
    language = None

    if module_name:
        try:
            mod = importlib.import_module(module_name)
            loader_candidates = []
            if preferred_loader:
                loader_candidates.append(preferred_loader.upper())
                loader_candidates.append(preferred_loader)
            loader_candidates.extend(
                [
                    "LANGUAGE",
                    "language",
                    f"LANGUAGE_{lang_name.upper()}",
                    f"language_{lang_name}",
                    "LANGUAGE_TYPESCRIPT",
                    "language_typescript",
                    "LANGUAGE_PHP",
                    "language_php",
                ]
            )
            for attr in dict.fromkeys(loader_candidates):
                val = getattr(mod, attr, None)
                if val is not None:
                    language_ptr = val() if callable(val) else val
                    language = Language(language_ptr)
                    break
            if language is None:
                raise AttributeError(
                    f"No supported language loader found in module {module_name}"
                )
        except Exception as exc:
            module_error = exc

    if language is None and _get_language_from_pack is not None:
        try:
            language = _get_language_from_pack(lang_name)
        except Exception:
            language = None

    if language is not None:
        return lang_name, language

    if module_name and module_error is not None:
        logger.warning("Could not load grammar %s: %s", module_name, module_error)
    return lang_name, None


def _extract_name(node, source_bytes: bytes) -> Optional[str]:
    """Extract identifier name from a definition node."""
    name_node = node.child_by_field_name("name")
    if name_node:
        return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    # Fallback for grammars where definitions don't expose a "name" field.
    stack = list(node.children)
    while stack:
        child = stack.pop(0)
        if child.type in ("identifier", "type_identifier", "field_identifier", "constant", "simple_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        stack.extend(list(child.children))
    return None


def _extract_signature(node, source_bytes: bytes) -> str:
    """First line of the definition, max 200 chars."""
    text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    first_line = text.split("\n")[0]
    return first_line[:200]


def _extract_python_docstring(node, source_bytes: bytes) -> Optional[str]:
    """Extract the first string literal from a Python function/class body."""
    body = node.child_by_field_name("body")
    if not body:
        return None
    for child in body.children:
        if child.type == "expression_statement":
            for inner in child.children:
                if inner.type == "string":
                    raw = source_bytes[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
                    if raw.startswith('"""') or raw.startswith("'''"):
                        return raw[3:-3].strip() or None
                    elif raw.startswith('"') or raw.startswith("'"):
                        return raw[1:-1] or None
            break
    return None


def _extract_comment_docstring(node, source_bytes: bytes) -> Optional[str]:
    """Find the nearest comment node immediately preceding this node."""
    parent = node.parent
    if not parent:
        return None
    children = list(parent.children)
    idx = next((i for i, c in enumerate(children) if c.id == node.id), None)
    if idx is None or idx == 0:
        return None
    prev = children[idx - 1]
    if prev.type in ("comment", "line_comment", "block_comment"):
        return source_bytes[prev.start_byte:prev.end_byte].decode("utf-8", errors="replace").strip()
    return None

def _extract_elixir_symbol(node, source_bytes: bytes) -> Optional[tuple[str, str]]:
    """Extract (kind, name) for Elixir def/defp/defmodule calls."""
    if node.type != "call" or not node.children:
        return None
    head = node.children[0]
    if head.type != "identifier":
        return None
    macro = source_bytes[head.start_byte:head.end_byte].decode("utf-8", errors="replace")
    kind = {"def": "function", "defp": "function", "defmodule": "class"}.get(macro)
    if kind is None:
        return None
    args = next((c for c in node.children if c.type == "arguments"), None)
    if args is None:
        return None
    target = next((c for c in args.children if c.is_named), None)
    if target is None:
        return None
    if target.type == "call":
        name_node = next((c for c in target.children if c.type in ("identifier", "alias", "constant")), None)
    elif target.type in ("alias", "identifier", "constant"):
        name_node = target
    else:
        name_node = None
    if name_node is None:
        return None
    name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    return kind, name


def _extract_vue_script(source_bytes: bytes) -> tuple[bytes, int, str]:
    """Extract the <script> block from a Vue SFC.

    Returns (script_bytes, byte_offset, lang_name).
    byte_offset is the position of script_bytes within source_bytes so that
    byte offsets stored in the DB remain relative to the full .vue file.
    lang_name is 'typescript' if lang="ts", otherwise 'javascript'.
    """
    match = re.search(rb"<script(\s[^>]*)?>(.+?)</script>", source_bytes, re.DOTALL | re.IGNORECASE)
    if not match:
        return b"", 0, "javascript"
    attrs = match.group(1) or b""
    lang_name = "typescript" if re.search(rb'lang=["\']tsx?["\']', attrs) else "javascript"
    return match.group(2), match.start(2), lang_name


def _iter_line_spans(source_bytes: bytes):
    start = 0
    while start < len(source_bytes):
        newline = source_bytes.find(b"\n", start)
        end = len(source_bytes) if newline == -1 else newline + 1
        yield start, end, source_bytes[start:end]
        start = end


def _parse_markdown_heading(line: bytes) -> tuple[str, str] | None:
    raw = line.rstrip(b"\r\n")
    stripped = raw.lstrip(b" ")
    if len(raw) - len(stripped) > 3:
        return None
    match = re.match(rb"(#{1,6})(?:[ \t]+|$)(.*)$", stripped)
    if not match:
        return None
    title = match.group(2).strip()
    title = re.sub(rb"[ \t]+#+[ \t]*$", b"", title).strip()
    if not title:
        return None
    return (
        title.decode("utf-8", errors="replace"),
        stripped.decode("utf-8", errors="replace"),
    )


def _parse_markdown_fence(line: bytes) -> tuple[bytes, int, str] | None:
    stripped = line.strip()
    match = re.match(rb"(`{3,}|~{3,})[ \t]*([^ \t`~]*)?", stripped)
    if not match:
        return None
    marker = match.group(1)
    info = (match.group(2) or b"").decode("utf-8", errors="replace")
    return marker[:1], len(marker), info


def _markdown_code_extension(info: str) -> str | None:
    token = info.strip().split(maxsplit=1)[0].lower() if info.strip() else ""
    token = token.strip("{}")
    if token.startswith(".") and token in _EXT_MAP:
        return token
    return _MARKDOWN_CODE_EXTS.get(token)


def _markdown_docstring(section_bytes: bytes) -> str | None:
    parts: list[str] = []
    fence: tuple[bytes, int] | None = None
    for _, _, line in _iter_line_spans(section_bytes):
        parsed_fence = _parse_markdown_fence(line)
        if parsed_fence:
            marker, length, _ = parsed_fence
            if fence is None:
                fence = (marker, length)
            elif marker == fence[0] and length >= fence[1]:
                fence = None
            continue
        if fence is not None:
            continue
        text = line.strip()
        if text:
            parts.append(text.decode("utf-8", errors="replace"))
    docstring = " ".join(parts).strip()
    return docstring[:500] if docstring else None


def _parent_type(node) -> str | None:
    parent = node.parent
    return parent.type if parent is not None else None


def _has_ancestor_type(node, target_types: set[str], *, max_depth: int = 4) -> bool:
    current = node.parent
    depth = 0
    while current is not None and depth < max_depth:
        if current.type in target_types:
            return True
        current = current.parent
        depth += 1
    return False


def _grandparent_type(node) -> str | None:
    parent = node.parent
    if parent is None or parent.parent is None:
        return None
    return parent.parent.type


def _modifier_text(node, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type == "modifiers":
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return ""


def _node_has_direct_child(node, child_type: str) -> bool:
    return any(child.type == child_type for child in node.children)


def _dart_declaration_is_callable(node) -> bool:
    return any(child.type == "function_signature" for child in node.children)


def _symbol_span(node, lang_name: str) -> tuple[int, int]:
    start_byte = node.start_byte
    end_byte = node.end_byte

    if lang_name == "dart" and node.type in {"function_signature", "method_signature"}:
        next_named = getattr(node, "next_named_sibling", None)
        if next_named is not None and next_named.type == "function_body":
            end_byte = next_named.end_byte

    return start_byte, end_byte


def _adjust_kind_for_context(node, lang_name: str, kind: str, source_bytes: bytes) -> str:
    """Refine symbol kind using AST context when grammars reuse node types."""
    if lang_name == "python" and node.type == "function_definition":
        if _has_ancestor_type(node, {"class_definition"}):
            return "method"

    if lang_name == "rust" and node.type in {"function_item", "function_signature_item"}:
        if _has_ancestor_type(node, {"impl_item", "trait_item"}):
            return "method"

    if lang_name == "cpp" and node.type == "function_definition":
        if _has_ancestor_type(node, {"class_specifier", "struct_specifier"}):
            return "method"

    if lang_name == "ruby" and node.type == "method":
        if _has_ancestor_type(node, {"class", "module", "singleton_class"}):
            return "method"
        return "function"

    if lang_name == "kotlin":
        if node.type == "function_declaration" and _has_ancestor_type(node, {"class_declaration", "companion_object"}):
            return "method"
        if node.type == "class_declaration" and "enum" in _modifier_text(node, source_bytes).split():
            return "enum"

    if lang_name == "dart":
        if node.type in {"function_signature", "method_signature", "declaration"}:
            if _has_ancestor_type(node, {"class_definition"}):
                return "method"
            return "function"

    if lang_name == "swift":
        if node.type == "function_declaration" and _has_ancestor_type(node, {"class_declaration", "protocol_declaration"}):
            return "method"
        if node.type == "class_declaration" and _node_has_direct_child(node, "enum"):
            return "enum"

    return kind


def _walk_and_extract(
    root_node,
    source_bytes: bytes,
    lang_name: str,
    rel_path: str,
    results: list,
) -> None:
    """Iterative DFS walk of tree-sitter AST to collect symbol dicts."""
    kind_map = _NODE_KINDS.get(lang_name, {})
    stack = [root_node]

    while stack:
        node = stack.pop()
        node_type = node.type

        if lang_name == "elixir" and node_type == "call":
            extracted = _extract_elixir_symbol(node, source_bytes)
            if extracted:
                kind, name = extracted
                results.append({
                    "name": name,
                    "file": rel_path,
                    "kind": kind,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                    "signature": _extract_signature(node, source_bytes),
                    "docstring": _extract_comment_docstring(node, source_bytes),
                })
            stack.extend(reversed(node.children))
            continue

        # JS/TS: arrow functions assigned to const/let/var
        if lang_name in ("javascript", "typescript") and node_type == "variable_declarator":
            value = node.child_by_field_name("value")
            if value and value.type in {"arrow_function", "function_expression"}:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    results.append({
                        "name": name,
                        "file": rel_path,
                        "kind": "function",
                        "start_byte": value.start_byte,
                        "end_byte": value.end_byte,
                        "signature": _extract_signature(value, source_bytes),
                        "docstring": _extract_comment_docstring(node.parent or node, source_bytes),
                    })
            # Still push children to walk rest of the tree
            stack.extend(reversed(node.children))
            continue

        if lang_name == "kotlin" and node_type == "property_declaration":
            lambda_node = next((child for child in node.children if child.type == "lambda_literal"), None)
            var_node = next((child for child in node.children if child.type == "variable_declaration"), None)
            name = _extract_name(var_node, source_bytes) if var_node is not None else None
            if lambda_node is not None and name:
                results.append({
                    "name": name,
                    "file": rel_path,
                    "kind": "function",
                    "start_byte": lambda_node.start_byte,
                    "end_byte": lambda_node.end_byte,
                    "signature": _extract_signature(node, source_bytes),
                    "docstring": _extract_comment_docstring(node, source_bytes),
                })
            stack.extend(reversed(node.children))
            continue

        if lang_name == "swift" and node_type == "property_declaration":
            lambda_node = next((child for child in node.children if child.type == "lambda_literal"), None)
            pattern_node = next((child for child in node.children if child.type == "pattern"), None)
            name = _extract_name(pattern_node, source_bytes) if pattern_node is not None else None
            if lambda_node is not None and name:
                results.append({
                    "name": name,
                    "file": rel_path,
                    "kind": "function",
                    "start_byte": lambda_node.start_byte,
                    "end_byte": lambda_node.end_byte,
                    "signature": _extract_signature(node, source_bytes),
                    "docstring": _extract_comment_docstring(node, source_bytes),
                })
            stack.extend(reversed(node.children))
            continue

        if lang_name == "dart" and node_type == "static_final_declaration":
            fn_expr = next((child for child in node.children if child.type == "function_expression"), None)
            name_node = next((child for child in node.children if child.type == "identifier"), None)
            if fn_expr is not None and name_node is not None:
                name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                results.append({
                    "name": name,
                    "file": rel_path,
                    "kind": "function",
                    "start_byte": fn_expr.start_byte,
                    "end_byte": fn_expr.end_byte,
                    "signature": _extract_signature(node, source_bytes),
                    "docstring": _extract_comment_docstring(node, source_bytes),
                })
            stack.extend(reversed(node.children))
            continue

        if node_type in kind_map:
            if lang_name == "dart":
                if node_type == "declaration" and not _dart_declaration_is_callable(node):
                    stack.extend(reversed(node.children))
                    continue
                if node_type == "function_signature" and _parent_type(node) == "method_signature":
                    stack.extend(reversed(node.children))
                    continue

            kind = _adjust_kind_for_context(node, lang_name, kind_map[node_type], source_bytes)

            # Python decorated_definition: push the inner definition only
            if lang_name == "python" and node_type == "decorated_definition":
                inner = node.child_by_field_name("definition")
                if inner:
                    stack.append(inner)
                continue

            name = _extract_name(node, source_bytes)
            if name:
                docstring = (
                    _extract_python_docstring(node, source_bytes)
                    if lang_name == "python"
                    else _extract_comment_docstring(node, source_bytes)
                )
                start_byte, end_byte = _symbol_span(node, lang_name)
                results.append({
                    "name": name,
                    "file": rel_path,
                    "kind": kind,
                    "start_byte": start_byte,
                    "end_byte": end_byte,
                    "signature": _extract_signature(node, source_bytes),
                    "docstring": docstring,
                })

        stack.extend(reversed(node.children))


def _parse_tree_sitter_source(source_bytes: bytes, ext: str, rel_path: str) -> list[SymbolDict]:
    if not _TREE_SITTER_AVAILABLE:
        return []

    lang_name, language = _get_language(ext)
    if language is None:
        return []

    try:
        parser = TSParser(language)
        tree = parser.parse(source_bytes)
    except Exception as exc:
        logger.warning("tree-sitter parse failed for %s: %s", rel_path, exc)
        return []

    results: list[SymbolDict] = []
    _walk_and_extract(tree.root_node, source_bytes, lang_name, rel_path, results)
    return results


def _parse_markdown(source_bytes: bytes, rel_path: str) -> list[SymbolDict]:
    results: list[SymbolDict] = []
    headings: list[tuple[int, int, str, str]] = []
    fence: tuple[bytes, int, str | None, int] | None = None

    for line_start, line_end, line in _iter_line_spans(source_bytes):
        parsed_fence = _parse_markdown_fence(line)
        if parsed_fence:
            marker, length, info = parsed_fence
            if fence is None:
                fence = (marker, length, _markdown_code_extension(info), line_end)
            elif marker == fence[0] and length >= fence[1]:
                _, _, code_ext, code_start = fence
                if code_ext is not None and line_start > code_start:
                    code_bytes = source_bytes[code_start:line_start]
                    for sym in _parse_tree_sitter_source(code_bytes, code_ext, rel_path):
                        sym["start_byte"] += code_start
                        sym["end_byte"] += code_start
                        results.append(sym)
                fence = None
            continue

        if fence is not None:
            continue

        heading = _parse_markdown_heading(line)
        if heading is not None:
            name, signature = heading
            headings.append((line_start, line_end, name, signature))

    for idx, (start_byte, heading_end, name, signature) in enumerate(headings):
        end_byte = headings[idx + 1][0] if idx + 1 < len(headings) else len(source_bytes)
        results.append({
            "name": name,
            "file": rel_path,
            "kind": "section",
            "start_byte": start_byte,
            "end_byte": end_byte,
            "signature": signature,
            "docstring": _markdown_docstring(source_bytes[heading_end:end_byte]),
        })

    return sorted(results, key=lambda sym: sym["start_byte"])


def parse_file(file_path: str, repo_root: str) -> list[SymbolDict]:
    """Parse a source file and return a list of symbol dicts.

    Returns [] for unsupported extensions or parse failures. Never raises.
    """
    ext = os.path.splitext(file_path)[1].lower()
    rel_path = os.path.relpath(file_path, repo_root).replace("\\", "/")

    try:
        with open(file_path, "rb") as fh:
            source_bytes = fh.read()
    except OSError as exc:
        logger.warning("Could not read %s: %s", file_path, exc)
        return []

    if ext in _MARKDOWN_EXTENSIONS:
        return _parse_markdown(source_bytes, rel_path)

    if not _TREE_SITTER_AVAILABLE:
        return []

    # Vue SFCs: extract <script> block and parse as JS/TS — no extra dependency needed.
    if ext == ".vue":
        script_bytes, script_offset, lang_name = _extract_vue_script(source_bytes)
        if not script_bytes.strip():
            return []
        results = _parse_tree_sitter_source(
            script_bytes,
            ".ts" if lang_name == "typescript" else ".js",
            rel_path,
        )
        for sym in results:
            sym["start_byte"] += script_offset
            sym["end_byte"] += script_offset
        return results

    return _parse_tree_sitter_source(source_bytes, ext, rel_path)

