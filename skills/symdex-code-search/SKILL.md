---
name: symdex-code-search
description: |
  Guide for using SymDex as the primary code-exploration layer in an indexed repository.
  Use when locating symbols, exploring unfamiliar code, tracing callers or callees,
  searching HTTP routes, checking index freshness, or replacing Read/Grep/Glob during
  code exploration.
---

# SymDex Code Search

Use SymDex first for code exploration.

## What This Skill Does

- Replaces broad file browsing with SymDex-backed discovery
- Uses symbol search, semantic search, route search, and call graphs
- Keeps reads small by jumping to the exact symbol or file slice
- Verifies index freshness before searching

## What This Skill Does Not Do

- It does not invent repo naming files or commit helper config
- It does not read whole files when a symbol-level lookup is enough
- It does not replace normal file reads when SymDex cannot cover a case

## Examples

- "Find the function that validates JWTs"
- "What calls this route handler?"
- "Show me the outline of this file"
- "Search for the code that parses webhook payloads"
- "Find the HTTP route for /api/checkout"

## Session Start

1. Check whether the current worktree is indexed.
2. If you already know the repo id, use `get_index_status(repo=...)`.
3. If not indexed, run `symdex index .` from the current worktree and let SymDex derive the repo name automatically.
4. After indexing, reuse the returned repo id for the rest of the session.
5. If you switch worktrees, check status again before searching.

## Tool Choice

| Need | Tool |
|------|------|
| Find a function, class, or method by name | `search_symbols` |
| Find code by intent or behavior | `semantic_search` |
| Find literal text or regex matches | `text_search` |
| Read exact source for one symbol | `get_symbol` |
| Get a file outline before reading | `focus_file` |
| Trace who calls a symbol | `get_callers` |
| Trace what a symbol calls | `get_callees` |
| Find HTTP routes | `search_routes` |
| Check repo freshness | `get_index_status` |
| List indexes | `list_repos` |
| Clean deleted-worktree indexes | `gc_stale_indexes` |

## Workflow

1. Search first.
2. Prefer the smallest exact slice you need.
3. Use callers and callees before refactors.
4. Use routes for endpoint discovery.
5. Fall back to normal file reads only when SymDex cannot answer.

## Decision Guide

- "Where is X defined?" -> `search_symbols`
- "What does this do?" -> `semantic_search`, then `get_symbol`
- "Who uses this?" -> `get_callers`
- "What does this call?" -> `get_callees`
- "Where is the endpoint?" -> `search_routes`
- "Is the index current?" -> `get_index_status`

## Rules

- Always scope tool calls with `repo` when you know it.
- Use `list_repos` or `get_index_status` when the repo id is unclear.
- Do not read whole files just to hunt for a symbol.
- For generated files or unsupported file types, use normal file browsing as a fallback.

## Editing

When you need to edit code:

1. Use SymDex to find the exact symbol or file location.
2. Read only that file or symbol slice.
3. Make the smallest change needed.

## Good Use Cases

- Locating a symbol before editing
- Tracing dependencies before refactoring
- Exploring an unfamiliar repository
- Finding the route that serves a request path
- Checking whether the current index is fresh enough to trust

## Output Checklist

- [ ] Repo id confirmed or derived
- [ ] Index freshness checked
- [ ] SymDex tool chosen before broad file reads
- [ ] Exact symbol or slice read instead of whole file when possible
- [ ] Fall back to normal file reads only when needed
