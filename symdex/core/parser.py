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

logger = logging.getLogger(__name__)

# Map file extension -> (language_name, grammar_module, preferred_loader_attr)
_EXT_MAP: dict[str, tuple[str, str, Optional[str]]] = {
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
    },
    "typescript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "interface_declaration": "class",
    },
    "go": {
        "function_declaration": "function",
        "method_declaration": "method",
        "type_declaration": "class",
    },
    "rust": {
        "function_item": "function",
        "struct_item": "class",
        "impl_item": "class",
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
    try:
        mod = importlib.import_module(module_name)
        loader_candidates = []
        if preferred_loader:
            loader_candidates.append(preferred_loader)
        loader_candidates.extend(
            [
                "language",
                f"language_{lang_name}",
                "language_typescript",
                "language_php",
                "language_php_only",
            ]
        )
        language = None
        for attr in dict.fromkeys(loader_candidates):
            fn = getattr(mod, attr, None)
            if callable(fn):
                language = Language(fn())
                break
        if language is None:
            raise AttributeError(
                f"No supported language loader found in module {module_name}"
            )
        return lang_name, language
    except Exception as exc:
        logger.warning("Could not load grammar %s: %s", module_name, exc)
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
        if child.type in ("identifier", "type_identifier", "field_identifier", "constant"):
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
            if value and value.type == "arrow_function":
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

        if node_type in kind_map:
            kind = kind_map[node_type]

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
                results.append({
                    "name": name,
                    "file": rel_path,
                    "kind": kind,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                    "signature": _extract_signature(node, source_bytes),
                    "docstring": docstring,
                })

        stack.extend(reversed(node.children))


def parse_file(file_path: str, repo_root: str) -> list[SymbolDict]:
    """Parse a source file and return a list of symbol dicts.

    Returns [] for unsupported extensions or parse failures. Never raises.
    """
    if not _TREE_SITTER_AVAILABLE:
        return []

    ext = os.path.splitext(file_path)[1].lower()

    # Vue SFCs: extract <script> block and parse as JS/TS — no extra dependency needed.
    if ext == ".vue":
        try:
            with open(file_path, "rb") as fh:
                source_bytes = fh.read()
        except OSError as exc:
            logger.warning("Could not read %s: %s", file_path, exc)
            return []
        script_bytes, script_offset, lang_name = _extract_vue_script(source_bytes)
        if not script_bytes.strip():
            return []
        _, language = _get_language(".ts" if lang_name == "typescript" else ".js")
        if language is None:
            return []
        try:
            parser = TSParser(language)
            tree = parser.parse(script_bytes)
        except Exception as exc:
            logger.warning("tree-sitter parse failed for %s: %s", file_path, exc)
            return []
        rel_path = os.path.relpath(file_path, repo_root).replace("\\", "/")
        results: list[SymbolDict] = []
        _walk_and_extract(tree.root_node, script_bytes, lang_name, rel_path, results)
        for sym in results:
            sym["start_byte"] += script_offset
            sym["end_byte"] += script_offset
        return results

    lang_name, language = _get_language(ext)

    if language is None:
        return []

    try:
        with open(file_path, "rb") as fh:
            source_bytes = fh.read()
    except OSError as exc:
        logger.warning("Could not read %s: %s", file_path, exc)
        return []

    try:
        parser = TSParser(language)
        tree = parser.parse(source_bytes)
    except Exception as exc:
        logger.warning("tree-sitter parse failed for %s: %s", file_path, exc)
        return []

    rel_path = os.path.relpath(file_path, repo_root).replace("\\", "/")
    results: list[SymbolDict] = []
    _walk_and_extract(tree.root_node, source_bytes, lang_name, rel_path, results)
    return results

