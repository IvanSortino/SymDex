# Copyright (c) 2026 Muhammad Husnain
# This file is part of SymDex.
# License: See LICENSE file in the project root.
#
# Tests for get_graph_diagram MCP tool and build_mermaid_diagram.

import pytest

from symdex.graph.diagram import build_mermaid_diagram, _lang_color


# ── Unit tests for build_mermaid_diagram ────────────────────────────────────────

def test_empty_graph_returns_valid_mermaid():
    """Empty edge list produces a minimal valid Mermaid header and zero counts."""
    result = build_mermaid_diagram([], {})
    assert result["diagram"] == "graph LR"
    assert result["node_count"] == 0
    assert result["edge_count"] == 0
    assert result["truncated"] is False


def test_three_node_graph():
    """Three nodes with two edges produces correct diagram structure."""
    symbols = {
        1: {"id": 1, "file": "src/cli.py",     "name": "main",   "kind": "function"},
        2: {"id": 2, "file": "src/parser.py",  "name": "parse",  "kind": "function"},
        3: {"id": 3, "file": "src/storage.py", "name": "store",  "kind": "function"},
    }
    edges = [
        {"caller_id": 1, "callee_name": "parse", "callee_file": "src/parser.py",
         "caller_file": "src/cli.py",     "caller_name": "main"},
        {"caller_id": 2, "callee_name": "store", "callee_file": "src/storage.py",
         "caller_file": "src/parser.py",  "caller_name": "parse"},
    ]
    result = build_mermaid_diagram(edges, symbols, direction="LR")

    assert result["node_count"] == 3
    assert result["edge_count"] == 2
    assert result["diagram"].startswith("graph LR")
    assert "-->" in result["diagram"]
    assert result["truncated"] is False


def test_language_color_python():
    """Python files get the correct hex color."""
    assert _lang_color("main.py") == "#3572A5"


def test_language_color_default():
    """Unknown extensions fall back to the default color."""
    assert _lang_color("main.xyz") == "#cccccc"


def test_language_color_javascript():
    assert _lang_color("app.js") == "#f1e05a"


def test_language_color_typescript():
    assert _lang_color("index.ts") == "#2b7489"


def test_language_color_go():
    assert _lang_color("main.go") == "#00ADD8"


def test_language_color_rust():
    assert _lang_color("lib.rs") == "#dea584"


def test_direction_td():
    """TD direction is reflected in the diagram header."""
    result = build_mermaid_diagram([], {}, direction="TD")
    assert result["diagram"] == "graph TD"


def test_truncation():
    """When unique files exceed max_nodes, truncated flag is set."""
    # Build edges between 10 distinct files (pairs 0->1, 1->2, ... 9->0)
    symbols = {}
    edges = []
    for i in range(10):
        symbols[i] = {"id": i, "file": f"src/file{i}.py", "name": f"fn{i}", "kind": "function"}
    for i in range(10):
        j = (i + 1) % 10
        edges.append({
            "caller_id": i,
            "callee_name": f"fn{j}",
            "callee_file": f"src/file{j}.py",
            "caller_file": f"src/file{i}.py",
            "caller_name": f"fn{i}",
        })
    result = build_mermaid_diagram(edges, symbols, max_nodes=5)
    assert result["truncated"] is True
    assert result["node_count"] <= 5


def test_node_ids_are_safe_aliases():
    """Node IDs must not contain slashes or dots (safe n0, n1, ... aliases)."""
    symbols = {
        1: {"id": 1, "file": "src/some/deep/path.py", "name": "fn1", "kind": "function"},
        2: {"id": 2, "file": "lib/other/module.py",   "name": "fn2", "kind": "function"},
    }
    edges = [
        {"caller_id": 1, "callee_name": "fn2", "callee_file": "lib/other/module.py",
         "caller_file": "src/some/deep/path.py", "caller_name": "fn1"},
    ]
    result = build_mermaid_diagram(edges, symbols)
    # Node IDs like n0, n1 should appear; raw paths must not appear as node IDs
    lines = result["diagram"].splitlines()
    edge_lines = [l for l in lines if "-->" in l]
    for line in edge_lines:
        # Each side of --> must be a safe alias like n0, n1
        parts = line.strip().split("-->")
        left = parts[0].strip().split("|")[0].strip()
        assert left.startswith("n") and left[1:].isdigit(), f"Unsafe node ID: {left!r}"
