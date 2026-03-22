<div align="center">

# SymDex

**Code intelligence MCP server for AI coding agents.**

*Index once. Find anything. Read only what you need.*

<br>

[![PyPI](https://img.shields.io/pypi/v/symdex?style=for-the-badge&color=3572A5&label=PyPI)](https://pypi.org/project/symdex/)
[![Downloads](https://img.shields.io/pypi/dm/symdex?style=for-the-badge&color=00ADD8&label=installs%2Fmonth)](https://pypi.org/project/symdex/)
[![Python](https://img.shields.io/pypi/pyversions/symdex?style=for-the-badge&color=f1e05a&labelColor=333)](https://pypi.org/project/symdex/)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](https://github.com/husnainpk/symdex/blob/main/LICENSE)
[![Stars](https://img.shields.io/github/stars/husnainpk/symdex?style=for-the-badge&color=f59e0b)](https://github.com/husnainpk/symdex/stargazers)

<br>

[![MCP client](https://img.shields.io/badge/MCP client-black?style=flat-square&logo=mcp)](https://mcpclient.ai)
[![Cursor](https://img.shields.io/badge/Cursor-black?style=flat-square)](https://cursor.sh)
[![Codex](https://img.shields.io/badge/Codex_CLI-black?style=flat-square&logo=openai)](https://github.com/openai/codex)
[![Gemini](https://img.shields.io/badge/Gemini_CLI-black?style=flat-square&logo=google)](https://github.com/google-gemini/gemini-cli)
[![Copilot](https://img.shields.io/badge/GitHub_Copilot-black?style=flat-square&logo=github)](https://github.com/features/copilot)
[![Windsurf](https://img.shields.io/badge/Windsurf-black?style=flat-square)](https://codeium.com/windsurf)
[![Roo](https://img.shields.io/badge/Roo-black?style=flat-square)](https://roocode.com)
[![Kilo](https://img.shields.io/badge/Kilo_Code-black?style=flat-square)](https://kilocode.ai)

<br>

<h2 align="center">7,500 tokens → 200 tokens</h2>
<p align="center"><strong>Per lookup. Every lookup. 97% reduction.</strong></p>
<p align="center">
  <img src="docs/images/symdex-hero-16x9.png" alt="SymDex hero visual showing token reduction and code intelligence workflow" width="100%" />
</p>

```bash
# Install with pip
pip install symdex

# Or run with uvx (no install step)
uvx symdex --help
```

</div>

---

## SymDex Skill For Agents

Install the SymDex code-search skill to make agents use SymDex first for code exploration:

```bash
npx skills add https://github.com/husnainpk/SymDex --skill symdex-code-search
```

What it does:
- Uses SymDex before Read/Grep/Glob for code discovery
- Checks index freshness first
- Searches by symbol, intent, routes, callers, and callees
- Reads only the exact symbol or file slice needed

The skill lives in this repo at `skills/symdex-code-search/SKILL.md` and follows the standard `skills/<name>/SKILL.md` layout used by the open skills ecosystem.

Installing through the `skills` CLI is also the path that feeds skills.sh discovery telemetry.

---

> **Current branch updates** — repo names now auto-derive from git branch plus a short path hash when `--repo` is omitted, `--repo` is the canonical flag everywhere, and successful searches print approximate token savings. [See full changelog →](#changelog)

---

## What makes SymDex different

Most code indexers find things by name. SymDex does three things no other tool does:

**1. Find code by what it does, not what it is called.**
```bash
symdex semantic "check that an email address is properly formatted" --repo myproject
# Finds validate_email, is_valid_address — without knowing either name existed
```

**2. Byte-precise symbol extraction — read only what you need.**
```json
{ "file": "auth/utils.py", "start_byte": 1024, "end_byte": 1340 }
```
The agent reads 316 bytes. Not 7,500. The index tells it exactly where to look.

**3. Zero infrastructure — one SQLite file per repo, no Docker, no server, no setup.**
```bash
uvx symdex index . && uvx symdex serve
```

---

## 60-second quickstart

```bash
# Install
pip install symdex
# OR
uvx symdex --help

# Index your project (run once; prints a summary with files, Lines of Code, symbols, and languages)
symdex index ./myproject --repo myproject
# OR
uvx symdex index ./myproject --repo myproject

# Search by name
symdex search "validate_email" --repo myproject
# OR
uvx symdex search "validate_email" --repo myproject

# After a successful search, SymDex prints an approximate token-savings footer
# "Without SymDex", "With SymDex", and a playful "You're in good hands."

# Search by meaning (no name required)
symdex semantic "check email format" --repo myproject
# OR
uvx symdex semantic "check email format" --repo myproject

# Start the MCP server — your agent can now use all 20 tools
symdex serve
# OR
uvx symdex serve
```

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

---

## The problem

AI agents often read entire files just to locate one function.

```text
Without indexing:
- read auth/utils.py        ~7,500 tokens
- read auth/validators.py   ~6,200 tokens
- read core/helpers.py      ~8,100 tokens
- find target on third try  ~21,800 tokens used
```

SymDex pre-indexes your codebase, so agents jump straight to exact symbols and byte ranges.

```text
With SymDex:
- search_symbols(...)       ~200 tokens
- get_symbol(...)           ~50 tokens
- total per lookup task     ~250 tokens
```

After each successful index, SymDex should also print a readable summary: files indexed, Lines of Code, symbol counts, skipped files, and language breakdown. That gives you an immediate picture of the codebase without opening a file.

---


## What you get

<p align="center">
  <img src="docs/images/what-you-get-grid.png" alt="SymDex feature grid showing core capabilities including semantic search, byte-precise extraction, call graph, routes, cross-repo registry, watch mode, and CLI plus MCP tools" width="100%" />
</p>

| Feature | Details |
|---|---|
| **Symbol search** | Any function, class, or method with exact byte offsets |
| **Semantic search** | Find code by intent, not exact name |
| **Text search** | Regex or literal across indexed files |
| **Call graph** | Callers, callees, circular dependency visibility |
| **HTTP routes** | Extract and query API routes without opening files |
| **File outline** | All symbols in one file without full file transfer |
| **Repo overview** | Structure and code summary |
| **Auto-watch** | Reindex on change; remove deleted files from index |
| **Cross-repo registry** | Search and manage multiple projects from one tool |
| **Stale index GC** | Clean orphaned index DBs after branch/worktree cleanup |
| **CLI + MCP tools** | Full terminal and MCP workflows |
| **Language support** | Python, JS, TS, Go, Rust, Java, PHP, C#, C/C++, Elixir, Ruby, Vue |

---


## For AI Agents

<details>
<summary><strong>Agent playbook (expand)</strong></summary>

- Index before querying: `index_folder`
- Never read full files to find symbols; use `search_symbols`/`semantic_search` first
- Retrieve source with byte ranges via `get_symbol`
- Re-index after edits with `index_folder` or `invalidate_cache`

</details>

## SymDex vs. everything else

<p align="center">
  <img src="docs/images/comparison-matrix.png" alt="SymDex versus alternatives comparison matrix across semantic search, byte-precise extraction, route indexing, zero infrastructure, cross-repo support, and CLI plus MCP coverage" width="100%" />
</p>

| Capability | LSP | Serena | CodeGraphContext | SocratiCode | **SymDex** |
|---|---|---|---|---|---|
| Find symbol by name | Yes | Yes | Yes | Yes | **Yes** |
| Search by meaning / intent | No | No | No | Yes | **Yes** |
| Byte-precise symbol extraction | No | No | No | No | **Yes** |
| HTTP route indexing | No | No | No | No | **Yes** |
| Auto-watch, live reindex | No | No | No | Yes | **Yes** |
| Call graph | Partial | Yes | Yes | File-level | **Symbol-level** |
| Cross-repo / multi-project | No | No | No | No | **Yes** |
| Works without an editor | No | No | No | Yes | **Yes** |
| Full CLI (non-agent access) | No | No | No | No | **Yes** |
| Zero infrastructure | Partial | Yes | No (graph DB) | No (Docker) | **Yes — one SQLite file** |
| one command and done | No | No | No | No (npm + Docker) | **Yes** |
| License | varies | MIT | MIT | AGPL-3.0 | **MIT** |
| Works offline | Yes | Yes | Yes | Yes | **Yes** |

<details>
<summary><strong>Compact vertical comparison (optional view)</strong></summary>

<p align="center">
  <img src="docs/images/comparison-matrix-vertical.png" alt="Vertical compact SymDex comparison matrix for narrow screen viewing" width="420" />
</p>

</details>

### vs. LSP (pylsp, tsserver, rust-analyzer)

LSP is excellent in an editor. It requires a running editor, a language server installed per language, and operates on live files. SymDex is terminal-native, editor-free, and works identically inside MCP client Code, Codex CLI, or any headless agent. LSP cannot do semantic search — if you don't know the function name, LSP cannot help you.

### vs. Serena

Serena wraps real language servers for true type-aware analysis — generics, interfaces, pointer dispatch. Genuinely powerful for large, strongly-typed codebases. The tradeoff: language servers installed per language, queries hit live files rather than a pre-built index. SymDex is faster per query (pre-indexed), adds semantic search and HTTP route indexing, and requires zero per-language setup.

### vs. CodeGraphContext

CodeGraphContext builds a graph database over your code. The tradeoff: you need to choose and run a graph database backend (KùzuDB, Neo4j). SymDex uses SQLite — one file per repo, zero configuration. No backend, no server, no Docker. CodeGraphContext has no semantic search and no HTTP route indexing.

### vs. SocratiCode

SocratiCode does hybrid search and Mermaid graph visualization. Worth knowing about. The tradeoffs: requires Docker (Qdrant + Ollama containers), npm install, AGPL-3.0 license, no byte-precise symbol table (chunk-based), no cross-repo registry, no CLI. SymDex is MIT, zero-Docker, has exact byte offsets, supports multiple repos simultaneously, and ships a full developer CLI.

---

## Features in depth

<p align="center">
  <img src="docs/images/symdex-features-collage.png" alt="SymDex feature collage: symbol search, semantic search, call graph, routes, multi-repo, and watch mode" width="100%" />
</p>

- **Semantic search**: find code by intent, not exact name.
- **Byte-precise symbol extraction**: return only the exact symbol range agents need.
- **Call graph + circular deps**: impact analysis and architecture debugging.
- **HTTP route indexing**: query API surfaces without opening route files.
- **Cross-repo registry**: one SymDex instance, many codebases.
- **Auto-watch + incremental indexing**: keep index fresh with minimal reprocessing.

## MCP Tool Reference

| Tool | Description |
|------|-------------|
| `index_folder` | Index a local folder |
| `index_repo` | Index a registered repo |
| `search_symbols` | Find function or class by name — returns byte offsets |
| `get_symbol` | Retrieve one symbol's source by byte offset |
| `get_symbols` | Bulk symbol retrieval |
| `get_file_outline` | All symbols in a file — no file content transferred |
| `get_repo_outline` | Directory structure and code summary |
| `get_file_tree` | Directory tree — structure only |
| `search_text` | Text or regex search — matching lines only |
| `list_repos` | List all indexed repos |
| `invalidate_cache` | Force re-index on next request |
| `semantic_search` | Find symbols by meaning — embedding similarity |
| `get_callers` | All functions that call a named function |
| `get_callees` | All functions a named function calls |
| `search_routes` | HTTP routes from a repo (Flask/FastAPI/Django/Express) |
| `gc_stale_indexes` | Remove databases for repos no longer on disk |
| `get_index_status` | Index freshness, file count, Lines of Code, watcher state |
| `get_repo_stats` | Code metrics: Lines of Code, fan-in, fan-out, orphans, language distribution |
| `get_graph_diagram` | Mermaid call graph — renders in MCP client, GitHub, Cursor |
| `find_circular_deps` | Detect circular import/call chains |

---

## CLI Reference

```bash
# Indexing
symdex index ./myproject                            # Index a folder (auto-names from git branch + path hash)
symdex index ./myproject --repo myproj             # Index with explicit name
symdex invalidate --repo myproj                    # Force re-index a repo
symdex invalidate --repo myproj --file auth.py     # Force re-index one file
symdex gc                                           # Remove stale indexes

# Symbol search
symdex search "validate email" --repo myproj       # Search by name across a repo
symdex search "validate email"                     # Search across all repos
symdex find MyClass --repo myproj                  # Exact name lookup

# Semantic search
symdex semantic "authentication token parsing" --repo myproj

# File and repo inspection
symdex outline myproj/auth/utils.py --repo myproj  # All symbols in a file
symdex tree myproj                                  # Directory tree
symdex repos                                        # List indexed repos

# Call graph
symdex callers validate_email --repo myproj
symdex callees validate_email --repo myproj

# HTTP routes
symdex routes myproj                               # All routes
symdex routes myproj -m POST                       # POST only
symdex routes myproj -p /api                       # Path filter

# Server
symdex serve                                       # stdio (for agents)
symdex serve --port 8080                           # HTTP

# Monitoring
symdex watch ./myproject                           # Auto-reindex on file changes
# Omit --repo to auto-name from git branch + path hash; use --repo to override
```

---

## Supported Languages

| Language | Extensions |
|----------|------------|
| Python | `.py` |
| JavaScript | `.js` `.mjs` |
| TypeScript | `.ts` `.tsx` |
| Go | `.go` |
| Rust | `.rs` |
| Java | `.java` |
| PHP | `.php` |
| C# | `.cs` |
| C | `.c` `.h` |
| C++ | `.cpp` `.cc` `.h` |
| Elixir | `.ex` `.exs` |
| Ruby | `.rb` |
| Vue | `.vue` (script block extracted, parsed as JS/TS) |

Powered by [tree-sitter](https://tree-sitter.github.io/tree-sitter/) — the same parser used by Neovim, Helix, and GitHub. Additional grammars can be added via pip.

---

## Supported Platforms

**Quick view:** `MCP desktop client` · `MCP client Code` · `Codex CLI` · `Gemini CLI` · `Cursor` · `Windsurf` · `GitHub Copilot` · `Roo` · `Continue.dev` · `Cline` · `Kilo Code` · `Zed` · `OpenCode` · `Any MCP client`

| Platform | How to connect |
|----------|---------------|
| MCP desktop client | Add to `mcp_client_config.json` |
| MCP client Code | `mcp-client add symdex -- uvx symdex serve` |
| Codex CLI | Add to MCP settings |
| Gemini CLI | Add to MCP settings |
| Cursor | `.cursor/mcp.json` |
| Windsurf | Add to MCP settings |
| GitHub Copilot (agent mode) | `.vscode/mcp.json` |
| Roo | Add to MCP settings |
| Continue.dev | `config.json` |
| Cline | Add to MCP settings |
| Kilo Code | `kilocode.mcpServers` in VS Code settings |
| Zed | Add to MCP settings |
| OpenCode | `opencode.json` |
| Any MCP client | stdio or HTTP transport |

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

HTTP mode (remote agents):
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

## Installation

```bash
# Method 1: pip
pip install symdex
symdex --help

# Method 2: uv tool install (isolated managed tool env)
uv tool install symdex
symdex --help

# Method 3: uvx (ephemeral isolated run; no install step)
uvx symdex --help
```

Requires Python 3.11+. No Docker. No external database. No API keys.

---

## Architecture

<p align="center">
  <img src="docs/images/symdex-architecture.png" alt="SymDex architecture diagram from MCP tools to SQLite index, embeddings, and tree-sitter parser" width="100%" />
</p>

```
User / AI Agent
      │
      │  MCP (stdio or HTTP)
      ▼
┌─────────────────────────────────────────┐
│           MCP Server (FastMCP)           │
│  20 tools: symbol · semantic · graph     │
│            routes · registry · stats     │
└──────────────┬──────────────────────────┘
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
  symbol_   text_    semantic_
  search    search   search
      │                 │
      ▼                 ▼
┌──────────┐     ┌──────────────┐
│  SQLite  │     │ sentence-    │
│ symbols  │     │ transformers │
│ edges    │     │ (local)      │
│ files    │     └──────────────┘
│ routes   │
│ repos    │
└────┬─────┘
     │
     ▼
┌──────────────┐
│  tree-sitter │  14 languages
│  parser      │
└──────────────┘
```

- **Storage:** SQLite + sqlite-vec. One `.db` file per repo. No external database.
- **Parser:** tree-sitter. Fast, incremental, accurate — same parser as major editors.
- **Embeddings:** sentence-transformers by default, with optional Voyage AI support for users who want a hosted backend.
- **Transport:** stdio (default) or HTTP. Same MCP interface either way.
- **Change detection:** SHA-256 per file. Re-indexing only processes changed files.

---

## Voyage AI embeddings

SymDex defaults to local `sentence-transformers`. Voyage AI is an optional hosted backend for people who want to offload embedding work to the cloud.

### When to use it

- Use Voyage text embeddings if you want a hosted alternative to local embeddings.
- Use Voyage multimodal mode if you also want images, screenshots, and PDFs to be searchable.
- Keep the default local backend if you want fully offline indexing and search.

### Text mode

```bash
SYMDEX_EMBED_BACKEND=voyage VOYAGE_API_KEY=... symdex index . --repo myrepo
SYMDEX_EMBED_BACKEND=voyage VOYAGE_API_KEY=... symdex semantic "parse source code" --repo myrepo
```

Recommended model:
- `SYMDEX_VOYAGE_MODEL=voyage-code-3`

### Multimodal mode

```bash
SYMDEX_EMBED_BACKEND=voyage
SYMDEX_VOYAGE_MULTIMODAL=1
VOYAGE_API_KEY=...
symdex index . --repo myrepo
```

Recommended multimodal model:
- `SYMDEX_VOYAGE_MULTIMODAL_MODEL=voyage-multimodal-3.5`

Requirements:
- `voyageai`
- `pillow`
- `pymupdf`

Notes:
- Voyage is opt-in. If you do not set `SYMDEX_EMBED_BACKEND=voyage`, SymDex keeps using local embeddings.
- Asset files are indexed as searchable asset entries when multimodal mode is on.
- PDFs are converted to a rendered page image before embedding.

## FAQ

<p align="center">
  <img src="docs/images/symdex-before-after.png" alt="Before and after comparison showing token-heavy code lookup versus SymDex efficient lookup" width="100%" />
</p>

**Does semantic search require an internet connection?**
Not by default. Local embeddings download once on first use and run fully offline after that. If you opt into Voyage AI, SymDex sends embedding requests to the Voyage API, so that mode needs network access and an API key.

**Can I use Voyage AI embeddings?**
Yes. Set `SYMDEX_EMBED_BACKEND=voyage` and provide `VOYAGE_API_KEY`. For code/text search, the recommended model is `SYMDEX_VOYAGE_MODEL=voyage-code-3`.

**Can Voyage index images, PDFs, and screenshots?**
Yes, if you also enable `SYMDEX_VOYAGE_MULTIMODAL=1`. SymDex will index supported asset files as searchable asset entries. For that mode, install `voyageai`, `pillow`, and `pymupdf`, then use `SYMDEX_VOYAGE_MULTIMODAL_MODEL=voyage-multimodal-3.5`.

**I see HuggingFace warnings in Roo / KiloCode on first use. Is that normal?**
Not anymore. v0.1.7 suppresses all HuggingFace Hub noise at startup (progress bars, token warnings, login advisories). If you are on an older version, upgrade (`uv tool upgrade symdex` or `pip install --upgrade symdex`).

**How long does indexing take?**
A typical 50-file Python project indexes in 2–5 seconds. Incremental re-indexing after a file change takes under a second for that file alone.

**Does SymDex work on Windows?**
Yes. SQLite and tree-sitter both work on Windows. The MCP server runs on stdio, which works on all platforms.

**Can I use SymDex on multiple projects simultaneously?**
Yes. Each project gets its own `.db` file in the registry. The `list_repos` tool and `symdex repos` command show all indexed projects. Search can be scoped to one repo or run across all.

**What happens to the index when I delete a branch or worktree?**
Run `symdex gc`. It finds all repos in the registry whose root path no longer exists and removes their database files and registry entries. Also available as `gc_stale_indexes` MCP tool.

**Can I exclude generated files or build output from indexing?**
Yes. Create a `.symdexignore` file at your project root with one glob pattern per line — same format as `.gitignore`. Common patterns (`node_modules/`, `__pycache__/`, `dist/`, `build/`, `*.min.js`) are excluded by default even without a `.symdexignore` file.

**Can I visualize the call graph?**
Yes. `get_graph_diagram` returns a Mermaid diagram that renders in MCP client, GitHub, Cursor, and any Markdown viewer. Use `focus_file` to zoom into a specific module and `depth` to control how many hops to traverse.

**How does circular dependency detection work?**
`find_circular_deps` runs a DFS over the call graph built during indexing. It returns up to 20 distinct cycles, each shown as a path from the first file back to itself.

**Is there a size limit?**
No hard limit. SymDex has been tested on codebases with 500+ files. For very large monorepos, index sub-directories by area (e.g. `symdex index ./src/auth --repo auth`) to keep individual databases small and fast.

**Do I need to keep SymDex running?**
No. The MCP server starts on demand when your agent calls it. For auto-watch, `symdex watch` runs as a background process you start once.

**Can I use the CLI without an AI agent?**
Yes — every capability is available via CLI. SymDex is useful as a developer tool independent of any AI agent: `symdex find`, `symdex semantic`, `symdex callers`, `symdex routes` all work from the terminal.

## Voyage AI backend

SymDex defaults to local `sentence-transformers`. If you want a hosted backend, Voyage AI is optional and explicit.

### Text embeddings

```bash
SYMDEX_EMBED_BACKEND=voyage VOYAGE_API_KEY=... symdex index . --repo myrepo
SYMDEX_EMBED_BACKEND=voyage VOYAGE_API_KEY=... symdex semantic "parse source code" --repo myrepo
```

Recommended text model:
- `SYMDEX_VOYAGE_MODEL=voyage-code-3`

### Multimodal assets

If you also want images, screenshots, and PDFs to be searchable, enable multimodal mode:

```bash
SYMDEX_EMBED_BACKEND=voyage
SYMDEX_VOYAGE_MULTIMODAL=1
VOYAGE_API_KEY=...
symdex index . --repo myrepo
```

Recommended multimodal model:
- `SYMDEX_VOYAGE_MULTIMODAL_MODEL=voyage-multimodal-3.5`

Requirements for multimodal mode:
- `voyageai`
- `pillow`
- `pymupdf`

Notes:
- Voyage is optional. If you do not set `SYMDEX_EMBED_BACKEND=voyage`, SymDex keeps using local embeddings.
- Asset files are indexed as searchable asset entries when multimodal mode is on.
- PDFs are converted to a rendered page image before embedding.
- If you only want code/text search, you do not need to enable multimodal mode.

---

## Changelog

### v0.1.9 — current branch
- **Repo auto-naming** — `symdex index .` and `symdex watch .` now derive a unique repo id from git branch + path hash when `--repo` is omitted.
- **Canonical repo flag** — `--repo` is the preferred name override on CLI and MCP; `--name` remains as a compatibility alias.
- **Search ROI footer** — successful search commands print approximate token savings using the default tokenizer profile.

### v0.1.8
- **SQLite compatibility fix** — SymDex no longer crashes on Python builds where `sqlite3.Connection.enable_load_extension` is unavailable. Extension loading is now best-effort and safely skipped when unsupported.
- **Regression test added** — `test_get_connection_works_without_enable_load_extension` protects this compatibility path.
- **CI guard added** — new workflow runs the sqlite-extension regression test on PRs and pushes to prevent reintroducing the crash.
- **Install docs parity** — README now presents `pip`, `uv tool install`, and `uvx` as equal first-class installation methods.

### v0.1.7
- **`get_graph_diagram`** — generates a Mermaid call graph from the index. Renders in MCP client, GitHub, Cursor, any Markdown viewer. Language-coloured nodes, cycle edges highlighted in red, `focus_file` + `depth` for subgraph zoom.
- **`find_circular_deps`** — DFS over the call graph. Returns up to 20 distinct circular import/call chains.
- **`get_repo_stats`** — code summary: Lines of Code, fan-in, fan-out, orphan files, language distribution, edge count, circular dep count.
- **`get_index_status`** — index freshness check: symbol count, file count, Lines of Code, last indexed time, staleness flag, watcher state.
- **Search ROI footer** — successful search commands print approximate token savings using the default tokenizer profile.
- **`.symdexignore`** — per-project ignore file (gitignore format). Built-in defaults always applied: `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`, `*.min.js`, and more.
- **HF Hub noise fix** — no more HuggingFace progress bars or warnings in Roo, KiloCode, or any MCP client on first `semantic_search` call.
- **Asymmetric embedding prefixes** — `search_document:` at index time, `search_query:` at query time. Improves semantic recall with MiniLM and nomic-embed-text models.
- **tree-sitter compatibility fix** — newer tree-sitter versions and TypeScript grammar loading now work correctly (community contribution).

### v0.1.5
- **Git worktree support** — `symdex index .` inside any git repo auto-names from the current branch plus a short path hash. No `--repo` flag needed.
- **`symdex gc`** — scans the registry, removes `.db` files for repos whose root directories no longer exist on disk. One command cleans up after deleted branches and worktrees.
- **`gc_stale_indexes` MCP tool** — same cleanup available to agents mid-session.
- **Bug fix** — `schema.sql` was missing from the PyPI wheel. Incremental re-index now works correctly after install.

### v0.1.3
- **`symdex watch`** — auto-reindex on file save and delete using native OS watchers. No polling.
- **HTTP route indexing** — Flask, FastAPI, Django, Express routes extracted during indexing. `search_routes` MCP tool + `symdex routes` CLI.

### v0.1.2
- **Vue SFC support** — `.vue` files parsed by extracting the `<script>` block. `lang="ts"` detected automatically. Byte offsets adjusted to the full file.

### v0.1.1
- **Case normalization fix** — repo names lowercased at index time. Fixes split-index bugs when the same project is indexed from different shells.

### v0.1.0
- Initial release: 14 MCP tools, 13 languages, semantic search, call graph, cross-repo registry, full CLI, MIT license.

---

## Contributing

Issues and PRs welcome at [github.com/husnainpk/SymDex](https://github.com/husnainpk/SymDex).

If SymDex saves you tokens, a star helps others find it.
