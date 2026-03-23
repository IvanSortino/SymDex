# Workspace-Local State Design

## Goal

Add an optional workspace-local SymDex state mode for Docker and portable repo workflows without breaking the existing global `~/.symdex` default.

## Problem

Today SymDex stores:

- repo databases under `~/.symdex/<repo>.db`
- the registry under `~/.symdex/registry.db`

That works well for a single-user machine, but it is weaker for containerized and portable workflows because:

- indexing state is detached from the project directory
- fresh containers re-index unless the home directory is mounted
- users cannot inspect indexed repos quickly without either running `symdex repos` or opening SQLite directly

## Non-Goals

- Replacing SQLite with JSON
- Removing the existing global registry mode
- Forcing local state on existing users
- Adding a new persistent daemon or background service

## Recommended Design

### 1. Keep the current global mode

If the user does nothing, SymDex continues to use:

- `~/.symdex/<repo>.db`
- `~/.symdex/registry.db`

This preserves backward compatibility.

### 2. Add an optional workspace-local state mode

When the user opts in with `--state-dir .symdex` or `SYMDEX_STATE_DIR=.symdex`, SymDex should store state under the working directory:

- `./.symdex/<repo>.db`
- `./.symdex/registry.db`
- `./.symdex/registry.json`

After that state exists, commands run from that workspace should auto-discover and reuse it.

### 3. Add a mirrored `registry.json`

`registry.json` is a human-readable manifest, not a replacement for SQLite.

It should contain:

- `name`
- `root_path`
- `db_path`
- `last_indexed`

In workspace-local mode:

- `root_path` should be relative to the parent of `.symdex`
- `db_path` should be relative to the parent of `.symdex`

In global mode:

- keep absolute paths

### 4. Timestamp format

Use:

- `YYYY-MM-DD HH:mm:ss`

This matches the request and keeps sorting straightforward.

### 5. Path resolution rules

Internally:

- registry rows may be stored relative in workspace-local mode
- SymDex should resolve them back to absolute paths before using them for search, invalidation, staleness checks, and file reads

Externally:

- `registry.json` should preserve the user-facing relative paths in workspace-local mode

### 6. Discovery rules

State resolution should work in this order:

1. explicit CLI `--state-dir`
2. `SYMDEX_STATE_DIR`
3. auto-discovered local `.symdex` in the current directory or ancestors
4. fallback to `~/.symdex`

This keeps first-time setup explicit while making repeat use frictionless.

## Affected Surfaces

- `symdex/core/storage.py`
- new state-path helper module
- `symdex/cli.py`
- `symdex/mcp/tools.py`
- `symdex/core/indexer.py`
- `symdex/core/watcher.py`
- tests covering storage, CLI, and registry behavior
- docs that describe where indexes live

## Behavioral Details

### Indexing

- `symdex --state-dir .symdex index .` creates local state
- registry updates should also refresh `registry.json`
- output should remain stable, but may include the state location for clarity

### Search and repo commands

- once `.symdex` exists in a workspace, `search`, `find`, `repos`, `gc`, `routes`, and MCP tools should use it automatically when invoked from that workspace

### Garbage collection

- stale repo detection should still operate on resolved absolute paths
- repo removal should delete the correct database file even when the registry stores relative paths

## Tradeoffs

### Why not replace global mode entirely?

Because the global registry is still valuable for:

- cross-repo search
- users who want one shared index store
- backward compatibility

### Why keep SQLite if `registry.json` exists?

Because the registry still needs transactional updates and the rest of the code already uses SQLite well. JSON is the visibility layer, not the source of truth.

## Success Criteria

- Existing users see no behavior change unless they opt in or already have a local `.symdex`
- Workspace-local mode stores databases under the requested directory
- `registry.json` is always refreshed when repo metadata changes
- Local-mode registry entries remain portable and human-readable
- Repo and search commands keep working with resolved absolute paths
