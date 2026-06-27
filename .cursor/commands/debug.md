# debug

{Describe the bug, unexpected behavior, or error you're seeing. Include error messages, stack traces, or steps to reproduce if available.}

---

## **Mission Briefing: Systematic Debugging Protocol**

You are conducting a methodical investigation to identify and fix a bug. No random changes. No guessing. Every action must be evidence-based and hypothesis-driven.

---

## **Phase 0: Problem Definition**

- **Directive:** Clearly define what's broken before attempting any fix.
- **Questions to answer:**
  1. **What is the expected behavior?**
  2. **What is the actual behavior?**
  3. **When did it start happening?** (Always worked? Recent regression? After specific change?)
  4. **How consistently does it occur?** (Always? Sometimes? Under specific conditions?)
- **Actions:**
  1. If user provided error message/stack trace, analyze it.
  2. If no error details, ask for reproduction steps.
  3. Check recent git history for related changes: `git log --oneline -20`
- **Output:**

  ```
  ## Problem Statement

  **Expected:** [behavior]
  **Actual:** [behavior]
  **Consistency:** [always/intermittent/conditional]
  **Recent changes:** [relevant commits or "none identified"]
  ```

- **Constraint:** Do NOT proceed until the problem is clearly defined.

---

## **Phase 1: Reproduction**

- **Directive:** Reproduce the bug in a controlled manner.
- **Actions:**
  1. Identify the minimal steps to reproduce.
  2. Execute those steps and observe the failure.
  3. Capture exact error messages, logs, or incorrect outputs.
- **Output:**

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

- **Constraint:** If unable to reproduce, do NOT guess. Ask for more information or access to logs/environment.

---

## **Phase 2: Isolation**

- **Directive:** Narrow down where the bug originates.
- **Isolation Techniques:**
  1. **Binary search:** If recent regression, use `git bisect` or manual commit checkout
  2. **Component isolation:** Identify which layer/component is failing
  3. **Input isolation:** Find minimal input that triggers the bug
  4. **Environment isolation:** Rule out environment-specific issues
- **Questions to answer:**
  - Which file(s) contain the bug?
  - Which function(s) are involved?
  - What is the exact line or operation that fails?
- **Output:**

  ```
  ## Isolation

  **Suspected location:** [file:function:line or component]
  **Isolation method:** [how we narrowed it down]
  **Confidence:** [high/medium/low]
  ```

---

## **Phase 3: Hypothesis Formation**

- **Directive:** Form a clear, testable hypothesis about the root cause.
- **Hypothesis requirements:**
  - Must explain ALL observed symptoms
  - Must be falsifiable (can be proven wrong)
  - Must suggest a specific test to validate
- **Common root cause categories:**
  | Category | Examples |
  |----------|----------|
  | State | Stale state, race condition, uninitialized variable |
  | Logic | Off-by-one, wrong operator, incorrect condition |
  | Data | None/wrong type, malformed input |
  | Timing | Async issue, timeout, order of operations |
  | Environment | Config, dependencies, API keys, venv |
  | Integration | API contract change, version mismatch |
- **Output:**

  ```
  ## Hypothesis

  **Root cause theory:** [specific explanation]

  **This explains:**
  - [symptom 1]
  - [symptom 2]

  **Test to validate:** [how we'll prove/disprove this]
  ```

- **Constraint:** Form hypothesis BEFORE looking at code fixes. Resist the urge to jump to solutions.

---

## **Phase 4: Hypothesis Testing**

- **Directive:** Test the hypothesis with minimal, targeted investigation.
- **Actions:**
  1. Read the suspected code (Read-only! No changes yet)
  2. Add temporary logging/debugging if needed to gather evidence
  3. Run the reproduction steps with debugging enabled
  4. Analyze the results
- **Output:**

  ```
  ## Hypothesis Test Results

  **Test performed:** [what we did]
  **Evidence gathered:** [logs, values observed, behavior]
  **Verdict:** ✅ Hypothesis confirmed / ❌ Hypothesis rejected

  [If rejected: return to Phase 3 with new information]
  ```

---

## **Phase 5: Fix Implementation**

- **Directive:** Implement the minimal fix that addresses the root cause.
- **Fix requirements:**
  - Addresses the ROOT CAUSE, not just symptoms
  - Minimal scope - don't refactor unrelated code
  - Maintains existing behavior for non-buggy cases
  - Follows codebase conventions (`.cursor/rules/python-style.mdc`)
- **Actions:**
  1. Read the file(s) to be modified
  2. Implement the fix
  3. Re-read to verify the change is correct
- **Output:**

  ```
  ## Fix Applied

  **File(s) modified:** [list]
  **Change summary:** [what was changed and why]
  **Root cause addressed:** [confirm this fixes the actual cause]
  ```

---

## **Phase 6: Verification**

- **Directive:** Prove the fix works and doesn't break anything else.
- **Verification checklist:**
  1. [ ] Original reproduction steps now pass
  2. [ ] Related functionality still works (regression check)
  3. [ ] Edge cases handled
  4. [ ] Tests pass (pytest)
  5. [ ] New test added to prevent regression (if applicable)
- **Output:**

  ```
  ## Verification

  **Original bug:** ✅ Fixed
  **Regression check:** ✅ No regressions
  **Tests:** ✅ All pass
  **New test added:** [yes/no - describe if yes]
  ```

---

## **Phase 7: Documentation & Prevention**

- **Directive:** Document findings and consider prevention measures.
- **Output:**

  ```
  ## Debug Summary

  **Bug:** [one-line description]
  **Root cause:** [what was actually wrong]
  **Fix:** [what was changed]
  **Prevention:** [how to prevent similar bugs]

  **Should this become a rule?** [yes/no - if yes, suggest running /add-rule]
  ```

---

## **Anti-Patterns to Avoid**

| Anti-Pattern | Why It's Bad | Do Instead |
|--------------|--------------|-------------|
| Random changes | Masks real cause, introduces new bugs | Form hypothesis first |
| Fixing symptoms | Bug will return or manifest elsewhere | Find root cause |
| Large fixes | Hard to verify, high regression risk | Minimal targeted fix |
| Skipping reproduction | Can't verify fix without it | Always reproduce first |
| Assuming the cause | Wastes time on wrong path | Test hypothesis |

---

**Begin debugging now.**
