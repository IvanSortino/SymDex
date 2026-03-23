# SymDex Specification

## Product Definition

SymDex is a repo-local codebase oracle for AI coding agents.
It indexes source code into a fast local SQLite-backed retrieval layer so agents can jump directly to the right symbol, route, caller, callee, or file outline without reading whole files blindly.

## Current Product State

- Current version: `0.1.19`
- Release tag at this checkout: `v0.1.19`
- Delivery surfaces: CLI, stdio MCP server, streamable HTTP MCP server
- Current MCP tool count: 20
- Supported language surfaces: 16
- Default state directory: `~/.symdex`
- Optional workspace-local state directory: `./.symdex`

## Core Capability Set

- Exact symbol search with byte offsets
- Semantic search for intent-based discovery
- Indexed text search
- File outlines and repo outlines
- Caller and callee tracing
- Circular dependency detection and graph diagrams
- HTTP route extraction across major backend stacks
- Repo stats including language mix and Lines of Code
- Watch mode and targeted invalidation
- Approximate token-savings reporting after successful search commands
- Upgrade notices on normal human-facing CLI commands

## CLI Surface

Primary human-facing commands:

- `symdex index`
- `symdex watch`
- `symdex search`
- `symdex find`
- `symdex text`
- `symdex semantic`
- `symdex outline`
- `symdex callers`
- `symdex callees`
- `symdex routes`
- `symdex repos`
- `symdex invalidate`
- `symdex gc`
- `symdex serve`

Behavior guarantees:

- `symdex index` prints a post-index code summary.
- Successful search commands print approximate token-savings footers.
- `--repo` is the canonical repo naming flag.
- Omitting `--repo` on `index` and `watch` auto-derives a stable repo id from the current git branch and worktree path hash.
- `--json` stays machine-readable and suppresses human upgrade messaging.

## MCP Surface

SymDex currently exposes these 20 MCP tools:

- `index_folder`
- `index_repo`
- `search_symbols`
- `semantic_search`
- `search_text`
- `get_symbol`
- `get_symbols`
- `get_file_outline`
- `get_file_tree`
- `get_repo_outline`
- `get_callers`
- `get_callees`
- `search_routes`
- `get_index_status`
- `get_repo_stats`
- `get_graph_diagram`
- `find_circular_deps`
- `list_repos`
- `invalidate_cache`
- `gc_stale_indexes`

## Supported Languages

SymDex currently parses and indexes these language surfaces:

- Python
- JavaScript
- TypeScript
- Go
- Rust
- Java
- Kotlin
- Dart
- Swift
- PHP
- C#
- C
- C++
- Elixir
- Ruby
- Vue script blocks

## Route Coverage

Route extraction currently covers:

- Flask, FastAPI, and Django path declarations
- Express and related JS or TS router patterns
- Spring and Spring-style Kotlin mappings
- Laravel route declarations
- Gin, Echo, Fiber, chi-style Go handlers, and generic `Handle` or `HandleFunc`
- ASP.NET attribute routes
- Rails and Sinatra route DSLs
- Phoenix router declarations
- Actix route attributes

## Storage Model

Default mode:

- Repo databases live under `~/.symdex`
- Central registry lives under `~/.symdex`

Workspace-local mode:

- Enabled via `SYMDEX_STATE_DIR=.symdex` or `symdex --state-dir .symdex ...`
- Stores `./.symdex/<repo>.db`
- Stores `./.symdex/registry.db`
- Stores `./.symdex/registry.json`
- Uses relative `root_path` and `db_path` values in `registry.json`
- Records `last_indexed` in `YYYY-MM-DD HH:mm:ss`
- Auto-discovers local state from nested directories once the workspace has been initialized

## Index And Search Output

Index output includes:

- files indexed
- Lines of Code
- functions, classes, methods, constants, and variables where available
- route count
- language breakdown
- skipped files
- error count
- elapsed time

Search ROI output includes approximate:

- lines searched
- tokens that would likely have been spent without SymDex
- tokens used with SymDex
- tokens saved

## Embedding Backends

Base `symdex` installs the lean core.

Optional extras:

- `symdex[local]` for local `sentence-transformers`
- `symdex[voyage]` for Voyage text embeddings
- `symdex[voyage-multimodal]` for Voyage text plus images and PDFs
- `symdex[all]` for the combined stack

Requirements:

- local semantic search requires `symdex[local]`
- Voyage text mode requires `symdex[voyage]`
- Voyage multimodal mode requires `symdex[voyage-multimodal]`
- SymDex must print actionable install hints when the selected backend extra is missing

## Positioning

SymDex is optimized for precise repo-local retrieval for agents.
It is intentionally not a full type checker or automated refactoring engine.
The product boundary is deliberate: SymDex complements editors, language servers, and model-driven coding workflows instead of replacing all of them.

## Release And Documentation Rules

- Public docs must reflect the actual checked-out product surface.
- Repo descriptions, README claims, and skill instructions must stay aligned.
- Release pipelines must build, validate, smoke-test, and publish immutable artifacts from a tag-driven flow.
- New docs must prefer stable product truth over stale historical phase notes.

## Known Operational Constraints

- Local pytest runs in this workspace can still hit a Windows temp-directory teardown permission issue.
- Public PyPI visibility must be verified independently from GitHub Actions whenever release status matters.

## Near-Term Priorities

- Keep parser and route extraction regressions tight across all supported languages.
- Keep README, skill docs, and repo metadata aligned after every release-level feature change.
- Continue hardening packaging and release verification so PyPI status is explicit and trustworthy.
