# review

{Optional: Specific focus areas, files, or concerns to prioritize in this review}

---

## **Mission Briefing: Code Review Protocol**

You are conducting a rigorous code review of changes since the branch diverged from the base branch. This review must balance **three sources of truth**: codebase conventions, project rules, and technology best practices. When these conflict, flag and resolve with the user.

**For this repo (ai-bootcamp):** Base branch is **main** (or **develop** if used). Project rules live in `.cursor/rules/` (ai-debugging-evaluation-core, codebase-conformance-python, quality-gates, python-style).

---

## **Phase 0: Scope Discovery**

- **Directive:** Identify the review scope by determining what has changed since branching.
- **Actions:**
  1. Use base branch: **main**.
  2. Run `git diff $(git merge-base HEAD main)..HEAD --stat` to get the list of changed files.
  3. Run `git diff $(git merge-base HEAD main)..HEAD` to get the full diff.
  4. Run `git log $(git merge-base HEAD main)..HEAD --oneline` to understand the commit history.
- **Output:** Report the scope: number of files changed, lines added/removed, and commits included.
- **Constraint:** If the diff is enormous (>2000 lines changed), ask the user if they want to review in chunks or focus on specific files.

---

## **Phase 1: Context & Standards Discovery**

- **Directive:** Build a complete understanding of the standards this code must adhere to.
- **Actions:**
  1. **Project Rules:** Read `.cursor/rules/` in the project.
  2. **Codebase Patterns:** Analyze 3-5 existing files similar to the changed files to infer established patterns (naming, structure, error handling, testing, logging).
  3. **Technology Standards:** Identify the tech stack (Python, pytest, Ruff) and recall best practices.
- **Output:** Produce a concise "Standards Context" summary. If no explicit project rules exist, flag this and offer to help create them after the review.

---

## **Phase 2: Change-by-Change Review**

- **Directive:** Review each changed file against all three sources of truth.
- **Review Checklist (for each file/change):** Correctness & Logic; Codebase Consistency; Technology Best Practices; Code Quality (readability, DRY, comments explain why not what).
- **Output Format (per file):**

  ```
  ### `path/to/file.ext`

  **Summary:** One-line description of changes

  **✅ Good:** ...

  **⚠️ Suggestions:** ...

  **❌ Issues:** ...

  **🔀 Conflict Detected:** (if applicable)
  ```

---

## **Phase 3: Conflict Resolution**

- **Directive:** For any conflicts between codebase conventions and technology best practices, present a clear choice to the user (follow convention / adopt best practice / adopt and create a rule). Wait for user input before finalizing.

---

## **Phase 4: Review Summary**

- **Directive:** Provide a comprehensive summary with **Verdict:** [APPROVE / APPROVE WITH SUGGESTIONS / REQUEST CHANGES], critical issues, suggestions, positive highlights, standards gaps, and conflicts resolved.

---

## **Phase 5: Rule Gap Remediation (Optional)**

- **Directive:** If you identified missing project rules during Phase 1, offer to help create them. Only proceed if user confirms.

---

## **Protocol Reminders**

- **Review ONLY changed code** — don't review unchanged files unless directly relevant.
- **Be specific** — reference exact line numbers and code snippets.
- **Be constructive** — explain WHY something is an issue, not just THAT it is.
- **Prioritize** — distinguish between blocking issues and nice-to-haves.
- **Acknowledge good work** — positive feedback reinforces good practices.

**Begin the review now.**
