---
name: verification-protocol
description: >-
  Evidence-based verification protocol for validating work completion. Runs actual
  commands, checks actual output, and provides evidence before making success claims.
  Use before declaring features complete, bugs fixed, or tests passing.
---

# Verification Protocol

Systematic verification that work is actually complete. No assertions without evidence. No claims without running actual commands.

## When to Use

- Before declaring a feature "complete"
- Before claiming a bug is "fixed"
- Before stating tests "pass"
- Before committing code
- Before creating a pull request
- After any significant code change

## Philosophy

**Evidence before assertions.** If you haven't run the command and seen the output, you don't know if it works.

**Verification Cycle:**
```
🔧 BUILD   → Ensure code compiles/builds
✅ TEST    → Run test suite and verify pass
🔍 LINT    → Check code quality and style
🚀 RUNTIME → Verify behavior in running application
```

---

## Phase 0: Verification Planning

**Directive:** Identify what needs to be verified before starting verification.

**Questions to answer:**

1. **What did we build/fix?**
   - New feature?
   - Bug fix?
   - Refactoring?
   - Performance improvement?

2. **What are the success criteria?**
   - What should work now that didn't before?
   - What behavior should NOT have changed?
   - What metrics should improve?

3. **What verification methods apply?**
   - Unit tests?
   - Integration tests?
   - Manual testing?
   - Performance benchmarks?

**Output:**
```
## Verification Plan

**Change Type:** [Feature/Bug Fix/Refactoring/Performance]

**Success Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

**Verification Methods:**
- [ ] Build succeeds
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Linter passes
- [ ] Manual testing in [environment]
- [ ] Performance benchmarks
```

---

## Phase 1: Build Verification

**Directive:** Verify the code compiles/builds without errors.

**Commands to run:**

```bash
# For TypeScript/JavaScript
npm run build
# or
yarn build
# or
pnpm build

# For Java
./gradlew build

# For Python
python -m py_compile src/**/*.py

# For Go
go build ./...
```

**Verification Steps:**

1. **Run the build command**
2. **Capture the full output**
3. **Check for errors**
4. **Verify artifacts are created**

**Output:**
```
## Build Verification

**Command:** `npm run build`

**Exit Code:** 0 ✅

**Output:**
```
> project@1.0.0 build
> tsc && vite build

vite v4.3.0 building for production...
✓ 234 modules transformed.
dist/index.html                 0.45 kB
dist/assets/index-d2f2a8.css    3.21 kB
dist/assets/index-f4e2b1.js   142.34 kB
✓ built in 2.43s
```

**Artifacts Created:**
- ✅ dist/index.html
- ✅ dist/assets/index-d2f2a8.css
- ✅ dist/assets/index-f4e2b1.js

**Status:** ✅ PASS / ❌ FAIL
```

**Constraint:** Do not proceed if build fails. Fix build errors first.

---

## Phase 2: Test Verification

**Directive:** Run ALL relevant tests and verify they pass. Capture actual output.

**Commands to run:**

```bash
# Run all tests
npm test
# or
yarn test
# or
pytest
# or
./gradlew test

# Run specific test suite (if applicable)
npm test -- user.test.ts
```

**Verification Steps:**

1. **Run the test command**
2. **Capture the full output**
3. **Count passing/failing tests**
4. **Identify any failures or warnings**
5. **Verify new tests were added (if feature work)**

**Output:**
```
## Test Verification

**Command:** `npm test`

**Exit Code:** 0 ✅

**Output:**
```
 PASS  src/features/auth/login.test.ts
  Login Component
    ✓ renders login form (45 ms)
    ✓ validates email format (32 ms)
    ✓ shows error on invalid credentials (87 ms)
    ✓ redirects on successful login (56 ms)

 PASS  src/features/auth/register.test.ts
  Register Component
    ✓ renders registration form (38 ms)
    ✓ validates password strength (41 ms)

