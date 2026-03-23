# Workspace-Local State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional workspace-local SymDex state mode with `.symdex` storage and `registry.json`, while preserving the current global `~/.symdex` default.

**Architecture:** Introduce a small state-resolution layer that decides where SymDex should keep its registry and repo databases. Keep SQLite as the operational registry, mirror the metadata into `registry.json`, and resolve relative local-mode paths back to absolute paths before using them elsewhere in the product.

**Tech Stack:** Python, Typer, SQLite, JSON, existing SymDex CLI/MCP/storage modules.

---

### Task 1: Add a state-resolution layer

**Files:**
- Create: `symdex/core/state.py`
- Test: `tests/unit/test_state_paths.py`

- [ ] Add helpers for default global state, explicit state-dir resolution, local `.symdex` discovery, and relative path serialization/resolution.
- [ ] Add tests for:
  - global fallback
  - explicit `SYMDEX_STATE_DIR`
  - local `.symdex` discovery from a nested working directory
  - relative path round-tripping

### Task 2: Teach storage to use local mode and write `registry.json`

**Files:**
- Modify: `symdex/core/storage.py`
- Test: `tests/unit/test_storage.py`

- [ ] Route `get_db_path()` and `get_registry_path()` through the new state layer.
- [ ] Update repo upsert/query/remove logic so workspace-local registry entries can be stored relative and resolved back to absolute paths.
- [ ] Mirror repo metadata into `registry.json` whenever the registry changes.
- [ ] Add tests for:
  - local-mode DB placement
  - registry.json creation
  - relative paths in the manifest
  - correct deletion of local-mode DB files

### Task 3: Surface state selection in the CLI

**Files:**
- Modify: `symdex/cli.py`
- Test: `tests/unit/test_cli_coverage.py`

- [ ] Add a global `--state-dir` option that sets the state location for the invoked command.
- [ ] Keep existing command behavior and output intact where possible.
- [ ] Add targeted CLI tests proving:
  - `index --state-dir .symdex` creates state under the workspace
  - `repos --state-dir .symdex --json` reads the same local registry
  - normal commands still work without a state override

### Task 4: Keep MCP and watcher behavior coherent

**Files:**
- Modify: `symdex/mcp/tools.py`
- Modify: `symdex/core/watcher.py`
- Test: `tests/unit/test_tools_coverage.py`
- Test: `tests/unit/test_watcher.py`

- [ ] Ensure MCP repo lookups and repo listing continue to work with resolved local-mode paths.
- [ ] Ensure watch mode indexes and cleans up against the correct local database when local state is active.

### Task 5: Update product docs after implementation

**Files:**
- Modify: `README.md`
- Modify: `SPEC.md`
- Modify: `CLAUDE.md`
- Modify: `context.md`
- Modify: `skills/symdex-code-search/SKILL.md`

- [ ] Document both storage modes.
- [ ] Add Docker/workspace-local examples using `.symdex`.
- [ ] Explain that `registry.json` is the human-readable manifest.
- [ ] Update any stale references that say indexes only live under `~/.symdex`.

### Task 6: Verify the shipped behavior

**Files:**
- Test: `tests/unit/test_state_paths.py`
- Test: `tests/unit/test_storage.py`
- Test: `tests/unit/test_cli_coverage.py`
- Test: `tests/unit/test_tools_coverage.py`

- [ ] Run targeted tests for the new storage/state behavior.
- [ ] Run `py -m py_compile` on changed Python modules.
- [ ] If the workspace temp-directory issue blocks broader pytest, state that explicitly and keep the verification claims narrow.
