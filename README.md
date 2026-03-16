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

```
7,500 tokens → 200 tokens. Per lookup. Every lookup. 97% reduction.
```

```bash
# Install with pip
pip install symdex

# Or run with uvx (no install step)
uvx symdex --help
```

</div>

---

> **What's new in v0.1.7** — Graph visualization (`get_graph_diagram` → instant Mermaid in MCP client/GitHub/Cursor), circular dep detection, repo architecture stats, index status check, `.symdexignore` support, HF Hub noise fixed for Roo/KiloCode users, improved semantic recall. [See full changelog →](#changelog)

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
# OR: uvx symdex --help

# Index your project (run once; only changed files re-process on subsequent runs)
symdex index ./myproject --name myproject
# OR: uvx symdex index ./myproject --name myproject

# Search by name
symdex search "validate_email" --repo myproject
# OR: uvx symdex search "validate_email" --repo myproject

# Search by meaning (no name required)
symdex semantic "check email format" --repo myproject
# OR: uvx symdex semantic "check email format" --repo myproject

# Start the MCP server — your agent can now use all 20 tools
symdex serve
# OR: uvx symdex serve
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

Every time an AI agent needs to find a function, it reads the entire file that might contain it:

```
Agent: "I need to find validate_email."
→ reads auth/utils.py        7,500 tokens
→ reads auth/validators.py   6,200 tokens
→ reads core/helpers.py      8,100 tokens
→ finds it on the third try  21,800 tokens wasted
```

On a real codebase, a single session can burn hundreds of thousands of tokens this way. SymDex pre-indexes the codebase so agents never read a full file to find a symbol again.

```
With SymDex:
→ search_symbols("validate_email")   ~200 tokens → exact file + byte offset
→ get_symbol(file, start, end)       ~50 tokens  → only that function's source
Total: ~250 tokens. Session after session.
```

---

## What you get

| | Feature | Details |
|---|---|---|
| 🔍 | **Symbol search** | Any function, class, or method — returns exact byte offsets |
| 🧠 | **Semantic search** | Search by what code *does*, not what it is *called* |
| 🔎 | **Text search** | Regex or literal across all indexed files — matching lines only |
| 🕸️ | **Call graph** | Who calls this? What does it call? Pre-built at index time |
| 🌐 | **HTTP routes** | Every API route extracted and searchable — no file reading needed |
| 📄 | **File outline** | All symbols in a file without transferring file content |
| 🗺️ | **Repo overview** | Directory structure + symbol statistics |
| 👁️ | **Auto-watch** | Save a file — index updates. Delete a file — index removes it. |
| 🗄️ | **Cross-repo registry** | One SymDex, many projects. Search all repos simultaneously. |
| 🧹 | **Stale index GC** | `symdex gc` — removes orphaned databases from deleted worktrees |
| ⌨️ | **Full CLI** | Every capability in the terminal, no agent required |
| 🔌 | **20 MCP tools** | Every capability available to any MCP-compatible agent |
| 🌍 | **14 languages** | Python · JS · TS · Go · Rust · Java · PHP · C# · C · C++ · Elixir · Ruby · Vue · more |

---

## Token savings in practice

```
Finding and reading 3 related functions in a 10,000-line codebase:

Without SymDex:
  read auth/utils.py          7,500 tokens
  read auth/validators.py     6,200 tokens
  read core/helpers.py        8,100 tokens
  ─────────────────────────────────────────
  Total                      21,800 tokens

With SymDex:
  semantic_search(query)        200 tokens
  get_symbol × 3               150 tokens
  ─────────────────────────────────────────
  Total                         350 tokens

Savings: 21,450 tokens — 98% reduction — on one micro-task.
```

The savings compound. Every symbol lookup, every session, every agent.

---

## For AI Agents

> **If you are an AI agent reading this:** Follow these rules to use SymDex correctly.

**Rule 1 — Index before anything else.**
```json
{ "tool": "index_folder", "path": "/path/to/project", "name": "myproject" }
```

**Rule 2 — Never read a full file to find a function.** Call `search_symbols` or `semantic_search` first. Use the returned byte offsets with `get_symbol`.

**Rule 3 — Use the right tool.**

| What you want | Tool |
|---|---|
| Find a function by name | `search_symbols` |
| Read a function's source | `get_symbol` (byte offsets from search) |
| Find by meaning / description | `semantic_search` |
| All symbols in a file | `get_file_outline` |
| Project structure | `get_repo_outline` |
| Who calls a function | `get_callers` |
| What a function calls | `get_callees` |
| String or regex in code | `search_text` |
| API routes in the repo | `search_routes` |
| Check index freshness | `get_index_status` |
| Architecture metrics (fan-in, orphans…) | `get_repo_stats` |
| Visualize call graph as Mermaid | `get_graph_diagram` |
| Detect circular imports/calls | `find_circular_deps` |
| Remove orphaned indexes | `gc_stale_indexes` |

