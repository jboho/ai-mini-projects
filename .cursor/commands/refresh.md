# refresh

{A concise but complete description of the persistent bug or issue. Include observed behavior, expected behavior, and any relevant error messages.}

---

## **Mission Briefing: Root Cause Analysis & Remediation Protocol**

Previous, simpler attempts to resolve this issue have failed. Standard procedures are now suspended. You will initiate a **deep diagnostic protocol.**

Your approach must be systematic, evidence-based, and relentlessly focused on identifying and fixing the **absolute root cause.** Patching symptoms is a critical failure.

---

## **Phase 0: Reconnaissance & State Baseline (Read-Only)**

Non-destructive scan of repository, runtime, configs, logs. Output concise digest (≤ 200 lines). No mutations.

---

## **Phase 1: Isolate the Anomaly**

Create minimal, reproducible test case. Define correctness, create failing test if possible, pinpoint trigger. No fixes until reproducible.

---

## **Phase 2: Root Cause Analysis (RCA)**

Formulate testable hypothesis, devise experiment, execute and conclude. Forbidden: fix without confirmed root cause; re-try failed fix without new data; patch symptom without understanding why.

---

## **Phase 3: Remediation**

Minimal, precise fix. Read-Write-Reread per file. If root cause is in shared component, analyze and fix all affected consumers.

---

## **Phase 4: Verification & Regression Guard**

Re-run failing test (must pass). Run full quality gates (ruff check, ruff format, pytest). Autonomously fix any new failures.

---

## **Phase 5: Mandatory Zero-Trust Self-Audit**

Re-verify final state with fresh commands. Test primary workflow for regressions.

---

## **Phase 6: Final Report & Verdict**

Report: Root Cause, Remediation, Verification Evidence, Final Verdict ("Mission accomplished" or "CRITICAL ISSUE FOUND..."). Maintain ✅/⚠️/🚧 TODO ledger.
