# AGENTS.md

SymDex is a repo-local code retrieval system for AI coding agents.
Use it to retrieve the exact symbol, route, caller, callee, or file slice you need instead of reading whole files blindly.

## What SymDex Is

- Repo-local MCP and CLI tooling for code exploration
- Built around exact symbol extraction, semantic search, route extraction, call graphs, and repo stats
- Optimized for lower-token retrieval and faster agent navigation
- Currently covers 16 language surfaces, including Python, Go, Kotlin, Dart, Swift, and Vue script blocks

## Default Workflow For Agents

1. Confirm whether the current worktree already has a SymDex index.
2. If the repo id is known, pass `repo` on every scoped tool call.
3. If the repo id is unknown, use `list_repos` or index the current folder and reuse the returned repo id.
4. Check freshness with `get_index_status(repo)`.
5. Search first with `search_symbols`, `semantic_search`, or `search_text`.
6. Narrow to `get_symbol` or `get_file_outline` before reading full files.
7. Use `get_callers`, `get_callees`, `search_routes`, or `get_repo_stats` before manual tracing.
8. Fall back to broad file reads only when SymDex cannot answer precisely enough.

## Tool Map

| Need | Preferred Tool |
|---|---|
| Index the current worktree | `index_folder` |
| Register and index a repo explicitly | `index_repo` |
| Find a function, class, or method by name | `search_symbols` |
| Find code by intent or behavior | `semantic_search` |
| Find literal or regex text | `search_text` |
| Read exact source for one symbol | `get_symbol` |
| Inspect a file before reading it | `get_file_outline` |
| Get a repo tree or summary | `get_file_tree`, `get_repo_outline`, `get_repo_stats` |
| Trace who calls a symbol | `get_callers` |
| Trace what a symbol calls | `get_callees` |
| Find HTTP routes | `search_routes` |
| Check freshness and watcher state | `get_index_status` |
| List available indexes | `list_repos` |
| Clean deleted-worktree indexes | `gc_stale_indexes` |

## State And Repo Rules

- Default state directory is `~/.symdex`.
- Optional workspace-local state lives in `./.symdex` when `SYMDEX_STATE_DIR=.symdex` or `symdex --state-dir .symdex ...` is used.
- Workspace-local mode writes repo databases, `registry.db`, and a human-readable `registry.json` manifest inside `./.symdex`.
- When local state already exists, commands run inside that workspace auto-discover and reuse it.
- `--repo` is the canonical naming flag.
- If `--repo` is omitted on `index` or `watch`, SymDex auto-generates a stable repo id from the current git branch and worktree path hash.

## Install And Upgrade

```bash
pip install symdex
pip install "symdex[local]"
pip install "symdex[voyage]"
uv tool install "symdex[local]"
uvx symdex --help
```

Upgrade commands:

```bash
py -m pip install -U symdex
uv tool upgrade symdex
uvx symdex@latest --help
```

Install the public SymDex skill:

```bash
npx skills add https://github.com/husnainpk/SymDex --skill symdex-code-search --yes --global
```

## Current Product Truth

- `symdex index` prints a code summary with files, Lines of Code, symbol counts, routes, skipped files, and language breakdown.
- Successful `search`, `find`, `text`, and `semantic` commands print approximate token-savings footers. MCP search tools also return structured `roi` data plus a plain-English `roi_summary`.
- Normal human-facing CLI commands can show an upgrade notice when a newer SymDex release is available.
- Local semantic search is optional through `symdex[local]`.
- Voyage AI is optional through `symdex[voyage]` or `symdex[voyage-multimodal]`.
- Kotlin, Dart, and Swift are first-class parser targets.

## Boundaries

- SymDex is not a full type checker.
- SymDex is not an automated refactoring engine.
- SymDex is strongest when used as the repo-local retrieval layer that sits beside editors, LSPs, and agents.
