---
name: systematic-debugging
description: >-
  Systematic debugging protocol with hypothesis-driven investigation. Includes
  standard mode for quick debugging and deep RCA mode for persistent/complex
  issues. Use when fixing bugs, investigating errors, or conducting root cause
  analysis. Evidence-based, no guessing.
---

# Systematic Debugging

Methodical investigation to identify and fix bugs. No random changes. No guessing. Every action must be evidence-based and hypothesis-driven.

## When to Use

- Bug reports or unexpected behavior
- Error messages or stack traces
- Intermittent issues
- Failed previous debugging attempts
- Need definitive root cause analysis

## Modes

**Standard Mode** (default): Quick hypothesis-driven debugging
- Use for: Straightforward bugs, clear error messages, first debugging attempt
- Process: 7 phases, focused on rapid hypothesis testing

**Deep Mode (RCA)**: Root cause analysis with exhaustive investigation
- Use for: Persistent bugs, previous attempts failed, intermittent issues, critical systems
- Process: 6 phases, emphasizes reconnaissance and zero-trust audit
- Keywords: Include "deep", "rca", or "root cause" in bug description

---

## Standard Mode Protocol

### Phase 0: Problem Definition

**Directive:** Clearly define what's broken before attempting any fix.

**Questions to answer:**
1. What is the expected behavior?
2. What is the actual behavior?
3. When did it start happening? (Always worked? Recent regression? After specific change?)
4. How consistently does it occur? (Always? Sometimes? Under specific conditions?)

**Actions:**
1. If user provided error message/stack trace, analyze it
2. If no error details, ask for reproduction steps
3. Check recent git history for related changes: `git log --oneline -20`

**Output:**
```
## Problem Statement

**Expected:** [behavior]
**Actual:** [behavior]
**Consistency:** [always/intermittent/conditional]
**Recent changes:** [relevant commits or "none identified"]
```

**Constraint:** Do NOT proceed until the problem is clearly defined.

---

### Phase 1: Reproduction

**Directive:** Reproduce the bug in a controlled manner.

**Actions:**
1. Identify the minimal steps to reproduce
2. Execute those steps and observe the failure
3. Capture exact error messages, logs, or incorrect outputs

**Output:**
```
## Reproduction

**Steps:**
1. [step]
2. [step]
3. [observe failure]

**Evidence:**
[error message, log output, or screenshot description]

**Reproduced:** ✅ Yes / ❌ No (if no, gather more info)
```

**Constraint:** If unable to reproduce, do NOT guess. Ask for more information or access to logs/environment.

---

### Phase 2: Isolation

**Directive:** Narrow down where the bug originates.

**Isolation Techniques:**
1. **Binary search:** If recent regression, use `git bisect` or manual commit checkout
2. **Component isolation:** Identify which layer/component is failing
3. **Input isolation:** Find minimal input that triggers the bug
4. **Environment isolation:** Rule out environment-specific issues

**Questions to answer:**
- Which file(s) contain the bug?
- Which function(s) are involved?
- What is the exact line or operation that fails?

**Output:**
```
## Isolation

**Suspected location:** [file:function:line or component]
**Isolation method:** [how we narrowed it down]
**Confidence:** [high/medium/low]
```

---

### Phase 3: Hypothesis Formation

**Directive:** Form a clear, testable hypothesis about the root cause.

**Hypothesis requirements:**
- Must explain ALL observed symptoms
- Must be falsifiable (can be proven wrong)
- Must suggest a specific test to validate

**Common root cause categories:**
| Category | Examples |
|----------|----------|
| State | Stale state, race condition, uninitialized variable |
| Logic | Off-by-one, wrong operator, incorrect condition |
| Data | Null/undefined, wrong type, malformed input |
| Timing | Async issue, timeout, order of operations |
| Environment | Config, dependencies, permissions |
| Integration | API contract change, version mismatch |

