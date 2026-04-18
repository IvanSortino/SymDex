# symdex/graph/diagram.py
# Copyright (c) 2026 Muhammad Husnain
# License: See LICENSE file in the project root.

"""Mermaid diagram generation from the SymDex call graph."""

from __future__ import annotations

import os
from collections import Counter


# ── Language colours ────────────────────────────────────────────────────────────

_LANG_COLORS: dict[str, str] = {
    ".py":  "#3572A5",
    ".js":  "#f1e05a",
    ".cjs": "#f1e05a",
    ".cjsx": "#f1e05a",
    ".jsx": "#f1e05a",
    ".mjs": "#f1e05a",
    ".mjsx": "#f1e05a",
    ".ts":  "#2b7489",
    ".cts": "#2b7489",
    ".mts": "#2b7489",
    ".tsx": "#2b7489",
    ".ctsx": "#2b7489",
    ".mtsx": "#2b7489",
    ".go":  "#00ADD8",
    ".rs":  "#dea584",
    ".html": "#e34c26",
    ".htm": "#e34c26",
    ".css": "#563d7c",
    ".scss": "#c6538c",
    ".sass": "#c6538c",
    ".less": "#1d365d",
    ".stylus": "#ff6347",
    ".styl": "#ff6347",
    ".sh": "#89e051",
    ".bash": "#89e051",
    ".zsh": "#89e051",
    ".svelte": "#ff3e00",
}


def _lang_color(filename: str) -> str:
    """Return the hex colour string for a given filename's extension."""
    ext = os.path.splitext(filename)[1].lower()
    return _LANG_COLORS.get(ext, "#cccccc")


# ── Cycle detection ─────────────────────────────────────────────────────────────

def _detect_cycles(adj: dict[str, set[str]]) -> set[tuple[str, str]]:
    """Return the set of (from_file, to_file) edges that participate in a cycle.

    Uses a DFS with a colour-marking scheme (white/grey/black).
    An edge u->v is a cycle edge when v is in the current DFS stack (grey).
    """
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in adj}
    # Ensure every target is also in color
    for targets in adj.values():
        for t in targets:
            if t not in color:
                color[t] = WHITE

    cycle_edges: set[tuple[str, str]] = set()

    def dfs(u: str, stack: set[str]) -> None:
        color[u] = GREY
        stack.add(u)
        for v in adj.get(u, set()):
            if color.get(v, WHITE) == GREY:
                cycle_edges.add((u, v))
            elif color.get(v, WHITE) == WHITE:
                dfs(v, stack)
        color[u] = BLACK
        stack.discard(u)

    for node in list(color):
        if color[node] == WHITE:
            dfs(node, set())

    return cycle_edges


# ── Main diagram builder ─────────────────────────────────────────────────────────

def build_mermaid_diagram(
    edges: list[dict],
    symbols: dict[int, dict],
    direction: str = "LR",
    max_nodes: int = 50,
) -> dict:
    """Build a Mermaid diagram string from call-graph edges and symbol metadata.

    Args:
        edges:     Rows from the edges table; each dict must have at minimum
                   ``caller_file`` and ``callee_file``.
        symbols:   Mapping of symbol id -> symbol row (``{id, file, name, kind}``).
        direction: Mermaid graph direction — ``"LR"`` or ``"TD"``.
        max_nodes: Maximum distinct file nodes to include; excess triggers
                   truncation by keeping the highest-frequency files.

    Returns:
        ``{diagram: str, node_count: int, edge_count: int, truncated: bool}``
    """
    if not edges:
        return {"diagram": f"graph {direction}", "node_count": 0, "edge_count": 0, "truncated": False}

    # Collect all unique files referenced by edges
    all_files: set[str] = set()
    for e in edges:
        cf = e.get("caller_file")
        tf = e.get("callee_file")
        if cf:
            all_files.add(cf)
        if tf:
            all_files.add(tf)

    truncated = False
    if len(all_files) > max_nodes:
        # Keep the files that appear most frequently
        freq: Counter[str] = Counter()
        for e in edges:
            cf = e.get("caller_file")
            tf = e.get("callee_file")
            if cf:
                freq[cf] += 1
            if tf:
                freq[tf] += 1
        kept = {f for f, _ in freq.most_common(max_nodes)}
        all_files = kept
        truncated = True

    # Assign stable safe aliases
    sorted_files = sorted(all_files)
    alias: dict[str, str] = {f: f"n{i}" for i, f in enumerate(sorted_files)}

    # Filter edges to those whose both endpoints are in the kept file set
    valid_edges: list[tuple[str, str]] = []
    for e in edges:
        cf = e.get("caller_file")
        tf = e.get("callee_file")
        if cf and tf and cf in all_files and tf in all_files and cf != tf:
            valid_edges.append((cf, tf))

    # Deduplicate edges while preserving order
    seen_pairs: set[tuple[str, str]] = set()
    deduped_edges: list[tuple[str, str]] = []
    for pair in valid_edges:
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            deduped_edges.append(pair)

    # Build adjacency map for cycle detection
    adj: dict[str, set[str]] = {}
    for src, dst in deduped_edges:
        adj.setdefault(src, set()).add(dst)

    cycle_edges = _detect_cycles(adj)

    # Render diagram
    lines: list[str] = [f"graph {direction}"]

    # Node declarations
    for f in sorted_files:
        basename = os.path.basename(f)
        lines.append(f'    {alias[f]}["{basename}"]')

    # Edge declarations
    cycle_edge_indices: list[int] = []
    for idx, (src, dst) in enumerate(deduped_edges):
        a_src = alias[src]
        a_dst = alias[dst]
        if (src, dst) in cycle_edges:
            lines.append(f"    {a_src} -->|cycle| {a_dst}")
            cycle_edge_indices.append(idx)
        else:
            lines.append(f"    {a_src} --> {a_dst}")

    # Cycle edge colouring via linkStyle
    for idx in cycle_edge_indices:
        lines.append(f"    linkStyle {idx} stroke:red")

    # Language colouring via style directives
    for f in sorted_files:
        color = _lang_color(f)
        lines.append(f"    style {alias[f]} fill:{color}")

    diagram = "\n".join(lines)

    return {
        "diagram": diagram,
        "node_count": len(sorted_files),
        "edge_count": len(deduped_edges),
        "truncated": truncated,
    }
