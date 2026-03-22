# Search ROI Summary Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show an estimated token-savings summary after search results so users can see how much work SymDex saved them.

**Architecture:** SymDex will attach a small ROI footer to successful search responses in both CLI and MCP surfaces. The footer will use one default tokenizer profile for all estimates, compute a conservative "without SymDex" cost from the searched content, compare that against the returned snippet/result size, and print a short playful closing line. The numbers are explicitly approximate unless a future caller provides an exact tokenizer context.

**Tech Stack:** Python, Typer, Rich, FastMCP, token counting helper

---

### Task 1: Define the search ROI data model

**Files:**
- Modify: `symdex/core/storage.py`
- Modify: `symdex/mcp/tools.py`
- Modify: `symdex/cli.py`

- [ ] **Step 1: Write the failing test**

Add a unit test that expects successful search results to include an ROI summary payload with `estimated_tokens_without_symdex`, `estimated_tokens_with_symdex`, `estimated_tokens_saved`, `lines_searched`, `files_searched`, and `tokenizer_name`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_tools_coverage.py::test_search_* -v`
Expected: fail because the ROI summary is not yet present.

- [ ] **Step 3: Write minimal implementation**

Add a small helper that returns a consistent ROI summary dict for search responses.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_tools_coverage.py::test_search_* -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add symdex/core/storage.py symdex/mcp/tools.py symdex/cli.py tests/unit/test_tools_coverage.py
git commit -m "feat: add search roi summary model"
```

### Task 2: Implement tokenizer-based estimate

**Files:**
- Modify: `symdex/search/semantic.py` or a new token utility module
- Modify: `symdex/core/storage.py`

- [ ] **Step 1: Write the failing test**

Add a unit test that feeds a known string into the token estimator and asserts the count is deterministic and marked approximate when the tokenizer is defaulted.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_*token* -v`
Expected: fail because the estimator does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement a single default tokenizer profile and a small token-count helper used by search summaries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_*token* -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add symdex/search/semantic.py symdex/core/storage.py tests/unit/test_*token*.py
git commit -m "feat: add default tokenizer token estimates"
```

### Task 3: Print the playful footer in CLI output

**Files:**
- Modify: `symdex/cli.py`
- Modify: `tests/unit/test_cli_coverage.py`

- [ ] **Step 1: Write the failing test**

Assert that `symdex search`, `symdex semantic`, and the relevant file lookup commands print the ROI footer after successful results, including the playful closing line.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_cli_coverage.py -v`
Expected: fail because the footer is missing.

- [ ] **Step 3: Write minimal implementation**

Render a compact footer below the results table. Keep the copy short and playful, but clearly labeled as approximate.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_cli_coverage.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add symdex/cli.py tests/unit/test_cli_coverage.py
git commit -m "feat: print search roi footer in cli"
```

### Task 4: Expose ROI summary in MCP responses

**Files:**
- Modify: `symdex/mcp/tools.py`
- Modify: `symdex/mcp/server.py`
- Modify: `tests/unit/test_tools_coverage.py`

- [ ] **Step 1: Write the failing test**

Assert that successful MCP search tool responses include the ROI summary fields.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_tools_coverage.py -v`
Expected: fail because the extra summary is not yet returned.

- [ ] **Step 3: Write minimal implementation**

Attach the ROI summary to search responses and keep the payload stable for clients.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_tools_coverage.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add symdex/mcp/tools.py symdex/mcp/server.py tests/unit/test_tools_coverage.py
git commit -m "feat: return search roi summary from mcp"
```

### Task 5: Verify summary wording and docs

**Files:**
- Modify: `README.md`
- Modify: `SPEC.md`
- Modify: `docs/pitch/PITCH.md`

- [ ] **Step 1: Update the docs**

Describe the footer as approximate, tokenizer-backed, and playful.

- [ ] **Step 2: Verify consistency**

Run: `rg -n "token savings|approximate|You’re in good hands|good hands" README.md SPEC.md docs/pitch`
Expected: all relevant docs use the same wording.

- [ ] **Step 3: Commit**

```bash
git add README.md SPEC.md docs/pitch/PITCH.md
git commit -m "docs: describe search roi footer"
```

---

**Open question to keep in mind:** if a future agent can provide an exact tokenizer/model identifier, the estimate can become model-specific, but this design intentionally starts with a single default tokenizer so the feature always works.
