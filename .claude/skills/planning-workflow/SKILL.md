---
name: planning-workflow
description: >-
  Implementation planning protocol with bite-sized task granularity (2-5 minute steps),
  TDD cycle structure, and self-review checklist. Use before implementing features,
  refactorings, or complex changes. Ensures clear requirements and executable plan.
---

# Planning Workflow

Create detailed implementation plans before writing code. Break work into atomic, bite-sized tasks with clear completion criteria.

## When to Use

- Before implementing new features
- Before major refactorings
- When requirements are unclear or complex
- When multiple approaches are possible
- Before starting work on unclear tickets/issues

## Philosophy

**Plans are executable roadmaps.** If you can't break a feature into 2-5 minute tasks, you don't understand it well enough to implement it.

**Planning Cycle:**
```
📋 UNDERSTAND  → Clarify requirements and success criteria
🔍 ANALYZE     → Identify existing patterns and constraints
🗺️  DESIGN     → Choose approach and break into tasks
✅ VALIDATE    → Review plan for completeness and risks
```

---

## Phase 0: Requirement Understanding

**Directive:** Deeply understand what we're building before planning HOW to build it.

**Questions to explore:**

1. **What is the core purpose?**
   - What problem does this solve?
   - Who benefits and how?
   - What defines success?

2. **What are the inputs/outputs?**
   - What data/events trigger this?
   - What should it produce/change?
   - What are the side effects?

3. **What are the constraints?**
   - Performance requirements?
   - Security considerations?
   - Backward compatibility needs?
   - Platform/browser/environment constraints?

4. **What already exists?**
   - Similar features in the codebase?
   - Existing utilities to reuse?
   - Patterns to follow?

**Output:**
```
## Requirement Summary

**Purpose:** [One sentence describing what we're building]

**Success Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

**Constraints:**
- Constraint 1
- Constraint 2

**Existing Patterns:**
- Pattern 1: [where it lives, how it works]
- Pattern 2: [where it lives, how it works]
```

**Constraint:** Do not proceed until requirements are clear. If uncertain, ask clarifying questions ONE AT A TIME.

---

## Phase 1: Approach Design

**Directive:** Propose 2-3 potential approaches and collaboratively select one.

**Questions to explore:**

1. **What are the options?**
   - Approach A: [brief description]
   - Approach B: [brief description]
   - Approach C: [brief description, if applicable]

2. **What are the tradeoffs?**
   - Complexity: Which is simplest?
   - Performance: Which is fastest?
   - Maintainability: Which is easiest to change later?
   - Risk: Which has fewest unknowns?

3. **What do similar features do?**
   - Search codebase for similar implementations
   - Follow established patterns unless there's a compelling reason to diverge

**Output:**
```
## Approach Options

### Option A: [Name]
**Description:** [How it works]
**Pros:** [Advantages]
**Cons:** [Disadvantages]

### Option B: [Name]
**Description:** [How it works]
**Pros:** [Advantages]
**Cons:** [Disadvantages]

**Recommendation:** [Option X] because [reason]
```

**Constraint:** Present options to user. Wait for selection before proceeding.

---

## Phase 2: Task Breakdown

**Directive:** Break the work into atomic, bite-sized tasks (2-5 minutes each) with clear completion criteria.

**Task Granularity Rules:**

- **Too Large:** "Implement user authentication" ❌
- **Good Size:** "Add username/password fields to login form" ✅
- **Too Large:** "Add API endpoint" ❌
- **Good Size:** "Create `/api/users` GET handler with ID param validation" ✅

**Task Structure:**
```
- [ ] **Task ID** (Xm): Clear action with completion criteria
      Dependencies: [Task IDs this depends on]
      Files: [Files to modify]
```

**TDD Integration:**
For each feature task, include corresponding test tasks:
```
- [ ] **TASK-001** (3m): Write test: User can submit login form
- [ ] **TASK-002** (2m): Implement form submission handler
- [ ] **TASK-003** (1m): Verify test passes
```