**Output:**
```
## Hypothesis

**Root cause theory:** [specific explanation]

**This explains:**
- [symptom 1]
- [symptom 2]

**Test to validate:** [how we'll prove/disprove this]
```

**Constraint:** Form hypothesis BEFORE looking at code fixes. Resist the urge to jump to solutions.

---

### Phase 4: Hypothesis Testing

**Directive:** Test the hypothesis with minimal, targeted investigation.

**Actions:**
1. Read the suspected code (Read-only! No changes yet)
2. Add temporary logging/debugging if needed to gather evidence
3. Run the reproduction steps with debugging enabled
4. Analyze the results

**Output:**
```
## Hypothesis Test Results

**Test performed:** [what we did]
**Evidence gathered:** [logs, values observed, behavior]
**Verdict:** ✅ Hypothesis confirmed / ❌ Hypothesis rejected

[If rejected: return to Phase 3 with new information]
```

---

### Phase 5: Fix Implementation

**Directive:** Implement the minimal fix that addresses the root cause.

**Fix requirements:**
- Addresses the ROOT CAUSE, not just symptoms
- Minimal scope - don't refactor unrelated code
- Maintains existing behavior for non-buggy cases
- Follows codebase conventions

**Actions:**
1. Read the file(s) to be modified
2. Implement the fix
3. Re-read to verify the change is correct

**Output:**
```
## Fix Applied

**File(s) modified:** [list]
**Change summary:** [what was changed and why]
**Root cause addressed:** [confirm this fixes the actual cause]
```

---

### Phase 6: Verification

**Directive:** Prove the fix works and doesn't break anything else.

**Verification checklist:**
- [ ] Original reproduction steps now pass
- [ ] Related functionality still works (regression check)
- [ ] Edge cases handled
- [ ] Tests pass (existing tests)
- [ ] New test added to prevent regression (if applicable)

**Output:**
```
## Verification

**Original bug:** ✅ Fixed
**Regression check:** ✅ No regressions
**Tests:** ✅ All pass
**New test added:** [yes/no - describe if yes]
```

---

### Phase 7: Documentation & Prevention

**Directive:** Document findings and consider prevention measures.

**Output:**
```
## Debug Summary

**Bug:** [one-line description]
**Root cause:** [what was actually wrong]
**Fix:** [what was changed]
**Prevention:** [how to prevent similar bugs]

**Should this become a rule?** [yes/no - if yes, suggest running /add-rule]
```

---

## Deep Mode (RCA) Protocol

Use this mode for persistent/critical bugs that require exhaustive investigation.

### Phase 0: Reconnaissance & State Baseline (Read-Only)

**Directive:** Perform a non-destructive scan of the repository, runtime environment, configurations, and recent logs. Establish a high-fidelity, evidence-based baseline of the system's current state.

**Actions:**
1. Repository scan: file structure, recent changes, dependencies
2. Runtime environment: configurations, environment variables, logs
3. Related systems: APIs, databases, external services
4. Historical context: git log, previous issues, documentation

**Output:** Concise digest (≤ 200 lines) of findings.

**Constraint:** **No mutations permitted during this phase.**

---

### Phase 1: Isolate the Anomaly

**Directive:** Create a **minimal, reproducible test case** that reliably triggers the bug.

**Actions:**
1. **Define Correctness:** State the expected, non-buggy behavior
2. **Create a Failing Test:** Write a new automated test that fails precisely because of this bug (becomes your success signal)
3. **Pinpoint the Trigger:** Identify exact conditions, inputs, or sequence that causes failure

**Constraint:** Do not attempt fixes until you can reliably reproduce the failure on command.

---

### Phase 2: Root Cause Analysis (RCA)

**Directive:** Methodically investigate the failing pathway to find the definitive root cause.