Test Suites: 2 passed, 2 total
Tests:       6 passed, 6 total
Snapshots:   0 total
Time:        3.451 s
```

**Test Summary:**
- Total: 6
- Passed: 6 ✅
- Failed: 0 ✅
- New tests added: 4 (CORE-001, CORE-003, EDGE-001, EDGE-003)

**Coverage (if available):**
- Statements: 94.2%
- Branches: 89.1%
- Functions: 92.7%
- Lines: 93.8%

**Status:** ✅ PASS / ❌ FAIL
```

**Constraint:** Do not proceed if any tests fail. Fix failing tests first.

---

## Phase 3: Linter Verification

**Directive:** Run linter and type checker to verify code quality.

**Commands to run:**

```bash
# ESLint (JavaScript/TypeScript)
npm run lint
# or
eslint src/

# TypeScript type checking
tsc --noEmit

# Prettier (code formatting)
npm run format:check

# Java Checkstyle
./gradlew checkstyleMain

# Python
flake8 src/
mypy src/
```

**Verification Steps:**

1. **Run linter**
2. **Run type checker**
3. **Run formatter check**
4. **Capture all output**
5. **Verify zero errors and warnings**

**Output:**
```
## Linter Verification

### ESLint

**Command:** `npm run lint`

**Exit Code:** 0 ✅

**Output:**
```
✔ No ESLint warnings or errors
```

### TypeScript

**Command:** `tsc --noEmit`

**Exit Code:** 0 ✅

**Output:**
```
[no output - compilation successful]
```

### Prettier

**Command:** `npm run format:check`

**Exit Code:** 0 ✅

**Output:**
```
All matched files use Prettier code style!
```

**Status:** ✅ PASS / ❌ FAIL
```

**Constraint:** Do not proceed if linter reports errors. Fix linting issues first.

---

## Phase 4: Runtime Verification

**Directive:** Run the application and manually verify the feature works as expected.

**Verification Steps:**

1. **Start the application** (dev server, local deployment, etc.)
2. **Navigate to the feature**
3. **Test the happy path**
4. **Test edge cases**
5. **Check for console errors**
6. **Verify network requests**
7. **Take screenshots if visual changes**

**Output:**
```
## Runtime Verification

### Environment
- **Mode:** Development
- **URL:** http://localhost:3000
- **Browser:** Chrome 122.0.6261.112

### Happy Path Testing

**Test 1: User can log in with valid credentials**
- Steps:
  1. Navigate to /login
  2. Enter email: test@example.com
  3. Enter password: validPassword123
  4. Click "Log In" button
- Expected: Redirect to /dashboard
- Actual: ✅ Redirected to /dashboard after 230ms
- Console: ✅ No errors
- Network: ✅ POST /api/auth/login returned 200

**Test 2: User sees profile after login**
- Steps:
  1. Click profile icon in navbar
- Expected: Profile menu shows user email
- Actual: ✅ Menu shows "test@example.com"
- Console: ✅ No errors

### Edge Case Testing

**Test 3: Invalid credentials show error**
- Steps:
  1. Navigate to /login
  2. Enter email: test@example.com
  3. Enter password: wrongPassword
  4. Click "Log In" button
- Expected: Error message "Invalid credentials"
- Actual: ✅ Error displayed "Invalid credentials"
- Console: ✅ No errors
- Network: ✅ POST /api/auth/login returned 401

**Test 4: Network timeout handled gracefully**
- Steps:
  1. Throttle network to "Offline" in DevTools
  2. Attempt login
- Expected: Error message "Network error, please try again"
- Actual: ✅ Error displayed correctly
- Console: ✅ No errors

### Regression Testing

**Verified unchanged features:**
- ✅ Registration still works
- ✅ Password reset still works
- ✅ Logout still works

### Console Errors
```
[no errors]
```

### Network Issues
```
[no issues]
```

**Screenshots:** [if applicable]
- Before: [screenshot]
- After: [screenshot]

**Status:** ✅ PASS / ❌ FAIL
```

**Constraint:** Do not proceed if runtime testing reveals issues. Fix issues first.

---

## Phase 5: Performance Verification (Optional)

**Directive:** For performance-sensitive changes, verify metrics have improved.

**Verification Steps:**

1. **Run performance benchmarks**
2. **Compare before and after**
3. **Verify improvement meets goals**