**Rule 4 — Re-index after code changes.** Call `index_folder` again (or `invalidate_cache`) after modifying source files.

---

## Real-world agent session

```json
// Step 1: Find the function
{ "tool": "search_symbols", "query": "validate_email", "repo": "myproject" }
// → { "file": "auth/utils.py", "start_byte": 1024, "end_byte": 1340 }   ~200 tokens

// Step 2: Read only that function
{ "tool": "get_symbol", "file": "auth/utils.py", "start_byte": 1024, "end_byte": 1340 }
// → { "source": "def validate_email(email: str) -> bool: ..." }           ~50 tokens

// Step 3: Check impact before changing it
{ "tool": "get_callers", "name": "validate_email", "repo": "myproject" }
// → { "callers": [{"name": "register_user", "file": "auth/views.py"}, ...] }  ~100 tokens

// Step 4: When you don't know the name
{ "tool": "semantic_search", "query": "check if user email is valid", "repo": "myproject" }
// → finds validate_email with score 0.91                                   ~150 tokens

// Total for the entire session: ~500 tokens
// Without SymDex: ~25,000 tokens
```

---

## SymDex vs. everything else

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

### Semantic Search

Every symbol's signature and docstring is embedded into a vector at index time. Search by what code does — not what it is called. Fully local, powered by `sentence-transformers`. No API calls. Nothing leaves your machine.

```bash
symdex semantic "parse and validate an authentication token" --repo myproject
```

```
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                 ┃ Kind     ┃ Score  ┃ File                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ verify_jwt           │ function │ 0.93   │ auth/tokens.py         │
│ decode_bearer_token  │ function │ 0.87   │ middleware/auth.py      │
└──────────────────────┴──────────┴────────┴────────────────────────┘
```

### Call Graph

Who calls this function? What does it call? Extracted during indexing, answered instantly at query time — no file reading.

```bash
symdex callers process_payment --repo myproject   # impact analysis before changing
symdex callees process_payment --repo myproject   # dependency trace
```

Via MCP:
```json
{ "tool": "get_callers", "name": "process_payment", "repo": "myproject" }
```

### HTTP Route Indexing

API routes extracted from source during indexing. No more reading route files to understand an API surface.

```bash
symdex routes myproject               # all routes
symdex routes myproject -m POST       # POST routes only
symdex routes myproject -p /users     # routes matching path
```

Supports Flask · FastAPI · Django · Express.

### Auto-Watch

```bash
symdex watch ./myproject
```

Save a file — SymDex reindexes it automatically. Delete a file — removed from the index. The agent always sees current code with no manual steps.

### Cross-Repo Registry

```bash
symdex index ./frontend --name frontend
symdex index ./backend  --name backend
symdex search "validate_token"   # searches both simultaneously
```

Each repo gets its own SQLite database. The registry tracks all of them. Search scoped or global.

### Graph Diagram (Mermaid)

SymDex stores a call graph at index time. `get_graph_diagram` turns it into a Mermaid diagram that renders instantly inside MCP client, GitHub, Cursor, and any Markdown viewer — no external tool needed.

```json
{ "tool": "get_graph_diagram", "repo": "myproject" }
```

```
graph LR
  n0["cli.py"] --> n1["core/indexer.py"]
  n1 --> n2["core/storage.py"]
  n2 -->|cycle| n1
  style n0 fill:#3572A5
  style n1 fill:#3572A5
  style n2 fill:#3572A5
```

Cycle edges are highlighted in red automatically. Focus on a single file with `focus_file` and control graph depth with `depth`.

### Circular Dependency Detection

```json
{ "tool": "find_circular_deps", "repo": "myproject" }
```

```json
{
  "cycles": [
    ["auth/login.py", "auth/middleware.py", "auth/login.py"],
    ["core/db.py", "core/models.py", "core/db.py"]
  ],
  "count": 2
}
```

DFS over the call graph. Returns up to 20 distinct cycles, deduplicated and normalized.

### Repo Stats

Architecture overview without reading a single file:

```json
{ "tool": "get_repo_stats", "repo": "myproject" }
```

```json
{
  "symbol_count": 1420,
  "file_count": 87,
  "language_distribution": { "python": 60, "javascript": 20, "typescript": 7 },
  "top_fan_in": [{ "name": "utils/helpers.py", "dependents": 34 }],
  "top_fan_out": [{ "name": "cli.py", "calls": 45 }],
  "orphan_files": ["scripts/old_migration.py"],
  "circular_dep_count": 2,
  "edge_count": 892
}
```

### Index Status

Before querying a large repo, agents can confirm the index is fresh:

```json
{ "tool": "get_index_status", "repo": "myproject" }
```

