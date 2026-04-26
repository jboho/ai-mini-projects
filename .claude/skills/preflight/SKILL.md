---
name: preflight
description: >-
  Pre-PR quality check: runs ruff lint, ruff format check, and pytest;
  checks git status; produces READY / WARNINGS / NOT READY verdict.
  Invoke before opening a PR or merging a branch.
---

# Preflight Check

Run ALL checks and accumulate results — do not stop on first failure.

## Optional Args

- `/preflight skip format` — skip format check
- `/preflight skip test` — skip pytest
- No args → run everything

## Phase 0: Detection

- Detect current mini-project directory (or run from repo root)
- Check for `pyproject.toml` → use ruff + pytest (this repo's standard)
- Print planned checks before executing

## Phase 1: Environment Verification

- `git rev-parse --git-dir` — confirm git repo
- `git status --porcelain` — note uncommitted changes (warn, don't stop)
- Confirm virtualenv active (`.venv` present or conda env)

## Phase 2: Execute Checks (run all, no early exit)

| Check | Command | Pass Condition |
|---|---|---|
| LINT | `ruff check .` | exit 0 |
| FORMAT | `ruff format --check .` | exit 0 |
| TEST | `pytest` | exit 0, 0 failures |

Report each result inline as it completes:
```
[LINT]   ✅ PASSED (1.2s)
[FORMAT] ❌ FAILED — 3 files need reformatting
[TEST]   ✅ PASSED — 47 tests in 4.1s
```

## Phase 3: Git Status

- `git status --porcelain` — list uncommitted/untracked files
- `git diff --stat` if uncommitted changes present
- Report: current branch, commits ahead of origin, uncommitted count, untracked count

## Phase 4: Verdict

Compile full report:

```
## Preflight Report

| Check   | Status     | Duration |
|---------|------------|----------|
| LINT    | ✅ PASSED  | 1.2s     |
| FORMAT  | ❌ FAILED  | 0.8s     |
| TEST    | ✅ PASSED  | 4.1s     |

Git: branch `feat/my-feature`, 2 commits ahead, 1 uncommitted file

Verdict: ⚠️ READY WITH WARNINGS

FORMAT failed: run `ruff format .` to fix, then re-run preflight.
```

Verdict rules:
- All pass + no uncommitted changes → `✅ READY FOR PR` (offer to open PR with gh)
- All pass + uncommitted changes present → `⚠️ READY WITH WARNINGS`
- Any check fails → `❌ NOT READY` (list each failure, offer to fix)
