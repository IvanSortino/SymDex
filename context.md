# SymDex Context

## Current Snapshot

- Version at this checkout: `0.1.21`
- Git tag at this checkout: `v0.1.21`
- Exact Git HEAD varies by checkout. Verify locally with `git rev-parse HEAD` when you need the precise commit.
- Product status: active and productized
- Primary positioning: repo-local codebase oracle for AI coding agents

## Current Product Truth

SymDex currently ships:

- CLI, stdio MCP, and streamable HTTP MCP delivery
- 20 MCP tools
- 16 language surfaces
- repo-local SQLite-backed indexes
- exact symbol search, semantic search, text search, call graphs, and route extraction
- index-time code summaries
- search-time approximate token-savings reporting
- optional workspace-local state with `./.symdex/registry.json`
- optional embedding backends for local `sentence-transformers` and Voyage AI
- stable auto-naming for repo ids when `--repo` is omitted on `index` or `watch`
- upgrade notices on normal human-facing CLI commands
- visible `--state-dir` support at both the global and subcommand level
- shell compatibility aliases for `index-folder`, `index-repo`, and `list-repos`
- clearer semantic-search errors when a repo is unindexed or lacks embeddings

## Recently Completed Work

Recent shipped product changes now reflected in the docs:

- workspace-local state for Docker and portable worktrees
- `registry.json` manifest with relative paths and `last_indexed`
- search ROI footer with approximate token savings
- optional `sentence-transformers` dependency via extras
- Voyage AI backend including optional multimodal indexing
- Kotlin, Dart, and Swift parser support
- broader multi-language route extraction coverage
- public agent skill published from this repo using the standard `skills/<name>/SKILL.md` layout

## Local Machine State

Verified earlier in this environment:

- global `pip` install should be kept aligned with the latest released SymDex version
- global `uv` tool install should be kept aligned with the latest released SymDex version
- repo, `.codex`, `.agents`, and `.claude` copies of the SymDex skill were aligned

## Documentation State

The markdown set is now expected to stay aligned around these files:

- `README.md` for public product usage
- `AGENTS.md` for repo-level agent guidance
- `SPEC.md` for the current product contract
- `CLAUDE.md` for internal contributor and agent rules
- `skills/symdex-code-search/SKILL.md` for installable agent behavior
- `docs/superpowers/specs/*` and `docs/superpowers/plans/*` for shipped feature decisions and implementation notes

## Known Operational Issues

- Local `pytest` runs in this workspace can still fail during teardown because Windows temp directories become permission-locked.
- GitHub Actions release success is not enough to prove public PyPI visibility from this machine, because direct DNS access to `pypi.org` has failed here during verification.
- The correct public rule is: treat GitHub Actions as packaging evidence and verify public registry visibility independently when release status matters.

## Current Documentation Rules

- Do not leave stale phase language in public docs when the product has already shipped beyond that phase.
- Keep repo counts, language counts, tool counts, and install commands synchronized across README, skill docs, and internal docs.
- Keep claims about PyPI and release state precise.
- Prefer plain English and current product truth over historical planning prose.

## Near-Term Priorities

- Keep parser coverage and route extraction consistent across all supported languages.
- Keep PyPI and packaging verification explicit and trustworthy.
- Keep agent-facing docs sharp so adoption does not depend on tribal knowledge.