**Output:**
```
## Performance Verification

### Metrics

| Metric | Before | After | Change | Goal | Status |
|--------|--------|-------|--------|------|--------|
| Load Time | 3.2s | 1.8s | -1.4s (-44%) | <2s | ✅ PASS |
| Time to Interactive | 4.1s | 2.3s | -1.8s (-44%) | <3s | ✅ PASS |
| Bundle Size | 842 KB | 654 KB | -188 KB (-22%) | <700 KB | ✅ PASS |

### Benchmark Results

**Command:** `npm run benchmark`

**Output:**
```
Running benchmark suite...

login-flow x 1,234 ops/sec ±1.2% (85 runs sampled)
registration-flow x 987 ops/sec ±0.8% (82 runs sampled)

Fastest is login-flow
```

**Status:** ✅ PASS / ⚠ INCONCLUSIVE / ❌ FAIL
```

---

## Phase 6: Final Checklist

**Directive:** Review all verification results and confirm work is complete.

**Final Checklist:**

- [ ] **Build succeeds** - Code compiles without errors
- [ ] **All tests pass** - No failing tests
- [ ] **Linter passes** - No linting errors or warnings
- [ ] **Runtime works** - Feature behaves correctly in application
- [ ] **Edge cases handled** - Error cases work as expected
- [ ] **No regressions** - Existing features still work
- [ ] **No console errors** - Clean console output
- [ ] **Performance acceptable** - Metrics meet requirements (if applicable)
- [ ] **Documentation updated** - README, comments, etc. (if needed)
- [ ] **Tests added** - New tests for new functionality

**Output:**
```
## Verification Summary

**Overall Status:** ✅ COMPLETE / ⚠ ISSUES FOUND / ❌ BLOCKED

**Results:**
- Build: ✅ PASS
- Tests: ✅ PASS (6/6)
- Linter: ✅ PASS
- Runtime: ✅ PASS
- Performance: ✅ PASS

**Issues Found:** 0

**Work is ready for:**
- [x] Commit
- [x] Push
- [x] Pull Request
- [ ] Deploy (pending review)
```

**Constraint:** Do not mark work as "complete" unless ALL checklist items are checked.

---

## Evidence Standards

### ❌ Assertions Without Evidence
```
"The feature works now."
"All tests pass."
"The bug is fixed."
```

### ✅ Evidence-Based Claims
```
"The feature works - verified by running `npm test` (6/6 tests pass) and manual testing in dev (login succeeds in 230ms)."

"All tests pass - exit code 0, output shows 'Test Suites: 2 passed, Tests: 6 passed'."

"The bug is fixed - reproduced the issue, applied fix, re-tested with same steps, error no longer occurs."
```

### ❌ Skipping Verification
```
"I added tests, so it should work."
"The code looks correct."
"It passed yesterday."
```

### ✅ Running Actual Commands
```
"Ran `npm test` - all 6 tests pass (see output above)."
"Ran `npm run build` - build succeeds, artifacts created in dist/."
"Manually tested in Chrome - login flow works as expected (see screenshots)."
```

---

## Anti-Patterns

### ❌ Claiming Success Without Running Commands
```
Agent: "The feature is complete and working."
[No evidence of running tests, build, or manual testing]
```

### ✅ Providing Evidence First
```
Agent: "Running verification..."

[Runs build command, shows output]
[Runs test command, shows output]
[Performs manual testing, describes results]

"Verification complete - all checks pass."
```

### ❌ Partial Verification
```
"I ran the tests and they pass."
[Doesn't check build, linter, or runtime]
```

### ✅ Complete Verification
```
"Verification checklist:
- ✅ Build: succeeded (0 errors)
- ✅ Tests: 6/6 pass
- ✅ Linter: 0 errors
- ✅ Runtime: feature works in dev
- ✅ Regressions: none found"
```

---

## Notes

- **Never skip verification** - Always run actual commands before claiming success
- **Show your work** - Include command output in verification results
- **Test edge cases** - Don't just test the happy path
- **Check for regressions** - Verify existing features still work
- **Evidence-based** - Every claim must be backed by actual output
- **Complete before committing** - Run full verification before creating commits/PRs
