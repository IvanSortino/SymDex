---
name: symdex-code-search
description: Use when finding, reading, tracing, or understanding code in a SymDex-backed repository. Triggers on locating symbols, exploring unfamiliar code, following call graphs, searching HTTP routes, checking index freshness, or replacing Read/Grep/Glob during code exploration.
---

# SymDex Code Search

Use SymDex first for code exploration.

## Session Start

1. Check whether the current worktree is indexed.
2. If you already know the repo id, use `get_index_status(repo=...)`.
3. If not indexed, run `symdex index .` from the current worktree and let SymDex derive the repo name automatically.
4. After indexing, keep using the returned repo id for the rest of the session.
5. If you switch worktrees, check status again before searching.

## Tool Choice

- Find symbol definitions: `search_symbols`
- Find code by intent: `semantic_search`
- Find literal text: `text_search`
- Read exact source for a symbol: `get_symbol`
- Get a file outline: `focus_file`
- Find callers: `get_callers`
- Find callees: `get_callees`
- Find HTTP routes: `search_routes`
- Check freshness and repo status: `get_index_status`
- List indexed repos: `list_repos`
- Clean stale indexes: `gc_stale_indexes`

## Workflow

1. Search first.
2. Read the smallest exact slice you need.
3. Use callers and callees before refactors.
4. Use routes for endpoint discovery.
5. Fall back to normal file reads only when SymDex cannot answer.

## Rules

- Always scope tool calls with `repo` when you know it.
- Do not invent committed naming files or `.env` workarounds.
- Do not read whole files just to hunt for a symbol.
- For generated files or unsupported file types, use normal file browsing as a fallback.

## Editing

When you need to edit code:

1. Use SymDex to find the exact symbol or file location.
2. Read only that file or symbol slice.
3. Make the smallest change needed.

