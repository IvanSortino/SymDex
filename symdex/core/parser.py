# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.

import importlib
import logging
import os
from typing import Optional, TypedDict

try:
    from tree_sitter import Language, Parser as TSParser
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    _TREE_SITTER_AVAILABLE = False
    Language = None  # type: ignore
    TSParser = None  # type: ignore

logger = logging.getLogger(__name__)

# Map file extension → (language_name, grammar_module)
_EXT_MAP: dict[str, tuple[str, str]] = {
    ".py":   ("python",     "tree_sitter_python"),
    ".js":   ("javascript", "tree_sitter_javascript"),
    ".mjs":  ("javascript", "tree_sitter_javascript"),
    ".ts":   ("typescript", "tree_sitter_typescript"),
    ".tsx":  ("typescript", "tree_sitter_typescript"),
    ".go":   ("go",         "tree_sitter_go"),
    ".rs":   ("rust",       "tree_sitter_rust"),
    ".java": ("java",       "tree_sitter_java"),
    ".php":  ("php",        "tree_sitter_php"),
    ".cs":   ("c_sharp",    "tree_sitter_c_sharp"),
    ".c":    ("c",          "tree_sitter_c"),
    ".h":    ("cpp",        "tree_sitter_cpp"),
    ".cpp":  ("cpp",        "tree_sitter_cpp"),
    ".cc":   ("cpp",        "tree_sitter_cpp"),
    ".ex":   ("elixir",     "tree_sitter_elixir"),
    ".exs":  ("elixir",     "tree_sitter_elixir"),
    ".rb":   ("ruby",       "tree_sitter_ruby"),
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
    lang_name, module_name = entry
    try:
        mod = importlib.import_module(module_name)
        language = Language(mod.language())
        return lang_name, language
    except Exception as exc:
        logger.warning("Could not load grammar %s: %s", module_name, exc)
        return lang_name, None


def _extract_name(node, source_bytes: bytes) -> Optional[str]:
    """Extract identifier name from a definition node."""
    name_node = node.child_by_field_name("name")
    if name_node:
        return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
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

    ext = os.path.splitext(file_path)[1]
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
