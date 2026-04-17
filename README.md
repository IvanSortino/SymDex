<div align="center">

# SymDex

**The codebase oracle AI coding agents wish every repo already had.**

*Index once. Jump straight to the exact symbol, route, caller, callee, or file slice. Read only what you need.*

<br>

[![PyPI](https://img.shields.io/pypi/v/symdex?style=for-the-badge&color=3572A5&label=PyPI)](https://pypi.org/project/symdex/)
[![Downloads](https://img.shields.io/pypi/dm/symdex?style=for-the-badge&color=00ADD8&label=installs%2Fmonth)](https://pypi.org/project/symdex/)
[![Python](https://img.shields.io/pypi/pyversions/symdex?style=for-the-badge&color=f1e05a&labelColor=333)](https://pypi.org/project/symdex/)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](https://github.com/husnainpk/symdex/blob/main/LICENSE)
[![Stars](https://img.shields.io/github/stars/husnainpk/symdex?style=for-the-badge&color=f59e0b)](https://github.com/husnainpk/symdex/stargazers)

<br>

[![Cursor](https://img.shields.io/badge/Cursor-black?style=flat-square)](https://cursor.sh)
[![Codex](https://img.shields.io/badge/Codex_CLI-black?style=flat-square&logo=openai)](https://github.com/openai/codex)
[![Gemini](https://img.shields.io/badge/Gemini_CLI-black?style=flat-square&logo=google)](https://github.com/google-gemini/gemini-cli)
[![Copilot](https://img.shields.io/badge/GitHub_Copilot-black?style=flat-square&logo=github)](https://github.com/features/copilot)
[![Windsurf](https://img.shields.io/badge/Windsurf-black?style=flat-square)](https://codeium.com/windsurf)
[![Roo](https://img.shields.io/badge/Roo-black?style=flat-square)](https://roocode.com)
[![Kilo](https://img.shields.io/badge/Kilo_Code-black?style=flat-square)](https://kilocode.ai)

<br>

<h2 align="center">7,500 tokens -> 200 tokens</h2>
<p align="center"><strong>Per lookup. Every lookup. Approximate, but directionally real.</strong></p>
<p align="center">
  <img src="docs/images/symdex-hero-16x9.png" alt="SymDex hero visual showing token reduction and code intelligence workflow" width="100%" />
</p>

```bash
# Install the lean core
pip install symdex

# Add local semantic search when you want the sentence-transformers backend
pip install "symdex[local]"

# Or install the local-backend CLI as an isolated tool
uv tool install "symdex[local]"

# Or run without installing
uvx symdex --help

# Upgrade an existing install
py -m pip install -U symdex
uv tool upgrade symdex
uvx symdex@latest --help

# Install the SymDex agent skill globally for supported agents
npx skills add https://github.com/husnainpk/SymDex --skill symdex-code-search --yes --global
```

</div>

---

## What SymDex Does

AI coding agents are useful until they have to rediscover your repo from scratch. They open whole files, grep broad patterns, miss the route handler, read the same utility twice, and spend thousands of tokens just getting oriented.

SymDex gives agents a repo-local retrieval layer before they start reading code.

It indexes your project into a small local SQLite knowledge base with:

- exact symbols and byte offsets
- file outlines and repo summaries
- literal text search
- optional semantic search
- callers, callees, and circular dependency checks
- extracted HTTP routes
- a registry for one repo, many repos, or many worktrees

Then agents can ask for the narrow slice they need: the function, route, caller chain, file outline, or intent match. That means less blind browsing, less context waste, and answers that can explain how much token budget SymDex saved.

SymDex is local-first. Base `symdex` keeps symbol, text, route, graph, and MCP features lean. Install `symdex[local]` only when you want local semantic embeddings, or use the Voyage extras when you want hosted embeddings and optional multimodal indexing.

Current product stage as of April 17, 2026:

- package version `0.1.23`; latest public tag `v0.1.23`
- 20 MCP tools across indexing, search, outlines, routes, stats, graphs, cache invalidation, and stale-index cleanup
- 17 language surfaces, including Markdown headings and supported fenced code blocks
- Android, Flutter, and iOS coverage through Kotlin, Dart, and Swift parser targets
- route extraction across Python, JavaScript/TypeScript, Spring/Kotlin, Laravel, Gin-style Go, ASP.NET, Rails/Sinatra, Phoenix, and Actix
- one-line CLI token-savings footers after successful search commands
- MCP `roi`, `roi_summary`, and `roi_agent_hint` fields so agents can mention savings in their final response
- low-memory `symdex watch` by default: structural refresh without loading embedding models unless `--embed` is passed
- duplicate watcher protection, idle auto-exit, and state-aware watcher metadata
- workspace-local `./.symdex` state for Docker, portable workspaces, and teams that do not want indexes hidden in home directories
- upgrade notices with exact `pip`, `uv tool`, and `uvx` commands when a newer release exists

---

## SymDex Skill For Agents

Install the SymDex code-search skill to make agents use SymDex before broad file browsing:

```bash
npx skills add https://github.com/husnainpk/SymDex --skill symdex-code-search --yes --global
```

If you want the interactive installer instead, omit `--yes --global`.

What it does:
- checks repo/index readiness first
- uses SymDex before Read/Grep/Glob for discovery
- prefers symbol-level and outline-level retrieval over full-file reads
- guides agents toward callers, callees, routes, and semantic search when those are the better fit
- keeps the workflow centered on lower-token code retrieval instead of broad file reads

The skill lives in this repo at `skills/symdex-code-search/SKILL.md` and follows the standard `skills/<name>/SKILL.md` layout.

Installing through the `skills` CLI uses the same public path that skills.sh indexes.

---

## 60-second quickstart

```bash
# Install the lean core
pip install symdex
# or
uv tool install symdex

# Index a project
symdex index ./myproject --repo myproject

# Search by symbol name
symdex search "validate_email" --repo myproject

# Search by literal text
symdex text "JWT" --repo myproject

# Add local semantic search only when you want embeddings
pip install "symdex[local]"

# Search by intent
symdex semantic "check email format" --repo myproject

# Show HTTP routes
symdex routes myproject -m POST

# Start the MCP server
symdex serve
```

Notes:
- If you omit `--repo` on `symdex index` or `symdex watch`, SymDex auto-generates a stable repo id from the current git branch and worktree path hash.
- After indexing, SymDex prints a code summary.
- After successful search commands, SymDex prints a one-line ROI footer with approximate token savings.
- MCP search tools also return `roi_agent_hint`, so agents can fold the savings into their user-facing response instead of burying it in logs.
- When a newer PyPI release exists, normal CLI commands print exact upgrade commands for `pip`, `uv tool`, and `uvx`.
- Set `SYMDEX_STATE_DIR=.symdex` on first index to keep repo databases, `registry.db`, and `registry.json` inside the current workspace. After that, commands run from the workspace auto-discover the local state.
- `--state-dir` can be passed either globally or after the subcommand, for example `symdex --state-dir .symdex repos` or `symdex repos --state-dir .symdex`.
- Canonical CLI commands are `index` and `repos`. Shell compatibility aliases also accept MCP-shaped names like `index-folder`, `index-repo`, and `list-repos`.
- Semantic search requires stored embeddings. If a repo was indexed before `symdex[local]` or Voyage was enabled, re-index it after enabling the backend you want.

Add to your agent config:

```json
{
  "mcpServers": {
    "symdex": {
      "command": "uvx",
      "args": ["symdex", "serve"]
    }
  }
}
```

HTTP mode:

```json
{
  "mcpServers": {
    "symdex": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

---

## Workspace-local state and Docker

SymDex defaults to `~/.symdex` and also supports a workspace-local state directory for portable and containerized workflows.

Use it like this on first setup:

```bash
SYMDEX_STATE_DIR=.symdex symdex index ./myproject --repo myproject
```

That creates:

- `./.symdex/<repo>.db`
- `./.symdex/registry.db`
- `./.symdex/registry.json`

`registry.json` is the human-readable manifest. In workspace-local mode it stores relative `root_path` and `db_path` values, so you can inspect what is indexed without opening SQLite.

After the local state exists, SymDex auto-discovers it from the current workspace or any nested subdirectory.

---

## What you get

<p align="center">
  <img src="docs/images/what-you-get-grid.png" alt="SymDex feature grid showing core capabilities including semantic search, byte-precise extraction, call graph, routes, cross-repo registry, watch mode, and CLI plus MCP tools" width="100%" />
</p>

| Feature | Details |
|---|---|
| Symbol search | Find functions, classes, and methods with exact byte offsets |
| Semantic search | Find code by intent instead of exact name |
| Text search | Search indexed files by literal text across the repo |
| Byte-precise retrieval | Read only the symbol span you need |
| File outline | List symbols in a file without transferring the whole file |
| Repo outline | Get a directory tree plus repo summary through MCP |
| Call graph | Trace callers, callees, and circular dependencies |
| HTTP routes | Extract Flask, FastAPI, Django, Express, Spring/Kotlin, Laravel, Gin-style Go, ASP.NET, Rails/Sinatra, Phoenix, and Actix routes |
| Markdown-aware docs | Index Markdown headings and supported fenced code blocks for SDK docs, specs, repo docs, and design notes |
| Auto-watch | Re-index on change, avoid duplicate watchers, stay low-memory by default, and auto-exit after idle time |
| Cross-repo registry | Manage multiple indexed repos from one local registry |
| Workspace-local state | Keep repo databases, `registry.json`, and watcher metadata inside `./.symdex` for Docker and portable workspaces |
| Search ROI footer | One-line approximate token savings after successful search commands |
| Agent ROI hint | MCP tools return `roi_agent_hint` so agents can mention savings naturally in their replies |
| Code summary | Files, Lines of Code, symbols, routes, skipped files, and languages after indexing |
| Optional embedding backends | Add `symdex[local]` for local embeddings or `symdex[voyage]` for hosted embeddings only when needed |

---

## Where SymDex Fits

SymDex is built for agents that need precise repo-local retrieval without depending on an editor session, hosted index, or heavyweight service stack.

| Approach | Strong at | Tradeoff | Where SymDex differs |
|---|---|---|---|
| Editor-bound LSPs | type-aware navigation and refactors inside the editor | tied to an editor session and weak on intent search | pre-indexed, terminal-first, semantic, and route-aware |
| LSP wrappers for agents | deeper language-server-backed analysis | heavier per-language setup and live-file coupling | one SQLite index per repo and the same interface across repos |
| Graph-backed code indexers | graph-style architecture queries | extra backend/storage complexity | zero-infra local storage with SQLite |
| Docker-heavy hybrid search stacks | chunked semantic search with external services | more moving parts at install and runtime | local-first workflow with simple CLI and MCP setup |
| SymDex | fast repo-local symbol, text, semantic, route, and call-graph retrieval | not a full type checker or automated refactoring engine | optimized for precise retrieval and agent efficiency |

If you need full type-system reasoning or editor-native refactors, a language server still goes deeper. If you need pre-indexed retrieval, repo-local portability, and an MCP-friendly search layer, SymDex is the better fit.

---

## CLI reference

```bash
# Indexing and maintenance
symdex index ./myproject --repo myproject       # Index with an explicit repo id
symdex index ./myproject                        # Auto-name from git branch + path hash
symdex watch ./myproject --repo myproject       # Keep an index fresh without loading embedding models
symdex watch ./myproject --repo myproject --embed  # Also refresh semantic embeddings on change
symdex invalidate --repo myproject              # Force re-index of a repo
symdex invalidate --repo myproject --file app.py
symdex gc                                       # Remove stale index databases
symdex repos                                    # List indexed repos

# Search
symdex search "validate_email" --repo myproject
symdex search "validate_email"                 # Search across all indexed repos
symdex find validate_email --repo myproject     # Exact lookup
symdex text "JWT" --repo myproject
symdex semantic "check auth token" --repo myproject

# Navigation
symdex outline auth/utils.py --repo myproject
symdex callers validate_email --repo myproject
symdex callees validate_email --repo myproject
symdex routes myproject
symdex routes myproject --method POST
symdex routes myproject --path /api

# Server
symdex serve
symdex serve --port 8080
```

MCP currently exposes additional repo-tree and repo-stats views that are not surfaced as dedicated CLI commands: `get_file_tree`, `get_repo_outline`, `get_index_status`, and `get_repo_stats`.

---

## MCP tools

SymDex currently exposes 20 MCP tools:

| Tool | Purpose |
|---|---|
| `index_folder` | Index a local folder and return indexing statistics |
| `index_repo` | Index a repo and register it in the central registry |
| `search_symbols` | Find functions, classes, and methods by name |
| `semantic_search` | Find symbols by meaning using embedding similarity |
| `search_text` | Search indexed files by text and return matching lines |
| `get_symbol` | Read one symbol by byte offsets |
| `get_symbols` | Bulk exact-name symbol lookup |
| `get_file_outline` | List symbols in a single file |
| `get_file_tree` | Return a directory tree without file contents |
| `get_repo_outline` | Return a repo tree plus summary stats |
| `get_callers` | Return symbols that call a named function |
| `get_callees` | Return symbols called by a named function |
| `search_routes` | Query extracted HTTP routes |
| `get_index_status` | Return symbol count, file count, Lines of Code, staleness, and watcher state |
| `get_repo_stats` | Return repo metrics such as language mix, fan-in, fan-out, and circular dependency count |
| `get_graph_diagram` | Generate a Mermaid call graph |
| `find_circular_deps` | Detect circular dependencies |
| `list_repos` | List all indexed repos |
| `invalidate_cache` | Force re-index on next use |
| `gc_stale_indexes` | Remove index databases for repos that no longer exist on disk |

---

## Supported languages

| Language | Extensions |
|---|---|
| Python | `.py` |
| JavaScript | `.js`, `.jsx`, `.mjs` |
| TypeScript | `.ts`, `.tsx` |
| Go | `.go` |
| Rust | `.rs` |
| Java | `.java` |
| Kotlin | `.kt`, `.kts` |
| Dart | `.dart` |
| Swift | `.swift` |
| PHP | `.php` |
| C# | `.cs` |
| C | `.c` |
| C++ | `.h`, `.cpp`, `.cc` |
| Elixir | `.ex`, `.exs` |
| Ruby | `.rb` |
| Vue | `.vue` script blocks parsed as JavaScript or TypeScript |
| Markdown | `.md`, `.markdown` headings plus supported fenced code blocks |

Powered by [tree-sitter](https://tree-sitter.github.io/tree-sitter/) for code, grammar fallbacks for mobile ecosystems, and a native Markdown scanner for headings and fenced code examples.

---

## Supported platforms

SymDex works with any MCP client that supports stdio or streamable HTTP.

| Platform | Typical setup |
|---|---|
| Codex CLI | Add to MCP settings |
| Gemini CLI | Add to MCP settings |
| Cursor | `.cursor/mcp.json` |
| Windsurf | Add to MCP settings |
| GitHub Copilot | `.vscode/mcp.json` |
| Roo | Add to MCP settings |
| Continue.dev | `config.json` |
| Cline | Add to MCP settings |
| Kilo Code | VS Code MCP settings |
| Zed | Add to MCP settings |
| OpenCode | `opencode.json` |
| Any MCP client | `uvx symdex serve` or `symdex serve --port 8080` |

---

## Voyage AI embeddings

Base `symdex` installs the lean core only. Choose the embedding extra that matches how you want semantic search to work:

- `symdex[local]` for local `sentence-transformers`
- `symdex[voyage]` for Voyage text embeddings
- `symdex[voyage-multimodal]` for Voyage text plus images and PDFs

Voyage AI is the hosted backend for users who want to offload embedding work to the cloud.

### Text mode

```bash
pip install "symdex[voyage]"

SYMDEX_EMBED_BACKEND=voyage \
VOYAGE_API_KEY=... \
SYMDEX_VOYAGE_MODEL=voyage-code-3 \
symdex index . --repo myrepo

SYMDEX_EMBED_BACKEND=voyage \
VOYAGE_API_KEY=... \
symdex semantic "parse source code" --repo myrepo
```

### Multimodal mode

```bash
pip install "symdex[voyage-multimodal]"

SYMDEX_EMBED_BACKEND=voyage
SYMDEX_VOYAGE_MULTIMODAL=1
VOYAGE_API_KEY=...
SYMDEX_VOYAGE_MULTIMODAL_MODEL=voyage-multimodal-3.5
symdex index . --repo myrepo
```

Multimodal mode lets SymDex index supported images, screenshots, and PDFs as searchable asset entries.

Notes:
- Base `symdex` keeps symbol, text, route, and call-graph features without pulling in the local embedding stack.
- Voyage is opt-in. If `SYMDEX_EMBED_BACKEND` is unset, SymDex keeps using the local backend when `symdex[local]` is installed.
- Local semantic search requires `symdex[local]` and downloads the model on first use.
- Voyage text mode requires `symdex[voyage]`.
- Voyage multimodal mode requires `symdex[voyage-multimodal]`.
- If the selected backend extra is missing, SymDex prints an actionable install hint.
- Multimodal indexing is only active when `SYMDEX_VOYAGE_MULTIMODAL=1`.

---

## FAQ

**Where are indexes stored?**
By default, each repo gets its own SQLite database under `~/.symdex`, plus a central registry database. If you set `SYMDEX_STATE_DIR=.symdex` or use `symdex --state-dir .symdex ...`, SymDex keeps repo databases, `registry.db`, `registry.json`, and watcher metadata inside the current workspace instead.

**What does indexing print?**
A code summary with files, Lines of Code, symbol counts, routes, skipped files, errors, and language breakdown.

**What do search commands print?**
CLI search commands print a one-line ROI footer showing approximate token savings. MCP search tools return structured `roi`, a concise `roi_summary`, and `roi_agent_hint` so clients can mention the savings when responding to users.

**Do existing users get update notices?**
Yes. Interactive CLI commands can print a brief upgrade notice with exact commands for `pip`, `uv tool`, and `uvx`. `--json` output stays quiet so structured consumers are not broken.

**Does semantic search require the internet?**
Not by default. Install `symdex[local]` for the local backend; it downloads its model once and then runs offline. Voyage mode requires `symdex[voyage]` or `symdex[voyage-multimodal]`, network access, and a `VOYAGE_API_KEY`.

**Why does `symdex semantic` say my repo has no semantic embeddings?**
That repo was indexed without an embedding backend, or kept fresh by the default low-memory watch mode. Install `symdex[local]` for local embeddings or enable Voyage, then run `symdex index` or `symdex watch --embed` so embeddings are written into the index.

**Will `symdex watch` keep a large embedding model in memory?**
No, not by default. Watch mode refreshes the structural index without loading the local semantic model unless `--embed` is passed. It also refuses duplicate watchers for the same repo/root, can auto-exit after an idle timeout, and stores watcher metadata in the active state directory so workspace-local mode stays isolated.

**Can I install SymDex without sentence-transformers?**
Yes. `pip install symdex` keeps the core symbol, text, route, and call-graph features without the local embedding dependencies. Install `symdex[local]` only when you want local semantic search.

**Can I use SymDex on multiple repos and worktrees?**
Yes. SymDex maintains a central registry, supports explicit `--repo` names, and can auto-generate stable repo ids from the current branch and worktree path when you omit `--repo`.

**Why do some agent logs show `index-folder` or `list-repos` while the CLI docs say `index` and `repos`?**
`index_folder` and `list_repos` are MCP tool names. The canonical shell commands are `symdex index` and `symdex repos`, and SymDex also accepts compatibility aliases such as `symdex index-folder` and `symdex list-repos`.

**What happens when I delete a worktree or repo?**
Run `symdex gc` or call `gc_stale_indexes` through MCP. SymDex removes stale registry entries and their database files.

**Can I exclude generated files?**
Yes. Use `.symdexignore` at the repo root with gitignore-style patterns. Common generated/build paths are also skipped by default.

**Can I use SymDex without an AI agent?**
Yes. All core search and navigation features are available through the CLI.

---

## Contributing

Issues and PRs are welcome at [github.com/husnainpk/SymDex](https://github.com/husnainpk/SymDex).

If SymDex saves you tokens, a star helps other people find it.