**Evidence-Gathering Protocol:**
1. **Formulate a Testable Hypothesis:** State a clear theory (e.g., "Hypothesis: The auth token is expiring prematurely")
2. **Devise an Experiment:** Design a safe, non-destructive test to prove/disprove hypothesis
3. **Execute and Conclude:** Run experiment, present evidence, state conclusion. If wrong, formulate new hypothesis based on new evidence

**Forbidden Actions:**
- ❌ Applying a fix without confirmed root cause supported by evidence
- ❌ Re-trying a previously failed fix without new data
- ❌ Patching a symptom (e.g., adding null check) without understanding *why* the value is null

**Loop until:** Root cause is definitively identified with evidence.

---

### Phase 3: Remediation

**Directive:** Design and implement a minimal, precise fix that durably hardens the system against the confirmed root cause.

**Core Protocols:**
- **Read-Write-Reread:** For every file modified, read immediately before and after the change
- **System-Wide Ownership:** If root cause is in a shared component, analyze and fix all other consumers affected by the same flaw

**Fix requirements:**
- Addresses the ROOT CAUSE with evidence
- Minimal scope
- Follows codebase conventions
- Considers system-wide impact

---

### Phase 4: Verification & Regression Guard

**Directive:** Prove the fix resolved the issue without creating new ones.

**Verification Steps:**
1. **Confirm the Fix:** Re-run the failing test case from Phase 1. It **MUST** now pass
2. **Run Full Quality Gates:** Execute entire suite (unit, integration tests, linters)
3. **Autonomous Correction:** If fix introduces new failures, diagnose and resolve them

---

### Phase 5: Mandatory Zero-Trust Self-Audit

**Directive:** Conduct skeptical, zero-trust audit of your own fix.

**Audit Protocol:**
1. **Re-verify Final State:** With fresh commands, confirm all modified files are correct
2. **Hunt for Regressions:** Test primary workflow of the fixed component
3. **Check edge cases:** Verify fix works for boundary conditions

---

### Phase 6: Final Report & Verdict

**Directive:** Conclude with structured "After-Action Report."

**Report Structure:**
- **Root Cause:** Definitive statement of underlying issue, supported by key evidence
- **Remediation:** List of all changes applied to fix the issue
- **Verification Evidence:** Proof that bug is fixed and no new regressions
- **Final Verdict:** 
  - ✅ `"Self-Audit Complete. Root cause addressed, system state verified. No regressions identified. Mission accomplished."`
  - OR ⚠️ `"Self-Audit Complete. CRITICAL ISSUE FOUND during audit. Halting work. [Describe issue and recommend steps]."`

**Constraint:** Maintain inline TODO ledger using ✅ / ⚠️ / 🚧 markers throughout process.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Do Instead |
|--------------|--------------|------------|
| Random changes | Masks real cause, introduces new bugs | Form hypothesis first |
| Fixing symptoms | Bug will return or manifest elsewhere | Find root cause |
| Large fixes | Hard to verify, high regression risk | Minimal targeted fix |
| Skipping reproduction | Can't verify fix without it | Always reproduce first |
| Assuming the cause | Wastes time on wrong path | Test hypothesis with evidence |
| Patching without RCA | Technical debt accumulates | Understand why before fixing |

---

## Mode Selection Guide

| Scenario | Recommended Mode |
|----------|------------------|
| First debugging attempt | Standard |
| Clear error message | Standard |
| Straightforward logic bug | Standard |
| Previous fixes failed | Deep (RCA) |
| Intermittent/heisenbug | Deep (RCA) |
| Critical system | Deep (RCA) |
| Need definitive root cause | Deep (RCA) |
| Production incident | Deep (RCA) |

---

## Examples

**Standard mode:**
- "The login button throws a 404 error when clicked"
- "React component re-renders infinitely"
- "API returns wrong status code"

**Deep mode:**
- "Memory leak that only appears after 6+ hours in production (deep investigation needed)"
- "Intermittent test failures that we've tried fixing twice already (RCA required)"
- "Data corruption issue affecting critical customer data (root cause essential)"