**Output:**
```
## Implementation Tasks

### Phase 1: Setup
- [ ] **SETUP-001** (2m): Create feature branch `feature/user-auth`
- [ ] **SETUP-002** (1m): Create test file `src/auth/login.test.ts`

### Phase 2: Core Implementation
- [ ] **CORE-001** (3m): Write test for login form validation
      Files: src/auth/login.test.ts
- [ ] **CORE-002** (4m): Implement form validation logic
      Files: src/auth/login.ts
      Dependencies: CORE-001
- [ ] **CORE-003** (2m): Write test for API integration
      Files: src/auth/login.test.ts
- [ ] **CORE-004** (5m): Implement API call with error handling
      Files: src/auth/login.ts, src/api/auth.ts
      Dependencies: CORE-003

### Phase 3: Edge Cases
- [ ] **EDGE-001** (3m): Test: Invalid credentials handling
- [ ] **EDGE-002** (3m): Implement: Show error message on invalid creds
- [ ] **EDGE-003** (2m): Test: Network timeout handling
- [ ] **EDGE-004** (3m): Implement: Retry logic with timeout

### Phase 4: Integration & Verification
- [ ] **INT-001** (3m): Run full test suite
- [ ] **INT-002** (2m): Manual testing in dev environment
- [ ] **INT-003** (2m): Check linter/type errors
- [ ] **INT-004** (2m): Update documentation if needed

**Total Estimate:** [Sum of all task times]
```

**Constraints:**
- Every task must have a time estimate (1-5 minutes)
- Tasks >5 minutes must be broken down further
- Include TDD cycle (test → implement → verify) for feature code
- Include verification tasks at the end

---

## Phase 3: Risk Identification

**Directive:** Identify potential blockers, unknowns, and areas requiring research.

**Questions to explore:**

1. **What could go wrong?**
   - External dependencies (APIs, services)?
   - Unclear requirements or edge cases?
   - Performance concerns?
   - Breaking changes to existing features?

2. **What do we not know?**
   - New libraries or frameworks?
   - Unfamiliar parts of the codebase?
   - Need for new infrastructure?

3. **What could block progress?**
   - Waiting on other teams?
   - Need for design/UX input?
   - Require production data or logs?

**Output:**
```
## Risks & Mitigations

### Risk 1: [Description]
**Likelihood:** [High/Medium/Low]
**Impact:** [High/Medium/Low]
**Mitigation:** [How to address]

### Unknown 1: [Description]
**Investigation Task:** [How to resolve unknown]
**Estimated Time:** [Time to investigate]

### Blocker 1: [Description]
**Dependency:** [What/who we're waiting on]
**Workaround:** [Can we proceed without this?]
```

---

## Phase 4: Plan Review & Validation

**Directive:** Self-review the plan for completeness, clarity, and feasibility.

**Review Checklist:**

- [ ] **Requirements are clear** - All success criteria defined
- [ ] **Approach is justified** - Explained why this approach was chosen
- [ ] **Tasks are atomic** - All tasks are 2-5 minutes
- [ ] **Tasks have clear completion criteria** - No ambiguous "implement X"
- [ ] **Dependencies are identified** - Task order makes sense
- [ ] **Tests are included** - TDD cycle for all feature code
- [ ] **Edge cases are covered** - Not just happy path
- [ ] **Verification is included** - Plan includes checking the work
- [ ] **Risks are identified** - Potential blockers documented
- [ ] **Estimate is realistic** - Total time seems achievable

**Output:**
```
## Plan Review

**Completeness:** ✅ / ⚠ / ❌
**Clarity:** ✅ / ⚠ / ❌
**Feasibility:** ✅ / ⚠ / ❌

**Issues Found:**
- Issue 1: [Description and fix]
- Issue 2: [Description and fix]

**Plan Status:** ✅ Ready to Execute / ⚠ Needs Revision / ❌ Blocked
```

**Constraint:** Do not mark plan as "Ready to Execute" unless all checklist items are ✅.

---

## Phase 5: Execution Mode

**Directive:** Execute the plan task-by-task, updating checkboxes as you complete each one.

**Execution Rules:**

1. **One task at a time** - Complete each task fully before moving to next
2. **Update checkboxes** - Mark tasks complete as you finish them
3. **Track deviations** - Note if tasks take longer than estimated or new tasks emerge
4. **Pause for blockers** - Stop and re-plan if you hit an unexpected blocker

