# Search ROI Summary Implementation

Status: completed
Date: 2026-03-22

## Implemented Scope

- Added shared token-estimation helpers
- Added approximate search ROI footers to successful CLI search commands
- Added ROI payloads to MCP search responses
- Stored and reused line-count information during indexing so estimates have a stable basis

## User-Facing Behavior

Search commands such as `search`, `find`, `text`, and `semantic` now print an approximate before-and-after token comparison.

MCP consumers receive the same family of ROI metrics as structured output.

## Verification Summary

Verified through targeted smoke checks and unit coverage around token estimation and output formatting.

## Constraint

Estimates are intentionally approximate because one default tokenizer profile is used unless a richer tokenizer contract is added in the future.
