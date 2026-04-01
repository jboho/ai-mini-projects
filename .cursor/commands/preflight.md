# preflight

{Optional: Specific checks to run, or 'skip <check>' to skip certain checks}

---

## **Mission Briefing: Pre-PR Preflight Check Protocol**

Run ALL checks and provide a complete report at the end, regardless of individual failures.

**For this repo (ai-mini-projects):** Use `.cursor/preflight.json`: lint (ruff check), format (ruff format --check), test (pytest). Ruff preferred; fall back to flake8/black if ruff not installed.

---

## **Phase 0: Project Detection & Configuration**

Read `.cursor/preflight.json` if present; else auto-detect (Python: pyproject.toml, requirements.txt). Output planned checks.

---

## **Phase 1: Environment Verification**

Verify git repo, uncommitted changes (warn but continue), venv/conda, dependencies. Output environment check summary.

---

## **Phase 2: Execute All Checks**

Run each check sequentially; capture stdout/stderr and duration; do NOT stop on failures. Report per check: LINT, FORMAT, TEST, any custom.

---

## **Phase 3: Git Status Check**

Run `git status --porcelain`, `git diff --stat` if uncommitted. Report branch, ahead count, uncommitted/untracked.

---

## **Phase 4: Final Report**

Compile results with verdict: ✅ READY FOR PR / ⚠️ READY WITH WARNINGS / ❌ NOT READY. If NOT READY, list failures and offer to help. If READY, suggest opening a PR.

---

**Begin preflight checks now.**