**During Execution:**
```
## Progress

**Current Task:** CORE-003 (in progress)
**Completed:** 12/24 tasks
**Estimated Remaining:** 18 minutes

**Deviations:**
- CORE-002 took 7m instead of 4m (more validation edge cases than expected)
- Added new task EDGE-005 for empty input handling

**Blockers:**
- None currently
```

**Post-Execution Review:**
```
## Execution Summary

**Actual Time:** [Total time taken]
**Planned Time:** [Original estimate]
**Variance:** [+X minutes / -X minutes]

**What went well:**
- Point 1
- Point 2

**What could improve:**
- Point 1
- Point 2

**Lessons for next plan:**
- Lesson 1
- Lesson 2
```

---

## Examples

### Example 1: Add Dark Mode Toggle

```markdown
## Requirement Summary

**Purpose:** Allow users to switch between light and dark themes

**Success Criteria:**
- [ ] Toggle button in settings menu
- [ ] Theme persists across sessions
- [ ] All components render correctly in both themes

**Constraints:**
- Must work with existing CSS-in-JS solution
- No layout shift when switching themes

**Existing Patterns:**
- Theme context in `src/context/ThemeContext.tsx`
- Theme tokens in `src/styles/tokens.ts`

---

## Implementation Tasks

### Phase 1: Setup
- [ ] **SETUP-001** (2m): Create branch `feature/dark-mode-toggle`
- [ ] **SETUP-002** (3m): Add dark theme tokens to `tokens.ts`

### Phase 2: State Management
- [ ] **STATE-001** (3m): Test: ThemeContext provides toggle function
- [ ] **STATE-002** (4m): Implement toggle function in ThemeContext
- [ ] **STATE-003** (2m): Verify test passes

### Phase 3: UI Component
- [ ] **UI-001** (3m): Test: Toggle button renders in settings
- [ ] **UI-002** (4m): Create ThemeToggle component
- [ ] **UI-003** (3m): Test: Clicking toggle updates theme
- [ ] **UI-004** (4m): Implement click handler with state update

### Phase 4: Persistence
- [ ] **PERSIST-001** (3m): Test: Theme saved to localStorage
- [ ] **PERSIST-002** (4m): Implement localStorage persistence
- [ ] **PERSIST-003** (2m): Test: Theme loaded on page refresh
- [ ] **PERSIST-004** (3m): Implement theme loading on mount

### Phase 5: Verification
- [ ] **VERIFY-001** (3m): Manual test: Toggle works
- [ ] **VERIFY-002** (3m): Manual test: Check all major pages in dark mode
- [ ] **VERIFY-003** (2m): Run test suite
- [ ] **VERIFY-004** (1m): Check for console errors

**Total Estimate:** 49 minutes
```

---

## Anti-Patterns

### ❌ Vague Tasks
```
- [ ] Implement authentication
- [ ] Fix bugs
- [ ] Add tests
```

### ✅ Specific Tasks
```
- [ ] **AUTH-001** (3m): Add email/password fields to login form
- [ ] **BUG-001** (2m): Fix null pointer in user profile when avatar is missing
- [ ] **TEST-001** (3m): Test: Login form validates email format
```

### ❌ Tasks Without Time Estimates
```
- [ ] Create API endpoint
- [ ] Update UI
```

### ✅ Tasks With Realistic Estimates
```
- [ ] **API-001** (4m): Create POST /api/users endpoint with body validation
- [ ] **UI-001** (3m): Update user list component to show avatars
```

### ❌ Missing Test Tasks
```
- [ ] Implement user registration
```

### ✅ TDD Cycle Included
```
- [ ] **REG-001** (3m): Test: User can register with email/password
- [ ] **REG-002** (4m): Implement registration form submission
- [ ] **REG-003** (2m): Verify test passes
```

---

## Notes

- **Iterative Planning**: For large features, plan 1-2 hours of work at a time, then re-plan based on progress
- **Collaborative**: Present options and wait for user input on approach selection
- **Adaptive**: If plan needs significant changes during execution, pause and re-plan
- **Evidence-Based**: After completing a plan, review actual vs. estimated time to improve future estimates
