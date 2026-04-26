---
name: test-driven-development
description: >-
  Test-first development protocol with collaborative test design before
  implementation. Covers feature understanding, test strategy, test case
  identification, mocking strategy, and TDD red-green-refactor cycle.
  Use when building new features, adding test coverage, or creating regression
  tests.
---

# Test-Driven Development

Collaborative dialogue to design tests BEFORE writing implementation code. This ensures deep understanding of requirements and writing only the code necessary to pass well-designed tests.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**

- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always:**

- Building new features
- Adding test coverage to existing code
- Creating regression tests for bugs
- Unclear requirements (tests clarify intent)
- Complex business logic requiring specification

**Exceptions (ask your human partner):**

- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## Philosophy

**Tests are a specification.** If we can't describe what to test, we don't understand the feature well enough to build it.

**TDD Cycle:**
```
RED    -> Write a failing test
GREEN  -> Write minimal code to pass
REFACTOR -> Clean up while keeping tests green
```

---

## Phase 0: Feature Understanding

**Directive:** Deeply understand what we're testing before discussing HOW to test.

**Questions to explore:**
1. **What is the core behavior?** What should this feature/change DO?
2. **Who/what triggers it?** User action? API call? Scheduled job? Event?
3. **What are the inputs?** What data does it receive?
4. **What are the outputs?** What should it return/produce/change?
5. **What are the side effects?** Database changes? API calls? Notifications?
6. **What are the constraints?** Validation rules? Business rules? Permissions?

**Output:**
```
## Feature Understanding

**Summary:** [one paragraph description]

**Inputs:** [list]
**Outputs:** [list]
**Side effects:** [list]
**Constraints:** [list]

**Clarifying questions for you:**
1. [question about unclear aspect]
2. [question about edge case]
```

**Constraint:** Have this dialogue. Do NOT proceed until requirements are clear.

**Checkpoint:** *"Does this capture the feature correctly?"*

---

## Phase 1: Test Strategy Discussion

**Directive:** Discuss what types of tests are most valuable for this feature.

### Test Type Options

| Type | Best For | Trade-offs |
|------|----------|------------|
| **Unit Tests** | Pure logic, calculations, transformations | Fast, isolated, but may miss integration issues |
| **Integration Tests** | Component interactions, API endpoints | Slower, but catches real-world issues |
| **E2E Tests** | Critical user journeys | Slowest, flaky, but highest confidence |
| **Contract Tests** | API boundaries between services | Good for microservices |
| **Snapshot Tests** | UI components, serialized output | Easy to write, but brittle |

**Present recommendation:**
```
## Test Strategy Discussion

Based on this feature, I recommend focusing on:

**Primary:** [test type] because [reason]
**Secondary:** [test type] for [specific aspect]

**My reasoning:**
- [why this strategy fits the feature]
- [what risks it mitigates]

**Questions for you:**
1. Are there existing patterns in the codebase for testing similar features?
2. What's the risk level of this feature? (affects test depth)
3. Any specific scenarios you're worried about?

**Do you agree with this approach, or would you prefer different coverage?**
```

**Checkpoint:** *"Do you agree with this test strategy?"*

---

## Phase 2: Test Case Identification

**Directive:** Collaboratively identify the specific test cases needed.

### Categories to Cover

**Happy Path:** The main success scenario(s). What happens when everything works correctly?

**Edge Cases:** Boundary conditions, empty inputs, maximum values, special characters

**Error Cases:** Invalid inputs, missing data, unauthorized access, external failures

**State Variations:** Different starting states that affect behavior

**Output format:**
```
## Proposed Test Cases

### Happy Path
1. **[Test name]** - [description]
   - Input: [what]
   - Expected: [outcome]
   - Priority: HIGH

### Edge Cases
1. **[Test name]** - [description]
   - Input: [what]
   - Expected: [outcome]
   - Priority: MEDIUM

### Error Cases
1. **[Test name]** - [description]
   - Input: [what]
   - Expected: [outcome]
   - Priority: HIGH

---

**Review these cases:**
- Are any critical scenarios missing?
- Are any of these unnecessary?
- Should any be higher/lower priority?
```

