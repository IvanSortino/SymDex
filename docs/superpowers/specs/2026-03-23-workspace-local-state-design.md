# Workspace-Local State Design

Status: shipped
Date: 2026-03-23

## Goal

Honor the Docker and portable-worktree request without breaking the existing global `~/.symdex` model.

## Shipped Behavior

SymDex now supports an optional workspace-local state mode.

Enable it with either:

```bash
SYMDEX_STATE_DIR=.symdex symdex index ./src --repo src
```

or:

```bash
symdex --state-dir .symdex index ./src --repo src
```

In that mode SymDex writes:

- `./.symdex/<repo>.db`
- `./.symdex/registry.db`
- `./.symdex/registry.json`

`registry.json` stores:

- `name`
- `root_path`
- `db_path`
- `last_indexed`

In workspace-local mode, `root_path` and `db_path` are relative to the workspace root and `last_indexed` is recorded in `YYYY-MM-DD HH:mm:ss`.

## Example Manifest

```json
[
  {
    "name": "src",
    "root_path": "./src",
    "db_path": "./.symdex/src.db",
    "last_indexed": "2026-03-23 09:43:42"
  },
  {
    "name": "submodule",
    "root_path": "./submodule",
    "db_path": "./.symdex/submodule.db",
    "last_indexed": "2026-03-23 09:50:42"
  }
]
```

## Deliberate Refinements

The original request asked for `./symdex/`.
SymDex ships `./.symdex/` instead because it is safer for repo-local tooling and less likely to be indexed or committed accidentally.

The feature is optional instead of mandatory so existing users relying on `~/.symdex` are not broken.

## Outcome

This preserves the default global workflow while adding a portable local-state option for Docker, worktrees, and team-shared environments.
