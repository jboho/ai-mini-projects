# test

{Describe the feature, change, or behavior you want to test. This can be a new feature you're about to build, an existing feature to add coverage for, or a bug fix that needs a regression test.}

---

## **Mission Briefing: Test-First Development Protocol**

Collaborative dialogue to design tests BEFORE implementation. Tests are a specification.

**For this repo (ai-bootcamp):** Python/pytest; use existing patterns in `mini-exercises/`. Run with `pytest` (per exercise or project root). See `.cursor/rules/quality-gates.mdc` and `codebase-conformance-python.mdc`.

---

## **Phase 0: Feature Understanding**

Understand core behavior, triggers, inputs, outputs, side effects, constraints. Output summary and clarifying questions. Do not proceed until clear.

---

## **Phase 1: Test Strategy Discussion**

Discuss unit vs integration vs E2E trade-offs. Recommend primary/secondary strategy. Pause for agreement.

---

## **Phase 2: Test Case Identification**

Happy path, edge cases, error cases, state variations. Output proposed cases with input/expected/priority. Get confirmation.

---

## **Phase 3: Data & Mock Strategy**

Test data and mocking; align with codebase (pytest, fixtures, `unittest.mock`). Pause for confirmation.

---

## **Phase 4: Test Structure Agreement**

File location (`tests/` or co-located `test_*.py`), naming, structure. Confirm with developer.

---

## **Phase 5: Test Implementation**

Write tests per spec. Run to confirm they fail (TDD red). Report file and list; suggest `/request` to implement.

---

## **Phase 6: Implementation Guidance**

When implementing: make tests pass, run after each change, refactor after green. RED → GREEN → REFACTOR.

---

Pause for developer input after each phase. Avoid testing implementation details; mock boundaries only; cover edge cases.

---

**Begin test design dialogue now.**