**Checkpoint:** *"Are these the right test cases?"*

---

## Phase 3: Data & Mock Strategy

**Directive:** Determine what test data and mocking is needed.

### Test Data

```
## Test Data Requirements

**Data needed:**
| Data | Source | Notes |
|------|--------|-------|
| User object | Factory/fixture | Need valid and invalid examples |
| API response | Mock | Need success and error responses |

**Existing fixtures/factories to use:**
- [list any found in codebase]

**New fixtures needed:**
- [list what needs to be created]
```

### Mocking Strategy

```
## Mocking Strategy

**External dependencies to mock:**
| Dependency | Why Mock | Mock Behavior |
|------------|----------|---------------|
| Database | Isolation, speed | In-memory or mock repository |
| External API | Reliability, cost | Return fixtures |
| Time/Date | Determinism | Fixed timestamp |
| Random | Determinism | Seeded/fixed values |

**Should NOT mock:**
- [things that should use real implementations]

**Questions:**
1. Do you have preferred mocking libraries/patterns?
2. Should we use existing test utilities or create new ones?
3. Any external services that are particularly tricky to mock?
```

**Checkpoint:** *"Does this data/mock strategy work?"*

---

## Phase 4: Test Structure Agreement

**Directive:** Agree on the test file structure and naming.

**Present plan:**
```
## Test Structure

**File location:** [path based on codebase conventions]
**Naming pattern:** [based on existing patterns]

**Proposed structure:**
describe('[Feature/Component Name]', () => {
  describe('[method/action]', () => {
    describe('when [condition]', () => {
      it('should [expected behavior]', () => {})
    })
  })
})

**Setup/teardown needs:**
- beforeEach: [what setup]
- afterEach: [what cleanup]
- beforeAll: [expensive setup if any]

**Does this structure work for you?**
```

**Checkpoint:** *"Happy with this test structure?"*

---

## Phase 5: Test Implementation (RED Phase)

**Directive:** Write the tests based on agreed specifications.

**Implementation order:**
1. Set up test file with imports and describe blocks
2. Implement test data factories/fixtures if needed
3. Write tests in priority order (HIGH first)
4. Run tests to confirm they fail (TDD red phase)

**Requirements for each test:**
- One behavior per test
- Clear, descriptive name
- Real code (no mocks unless unavoidable)

**MANDATORY: Watch it fail.**

```bash
npm test path/to/test.test.ts
```

Confirm:
- Test fails (not errors)
- Failure message is expected
- Fails because feature is missing (not typos)

**Test passes immediately?** You're testing existing behavior. Fix the test.

**Test errors?** Fix the error, re-run until it fails correctly.

**Output:**
```
## Tests Written

**File:** [path]

**Tests implemented:**
- [test name] - currently FAILING (expected, no implementation yet)
- [test name] - currently FAILING
- ...

**All tests are failing as expected.** This confirms they're testing
real behavior that doesn't exist yet.

**Ready to implement?** Run `/request` with the feature description,
and I'll implement code to make these tests pass.
```

**Checkpoint:** *"Ready to implement, or adjust tests first?"*

---

## Phase 6: Implementation Guidance (GREEN Phase)

**Directive:** After tests are written, guide implementation to pass tests.

**When implementation is requested:**
1. Focus on making tests pass, nothing more
2. Run tests after each change
3. Refactor only after tests are green

**GREEN — Write simplest code to pass the test.**

Don't add features, refactor other code, or "improve" beyond the test.

```bash
npm test path/to/test.test.ts
```

Confirm:
- Test passes
- Other tests still pass
- Output pristine (no errors, warnings)

**Test fails?** Fix code, not test.

**Other tests fail?** Fix now.

**REFACTOR — Clean up after green only:**

- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior.

**Then: Next failing test for next feature.**

**Implementation tips:**
- One failing test at a time
- Simplest possible implementation first
- Resist the urge to add features not covered by tests
- If test is hard to pass, test might be wrong - discuss with developer

---

## Common Rationalizations

These are NOT valid reasons to skip TDD. If you catch yourself thinking any of these, stop.