```json
{
  "symbol_count": 1420,
  "file_count": 87,
  "last_indexed": "2026-03-15T14:32:00Z",
  "age_seconds": 3600,
  "stale": false,
  "watcher_active": true
}
```

`stale` is `true` if any tracked file has been modified since the last index run.

### `.symdexignore`

Place a `.symdexignore` file at your project root to exclude paths from indexing — same format as `.gitignore`:

```
# .symdexignore
generated/
*.pb.go
vendor/
```

Built-in defaults are always applied even without a `.symdexignore` file: `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`, `*.min.js`, `*.pyc`, and more.

### Stale Index GC

Working with git worktrees or parallel agents? Deleted branches leave orphaned `.db` files.

```bash
symdex gc
# Removed 3 stale indexes: task-auth, feature-payments, task-tests
```

Also available as MCP tool `gc_stale_indexes` for automated cleanup from within an agent session.

### Auto-Name from Git Branch

Inside a git worktree, `--name` is optional — SymDex reads the current branch name automatically:

```bash
git checkout -b feature/auth
symdex index .
# Indexed as: feature-auth
```

---

## MCP Tool Reference

| Tool | Description |
|------|-------------|
| `index_folder` | Index a local folder |
| `index_repo` | Index a named registered repo |
| `search_symbols` | Find function or class by name — returns byte offsets |
| `get_symbol` | Retrieve one symbol's source by byte offset |
| `get_symbols` | Bulk symbol retrieval |
| `get_file_outline` | All symbols in a file — no file content transferred |
| `get_repo_outline` | Directory structure and symbol statistics |
| `get_file_tree` | Directory tree — structure only |
| `search_text` | Text or regex search — matching lines only |
| `list_repos` | List all indexed repos |
| `invalidate_cache` | Force re-index on next request |
| `semantic_search` | Find symbols by meaning — embedding similarity |
| `get_callers` | All functions that call a named function |
| `get_callees` | All functions a named function calls |
| `search_routes` | HTTP routes from a repo (Flask/FastAPI/Django/Express) |
| `gc_stale_indexes` | Remove databases for repos no longer on disk |
| `get_index_status` | Index freshness, file count, watcher state |
| `get_repo_stats` | Architecture metrics: fan-in, fan-out, orphans, language distribution |
| `get_graph_diagram` | Mermaid call graph — renders in MCP client, GitHub, Cursor |
| `find_circular_deps` | Detect circular import/call chains |

---

## CLI Reference

```bash
# Indexing
symdex index ./myproject                            # Index a folder (auto-names from git branch)
symdex index ./myproject --name myproj             # Index with explicit name
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
- **Embeddings:** sentence-transformers running locally. No API calls.
- **Transport:** stdio (default) or HTTP. Same MCP interface either way.
- **Change detection:** SHA-256 per file. Re-indexing only processes changed files.

---

## FAQ

**Does semantic search require an internet connection?**
No. The embedding model downloads once on first use and runs fully offline after that. No API keys, no data leaves your machine.

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
No hard limit. SymDex has been tested on codebases with 500+ files. For very large monorepos, index sub-directories by area (e.g. `symdex index ./src/auth --name auth`) to keep individual databases small and fast.

**Do I need to keep SymDex running?**
No. The MCP server starts on demand when your agent calls it. For auto-watch, `symdex watch` runs as a background process you start once.

**Can I use the CLI without an AI agent?**
Yes — every capability is available via CLI. SymDex is useful as a developer tool independent of any AI agent: `symdex find`, `symdex semantic`, `symdex callers`, `symdex routes` all work from the terminal.

---

## Changelog

### v0.1.7 — current
- **`get_graph_diagram`** — generates a Mermaid call graph from the index. Renders in MCP client, GitHub, Cursor, any Markdown viewer. Language-coloured nodes, cycle edges highlighted in red, `focus_file` + `depth` for subgraph zoom.
- **`find_circular_deps`** — DFS over the call graph. Returns up to 20 distinct circular import/call chains.
- **`get_repo_stats`** — architecture overview: fan-in, fan-out, orphan files, language distribution, edge count, circular dep count.
- **`get_index_status`** — index freshness check: symbol count, file count, last indexed time, staleness flag, watcher state.
- **`.symdexignore`** — per-project ignore file (gitignore format). Built-in defaults always applied: `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `build/`, `*.min.js`, and more.
- **HF Hub noise fix** — no more HuggingFace progress bars or warnings in Roo, KiloCode, or any MCP client on first `semantic_search` call.
- **Asymmetric embedding prefixes** — `search_document:` at index time, `search_query:` at query time. Improves semantic recall with MiniLM and nomic-embed-text models.
- **tree-sitter compatibility fix** — newer tree-sitter versions and TypeScript grammar loading now work correctly (community contribution).

### v0.1.5
- **Git worktree support** — `symdex index .` inside any git repo auto-names from the current branch (`feature/auth` → `feature-auth`). No `--name` flag needed.
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
