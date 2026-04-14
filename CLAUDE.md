# CLAUDE.md

This repository builds SymDex.
SymDex is a repo-local codebase oracle for AI coding agents, delivered as a CLI plus MCP server.

## Current Product Truth

- Current version at this checkout: `0.1.19`
- Current tag at this checkout: `v0.1.19`
- Current MCP tool count: 20
- Current language surfaces: 17
- Default state directory: `~/.symdex`
- Optional workspace-local state directory: `./.symdex`

## What SymDex Must Continue To Be

- local-first
- SQLite-backed
- precise at symbol and file-slice retrieval
- coherent across CLI, MCP, README, skill docs, and packaging
- optimized for lower-token agent navigation

## Current Feature Surface

SymDex currently supports:

- exact symbol search
- semantic search
- indexed text search
- file outlines and repo outlines
- callers and callees
- route extraction
- repo stats and Lines of Code
- search ROI summaries
- index-time code summaries
- watch mode and invalidation
- workspace-local state with `registry.json`
- optional local and Voyage embedding backends
- Kotlin, Dart, and Swift along with the older language set

## Documentation Rules

- `README.md` is the public product page and must stay crisp and current.
- `AGENTS.md` is the repo-level guide for external agents and should explain how to use SymDex effectively.
- `SPEC.md` is the current product contract, not a graveyard of historical phases.
- `context.md` is the internal project snapshot and must reflect verified current state.
- shipped feature docs under `docs/superpowers/` should be marked as shipped or completed, not left looking speculative.

## Release Truth Rules

- Do not claim public PyPI visibility solely because a GitHub Actions publish job succeeded.
- When release status matters, distinguish between:
  - build and publish pipeline success
  - public registry visibility independently verified
- Keep the release flow tag-driven and artifact-based.

## Verification Rules

- Do not claim parser or route support without direct evidence.
- Do not claim a packaging fix works forever unless the workflow and its failure mode were both re-audited.
- Prefer concrete counts and checked facts over broad product hype.

## Product Boundaries

- SymDex is not a full type checker.
- SymDex is not an automated refactoring engine.
- SymDex should complement editors, LSPs, and agent runtimes rather than trying to replace all of them.

## Current Priorities

- keep markdown docs synchronized after every meaningful feature change
- keep mobile-language support and multi-language routes honest
- keep the skill, README, and repo metadata aligned
- keep packaging, install, and upgrade paths simple and trustworthy