| Rationalization | Reality |
|----------------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll write tests after" | Tests passing immediately prove nothing. You verify what you built, not what's required. |
| "Tests after achieve the same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" You'll test what you remembered, not what you discovered. |
| "Already manually tested" | Ad-hoc is not systematic. No record, can't re-run, you'll forget cases under pressure. |
| "Deleting X hours of work is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. Working code without real tests is a liability. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after with extra steps. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration completely, then start with TDD. |
| "Test is hard to write = skip it" | Listen to the test. Hard to test = hard to use. Simplify the design. |
| "TDD will slow me down" | TDD is faster than debugging. "Pragmatic" shortcuts = debugging in production = slower. |
| "Manual test is faster right now" | Manual doesn't prove edge cases. You'll re-test every change manually forever. |
| "Existing code has no tests" | You're improving it now. Add tests for what you're changing. |
| "This is different because..." | It's not. All rationalizations lead here. Delete code. Start over with TDD. |
| "It's about spirit not ritual" | The ritual IS the spirit. Seeing the test fail proves it tests the right thing. |
| "TDD is dogmatic, I'm being pragmatic" | TDD finds bugs before commit, prevents regressions, documents behavior, enables refactoring. That IS pragmatic. |

---

## Red Flags — STOP and Start Over

If any of these happen, the TDD process was violated. Delete the implementation and restart from the failing test.

- Code written before test
- Test written after implementation
- Test passes immediately (wasn't testing new behavior)
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**

---

## Dialogue Checkpoints

Throughout this process, pause for developer input at these points:

| Checkpoint | Question |
|------------|----------|
| After Phase 0 | "Does this capture the feature correctly?" |
| After Phase 1 | "Do you agree with this test strategy?" |
| After Phase 2 | "Are these the right test cases?" |
| After Phase 3 | "Does this data/mock strategy work?" |
| After Phase 4 | "Happy with this test structure?" |
| After Phase 5 | "Ready to implement, or adjust tests first?" |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Do Instead |
|--------------|--------------|------------|
| Testing implementation details | Tests break on refactor | Test behavior/outcomes |
| Too many mocks | Tests pass but code doesn't work | Mock boundaries only |
| Testing obvious things | Wastes time, clutters suite | Focus on valuable cases |
| One massive test | Hard to debug failures | Small, focused tests |
| Skipping edge cases | Bugs in production | Cover boundaries |
| Writing tests after code | Loses specification benefit | Tests first always |
| Green test without implementation | False confidence | Verify test fails first |
| Vague test names | Can't tell what broke | Name describes behavior |

---

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered
- [ ] Test names describe behavior, not implementation

Can't check all boxes? You skipped TDD. Start over.

---

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write wished-for API. Write assertion first. Ask your human partner. |
| Test too complicated | Design too complicated. Simplify interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify design. |

## Debugging Integration

Bug found? Write failing test reproducing it. Follow TDD cycle. Test proves fix and prevents regression.

Never fix bugs without a test.

---

## Examples

**Unit test for pure function:**
```javascript
describe('calculateDiscount', () => {
  it('should apply 10% discount for orders over $100', () => {
    expect(calculateDiscount(150)).toBe(15)
  })

  it('should return 0 for orders under $100', () => {
    expect(calculateDiscount(50)).toBe(0)
  })
})
```

**Bug fix example (RED -> verify -> GREEN -> verify -> REFACTOR):**

Bug: Empty email accepted

RED:
```typescript
test('rejects empty email', async () => {
  const result = await submitForm({ email: '' })
  expect(result.error).toBe('Email required')
})
```

Verify RED:
```bash
$ npm test
FAIL: expected 'Email required', got undefined
```

GREEN:
```typescript
function submitForm(data: FormData) {
  if (!data.email?.trim()) {
    return { error: 'Email required' }
  }
  // ...
}
```

Verify GREEN:
```bash
$ npm test
PASS
```

REFACTOR: Extract validation for multiple fields if needed.

---

## Final Rule

```
Production code -> test exists and failed first
Otherwise -> not TDD
```

No exceptions without your human partner's permission.
